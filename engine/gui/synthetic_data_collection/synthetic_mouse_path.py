import numpy as np
from scipy.special import comb
import random
from typing import List, Dict, Any


def bernstein_poly(i, n, t):
    return comb(n, i) * (t**(i)) * ((1-t)**(n-i))

def bezier_curve(points, num_points=1000):
    n = len(points) - 1
    t = np.linspace(0, 1, num_points)
    curve = np.zeros((num_points, 2))
    for i, point in enumerate(points):
        curve += np.outer(bernstein_poly(i, n, t), point)
    return curve

def add_noise(curve, noise_level=0.1):
    noise = np.random.normal(0, noise_level, curve.shape)
    return curve + noise

def generate_control_points(num_points, screen_width, screen_height):
    """Generate control points with some points near or at the boundaries"""
    points = []
    for _ in range(num_points):
        if random.random() < 0.3:  # 30% chance of boundary point
            # Generate a point on or very close to a boundary
            if random.random() < 0.5:  # horizontal boundary
                x = random.randint(0, screen_width)
                y = random.choice([0, screen_height - 1]) if random.random() < 0.5 else random.randint(0, screen_height)
            else:  # vertical boundary
                x = random.choice([0, screen_width - 1]) if random.random() < 0.5 else random.randint(0, screen_width)
                y = random.randint(0, screen_height)
        else:
            # Regular point
            x = random.randint(0, screen_width)
            y = random.randint(0, screen_height)
        points.append((x, y))
    return points

# XDOTOOL compatible keys only
XDOTOOL_KEYS = [
    # Basic keys
    'Return', 'Tab', 'space', 'BackSpace', 'Delete', 'Escape', 'Insert',
    'Home', 'End', 'Prior', 'Next',  # pageup/pagedown
    
    # Arrow keys
    'Up', 'Down', 'Left', 'Right',
    
    # Function keys
    'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
    
    # Modifier keys
    'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Shift_L', 'Shift_R',
    
    # Special keys
    'Caps_Lock', 'Num_Lock', 'Scroll_Lock', 'Print', 'Pause', 'Break',
    
    # Number pad keys
    'KP_0', 'KP_1', 'KP_2', 'KP_3', 'KP_4', 'KP_5', 'KP_6', 'KP_7', 'KP_8', 'KP_9',
    'KP_Decimal', 'KP_Divide', 'KP_Multiply', 'KP_Subtract', 'KP_Add',
    
    # Media keys (some may not be supported by xdotool)
    'XF86AudioLowerVolume', 'XF86AudioRaiseVolume', 'XF86AudioMute',
    'XF86AudioPlay', 'XF86AudioNext', 'XF86AudioPrev', 'XF86AudioStop',
    
    # Other keys
    'Menu', 'Clear', 'Help', 'Select', 'Separator', 'Execute',
    'Mode_switch', 'XF86Sleep',
    
    # Windows keys
    'Super_L', 'Super_R',
    
    # Control characters
    '\t', ' ',
]

# Keys that xdotool doesn't support (filter these out)
UNSUPPORTED_XDOTOOL_KEYS = {
    '.', ';', '^', '_', '#', '~', '*', ')', '}', '&', '`', '?', '[', '/', '$', 
    '-', '{', '|', '\n', '>', ',', '@', '<', 'Convert', 'Accept', 'Final', 'Nonconvert'
}

# Printable characters for typing (filtered for xdotool compatibility)
PRINTABLE_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

def generate_human_like_trajectory(screen_width, screen_height,
                                   duration,  # Duration in seconds
                                   fps,  # Match recording FPS
                                   num_clicks,
                                   num_control_points=25, 
                                   double_click_prob=0.3,
                                   right_click_prob=0.05,
                                   max_key_event_prob=0.5):  # Probability of double click
    # Calculate number of points based on duration and fps
    num_points = int(duration * fps)
    HUMAN = random.random() > 0.5
    key_event_prob = random.random() * max_key_event_prob
    
    if HUMAN:
        # Generate more control points for more complex paths
        control_points = generate_control_points(num_control_points + random.randint(0, 10), 
                                              screen_width, screen_height)
        
        # Add some extra control points at the start and end to ensure full range
        if random.random() < 0.3:  # 30% chance of boundary-to-boundary movement
            # Add boundary points at start and end
            start_point = (random.choice([0, screen_width - 1]), random.randint(0, screen_height))
            end_point = (random.choice([0, screen_width - 1]), random.randint(0, screen_height))
            control_points = [start_point] + control_points + [end_point]
        
        curve = bezier_curve(control_points, num_points)
        noisy_curve = add_noise(curve, noise_level=0.15)  # Slightly increased noise
        trajectory = np.clip(noisy_curve, 0, [screen_width - 1, screen_height - 1]).astype(int)
    else: # just random points within the screen
        x = np.random.randint(0, screen_width, num_points)
        y = np.random.randint(0, screen_height, num_points)
        trajectory = np.vstack((x, y)).T
    
    # Generate fixed number of clicks at random points
    buffer = 0
    click_indices = np.random.choice(
        range(buffer, num_points - buffer), 
        size=num_clicks, 
        replace=False
    )
    click_indices.sort()  # Sort to maintain temporal order
    
    # Create click array with double clicks
    clicks = np.zeros(len(trajectory), dtype=bool)
    
    for idx in click_indices:
        if random.random() < double_click_prob and idx < len(trajectory) - 8:  # More room for second click
            # First click
            clicks[idx] = True
            
            # Gap calculation: 
            # At 24fps: 3 frames ≈ 125ms, 6 frames ≈ 250ms
            gap = random.randint(1, 6)  # Between 125ms and 250ms
            
            # Add small random movement between clicks
            #if not HUMAN:
            original_pos = trajectory[idx].copy()
            for j in range(1, gap + 1):
                jitter = np.random.normal(0, 1, 2)  # 1 pixel standard deviation for more stability
                new_pos = original_pos + jitter
                new_pos = np.clip(new_pos, 0, [screen_width - 1, screen_height - 1])
                trajectory[idx + j] = new_pos.astype(int)
        
            # Second click
            clicks[idx + gap] = True
        else:
            clicks[idx] = True  # Single click

    # Generate keyboard events using xdotool-compatible keys
    keyboard_events = [set() for _ in trajectory]
    active_keys = set()
    up_keys = set()
    right_clicks = np.zeros(len(trajectory), dtype=bool)
    
    for i in range(len(trajectory)):
        if random.random() < right_click_prob:
            right_clicks[i] = True
            
        # Handle key up events for active keys
        to_remove = []
        for key in active_keys:
            if random.random() < 0.8: # key up
                keyboard_events[i].add(('keyup', key))
                up_keys.add(key)
                to_remove.append(key)
        for key in to_remove:
            active_keys.remove(key)
            
        # Generate new key events
        if random.random() < key_event_prob:
            while True:
                # Choose between special keys and printable characters
                if random.random() < 0.3:  # 30% chance for special keys
                    key = random.choice(XDOTOOL_KEYS)
                else:  # 70% chance for printable characters
                    key = random.choice(PRINTABLE_CHARS)
                    
                # Filter out unsupported keys
                if key in UNSUPPORTED_XDOTOOL_KEYS:
                    continue
                    
                if key not in active_keys and key not in up_keys:
                    keyboard_events[i].add(('keydown', key))
                    active_keys.add(key)
                if random.random() < 0.8:
                    break

    events = []
    for pos, left, right, key_events in zip(trajectory, clicks, right_clicks, keyboard_events):
        events.append({
            'pos': pos,
            'left_click': left,
            'right_click': right,
            'key_events': key_events
        })

    return events


class SyntheticToActionsConverter:
    """Convert synthetic trajectory data to computer_use_agent actions."""
    
    def __init__(self, fps: int = 15):
        self.fps = fps
        self.frame_interval = 1.0 / fps
        
    def convert_trajectory_to_actions(self, trajectory_data: List[Dict]) -> List[Dict]:
        """Convert synthetic trajectory data to high-level actions."""
        actions = []
        
        # Track state for action detection
        last_pos = None
        last_left_click = False
        last_right_click = False
        active_keys = set()
        
        # Detect double clicks (two left clicks within 300ms)
        double_click_frames = self._detect_double_clicks(trajectory_data)
        
        for i, frame in enumerate(trajectory_data):
            pos = frame['pos']
            left_click = frame['left_click']
            right_click = frame['right_click']
            key_events = frame['key_events']
            
            # Handle mouse movement
            if last_pos is not None and (pos[0] != last_pos[0] or pos[1] != last_pos[1]):
                # Only record significant movements (more than 5 pixels)
                distance = ((pos[0] - last_pos[0])**2 + (pos[1] - last_pos[1])**2)**0.5
                if distance > 5:
                    actions.append({
                        'action': 'mouse_move',
                        'coordinate': [int(pos[0]), int(pos[1])],
                        'timestamp': i * self.frame_interval
                    })
            
            # Handle clicks
            if left_click and not last_left_click:
                if i in double_click_frames:
                    # This is part of a double click, skip individual clicks
                    pass
                else:
                    actions.append({
                        'action': 'left_click',
                        'coordinate': [int(pos[0]), int(pos[1])],
                        'timestamp': i * self.frame_interval
                    })
            
            if right_click and not last_right_click:
                actions.append({
                    'action': 'right_click',
                    'coordinate': [int(pos[0]), int(pos[1])],
                    'timestamp': i * self.frame_interval
                })
            
            # Handle double clicks
            if i in double_click_frames:
                actions.append({
                    'action': 'double_click',
                    'coordinate': [int(pos[0]), int(pos[1])],
                    'timestamp': i * self.frame_interval
                })
            
            # Handle keyboard events
            for event_type, key in key_events:
                if event_type == 'keydown' and key not in active_keys:
                    active_keys.add(key)
                    
                    # Convert to type action for printable characters
                    if len(key) == 1 and key.isprintable():
                        actions.append({
                            'action': 'type',
                            'text': key,
                            'timestamp': i * self.frame_interval
                        })
                    else:
                        # Special keys
                        actions.append({
                            'action': 'key',
                            'text': key,
                            'timestamp': i * self.frame_interval
                        })
                elif event_type == 'keyup' and key in active_keys:
                    active_keys.remove(key)
            
            # Update state
            last_pos = pos
            last_left_click = left_click
            last_right_click = right_click
        
        return actions
    
    def _detect_double_clicks(self, trajectory_data: List[Dict]) -> set:
        """Detect double click frames (two left clicks within 300ms)."""
        double_click_frames = set()
        left_click_frames = []
        
        # Find all left click frames
        for i, frame in enumerate(trajectory_data):
            if frame['left_click']:
                left_click_frames.append(i)
        
        # Detect double clicks
        for i in range(len(left_click_frames) - 1):
            frame1 = left_click_frames[i]
            frame2 = left_click_frames[i + 1]
            time_diff = (frame2 - frame1) * self.frame_interval
            
            if time_diff <= 0.3:  # 300ms threshold
                # Mark the second click as part of double click
                double_click_frames.add(frame2)
        
        return double_click_frames


def generate_multiple_trajectories(num_trajectories, screen_width, screen_height, duration, fps):
    """Generate multiple trajectories with both frame data and converted actions."""
    trajectories = []
    actions_list = []
    
    converter = SyntheticToActionsConverter(fps=fps)
    
    for i in range(num_trajectories):
        # Randomly choose number of clicks for this trajectory
        num_clicks = np.random.randint(0, int(0.4*duration*fps))  # Random number of clicks proportional to duration
        trajectory = generate_human_like_trajectory(
            screen_width, screen_height,
            duration=duration,
            num_clicks=num_clicks,
            fps=fps
        )
        
        # Convert to actions
        actions = converter.convert_trajectory_to_actions(trajectory)
        
        trajectories.append(trajectory)
        actions_list.append(actions)
        
        print(f"Generated trajectory {i+1}/{num_trajectories}: {len(trajectory)} frames -> {len(actions)} actions")
    
    return trajectories, actions_list
