"""Audit the exact signed package, original PNG bytes, decoded images and fonts."""
import sys,json,io,re,hashlib,zipfile
from pathlib import Path
from PIL import Image
from fontTools.ttLib import TTFont

root=Path(__file__).resolve().parents[1]
from rpk_signature import audit

manifest=json.loads((root/'src/manifest.json').read_text('utf8'))
package=root/'dist'/f'{manifest["package"]}.debug.{manifest["versionName"]}.rpk'
report=audit(package)
assert report['bytes']<=10000000
z=zipfile.ZipFile(package)
assert json.loads(z.read('manifest.json'))['package']=='com.codex.stella.band8pro'
watch=json.loads(z.read('manifest-watch.json'))
assert watch==manifest,'Watch-specific manifest does not match the source manifest'
images=0;pngs=0
for name in z.namelist():
    if name.endswith('/'):continue
    if name.startswith('common/'):
        source=root/'src'/name
        assert source.exists() and z.read(name)==source.read_bytes(),name
    if name.endswith(('.png','.jpg')):
        im=Image.open(io.BytesIO(z.read(name)));im.load();images+=1
        if '/images/' in name:assert im.width<=320 and im.height<=256,name
        if name.endswith('.png'):
            pngs+=1
            if '/images/' in name:assert im.mode in ['RGBA','P'] and im.convert('RGBA').getchannel('A').getextrema()[0]==0,name
logo=Image.open(io.BytesIO(z.read('common/logo.png')))
assert logo.size==(192,192) and logo.mode=='RGBA'
assert all(logo.getpixel(pt)[3]==0 for pt in [(0,0),(191,0),(0,191),(191,191)])
default_path=Path(sys.argv[1]) if len(sys.argv)>1 else root.parent/'clannad-probe/native-default-font.ttf'
default=TTFont(default_path).getBestCmap()
extra=TTFont(io.BytesIO(z.read('common/stella-extra.otf'))).getBestCmap()
triggers=set(json.loads((root/'reports/text-font.json').read_text('utf8'))['missingDefaultGlyphs'])
strings=[]
def visit(v):
    if isinstance(v,str):strings.append(v.replace('・','·'))
    elif isinstance(v,list):
        for item in v:visit(item)
    elif isinstance(v,dict):
        for item in v.values():visit(item)
for name in z.namelist():
    if name.startswith('common/story/') and name.endswith('.txt'):visit(json.loads(z.read(name)))
visit(json.loads(z.read('common/gallery.txt')))
for s in strings:
    cmap=extra if triggers.intersection(s) else default
    assert all(ch.isspace() or ord(ch)<32 or ord(ch) in cmap for ch in s),repr(s)
report.update({'watchManifestPresentAndCorrect':True,'decodedImages':images,'preservedPNGs':pngs,'allCommonResourcesMatchSource':True,'circularRGBAIcon':True,'textFontCoverageValid':True,'physicalDeviceTested':False})
(root/'reports/package-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
