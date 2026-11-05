"""Check the exact package, unchanged story, and native text bounds after scrolling."""
from pathlib import Path
import hashlib
import io
import json
import zipfile
from PIL import Image
from rpk_signature import audit

root = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((root / 'src/manifest.json').read_text('utf8'))
assert manifest['versionName'] == '0.1.3' and manifest['versionCode'] == 4
package = root / 'dist' / f'{manifest["package"]}.debug.{manifest["versionName"]}.rpk'
report = audit(package)
assert report['bytes'] < 10_000_000 and report['bytes'] % 16 == 1
baseline = json.loads((root / 'reports/layout-v012-baseline.json').read_text('utf8'))
changed = [name for name, digest in baseline['files'].items() if sha(root / name) != digest]
assert sorted(changed) == ['src/manifest.json', 'src/pages/index/index.ux']
assert set(baseline['files']) == {p.relative_to(root).as_posix() for p in (root / 'src').rglob('*') if p.is_file()}
snapshot = root / 'reports/layout-original-ux-v012.txt'
assert sha(snapshot) == baseline['files']['src/pages/index/index.ux']
old_page = snapshot.read_text('utf8')
page = (root / 'src/pages/index/index.ux').read_text('utf8')
assert old_page.split('<style>')[0] == page.split('<style>')[0], 'Template or logic changed during layout-only fix'
assert 'font-family: {{' not in page and 'font-family:sans-serif' not in page
assert 'font-family:stellaextra' in page

images = 0
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    assert json.loads(z.read('manifest-watch.json')) == manifest
    for name in z.namelist():
        if name.startswith('common/') and not name.endswith('/'):
            assert z.read(name) == (root / 'src' / name).read_bytes()
        if name.endswith(('.jpg', '.png')):
            Image.open(io.BytesIO(z.read(name))).load()
            images += 1
assert images == 1080

text_count = leading = controls = 0
for p in (root / 'src/common/story').rglob('*.txt'):
    for op in json.loads(p.read_text('utf8')):
        if op.get('op') != 'text':
            continue
        text_count += 1
        text = op['text']
        leading += bool(text and text[0].isspace())
        controls += any(ord(c) < 32 and c not in '\n\t\r' for c in text)
assert text_count == 10975 and leading == controls == 0

def bounds(file):
    im = Image.open(file).convert('RGB')
    assert im.size == (336, 480)
    foreground = [(x, y) for y in range(243, 426) for x in range(336)
                  if min(im.getpixel((x, y))) >= 238]
    assert foreground, file
    return [min(x for x, y in foreground), min(y for x, y in foreground),
            max(x for x, y in foreground), max(y for x, y in foreground)]

comparison = root / 'native-test-results/layout-v013'
before = bounds(comparison / 'before/reported-102-1.png')
assert before[0] < 16 and before[1] < 290, 'Reported old-version drift was not reproduced'
checked = {}
names = ['102-0', 'reported-102-1', 'reported-102-1-back', '102-2']
for name in names:
    p = comparison / 'after' / (name + '.png')
    checked[p.relative_to(root).as_posix()] = bounds(p)
for name in ['reading-standard', 'long-text', 'long-text-large', 'long-text-after-drag']:
    p = root / 'native-test-results/band-v013' / (name + '.png')
    checked[p.relative_to(root).as_posix()] = bounds(p)
for chapter in range(1, 22):
    p = root / 'native-test-results/band-v013' / f'main-chapter-{chapter}.png'
    checked[p.relative_to(root).as_posix()] = bounds(p)
for name, (left, top, right, bottom) in checked.items():
    assert left >= 16 and top >= 290 and right <= 319 and bottom <= 425, (name, checked[name])
native = json.loads((root / 'native-test-results/band-v013/report.json').read_text('utf8'))
assert native['result'] == 'passed' and native['packageSha256'] == sha(package)
font = json.loads((root / 'reports/package-audit.json').read_text('utf8'))
assert font['sha256'] == sha(package) and font['textFontCoverageValid']
report.update({
    'result': 'passed', 'date': '2026-11-02', 'screen': [336, 480],
    'allResourcesAndAutoReadingLogicUnchangedFrom012': True,
    'templateAndScriptUnchangedAfterLineEndingNormalization': True, 'changedSourceFiles': sorted(changed),
    'decodedImages': images, 'textOperationsScanned': text_count,
    'leadingWhitespaceFound': leading, 'unexpectedControlCharactersFound': controls,
    'fontInheritanceFixRetained': True, 'physicalDeviceTested': False,
    'reproducedFrame': '102:1', 'oldTextBounds': before,
    'fixedTextBounds': checked['native-test-results/layout-v013/after/reported-102-1.png'],
    'nativeReadingScreensWithinViewport': checked,
    'nativePackageMatched': True,
})
(root / 'reports/package-audit-v013.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
print(json.dumps({'result': 'passed', 'bytes': report['bytes'], 'sha256': report['sha256'],
                  'readingScreens': len(checked), 'scannedTexts': text_count,
                  'before': before, 'after': report['fixedTextBounds']}, ensure_ascii=False))
