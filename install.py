#!/usr/bin/env python3
"""Install into the current user's Claude config; back up files before changes."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile

FIELDS = ('model', 'app', 'git', 'effort', 'context', 'current', 'week',
          'cost', 'duration', 'spend')

LABELS = {
    'model': 'Model name', 'app': 'Current project / app folder',
    'git': 'Git branch', 'effort': 'Reasoning effort',
    'context': 'Context remaining', 'current': 'Current quota (5 hours)',
    'week': 'Week quota (7 days)', 'cost': 'Estimated API cost',
    'duration': 'Session duration', 'spend': 'Gateway spend limit (when available)',
}


def choose_fields():
    """Built-in curses UI; wrapper always restores the terminal on exit."""
    try:
        import curses
    except ImportError:
        raise ValueError('Checkbox menu unavailable. Use --show all or --show model,git,app,effort.')

    def menu(screen):
        screen.keypad(True)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        selected = set(FIELDS)
        cursor = 0
        message = ''
        while True:
            screen.erase()
            height, width = screen.getmaxyx()

            def put(row, text, style=0):
                if 0 <= row < height and width > 1:
                    try:
                        screen.addnstr(row, 0, text, width - 1, style)
                    except curses.error:
                        pass

            put(0, 'CLAUDE STATUS LINE - Select fields', curses.A_BOLD)
            put(1, 'Up/Down: move | Space: toggle | Enter: confirm')
            put(2, 'A: select all | N: clear all | Q/Esc: cancel')
            visible = max(1, height - 6)
            start = max(0, min(cursor - visible + 1, len(FIELDS) - visible))
            for offset, field in enumerate(FIELDS[start:start + visible]):
                index = start + offset
                tick = 'x' if field in selected else ' '
                text = f'{">" if index == cursor else " "} [{tick}] {field:<9} {LABELS[field]}'
                put(4 + offset, text, curses.A_REVERSE if index == cursor else 0)
            put(height - 1, message or f'{len(selected)}/{len(FIELDS)} selected; default: all')
            screen.refresh()
            key = screen.getch()
            if key in (curses.KEY_UP, ord('k')):
                cursor = (cursor - 1) % len(FIELDS)
            elif key in (curses.KEY_DOWN, ord('j'), 9):
                cursor = (cursor + 1) % len(FIELDS)
            elif key == ord(' '):
                field = FIELDS[cursor]
                selected.symmetric_difference_update([field])
                message = ''
            elif key in (ord('a'), ord('A')):
                selected = set(FIELDS)
                message = ''
            elif key in (ord('n'), ord('N')):
                selected.clear()
                message = ''
            elif key in (10, 13, curses.KEY_ENTER):
                if selected:
                    return [field for field in FIELDS if field in selected]
                message = 'Select at least one field. Space to toggle, A for all.'
            elif key in (27, ord('q'), ord('Q'), 3):
                raise KeyboardInterrupt('Cancelled; no files changed.')
            elif key == -1:
                raise EOFError('Terminal input closed; no files changed.')

    try:
        return curses.wrapper(menu)
    except curses.error as error:
        raise ValueError('Cannot open checkbox menu. Use --show all or --show model,git,app,effort.') from error


def parse_show(value):
    if value.strip().lower() == 'all':
        return list(FIELDS)
    fields = list(dict.fromkeys(x.strip().lower() for x in value.split(',') if x.strip()))
    if not fields or any(x not in FIELDS for x in fields):
        raise ValueError('Use all or comma-separated fields: ' + ','.join(FIELDS))
    return fields


def atomic_write(path, content, mode):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(config_dir, show):
    source = Path(__file__).resolve().with_name('statusline.py')
    script_content = source.read_text(encoding='utf-8')
    config_dir = config_dir.expanduser().absolute()
    config_dir.mkdir(parents=True, exist_ok=True)
    settings = config_dir / 'settings.json'
    script = config_dir / 'statusline.py'
    options_path = config_dir / 'statusline-config.json'
    if source == script.resolve():
        raise ValueError('Run installer from the extracted download folder.')
    for target in (settings, script, options_path):
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError(f'Refusing non-regular target: {target}')
    config = json.loads(settings.read_text(encoding='utf-8')) if settings.exists() else {}
    if not isinstance(config, dict):
        raise ValueError('settings.json must be a JSON object; no files changed.')
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backups = []
    for target in (settings, script, options_path):
        if target.exists():
            backup = target.with_name(target.name + '.backup-' + stamp)
            shutil.copy2(target, backup)
            os.chmod(backup, 0o600)
            backups.append(backup)
    config['statusLine'] = {
        'type': 'command',
        'command': shlex.quote(sys.executable) + ' ' + shlex.quote(str(script)),
        'padding': 0,
    }
    atomic_write(script, script_content, 0o600)
    atomic_write(options_path, json.dumps({'show': show}, indent=2) + '\n', 0o600)
    atomic_write(settings, json.dumps(config, ensure_ascii=False, indent=2) + '\n', 0o600)
    print(f'Installed: {script}')
    print(f'Updated: {settings}')
    print(f'Show: {", ".join(show)}')
    print(f'Display options: {options_path}')
    for backup in backups:
        print(f'Backup: {backup}')
    print('Open Claude Code in Warp, then send one message to populate session data.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config-dir', type=Path,
                        default=Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude'))
    parser.add_argument('--show', help='all (default), or comma-separated: ' + ','.join(FIELDS))
    parser.add_argument('--yes', '-y', action='store_true', help='Use defaults without interactive questions')
    args = parser.parse_args()
    try:
        chosen = args.show
        selected_fields = None
        if not args.yes and args.show is None and sys.stdin.isatty():
            selected_fields = choose_fields()
        install(args.config_dir, selected_fields if selected_fields is not None else parse_show(chosen or 'all'))
    except (OSError, ValueError, EOFError, KeyboardInterrupt) as error:
        print(f'Installation stopped: {error}', file=sys.stderr)
        sys.exit(1)
