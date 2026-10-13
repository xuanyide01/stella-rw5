"""RPA-3.0 primitive-only index reader; no executable deserialization globals."""
from pathlib import Path
import io
import pickle
import zlib

class PrimitiveUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError('RPA global is forbidden: ' + module + '.' + name)

def index(path):
    with Path(path).open('rb') as stream:
        header = stream.readline(200).decode('ascii').split()
        if header[0] != 'RPA-3.0':
            raise ValueError('Expected RPA-3.0')
        offset, key = int(header[1], 16), int(header[2], 16)
        if offset >= Path(path).stat().st_size or Path(path).stat().st_size - offset > 64_000_000:
            raise ValueError('Invalid RPA index size')
        stream.seek(offset)
        data = PrimitiveUnpickler(io.BytesIO(zlib.decompress(stream.read()))).load()
    result = {}
    for name, rows in data.items():
        if not isinstance(name, str) or name.startswith('/') or '..' in Path(name).parts:
            raise ValueError('Invalid archive path')
        result[name] = [(row[0] ^ key, row[1] ^ key, row[2] if len(row) > 2 else b'') for row in rows]
        if any(start < 0 or size < 0 or start + size > offset for start, size, prefix in result[name]):
            raise ValueError('RPA content range invalid')
    return result

def payload(path, rows):
    result = bytearray()
    with Path(path).open('rb') as stream:
        for offset, size, prefix in rows:
            if size > 64_000_000:
                raise ValueError('Archive entry exceeds supported static resource size')
            stream.seek(offset)
            raw = stream.read(size)
            if len(raw) != size:
                raise ValueError('Short RPA read')
            result.extend(prefix)
            result.extend(raw)
    return bytes(result)
