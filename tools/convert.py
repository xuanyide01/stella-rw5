"""Convert the user's installed Artemis/PF8 game to a bounded Vela reader.
Only literal AST tables are parsed. Original executable/Lua code is never run.
"""
from pathlib import Path
from functools import lru_cache
import os,json,io,hashlib,collections,re
from PIL import Image,ImageOps,ImageDraw
from pfs import index,payload
from lua_table import parse,array
ROOT=Path(__file__).resolve().parents[1]
if not os.environ.get('STELLA_GAME_ROOT'):raise SystemExit('Set STELLA_GAME_ROOT to your own Steam game directory before converting.')
GAME=Path(os.environ['STELLA_GAME_ROOT']).expanduser().resolve()
COMMON=ROOT/'src/common';IMAGES=COMMON/'images';IMAGES.mkdir(parents=True,exist_ok=True)
REPORTS=ROOT/'reports';REPORTS.mkdir(exist_ok=True)
entries={};provenance=[]
for arc in sorted(GAME.glob('*.pfs*')):
    es,key=index(arc)
    provenance.append({'archive':arc.name,'bytes':arc.stat().st_size,'indexSHA1':key.hex(),'entries':len(es)})
    for e in es:entries[e['name'].lower()]=(arc,e,key)
def raw(name):
    a,e,k=entries[name.lower()];return payload(a,e,k)
def table(name):return parse(raw(name).decode('utf-8-sig'))
@lru_cache(maxsize=36)
def image(name):
    im=Image.open(io.BytesIO(raw(name)));im.load();return im
def pos(im):
    c=im.info.get('comment','').split(',')
    return tuple(map(int,c[1:3])) if len(c)>=5 and c[0]=='pos' else (0,0)
def stable(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(stable(v),encoding='utf8')
asts={Path(n).stem:table(n)['ast'] for n in entries if n.startswith('script/') and n.endswith('.ast')}
config=table('system/table/list_windows.tbl');lang=table('system/table/list_windows_cn.tbl')['lang']
flow=asts['00シナリオフロー'];calls=array(flow['block_00000'])
starts={};chapterNames={1:'遭遇与觉醒',20:'片尾',21:'尾声'}
for i in range(1,22):
    label=flow['label']['z'+str(i).zfill(2)];n=label['label']-1
    c=next(c for c in calls[n:] if c[1]=='excall' and c.get('file','').startswith('01_stella'))
    fn=c['file'];bn='block_00000';ci=0
    if i in [10,20]:
        target=asts[fn]['label']['label_z50'];bn=target['block'];ci=target['label']-1
    starts[(fn,bn,ci)]=i
    for b in asts[fn].values():
        if not isinstance(b,dict):continue
        found=next((c.get('cn') for c in array(b) if isinstance(c,dict) and c.get(1)=='savetitle' and c.get('cn')),None)
        if found:chapterNames.setdefault(i,found)
    chapterNames.setdefault(i,'第 '+str(i)+' 章')
assets={};dimensions={};bgCache={};portraitCache={};assetReport=[];missing=set()
def resource(file,path):
    category=(path or ':bg/').strip(':/');name='image/'+category+'/'+file+'.png'
    if name.lower() in entries:return name
    return None
def saveAsset(im,kind,key):
    identifier=kind+'_'+hashlib.sha256(key.encode()).hexdigest()[:20]
    ext='.png' if kind=='p' else '.jpg';filename=identifier+ext;dest=IMAGES/filename
    if kind=='p':
        im=im.convert('RGBA');im.thumbnail((200,256),Image.Resampling.LANCZOS)
        im=im.quantize(colors=256,method=Image.Quantize.FASTOCTREE)
        im.save(dest,optimize=True,compress_level=9)
        dimensions[filename]=list(im.size)
    else:
        im=im.convert('RGB');im.thumbnail((320,256),Image.Resampling.LANCZOS);im.save(dest,quality=76,optimize=True,progressive=False)
    assets[identifier]=filename
    assetReport.append({'id':identifier,'file':filename,'kind':kind,'size':list(im.size),'bytes':dest.stat().st_size})
    return identifier
def background(layers):
    key=stable(layers)
    if key in bgCache:return bgCache[key]
    canvas=Image.new('RGBA',(320,180),(0,0,0,255))
    for layer in layers:
        source=layer['source'];im=image(source).convert('RGBA')
        # Static base images keep their full composition; tall scrolling art uses a center crop.
        if layer['base']:
            im=ImageOps.fit(im,(320,180),Image.Resampling.LANCZOS)
            xy=(0,0)
        else:
            px,py=pos(image(source));xy=(round((px+layer.get('x',0))*320/1920),round((py+layer.get('y',0))*180/1080))
            im=im.resize((max(1,round(im.width/6)),max(1,round(im.height/6))),Image.Resampling.LANCZOS)
        alpha=layer.get('alpha',255)
        if alpha<255:im.putalpha(im.getchannel('A').point(lambda n:round(n*alpha/255)))
        canvas.alpha_composite(im,xy)
    result=saveAsset(canvas,'b',key);bgCache[key]=result;return result
def portrait(c):
    parts=[c.get(k) for k in ['file','face','ex01'] if c.get(k)]
    key=stable([parts,c.get('dir','')])
    if key in portraitCache:return portraitCache[key]
    parts=[resource(n,':fg/') for n in parts]
    if not parts or any(n is None for n in parts):raise ValueError('Missing portrait '+key)
    ims=[image(n) for n in parts];ps=[pos(im) for im in ims]
    x0=min(p[0] for p in ps);y0=min(p[1] for p in ps)
    x1=max(p[0]+im.width for p,im in zip(ps,ims));y1=max(p[1]+im.height for p,im in zip(ps,ims))
    canvas=Image.new('RGBA',(x1-x0,y1-y0))
    for im,(x,y) in zip(ims,ps):canvas.alpha_composite(im.convert('RGBA'),(x-x0,y-y0))
    bbox=canvas.getchannel('A').getbbox()
    if not bbox:raise ValueError('Empty portrait')
    canvas=canvas.crop(bbox)
    # Keep the head and upper body large enough to read on the watch.
    canvas=canvas.crop((0,0,canvas.width,max(1,round(canvas.height*.78))))
    if c.get('dir') in ['rx','rxy']:canvas=ImageOps.mirror(canvas)
    result=saveAsset(canvas,'p',key);portraitCache[key]=result;return result
scenes={str(i):[] for i in range(1,22)};chapter=1;layers={};sprites={};textProof=[];commands=collections.Counter();frames=0;sourceTexts=0
for call in calls:
    if call[1]!='excall' or not call.get('file','').startswith('01_stella'):continue
    fn=call['file'];ast=asts[fn];bn='block_00000';seen=set();finished=False
    while bn and not finished:
        if bn in seen:raise ValueError('Loop in original AST '+fn)
        seen.add(bn);b=ast[bn]
        for ci,c in enumerate(array(b)):
            if (fn,bn,ci) in starts:
                chapter=starts[(fn,bn,ci)]
                if chapter==20:scenes['20'].append({'op':'text','speaker':'','text':'（原作片尾动画在手表图文版中省略，点击下一句继续尾声。）','background':background(list(layers.values())),'bodies':[]})
            tag=c[1];commands[tag]+=1
            if tag=='exreturn':finished=True;break
            if tag=='select':raise ValueError('Unexpected choice requires a verified converter')
            if tag=='excall':
                if c.get('cond') not in ['s.trial==1','f.chap==1']:raise ValueError('Unexpected control flow '+str(c))
            elif tag=='cgdel':
                if c.get('id')==-1:layers={k:v for k,v in layers.items() if k==0}
                else:layers.pop(c.get('id',0),None)
            elif tag=='bg' and c.get('file') and not c.get('movie'):
                file=c['file'];src=resource(file,c.get('path'))
                slot=c.get('id',0)
                if file.startswith('ef_') or c.get('style'):continue
                if src is None:missing.add(str(c));continue
                layers[slot]={'source':src,'base':slot==0,'alpha':c.get('alpha',255),'x':0,'y':0}
            elif tag=='fg':
                mode=c.get('mode',3);slot=c.get('id',13)
                if mode==-2:sprites={}
                elif mode in [-1,1]:
                    if c.get('ch'):sprites={k:v for k,v in sprites.items() if v['ch']!=c['ch']}
                    else:sprites.pop(slot,None)
                elif c.get('file'):
                    if c.get('ch'):sprites={k:v for k,v in sprites.items() if v['ch']!=c['ch']}
                    sprites[slot]={'image':portrait(c),'ch':c.get('ch','')}
            elif tag=='text' and b.get('text',{}).get('cn'):
                cn=b['text']['cn'];rows=[]
                for row in array(cn):rows.append(''.join(v if isinstance(v,str) else v['text'] for v in array(row)))
                text='\n'.join(rows).strip();sourceTexts+=1
                if not text:raise ValueError('Empty CN block '+fn+'/'+bn)
                sourceHash=hashlib.sha256(text.encode()).hexdigest()
                textProof.append({'file':fn,'block':bn,'chapter':chapter,'textSHA256':sourceHash})
                # The original uses novel-style text with no speaker labels; keep it that way.
                frame={'op':'text','speaker':'','text':text,'background':background([layers[k] for k in sorted(layers)]),'bodies':[sprites[k]['image'] for k in sorted(sprites)][:3]}
                scenes[str(chapter)].append(frame);frames+=1
        if not finished:bn=b.get('linknext')
    print('STORY',fn,frames,flush=True)
assert sourceTexts==9424,(sourceTexts,'Chinese block count changed')
assert not missing,missing
for i in range(1,22):
    assert scenes[str(i)],'Empty chapter '+str(i)
    scenes[str(i)].append({'op':'jumpScene','scene':i+1,'to':0} if i<21 else {'op':'end'})
    for n in range(0,len(scenes[str(i)]),512):write(COMMON/'story'/str(i)/(str(n//512)+'.txt'),scenes[str(i)][n:n+512])
catalog={'initial':1,'flowScene':1,'scenes':{str(i):{'name':chapterNames[i],'length':len(scenes[str(i)])} for i in range(1,22)},'routes':[{'name':'完整故事','scenes':list(range(1,22))}],'chapters':[{'id':i,'name':str(i).zfill(2)+' · '+chapterNames[i],'route':0} for i in range(1,22)],'endings':{'21':'星之终途'}}
(COMMON/'catalog.js').write_text('export const catalog='+stable(catalog)+';\n',encoding='utf8')
gallery=[];omitted=[]
for group,v in config['csv']['extra_cgmode'].items():
    files=array(v)[2:]
    for f in files:
        src=resource(f,':bg/' if group.startswith('bg') else ':ev/')
        if src is None:
            if f=='op01':omitted.append({'group':group,'file':f,'reason':'opening movie omitted'});continue
            omitted.append({'group':group,'file':f,'reason':'declared by original gallery table, absent from installed archives'});continue
        asset=background([{'source':src,'base':True,'alpha':255,'x':0,'y':0}])
        gallery.append({'group':group,'image':asset,'source':f,'label':('背景 ' if group.startswith('bg') else 'CG ')+group[2:]})
# Include extra still-image variants shipped by this particular Steam build too.
covered={x['source'] for x in gallery}
for name in sorted(entries):
    if not name.startswith('image/ev/') or not name.endswith('.png'):continue
    file=Path(name).stem
    if file in covered:continue
    group='ts'+re.match(r'cg_ts(\d+)',file).group(1)
    asset=background([{'source':name,'base':True,'alpha':255,'x':0,'y':0}])
    gallery.append({'group':group,'image':asset,'source':file,'label':'CG '+group[2:]})
write(COMMON/'gallery.txt',gallery)
(COMMON/'assets.js').write_text('export const assets='+stable(assets)+';\nexport function imagePath(name){return assets[name]?\'/common/images/\'+assets[name]:\'/common/title_bg.png\';}\n',encoding='utf8')
(COMMON/'portrait-layout.js').write_text('const dimensions='+stable(dimensions)+''';
export function portraitBox(path,count,index){const name=String(path||'').split('/').pop(),size=dimensions[name]||[180,256],cell=count>=3?144:count===2?216:432,scale=Math.min((count===1?280:cell)/size[0],286/size[1]),width=Math.round(size[0]*scale),height=Math.round(size[1]*scale);return {width,height,left:Math.round(index*cell+(cell-width)/2),top:286-height};}
''',encoding='utf8')
# Recompose the official title layers from the Chinese UI's original coordinates.
title=Image.new('RGBA',(1920,1080));cfg=lang['ui_title01']
for k in ['bg','ch01']:
    c=cfg[k];im=image('pc/cn/'+c['file']+'.png').convert('RGBA');title.alpha_composite(im,(c['x'],c['y']))
title=ImageOps.fit(title,(432,286),Image.Resampling.LANCZOS);title.convert('RGB').save(COMMON/'title_bg.png',optimize=True)
# Round portrait icon based on the original title heroine, with transparent corners.
hero=image('pc/cn/title/char01.png').convert('RGBA').crop((1060,0,1680,620))
icon=ImageOps.fit(hero,(192,192),Image.Resampling.LANCZOS,centering=(.5,.24));base=Image.new('RGBA',(192,192),(54,95,103,255));base.alpha_composite(icon)
mask=Image.new('L',(768,768));ImageDraw.Draw(mask).ellipse((0,0,767,767),fill=255);base.putalpha(mask.resize((192,192),Image.Resampling.LANCZOS));base.save(COMMON/'logo.png',optimize=True)
report={'game':'星之终途','sourceEngine':'Artemis PF8/AST','archives':provenance,'sourceFiles':len([x for x in asts if x.startswith('01_stella')]),'sourceChineseBlocks':sourceTexts,'convertedChineseBlocks':frames,'originalChoices':commands.get('select',0),'chapters':21,'sourceOrderPreserved':True,'originalChapterEntryPositions':[{ 'file':k[0],'block':k[1],'command':k[2]+1,'chapter':v} for k,v in starts.items()],'galleryGroups':len(set(x['group'] for x in gallery)),'galleryEntries':len(gallery),'allShippedEventCGStillsIncluded':True,'omittedMovies':omitted,'portraitCombinations':len(portraitCache),'backgroundCompositions':len(bgCache),'resources':len(assets),'resourceBytes':sum(x['bytes'] for x in assetReport),'maximumPackageBytes':15000000,'limitations':['No audio, opening/ending movies, or animated visual effects','Static scene composition; camera movement/zoom simplified'],'physicalDeviceTested':False}
write(REPORTS/'conversion.json',report);write(REPORTS/'text-provenance.json',textProof);write(REPORTS/'assets.json',assetReport)
print('CONVERTED',stable(report))
