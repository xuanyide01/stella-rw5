"""Load RPYC syntax as inert data, never importing Ren'Py or executing source/Python."""
import collections
import io
import pickle
import struct
import zlib

class Node:
    def __setstate__(self, state):
        self._pickle_state = state
        if isinstance(state, dict):
            self.__dict__.update(state)
        elif isinstance(state, tuple):
            for value in state:
                if isinstance(value, dict):
                    self.__dict__.update(value)

class Expr(str):
    def __new__(cls, value='', *args):
        obj = str.__new__(cls, value)
        obj._expr_metadata = args
        return obj
    def __setstate__(self, state):
        if isinstance(state, dict):
            self.__dict__.update(state)

AST_NAMES = {'Init', 'Python', 'PyCode', 'Define', 'PyExpr', 'Label', 'UserStatement',
             'Show', 'With', 'Say', 'Scene', 'If', 'Jump', 'Return', 'Hide', 'Image',
             'Menu', 'Call', 'Pass', 'Translate', 'TranslateEnd', 'EndTranslate',
             'TranslateString', 'Style', 'Default'}
ATL_NAMES = {'RawBlock', 'RawMultipurpose', 'RawChild', 'RawChoice', 'RawParallel',
             'RawRepeat', 'RawEvent', 'RawFunction', 'RawContainsExpr', 'RawTime'}
CLASSES = {name: type(name, (Node,), {}) for name in AST_NAMES | ATL_NAMES if name != 'PyExpr'}

class SyntaxUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module in ['__builtin__', 'builtins'] and name in ['list', 'set', 'frozenset']:
            return {'list': list, 'set': set, 'frozenset': frozenset}[name]
        if (module, name) == ('collections', 'defaultdict'):
            return collections.defaultdict
        if module == 'renpy.ast' and name in AST_NAMES:
            return Expr if name == 'PyExpr' else CLASSES[name]
        if module == 'renpy.atl' and name in ATL_NAMES:
            return CLASSES[name]
        if module == 'renpy.revertable' and name == 'RevertableDict':
            return dict
        raise ValueError('Unsupported pickle global: ' + module + '.' + name)

def load(raw):
    if not raw.startswith(b'RENPY RPC2'):
        raise ValueError('Expected RPYC2 syntax archive')
    slot, start, size = struct.unpack_from('<III', raw, 10)
    if slot != 1 or start + size > len(raw):
        raise ValueError('Invalid RPYC2 syntax slot')
    data = zlib.decompress(raw[start:start + size])
    if len(data) > 32_000_000:
        raise ValueError('Syntax data too large')
    return SyntaxUnpickler(io.BytesIO(data)).load()

def plain(value, active=None):
    active = set() if active is None else active
    if isinstance(value, (Node, dict, list, tuple, set, frozenset)):
        if id(value) in active:
            return {'reference': type(value).__name__, 'line': getattr(value, 'linenumber', None)}
        active = active | {id(value)}
    if isinstance(value, Node):
        return {'type': type(value).__name__, **{key: plain(item, active) for key, item in value.__dict__.items()
                if key not in ['next', '_pickle_state']},
                **({'pickleState': plain(value._pickle_state, active)} if type(value).__name__ == 'PyCode' else {})}
    if isinstance(value, dict):
        return {str(key): plain(item, active) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [plain(item, active) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError('Unsupported syntax value ' + str(type(value)))

if __name__ == '__main__':
    from pathlib import Path
    import json
    root = Path(__file__).resolve().parent
    for path in (root / 'scripts/rpy').rglob('*.rpyc'):
        if path.parent.name not in ['drama', 'options']:
            continue
        if path.parent.name == 'options' and path.stem not in ['image', 'options']:
            continue
        data = load(path.read_bytes())
        dest = root / 'ast' / path.relative_to(root / 'scripts').with_suffix('.json')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(plain(data), ensure_ascii=False, indent=2), 'utf8')
        print(path.name, 'nodes', len(data[1]))
