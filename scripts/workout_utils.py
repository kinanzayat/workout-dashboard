from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path('/home/node/clawd')
DASHBOARD_DIR = ROOT / 'dashboard'
DATA_PATH = DASHBOARD_DIR / 'workout-data.js'


def load_workout_data(path: Path = DATA_PATH):
    text = path.read_text()
    payload = re.sub(r'^window\.WORKOUT_DATA = ', '', text)
    payload = re.sub(r';\s*$', '', payload)
    return json.loads(payload)


def compare_entry(entries, idx):
    current = entries[idx]
    for i in range(idx - 1, -1, -1):
        prev = entries[i]
        if prev.get('gymId') == current.get('gymId') and current.get('gymId') != 'unknown':
            return prev
    return entries[idx - 1] if idx > 0 else None


def weight_delta(current, prev):
    if not prev:
        return None
    cw, pw = current.get('weightValue'), prev.get('weightValue')
    if cw is None or pw is None:
        return None
    return round(cw - pw, 2)


def rep_delta(current, prev):
    if not prev:
        return None
    return current.get('bestSet', 0) - prev.get('bestSet', 0)


def gym_label(data, gym_id):
    return data.get('gyms', {}).get(gym_id, {}).get('label', gym_id or 'Unknown gym')
