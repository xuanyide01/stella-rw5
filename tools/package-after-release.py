"""Deliver the exact audited 0.2.1 build, with version-specific evidence and source."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

root = Path(__file__).resolve().parents[1]
out = root.parents[1] / 'outputs'
manifest = json.loads((root / 'src/manifest.json').read_text('utf8'))
assert manifest['versionName'] == '0.2.1' and manifest['versionCode'] == 3
package = root / 'dist' / (manifest['package'] + '.debug.' + manifest['versionName'] + '.rpk')
digest = hashlib.sha256(package.read_bytes()).hexdigest()
audit = json.loads((root / 'reports/package-audit.json').read_text('utf8'))
native = json.loads((root / 'native-test-results/v021/report.json').read_text('utf8'))
after = json.loads((root / 'reports/after-conversion.json').read_text('utf8'))
source_check = json.loads((root / 'reports/after-source-audit.json').read_text('utf8'))
assert audit['sha256'] == native['packageSha256'] == digest
assert package.stat().st_size <= 15_000_000
assert native['version'] == '0.2.1' and native['result'] == 'passed'
assert native['coldUpgradeRepresentativeSlots'] == [1,30] and native['coldBootUnlockPreserved']
assert not native['physicalDeviceTested']
assert any('24px and 28px' in check for check in native['checks'])
assert source_check['result'] == 'passed' and source_check['checkedTextBlocks'] == 1549
for file, sha in json.loads((root / 'reports/after-story-baseline.json').read_text('utf8'))['files'].items():
    assert hashlib.sha256((root / file).read_bytes()).hexdigest() == sha
stem = '星之终途-RW5-0.2.1'
created = []
for extension in ['.bin', '.rpk']:
    dest = out / (stem + extension)
    shutil.copyfile(package, dest)
    created.append(dest)
readme = out / (stem + '-安装说明.md')
shutil.copyfile(root / 'README.md', readme)
created.append(readme)
report = {'game': '星之终途', 'version': '0.2.1', 'package': audit,
          'afterStory': after, 'afterSourceAudit': source_check,
          'ui': json.loads((root / 'reports/ui-remake.json').read_text('utf8')),
          'nativeEmulator': native, 'automatedTests': {'passed': 17, 'failed': 0},
          'uiPixelAudit': json.loads((root / 'reports/ui-layout-audit.json').read_text('utf8')),
          'priorCandidateFailure': json.loads((root / 'reports/native-v021-first-exit.json').read_text('utf8')),
          'originalMainStoryBlocksUnchanged': 30, 'oldMainSaveLocationsRetained': True,
          'physicalDeviceTested': False, 'physicalRetestPending': True,
          'historicalPhysicalTest': '0.1.0-r1 confirmed by maintainer; not substituted for current-version testing'}
confirmation = root / 'reports/physical-confirmation-v021.json'
if confirmation.exists():
    physical = json.loads(confirmation.read_text('utf8'))
    assert physical['packageSHA256'] == digest and physical['physicalTestReported']
    report.update(physicalDeviceTested=True, physicalRetestPending=False, physicalConfirmation=physical)
dest = out / (stem + '-检查报告.json')
dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
created.append(dest)

images = root / 'docs/images/v021'
images.mkdir(parents=True, exist_ok=True)
for name in ['title','title-after-cold','after-intro','routes','after-chapters-first',
             'long-standard-top','long-standard-bottom','long-large-top','long-large-bottom',
             'menu','settings','gallery','after-ending-title','choice-loaded-cold']:
    shutil.copyfile(root / 'native-test-results/v021' / (name + '.png'), images / (name + '.png'))
for name, target in [('title', '标题'), ('long-large-bottom', '长文本滑动')]:
    shutil.copyfile(images / (name + '.png'), out / (stem + '-' + target + '.png'))
source = out / (stem + '-源码.zip')
excluded = {'node_modules', '__pycache__', '.git', '.emulator', 'build', 'dist'}
with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for folder in ['src', 'tools', 'tests', 'licenses', 'reports', 'native-test-results', 'docs']:
        for file in sorted((root / folder).rglob('*')):
            rel = file.relative_to(root)
            if not file.is_file() or excluded.intersection(rel.parts) or file.suffix in ['.pem', '.pyc', '.db', '.log', '.rpa', '.rpyc', '.bin', '.rpk']:
                continue
            if file.name.startswith('native-first-') or file.name == 'native-progress.png':
                continue
            # Keep final screenshots and the lock/wake evidence; candidate
            # failure metadata stays included, while duplicate image sets stay local.
            if rel.parts[:2] in [('native-test-results','v021-first'),('native-test-results','v021-third')] and file.suffix == '.png':
                continue
            if rel.parts[:2] == ('native-test-results','v021-second') and file.suffix == '.png' and file.stem not in ['title-locked','main-clear-unlock','wake-screen']:
                continue
            archive.write(file, 'stella-rw5/' + rel.as_posix())
    for filename in ['README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'package.json', 'quickapp.config.js', '.gitignore', '.gitattributes', 'requirements.txt']:
        archive.write(root / filename, 'stella-rw5/' + filename)
assert source.stat().st_size < 25_000_000
with zipfile.ZipFile(source) as archive:
    assert archive.testzip() is None
    assert archive.read('stella-rw5/src/manifest.json') == (root / 'src/manifest.json').read_bytes()
    assert archive.read('stella-rw5/README.md') == readme.read_bytes()
created.append(source)
checksum = out / (stem + '-SHA256.txt')
checksum.write_text(''.join(hashlib.sha256(file.read_bytes()).hexdigest() + '  ' + file.name + '\n' for file in created), 'utf8')
created.append(checksum)
for file in created:
    print(file.name, file.stat().st_size, hashlib.sha256(file.read_bytes()).hexdigest())
