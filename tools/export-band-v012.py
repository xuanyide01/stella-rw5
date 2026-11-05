"""Deliver the exact audited package, its matching source, and scoped evidence."""
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
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((root / 'src/manifest.json').read_text('utf8'))
package = root / 'dist' / f'{manifest["package"]}.debug.{manifest["versionName"]}.rpk'
audit = json.loads((root / 'reports/package-audit-v012.json').read_text('utf8'))
font_audit = json.loads((root / 'reports/package-audit.json').read_text('utf8'))
native = json.loads((root / 'native-test-results/band-v012/report.json').read_text('utf8'))
assert audit['sha256'] == font_audit['sha256'] == native['packageSha256'] == sha(package)
assert audit['result'] == native['result'] == 'passed' and font_audit['textFontCoverageValid']
assert audit['bytes'] < 10_000_000 and manifest['versionName'] == '0.1.2'
assert not native['physicalDeviceTested']
tap = (root / 'reports/autoplay-tests-v012.tap').read_text('utf8')
assert '# pass 28' in tap and '# fail 0' in tap
stem = '星之终途-Band8Pro-0.1.2'
readme = '''# 《星之终途》· 小米手环 8 Pro

版本 **0.1.2 / versionCode 3**，目标屏幕 **336×480**，包名 `com.codex.stella.band8pro`。安装包 **9,865,281 字节（9.87 MB）**，低于 10,000,000 字节上限；解包后 11,114,728 字节。程序、适配、转换和检查由 **OpenAI Codex** 完成，维护者提供需求、资源与实机反馈。

## 本次适配

以已有手环 0.1.1 为基础，合入已通过维护者实机测试的 REDMI Watch 5 0.2.4 全部阅读功能，包括三档自动播放及相关暂停、恢复和退出处理。手表版的实机记录不替代本版测试：**本版已通过自动检查及 336×480 官方通用 Vela 模拟器检查，仍待小米手环 8 Pro 实机复测。**

原有墨绿色界面、右侧贴底的完整菲莉娅标题构图、原作英文标题选项和左对齐排布保留。九项阅读菜单重新排入 480 像素高度，所有按键均可直接操作。人物名和章节提示分两行，剧情标准字号 22、大字号 26，长文本自动换行并可滑动。

沿用《纸上的魔法使》手环版已获维护者实机确认的字体处理：通常动态文本继承默认字体，不显式绑定 `sans-serif`；含罕用字的文本采用单独、静态指定的补充字体分支。对模拟器实际默认字体及包内字库重新核验覆盖，不将通用模拟器称为真实手环固件。

## 保留的功能

- **START**：正篇全部 9,424 段中文文本和 21 个章节入口。
- **AFTER STORY**：从 START 完成正篇后解锁，并出现在标题第一项。保留《渺茫希望的日记》正常流程 1,392 段源文本及 8 个章节入口；后日谈结束后返回标题。157 段重复尾声保留为历史数据兼容，正常后日谈不重复衔接；正篇终章继续保留。
- **SAVE / LOAD**：30 个独立栏位，自选栏位读取，覆盖前确认；手环旧版包名、存档、设置和通关记录键保持不变。手表版存档不自动迁移到手环。
- **CHAPTER**：路线和章节回看；第一页切换使用不同列表标识，避免目录内容卡住。菜单“下一章”遇到未作出的选项必须停下，重复点击也不能跳过。
- **EXTRA**：全部 256 组／394 张 CG，同场景差分归在一组，打开后点击图片切换，并支持前后组浏览。
- **CONFIG**：即时／逐字显示、标准／大字号。剧情文字保持白色，上方 CG 按比例显示，间隙用墨绿色渐变填充，299 张透明剧情立绘贴合文本框。
- **EXIT**：标题入口调用系统 `$app.exit()` 退出应用，退出前自行保存。

现有版本属于图文阅读移植，不含原作音频、视频及复杂动态演出。本次未删减现有剧情、选项、CG、差分或立绘；全部剧情块、图片、字体和原有存档模块与手环 0.1.1 逐字节一致，也没有再次降低立绘画质。证据见 `reports/band-v011-baseline.json` 和 `reports/package-audit-v012.json`。

## 自动播放

在正文打开“菜单”，点“自动播放：关闭”切换为开启，再点“返回游戏”。文字按约 **30 毫秒／字**显示，完成当前句后再等待：

| 档位 | 逐字完成后的等待 |
| --- | --- |
| 慢速 | 2.6 秒 |
| 标准（默认） | 1.5 秒 |
| 快速 | 0.8 秒 |

点击“自动速度”循环切换。超过 60 字时，每多一字增加 55 毫秒等待，最多额外 5 秒。选项必须由玩家选择，选完后自动继续。菜单、存读档、正文拖动和后台暂停推进；返回正文或滑动结束后重新等待。手动点击未显示完的正文会先补全当前句，完整显示后点击仍可推进；“上一句”关闭自动播放。

只保存速度档位，每次启动应用默认关闭自动播放。返回标题、剧情结束、报错、销毁或退出均取消自动计时；异步章节加载取消后不能重新弹回正文。

## 安装与异常处理

1. 使用[表盘自定义工具](https://www.bandbbs.cn/)传输 `星之终途-Band8Pro-0.1.2.bin`。同版 `.rpk` 与 `.bin` 字节相同，任选其一。
2. **手机传输结束后仍需等待手环完成安装并显示图标**，避免安装处理中连续重复上传。
3. 保留存档时优先尝试覆盖手环旧版；主动卸载通常会清除应用数据。安装前保存进度，并保留旧包和能够导出的备份。覆盖升级的数据保留仍需实机确认。
4. 若应用卡住，先通过手环返回操作离开，重新打开并读取较早栏位；必要时正常重启。反馈时附章节、触发操作、固件版本和包 SHA-256。
5. 若安装后暂未出现图标，先等待安装处理结束，再正常重启检查。恢复出厂设置会清空数据，不作为首选处理。

10 MB 指压缩安装包体积，不等于安装所需空间或运行 RAM。本应用使用普通 Vela 应用接口，不修改固件。

## 验证范围

28 项自动检查全部通过：全文顺序、章节入口、真实选项保护、存档与通关解锁，以及自动播放计时、长文延迟、菜单／后台／拖动暂停、选择后恢复、旧存档、速度持久化和异步加载取消。记录为 `reports/autoplay-tests-v012.tap`。

当前精确包通过内外签名、全部文件摘要和 CRC 检查，1,080 张图片均可解码，透明立绘和圆形图标正常，包内资源与源码一致。使用模拟器实际 `MiSansW_Normal.ttf` 重新检查默认和补充字体覆盖；该系统字库只用于验证，不随源码分发。

`native-test-results/band-v012/report.json` 绑定本包 SHA-256，记录独立安装、九项菜单、三档自动速度、真实应用重启后的 1／30 号存档读取、正篇解锁 AFTER STORY、目录第一页刷新、长文本两种字号与滑动、107:423 真实选项暂停／确认后继续、后日谈结束返回标题、CG 差分和系统退出。截图来自本版精确包，不使用旧版截图代替。

运行环境为官方通用 `vela-watch-5.0` 模拟器、336×480、128 MB；这不代表真实小米手环 8 Pro 固件或 RAM。首次虚拟屏幕为熄屏状态，发送一次虚拟 Power 键唤醒后进行检查。**本版没有小米手环实机通过记录。**

## 构建

需要 Node.js；Python 审计工具需要 Pillow、fontTools 和 cryptography。`src/` 已包含转换后的资源，可以直接构建。实际使用兼容编译器 **aiot-toolkit 1.1.0**，图像复制保真和兼容签名重封装不可省略。

```powershell
npm install --prefix tools/compat-toolkit --ignore-scripts
node --test tests/reader.test.cjs tests/auto-reader.test.cjs
node tools/build.cjs
python tools/audit-band-v012.py
```

可通过 `WATCH_COMPAT_TOOLKIT` 指向已有同版编译器。兼容工具链将 `sharp` 固定为 0.34.5，以支持当前 Windows / Node 环境；最终图片仍由构建后处理逐字节保留。`tools/audit-package.py` 可传入自行取得的默认字体路径，检查完整字形覆盖。测试环境脚本仅用于模拟器；本机测试的独立环境位于源码目录之外，不随安装包或源码压缩包分发。

原作：[《星之终途》Key 官网](https://key.visualarts.gr.jp/kinetic/stella/) · [Steam](https://store.steampowered.com/app/2510770/Stella_of_The_End/)。后日谈采用维护者提供的独立 Ren’Py 资源，不将其称为 Steam 官方 DLC；本项目为非官方适配。

参考《纸上的魔法使》手环版的布局和字体修复，并感谢 **@liuyuze61** 的[《ATRI》1.5.1 移植作品](https://api.bandbbs.cn/wftools/bandbbs.html?code=A&state=1820673)、[《星空列车与白的旅行》1.0.0 移植作品](https://api.bandbbs.cn/wftools/bandbbs.html?code=A&state=1841662)以及[表盘自定义工具相关团队](https://www.bandbbs.cn/)。

自编代码采用 MIT；原作文本、图像、标识与第三方字体保留各自许可，见 `THIRD_PARTY_NOTICES.md` 和 `licenses/`。

问题反馈与交流：[shining237841@gmail.com](mailto:shining237841@gmail.com)。
'''
(root / 'README.md').write_text(readme, 'utf8')
report = {'game': '星之终途', 'version': '0.1.2', 'device': 'Xiaomi Smart Band 8 Pro',
          'date': '2026-11-02', 'package': audit, 'directFontAndPackageAudit': font_audit,
          'automatedTests': {'passed': 28, 'failed': 0}, 'native': native,
          'allCurrentRW5Version024FunctionsRetained': True,
          'allStoryImagesAndFontsPreservedWithoutFurtherCompression': True,
          'physicalDeviceTested': False, 'physicalRetestPending': True}
created = []
for ext in ['bin', 'rpk']:
    target = out / (stem + '.' + ext)
    shutil.copyfile(package, target)
    created.append(target)
for suffix, text in [('-安装说明.md', readme), ('-检查报告.json', json.dumps(report, ensure_ascii=False, indent=2) + '\n')]:
    target = out / (stem + suffix)
    target.write_text(text, 'utf8')
    created.append(target)
for name, label in [('title-after-unlocked', '标题'), ('menu-auto-enabled', '自动播放菜单'), ('long-text-large', '长文本')]:
    target = out / (stem + '-' + label + '.png')
    shutil.copyfile(root / 'native-test-results/band-v012' / (name + '.png'), target)
    created.append(target)

reports = {'text-font.json', 'text-provenance.json', 'after-text-provenance.json',
           'after-story-baseline.json', 'after-choice-source.json', 'after-source-audit.json',
           'after-conversion.json', 'assets.json', 'conversion.json', 'band-v011-baseline.json',
           'package-audit.json', 'package-audit-v012.json', 'autoplay-tests-v012.tap',
           'ui-remake.json', 'title-complete-audit.json', 'native-band-v012.log'}
candidates = []
for folder in ['src', 'tests', 'licenses', 'tools', 'docs']:
    candidates.extend(p for p in (root / folder).rglob('*') if p.is_file()
                      and not {'node_modules', '__pycache__'}.intersection(p.relative_to(root).parts))
for name in ['README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'package.json',
             'quickapp.config.js', 'requirements.txt', '.gitignore', '.gitattributes']:
    p = root / name
    if p.is_file():
        candidates.append(p)
candidates += [root / 'reports' / name for name in reports if (root / 'reports' / name).is_file()]
candidates += [p for p in (root / 'native-test-results/band-v012').iterdir()
               if (p.suffix == '.png' and p.name != 'initial.png') or p.name == 'report.json']
source = out / (stem + '-源码.zip')
with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(set(candidates)):
        z.write(p, root.name + '/' + p.relative_to(root).as_posix())
assert source.stat().st_size < 25_000_000
with zipfile.ZipFile(source) as z:
    assert z.testzip() is None
    assert z.read(root.name + '/README.md') == (root / 'README.md').read_bytes()
created.append(source)
(out / (stem + '-SHA256.txt')).write_text(''.join(sha(p) + '  ' + p.name + '\n' for p in created), 'utf8')

# Update the organized, editable source after every required check has passed.
editable = project / '源码'
baseline = json.loads((root / 'reports/band-v011-baseline.json').read_text('utf8'))['files']
for name, previous_hash in baseline.items():
    previous = editable / name
    if previous.is_file():
        assert sha(previous) in [previous_hash, sha(root / name)], 'Unmerged editable source: ' + name
for p in sorted(set(candidates)):
    target = editable / p.relative_to(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, target)
index = project / '目录说明.md'
text = index.read_text('utf8') if index.exists() else '# 《星之终途》· 小米手环 8 Pro\n\n本地最终交付版本：0.1.2。\n'
text = text.replace('本地最终交付版本：0.1.1', '本地最终交付版本：0.1.2')
text += '\n0.1.2 保留当前手表版全部图文功能，安装包 9.87 MB，自动检查和原生模拟器通过，待手环实机复测。旧 0.1.1 交付文件继续保留。\n'
index.write_text(text, 'utf8')
index = project.parent / 'README.md'
if index.is_file():
    text = index.read_text('utf8').replace('| 星之终途 · Band 8 Pro | 0.1.1 |', '| 星之终途 · Band 8 Pro | 0.1.2 |')
    index.write_text(text, 'utf8')
print(json.dumps({'package': str(out / (stem + '.bin')), 'packageBytes': audit['bytes'],
                  'sha256': sha(package), 'sourceBytes': source.stat().st_size,
                  'nativePassed': True, 'physicalRetestPending': True}, ensure_ascii=False))
