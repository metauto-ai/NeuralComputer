import ast
import json
import math
from io import StringIO
from typing import Dict, List, Any, Optional, Union, Tuple

import pandas as pd
import warnings

# Canonical mouse action aliases
MOUSE_ACTION_ALIASES = {
    'lclick': 'left_click', 'left': 'left_click', 'button1': 'left_click', 'left_button': 'left_click',
    'rclick': 'right_click', 'right': 'right_click', 'button3': 'right_click', 'right_button': 'right_click',
    'mclick': 'middle_click', 'middle': 'middle_click', 'button2': 'middle_click', 'wheel_click': 'middle_click',
    'dblclick': 'double_click', 'double_left_click': 'double_click', 'doubleclick': 'double_click',
    'tripleclick': 'triple_click', 'triple_left_click': 'triple_click',
}

def canonicalize_mouse_action(name: str) -> str:
    if not isinstance(name, str):
        return name
    key = name.strip().lower()
    return MOUSE_ACTION_ALIASES.get(key, name)


def _parse_keys_cell(cell: Any) -> List[Tuple[str, str]]:
    if cell is None:
        return []
    if isinstance(cell, list):
        out: List[Tuple[str, str]] = []
        for item in cell:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                out.append((str(item[0]), str(item[1])))
        return out
    if isinstance(cell, str):
        text = cell.strip()
        if not text or text == '[]':
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(text)
            except Exception:
                return []
        return _parse_keys_cell(parsed)
    return []


def _normalize_action_csv_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names for different CSV variants in this repo.

    Supported variants include:
    - Timestamp_formatted vs Time
    - Key Events vs Keys
    """
    df = df.copy()

    # Normalize formatted time column
    if 'Time' not in df.columns and 'Timestamp_formatted' in df.columns:
        df.rename(columns={'Timestamp_formatted': 'Time'}, inplace=True)

    # Normalize key events column
    if 'Keys' not in df.columns and 'Key Events' in df.columns:
        df.rename(columns={'Key Events': 'Keys'}, inplace=True)

    # Ensure required columns exist
    required = {'Timestamp', 'X', 'Y', 'Left Click', 'Right Click'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}. Found: {list(df.columns)}")

    return df


def read_record_csv(record_csv_path: str) -> pd.DataFrame:
    """Read per-frame CSV from path and normalize columns."""
    df = pd.read_csv(record_csv_path)
    return _normalize_action_csv_columns(df)


def parse_raw_trajectory(raw_trajectory: Union[str, pd.DataFrame]) -> pd.DataFrame:
    """Parse a raw trajectory CSV payload (string or DataFrame) from Hive."""
    if isinstance(raw_trajectory, pd.DataFrame):
        return _normalize_action_csv_columns(raw_trajectory)

    if not isinstance(raw_trajectory, str) or not raw_trajectory.strip():
        raise ValueError("raw_trajectory must be a non-empty CSV string or DataFrame")

    csv_buffer = StringIO(raw_trajectory)
    df = pd.read_csv(csv_buffer)
    return _normalize_action_csv_columns(df)


def read_actions_json(actions_json_path: str) -> Dict[str, Any]:
    """Read actions JSON file from path."""
    with open(actions_json_path, 'r') as f:
        data = json.load(f)
    if 'actions' not in data:
        raise ValueError(f"Invalid actions JSON (missing 'actions'): {actions_json_path}")
    return data


def parse_meta_actions(meta_action: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Parse a meta_action JSON payload (string or dict) from Hive."""
    if isinstance(meta_action, dict):
        data = meta_action
    elif isinstance(meta_action, str) and meta_action.strip():
        data = json.loads(meta_action)
    else:
        raise ValueError("meta_action must be a non-empty JSON string or dict")

    if not isinstance(data, dict):
        raise ValueError("meta_action JSON must decode to an object")
    if 'actions' not in data:
        data.setdefault('actions', [])
    return data


def _timestamp_to_csv_frame_index(ts: float, fps: float, frame_count: int) -> int:
    """Map an action timestamp (seconds) to CSV row index (0-based).

    Observed采样方式：CSV 第 k 行时间戳为 (k+1)/fps。为了让事件精确落在实际帧，我们使用 round(t * fps - 1)
    映射到 0-based 行，结果再裁剪到 [0, frame_count-1]。

    例如 fps=15：t=0.1333 -> round(0.1333*15-1)=round(0.9995)=1，对应 CSV 第 1 行 (0.1333s)。
    """
    if fps <= 0:
        return 0
    idx = int(round(ts * fps - 1))
    if idx < 0:
        idx = 0
    if idx >= frame_count:
        idx = frame_count - 1
    return idx


def align_actions_to_frames(
    actions_json: Dict[str, Any],
    record_df: pd.DataFrame,
    fps: Optional[float] = None,
) -> List[List[Dict[str, Any]]]:
    """Align actions to per-frame bins matching the CSV rows.

    Returns a list of lists: frame_actions[i] contains the JSON actions that
    align with CSV row i.

    Notes on alignment:
    - The sample CSV uses timestamps at (k+1)/fps; events from JSON at time t
      align with frame index round(t*fps - 1), clamped to valid range.
    - We ignore 'mouse_move' actions because per-frame X/Y are already logged
      in the CSV. Clicks and key events are binned.
    """
    frame_count = len(record_df)
    if frame_count <= 0:
        return []

    if fps is None:
        # Prefer metadata fps if present; otherwise estimate from CSV spacing
        meta_fps = actions_json.get('metadata', {}).get('fps')
        if isinstance(meta_fps, (int, float)) and meta_fps > 0:
            fps = float(meta_fps)
        else:
            # Estimate FPS from median delta of Timestamp column
            ts = record_df['Timestamp'].astype(float).values
            if len(ts) >= 2:
                deltas = pd.Series(ts).diff().dropna().values
                # Guard against zeros
                med = float(pd.Series(deltas[deltas > 0]).median()) if (deltas > 0).any() else 1/15
                fps = 1.0 / med if med > 0 else 15.0
            else:
                fps = 15.0

    frame_actions: List[List[Dict[str, Any]]] = [[] for _ in range(frame_count)]

    for action in actions_json.get('actions', []):
        ts = float(action.get('timestamp', 0.0))
        a_type = action.get('action')

        # Skip mouse_move; CSV already has positions
        if a_type == 'mouse_move':
            continue

        idx = _timestamp_to_csv_frame_index(ts, fps, frame_count)
        frame_actions[idx].append(action)

    return frame_actions


def load_and_align(
    record_csv_path: str,
    actions_json_path: str,
) -> Dict[str, Any]:
    """Convenience loader that returns CSV DataFrame + frame-aligned actions.

    Returns dict with keys:
      - record_df: the normalized CSV DataFrame
      - actions_json: the raw actions JSON
      - frame_actions: list of per-frame action lists (aligned)
      - fps: fps used for alignment
    """
    record_df = read_record_csv(record_csv_path)
    actions_json = read_actions_json(actions_json_path)

    # Determine fps
    fps = actions_json.get('metadata', {}).get('fps')
    if not isinstance(fps, (int, float)) or fps <= 0:
        # Fallback: infer from CSV
        ts = record_df['Timestamp'].astype(float)
        deltas = ts.diff().dropna()
        med = deltas[deltas > 0].median() if not deltas.empty else (1/15)
        fps = float(1.0 / med) if med and med > 0 else 15.0

    frame_actions = align_actions_to_frames(actions_json, record_df, float(fps))

    return {
        'record_df': record_df,
        'actions_json': actions_json,
        'frame_actions': frame_actions,
        'fps': float(fps),
    }


def load_session(
    *,
    meta_action: Optional[Union[str, Dict[str, Any]]] = None,
    raw_trajectory: Optional[Union[str, pd.DataFrame]] = None,
    fps: Optional[float] = None,
) -> Dict[str, Any]:
    """Load a session from Hive-style columns.

    Args:
        meta_action: JSON string or dict containing actions (optional)
        raw_trajectory: CSV string or DataFrame of per-frame data (optional)
        fps: Optional override for frames-per-second alignment

    Returns dict with keys:
        - record_df: per-frame DataFrame
        - actions_json: parsed meta action dict (if provided)
        - frame_actions: combined per-frame actions (meta + raw)
        - frame_actions_meta: actions derived purely from meta_action (if any)
        - frame_actions_raw: actions derived from raw_trajectory
        - meta_actions_list: flattened meta actions
        - raw_actions_list: flattened raw actions
        - fps: fps used for alignment (float)
    """

    record_df: Optional[pd.DataFrame] = None
    actions_json: Optional[Dict[str, Any]] = None

    if raw_trajectory is not None:
        record_df = parse_raw_trajectory(raw_trajectory)

    if meta_action is not None:
        actions_json = parse_meta_actions(meta_action)
        if record_df is None:
            derived_df = _meta_frames_to_dataframe(actions_json)
            if derived_df is not None:
                record_df = derived_df

    if record_df is None:
        raise ValueError("No per-frame trajectory available. Provide raw_trajectory CSV or meta_action with frames[]")

    resolved_fps: float
    if isinstance(fps, (int, float)) and fps > 0:
        resolved_fps = float(fps)
    elif actions_json and isinstance(actions_json.get('metadata', {}).get('fps'), (int, float)):
        resolved_fps = float(actions_json['metadata']['fps'])
    else:
        ts = record_df['Timestamp'].astype(float)
        deltas = ts.diff().dropna()
        med = deltas[deltas > 0].median() if not deltas.empty else (1/15)
        resolved_fps = float(1.0 / med) if med and med > 0 else 15.0

    if actions_json:
        frame_actions_meta = align_actions_to_frames(actions_json, record_df, resolved_fps)
        meta_actions_flat = actions_json.get('actions', [])
    else:
        frame_actions_meta = [[] for _ in range(len(record_df))]
        meta_actions_flat = []

    frame_actions_raw, raw_actions_flat = _frame_actions_from_record_df(record_df)
    combined_frame_actions = merge_frame_actions(frame_actions_meta, frame_actions_raw)

    return {
        'record_df': record_df,
        'actions_json': actions_json,
        'frame_actions': combined_frame_actions,
        'frame_actions_meta': frame_actions_meta,
        'frame_actions_raw': frame_actions_raw,
        'meta_actions_list': meta_actions_flat,
        'raw_actions_list': raw_actions_flat,
        'fps': resolved_fps,
    }


def read_meta_actions_json(path: str) -> Dict[str, Any]:
    """Read meta-actions JSON produced by convert_csv_to_meta_actions.

    Expects schema with keys: metadata, frames (optional), actions (optional).
    """
    with open(path, 'r') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Meta-actions JSON must be an object")
    return data


def _meta_frames_to_dataframe(meta: Dict[str, Any]) -> Optional[pd.DataFrame]:
    frames = meta.get('frames')
    if not isinstance(frames, list) or not frames:
        return None

    rows = []
    for frame in frames:
        timestamp = float(frame.get('timestamp', 0.0))
        time_fmt = frame.get('time_formatted') or frame.get('Time')
        if not time_fmt:
            seconds = int(timestamp)
            milliseconds = int((timestamp - seconds) * 1000)
            time_fmt = f"{seconds}:{milliseconds}"

        x = int(frame.get('x', frame.get('X', 0)))
        y = int(frame.get('y', frame.get('Y', 0)))
        left = bool(frame.get('left_click', frame.get('Left Click', False)))
        right = bool(frame.get('right_click', frame.get('Right Click', False)))

        keys_raw = frame.get('keys', frame.get('Keys', [])) or []
        key_tuples: List[tuple] = []
        if isinstance(keys_raw, list):
            for item in keys_raw:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    key_tuples.append((item[0], item[1]))
        elif isinstance(keys_raw, str):
            # Assume already serialized
            try:
                parsed = json.loads(keys_raw)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, (list, tuple)) and len(item) == 2:
                            key_tuples.append((item[0], item[1]))
            except Exception:
                pass

        rows.append({
            'Timestamp': timestamp,
            'Time': time_fmt,
            'X': x,
            'Y': y,
            'Left Click': left,
            'Right Click': right,
            'Keys': str(key_tuples),
        })

    df = pd.DataFrame(rows, columns=['Timestamp', 'Time', 'X', 'Y', 'Left Click', 'Right Click', 'Keys'])
    return _normalize_action_csv_columns(df)


def _frame_actions_from_record_df(record_df: pd.DataFrame) -> Tuple[List[List[Dict[str, Any]]], List[Dict[str, Any]]]:
    frame_actions: List[List[Dict[str, Any]]] = [[] for _ in range(len(record_df))]
    flat_actions: List[Dict[str, Any]] = []

    for idx, row in record_df.iterrows():
        try:
            ts = float(row.get('Timestamp', idx))
        except Exception:
            ts = float(idx)
        x = int(row.get('X', 0))
        y = int(row.get('Y', 0))

        def append_event(event: Dict[str, Any]) -> None:
            frame_actions[idx].append(event)
            flat_actions.append(event)

        if bool(row.get('Left Click', False)):
            append_event({'action': 'left_click', 'coordinate': [x, y], 'timestamp': ts, 'frame_index': idx})
        if bool(row.get('Right Click', False)):
            append_event({'action': 'right_click', 'coordinate': [x, y], 'timestamp': ts, 'frame_index': idx})

        for state, key in _parse_keys_cell(row.get('Keys', [])):
            if str(state).lower() != 'keydown':
                continue
            key_str = str(key)
            if len(key_str) == 1 and key_str.isprintable():
                event = {'action': 'type', 'text': key_str, 'timestamp': ts, 'frame_index': idx}
            else:
                event = {'action': 'key', 'text': key_str, 'timestamp': ts, 'frame_index': idx}
            append_event(event)

    return frame_actions, flat_actions


def build_frame_actions_from_meta(meta: Dict[str, Any], frame_count: Optional[int] = None) -> List[List[Dict[str, Any]]]:
    """Build per-frame actions from a meta JSON.

    If actions include 'frame_index', we place them directly. Otherwise, we
    fall back to timestamp alignment using metadata.fps.
    """
    actions = meta.get('actions', []) or []
    if frame_count is None:
        # Prefer frames length if present; otherwise use metadata.frame_count
        if isinstance(meta.get('frames'), list):
            frame_count = len(meta['frames'])
        else:
            frame_count = int(meta.get('metadata', {}).get('frame_count', 0))
    if not frame_count:
        raise ValueError("Cannot determine frame_count from meta JSON")

    fps = meta.get('metadata', {}).get('fps', 15.0)
    try:
        fps = float(fps)
    except Exception:
        fps = 15.0

    frame_actions: List[List[Dict[str, Any]]] = [[] for _ in range(frame_count)]

    def to_idx(evt: Dict[str, Any]) -> Optional[int]:
        if 'frame_index' in evt:
            try:
                idx = int(evt['frame_index'])
            except Exception:
                return None
            if 0 <= idx < frame_count:
                return idx
            return max(0, min(frame_count - 1, idx))
        ts = evt.get('timestamp')
        if ts is None:
            return None
        try:
            return _timestamp_to_csv_frame_index(float(ts), fps, frame_count)
        except Exception:
            return None

    for evt in actions:
        idx = to_idx(evt)
        if idx is None:
            continue
        # Do not clone; pass through as-is so consumers can see original fields
        frame_actions[idx].append(evt)

    return frame_actions


def align_generic_events_to_frames(
    events: List[Dict[str, Any]],
    record_df: pd.DataFrame,
    fps: Optional[float] = None,
) -> List[List[Dict[str, Any]]]:
    """Align arbitrary events (interactive/API) to CSV frames.

    Each event may carry 'frame_index' or 'timestamp'. If both are missing,
    the event is skipped. 'mouse_move' events are ignored by default.
    """
    frame_count = len(record_df)
    if frame_count <= 0:
        return []

    if fps is None:
        ts = record_df['Timestamp'].astype(float)
        deltas = ts.diff().dropna()
        med = deltas[deltas > 0].median() if not deltas.empty else (1/15)
        fps = float(1.0 / med) if med and med > 0 else 15.0

    frame_actions: List[List[Dict[str, Any]]] = [[] for _ in range(frame_count)]

    for evt in events or []:
        if evt.get('action') == 'mouse_move':
            continue
        if 'frame_index' in evt:
            try:
                idx = int(evt['frame_index'])
            except Exception:
                continue
        else:
            ts = evt.get('timestamp')
            if ts is None:
                continue
            try:
                idx = _timestamp_to_csv_frame_index(float(ts), float(fps), frame_count)
            except Exception:
                continue
        idx = max(0, min(frame_count - 1, idx))
        frame_actions[idx].append(evt)

    return frame_actions


def merge_frame_actions(a: List[List[Dict[str, Any]]], b: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
    """Merge two per-frame action lists (e.g., interactive + API) by concatenation.

    If lengths differ, the result has min(len(a), len(b)) frames.
    """
    if not a:
        return b or []
    if not b:
        return a
    n = min(len(a), len(b))
    merged: List[List[Dict[str, Any]]] = []
    for i in range(n):
        merged.append(list(a[i]) + list(b[i]))
    return merged


def build_keyboard_vocab_from_frame_actions(
    frame_actions: List[List[Dict[str, Any]]],
    include_type: bool = True,
    include_key: bool = True,
    include_chord: bool = True,
) -> Dict[str, int]:
    """Build a token->index vocab from per-frame actions.

    - type: single printable characters, tokenized as literal chars
    - key: special keys, tokenized as e.g. 'KEY:Enter'
    - key_chord: combos, tokenized as e.g. 'CHORD:ctrl+c'
    Returns mapping without reserved specials; caller can add PAD/UNK.
    """
    tokens = []
    for fa in frame_actions or []:
        for a in fa or []:
            t = a.get('action')
            if include_type and t == 'type':
                ch = a.get('text')
                if isinstance(ch, str) and ch:
                    tokens.append(ch)
            elif include_key and t == 'key':
                k = a.get('text')
                if isinstance(k, str) and k:
                    tokens.append(f"KEY:{k}")
            elif include_chord and t == 'key_chord':
                combo = a.get('combo')
                if isinstance(combo, str) and combo:
                    tokens.append(f"CHORD:{combo}")
    uniq = sorted(set(tokens))
    return {tok: i for i, tok in enumerate(uniq)}


__all__ = [
    'read_record_csv',
    'read_actions_json',
    'parse_raw_trajectory',
    'parse_meta_actions',
    'align_actions_to_frames',
    'load_and_align',
    'load_session',
    'read_meta_actions_json',
    'build_frame_actions_from_meta',
    'align_generic_events_to_frames',
    'merge_frame_actions',
    'MOUSE_ACTION_ALIASES',
    'canonicalize_mouse_action',
    'build_keyboard_vocab_from_frame_actions',
]
