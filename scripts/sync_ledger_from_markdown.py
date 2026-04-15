#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path('/home/node/clawd')
LOG_PATH = ROOT / 'routines' / 'weight-log.md'
LEDGER_PATH = ROOT / 'routines' / 'workout-ledger.json'

EXERCISE_ALIASES = {
    'Chest Press (Flat DBs)': ('chestPressFlatDB', 'Chest Press (Flat DB)'),
    'Lat Pulldown': ('latPulldown', 'Lat Pulldown'),
    'Unilateral Lat Pulldown': ('unilateralLatPulldown', 'Unilateral Lat Pulldown'),
    'Delt Press Machine': ('deltPress', 'Delt Press Machine'),
    'Lat Pullover': ('latPullover', 'Lat Pullover'),
    'Goblet Squat': ('gobletSquat', 'Goblet Squat'),
    'Squat Machine': ('squatMachine', 'Squat Machine'),
    'Lateral Raise (Cable Behind)': ('lateralRaiseCableBehind', 'Lateral Raise (Cable Behind)'),
    'Lateral Raise (Cable Front)': ('lateralRaiseCableFront', 'Lateral Raise (Cable Front)'),
    'Lateral Raise (Dumbbell)': ('lateralRaiseDB', 'Lateral Raise (DB)'),
    'Lateral Raise (Cable)': ('lateralRaiseCable', 'Lateral Raise (Cable)'),
    'Cable Chest Fly (High to Low)': ('cableChestFly', 'Cable Chest Fly'),
    'Bicep Curl (Barbell)': ('bicepCurl', 'Bicep Curl (Barbell)'),
    'Incline Chest Press (Barbell/Smith)': ('inclineChestPress', 'Incline Chest Press'),
    'Upper Row (Cable)': ('upperRowCable', 'Upper Row (Cable)'),
    'Leg Curl (Machine)': ('legCurl', 'Leg Curl'),
    'Reverse Peck Deck': ('reversePecDeck', 'Reverse Pec Deck'),
    'Overhead Tricep Extension (Dumbbell)': ('overheadTricepDB', 'OH Triceps (DB)'),
    'Cable Triceps': ('cableTriceps', 'Cable Triceps'),
    'Lat Row (Cable)': ('latRow', 'Lat Row'),
    'Pec Deck': ('pecDeck', 'Pec Deck'),
    'Middle Cable Chest Press': ('middleCableChestPress', 'Middle Cable Chest Press'),
    'Leg Extension (Machine)': ('legExtension', 'Leg Extension'),
    'Cable V-Bar Pushdown': ('cableVBar', 'V-Bar Pushdown'),
    'Hammer Curl (Dumbbells)': ('hammerCurls', 'Hammer Curls'),
    'Dumbbell Preacher Curl': ('preacherCurl', 'Preacher Curl (DB)'),
    'Preacher Curl (Barbell)': ('preacherCurlBarbell', 'Preacher Curl (Barbell)'),
    'Upper Back Row (Machine)': ('upperBackRow', 'Upper Back Row'),
    'Overhead Triceps (Cable)': ('overheadTricepsCable', 'OH Triceps (Cable)'),
    'RDLs (Dumbbells)': ('rdls', 'RDLs (DB)'),
    'Bulgarian Split Squats': ('bulgarianSplitSquat', 'Bulgarian Split Squat'),
    'Face Pull (Cable)': ('facePull', 'Face Pull')
}


def parse_sets(text: str):
    nums = [int(n) for n in re.findall(r'\d+', text)]
    if not nums:
        return []
    if ',' in text:
        return nums[:2]
    if '/' in text:
        return [nums[0], nums[0]]
    return [nums[0], nums[0]]


def infer_unit(weight_text: str):
    lower = weight_text.lower()
    if 'lbs' in lower or 'lb' in lower:
        return 'lbs'
    if 'kg' in lower:
        return 'kg'
    return ''


def first_number(text: str):
    m = re.search(r'\d+(?:\.\d+)?', text)
    return float(m.group(0)) if m else None


def infer_gym(date_str: str, note: str):
    lower = note.lower()
    if 'avenue mall' in lower:
        return 'avenue_mall'
    if 'upper gym' in lower or 'new gym' in lower:
        return 'upper_gym'
    if 'lower street gym' in lower or 'previous gym' in lower:
        return 'lower_street'
    if date_str < '2026-04-10':
        return 'lower_street'
    return 'unknown'


def table_row(line: str):
    return [p.strip() for p in line.strip().strip('|').split('|')]


def build_sessions():
    lines = LOG_PATH.read_text().splitlines()
    current_section = None
    in_warmup = False
    sessions = defaultdict(lambda: {"date": None, "warmups": [], "exercises": []})

    for line in lines:
        if line.startswith('## '):
            title = line[3:].strip()
            in_warmup = title == 'Warmup'
            current_section = None if in_warmup else title
            continue

        if not line.startswith('| 2026-'):
            continue

        row = table_row(line)
        if in_warmup:
            date, activity, duration, notes = row[:4]
            sessions[date]['date'] = date
            sessions[date]['warmups'].append({
                'activity': activity,
                'summary': duration,
                'notes': notes,
            })
            continue

        if not current_section or current_section not in EXERCISE_ALIASES:
            continue

        date, weight_text, reps_text, diff = row[:4]
        key, name = EXERCISE_ALIASES[current_section]
        note = '' if diff == '—' else diff
        sessions[date]['date'] = date
        sessions[date]['exercises'].append({
            'key': key,
            'name': name,
            'sourceSection': current_section,
            'weightText': weight_text,
            'weightValue': first_number(weight_text),
            'unit': infer_unit(weight_text),
            'repsText': reps_text,
            'sets': parse_sets(reps_text),
            'bestSet': max(parse_sets(reps_text)) if parse_sets(reps_text) else None,
            'gymId': infer_gym(date, note),
            'note': note,
        })

    return [sessions[d] for d in sorted(sessions)]


def main():
    ledger = json.loads(LEDGER_PATH.read_text())
    ledger['sessions'] = build_sessions()
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2) + '\n')
    print(f'Updated {LEDGER_PATH}')


if __name__ == '__main__':
    main()
