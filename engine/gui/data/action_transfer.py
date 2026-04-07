#!/usr/bin/env python3

import argparse
import ast
import json
import math
import os
from typing import Any, Dict, List, Tuple, Optional
from collections import deque

import pandas as pd


def _normalize_csv_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Normalize time formatted column name
    if 'Time' not in df.columns and 'Timestamp_formatted' in df.columns:
        df.rename(columns={'Timestamp_formatted': 'Time'}, inplace=True)

    # Normalize keys column name
    if 'Keys' not in df.columns and 'Key Events' in df.columns:
        df.rename(columns={'Key Events': 'Keys'}, inplace=True)

    required = {'Timestamp', 'X', 'Y', 'Left Click', 'Right Click'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}. Found: {list(df.columns)}")
    return df


def _parse_keys_cell(cell: Any) -> List[Tuple[str, str]]:
    """Parse the 'Keys' cell (Python-like list of tuples as string)."""
    if cell is None or (isinstance(cell, float) and math.isnan(cell)):
        return []
    s = str(cell).strip()
    if not s or s == '[]':
        return []
    try:
        value = ast.literal_eval(s)
    except Exception:
        return []
    result: List[Tuple[str, str]] = []
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                etype, key = item
                if isinstance(etype, str) and isinstance(key, str):
                    result.append((etype, key))
    return result


def _infer_fps_from_timestamps(df: pd.DataFrame) -> float:
    ts = df['Timestamp'].astype(float)
    deltas = ts.diff().dropna()
    pos = deltas[deltas > 0]
    med = float(pos.median()) if not pos.empty else (1.0 / 15.0)
    fps = 1.0 / med if med > 0 else 15.0
    return float(fps)


def _derive_actions_from_frames(
    frames: List[Dict[str, Any]],
    double_click_window_s: float = 0.3,
    chord_modifiers: Tuple[str, ...] = (
        'Control_L', 'Control_R', 'Shift_L', 'Shift_R', 'Alt_L', 'Alt_R', 'Super_L', 'Super_R', 'Meta_L', 'Meta_R'
    ),
) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []

    # Click pulses: treat any frame with left/right_click=True as a click pulse.
    left_click_times = deque(maxlen=4)

    # Active modifier state across frames for chord detection
    active_mods: set = set()

    for f in frames:
        i = f['index']
        t = float(f['timestamp'])
        x = int(f['x'])
        y = int(f['y'])
        left = bool(f['left_click'])
        right = bool(f['right_click'])

        # Left click pulse
        if left:
            actions.append({
                'action': 'left_click',
                'coordinate': [x, y],
                'timestamp': t,
                'frame_index': i,
            })
            # Multi-click identification within a time window
            left_click_times.append(t)
            count = 1
            for prev_t in list(left_click_times)[:-1][::-1]:
                if (t - prev_t) <= double_click_window_s:
                    count += 1
                else:
                    break
            if count == 2:
                actions.append({
                    'action': 'double_click',
                    'coordinate': [x, y],
                    'timestamp': t,
                    'frame_index': i,
                })
            elif count == 3:
                actions.append({
                    'action': 'triple_click',
                    'coordinate': [x, y],
                    'timestamp': t,
                    'frame_index': i,
                })

        # Right click pulse
        if right:
            actions.append({
                'action': 'right_click',
                'coordinate': [x, y],
                'timestamp': t,
                'frame_index': i,
            })

        # Key events to meta-actions
        # First pass: clear modifiers on keyup
        for etype, key in f.get('keys', []):
            if key in chord_modifiers and etype == 'keyup':
                active_mods.discard(key)
        # Second pass: handle keydowns
        for etype, key in f.get('keys', []):
            if key in chord_modifiers:
                if etype == 'keydown':
                    active_mods.add(key)
                continue

            if etype == 'keydown':
                if len(key) == 1 and key.isprintable():
                    actions.append({
                        'action': 'type',
                        'text': key,
                        'timestamp': t,
                        'frame_index': i,
                    })
                else:
                    actions.append({
                        'action': 'key',
                        'text': key,
                        'timestamp': t,
                        'frame_index': i,
                    })
                # Derived chord event if modifiers are active
                if active_mods:
                    def canon(m: str) -> str:
                        m = m.lower()
                        if 'control' in m:
                            return 'ctrl'
                        if 'shift' in m:
                            return 'shift'
                        if 'alt' in m:
                            return 'alt'
                        if 'super' in m or 'meta' in m:
                            return 'meta'
                        return m
                    mods = sorted({canon(m) for m in active_mods})
                    combo = '+'.join(mods + [str(key)])
                    actions.append({
                        'action': 'key_chord',
                        'combo': combo,
                        'timestamp': t,
                        'frame_index': i,
                    })

    return actions


def csv_to_meta_json(df: pd.DataFrame, source_path: str) -> Dict[str, Any]:
    df = _normalize_csv_columns(df)
    fps = _infer_fps_from_timestamps(df)

    frames: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        keys_parsed = _parse_keys_cell(row.get('Keys', '[]'))
        frames.append({
            'index': int(idx),
            'timestamp': float(row['Timestamp']),
            'time_formatted': str(row.get('Time', '')),
            'x': int(row.get('X', 0)),
            'y': int(row.get('Y', 0)),
            'left_click': bool(row.get('Left Click', False)),
            'right_click': bool(row.get('Right Click', False)),
            'double_click': False,
            'triple_click': False,
            'middle_click': False,
            'keys': [[str(et), str(k)] for (et, k) in keys_parsed],
        })

    actions = _derive_actions_from_frames(frames)
    # Annotate frames with derived double/triple click pulses
    for a in actions:
        typ = a.get('action')
        if typ in ('double_click', 'triple_click') and 'frame_index' in a:
            fi = int(a['frame_index'])
            if 0 <= fi < len(frames):
                frames[fi][typ] = True

    meta: Dict[str, Any] = {
        'metadata': {
            'source': 'csv_record',
            'source_path': source_path,
            'fps': fps,
            'frame_count': len(frames),
            'action_frame_applies_to_next_frame': True,
            'csv_columns': list(df.columns),
            'double_click_window_s': 0.3,
        },
        'frames': frames,
        'actions': actions,
    }
    return meta


def _extract_index_from_filename(path: str) -> Optional[int]:
    import re
    m = re.search(r'_(\d+)\.csv$', os.path.basename(path))
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def csv_to_actions_only_json(
    df: pd.DataFrame,
    source_path: str,
    trajectory_id: Optional[int] = None,
    add_success_events: bool = True,
    success_delay_seconds: float = 0.0,
) -> Dict[str, Any]:

    df = _normalize_csv_columns(df)
    fps = _infer_fps_from_timestamps(df)

    # Build frames to reuse action derivation
    frames: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        keys_parsed = _parse_keys_cell(row.get('Keys', '[]'))
        frames.append({
            'index': int(idx),
            'timestamp': float(row['Timestamp']),
            'x': int(row.get('X', 0)),
            'y': int(row.get('Y', 0)),
            'left_click': bool(row.get('Left Click', False)),
            'right_click': bool(row.get('Right Click', False)),
            'keys': [[str(et), str(k)] for (et, k) in keys_parsed],
        })

    derived = _derive_actions_from_frames(frames)

    def fmt_time(ts: float) -> str:
        s = int(ts)
        ms = int(round((ts - s) * 1000))
        return f"{s}:{ms}"

    def add_success(base_action: Dict[str, Any]):
        if not add_success_events:
            return
        ts_s = float(base_action['timestamp']) + float(success_delay_seconds)
        actions_v2.append({
            'timestamp': ts_s,
            'time_formatted': fmt_time(ts_s),
            'tool_name': 'computer',
            'action': f"{base_action['action']}_success",
            'x': None,
            'y': None,
            'text': None,
            'key': None,
            'scroll_direction': None,
            'scroll_amount': None,
            'duration': None,
            'success': True,
            'error': None,
            'thinking': None,
        })

    actions_v2: List[Dict[str, Any]] = []
    for a in derived:
        typ = a.get('action')
        ts = float(a.get('timestamp', 0.0))
        fi = int(a.get('frame_index', -1)) if 'frame_index' in a else -1
        x = y = None
        if typ in ('left_click', 'right_click', 'double_click', 'triple_click'):
            coord = a.get('coordinate')
            if not coord and 0 <= fi < len(frames):
                coord = [frames[fi]['x'], frames[fi]['y']]
            if coord:
                x, y = int(coord[0]), int(coord[1])

        # Map meta types to CUA schema
        if typ in ('left_click', 'right_click', 'double_click', 'triple_click'):
            base = {
                'timestamp': ts,
                'time_formatted': fmt_time(ts),
                'tool_name': 'computer',
                'action': typ,
                'x': x,
                'y': y,
                'text': None,
                'key': None,
                'scroll_direction': None,
                'scroll_amount': None,
                'duration': None,
                'success': True,
                'error': None,
                'thinking': None,
            }
            actions_v2.append(base)
            add_success(base)
        elif typ == 'type':
            text = a.get('text')
            if isinstance(text, str) and text:
                base = {
                    'timestamp': ts,
                    'time_formatted': fmt_time(ts),
                    'tool_name': 'computer',
                    'action': 'type',
                    'x': None,
                    'y': None,
                    'text': text,
                    'key': None,
                    'scroll_direction': None,
                    'scroll_amount': None,
                    'duration': None,
                    'success': True,
                    'error': None,
                    'thinking': None,
                }
                actions_v2.append(base)
                add_success(base)
        elif typ == 'key' or typ == 'key_chord':
            keyname = a.get('text') if typ == 'key' else a.get('combo')
            if isinstance(keyname, str) and keyname:
                base = {
                    'timestamp': ts,
                    'time_formatted': fmt_time(ts),
                    'tool_name': 'computer',
                    'action': 'key',
                    'x': None,
                    'y': None,
                    'text': None,
                    'key': keyname,
                    'scroll_direction': None,
                    'scroll_amount': None,
                    'duration': None,
                    'success': True,
                    'error': None,
                    'thinking': None,
                }
                actions_v2.append(base)
                add_success(base)
        else:
            # ignore mouse_move etc.
            pass

    meta: Dict[str, Any] = {
        'metadata': {
            'trajectory_id': int(trajectory_id) if trajectory_id is not None else None,
            'source': 'csv_record',
            'fps': float(fps),
            'total_actions': len(actions_v2),
            'recording_type': 'tool_execution',
            'video_sync': True,
        },
        'actions': actions_v2,
    }
    if meta['metadata']['trajectory_id'] is None:
        del meta['metadata']['trajectory_id']
    return meta


def meta_json_to_csv(meta: Dict[str, Any]) -> pd.DataFrame:
    frames = meta.get('frames', [])
    rows = []
    for f in frames:
        keys_list = f.get('keys', [])
        keys_tuples = [(et, k) for et, k in keys_list]
        rows.append({
            'Timestamp': float(f.get('timestamp', 0.0)),
            'Time': str(f.get('time_formatted', '')),
            'X': int(f.get('x', 0)),
            'Y': int(f.get('y', 0)),
            'Left Click': bool(f.get('left_click', False)),
            'Right Click': bool(f.get('right_click', False)),
            'Keys': str(keys_tuples),
        })
    df = pd.DataFrame(rows, columns=['Timestamp', 'Time', 'X', 'Y', 'Left Click', 'Right Click', 'Keys'])
    return df


def actions_only_json_to_csv(actions_obj: Dict[str, Any], ref_df: pd.DataFrame) -> pd.DataFrame:

    df = _normalize_csv_columns(ref_df)
    out = df.copy()
    out['Left Click'] = False
    out['Right Click'] = False
    out['Keys'] = '[]'

    fps = actions_obj.get('metadata', {}).get('fps')
    if not isinstance(fps, (int, float)) or fps <= 0:
        fps = _infer_fps_from_timestamps(df)

    def frame_index(ts: float) -> int:
        # Inverse of CSV frame timestamp mapping: timestamps are (i+1)/fps
        idx = int(round(ts * float(fps) - 1))
        return max(0, min(len(out) - 1, idx))

    key_events_per_frame: List[List[Tuple[str, str]]] = [[] for _ in range(len(out))]

    def expand_chord_keys(keyname: str) -> list[tuple[str, str]]:
        """Expand chord like 'ctrl+shift+t' into multiple keydown pulses.
        Maps modifiers to CSV-friendly names (Control_L/Shift_L/Alt_L/Super_L).
        """
        if not isinstance(keyname, str) or not keyname:
            return []
        parts = [p.strip() for p in keyname.split('+') if p.strip()]
        out: list[tuple[str, str]] = []
        for p in parts:
            low = p.lower()
            if low in ( 'ctrl', 'control'):
                out.append(('keydown', 'Control_L'))
            elif low in ('shift',):
                out.append(('keydown', 'Shift_L'))
            elif low in ('alt', 'option'):
                out.append(('keydown', 'Alt_L'))
            elif low in ('super', 'meta', 'cmd', 'command', 'win'):
                out.append(('keydown', 'Super_L'))
            else:
                out.append(('keydown', p))
        return out

    for ev in actions_obj.get('actions', []) or []:
        typ = ev.get('action')
        ts = ev.get('timestamp')
        if ts is None:
            continue
        try:
            idx = frame_index(float(ts))
        except Exception:
            continue
        if typ == 'left_click':
            out.at[idx, 'Left Click'] = True
        elif typ == 'right_click':
            out.at[idx, 'Right Click'] = True
        elif typ == 'type':
            text = ev.get('text')
            if isinstance(text, str) and text:
                key_events_per_frame[idx].append(('keydown', text))
        elif typ == 'key':
            keyval = ev.get('key') or ev.get('text')
            if isinstance(keyval, str) and keyval:
                for kd in expand_chord_keys(keyval):
                    key_events_per_frame[idx].append(kd)
        else:
            # Ignore double/triple_click for CSV; pulses already captured by left_click
            pass

    # Serialize Keys column as Python-like list of tuples
    out['Keys'] = [str(evts if evts else []) for evts in key_events_per_frame]
    return out


def save_json(obj: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2)


def load_json(path: str) -> Dict[str, Any]:
    with open(path, 'r') as f:
        return json.load(f)


def run_single_csv(
    csv_path: str,
    out_json: str,
    out_format: str = 'meta',
    add_success_events: bool = True,
    success_delay_seconds: float = 0.0,
) -> None:
    df = pd.read_csv(csv_path)
    if out_format == 'meta':
        obj = csv_to_meta_json(df, source_path=csv_path)
    elif out_format == 'actions':
        obj = csv_to_actions_only_json(
            df,
            source_path=csv_path,
            trajectory_id=_extract_index_from_filename(csv_path),
            add_success_events=add_success_events,
            success_delay_seconds=success_delay_seconds,
        )
    else:
        raise SystemExit(f"Unknown out_format: {out_format}")
    save_json(obj, out_json)
    print(f"Saved JSON ({out_format}): {out_json}")


def run_directory(
    in_dir: str,
    out_dir: Optional[str] = None,
    out_format: str = 'meta',
    naming: str = 'meta',
    add_success_events: bool = True,
    success_delay_seconds: float = 0.0,
) -> None:
    """Batch convert a directory of CSVs.

    - out_format: 'meta' (frames+actions) or 'actions' (classic actions-only)
    - naming: 'meta' -> meta_actions_{idx}.json; 'actions_v2' -> actions_{idx}_v2.json
    """
    if out_dir is None:
        out_dir = in_dir
    os.makedirs(out_dir, exist_ok=True)

    for name in sorted(os.listdir(in_dir)):
        if not name.endswith('.csv'):
            continue
        csv_path = os.path.join(in_dir, name)
        import re
        m = re.search(r'_(\d+)\.csv$', name)
        if not m:
            continue
        idx = int(m.group(1))
        if naming == 'meta':
            out_name = f"meta_actions_{idx}.json"
        elif naming == 'actions_v2':
            out_name = f"actions_{idx}_v2.json"
        else:
            raise SystemExit(f"Unknown naming: {naming}")
        out_json = os.path.join(out_dir, out_name)
        run_single_csv(
            csv_path,
            out_json,
            out_format=out_format,
            add_success_events=add_success_events,
            success_delay_seconds=success_delay_seconds,
        )


def _format_time_str(ts: float) -> str:
    s = int(ts)
    ms = int(round((ts - s) * 1000))
    return f"{s}:{ms}"


def cua_json_to_csv(obj: Dict[str, Any], fps: float = 15.0) -> pd.DataFrame:
    """Convert a CUA-style action log JSON to CSV with our standard columns.

    - Builds a per-frame timeline sampled at fps over metadata.duration or last timestamp.
    - X/Y are forward-filled from latest known (x,y) in events; start at 0,0 if unknown.
    - Left/Right Click are pulses set True on frames containing corresponding events.
    - Keys contain ('keydown', ch) for type text (char-wise), and ('scroll', 'dir:amount') for scroll events.
    - Ignores *_success, screenshot, mouse_move in the CSV pulses.
    """
    actions = obj.get('actions', []) or []
    # Determine total duration
    duration = None
    md = obj.get('metadata') or {}
    if isinstance(md.get('duration'), (int, float)):
        duration = float(md['duration'])
    if duration is None:
        # fallback: max timestamp
        ts = [float(a.get('timestamp', 0.0)) for a in actions if a.get('timestamp') is not None]
        duration = max(ts) if ts else 0.0
    duration = max(0.0, duration)

    n_frames = int(math.ceil(duration * float(fps)))
    if n_frames <= 0:
        n_frames = 1

    # Initialize arrays
    timestamps = [ (i+1)/float(fps) for i in range(n_frames) ]  # match our CSV style
    xs = [0] * n_frames
    ys = [0] * n_frames
    left = [False] * n_frames
    right = [False] * n_frames
    keys: List[List[Tuple[str, str]]] = [[] for _ in range(n_frames)]

    # Collect per-frame position samples to forward-fill
    pos_samples: Dict[int, Tuple[int, int]] = {}

    def to_index(t: float) -> int:
        # Map event time to CSV frame index where CSV timestamps are (i+1)/fps
        idx = int(round(t * float(fps) - 1))
        if idx < 0:
            idx = 0
        if idx >= n_frames:
            idx = n_frames - 1
        return idx

    def expand_chord_keys(keyname: str) -> list[tuple[str, str]]:
        if not isinstance(keyname, str) or not keyname:
            return []
        parts = [p.strip() for p in keyname.split('+') if p.strip()]
        out: list[tuple[str, str]] = []
        for p in parts:
            low = p.lower()
            if low in ( 'ctrl', 'control'):
                out.append(('keydown', 'Control_L'))
            elif low in ('shift',):
                out.append(('keydown', 'Shift_L'))
            elif low in ('alt', 'option'):
                out.append(('keydown', 'Alt_L'))
            elif low in ('super', 'meta', 'cmd', 'command', 'win'):
                out.append(('keydown', 'Super_L'))
            else:
                out.append(('keydown', p))
        return out

    for ev in actions:
        act = str(ev.get('action', '') or '')
        if not act:
            continue
        # Normalize action name by stripping success suffix
        if act.endswith('_success'):
            continue
        t = ev.get('timestamp')
        if t is None:
            continue
        try:
            idx = to_index(float(t))
        except Exception:
            continue

        # Position sample
        ex, ey = ev.get('x'), ev.get('y')
        if isinstance(ex, (int, float)) and isinstance(ey, (int, float)):
            pos_samples[idx] = (int(ex), int(ey))

        # Mouse pulses
        if act in ('left_click', 'double_click', 'triple_click'):
            left[idx] = True
        elif act == 'right_click':
            right[idx] = True
        elif act == 'middle_click':
            # CSV schema has no middle button; skip or encode in keys if desired
            pass
        # Keyboard / type
        elif act == 'type':
            text = ev.get('text')
            if isinstance(text, str) and text:
                for ch in text:
                    keys[idx].append(('keydown', ch))
        elif act == 'key':
            keyname = ev.get('key') or ev.get('text')
            if isinstance(keyname, str) and keyname:
                for kd in expand_chord_keys(keyname):
                    keys[idx].append(kd)
        # Scroll
        elif act == 'scroll':
            direction = str(ev.get('scroll_direction') or '')
            amount = ev.get('scroll_amount')
            payload = f"{direction}:{amount}" if amount is not None else direction
            keys[idx].append(('scroll', payload))
        # Ignore others (screenshot, mouse_move, etc.)

    # Forward-fill positions
    last_x, last_y = 0, 0
    for i in range(n_frames):
        if i in pos_samples:
            last_x, last_y = pos_samples[i]
        xs[i] = last_x
        ys[i] = last_y

    # Build DataFrame
    df = pd.DataFrame({
        'Timestamp': timestamps,
        'Time': [_format_time_str(t) for t in timestamps],
        'X': xs,
        'Y': ys,
        'Left Click': left,
        'Right Click': right,
        'Keys': [str(v if v else []) for v in keys],
    })
    return df


def reconstruct_csv(json_path: str, out_csv: str, ref_csv: Optional[str] = None, fps: Optional[float] = None) -> None:
    obj = load_json(json_path)
    if 'frames' in obj:  # meta JSON
        df = meta_json_to_csv(obj)
    else:
        # actions-only paths
        # Heuristic: if it has 'tool_name' entries, treat as CUA; else legacy actions-only v2
        acts = obj.get('actions') or []
        is_cua = any(isinstance(a, dict) and 'tool_name' in a for a in acts)
        if is_cua:
            f = float(fps) if isinstance(fps, (int, float)) else 15.0
            df = cua_json_to_csv(obj, fps=f)
        else:
            if not ref_csv:
                raise SystemExit('--ref-csv is required when reconstructing from actions-only JSON')
            ref_df = pd.read_csv(ref_csv)
            df = actions_only_json_to_csv(obj, ref_df)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"Reconstructed CSV: {out_csv}")


def main():
    parser = argparse.ArgumentParser(description='Transfer between per-frame CSV and meta/action JSON formats.')
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--csv', type=str, help='Input CSV file path')
    g.add_argument('--csv-dir', type=str, help='Input directory containing CSV files')
    g.add_argument('--json', type=str, help='Input JSON file (for reconstructing CSV)')

    parser.add_argument('--out-json', type=str, help='Output JSON file path')
    parser.add_argument('--out-dir', type=str, help='Output directory for batch conversion (defaults to in-dir)')
    parser.add_argument('--out-csv', type=str, help='Output CSV file path when using --json')
    parser.add_argument('--ref-csv', type=str, help='Reference CSV path (required when --json is actions-only)')
    parser.add_argument('--fps', type=float, default=None, help='FPS to use when reconstructing CSV from CUA JSON (default 15.0)')
    parser.add_argument('--out-format', type=str, choices=['meta', 'actions'], default='meta', help='Output content format')
    parser.add_argument('--naming', type=str, choices=['meta', 'actions_v2'], default='meta', help='Output file naming in directory mode')
    parser.add_argument('--with-success', dest='with_success', action='store_true', help='(actions) emit *_success events like CUA')
    parser.add_argument('--no-success', dest='with_success', action='store_false', help='(actions) do not emit *_success events')
    parser.add_argument('--success-delay-seconds', type=float, default=0.0, help='Time offset for *_success timestamps')
    # Default: do NOT emit *_success events
    parser.set_defaults(with_success=False)

    args = parser.parse_args()

    if args.csv:
        if not args.out_json:
            raise SystemExit('--out-json is required when using --csv')
        run_single_csv(
            args.csv,
            args.out_json,
            out_format=args.out_format,
            add_success_events=args.with_success,
            success_delay_seconds=args.success_delay_seconds,
        )
    elif args.csv_dir:
        run_directory(
            args.csv_dir,
            out_dir=args.out_dir,
            out_format=args.out_format,
            naming=args.naming,
            add_success_events=args.with_success,
            success_delay_seconds=args.success_delay_seconds,
        )
    elif args.json:
        if not args.out_csv:
            raise SystemExit('--out-csv is required when using --json')
        reconstruct_csv(args.json, args.out_csv, ref_csv=args.ref_csv, fps=args.fps)


if __name__ == '__main__':
    main()
