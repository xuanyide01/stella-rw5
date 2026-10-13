"""Rebuild the watch interface from the original title art and button glyphs."""
from pathlib import Path
import hashlib
import json
import os
import io
from PIL import Image, ImageOps, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'stella-after-probe/original-ui/pc/cn'
UI = ROOT / 'src/common/ui'
UI.mkdir(exist_ok=True)
ink = (19, 66, 57)
originals = {}
archive_resources = {}
if os.environ.get('STELLA_GAME_ROOT'):
    from pfs import index, payload
    for archive in sorted(Path(os.environ['STELLA_GAME_ROOT']).glob('*.pfs*')):
        entries, key = index(archive)
        for entry in entries:
            if entry['name'].startswith('pc/cn/'):
                archive_resources[entry['name']] = (archive, entry, key)
def read(name):
    path = SOURCE / name
    if archive_resources:
        archive, entry, key = archive_resources['pc/cn/' + name]
        raw = payload(archive, entry, key)
    else:
        raw = path.read_bytes()
    originals[name] = hashlib.sha256(raw).hexdigest()
    return Image.open(io.BytesIO(raw)).convert('RGBA')

# The requested normal title illustration is independently fitted to the watch;
# char01 sits to the right, below the logo. No opaque menu panel is painted in.
sky = ImageOps.fit(read('title/bg.png'), (432, 514), Image.Resampling.LANCZOS, centering=(.63, .45))
hero = read('title/char01.png')
hero = hero.crop((900, 0, hero.width, hero.height))
hero = hero.crop(hero.getchannel('A').getbbox())
hero_height = 370
hero = hero.resize((round(hero.width * hero_height / hero.height), hero_height), Image.Resampling.LANCZOS)
hero_position = (160, 514 - hero.height)
sky.alpha_composite(hero, hero_position)
sky.convert('RGB').save(UI / 'title.jpg', quality=89, optimize=True)
logo = read('title/logo.png')
logo = logo.crop(logo.getchannel('A').getbbox())
logo.thumbnail((352, 135), Image.Resampling.LANCZOS)
logo.save(UI / 'title-logo.png', optimize=True)

sheet = read('title/btn.png')
glyphs = {}
labels = ['START', 'CHAPTER', 'LOAD', 'CONFIG', 'EXTRA', 'EXIT']
button_lefts = {}
button_heights = {}
button_scale = 0.62

def write_button(label, raw):
    # Original sheets contain almost-transparent padding; align visible ink,
    # including AFTER STORY, rather than merely aligning equal-sized images.
    alpha = raw.getchannel('A').point(lambda value: value if value >= 32 else 0)
    raw.putalpha(alpha)
    box = alpha.getbbox()
    # All original title rows share a 17..46 px baseline. Use one common
    # scale, even for the longest word; never fit each label separately.
    raw = raw.crop((box[0], 16, box[2], 47))
    raw = raw.resize((round(raw.width * button_scale), round(31 * button_scale)), Image.Resampling.LANCZOS)
    alpha = raw.getchannel('A')
    visible = alpha.point(lambda value: 255 if value >= 64 else 0).getbbox()
    raw = raw.crop(visible)
    tinted = Image.new('RGBA', raw.size, ink + (255,))
    tinted.putalpha(raw.getchannel('A'))
    button = Image.new('RGBA', (222, 28))
    button.alpha_composite(tinted, (0, (28 - tinted.height) // 2))
    button.save(UI / ('title-' + label + '.png'), optimize=True)
    button_lefts[label] = button.getchannel('A').point(lambda value: 255 if value >= 64 else 0).getbbox()[0]
    button_heights[label] = tinted.height
    assert tinted.width <= 222

for i, label in enumerate(labels):
    row = sheet.crop((0, i * 64, 272, i * 64 + 64))
    alpha = row.getchannel('A')
    solid = alpha.point(lambda value: 255 if value >= 100 else 0)
    occupied = [solid.crop((x, 0, x + 1, 64)).getbbox() is not None for x in range(272)]
    spans = []
    start = None
    for x, on in enumerate(occupied + [False]):
        if on and start is None:
            start = x
        elif not on and start is not None:
            spans.append((start, x))
            start = None
    assert len(spans) == len(label), (label, spans)
    for char, (x0, x1) in zip(label, spans):
        glyph = row.crop((x0, 0, x1, 64))
        if char not in glyphs:
            glyphs[char] = glyph
    write_button(label.lower(), row)

# The six title words have no Y. Reuse the original dialog's YES glyph.
yes_y = read('mw/dialog.png').crop((205, 213, 245, 255))
mask = yes_y.convert('L').point(lambda value: max(0, min(255, round((192 - value) * 255 / 192))))
box = mask.point(lambda value: 255 if value >= 100 else 0).getbbox()
assert box
mask = mask.crop(box)
reference = glyphs['T'].getchannel('A').point(lambda value: 255 if value >= 100 else 0).getbbox()
height = reference[3] - reference[1]
mask = mask.resize((round(mask.width * height / mask.height), height), Image.Resampling.LANCZOS)
letter = Image.new('RGBA', (mask.width, 64))
colored = Image.new('RGBA', mask.size, ink + (255,))
colored.putalpha(mask)
letter.alpha_composite(colored, (0, reference[1]))
glyphs['Y'] = letter

word = 'AFTER STORY'
width = sum(glyphs[char].width if char != ' ' else 18 for char in word) + 8 * (len(word) - 1)
raw = Image.new('RGBA', (width, 64))
x = 0
for char in word:
    if char == ' ':
        x += 26
        continue
    raw.alpha_composite(glyphs[char], (x, 0))
    x += glyphs[char].width + 8
write_button('after', raw)
assert set(button_lefts.values()) == {0}

art = Image.new('RGB', (432, 286))
draw = ImageDraw.Draw(art)
for y in range(286):
    # Match both letterbox edges to the dialogue's solid, muted forest green.
    t = 1 - abs(2 * y / 285 - 1)
    color = tuple(round(a + (b - a) * t) for a, b in zip((55, 107, 94), (17, 62, 53)))
    draw.line((0, y, 431, y), fill=color)
art.save(UI / 'art-fill.png', optimize=True)
# Kept for reproducible historical paths; current panel uses its CSS solid color.
Image.new('RGB', (432, 228), '#376b5e').save(UI / 'dialogue.png', optimize=True)
system = Image.new('RGB', (432, 514), '#f4f8f5')
draw = ImageDraw.Draw(system)
for x in range(18, 432, 32):
    draw.line((x, 0, x, 514), fill='#e8efeb')
for y in range(0, 514, 32):
    draw.line((0, y, 432, y), fill='#e8efeb')
system.save(UI / 'system.png', optimize=True)
report = {'theme': 'original sky and normal-title character on right; white / forest green system panels',
          'titleBackground': 'Original sky and char01 heroine crop; enlarged on right, below logo and touching bottom',
          'titleHeroinePosition': list(hero_position), 'titleHeroineSize': list(hero.size),
          'titleHeroineBottom': hero_position[1] + hero.height,
          'titleMenuBackground': 'transparent; no white panel or panel decoration',
          'dialogueText': '#ffffff', 'dialogueBackground': '#376b5e solid',
          'artLetterbox': 'symmetric forest-green gradient; CG remains contain', 'systemBottomDecoration': False,
          'titleVisibleInkLeftPixels': button_lefts,
          'titleCommonSourceScale': button_scale, 'titleVisibleInkHeights': button_heights,
          'titleLeftAlignment': True, 'titleLabels': ['AFTER STORY', 'START', 'CHAPTER', 'LOAD', 'CONFIG', 'EXTRA', 'EXIT'],
          'afterStoryUnlock': 'sf.stella_main_clear; completed START flow; hidden and menu collapses before clear',
          'originalResourceSHA256': originals, 'titleButtonOrigins': 'Six original raster button rows; AFTER STORY assembled from their glyphs plus Y from the original YES dialog.',
          'screen': [432, 514], 'uiAssetBytes': sum(path.stat().st_size for path in UI.iterdir())}
(ROOT / 'reports/ui-remake.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
print(json.dumps(report, ensure_ascii=False))
