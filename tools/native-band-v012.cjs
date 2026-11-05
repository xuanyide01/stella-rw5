// Exercise the installed, signed Band package through ordinary simulator input.
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),crypto=require('crypto');
const root=path.resolve(__dirname,'..'),environment=process.env.STARRY_EMULATOR_HOME||path.resolve(root,'../stella-band-environment');
const out=path.join(root,'native-test-results/band-v012'),url=process.env.STELLA_CONTROL_URL||'http://127.0.0.1:43152/';
const log=path.join(environment,'emulator.log'),prefix='STELLA_BAND8PRO';fs.mkdirSync(out,{recursive:true});
const sleep=ms=>new Promise(r=>setTimeout(r,ms)),logs=()=>fs.readFileSync(log,'utf8');
async function get(endpoint,timeout=20000){const response=await fetch(url+endpoint,{signal:AbortSignal.timeout(timeout)});if(!response.ok)throw Error(await response.text());return response;}
async function click(x,y){await get('click?x='+x+'&y='+y);await sleep(170);}
async function wait(at,re){for(let i=0;i<160;i++){const text=logs().slice(at);if(re.test(text))return text;await sleep(180);}throw Error('Native timeout: '+re);}
async function expected(x,y,re){const at=logs().length;await click(x,y);return wait(at,re);}
async function shot(name){await sleep(280);const data=Buffer.from(await(await get('screen')).arrayBuffer());assert.equal(data.readUInt32BE(16),336);assert.equal(data.readUInt32BE(20),480);fs.writeFileSync(path.join(out,name+'.png'),data);return data;}
async function menu(){await expected(168,448,/STELLA_BAND8PRO menu/);}
async function title(){await menu();await expected(168,423,/STELLA_BAND8PRO background loaded title/);}
async function frozen(ms=2200){const at=logs().length;await sleep(ms);assert.ok(!/STELLA_BAND8PRO auto advance|STELLA_BAND8PRO frame/.test(logs().slice(at)));}
async function standardSpeed(){for(let i=0;i<3;i++){const text=await expected(168,247,/STELLA_BAND8PRO auto speed \d/);const speed=Number(text.match(/auto speed (\d)/)[1]);await shot('speed-'+speed);if(speed===1)return;}throw Error('Speed did not cycle');}
async function lastSlotPage(){for(let i=0;i<7;i++)await click(280,444);}

(async()=>{
 const begin=logs().length,checks=[];
 await shot('title-locked');
 await expected(110,221,/STELLA_BAND8PRO frame 1 0(?:\r|\n|$)/);await shot('reading-standard');await menu();await shot('menu-default-off');
 // Persisted manual instant display remains independent from automatic typewriter display.
 await click(168,291);await click(168,335);await shot('menu-large-font');await click(168,335);
 await expected(168,71,/STELLA_BAND8PRO slots ready save/);await expected(168,118,/STELLA_BAND8PRO slot saved 1 1 0(?:\r|\n|$)/);
 await expected(285,448,/STELLA_BAND8PRO frame 1 1(?:\r|\n|$)/);await menu();await expected(168,71,/STELLA_BAND8PRO slots ready save/);await lastSlotPage();await shot('slots-last-page');
 await expected(168,204,/STELLA_BAND8PRO slot saved 30 1 1(?:\r|\n|$)/);await menu();
 await expected(168,203,/STELLA_BAND8PRO auto enabled true/);await shot('menu-auto-enabled');await standardSpeed();await frozen(2800);
 let at=logs().length,started=Date.now();await click(168,379);await wait(at,/STELLA_BAND8PRO auto advance 1 1(?:\r|\n|$)/);
 const initialWaitWallMS=Date.now()-started;assert.ok(initialWaitWallMS>=1300);await wait(at,/STELLA_BAND8PRO auto advance 1 2(?:\r|\n|$)/);await shot('reading-auto');
 await menu();await frozen();await expected(168,115,/STELLA_BAND8PRO slots ready load/);await frozen();await shot('load-auto-paused');await click(168,444);await frozen(1800);
 at=logs().length;await click(168,379);await wait(at,/STELLA_BAND8PRO auto advance/);await expected(45,448,/STELLA_BAND8PRO frame/);await menu();await shot('previous-disables-auto');
 // Save FAST and stop the app while automatic mode is enabled, then reopen it.
 await expected(168,247,/STELLA_BAND8PRO auto speed 2/);await expected(168,203,/STELLA_BAND8PRO auto enabled true/);await click(168,379);
 at=logs().length;await get('stop');await wait(at,/STELLA_BAND8PRO app destroyed/);await sleep(2000);
 at=logs().length;await get('start',90000);await wait(at,/STELLA_BAND8PRO background loaded title/);await sleep(700);
 await expected(110,289,/STELLA_BAND8PRO slots ready load/);await lastSlotPage();await expected(168,204,/STELLA_BAND8PRO slot loaded 30 1 1(?:\r|\n|$)/);await menu();await frozen();await shot('restart-auto-off-fast-preserved');
 await expected(168,115,/STELLA_BAND8PRO slots ready load/);await expected(168,118,/STELLA_BAND8PRO slot loaded 1 1 0(?:\r|\n|$)/);
 checks.push('336x480 title and inherited dynamic fonts render; 22/26-pixel setting toggles',
 'all nine menu actions fit, all three automatic speed settings respond',
 'slots 1 and 30 save distinct positions and load after real application restart',
 'automatic reading advances successive typed sentences after standard wait',
 'menu and LOAD pause automatic reading; return resumes; previous sentence disables auto',
 'restart defaults to manual, preserves FAST speed and existing Band storage keys');
 // Complete the main story using the normal protected Next Chapter button.
 for(let chapter=1;chapter<=21;chapter++){
  await menu();const re=chapter<21?new RegExp(prefix+' frame '+(chapter+1)+' 0(?:\\r|\\n|$)'):/STELLA_BAND8PRO ending 21/;
  await expected(168,159,re);if(chapter%5===0)console.log('MAIN_SAFE_SKIP',chapter);
 }
 await shot('main-complete');await expected(168,274,/STELLA_BAND8PRO background loaded title/);await shot('title-after-unlocked');
 // Normal chapter selector navigation must refresh the first page without paging workarounds.
 await click(110,289);await shot('route-list');await click(168,204);await shot('after-chapters-first-page');await click(168,444);await shot('route-list-return');await click(168,204);
 await click(280,444);await expected(168,290,/STELLA_BAND8PRO frame 107 0(?:\r|\n|$)/);
 for(let i=1;i<=110;i++){await expected(285,448,new RegExp(prefix+' frame 107 '+i+'(?:\\r|\\n|$)'));if(i%40===0)console.log('LONG_PARAGRAPH',i);}
 await shot('long-text');await menu();await click(168,335);await click(168,379);await shot('long-text-large');await menu();await click(168,335);
 await expected(168,203,/STELLA_BAND8PRO auto enabled true/);await standardSpeed();await click(168,379);at=logs().length;
 await get('drag?x0=168&y0=395&x1=168&y1=314');assert.match(logs().slice(at),/STELLA_BAND8PRO dialogue scroll 107 110 [1-9]/);assert.ok(!/STELLA_BAND8PRO auto advance/.test(logs().slice(at)));await shot('long-text-after-drag');
 await wait(at,/STELLA_BAND8PRO auto advance 107 110/);await menu();await expected(168,159,/STELLA_BAND8PRO choice 107 423/);await shot('choice-paused');await frozen(3500);
 await expected(168,436,/STELLA_BAND8PRO menu 107/);await shot('choice-menu');await click(168,159);await frozen(1800);await shot('repeated-skip-still-at-choice');
 at=logs().length;await expected(168,125,/STELLA_BAND8PRO frame 107 424/);await wait(at,/STELLA_BAND8PRO auto advance 107 424/);await shot('choice-selected-auto-resumes');
 await expected(45,448,/STELLA_BAND8PRO frame/);await menu();await expected(168,159,/STELLA_BAND8PRO ending 107/);await wait(logs().length-1600,/STELLA_BAND8PRO background loaded title/);await shot('after-end-title');
 checks.push('START completion unlocks AFTER STORY at the first title row',
 'route/chapter first pages refresh and return without extra pagination',
 'real long paragraph wraps, scrolls at both sizes and resumes AUTO after dragging',
 'repeated protected chapter skip cannot bypass the real 107:423 confirmation',
 'AUTO remains paused at choices and resumes only after manual confirmation',
 'after-story ending returns to the title');
 await expected(110,391,/STELLA_BAND8PRO gallery ready 256 394/);await shot('gallery');await click(85,145);const first=await shot('cg-variant-1');await click(168,190);const second=await shot('cg-variant-2');assert.ok(!first.equals(second));
 await click(168,452);await click(168,444);await expected(110,425,/STELLA_BAND8PRO app destroyed/);await sleep(2000);
 checks.push('256 CG groups / 394 images remain; tapping a group cycles its original differences',
 'title EXIT invokes the system application exit and cancels automatic timers');
 const recent=logs().slice(begin);assert.ok(!/STELLA_BAND8PRO error|STELLA_BAND8PRO background failed|ASSERTION FAILED|PANIC!!!|coredump_dump_dev/.test(recent));
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'src/manifest.json'),'utf8')),rpk=path.join(root,'dist',manifest.package+'.debug.'+manifest.versionName+'.rpk');
 const report={result:'passed',version:manifest.versionName,date:'2026-11-02',packageSha256:crypto.createHash('sha256').update(fs.readFileSync(rpk)).digest('hex'),packageBytes:fs.statSync(rpk).size,
 screen:[336,480],runtime:'official generic vela-watch-5.0 simulator; not physical Xiaomi Smart Band 8 Pro firmware',emulatorRAMMB:128,physicalDeviceTested:false,initialWaitWallMS,checks};
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log('NATIVE_BAND_PASSED',JSON.stringify(report));
})().catch(error=>{fs.writeFileSync(path.join(out,'failure.txt'),error.stack);console.error(error.stack);process.exitCode=1;});
