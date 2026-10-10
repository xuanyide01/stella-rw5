"""Read-only Artemis pf8 reader. Format reference: morkt/GARbro ArcPFS.cs (MIT)."""
from pathlib import Path
import struct,hashlib

def index(archive):
    archive=Path(archive)
    with archive.open('rb') as stream:
        header=stream.read(7)
        if header[:3]!=b'pf8':raise ValueError('Expected pf8 archive')
        size=struct.unpack_from('<I',header,3)[0]
        if size>10000000 or size+7>archive.stat().st_size:raise ValueError('Invalid index size')
        raw=stream.read(size)
    count=struct.unpack_from('<I',raw)[0];pos=4;entries=[]
    if count>100000:raise ValueError('Invalid entry count')
    for i in range(count):
        n=struct.unpack_from('<I',raw,pos)[0]
        if not 0<n<4096 or pos+n+16>len(raw):raise ValueError('Invalid name length')
        name=raw[pos+4:pos+4+n].decode('utf8').replace('\\','/')
        if name.startswith('/') or '..' in Path(name).parts:raise ValueError('Unsafe archive path')
        pos+=n+8;offset,length=struct.unpack_from('<II',raw,pos);pos+=8
        if offset<7+size or offset+length>archive.stat().st_size:raise ValueError('Entry out of bounds')
        entries.append({'name':name,'offset':offset,'size':length})
    return entries,hashlib.sha1(raw).digest()

def payload(archive,entry,key):
    with Path(archive).open('rb') as stream:
        stream.seek(entry['offset']);raw=stream.read(entry['size'])
    if len(raw)!=entry['size']:raise ValueError('Short archive read')
    out=bytearray(len(raw))
    for i,value in enumerate(key):
        table=bytes(n^value for n in range(256))
        out[i::len(key)]=raw[i::len(key)].translate(table)
    return bytes(out)
