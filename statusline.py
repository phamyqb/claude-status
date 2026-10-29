#!/usr/bin/env python3
"""Claude Code status line. Standard library only; no credentials or network."""
import json
from datetime import datetime
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import textwrap
import unicodedata

FIELDS = ('model', 'app', 'git', 'effort', 'context', 'current', 'week',
          'cost', 'duration', 'spend')


def load_options():
    try:
        path = Path(__file__).resolve().with_name('statusline-config.json')
        return obj(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, ValueError):
        return {}


def obj(value):
    return value if isinstance(value, dict) else {}


def clean(value, limit=42):
    # Strip terminal controls, newlines, bidi controls, and other format chars.
    text = ''.join(c for c in str(value or '')
                   if not unicodedata.category(c).startswith('C'))
    return text if len(text) <= limit else text[:max(0, limit - 3)] + '...'


def display_width(text):
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    return sum(0 if unicodedata.category(c) in ('Mn', 'Me') else
               2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1
               for c in text)


def clip(text, width):
    text = clean(text, 10000)
    if display_width(text) <= width:
        return text
    budget = max(0, width - 3)
    output = ''
    for c in text:
        if display_width(output + c) > budget:
            break
        output += c
    return output + '.' * min(3, width)


def number(value):
    if isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError, OverflowError):
        return None


def percent(value):
    n = number(value)
    return None if n is None else max(0, min(100, n))


def duration(seconds):
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes = rest // 60
    return f'{hours}h{minutes:02d}m' if hours else f'{minutes}m'


def reset_date(timestamp):
    try:
        dt = datetime.fromtimestamp(timestamp).astimezone()
        month = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')[dt.month - 1]
        return f'{dt.day:02d}-{month}-{dt.year:04d} {dt.hour:02d}:{dt.minute:02d}'
    except (ValueError, OverflowError, OSError):
        return '--'


def branch(directory):
    git = shutil.which('git')
    if not git or not directory:
        return ''
    try:
        # Read one ref only: no shell, hooks, git status, or repository writes.
        result = subprocess.run(
            [git, '--no-optional-locks', '-c', 'core.fsmonitor=false', '-C',
             directory, 'symbolic-ref', '--quiet', '--short', 'HEAD'],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=0.4, check=False)
        return clean(result.stdout.decode('utf-8', errors='replace').strip(), 28)
    except (OSError, subprocess.TimeoutExpired):
        return ''


def remaining_color(left):
    return 82 if left >= 50 else 226 if left >= 20 else 208 if left >= 10 else 196


def meter(label, used, cells=10):
    label = f'{label:<7}'
    if used is None:
        return (f'{label}  {"▫" * cells}  {"--":>3}% left', 245)
    left = 100 - used
    filled = max(0, min(cells, int(left * cells / 100 + 0.5)))
    return (f'{label}  {"▪" * filled}{"▫" * (cells - filled)}  {left:3.0f}% left',
            remaining_color(left))


def line(parts, width):
    colorful = 'NO_COLOR' not in os.environ and os.environ.get('TERM') != 'dumb'
    output = []
    remaining = width
    for index, (text, color) in enumerate(parts):
        separator = '  │  ' if index else ''
        if remaining <= len(separator):
            break
        output.append(('\033[38;5;240m' + separator + '\033[0m')
                      if colorful and separator else separator)
        remaining -= len(separator)
        text = clip(text, remaining)
        output.append(f'\033[38;5;{color}m{text}\033[0m' if colorful else text)
        remaining -= display_width(text)
    return ''.join(output)


def frame(lines):
    width = max(display_width(row) for row in lines)
    colorful = 'NO_COLOR' not in os.environ and os.environ.get('TERM') != 'dumb'
    def border(text):
        return f'\033[38;5;141m{text}\033[0m' if colorful else text
    result = [border('╭' + '─' * (width + 2) + '╮')]
    for row in lines:
        result.append(border('│') + ' ' + row +
                      ' ' * (width - display_width(row) + 1) + border('│'))
    result.append(border('╰' + '─' * (width + 2) + '╯'))
    return '\n'.join(result)


def render(data, now=None, options=None):
    now = time.time() if now is None else now
    data = obj(data)
    options = obj(options)
    show = options.get('show', list(FIELDS))
    show = set(x for x in show if isinstance(x, str) and x in FIELDS) if isinstance(show, list) else set(FIELDS)
    model = obj(data.get('model'))
    workspace = obj(data.get('workspace'))
    directory = workspace.get('current_dir') or data.get('cwd') or ''
    directory = directory if isinstance(directory, str) else ''
    top = []
    if 'model' in show:
        top.append((clean(model.get('display_name') or model.get('id') or 'Claude', 30), 213))
    if directory and 'app' in show:
        top.append((clean(Path(directory).name or directory, 28), 117))
    git_branch = branch(directory) if 'git' in show else ''
    if git_branch:
        top.append(('git:' + git_branch, 221))
    effort = clean(obj(data.get('effort')).get('level'), 10)
    if effort and 'effort' in show:
        top.append(('effort:' + effort, 183))

    context = percent(obj(data.get('context_window')).get('used_percentage'))
    bottom = [meter('Context', context)] if 'context' in show else []
    cost = obj(data.get('cost'))
    usd = number(cost.get('total_cost_usd'))
    if 'cost' in show and usd is not None and usd >= 0:
        bottom.append((f'API est. ${usd:.2f}', 153))
    ms = number(cost.get('total_duration_ms'))
    if 'duration' in show and ms is not None and ms >= 0:
        bottom.append((duration(ms / 1000), 245))

    quotas = []
    rates = obj(data.get('rate_limits'))
    for key, label in [('five_hour', 'Current'), ('seven_day', 'Week'),
                       ('spend_limit', 'spend')]:
        field = {'five_hour': 'current', 'seven_day': 'week', 'spend_limit': 'spend'}[key]
        if field not in show:
            continue
        window = obj(rates.get(key))
        pct = percent(window.get('used_percentage'))
        reset = number(window.get('resets_at'))
        if pct is None or (reset is not None and reset <= now):
            continue
        value, color = meter(label, pct)
        if reset is not None:
            value += f'  │  reset {duration(min(reset - now, 315360000)):>6} ({reset_date(reset)})'
        quotas.append((value, color))

    # Keep account quotas on their own line so the display stays readable.
    width = shutil.get_terminal_size(fallback=(120, 24)).columns
    width = max(8, min(width - 8, 232))
    lines = [line(parts, width) for parts in (top, bottom) if parts]
    for quota in quotas:
        # Each quota always starts on a new row, including on wide terminals.
        for chunk in textwrap.wrap(quota[0], width=width):
            lines.append(line([(chunk, quota[1])], width))
    return frame(lines or [line([('No selected fields available', 245)], width)])


def main():
    try:
        raw = sys.stdin.read(1048577)
        if len(raw) > 1048576:
            raise ValueError('oversized input')
        data = json.loads(raw)
        print(render(data, options=load_options()))
    except (ValueError, TypeError, OSError, RecursionError):
        print('Claude | status unavailable')


if __name__ == '__main__':
    main()
