"""Package 0.2.4 only after its exact variant has passed native AUTO checks."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

root = Path(__file__).resolve().parents[1]
out = root.parents[1] / 'outputs'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
m = json.loads((root / 'src/manifest.json').read_text('utf8'))
a = json.loads((root / 'reports/package-audit.json').read_text('utf8'))
n = json.loads((root / 'native-test-results/auto-v024/report.json').read_text('utf8'))
checks = json.loads((root / 'reports/autoplay-audit.json').read_text('utf8'))
rpk = root / 'dist' / f'{m["package"]}.debug.{m["versionName"]}.rpk'
assert m['versionName'] == '0.2.4' and m['versionCode'] == 6
assert a['sha256'] == n['packageSha256'] == checks['packageSha256'] == sha(rpk)
assert n['result'] == checks['result'] == 'passed' and not n['physicalDeviceTested']
lite = root.name.endswith('lite')
assert a['bytes'] < (10_000_000 if lite else 15_000_000)
stem = '星之终途-RW5-0.2.4' + ('-轻量版' if lite else '')
variant = '轻量版' if lite else '标准版'
old_readme = (root / 'README.md').read_text('utf8')
history = root / 'docs/history/README-v023.md'
history.parent.mkdir(parents=True, exist_ok=True)
if not history.exists() and '当前版本 **0.2.3' in old_readme:
    history.write_text(old_readme, 'utf8')
if '当前版本 **0.2.3' in old_readme:
    text = old_readme.replace('当前版本 **0.2.3 / versionCode 5**','当前版本 **0.2.4 / versionCode 6**')
    text = text.replace('12,212,113', f"{a['bytes']:,}").replace('9,879,089', f"{a['bytes']:,}")
    text = text.replace('13,460,923', f"{a['expandedBytes']:,}").replace('11,122,927', f"{a['expandedBytes']:,}")
    start, end = text.index('## 本次修复'), text.index('## 功能')
    auto = '''## 自动播放（0.2.4）

在剧情中打开“菜单”，点“自动播放：关闭”切换为开启，再点“返回游戏”。自动播放按约 **30 毫秒／字**显示；当前句逐字完成后，按所选档位等待，再进入下一句。

| 自动速度 | 逐字完成后的等待 |
| --- | --- |
| 慢速 | 2.6 秒 |
| 标准（默认） | 1.5 秒 |
| 快速 | 0.8 秒 |

点击“自动速度”循环切换三档。超过 60 字的段落，每多一字再延长 55 毫秒，最多额外 5 秒。自动时始终逐字显示；手动阅读原有的“即时／逐字”设置仍保留。

- 遇到选项时暂停，必须由玩家选择，之后继续；不会自动选择或绕过“谢谢你，菲莉娅”的确认。
- 打开菜单、存读档界面或切到后台时暂停；返回正文后从当前句重新等待。正文拖动时暂停，松手及惯性滚动结束后重新计时。
- 手动点击还没显示完的文本会补全当前句并重新等待；已显示完整时点击仍可推进。点“上一句”关闭自动播放，方便回看。
- 返回标题、剧情结束、报错或退出均取消自动推进。章节加载中切到后台不会漏掉下一章第一句；已取消的加载也不会在返回标题后重新打开剧情。
- **只保存速度档位；每次启动应用，自动播放默认关闭。** 不把自动开关写进存档或通关记录。

菜单保留保存、读取、下一章、显示速度、字号和返回入口；九个按钮均完整显示。沿用 0.2.3 的完整标题立绘，本次不重新压缩或裁剪 CG、剧情立绘和字体；剧情、选择目标及原有存档模块逐字节不变，见 `reports/autoplay-audit.json`。

'''
    text = text[:start] + auto + text[end:]
    text = text.replace('星之终途-RW5-0.2.3-轻量版.bin', stem + '.bin').replace('星之终途-RW5-0.2.3.bin', stem + '.bin')
    start, end = text.index('## 验证范围'), text.index('## 构建与来源')
    validation = '''## 验证范围

标准版和轻量版各通过 **28 项自动检查**：原有全文、章节、选项与存档检查，以及自动播放计时、选项暂停／恢复、菜单／后台／触摸暂停、长文等待、手动补全、保存读取、速度持久化、关闭重开、终止与异步加载取消检查。记录为 `reports/autoplay-tests.tap`。

每个精确安装包分别通过内外签名、摘要、CRC、1080 张图像解码、圆形透明图标和字体覆盖检查；新增菜单字形也核对了原生默认字体。`reports/autoplay-v023-baseline.json` 与 `reports/autoplay-audit.json` 核对本次源文件差异，原作资源保持不变。

**两版分别安装到官方通用 Vela 模拟器实测**。`native-test-results/auto-v024/report.json` 绑定各自安装包 SHA-256，覆盖九项菜单、三档速度、连续自动推进、菜单及 LOAD 暂停、真实长段落拖动后恢复、后日谈 107:423 选项停留／选择后恢复、上一句关闭自动、重开后默认关闭且速度保留。截图只代表对应的实际运行。

该环境为 `vela-watch-5.0`、432×514、128 MB，不代表 REDMI Watch 5 实际固件或 RAM。后台和异步加载等边界另有自动检查；历史 0.2.3 标题检查及更早报告不替代本版新验证。**0.2.4 尚待实机复测。**

'''
    text = text[:start] + validation + text[end:]
    text = text.replace('node --test tests/reader.test.cjs', 'node --test tests/reader.test.cjs tests/auto-reader.test.cjs')
    (root / 'README.md').write_text(text, 'utf8')
else:
    text = old_readme
assert '当前版本 **0.2.4' in text and '28 项自动检查' in text
created = []
for ext in ['.bin','.rpk']:
    dest = out / (stem + ext);shutil.copyfile(rpk,dest);created.append(dest)
dest = out / (stem + '-安装说明.md');dest.write_text(text,'utf8');created.append(dest)
report = {'game':'星之终途','device':'REDMI Watch 5','variant':variant,'version':'0.2.4','date':'2026-10-20',
          'package':a,'autoplay':checks,'native':n,'physicalDeviceTested':False}
confirmation = root / 'reports/physical-confirmation-v024.json'
if confirmation.is_file():
    physical = json.loads(confirmation.read_text('utf8'))
    assert physical['version'] == '0.2.4' and physical['physicalTestReported']
    assert physical['deliveredPackageSHA256'][root.name] == sha(rpk)
    report.update(physicalDeviceTested=True, physicalConfirmation=physical)

dest = out / (stem + '-检查报告.json');dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');created.append(dest)
dest = out / (stem + '-自动播放菜单.png');shutil.copyfile(root/'native-test-results/auto-v024/menu-enabled.png',dest);created.append(dest)
source = out / (stem + '-源码.zip')
reports = {'physical-confirmation-v024.json','autoplay-v023-baseline.json','autoplay-audit.json','autoplay-tests.tap','package-audit.json','ui-remake.json','text-font.json','text-provenance.json','assets.json','conversion.json','after-story-baseline.json','after-choice-source.json','after-text-provenance.json','after-source-audit.json','after-conversion.json','title-complete-audit.json'}
tools = {'build.cjs','repack-rpk.cjs','rpk_signature.py','audit-package.py','audit-auto.py','package-auto-release.py','remake-ui.py','build-text-font.py','pfs.py','lua_table.py','rpa_data.py','renpy_data.py','audit-after-source.py','emulator-server.cjs','emulator-view.html','setup-emulator.cjs','start-emulator.ps1','native-ui-install.cjs','native-auto-check.cjs','restart-after-isolated.ps1'}
top = {'README.md','LICENSE','THIRD_PARTY_NOTICES.md','package.json','quickapp.config.js','requirements.txt','.gitignore','.gitattributes'}
with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    candidates = []
    for folder in ['src','tests','licenses']:
        candidates.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    candidates.extend(root/name for name in top if (root/name).is_file())
    candidates.extend(root/'reports'/name for name in reports if (root/'reports'/name).is_file())
    candidates.extend(root/'tools'/name for name in tools if (root/'tools'/name).is_file())
    for name in ['package.json','package-lock.json']:
        p=root/'tools/compat-toolkit'/name
        if p.is_file():candidates.append(p)
    candidates.extend(p for p in (root/'native-test-results/auto-v024').iterdir() if p.suffix=='.png' or p.name=='report.json')
    if history.is_file():candidates.append(history)
    for p in sorted(set(candidates)):z.write(p,root.name+'/'+p.relative_to(root).as_posix())
assert source.stat().st_size < 25_000_000
with zipfile.ZipFile(source) as z:
    assert z.testzip() is None
    assert z.read(root.name+'/README.md') == (root/'README.md').read_bytes()
    assert json.loads(z.read(root.name+'/src/manifest.json'))['versionName'] == '0.2.4'
created.append(source)
(out/(stem+'-SHA256.txt')).write_text(''.join(sha(p)+'  '+p.name+'\n' for p in created),'utf8')
print(json.dumps({'stem':stem,'packageBytes':a['bytes'],'sourceBytes':source.stat().st_size,'sha256':sha(rpk)},ensure_ascii=True))
