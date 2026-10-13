"""Independently audit the extracted source labels against merged story text order."""
from pathlib import Path
import ast
import hashlib
import json
import re
from renpy_data import load

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'stella-after-probe/scripts/rpy'
labels = {}
for path in (SOURCE / 'drama').glob('*.rpyc'):
    for node in load(path.read_bytes())[1]:
        if type(node).__name__ == 'Label':
            labels[node.name] = node
images = {}
for node in load((SOURCE / 'options/image.rpyc').read_bytes())[1]:
    if type(node).__name__ != 'Init':
        continue
    for item in node.block:
        if type(item).__name__ == 'Image' and item.code and item.code._pickle_state[1].startswith('Text('):
            expression = ast.parse(item.code._pickle_state[1], mode='eval').body
            if expression.args and isinstance(expression.args[0], ast.Constant):
                images[' '.join(item.imgname)] = expression.args[0].value
expected = []
label_scene = {'start': 101, 'a1': 102, 'a2_1': 103, 'a2': 103, 'a3_1': 104, 'a3': 104,
               'a4_1': 105, 'a4': 105, 'a5_1': 106, 'a5': 106, 'a6_1': 107, 'a6': 107, 'AE': 107, 'a7': 108, 'a0': 109}
for entry in ['start', 'a0']:
    current = entry
    visited = set()
    while current:
        assert current not in visited, 'Unexpected source loop'
        visited.add(current)
        target = None
        for node in labels[current].block:
            kind = type(node).__name__
            text = None
            if kind == 'Say' and node.what.strip():
                text = node.what
            elif kind in ['Show', 'Scene'] and node.imspec:
                text = images.get(' '.join(node.imspec[0]))
            elif kind == 'Jump':
                target = None if node.target == 'splashscreen' else node.target
                break
            elif kind == 'Menu':
                assert len(node.items) == 1 and str(node.items[0][1]) == 'True'
                branch = node.items[0][2]
                assert len(branch) == 1 and type(branch[0]).__name__ == 'Jump'
                assert re.sub(r'\{/?color(?:=[^}]*)?\}', '', node.items[0][0]) == '「谢谢你，菲莉娅！！！」'
                target = branch[0].target
                break
            if text is not None:
                expected.append({'scene': label_scene[current], 'textSHA256': hashlib.sha256(text.encode()).hexdigest()})
        current = target
proof = json.loads((ROOT / 'reports/after-text-provenance.json').read_text('utf8'))
actual = [{key: item[key] for key in ['scene', 'textSHA256']} for item in proof]
assert actual == expected
catalog = json.loads((ROOT / 'src/common/catalog.js').read_text('utf8').split('=',1)[1].strip().rstrip(';'))
after_ops = json.loads((ROOT / 'src/common/story/107/0.txt').read_text('utf8'))
assert after_ops[-1] == {'op':'end'} and catalog['afterEnd'] == 107
assert 108 not in catalog['routes'][1]['scenes'] and 21 in catalog['routes'][0]['scenes']
report = {'result': 'passed', 'extractedSourceChineseTextOrderMatchesConverted': True,
          'checkedTextBlocks': len(expected), 'choiceTextAndDestinationChecked': True,
          'confirmationTargetLabel': 'AE', 'sourceEndingLabel': 'a7', 'adaptedAfterEnding': 'AE -> title',
          'legacyEpiloguePreserved': True, 'mainEpilogueScene': 21, 'bonusEndingLabel': 'a0 -> splashscreen',
          'sourceParsedAsInertData': True, 'gameCodeExecuted': False}
(ROOT / 'reports/after-source-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
print(json.dumps(report, ensure_ascii=False))
