#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path

from workout_utils import gym_label, load_workout_data

OUT_PATH = Path('/home/node/clawd/dashboard/coach-summary.txt')


def format_weight_delta(item):
    delta = item.get('weightDelta')
    unit = item['current'].get('unit', '')
    if delta is None or delta == 0:
        return None
    sign = '+' if delta > 0 else ''
    return f'{sign}{delta}{unit}'


def format_rep_delta(item):
    delta = item.get('repDelta')
    if delta is None or delta == 0:
        return None
    sign = '+' if delta > 0 else ''
    return f'{sign}{delta} reps'


def classify(item):
    wd = item.get('weightDelta')
    rd = item.get('repDelta')
    cur = item['current']
    prev = item.get('previous')
    if prev is None:
        return 'new baseline'
    if cur.get('gymId') != 'unknown' and prev.get('gymId') != 'unknown' and cur.get('gymId') != prev.get('gymId'):
        return 'gym change'
    if (wd or 0) > 0 or (rd or 0) > 0:
        return 'improved'
    if (wd or 0) == 0 and (rd or 0) == 0:
        return 'same'
    return 'needs work'


def main():
    data = load_workout_data()
    session = data.get('recentSession', [])
    date = data.get('lastUpdate') or 'unknown date'
    if not session:
        OUT_PATH.write_text(f'No recent session found for {date}.\n')
        return

    split_day = session[0].get('splitDay') or '?'
    lines = [f"🏋️ Kinan's Day {split_day} — {date}", '']
    summary = Counter()

    for item in session:
        cur = item['current']
        prev = item.get('previous')
        prev_text = f"{prev['weightText']}/{prev['repsText']}" if prev else '—'
        today_text = f"{cur['weightText']}/{cur['repsText']}"
        parts = [p for p in [format_weight_delta(item), format_rep_delta(item)] if p]
        label = classify(item)
        summary[label] += 1
        progress = ', '.join(parts) if parts else label
        gym = gym_label(data, cur.get('gymId'))
        lines.append(f"• {item['name']}: {prev_text} → {today_text} ({progress})")
        lines.append(f"  gym: {gym}")
        if cur.get('note'):
            lines.append(f"  note: {cur['note']}")

    lines.append('')
    lines.append(
        'Summary: '
        + ', '.join([
            f"{summary['improved']} improved",
            f"{summary['same']} same",
            f"{summary['needs work']} need work",
            f"{summary['gym change']} gym-change comparisons",
            f"{summary['new baseline']} new baselines",
        ])
    )
    OUT_PATH.write_text('\n'.join(lines) + '\n')
    print(f'Wrote {OUT_PATH}')


if __name__ == '__main__':
    main()
