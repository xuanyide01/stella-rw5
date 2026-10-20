const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const clean=name=>fs.readFileSync(path.join(root,'src/common',name+'.js'),'utf8').replace(/^import[^\n]*\n/gm,'').replace(/export /g,'');
const api=new Function(['catalog','auto-reader','text-font','portrait-layout','progress','engine','saves','gallery','assets'].map(clean).join('\n')+';return {autoSpeeds,autoWait,catalog,textFont,portraitBox,PROGRESS_KEY,emptyProgress,decodeProgress,progressFromState,withProgress,newState,restore,readFrame,readChapterSkip,next,nextChapter,choose,previous,previewMap,SLOT_COUNT,LEGACY_KEY,slotKey,decodeSave,createSave,slotRow,imagePath,groupGallery,stepVariant};')();
class Clock{
 constructor(){this.now=0;this.id=0;this.tasks=new Map();}
 set(fn,ms){const id=++this.id;this.tasks.set(id,{fn,at:this.now+Math.max(0,Number(ms)||0)});return id;}
 tick(ms){const end=this.now+ms;let count=0;while(true){const next=[...this.tasks].sort((a,b)=>a[1].at-b[1].at||a[0]-b[0])[0];if(!next||next[1].at>end)break;assert.ok(++count<20000,'timer loop');this.tasks.delete(next[0]);this.now=next[1].at;next[1].fn();}this.now=end;}
}
function fixture(values={}){
 const clock=new Clock(),data=new Map(Object.entries(values)),writes=[],events=[],files=[];let deferred=false;
 const source=fs.readFileSync(path.join(root,'src/pages/index/index.ux'),'utf8').split('<script>')[1].split('</script>')[0].replace(/^import[^\n]*\n/gm,'').replace('export default','globalThis.page=');
 const context=vm.createContext({...api,Date,console:{log:(...args)=>events.push({at:clock.now,args}),error:(...args)=>events.push({at:clock.now,args})},
  setTimeout:(fn,ms)=>clock.set(fn,ms),clearTimeout:id=>clock.tasks.delete(id),
  file:{readText:o=>{const finish=()=>o.success({text:fs.readFileSync(path.join(root,'src',o.uri),'utf8')});if(deferred)files.push(finish);else finish();}},
  storage:{get:o=>o.success(data.get(o.key)||''),set:o=>{data.set(o.key,o.value);writes.push(o);if(o.success)o.success();}},prompt:{showToast(){}}});
 vm.runInContext(source,context);const p=context.page;Object.assign(p,p.private);p.onInit();p.$element=()=>({scrollTo(){}});p.$app={exit(){events.push({at:clock.now,args:['exit']});}};
 function enter(chapter=1,cursor=0){p.stopAuto();p.clearTyping();p.session=api.newState(chapter,true);p.session.cursor=cursor;p.cachedChapter=0;p.textSpeed=0;p.renderFrame();}
 function enable(){p.showMenu();p.toggleAuto();p.resume();}
 function typed(){for(let i=0;p.timer!==null;i++){assert.ok(i<2000);clock.tick(30);}}
 return {p,clock,data,writes,events,enter,enable,typed,defer:()=>{deferred=true;},flush:()=>{deferred=false;while(files.length)files.shift()();}};
}
test('three post-text delays, long-paragraph allowance and old settings defaults',()=>{
 assert.deepEqual(api.autoSpeeds,['慢速','标准','快速']);assert.deepEqual([0,1,2].map(i=>api.autoWait(i,40)),[2600,1500,800]);
 assert.equal(api.autoWait(1,61),1555);assert.equal(api.autoWait(2,1000),5800);
 const {p}=fixture({'stella_rw5_settings_v1':JSON.stringify({fontSize:28,textSpeed:0})});assert.equal(p.autoEnabled,false);assert.equal(p.autoSpeed,1);assert.equal(p.fontSize,28);
});
test('menu enables auto but stays paused; subsequent sentences type at 30 ms before waiting',()=>{
 const f=fixture(),{p,clock}=f;f.enter();p.showMenu();p.toggleAuto();clock.tick(10000);assert.equal(p.session.cursor,0);assert.equal(p._autoTimer,null);
 p.resume();clock.tick(1499);assert.equal(p.session.cursor,0);clock.tick(1);assert.equal(p.session.cursor,1);assert.equal(p.displayText.length,1);
 clock.tick(29);assert.equal(p.displayText.length,1);clock.tick(1);assert.equal(p.displayText.length,2);f.typed();
 const cursor=p.session.cursor,delay=api.autoWait(p.autoSpeed,p.fullText.length);clock.tick(delay-1);assert.equal(p.session.cursor,cursor);clock.tick(1);assert.equal(p.session.cursor,cursor+1);
});
test('real after-story choice waits indefinitely and resumes only after the player chooses',()=>{
 const f=fixture(),{p,clock}=f;f.enter(107,422);f.enable();clock.tick(api.autoWait(1,p.fullText.length));assert.equal(p.mode,'choice');assert.equal(p.session.cursor,423);
 clock.tick(100000);assert.equal(p.session.cursor,423);assert.equal(p.session.choices.length,0);assert.equal(p._autoTimer,null);assert.equal(p.autoEnabled,true);
 p.pick(0);assert.equal(p.session.cursor,424);assert.equal(p.mode,'play');f.typed();clock.tick(api.autoWait(1,p.fullText.length));assert.equal(p.session.cursor,425);
});
test('background, menu and stale queued callbacks cannot advance; return starts a new full delay',()=>{
 const f=fixture(),{p,clock}=f;f.enter();f.enable();const stale=clock.tasks.get(p._autoTimer).fn;clock.tick(1400);p.onHide();stale();clock.tick(100000);assert.equal(p.session.cursor,0);
 p.onShow();clock.tick(1499);assert.equal(p.session.cursor,0);clock.tick(1);assert.equal(p.session.cursor,1);f.typed();p.showMenu();clock.tick(100000);assert.equal(p.session.cursor,1);
 p.resume();const cursor=p.session.cursor;clock.tick(api.autoWait(1,p.fullText.length));assert.equal(p.session.cursor,cursor+1);
});
test('manual completion restarts the full wait and going back turns automatic playback off',()=>{
 const f=fixture(),{p,clock}=f;f.enter();f.enable();clock.tick(1500);const cursor=p.session.cursor;clock.tick(30);p.advance();assert.equal(p.displayText,p.fullText);assert.equal(p.session.cursor,cursor);
 const delay=api.autoWait(1,p.fullText.length);clock.tick(delay-1);assert.equal(p.session.cursor,cursor);clock.tick(1);assert.equal(p.session.cursor,cursor+1);
 p.goBack();assert.equal(p.autoEnabled,false);assert.equal(p.session.cursor,cursor);f.typed();clock.tick(100000);assert.equal(p.session.cursor,cursor);
});
test('holding, dragging, inertia and a fresh tap safely pause or restart the wait',()=>{
 const f=fixture(),{p,clock}=f;f.enter(107,110);f.enable();const cursor=p.session.cursor;
 p.dialogueTouchStart({touches:[{pageX:200,pageY:440}]});clock.tick(100000);assert.equal(p.session.cursor,cursor);
 p.dialogueTouchMove({touches:[{pageX:200,pageY:340}]});p.dialogueTouchEnd();p.dialogueTap();assert.equal(p.session.cursor,cursor);
 clock.tick(500);p.dialogueScrolled({scrollY:35});const delay=api.autoWait(1,p.fullText.length);clock.tick(delay-1);assert.equal(p.session.cursor,cursor);
 p.dialogueTouchStart({touches:[{pageX:200,pageY:370}]});p.dialogueTouchEnd();p.dialogueTap();assert.equal(p.session.cursor,cursor+1);
});
test('save/LOAD pages freeze the cursor and an actual old save resumes with its saved choice intact',()=>{
 const saved=api.createSave(Object.assign(api.newState(107,true),{cursor:423}),'choice',1000);
 const f=fixture({[api.slotKey(29)]:JSON.stringify(saved)}),{p,clock}=f;f.enter();f.enable();p.showMenu();p.loadGame();clock.tick(0);assert.equal(p.mode,'slots');clock.tick(100000);assert.equal(p.session.cursor,0);
 p.selectSlot(29);assert.equal(p.mode,'choice');clock.tick(100000);assert.equal(p.session.cursor,423);p.pick(0);assert.equal(p.session.cursor,424);
 f.typed();p.showMenu();p.saveGame();clock.tick(0);const before=p.session.cursor;clock.tick(100000);assert.equal(p.session.cursor,before);p.selectSlot(0);assert.equal(p.mode,'play');
 clock.tick(api.autoWait(1,p.fullText.length));assert.equal(p.session.cursor,before+1);
});
test('only the speed is persisted: restarting retains speed but never silently enables auto',()=>{
 const f=fixture(),{p,data}=f;f.enter();p.showMenu();p.toggleAuto();p.cycleAutoSpeed();assert.equal(p.autoSpeed,2);
 const raw=data.get('stella_rw5_settings_v1'),settings=JSON.parse(raw);assert.equal(settings.autoSpeed,2);assert.ok(!('autoEnabled' in settings));
 const restarted=fixture({'stella_rw5_settings_v1':raw});assert.equal(restarted.p.autoSpeed,2);assert.equal(restarted.p.autoEnabled,false);
 p.cycleAutoSpeed();assert.equal(p.autoSpeed,0);p.cycleAutoSpeed();assert.equal(p.autoSpeed,1);
});
test('all real endings, title, errors and destruction cancel auto permanently',()=>{
 for(const action of ['ending-main','ending-after','ending-bonus','title','error','destroy','exit']){
  const f=fixture(),{p,clock}=f;f.enter();f.enable();
  if(action.startsWith('ending-')){const chapter=action==='ending-main'?21:action==='ending-after'?107:109;p.session=api.newState(chapter,true);p.session.cursor=api.catalog.scenes[String(chapter)].length-1;p.cachedChapter=0;p.renderFrame();}
  else if(action==='title')p.toTitle();else if(action==='error')p.fail('test failure');else if(action==='destroy')p.onDestroy();else p.exitApplication();
  const position=[p.session.chapter,p.session.cursor];clock.tick(100000);assert.equal(p.autoEnabled,false,action);assert.equal(p._autoTimer,null,action);assert.deepEqual([p.session.chapter,p.session.cursor],position,action);
 }
});
test('a chapter loading while backgrounded resumes its first sentence instead of skipping it',()=>{
 const f=fixture(),{p,clock}=f;f.enter(1,api.catalog.scenes['1'].length-2);f.enable();f.defer();clock.tick(api.autoWait(1,p.fullText.length));assert.equal(p.session.chapter,2);assert.equal(p.session.cursor,0);assert.equal(p.loading,true);
 p.onHide();f.flush();assert.equal(p._needsFrame,true);clock.tick(100000);assert.equal(p.session.cursor,0);p.onShow();assert.equal(p.mode,'play');assert.equal(p._needsFrame,false);assert.equal(p.session.cursor,0);
 f.typed();clock.tick(api.autoWait(1,p.fullText.length)-1);assert.equal(p.session.cursor,0);
});
test('cancelled pending loads never resurrect the game after returning to title or an error',()=>{
 for(const exit of ['title','error']){
  const f=fixture(),{p}=f;f.enter();f.defer();p.session=api.newState(2,true);p.cachedChapter=0;p.renderFrame();assert.equal(p._needsFrame,true);
  if(exit==='title')p.toTitle();else p.fail('cancelled load');
  assert.equal(p._needsFrame,false);p.onHide();p.onShow();assert.equal(p.mode,exit);
  f.flush();assert.equal(p.mode,exit);
 }
});
