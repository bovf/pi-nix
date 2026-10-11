"""Native embellishments on validated cuts; no arbitrary script/file execution."""
from store import json_text, rational, TICKS

PREFIXES = ('effects.', 'graphics.', 'captions.')
EXACT = {'sequence.applyVideoTransition', 'sequence.applyAudioTransition', 'sequence.setTransition'}
# These commands import/export files or templates rather than editing this native document.
FILE_COMMANDS = {'captions.import', 'captions.export', 'graphics.exportTemplate', 'graphics.importTemplate', 'graphics.replaceTemplate', 'graphics.exportMotionGraphicsTemplate', 'effects.savePreset', 'effects.importPresets', 'effects.exportPresets'}


def validate(commands):
    if not isinstance(commands, list) or len(commands) > 100 or len(json_text(commands).encode('utf-8')) > 65536:
        raise ValueError('nativeCommands must be at most 100 commands/64 KiB')
    for command in commands:
        if not isinstance(command, dict) or set(command) != {'id', 'params'} or not isinstance(command['id'], str) or not isinstance(command['params'], dict):
            raise ValueError('native command requires exactly id and params')
        name = command['id']
        if not (name.startswith(PREFIXES) or name in EXACT) or name in FILE_COMMANDS:
            raise ValueError('native command is not an in-document effect/graphic/caption/transition edit')
        check_values(command['params'])
    return commands


def check_values(value, depth=0):
    if depth > 12:
        raise ValueError('native parameter nesting is too deep')
    if isinstance(value, dict):
        # Filename-bearing commands/parameters cannot smuggle extra media or overwrite history.
        if any(k.lower() in {'path', 'paths', 'file', 'filename', 'url', 'uri', 'template', 'presetpath'} for k in value):
            raise ValueError('native edit file/URL parameters are not supported; use an authorized asset workflow')
        for v in value.values():
            check_values(v, depth + 1)
    elif isinstance(value, list):
        for v in value:
            check_values(v, depth + 1)
    elif value == 'time_remap':
        raise ValueError('time remapping requires a retiming-aware plan; source-range constraints must not be bypassed')
    elif isinstance(value, str) and (value.startswith(('/', 'file:', 'http:', 'https:')) or '..' in value.split('/')):
        raise ValueError('native edit parameters cannot reference external paths/URLs')


def resolve(value, clips, results):
    if isinstance(value, dict):
        if set(value) == {'$clip'}:
            index = value['$clip']
            if type(index) is not int or not 0 <= index < len(clips):
                raise ValueError('$clip must index a validated video cut')
            return clips[index]
        if set(value) == {'$seconds'}:
            seconds = rational(value['$seconds'])
            if seconds < 0 or seconds > 3600:
                raise ValueError('native time must be within one hour')
            return round(seconds * TICKS)
        if set(value) == {'$result', 'field'}:
            index, field = value['$result'], value['field']
            if type(index) is not int or not 0 <= index < len(results) or not isinstance(field, str):
                raise ValueError('native result reference is invalid')
            return results[index][field]
        return {k: resolve(v, clips, results) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, clips, results) for v in value]
    return value


def run(film, commands, clips):
    results = []
    for command in validate(commands):
        params = resolve(command['params'], clips, results)
        check_values(params)
        results.append(film.tool('command_run', {'id': command['id'], 'params': params}))
    return results
