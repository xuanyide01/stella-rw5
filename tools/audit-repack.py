"""Verify rewrapped RPK signatures and prove every original ZIP stream is retained."""
from pathlib import Path
import io, json, struct, sys, zipfile
from rpk_signature import audit

root = Path(__file__).resolve().parents[1]
original = Path(sys.argv[1])
candidate = Path(sys.argv[2])
raw0, raw1 = original.read_bytes(), candidate.read_bytes()
old, new = audit(original), audit(candidate)
assert new['bytes'] <= 15000000
assert old['certificateSha256'] == new['certificateSha256']

def sections(raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    central = z.start_dir
    start = central - struct.unpack_from('<Q', raw, central - 24)[0] - 8
    footer = raw.rfind(b'PK\x05\x06')
    return raw[:start], raw[central:footer], z

local0, central0, z0 = sections(raw0)
local1, central1, z1 = sections(raw1)
assert local0 == local1, 'Local headers or compressed entry data changed'
assert central0 == central1, 'ZIP directory metadata changed'
assert z0.namelist() == z1.namelist()
assert all(z0.read(name) == z1.read(name) for name in z0.namelist())
extra = len(raw1) - len(raw0)
assert 0 <= extra < 16 and len(raw1) % 16 == 1
assert z1.comment == z0.comment + b' ' * extra
report = {
    'revision': 'r1', 'original': old, 'candidate': new,
    'zipEntryContentsAndCompressedStreamsUnchanged': True,
    'allScriptsAndGameResourcesUnchanged': True,
    'innerSignatureBytesUnchanged': z0.read('META-INF/CERT') == z1.read('META-INF/CERT'),
    'extraZipCommentBytes': extra,
    'procedure': 'Append ZIP comment whitespace to length mod 16 = 1; re-sign outer RPK',
    'precedent': 'Summer Pockets 0.1.6-r1 / 0.1.7 installed on physical REDMI Watch 5',
    'failureCause': 'Unidentified; packaging sensitivity is a candidate, not a proven cause',
    'physicalInstallationPassed': None,
}
(root/'reports/repack-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps(report, ensure_ascii=False))
