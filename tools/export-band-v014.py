"""Package the launcher-icon correction without relabelling old native tests."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import zipfile

root = Path(__file__).resolve().parents[1]
project = Path(os.environ.get('STELLA_DELIVERY_PROJECT', root.parent / 'stella-band8pro-delivery'))
out = project / '最终交付'
out.mkdir(parents=True, exist_ok=True)
stem = '星之终途-Band8Pro-0.1.4'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((root / 'src/manifest.json').read_text('utf8'))
package = root / 'dist' / f'{manifest["package"]}.debug.{manifest["versionName"]}.rpk'
audit = json.loads((root / 'reports/package-audit-v014.json').read_text('utf8'))
font = json.loads((root / 'reports/package-audit.json').read_text('utf8'))
assert audit['result'] == 'passed' and audit['sha256'] == font['sha256'] == sha(package)
assert audit['bytes'] < 10_000_000 and manifest['versionName'] == '0.1.4'
tap = (root / 'reports/autoplay-tests-v014.tap').read_text('utf8')
assert '# pass 28' in tap and '# fail 0' in tap
text = (root / 'docs/history/README-band-v013.md').read_text('utf8')
text = text.replace('版本 **0.1.3 / versionCode 4**', '版本 **0.1.4 / versionCode 5**')
text = text.replace('9,865,313 字节（9.87 MB）', f'{audit["bytes"]:,} 字节（{audit["bytes"]/1e6:.2f} MB）')
text = text.replace('11,114,818', f'{audit["expandedBytes"]:,}')
section = '''## 应用列表图标修复（0.1.4）

依据维护者 2026-11-04 的小米手环 8 Pro 实机反馈，将应用列表图标由 **192×192 改为 128×128**，与已获实机确认的《纸上的魔法使》手环 0.1.1 安装包一致。保留原有菲莉娅图案、宽高比和圆形透明边缘，采用 8 位真彩 RGBA PNG，并与参考图标一样不附加 DPI 缩放提示。

构建脚本新增图标尺寸和 PNG 类型检查，阻止再次将 192 像素的手表图标打入手环包。检查针对最终安装包内的 `common/logo.png`，而非只检查源码图片。

除启动器图标及必要版本／构建信息和签名外，安装包文件保持原样；`pages/index/index.js`、全部剧情、CG、字体、自动播放、30 栏存档和 0.1.3 文本错位修复代码均逐字节一致。包名和存档键沿用旧版。**0.1.4 的实际应用列表大小待手环复测。**

'''
text = text.replace('## 文本错位修复（0.1.3）', section + '## 保留的文本错位修复（0.1.3）')
text = text.replace('当前精确包的 29 张原生阅读画面', '0.1.3 精确包的 29 张原生阅读画面')
text = text.replace('全部剧情块、图片、字体和原有存档模块', '全部剧情块、剧情图片、字体和原有存档模块')
text = text.replace('**本版已通过自动检查、29 张阅读画面的像素边界检查及 336×480 官方通用 Vela 模拟器回归，仍待小米手环 8 Pro 实机复测。**',
                    '**0.1.3 已通过 29 张阅读画面的边界检查及通用 Vela 模拟器回归；本次 0.1.4 仅修正启动器图标，图标效果待手环复测。**')
text = text.replace('星之终途-Band8Pro-0.1.3.bin', stem + '.bin')
text = text.replace('3. 保留存档时优先尝试覆盖手环旧版；', '3. 覆盖后若仍显示旧图标，可正常重启手环再查看。保留存档时优先尝试覆盖手环旧版；')
a, b = text.index('## 验证范围'), text.index('## 构建')
text = text[:a] + '''## 验证范围

本版重新通过 28 项自动检查、内外签名、全部文件摘要与 CRC、1,080 张图片解码和字体覆盖检查。最终包图标为 128×128、RGBA、四角透明，尺寸、PNG 类型及透明格式与《纸上的魔法使》已安装包对照一致。当前报告为 `reports/package-audit-v014.json`，参考证据位于 `reports/icon-v014/`。

对比 0.1.3 实际安装包，仅图标、版本／构建信息和相应签名发生变化；编译后的应用入口仅更新版本字段，阅读页面及其他文件逐字节相同。保留 0.1.3 的原生回归和 29 张阅读画面记录作为历史证据，不将其标注为 0.1.4 的独立原生或实机测试。

**本次未重新进行独立原生模拟器或手环实机验证；新图标效果需在小米手环 8 Pro 上复测。**

''' + text[b:]
text = text.replace('python tools/audit-layout-v013.py', 'python tools/audit-icon-v014.py')
old = '本版 `audit-layout-v013.py` 核对交付精确包与对应原生报告；重新构建改变包摘要后，需对新包重新运行原生回归，再核对版面证据。'
text = text.replace(old, '`tools/audit-icon-v014.py` 对比随源码提供的 0.1.3 包文件摘要和元数据快照；重新构建后，需先用 `audit-package.py` 更新当前包的签名与字体报告。图标可用 `node tools/resize-band-icon-v014.cjs reports/icon-v014/original-192.png` 从原图重新生成。')
(root / 'README.md').write_text(text, 'utf8')
report = {
    'game': '星之终途', 'version': '0.1.4', 'date': '2026-11-04',
    'device': 'Xiaomi Smart Band 8 Pro', 'package': audit, 'fontAndResourceAudit': font,
    'automatedTests': {'passed': 28, 'failed': 0},
    'priorNativeEvidenceVersion': '0.1.3', 'independentNativeTested': False,
    'physicalDeviceTested': False, 'physicalRetestPending': True,
    'priorPhysicalFeedback': {'version': '0.1.3', 'reportedBy': 'maintainer',
                              'issue': 'Launcher icon oversized on Xiaomi Smart Band 8 Pro'},
}
created = []
for extension in ['bin', 'rpk']:
    target = out / (stem + '.' + extension)
    shutil.copyfile(package, target)
    created.append(target)
for suffix, data in [('-安装说明.md', text), ('-检查报告.json', json.dumps(report, ensure_ascii=False, indent=2) + '\n')]:
    target = out / (stem + suffix)
    target.write_text(data, 'utf8')
    created.append(target)
target = out / (stem + '-图标.png')
shutil.copyfile(root / 'src/common/logo.png', target)
created.append(target)

previous_source = out / '星之终途-Band8Pro-0.1.3-源码.zip'
with zipfile.ZipFile(previous_source) as z:
    entries = {Path(i.filename).relative_to('stella-band8pro').as_posix()
               for i in z.infolist() if not i.is_dir()}
entries.update(['tools/resize-band-icon-v014.cjs', 'tools/audit-icon-v014.py', 'tools/export-band-v014.py',
                'reports/icon-v013-baseline.json', 'reports/package-audit-v014.json',
                'reports/autoplay-tests-v014.tap', 'docs/history/README-band-v013.md'])
entries.update(p.relative_to(root).as_posix() for p in (root / 'reports/icon-v014').iterdir() if p.is_file())
assert all((root / name).is_file() for name in entries)
source = out / (stem + '-源码.zip')
with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name in sorted(entries):
        assert not {'node_modules', '.git', '__pycache__'}.intersection(Path(name).parts)
        z.write(root / name, 'stella-band8pro/' + name)
with zipfile.ZipFile(source) as z:
    assert z.testzip() is None
    assert z.read('stella-band8pro/src/common/logo.png') == (root / 'src/common/logo.png').read_bytes()
assert source.stat().st_size < 25_000_000
created.append(source)
(out / (stem + '-SHA256.txt')).write_text(''.join(sha(p) + '  ' + p.name + '\n' for p in created), 'utf8')

editable = project / '源码'
baseline = json.loads((root / 'reports/icon-v013-baseline.json').read_text('utf8'))['files']
for name, digest in baseline.items():
    target = editable / name
    if target.exists():
        assert sha(target) in [digest, sha(root / name)], 'Unmerged editable source: ' + name
for name in sorted(entries):
    target = editable / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, target)
index = project / '目录说明.md'
if index.exists():
    data = index.read_text('utf8').replace('本地最终交付版本：0.1.3', '本地最终交付版本：0.1.4')
    note = '\n0.1.4 按《纸上的魔法使》将图标调整为 128×128 圆形透明 PNG；安装包 9.83 MB，图标效果待手环复测。\n'
    if note not in data:
        data += note
    index.write_text(data, 'utf8')
index = project.parent / 'README.md'
if index.exists():
    index.write_text(index.read_text('utf8').replace('| 星之终途 · Band 8 Pro | 0.1.3 |', '| 星之终途 · Band 8 Pro | 0.1.4 |'), 'utf8')
print(json.dumps({'package': str(out / (stem + '.bin')), 'bytes': audit['bytes'],
                  'sha256': sha(package), 'icon': [128, 128], 'sourceBytes': source.stat().st_size,
                  'physicalRetestPending': True}, ensure_ascii=False))
