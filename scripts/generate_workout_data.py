#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from workout_utils import compare_entry, rep_delta, weight_delta

ROOT = Path('/home/node/clawd')
LOG_PATH = ROOT / 'routines' / 'weight-log.md'
LEDGER_PATH = ROOT / 'routines' / 'workout-ledger.json'
OUT_PATH = ROOT / 'dashboard' / 'workout-data.js'

EXERCISE_KEY_MAP = {
    'Chest Press (Flat DBs)': 'chestPressFlatDB',
    'Lat Pulldown': 'latPulldown',
    'Unilateral Lat Pulldown': 'unilateralLatPulldown',
    'Delt Press Machine': 'deltPress',
    'Lat Pullover': 'latPullover',
    'Goblet Squat': 'gobletSquat',
    'Squat Machine': 'squatMachine',
    'Lateral Raise (Cable Behind)': 'lateralRaiseCableBehind',
    'Lateral Raise (Cable Front)': 'lateralRaiseCableFront',
    'Lateral Raise (Dumbbell)': 'lateralRaiseDB',
    'Lateral Raise (Cable)': 'lateralRaiseCable',
    'Cable Chest Fly (High to Low)': 'cableChestFly',
    'Bicep Curl (Barbell)': 'bicepCurl',
    'Bicep Curl (Cable Machine)': 'bicepCurlCable',
    'Incline Chest Press (Barbell/Smith)': 'inclineChestPress',
    'Upper Row (Cable)': 'upperRowCable',
    'Leg Curl (Machine)': 'legCurl',
    'Reverse Peck Deck': 'reversePecDeck',
    'Overhead Tricep Extension (Dumbbell)': 'overheadTricepDB',
    'Cable Triceps': 'cableTriceps',
    'Lat Row (Cable)': 'latRow',
    'Pec Deck': 'pecDeck',
    'Incline Dumbbell Fly': 'inclineDBFly',
    'Middle Cable Chest Press': 'middleCableChestPress',
    'Leg Extension (Machine)': 'legExtension',
    'Cable V-Bar Pushdown': 'cableVBar',
    'Hammer Curl (Dumbbells)': 'hammerCurls',
    'Dumbbell Preacher Curl': 'preacherCurl',
    'Preacher Curl (Barbell)': 'preacherCurlBarbell',
    'Upper Back Row (Machine)': 'upperBackRow',
    'Overhead Triceps (Cable)': 'overheadTricepsCable',
    'Single-Arm Cable Triceps': 'singleArmCableTriceps',
    'RDLs (Dumbbells)': 'rdls',
    'Bulgarian Split Squats': 'bulgarianSplitSquat',
    'Face Pull (Cable)': 'facePull',
}

EXERCISE_META = {
    'chestPressFlatDB': {'name': 'Chest Press (Flat DB)', 'group': 'Chest', 'splitDay': 1},
    'latPulldown': {'name': 'Lat Pulldown', 'group': 'Back', 'splitDay': 1},
    'unilateralLatPulldown': {'name': 'Unilateral Lat Pulldown', 'group': 'Back', 'splitDay': 1},
    'gobletSquat': {'name': 'Goblet Squat', 'group': 'Legs', 'splitDay': 1},
    'squatMachine': {'name': 'Squat Machine', 'group': 'Legs', 'splitDay': 1},
    'bulgarianSplitSquat': {'name': 'Bulgarian Split Squat', 'group': 'Legs', 'splitDay': 1},
    'lateralRaiseDB': {'name': 'Lateral Raise (DB)', 'group': 'Shoulders', 'splitDay': 1},
    'preacherCurl': {'name': 'Preacher Curl (DB)', 'group': 'Arms', 'splitDay': 1},
    'preacherCurlBarbell': {'name': 'Preacher Curl (Barbell)', 'group': 'Arms', 'splitDay': 1},
    'inclineChestPress': {'name': 'Incline Chest Press', 'group': 'Chest', 'splitDay': 2},
    'upperBackRow': {'name': 'Upper Back Row', 'group': 'Back', 'splitDay': 2},
    'upperRowCable': {'name': 'Upper Row (Cable)', 'group': 'Back', 'splitDay': 2},
    'legCurl': {'name': 'Leg Curl', 'group': 'Legs', 'splitDay': 2},
    'reversePecDeck': {'name': 'Reverse Pec Deck', 'group': 'Shoulders', 'splitDay': 2},
    'facePull': {'name': 'Face Pull', 'group': 'Shoulders', 'splitDay': 2},
    'overheadTricepsCable': {'name': 'OH Triceps (Cable)', 'group': 'Arms', 'splitDay': 2},
    'overheadTricepDB': {'name': 'OH Triceps (DB)', 'group': 'Arms', 'splitDay': 2},
    'singleArmCableTriceps': {'name': 'Single-Arm Cable Triceps', 'group': 'Arms', 'splitDay': 2},
    'pecDeck': {'name': 'Pec Deck', 'group': 'Chest', 'splitDay': 3},
    'middleCableChestPress': {'name': 'Middle Cable Chest Press', 'group': 'Chest', 'splitDay': 3},
    'latRow': {'name': 'Lat Row', 'group': 'Back', 'splitDay': 3},
    'legExtension': {'name': 'Leg Extension', 'group': 'Legs', 'splitDay': 3},
    'cableVBar': {'name': 'V-Bar Pushdown', 'group': 'Arms', 'splitDay': 3},
    'bicepCurl': {'name': 'Bicep Curl (Barbell)', 'group': 'Arms', 'splitDay': 3},
    'deltPress': {'name': 'Delt Press Machine', 'group': 'Shoulders', 'splitDay': 4},
    'latPullover': {'name': 'Lat Pullover', 'group': 'Back', 'splitDay': 4},
    'rdls': {'name': 'RDLs (DB)', 'group': 'Legs', 'splitDay': 4},
    'cableTriceps': {'name': 'Cable Triceps', 'group': 'Arms', 'splitDay': 4},
    'hammerCurls': {'name': 'Hammer Curls', 'group': 'Arms', 'splitDay': 4},
    'cableChestFly': {'name': 'Cable Chest Fly', 'group': 'Chest', 'splitDay': 1},
    'inclineDBFly': {'name': 'Incline Dumbbell Fly', 'group': 'Chest', 'splitDay': 3},
    'bicepCurlCable': {'name': 'Bicep Curl (Cable Machine)', 'group': 'Arms', 'splitDay': 3},
    'lateralRaiseCableBehind': {'name': 'Lateral Raise (Cable Behind)', 'group': 'Shoulders', 'splitDay': 1},
    'lateralRaiseCableFront': {'name': 'Lateral Raise (Cable Front)', 'group': 'Shoulders', 'splitDay': 1},
    'lateralRaiseCable': {'name': 'Lateral Raise (Cable)', 'group': 'Shoulders', 'splitDay': 1},
}

SPLIT = [
    {'day': 1, 'label': 'Chest / Back / Legs', 'keys': ['chestPressFlatDB', 'latPulldown', 'unilateralLatPulldown', 'squatMachine', 'gobletSquat', 'bulgarianSplitSquat', 'lateralRaiseDB', 'lateralRaiseCable', 'lateralRaiseCableBehind', 'lateralRaiseCableFront', 'preacherCurl', 'preacherCurlBarbell', 'cableChestFly']},
    {'day': 2, 'label': 'Incline / Row / Hamstring', 'keys': ['inclineChestPress', 'upperBackRow', 'upperRowCable', 'legCurl', 'reversePecDeck', 'facePull', 'overheadTricepsCable', 'overheadTricepDB', 'singleArmCableTriceps']},
    {'day': 3, 'label': 'Pec / Lat / Quads', 'keys': ['pecDeck', 'inclineDBFly', 'middleCableChestPress', 'latRow', 'legExtension', 'cableVBar', 'bicepCurl', 'bicepCurlCable']},
    {'day': 4, 'label': 'Shoulders / Pull / RDL', 'keys': ['deltPress', 'latPullover', 'rdls', 'cableTriceps', 'hammerCurls']},
]

GYMS = {
    'lower_street': {'label': 'Lower street gym'},
    'upper_gym': {'label': 'Upper gym'},
    'avenue_mall': {'label': 'Avenue Mall gym'},
    'unknown': {'label': 'Gym not specified'},
}


def parse_sets(reps_text: str):
    text = reps_text.strip()
    nums = [int(n) for n in re.findall(r'\d+', text)]
    if not nums:
        return []
    if ',' in text:
        return nums[:2]
    if '/' in text:
        # Historical log style: 9/10 means max set = 9 with target 10, not two explicit sets.
        # User rule: if second set isn't mentioned, assume it matched the first.
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


def parse_markdown_table_row(line: str):
    parts = [p.strip() for p in line.strip().strip('|').split('|')]
    return parts


def main():
    ledger = json.loads(LEDGER_PATH.read_text())
    sessions = ledger.get('sessions', [])
    exercises = {}
    cardio = []
    workout_days = set()

    for session in sessions:
        date = session.get('date')
        if not date:
            continue
        workout_days.add(date)
        for warmup in session.get('warmups', []):
            cardio.append({
                'date': date,
                'activity': warmup.get('activity', ''),
                'summary': warmup.get('summary', ''),
                'notes': warmup.get('notes', ''),
            })
        for ex in session.get('exercises', []):
            key = ex.get('key')
            if not key:
                continue
            exercises.setdefault(key, [])
            exercises[key].append({
                'date': date,
                'exercise': ex.get('sourceSection') or ex.get('name') or key,
                'weightText': ex.get('weightText', ''),
                'weightValue': ex.get('weightValue'),
                'unit': ex.get('unit', ''),
                'repsText': ex.get('repsText', ''),
                'sets': ex.get('sets', []),
                'bestSet': ex.get('bestSet'),
                'note': ex.get('note', ''),
                'gymId': ex.get('gymId', 'unknown'),
            })

    exercises = {k: v for k, v in exercises.items() if v}
    last_update = max(workout_days) if workout_days else None

    # infer last split day from the most recent workout date,
    # using the dominant split bucket for that date (handles mixed/ad-hoc sessions better)
    split_counts_by_date = {}
    for key, entries in exercises.items():
        split_day = EXERCISE_META.get(key, {}).get('splitDay')
        if not split_day:
            continue
        for entry in entries:
            split_counts_by_date.setdefault(entry['date'], {})
            split_counts_by_date[entry['date']][split_day] = split_counts_by_date[entry['date']].get(split_day, 0) + 1
    if split_counts_by_date:
        latest_date = max(split_counts_by_date)
        counts = split_counts_by_date[latest_date]
        last_split_day = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    else:
        last_split_day = 4
    next_split_day = 1 if last_split_day == 4 else last_split_day + 1

    recent_session = []
    if last_update:
        for key, entries in exercises.items():
            if entries[-1]['date'] != last_update:
                continue
            current = entries[-1]
            prev = compare_entry(entries, len(entries) - 1)
            meta = EXERCISE_META.get(key, {})
            recent_session.append({
                'key': key,
                'name': meta.get('name', key),
                'group': meta.get('group'),
                'splitDay': meta.get('splitDay'),
                'current': current,
                'previous': prev,
                'weightDelta': weight_delta(current, prev),
                'repDelta': rep_delta(current, prev),
            })
        recent_session.sort(key=lambda x: ((x.get('splitDay') if x.get('splitDay') is not None else 99), x.get('name', '')))

    data = {
        'generatedAt': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        'lastUpdate': last_update,
        'split': SPLIT,
        'gyms': GYMS,
        'exerciseMeta': EXERCISE_META,
        'exercises': exercises,
        'cardio': sorted(cardio, key=lambda x: x['date'], reverse=True),
        'workoutDays': sorted(workout_days),
        'lastSplitDay': last_split_day,
        'nextSplitDay': next_split_day,
        'recentSession': recent_session,
        'entryRules': ledger.get('entryRules', {
            'defaultSetCount': 2,
            'assumeSecondSetSameIfMissing': True,
            'compareWithinSameGymFirst': True,
            'keepExerciseNotes': True,
        }),
        'ledgerBacked': True,
        'sessionCount': len(sessions),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text('window.WORKOUT_DATA = ' + json.dumps(data, indent=2) + ';\n')
    print(f'Wrote {OUT_PATH}')


if __name__ == '__main__':
    main()
