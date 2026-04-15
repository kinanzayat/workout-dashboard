#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path('/home/node/clawd')
LEDGER_PATH = ROOT / 'routines' / 'workout-ledger.json'
DASHBOARD_DIR = ROOT / 'dashboard'

EXERCISE_PATTERNS = [
    (r'flat\s+(?:chess|chest|db|dumbbell).*press|chest\s+press.*flat|flat\s+chest', 'chestPressFlatDB', 'Chest Press (Flat DB)'),
    (r'lat\s+pullover|pull\s*over', 'latPullover', 'Lat Pullover'),
    (r'lat\s+pull\s*down|lat\s+pulldown', 'latPulldown', 'Lat Pulldown'),
    (r'uni(?:lateral)?\s+lat\s+pull\s*down', 'unilateralLatPulldown', 'Unilateral Lat Pulldown'),
    (r'squat\s+machine|squats?', 'squatMachine', 'Squat Machine'),
    (r'lateral\s+raises?|lat\s+raises?', 'lateralRaiseDB', 'Lateral Raise (DB)'),
    (r'preacher\s+curl', 'preacherCurl', 'Preacher Curl (DB)'),
    (r'lat\s+row', 'latRow', 'Lat Row'),
    (r'pec\s+deck', 'pecDeck', 'Pec Deck'),
    (r'leg\s+extension', 'legExtension', 'Leg Extension'),
    (r'leg\s+curl', 'legCurl', 'Leg Curl'),
    (r'incline\s+chest', 'inclineChestPress', 'Incline Chest Press'),
    (r'delt\s+press|shoulder\s+press', 'deltPress', 'Delt Press Machine'),
    (r'rdl', 'rdls', 'RDLs (DB)'),
    (r'hammer\s+curl', 'hammerCurls', 'Hammer Curls'),
    (r'cable\s+triceps?|triceps?', 'cableTriceps', 'Cable Triceps'),
]

GYM_PATTERNS = {
    'upper_gym': r'\bupper\s+gym\b|\bnew\s+gym\b',
    'lower_street': r'\blower\s+street\b|\bold\s+gym\b|\bprevious\s+gym\b',
    'avenue_mall': r'\bavenue\s+mall\b',
}


def load_ledger():
    return json.loads(LEDGER_PATH.read_text())


def save_ledger(ledger):
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2) + '\n')


def infer_gym(text: str):
    lower = text.lower()
    for gym_id, pattern in GYM_PATTERNS.items():
        if re.search(pattern, lower):
            return gym_id
    return 'unknown'


def infer_exercise(chunk: str):
    lower = chunk.lower()
    for pattern, key, name in EXERCISE_PATTERNS:
        if re.search(pattern, lower):
            return key, name
    return None, None


def parse_weight(chunk: str):
    lower = chunk.lower()
    nums = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', chunk)]
    if not nums:
        return None, '', ''
    weight = nums[0]
    unit = 'kg' if 'kg' in lower else ('lbs' if 'lb' in lower else '')
    if 'each hand' in lower or 'each side' in lower:
        suffix = ' each hand' if 'hand' in lower else ' each side'
    elif '/side' in lower:
        suffix = '/side'
    elif 'max weight' in lower or 'max stack' in lower:
        suffix = ''
    else:
        suffix = ''
    if unit:
        weight_text = f'{int(weight) if weight.is_integer() else weight} {unit}{suffix}'
    else:
        weight_text = f'{int(weight) if weight.is_integer() else weight}{suffix}'
    return weight, unit, weight_text


def parse_sets(chunk: str):
    lower = chunk.lower()
    named = re.search(r'(?:first\s+(?:set|rep)?\s*)(\d{1,2}).*?(?:second\s+(?:set|rep)?\s*)(\d{1,2})', lower)
    if named:
        a, b = int(named.group(1)), int(named.group(2))
        return [a, b], f'{a},{b}'
    pair = re.search(r'(\d{1,2})\s*[,،/]\s*(\d{1,2})', chunk)
    if pair:
        a, b = int(pair.group(1)), int(pair.group(2))
        return [a, b], f'{a},{b}'
    max_rep = re.search(r'(?:max\s+rep|max\s+reps|reps?)\D*(\d{1,2})\b', lower)
    if max_rep:
        r = int(max_rep.group(1))
        return [r, r], f'{r}/10'
    tail = re.search(r'\b(\d{1,2})\b\s*$', lower)
    if tail:
        r = int(tail.group(1))
        return [r, r], f'{r}/10'
    return [10, 10], '10/10'


def parse_note(chunk: str, consumed_patterns: list[str]):
    note = chunk
    for pat in consumed_patterns:
        note = re.sub(pat, ' ', note, flags=re.I)
    note = re.sub(r'\b(first|second|set|rep|on each side|on each hand|each side|each hand|max weight|max rep|max reps)\b', ' ', note, flags=re.I)
    note = re.sub(r'\s+', ' ', note).strip(' ,.-')
    return note


def upsert_session(ledger, date: str):
    for session in ledger['sessions']:
        if session.get('date') == date:
            return session
    session = {'date': date, 'warmups': [], 'exercises': []}
    ledger['sessions'].append(session)
    ledger['sessions'].sort(key=lambda s: s['date'])
    return session


def upsert_exercise(session, exercise):
    for idx, existing in enumerate(session['exercises']):
        if existing.get('key') == exercise['key']:
            session['exercises'][idx] = exercise
            return 'updated'
    session['exercises'].append(exercise)
    return 'added'


def run_generators():
    import subprocess
    subprocess.run(['python3', str(DASHBOARD_DIR / 'scripts' / 'generate_workout_data.py')], check=True)
    subprocess.run(['python3', str(DASHBOARD_DIR / 'scripts' / 'generate_coach_summary.py')], check=True)


def main():
    ap = argparse.ArgumentParser(description='Parse WhatsApp-style workout entry text into workout ledger.')
    ap.add_argument('--date', required=True, help='Session date YYYY-MM-DD')
    ap.add_argument('--text', required=True, help='Raw workout message text')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    ledger = load_ledger()
    session = upsert_session(ledger, args.date)
    gym_id = infer_gym(args.text)

    raw_chunks = [c.strip() for c in re.split(r'\n+|\s*;\s*|\s*\.\s*(?=[A-Z0-9a-z])', args.text) if c.strip()]
    chunks = []
    for chunk in raw_chunks:
        lower = chunk.lower()
        if chunks and (lower.startswith('max rep') or lower.startswith('max reps') or lower.startswith('note ') or lower.startswith('felt ') or lower.startswith('machine ')):
            chunks[-1] += '. ' + chunk
        else:
            chunks.append(chunk)

    results = []
    for chunk in chunks:
        key, name = infer_exercise(chunk)
        if not key:
            continue
        weight_value, unit, weight_text = parse_weight(chunk)
        sets, reps_text = parse_sets(chunk)
        consumed = []
        for pattern, p_key, _ in EXERCISE_PATTERNS:
            if p_key == key:
                consumed.append(pattern)
        consumed += [
            r'\d+(?:\.\d+)?\s*(?:kg|kgs|lb|lbs)?(?:\s*(?:each hand|each side|on each hand|on each side|/side))?',
            r'(\d{1,2})\s*[,،/]\s*(\d{1,2})',
            r'(?:first\s+(?:set|rep)\s*)\d{1,2}',
            r'(?:second\s+(?:set|rep)\s*)\d{1,2}',
            r'(?:max\s+rep|max\s+reps|reps?)\D*\d{1,2}',
            *GYM_PATTERNS.values()
        ]
        note = parse_note(chunk, consumed)
        exercise = {
            'key': key,
            'name': name,
            'sourceSection': name,
            'weightText': weight_text,
            'weightValue': weight_value,
            'unit': unit,
            'repsText': reps_text,
            'sets': sets,
            'bestSet': max(sets) if sets else None,
            'gymId': gym_id,
            'note': note,
        }
        action = upsert_exercise(session, exercise)
        results.append({'action': action, 'exercise': exercise})

    if not args.dry_run:
        save_ledger(ledger)
        run_generators()

    print(json.dumps({'date': args.date, 'gymId': gym_id, 'results': results}, indent=2))


if __name__ == '__main__':
    main()
