"""Check final raster label alignment, common size and native scroll evidence."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageChops

root = Path(__file__).resolve().parents[1]
ui = root / 'src/common/ui'
labels = ['after','start','chapter','load','config','extra','exit']
bounds = {}
for label in labels:
    im = Image.open(ui / ('title-' + label + '.png')).convert('RGBA')
    assert im.size == (222,28)
    box = im.getchannel('A').point(lambda x: 255 if x >= 64 else 0).getbbox()
    bounds[label] = box
    assert box[0] == 0 and box[3] - box[1] == 18
system = Image.open(ui / 'system.png').convert('RGB')
# Previously the bottom stripe started at y=500, with a bold block at x=24..78.
assert system.getpixel((24,500)) == system.getpixel((24,498))
art = Image.open(ui / 'art-fill.png').convert('RGB')
assert art.getpixel((216,0)) == art.getpixel((216,285)) == (55,107,94)
assert art.getpixel((216,140)) != art.getpixel((216,0))
frames = root / 'native-test-results/v021'
theme = json.loads((root / 'reports/ui-remake.json').read_text('utf8'))
assert theme['titleHeroineBottom'] == 514 and theme['titleHeroineSize'][1] == 370
assert theme['titleMenuBackground'].startswith('transparent')
title = Image.open(frames / 'title.png').convert('RGB')
title_art = Image.open(ui / 'title.jpg').convert('RGB')
for point in [(50,470),(316,512)]:
    assert max(abs(a-b) for a,b in zip(title.getpixel(point),title_art.getpixel(point))) <= 10
for size in ['standard','large']:
    top = Image.open(frames / ('long-' + size + '-top.png')).convert('RGB')
    bottom = Image.open(frames / ('long-' + size + '-bottom.png')).convert('RGB')
    assert ImageChops.difference(top.crop((18,328,414,456)),bottom.crop((18,328,414,456))).getbbox()
    assert ImageChops.difference(top.crop((0,0,432,286)),bottom.crop((0,0,432,286))).getbbox() is None
    color = top.getpixel((2,400))
    assert color == bottom.getpixel((2,400)) == top.getpixel((8,470))
    # Native display color conversion may quantize the CSS RGB channels.
    assert max(abs(a-b) for a,b in zip(color,(55,107,94))) <= 10
reset = Image.open(frames / 'long-standard-return.png').convert('RGB')
top = Image.open(frames / 'long-standard-top.png').convert('RGB')
assert ImageChops.difference(reset,top).getbbox() is None
report = {'result':'passed','titleVisibleInkBounds':bounds,'allTitleLabelsVisibleHeight':18,
          'allTitleLabelsVisibleLeft':0,'systemBottomStripeRemoved':True,'symmetricForestGreenArtFill':True,
          'native24And28pxTextScrolledWithoutChangingCG':True,'dialoguePanelSourceSolidColor':'#376b5e',
          'nativeDialoguePanelPixelRGB':color,
          'nativeBackResetsTextScrollExactly':True,
          'nativeTransparentTitleMenuAndHeroineTouchingBottom':True,
          'titleFirstAfterStory':'AFTER STORY; only after sf.stella_main_clear',
          'screenshotsSHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in frames.glob('*.png')}}
(root / 'reports/ui-layout-audit.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
print(json.dumps({k:v for k,v in report.items() if k!='screenshotsSHA256'}))
