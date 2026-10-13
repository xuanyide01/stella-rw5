const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),cat=fs.readFileSync(path.join(root,'src/common/catalog.js'),'utf8').replace('export const','const');
const script=name=>fs.readFileSync(path.join(root,'src/common',name+'.js'),'utf8').replace(/^import[^\n]*\n/gm,'').replace(/export /g,'');
const api=new Function(cat+['text-font','portrait-layout','progress','engine','saves','gallery','assets'].map(script).join('\n')+';return {checkpoint,portraitBox,PROGRESS_KEY,emptyProgress,decodeProgress,progressFromState,withProgress,textFont,catalog,newState,restore,readFrame,readChapterSkip,next,nextChapter,choose,previous,previewMap,SLOT_COUNT,LEGACY_KEY,slotKey,decodeSave,createSave,slotRow,imagePath,groupGallery,stepVariant};')();
const operations={};for(const id of Object.keys(api.catalog.scenes)){operations[id]=[];const dir=path.join(root,'src/common/story',id);for(const f of fs.readdirSync(dir).sort((a,b)=>parseInt(a)-parseInt(b)))operations[id].push(...JSON.parse(fs.readFileSync(path.join(dir,f),'utf8')));}
function frame(s,skip,context){for(let i=0;i<1000;i++){const ops=operations[s.chapter],base=Math.floor(s.cursor/512)*512,part=ops.slice(base,base+512),f=skip?api.readChapterSkip(part,s,context,base,ops.length):api.readFrame(part,s,base,ops.length);if(!['yield','jump'].includes(f.type))return f;}throw Error('Reader did not settle');}
test('all 9424 original Chinese blocks replay in original order through the ending',()=>{const s=api.newState(1,true),proof=JSON.parse(fs.readFileSync(path.join(root,'reports/text-provenance.json'),'utf8')),actual=[];for(let i=0;i<10000;i++){const f=frame(s);if(f.type==='end')break;assert.equal(f.type,'text');if(s.rootChapter!==20)actual.push({chapter:s.rootChapter,textSHA256:crypto.createHash('sha256').update(f.text).digest('hex')});api.next(s);if(i%53===0)Object.assign(s,api.decodeSave(JSON.stringify(api.createSave(s,'play',1000))).state);}assert.equal(s.chapter,21);assert.ok(s.ended);assert.deepEqual(actual,proof.map(p=>({chapter:p.chapter,textSHA256:p.textSHA256})));});
test('each original chapter entry reaches the ending and skipping arrives at the next chapter',()=>{for(let id=1;id<=21;id++){const s=api.newState(id);assert.equal(frame(s).type,'text');const context=api.nextChapter(s),f=frame(s,true,context);if(id<21){assert.equal(f.type,'text');assert.equal(s.chapter,id+1);assert.equal(s.cursor,0);}else assert.equal(f.type,'end');}});
test('generic safe skip preserves a pending choice and ignores neither choice nor save restore',()=>{const s=api.newState(1);s.cursor=1;const ops=[{op:'text',speaker:'',text:'A',bodies:[]},{op:'choice',items:[{text:'B',to:2}]},{op:'text',speaker:'',text:'C',bodies:[]}];for(let n=0;n<3;n++){const context=api.nextChapter(s);assert.equal(api.readChapterSkip(ops,s,context,0,3).type,'choice');assert.equal(s.cursor,1);}for(let slot=0;slot<30;slot++){const saved=api.decodeSave(JSON.stringify(api.createSave(s,'choice',slot)));assert.equal(saved.state.cursor,1);}assert.equal(new Set(Array.from({length:30},(_,i)=>api.slotKey(i))).size,30);});
test('all image references exist; portraits meet the text box and preserve their proportions',()=>{const data=JSON.parse(fs.readFileSync(path.join(root,'reports/assets.json'),'utf8'));for(const ops of Object.values(operations))for(const o of ops)if(o.op==='text')for(const key of [o.background,...o.bodies])assert.ok(fs.existsSync(path.join(root,'src',api.imagePath(key))),key);for(const a of data)if(a.kind==='p')for(const count of [1,2,3])for(let i=0;i<count;i++){const b=api.portraitBox('/common/images/'+a.file,count,i);assert.equal(b.top+b.height,286);assert.ok(Math.abs(b.width/b.height-a.size[0]/a.size[1])<.02);}});
test('gallery retains all available original entries with differences grouped and cycled',()=>{const data=JSON.parse(fs.readFileSync(path.join(root,'src/common/gallery.txt'),'utf8')),report=JSON.parse(fs.readFileSync(path.join(root,'reports/conversion.json'),'utf8')),groups=api.groupGallery(data);assert.equal(groups.length,report.galleryGroups);assert.equal(data.length,report.galleryEntries);const first=groups[0];assert.equal(first.variants.length,10);assert.equal(api.stepVariant(9,1,10),0);for(const x of data)assert.ok(fs.existsSync(path.join(root,'src',api.imagePath(x.image))));});
function page(){const pending=[],timers=[],writes=[],source=fs.readFileSync(path.join(root,'src/pages/index/index.ux'),'utf8').split('<script>')[1].split('</script>')[0].replace(/^import[^\n]*\n/gm,'').replace('export default','globalThis.page=');const context=vm.createContext({...api,file:{readText:o=>o.success({text:fs.readFileSync(path.join(root,'src',o.uri),'utf8')})},storage:{get:o=>pending.push(o),set:o=>writes.push(o)},prompt:{showToast(){}},console:{log(){},error(){}},Date,setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout(){}});vm.runInContext(source,context);const p=context.page;Object.assign(p,p.private);p.onInit();pending.shift().success('');pending.shift().success('');p.textSpeed=0;return {p,pending,timers,writes};}
test('actual chapter UI refreshes first page repeatedly and returns directly to title',()=>{const {p}=page();for(let i=0;i<5;i++){p.openRoutes();assert.equal(p.mode,'chapters');assert.equal(p.browseRows[0].name,'01 · 遭遇与觉醒');const keys=p.browseRows.map(x=>x.key);p.nextBrowse();assert.ok(p.browseRows.every(x=>!keys.includes(x.key)));p.previousBrowse();assert.deepEqual(p.browseRows.map(x=>x.key),keys);p.closeBrowse();assert.equal(p.mode,'title');}});
test('actual slot UI reads 30 slots sequentially and cancels late callbacks on close',()=>{const {p,pending,timers}=page();p.openSlots('load');const saved=JSON.stringify(api.createSave(api.newState(),'play',1000));for(let i=0;i<30;i++){assert.equal(pending.length,1);const r=pending.shift();assert.equal(r.key,api.slotKey(i));r.success(saved);if(i<29)timers.shift()();}assert.equal(p._slotData.length,30);assert.equal(p.loading,false);p.closeSlots();p.openSlots('load');const first=pending.shift();p.closeSlots();first.success('');assert.equal(pending.length,0);});
test('actual page menu skips exactly one chapter and history restores the previous frame',()=>{const {p,timers}=page();p.startNew();assert.equal(p.mode,'play');assert.equal(p.session.chapter,1);const before=api.checkpoint(p.session);p.showMenu();p.goNextChapter();for(let n=0;p._chapterSkip;n++){assert.ok(n<1000);timers.shift()();}assert.equal(p.session.chapter,2);p.goBack();assert.deepEqual(api.checkpoint(p.session),before);});
test('invalid save locations are rejected and storage keys are independent',()=>{for(const cursor of [-1,NaN,1.5,100000])assert.throws(()=>api.restore({...api.newState(),cursor}));assert.match(api.slotKey(0),/^stella_rw5_/);assert.match(api.PROGRESS_KEY,/^stella_rw5_/);});

test('after story replays every converted source text and reaches its own ending',()=>{
 const proof=JSON.parse(fs.readFileSync(path.join(root,'reports/after-text-provenance.json'),'utf8'));
 for(const start of [api.catalog.afterInitial,108,109]){
  const s=api.newState(start,true),expected=proof.filter(x=>start>=108?x.scene===start:x.scene!==108&&x.scene!==109),actual=[];let notes=0,choices=0;
  for(let i=0;i<2000;i++){
   const f=frame(s);if(f.type==='end')break;
   if(f.type==='choice'){choices++;api.choose(s,f.items[0],0);continue;}
   assert.equal(f.type,'text');
   if(f.text==='（后日谈片尾动画在手表图文版中省略，点击继续返回标题。）')notes++;
   else actual.push({scene:s.chapter,cursor:s.cursor,textSHA256:crypto.createHash('sha256').update(f.text).digest('hex')});
   api.next(s);
   if(i%17===0)Object.assign(s,api.decodeSave(JSON.stringify(api.createSave(s,'play',i))).state);
  }
  assert.ok(s.ended);assert.equal(s.chapter,start>=108?start:107);assert.equal(choices,start>=108?0:1);assert.equal(notes,start>=108?0:1);
  assert.deepEqual(actual,expected.map(({scene,cursor,textSHA256})=>({scene,cursor,textSHA256})));
 }
});
test('the real after-story confirmation cannot be bypassed by repeated chapter skip or saving',()=>{
 const source=JSON.parse(fs.readFileSync(path.join(root,'reports/after-choice-source.json'),'utf8'))[0],s=api.newState(source.scene,true);
 assert.equal(frame(s,true,api.nextChapter(s)).type,'choice');assert.equal(s.cursor,source.cursor);
 for(let i=0;i<3;i++){const saved=api.decodeSave(JSON.stringify(api.createSave(s,'choice',i)));Object.assign(s,saved.state);assert.equal(frame(s,true,api.nextChapter(s)).type,'choice');assert.equal(s.cursor,source.cursor);}
 const f=frame(s);assert.equal(f.items[0].text,'「谢谢你，菲莉娅！！！」');assert.equal(f.items[0].to,source.items[0].to);
 api.choose(s,f.items[0],0);const target=frame(s);assert.equal(target.type,'text');assert.equal(s.cursor,source.items[0].to);
});
test('new title entries select independent stories, settings and system exit',()=>{
 const {p}=page();p.startAfterStory();assert.equal(p.mode,'title');p._progress.variables['sf.stella_main_clear']=true;p.refreshProgress();p.startAfterStory();assert.equal(p.mode,'play');assert.equal(p.session.chapter,101);
 p.toTitle();p.startNew();assert.equal(p.session.chapter,1);
 p.toTitle();p.openSettings();assert.equal(p.mode,'settings');p.toggleFont();assert.equal(p.fontSize,28);p.toTitle();
 let exits=0;p.$app={exit(){exits++;}};p.exitApplication();assert.equal(exits,1);assert.equal(p.timer,null);assert.equal(p._chapterSkip,null);
});
test('two-story chapter selector refreshes its first page and returns to the story selector',()=>{
 const {p}=page();p._progress.variables['sf.stella_main_clear']=true;p.refreshProgress();
 for(let i=0;i<4;i++){
  p.openChapterRoutes();assert.equal(p.mode,'routes');assert.equal(p.browseRows.length,2);const keys=p.browseRows.map(x=>x.key);
  p.selectBrowse(1);assert.equal(p.mode,'chapters');assert.equal(p.browseRows[0].name,'后日谈 · 阅读说明');assert.ok(p.browseRows.every(x=>!keys.includes(x.key)));
  const first=p.browseRows.map(x=>x.key);p.nextBrowse();p.previousBrowse();assert.deepEqual(p.browseRows.map(x=>x.key),first);
  p.closeBrowse();assert.equal(p.mode,'routes');assert.deepEqual(p.browseRows.map(x=>x.key),keys);p.selectBrowse(0);assert.equal(p.browseRows[0].name,'01 · 遭遇与觉醒');p.closeBrowse();p.closeBrowse();assert.equal(p.mode,'title');
 }
});
test('all historical main-story data is byte-identical and old save locations still restore',()=>{
 const baseline=JSON.parse(fs.readFileSync(path.join(root,'reports/after-story-baseline.json'),'utf8'));
 for(const [file,sha] of Object.entries(baseline.files))assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex'),sha,file);
 for(let id=1;id<=21;id++){const old=api.createSave(api.newState(id,true),'play',1000);assert.equal(api.decodeSave(JSON.stringify(old)).state.chapter,id);}
});

test('after story ends at AE and returns to title; the original epilogue stays in the main story',()=>{
 const {p}=page();assert.equal(api.catalog.afterEnd,107);assert.ok(!api.catalog.routes[1].scenes.includes(108));assert.ok(api.catalog.routes[0].scenes.includes(21));
 for(const id of [107,108,109,21]){
  p.session=api.newState(id);p.session.cursor=operations[id].length-1;p.cachedChapter=0;p.renderFrame();
  assert.equal(p.mode,id===21?'end':'title');assert.ok(p.session.ended);
 }
});

test('dragging a long dialogue keeps its position, a fresh tap advances, and each sentence resets scroll to top',()=>{
 const {p}=page(),scrolls=[];p.$element=()=>({scrollTo:position=>scrolls.push(position)});
 p.session=api.newState(107);p.session.cursor=110;p.cachedChapter=0;p.renderFrame();assert.ok(p.fullText.length>65);
 const position=p.session.cursor;
 p.dialogueTouchStart({touches:[{pageX:200,pageY:430}]});p.dialogueTouchMove({touches:[{pageX:201,pageY:350}]});p.dialogueTap();
 assert.equal(p.session.cursor,position);p.swipe({direction:'up'});assert.equal(p.mode,'play');
 p.dialogueTouchStart({touches:[{pageX:200,pageY:360}]});p.dialogueTap();assert.equal(p.session.cursor,position+1);
 assert.ok(scrolls.length>=2);for(const s of scrolls){assert.equal(s.top,0);assert.equal(s.behavior,'instant');}
});

test('AFTER STORY unlocks only after story-mode main completion and the flag survives progress reload',()=>{
 const {p,writes}=page();assert.equal(p.afterUnlocked,false);p.openChapterRoutes();assert.equal(p.browseRows.length,1);p.selectBrowse(1);assert.equal(p.mode,'routes');p.toTitle();
 p.session=api.newState(21);p.session.cursor=operations[21].length-1;p.cachedChapter=0;p.renderFrame();assert.equal(p.afterUnlocked,false);
 p.session=api.newState(21,true);p.session.cursor=operations[21].length-1;p.cachedChapter=0;p.renderFrame();assert.equal(p.afterUnlocked,true);
 const record=writes.find(x=>x.key===api.PROGRESS_KEY);assert.ok(record);const decoded=api.decodeProgress(record.value);assert.equal(decoded.variables['sf.stella_main_clear'],true);
 p._progress=decoded;p.refreshProgress();p.toTitle();p.openChapterRoutes();assert.equal(p.browseRows.length,2);p.toTitle();p.startAfterStory();assert.equal(p.session.chapter,101);
});
