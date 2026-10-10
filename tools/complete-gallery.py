"""Add shipped extra still variants to an already converted build, without rerunning story conversion."""
from pathlib import Path
import os,json,io,hashlib,re
from PIL import Image,ImageOps
from pfs import index,payload
root=Path(__file__).resolve().parents[1];common=root/'src/common';reports=root/'reports'
if not os.environ.get('STELLA_GAME_ROOT'):raise SystemExit('Set STELLA_GAME_ROOT to your own Steam game directory before converting.')
game=Path(os.environ['STELLA_GAME_ROOT']).expanduser().resolve()
gallery=json.loads((common/'gallery.txt').read_text('utf8'));covered={x['source'] for x in gallery}
report=json.loads((reports/'conversion.json').read_text('utf8'));assetReport=json.loads((reports/'assets.json').read_text('utf8'))
js=(common/'assets.js').read_text('utf8');assets=json.loads(js.split('export const assets=')[1].split(';\n')[0])
def stable(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
for arc in sorted(game.glob('*.pfs*')):
    es,key=index(arc)
    for e in es:
        n=e['name'].lower();f=Path(n).stem
        if not n.startswith('image/ev/') or not n.endswith('.png') or f in covered:continue
        group='ts'+re.match(r'cg_ts(\d+)',f).group(1)
        layers=[{'source':n,'base':True,'alpha':255,'x':0,'y':0}];identifier='b_'+hashlib.sha256(stable(layers).encode()).hexdigest()[:20];filename=identifier+'.jpg'
        if identifier not in assets:
            im=Image.open(io.BytesIO(payload(arc,e,key)));im=ImageOps.fit(im,(320,180),Image.Resampling.LANCZOS).convert('RGB');dest=common/'images'/filename;im.save(dest,quality=76,optimize=True,progressive=False)
            assets[identifier]=filename;assetReport.append({'id':identifier,'file':filename,'kind':'b','size':list(im.size),'bytes':dest.stat().st_size})
        gallery.append({'group':group,'image':identifier,'source':f,'label':'CG '+group[2:]});covered.add(f)
report.update(galleryEntries=len(gallery),resources=len(assets),backgroundCompositions=len([a for a in assetReport if a['kind']=='b']),resourceBytes=sum(a['bytes'] for a in assetReport));report['allShippedEventCGStillsIncluded']=True
for p,v in [(common/'gallery.txt',gallery),(reports/'conversion.json',report),(reports/'assets.json',assetReport)]:p.write_text(stable(v),encoding='utf8')
(common/'assets.js').write_text('export const assets='+stable(assets)+';\n'+js.split(';\n',1)[1],encoding='utf8')
print('GALLERY',len(gallery),'RESOURCES',len(assets),report['resourceBytes'])
