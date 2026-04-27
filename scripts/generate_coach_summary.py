#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path

from workout_utils import gym_label, load_workout_data

OUT_PATH = Path('/home/node/clawd/dashboard/coach-summary.txt')


def fmt_num(value):
    if value is None:
        return None
    return str(int(value)) if float(value).is_integer() else str(value)


def format_weight_delta(item):
    delta = item.get('weightDelta')
    unit = item['current'].get('unit', '')
    if delta is None or delta == 0:
        return None
    sign = '+' if delta > 0 else ''
    return f'{sign}{fmt_num(delta)}{unit}'


def format_rep_delta(item):
    delta = item.get('repDelta')
    if delta is None or delta == 0:
        return None
    sign = '+' if delta > 0 else ''
    return f'{sign}{delta} rep' + ('' if abs(delta) == 1 else 's')


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


def status_icon(label):
    return {
        'improved': '↗',
        'same': '→',
        'needs work': '↘',
        'gym change': '⇄',
        'new baseline': '★',
    }.get(label, '•')


def compact_entry(entry):
    return f"{entry['weightText']} x {entry['repsText']}"


def main():
    data = load_workout_data()
    session = data.get('recentSession', [])
    date = data.get('lastUpdate') or 'unknown date'
    if not session:
        OUT_PATH.write_text(f'No recent session found for {date}.\n')
        return

    split_day = session[0].get('splitDay') or '?'
    gym = gym_label(data, session[0]['current'].get('gymId'))
    lines = [f"🏋️ Kinan | Day {split_day} | {date}", f"Gym: {gym}", '']
    summary = Counter()
    notes = []

    for item in session:
        cur = item['current']
        prev = item.get('previous')
        label = classify(item)
        summary[label] += 1
        parts = [p for p in [format_weight_delta(item), format_rep_delta(item)] if p]
        delta_text = ' | '.join(parts) if parts else label
        prev_text = compact_entry(prev) if prev else 'new baseline'
        cur_text = compact_entry(cur)
        lines.append(f"{status_icon(label)} {item['name']}")
        lines.append(f"  prev: {prev_text}")
        lines.append(f"  now : {cur_text}")
        lines.append(f"  diff: {delta_text}")
        if cur.get('note'):
            notes.append(f"- {item['name']}: {cur['note']}")
        lines.append('')

    lines.append('Summary')
    lines.append(
        f"improved {summary['improved']} | same {summary['same']} | "
        f"need work {summary['needs work']} | gym change {summary['gym change']} | baseline {summary['new baseline']}"
    )
    if notes:
        lines.append('')
        lines.append('Notes')
        lines.extend(notes)

    OUT_PATH.write_text('\n'.join(lines).rstrip() + '\n')
    print(f'Wrote {OUT_PATH}')


if __name__ == '__main__':
    main()
