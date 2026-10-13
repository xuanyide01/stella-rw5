"""Merge the provided Ren'Py after-story through data-only RPYC/RPA readers.

STELLA_AFTER_ROOT points to the directory containing game/archive.rpa.
The executable, Python statements, screens, music and video are never run.
"""
from pathlib import Path
from functools import lru_cache
import ast
import collections
import hashlib
import io
import json
import os
import re
from PIL import Image, ImageOps
from rpa_data import index, payload
from renpy_data import load, Node

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / 'src/common'
REPORTS = ROOT / 'reports'
GAME = Path(os.environ['STELLA_AFTER_ROOT']).resolve()
ARCHIVE = GAME / 'game/archive.rpa'
ENTRIES = index(ARCHIVE)
stable = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
catalog = json.loads((COMMON / 'catalog.js').read_text('utf8').removeprefix('export const catalog=').strip().removesuffix(';'))
assets = json.loads((COMMON / 'assets.js').read_text('utf8').split('export const assets=', 1)[1].split(';', 1)[0])
layout_path = COMMON / 'portrait-layout.js'
layout = layout_path.read_text('utf8')
dimensions = json.loads(layout.split('const dimensions=', 1)[1].split(';', 1)[0])
asset_report = [item for item in json.loads((REPORTS / 'assets.json').read_text('utf8')) if not item['id'].startswith('as_')]
gallery = [item for item in json.loads((COMMON / 'gallery.txt').read_text('utf8')) if not item['group'].startswith('after:')]
asts = {Path(name).stem: load(payload(ARCHIVE, rows))[1] for name, rows in ENTRIES.items()
        if name.startswith('rpy/drama/') and name.endswith('.rpyc')}
image_nodes = load(payload(ARCHIVE, ENTRIES['rpy/options/image.rpyc']))[1]
labels = {}
for nodes in asts.values():
    for node in nodes:
        if type(node).__name__ == 'Label':
            assert node.name not in labels
            labels[node.name] = node

def walk(nodes):
    for node in nodes:
        yield node
        if hasattr(node, 'block'):
            yield from walk(node.block)

def literal_source(code):
    if code is None:
        return None
    source = code._pickle_state[1]
    try:
        value = ast.literal_eval(source)
        return value if isinstance(value, str) else None
    except (ValueError, SyntaxError):
        return None

image_definitions = {}
text_definitions = {}
movie_names = set()
for node in walk(image_nodes + [node for nodes in asts.values() for node in nodes]):
    if type(node).__name__ != 'Image':
        continue
    name = ' '.join(node.imgname)
    source = literal_source(node.code)
    if source:
        image_definitions[name] = source
    elif node.code and node.code._pickle_state[1].startswith('Text('):
        expression = ast.parse(node.code._pickle_state[1], mode='eval').body
        if isinstance(expression, ast.Call) and expression.args and isinstance(expression.args[0], ast.Constant) and isinstance(expression.args[0].value, str):
            text_definitions[name] = expression.args[0].value
    elif node.code and 'Movie(' in node.code._pickle_state[1]:
        movie_names.add(name)
    elif node.atl:
        for statement in node.atl.statements:
            for expression in getattr(statement, 'expressions', []):
                try:
                    source = ast.literal_eval(str(expression[0]))
                except (ValueError, SyntaxError):
                    continue
                if isinstance(source, str) and source in ENTRIES:
                    image_definitions[name] = source
                    break
            if name in image_definitions:
                break

auto_images = {}
for name in ENTRIES:
    if name.startswith(('images/', 'image/')) and Path(name).suffix in ['.png', '.jpg', '.bmp']:
        for alias in [Path(name).stem, Path(name).stem.replace('_', ' ')]:
            auto_images.setdefault(alias, []).append(name)

def resolve(name):
    if name in movie_names:
        return None
    if name in image_definitions:
        assert image_definitions[name] in ENTRIES, image_definitions[name]
        return image_definitions[name]
    matches = auto_images.get(name, [])
    if len(set(matches)) == 1:
        return matches[0]
    if name == 'black':
        return ':black'
    raise ValueError('Unresolved or ambiguous image: ' + name + ' ' + str(matches))

@lru_cache(maxsize=18)
def image(source):
    if source == ':black':
        return Image.new('RGBA', (1920, 1080), '#000000')
    im = Image.open(io.BytesIO(payload(ARCHIVE, ENTRIES[source])))
    im.load()
    return im

def save_asset(im, kind, key):
    identifier = 'as_' + kind + '_' + hashlib.sha256(key.encode()).hexdigest()[:20]
    if identifier in assets:
        return identifier
    if kind == 'p':
        im = im.convert('RGBA')
        im.thumbnail((200, 256), Image.Resampling.LANCZOS)
        im = im.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
        filename = identifier + '.png'
        im.save(COMMON / 'images' / filename, optimize=True, compress_level=9)
        dimensions[filename] = list(im.size)
    else:
        im = im.convert('RGB')
        im.thumbnail((320, 180), Image.Resampling.LANCZOS)
        filename = identifier + '.jpg'
        im.save(COMMON / 'images' / filename, quality=76, optimize=True, progressive=False)
    assets[identifier] = filename
    asset_report.append({'id': identifier, 'file': filename, 'kind': kind, 'size': list(im.size),
                         'bytes': (COMMON / 'images' / filename).stat().st_size})
    return identifier

background_cache = {}
portrait_cache = {}
used_sources = set()
omitted = collections.Counter()
def portrait(source):
    if source in portrait_cache:
        return portrait_cache[source]
    im = image(source).convert('RGBA')
    box = im.getchannel('A').getbbox()
    if not box:
        raise ValueError('Empty portrait: ' + source)
    im = im.crop(box)
    im = im.crop((0, 0, im.width, max(1, round(im.height * .78))))
    result = save_asset(im, 'p', source)
    portrait_cache[source] = result
    return result

def snapshot(layers):
    visible = [layer for layer in layers.values() if not layer['name'].startswith('philia')]
    key = stable(visible)
    if key in background_cache:
        return background_cache[key]
    canvas = Image.new('RGBA', (320, 180), '#000000')
    for i, layer in enumerate(visible):
        im = image(layer['source']).convert('RGBA')
        if i == 0 or im.width / im.height >= 1.65:
            # Preserve the complete 16:9 illustration instead of replaying camera zooms.
            im = ImageOps.contain(im, (320, 180), Image.Resampling.LANCZOS)
            canvas.alpha_composite(im, ((320 - im.width) // 2, (180 - im.height) // 2))
        else:
            im.thumbnail((320, 180), Image.Resampling.LANCZOS)
            canvas.alpha_composite(im, ((320 - im.width) // 2, (180 - im.height) // 2))
    result = save_asset(canvas, 'b', key)
    background_cache[key] = result
    return result

order = [('start', 101, '后日谈 · 阅读说明'), ('a1', 102, '后日谈 · 第一章'),
         ('a2', 103, '后日谈 · 第二章'), ('a3', 104, '后日谈 · 第三章'),
         ('a4', 105, '后日谈 · 第四章'), ('a5', 106, '后日谈 · 第五章'),
         ('a6', 107, '后日谈 · 第六章'), ('a7', 108, '原作尾声 · 旧版兼容'),
         ('a0', 109, '后日谈 · 附加故事')]
label_to_scene = {name: identifier for name, identifier, title in order}
label_to_scene.update({name + '_1': identifier for name, identifier, title in order if name in ['a2', 'a3', 'a4', 'a5', 'a6']})
label_to_scene['AE'] = 107
proof = []
choices = []
counts = collections.Counter()
scene_lengths = {}
layers = collections.OrderedDict()

def clean_text(value):
    return re.sub(r'\{/?(?:color|size|font|b|i|u|cps|w|p|nw|fast)(?:=[^}]*)?\}', '', value)

for label, scene, title in order:
    if label in ['start', 'a0']:
        layers.clear()
    ops = []
    local_offsets = {}
    deferred_choices = []
    def process(nodes):
        for node in nodes:
            kind = type(node).__name__
            counts[kind] += 1
            if kind == 'Say':
                text = clean_text(node.what)
                if not text.strip():
                    omitted['empty_nvl_pause'] += 1
                    continue
                bg = snapshot(layers)
                bodies = [portrait(layer['source']) for layer in layers.values() if layer['name'].startswith('philia')][:3]
                ops.append({'op': 'text', 'speaker': '', 'text': text, 'background': bg, 'bodies': bodies})
                proof.append({'scene': scene, 'cursor': len(ops) - 1, 'file': Path(node.filename).name,
                              'line': node.linenumber, 'textSHA256': hashlib.sha256(text.encode()).hexdigest()})
            elif kind in ['Scene', 'Show']:
                if kind == 'Scene':
                    layers.clear()
                if not node.imspec:
                    continue
                name = ' '.join(node.imspec[0])
                if name in text_definitions:
                    text = clean_text(text_definitions[name])
                    ops.append({'op': 'text', 'speaker': '', 'text': text, 'background': snapshot(layers), 'bodies': []})
                    proof.append({'scene': scene, 'cursor': len(ops) - 1, 'file': Path(node.filename).name,
                                  'line': node.linenumber, 'kind': 'imageText', 'textSHA256': hashlib.sha256(text.encode()).hexdigest()})
                    continue
                source = resolve(name)
                if source is None:
                    omitted['movie'] += 1
                    ops.append({'op': 'text', 'speaker': '', 'text': '（后日谈片尾动画在手表图文版中省略，点击继续返回标题。）', 'background': snapshot(layers), 'bodies': []})
                    continue
                used_sources.add(source)
                tag = node.imspec[2] or node.imspec[0][0]
                layers[tag] = {'name': name, 'source': source}
                if node.atl or node.imspec[3]:
                    omitted['camera_animation_transform'] += 1
            elif kind == 'Hide':
                if node.imspec:
                    layers.pop(node.imspec[2] or node.imspec[0][0], None)
            elif kind == 'Jump':
                assert not node.expression
                if node.target in ['splashscreen', 'a7']:
                    # a7 repeats the original main-game epilogue. Keep its data
                    # for old saves, but finish AFTER STORY before that reprise.
                    ops.append({'op': 'end'})
                elif label_to_scene.get(node.target) == scene:
                    # Introductory chapter-card label proceeds into its own chapter body.
                    assert node.target == label or node.target in local_offsets
                else:
                    assert node.target in label_to_scene, node.target
                    ops.append({'op': 'jumpScene', 'scene': label_to_scene[node.target], 'to': 0})
            elif kind == 'Menu':
                items = []
                for caption, condition, branch in node.items:
                    assert str(condition) == 'True' and len(branch) == 1 and type(branch[0]).__name__ == 'Jump'
                    target = branch[0].target
                    assert label_to_scene[target] == scene
                    item = {'text': clean_text(caption), 'to': -1}
                    items.append(item)
                    deferred_choices.append((item, target))
                ops.append({'op': 'choice', 'items': items})
                choices.append({'scene': scene, 'cursor': len(ops) - 1, 'sourceFile': Path(node.filename).name,
                                'line': node.linenumber, 'items': [dict(item, target=target) for item, (_, target) in zip(items, deferred_choices[-len(items):])]})
            elif kind == 'If':
                # These conditions control achievements and a language-specific UI popup only.
                assert all(str(condition).startswith('not persistent.unlock_ach') or str(condition) in ['config.language == None', 'config.language == "Japanese"'] for condition, block in node.entries)
                assert not any(type(child).__name__ in ['Say', 'Jump', 'Menu'] for condition, block in node.entries for child in block)
                omitted['achievement_or_language_popup'] += 1
            elif kind == 'Return':
                ops.append({'op': 'end'})
            elif kind in ['Python', 'UserStatement', 'With', 'Init']:
                omitted[kind] += 1
            else:
                raise ValueError('Unhandled story syntax: ' + kind)
    if label in ['a2', 'a3', 'a4', 'a5', 'a6']:
        process(labels[label + '_1'].block)
    process(labels[label].block)
    if label == 'a6':
        local_offsets['AE'] = len(ops)
        process(labels['AE'].block)
    for item, target in deferred_choices:
        item['to'] = local_offsets[target]
    if not ops or ops[-1]['op'] not in ['jumpScene', 'end']:
        ops.append({'op': 'end'})
    scene_lengths[scene] = len(ops)
    for start in range(0, len(ops), 512):
        dest = COMMON / 'story' / str(scene) / (str(start // 512) + '.txt')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(stable(ops[start:start + 512]), 'utf8')
    catalog['scenes'][str(scene)] = {'name': title, 'length': len(ops)}
    print('AFTER_CHAPTER', scene, len(ops), flush=True)

assert len(choices) == 1 and len(choices[0]['items']) == 1
for choice in choices:
    op = json.loads((COMMON / 'story' / str(choice['scene']) / (str(choice['cursor'] // 512) + '.txt')).read_text('utf8'))[choice['cursor'] % 512]
    choice['items'] = op['items']
catalog['afterInitial'] = 101
catalog['afterEnd'] = 107
catalog['routes'] = [catalog['routes'][0], {'name': 'AFTER STORY · 渺茫希望的日记', 'scenes': [scene for label, scene, title in order if scene != 108]}]
catalog['chapters'] = [entry for entry in catalog['chapters'] if entry['route'] == 0] + [
    {'id': scene, 'name': title, 'route': 1} for label, scene, title in order if scene != 108]
catalog['endings'].update({'107': 'AFTER STORY', '108': '原作尾声 · 旧版兼容', '109': '后日谈附加故事'})
(COMMON / 'catalog.js').write_text('export const catalog=' + stable(catalog) + ';\n', 'utf8')

# Gallery uses only the story's actual static illustrations, with related differences grouped.
for source in sorted(used_sources):
    if source.startswith(':') or source.startswith(('gui/', 'image/ef', 'image/wipes')) or Path(source).stem.startswith(('te', 'philia', 'endlogo', 'white')):
        continue
    im = image(source).convert('RGBA')
    if im.width < 400 or im.height < 200 or im.getchannel('A').getextrema()[0] == 0:
        continue
    key = 'after-gallery:' + source
    asset = save_asset(ImageOps.contain(im, (320, 180), Image.Resampling.LANCZOS), 'b', key)
    stem = Path(source).stem
    group = 'after:' + re.sub(r'(?:_\d+|_patch\d*)$', '', stem)
    gallery.append({'group': group, 'image': asset, 'source': source, 'label': '后日谈 · ' + stem})

(COMMON / 'assets.js').write_text('export const assets=' + stable(assets) + ';\nexport function imagePath(name){return assets[name]?\'/common/images/\'+assets[name]:\'/common/title_bg.png\';}\n', 'utf8')
layout_path.write_text('const dimensions=' + stable(dimensions) + ';' + layout.split(';', 1)[1], 'utf8')
(COMMON / 'gallery.txt').write_text(stable(gallery), 'utf8')
(REPORTS / 'assets.json').write_text(stable(asset_report), 'utf8')
(REPORTS / 'after-text-provenance.json').write_text(stable(proof), 'utf8')
(REPORTS / 'after-choice-source.json').write_text(json.dumps(choices, ensure_ascii=False, indent=2), 'utf8')
report = {'sourceEngine': 'RenPy RPYC2 / RPA3 data only', 'archiveBytes': ARCHIVE.stat().st_size,
          'compiledStorySHA256': {name: hashlib.sha256(payload(ARCHIVE, rows)).hexdigest() for name, rows in ENTRIES.items() if name.startswith('rpy/drama/') and name.endswith('.rpyc')},
          'afterChapters': 8, 'mainAfterTextBlocks': sum(item['scene'] not in [108,109] for item in proof),
          'legacyEpilogueTextBlocks': sum(item['scene'] == 108 for item in proof),
          'endingAdaptation': 'AE finishes at scene 107 and returns to title; a7 reprises main epilogue and is kept only for historical saves. Main scene 21 is unchanged.',
          'bonusTextBlocks': sum(item['scene'] == 109 for item in proof), 'convertedTextBlocks': len(proof),
          'choices': 1, 'choiceItems': 1, 'storyNodeCounts': dict(counts), 'omittedEffects': dict(omitted),
          'newResourceBytes': sum(item['bytes'] for item in asset_report if item['id'].startswith('as_')),
          'afterGalleryImages': sum(item['group'].startswith('after:') for item in gallery),
          'renpyPythonExecuted': False, 'executableLaunched': False,
          'limitations': ['Audio and video omitted, including ending animation.', 'Camera movement, zoom, visual filters and timed transitions reduced to static compositions.',
                         'Achievement flags and language-choice popups do not affect the Chinese story and are not emulated.', 'Original NVL text keeps no explicit speaker label.']}
(REPORTS / 'after-conversion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
conversion_path = REPORTS / 'conversion.json'
conversion = json.loads(conversion_path.read_text('utf8'))
conversion.setdefault('originalGalleryGroups', conversion['galleryGroups'])
conversion.setdefault('originalGalleryEntries', conversion['galleryEntries'])
conversion.update(galleryGroups=len({item['group'] for item in gallery}), galleryEntries=len(gallery),
                  afterStory=report)
conversion_path.write_text(json.dumps(conversion, ensure_ascii=False, indent=2) + '\n', 'utf8')
for file, sha in json.loads((REPORTS / 'after-story-baseline.json').read_text('utf8'))['files'].items():
    assert hashlib.sha256((ROOT / file).read_bytes()).hexdigest() == sha
print('AFTER_CONVERSION', stable(report))
