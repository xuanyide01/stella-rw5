"""Audit autoplay's exact build, unchanged 0.2.3 resources and native evidence."""
from pathlib import Path
import hashlib
import json
import re
from PIL import Image, ImageChops
from fontTools.ttLib import TTFont

root = Path(__file__).resolve().parents[1]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = json.loads((root / 'reports/autoplay-v023-baseline.json').read_text('utf8'))['files']
changed = []
for name, expected in baseline.items():
    current = root / name
    assert current.is_file(), name
    if digest(current) != expected:
        changed.append(name)
assert set(changed) == {'src/manifest.json', 'src/pages/index/index.ux'}, changed
added = {p.relative_to(root).as_posix() for p in (root / 'src').rglob('*') if p.is_file()} - set(baseline)
assert added == {'src/common/auto-reader.js'}, added
tests = (root / 'reports/autoplay-tests.tap').read_text('utf-8-sig')
assert re.search(r'# pass 28\b', tests) and re.search(r'# fail 0\b', tests)
package = json.loads((root / 'reports/package-audit.json').read_text('utf8'))
native = json.loads((root / 'native-test-results/auto-v024/report.json').read_text('utf8'))
manifest = json.loads((root / 'src/manifest.json').read_text('utf8'))
rpk = root / 'dist' / f'{manifest["package"]}.debug.{manifest["versionName"]}.rpk'
assert package['sha256'] == native['packageSha256'] == digest(rpk)
assert native['result'] == 'passed' and native['version'] == '0.2.4'
assert package['bytes'] < (10_000_000 if root.name.endswith('lite') else 15_000_000)
default = TTFont(root.parent / 'clannad-probe/native-default-font.ttf').getBestCmap()
assert all(ord(c) in default or c.isspace() for c in '自动播放：开启关闭速度慢速标准快速')
frames = root / 'native-test-results/auto-v024'
fast = Image.open(frames / 'menu-fast-on.png').convert('RGB')
restarted = Image.open(frames / 'restart-auto-off-speed-fast.png').convert('RGB')
auto_box, speed_box = (24,201,408,243), (24,248,408,290)
assert ImageChops.difference(fast.crop(auto_box),restarted.crop(auto_box)).getbbox()
assert ImageChops.difference(fast.crop(speed_box),restarted.crop(speed_box)).getbbox() is None
menu = Image.open(frames / 'menu-enabled.png').convert('RGB')
assert menu.size == (432,514)
green = menu.getpixel((25,61))
for index in range(9):
    top = 60 + 47 * index
    assert menu.getpixel((25,top+1)) == green if index < 8 else menu.getpixel((25,top+1)) != green
    assert top+42 <= 514
report = {'result':'passed','version':'0.2.4','baselineVersion':'0.2.3',
          'changedExistingSourceFiles':changed,'addedSourceFiles':sorted(added),
          'allStoryImagesFontsAndOldSaveModulesUnchanged':True,
          'typewriterMillisecondsPerGlyph':30,'postTextWaitMilliseconds':[2600,1500,800],
          'defaultSpeed':'标准','defaultAutoEnabled':False,'onlySpeedPersisted':True,
          'extraWaitAfter60Glyphs':{'perGlyphMilliseconds':55,'maximumMilliseconds':5000},
          'automatedTests':{'passed':28,'failed':0},'nativeExactPackageChecked':True,
          'nativeMenuActionsFullyVisible':9,'nativeRestartOffAndFastSpeedPreserved':True,
          'newUILabelsCoveredByNativeDefaultFont':True,'physicalDeviceTested':False,
          'packageSha256':package['sha256']}
(root / 'reports/autoplay-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(report,ensure_ascii=True))
