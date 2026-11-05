"""Check launcher compatibility against Paper and keep the tested game bytes exact."""
from pathlib import Path
import hashlib
import io
import json
import zipfile
from PIL import Image
from rpk_signature import audit

root = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
manifest = json.loads((root / 'src/manifest.json').read_text('utf8'))
assert manifest['versionName'] == '0.1.4' and manifest['versionCode'] == 5
assert manifest['package'] == 'com.codex.stella.band8pro' and manifest['config']['designWidth'] == 336
package = root / 'dist' / f'{manifest["package"]}.debug.{manifest["versionName"]}.rpk'
report = audit(package)
assert report['bytes'] < 10_000_000 and report['bytes'] % 16 == 1
baseline = json.loads((root / 'reports/icon-v013-baseline.json').read_text('utf8'))
source_changes = sorted(name for name, digest in baseline['files'].items() if sha((root / name).read_bytes()) != digest)
assert source_changes == ['src/common/logo.png', 'src/manifest.json']
prior = json.loads((root / 'reports/icon-v014/package-v013.json').read_text('utf8'))
allowed = {'META-INF/CERT', 'META-INF/build.txt', 'app.js', 'common/logo.png', 'manifest-watch.json', 'manifest.json'}
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None and set(z.namelist()) == set(prior['entries'])
    changed = {n for n in z.namelist() if sha(z.read(n)) != prior['entries'][n]}
    assert changed == allowed, changed
    app = z.read('app.js').decode('utf8')
    old_app = (root / 'reports/icon-v014/app-v013.js').read_text('utf8')
    assert app.replace('"versionName":"0.1.4","versionCode":5', '"versionName":"0.1.3","versionCode":4') == old_app
    assert z.read('common/logo.png') == (root / 'src/common/logo.png').read_bytes()
    assert json.loads(z.read('manifest-watch.json')) == manifest
    for name in ['manifest.json', 'manifest-watch.json']:
        old = prior['manifests'][name]
        new = json.loads(z.read(name))
        for d in [old, new]:
            d.pop('versionName'); d.pop('versionCode')
            if 'packageInfo' in d:
                d['packageInfo'].pop('timeStamp')
        assert old == new
    info = lambda s: dict(line.split('=', 1) for line in s.splitlines() if '=' in line and not line.startswith('timeStamp='))
    assert info(z.read('META-INF/build.txt').decode('utf8')) == info(prior['buildInfo'])
    icon = Image.open(io.BytesIO(z.read('common/logo.png')))
    assert icon.size == (128, 128) and icon.mode == 'RGBA'
    alpha = icon.getchannel('A')
    assert all(alpha.getpixel(p) == 0 for p in [(0, 0), (127, 0), (0, 127), (127, 127)])
    assert alpha.getpixel((64, 64)) == 255
    # Match the footprint and PNG type of the user-confirmed Paper Band package.
    reference = json.loads((root / 'reports/icon-v014/paper-reference.json').read_text('utf8'))
    assert reference['size'] == list(icon.size) and reference['mode'] == icon.mode
    assert 'dpi' not in icon.info and 'dpi' not in reference['pngInfo']
    assert reference['transparentCorners'] and reference['bitDepth'] == z.read('common/logo.png')[24] == 8
    assert reference['colorType'] == z.read('common/logo.png')[25] == 6

font = json.loads((root / 'reports/package-audit.json').read_text('utf8'))
assert font['sha256'] == report['sha256'] and font['textFontCoverageValid']
report.update({
    'result': 'passed', 'date': '2026-11-04', 'changedSourceFiles': source_changes,
    'changedPackageEntries': sorted(changed), 'iconDimensions': [128, 128],
    'previousIconDimensions': [192, 192], 'referenceGame': '纸上的魔法使',
    'referenceIconDimensions': reference['size'], 'circularRGBAIcon': True,
    'allGameplayCodeAndResourcesExceptLauncherIconUnchanged': True,
    'compiledAppOnlyVersionMetadataChanged': True,
    'defaultFontAndImageAuditPassed': True,
    'priorPackageSHA256': prior['packageSha256'],
    'currentVersionIndependentlyNativeTested': False,
    'physicalDeviceTested': False,
})
(root / 'reports/package-audit-v014.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
print(json.dumps(report, ensure_ascii=False))
