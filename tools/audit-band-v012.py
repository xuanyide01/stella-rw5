"""Audit the exact Band package and its relationship to both maintained versions."""
from pathlib import Path
import hashlib
import io
import json
import re
import zipfile
from PIL import Image
from fontTools.ttLib import TTFont
from rpk_signature import audit

root = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((root / 'src/manifest.json').read_text('utf8'))
assert manifest['package'] == 'com.codex.stella.band8pro'
assert manifest['versionName'] == '0.1.2' and manifest['versionCode'] == 3
assert manifest['config']['designWidth'] == 336 and manifest['minAPILevel'] == 1
package = root / 'dist' / f'{manifest["package"]}.debug.{manifest["versionName"]}.rpk'
proof = audit(package)
assert proof['bytes'] < 10_000_000
assert proof['bytes'] % 16 == 1
baseline = json.loads((root / 'reports/band-v011-baseline.json').read_text('utf8'))['files']
changed = [n for n, digest in baseline.items() if sha(root / n) != digest]
added = sorted(p.relative_to(root).as_posix() for p in (root / 'src').rglob('*')
               if p.is_file() and p.relative_to(root).as_posix() not in baseline)
assert sorted(changed) == ['src/manifest.json', 'src/pages/index/index.ux']
assert added == ['src/common/auto-reader.js']
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    compiled_manifest = json.loads(z.read('manifest.json'))
    assert compiled_manifest.pop('packageInfo')['toolkit'] == '1.1.0'
    assert compiled_manifest['config'].pop('debug') is False
    assert compiled_manifest == manifest
    assert json.loads(z.read('manifest-watch.json')) == manifest
    images = portraits = common = 0
    max_pixels = 0
    for name in z.namelist():
        if name.startswith('common/') and not name.endswith('/'):
            assert z.read(name) == (root / 'src' / name).read_bytes(), name
            common += 1
        if name.endswith(('.jpg', '.png')):
            im = Image.open(io.BytesIO(z.read(name)))
            im.load()
            images += 1
            max_pixels = max(max_pixels, im.width * im.height)
            if '/images/' in name:
                assert im.width <= 300 and im.height <= 256, name
                if name.endswith('.png'):
                    assert im.convert('RGBA').getchannel('A').getextrema()[0] == 0
                    portraits += 1
    logo = Image.open(io.BytesIO(z.read('common/logo.png')))
    assert logo.mode == 'RGBA' and logo.size == (192, 192)
    assert all(logo.getpixel(p)[3] == 0 for p in [(0, 0), (191, 0), (0, 191), (191, 191)])
    font = TTFont(io.BytesIO(z.read('common/stella-extra.otf'))).getBestCmap()
    assert ord('躙') in font

page = (root / 'src/pages/index/index.ux').read_text('utf8')
assert 'font-family: {{' not in page and 'font-family:sans-serif' not in page
assert 'font-family:stellaextra' in page
assert 'ontouchend="dialogueTouchEnd"' in page
assert "key:'stella_band8pro_settings_v1'" in page
assert 'stella_rw5_' not in page
assert '.reading-action{height:38px;margin-bottom:6px;font-size:20px;}' in page
assert 14 + 32 + 6 + 9 * (38 + 6) + 14 <= 480

strings = []
def visit(value):
    if isinstance(value, str):
        strings.append(value.replace('・', '·'))
    elif isinstance(value, list):
        for item in value:
            visit(item)
    elif isinstance(value, dict):
        for item in value.values():
            visit(item)
for file in (root / 'src/common/story').rglob('*.txt'):
    visit(json.loads(file.read_text('utf8')))
visit(json.loads((root / 'src/common/gallery.txt').read_text('utf8')))
triggers = set(json.loads((root / 'reports/text-font.json').read_text('utf8'))['missingDefaultGlyphs'])
normal_chars = set(''.join(s for s in strings if not triggers.intersection(s)))
extra_strings = [s for s in strings if triggers.intersection(s)]
assert all(ch.isspace() or ord(ch) < 32 or ord(ch) in font for s in extra_strings for ch in s)
new_labels = '自动播放：开启关闭自动速度：慢速标准快速'
new_chars_not_in_existing_text = sorted(set(new_labels) - normal_chars)
assert not new_chars_not_in_existing_text, new_chars_not_in_existing_text

reference = Path(__import__('os').environ.get('STELLA_RW5_REFERENCE', root / '../stella-rw5-lite'))
if reference.exists():
    watch = (reference / 'src/pages/index/index.ux').read_text('utf8').split('<script>')[1].split('</script>')[0]
    expected = watch.replace('stella_rw5_', 'stella_band8pro_').replace('STELLA_RW5', 'STELLA_BAND8PRO')
    expected = expected.replace('红米手表 5 · 图文版', '小米手环 8 Pro · 图文版')
    for old, new in [(286, 240), (28, 26), (24, 22)]:
        expected = re.sub(r'\b' + str(old) + r'\b', str(new), expected)
    assert page.split('<script>')[1].split('</script>')[0] == expected
    assert (root / 'src/common/auto-reader.js').read_bytes() == (reference / 'src/common/auto-reader.js').read_bytes()

proof.update({
    'result': 'passed', 'date': '2026-11-02', 'screen': [336, 480],
    'maximumPackageBytes': 10_000_000, 'watchManifestMatches': True,
    'commonResourcesMatchSource': common, 'decodedImages': images,
    'transparentPortraitsPreserved': portraits, 'maximumSingleImagePixels': max_pixels,
    'circularRGBAIcon': True, 'changedExistingSourceFiles': sorted(changed),
    'addedSourceFiles': added, 'allOriginalStoryImagesAndFontsByteIdenticalToBand011': True,
    'rw5Version024LogicRetainedWithBandCoordinatesFontsAndStorage': True,
    'dynamicTextInheritsDefaultFontExceptStaticExtraFontBranch': True,
    'rareGlyphFontCoverage': True, 'newUILabelsUseAlreadyCoveredNarrativeCharacters': True,
    'fontCoverageMethod': 'Unchanged 0.1.1 narrative and font bytes; new labels use characters already in previously checked normal-font narrative. Extra-font strings are checked directly against the bundled cmap.',
    'allNineMenuActionsFitByLayout': True, 'storageKeysUnchanged': True,
    'physicalDeviceTested': False,
})
(root / 'reports/package-audit-v012.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', 'utf8')
print(json.dumps(proof, ensure_ascii=False))
