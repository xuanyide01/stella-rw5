// Real clicks and vertical drags against the exact 0.2.1 installed package.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const zlib=require('zlib');
const root=path.resolve(__dirname,'..'),out=path.join(root,'native-test-results/v021'),url='http://127.0.0.1:43135';
const log=path.resolve(root,'../stella-after-environment/emulator.log');
fs.mkdirSync(out,{recursive:true});
const sleep=ms=>new Promise(r=>setTimeout(r,ms)),logs=()=>fs.readFileSync(log,'utf8');
async function request(endpoint,timeout=20000){const r=await fetch(url+'/'+endpoint,{signal:AbortSignal.timeout(timeout)});if(!r.ok)throw Error(await r.text());return r;}
async function click(x,y){await request('click?x='+x+'&y='+y);await sleep(160);}
async function wait(at,re){for(let i=0;i<100;i++){const text=logs().slice(at);if(re.test(text))return text;await sleep(200);}throw Error('Native timeout: '+re);}
async function expected(x,y,re){const at=logs().length;await click(x,y);return wait(at,re);}
async function shot(name){await sleep(300);fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(await(await request('screen')).arrayBuffer()));}
async function wakeIfBlack(){
 const png=Buffer.from(await(await request('screen')).arrayBuffer()),blocks=[];let at=8;
 while(at<png.length){const size=png.readUInt32BE(at),kind=png.toString('ascii',at+4,at+8);if(kind==='IDAT')blocks.push(png.subarray(at+8,at+8+size));at+=12+size;}
 const decoded=zlib.inflateSync(Buffer.concat(blocks)),width=png.readUInt32BE(16),height=png.readUInt32BE(20),channels=png[25]===6?4:3;
 assert.equal(png[24],8);assert.ok([2,6].includes(png[25]));
 let previous=new Uint8Array(width*channels),offset=0,black=true;
 const paeth=(a,b,c)=>{const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);return pa<=pb&&pa<=pc?a:pb<=pc?b:c;};
 for(let y=0;y<height&&black;y++){
  const filter=decoded[offset++],row=new Uint8Array(width*channels);
  for(let x=0;x<row.length;x++){
   const a=x>=channels?row[x-channels]:0,b=previous[x],c=x>=channels?previous[x-channels]:0;
   row[x]=(decoded[offset++]+(filter===0?0:filter===1?a:filter===2?b:filter===3?Math.floor((a+b)/2):paeth(a,b,c)))&255;
   if(x%channels<3&&row[x]>2)black=false;
  }previous=row;
 }
 if(black){await request('wake');await sleep(1500);console.log('VIRTUAL_DISPLAY_WOKEN');}
}
async function menu(){await expected(216,488,/STELLA_RW5 menu/);}
async function title(){await menu();await expected(216,447,/STELLA_RW5 background loaded title/);}
async function drag(){await request('drag?x0=210&y0=440&x1=210&y1=345');await sleep(450);}

(async()=>{
 const begin=logs().length,checks=[];
 if(process.argv.includes('--cold-only')){
  await wakeIfBlack();await shot('title-after-cold');await expected(125,232,/STELLA_RW5 frame 101 0/);await title();
  assert.ok(!/STELLA_RW5 error|STELLA_RW5 background failed|ASSERTION FAILED|PANIC!!!|coredump/.test(logs().slice(begin)));
  const report=JSON.parse(fs.readFileSync(path.join(out,'report.json'),'utf8')),manifest=JSON.parse(fs.readFileSync(path.join(root,'src/manifest.json'),'utf8'));
  const rpk=path.join(root,'dist',manifest.package+'.debug.'+manifest.versionName+'.rpk');
  assert.equal(report.packageSha256,crypto.createHash('sha256').update(fs.readFileSync(rpk)).digest('hex'));
  report.coldBootUnlockPreserved=true;report.checks.push('AFTER STORY remains unlocked and its first-row entry works after complete simulator restart');
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log('UI_COLD_UNLOCK_PASSED');return;
 }
 const alreadyUnlocked=process.argv.includes('--unlocked');await wakeIfBlack();await shot(alreadyUnlocked?'title-before-replay':'title-locked');
 // Complete the real main-story flow using the public chapter-skip action.
 await expected(125,alreadyUnlocked?268:232,/STELLA_RW5 frame 1 0/);
 for(let chapter=1;chapter<=21;chapter++){
  await menu();await expected(216,215,chapter===21?/STELLA_RW5 after story unlocked/:new RegExp('STELLA_RW5 frame '+(chapter+1)+' 0'));
  if(chapter%5===0)console.log('MAIN_UNLOCK_CHAPTER',chapter);
 }
 await shot('main-clear-unlock');await expected(216,280,/STELLA_RW5 background loaded title/);await shot('title');
 await expected(125,232,/STELLA_RW5 frame 101 0/);await shot('after-intro');await title();
 checks.push(alreadyUnlocked?'real START flow completes and retains unlocked first-row AFTER STORY':'AFTER STORY initially hidden; real START flow completion unlocks it as first title row');
 // Existing real save 01 and a pending choice in 30 survive the package upgrade.
 await expected(125,340,/STELLA_RW5 slots ready load/);await expected(216,126,/STELLA_RW5 slot loaded 1 101 0/);
 await shot('old-slot-01');await menu();await expected(216,157,/STELLA_RW5 slots ready load/);
 for(let i=0;i<7;i++)await click(354,474);
 await expected(216,218,/STELLA_RW5 slot loaded 30 107 423/);await shot('choice-loaded-cold');
 await expected(216,471,/STELLA_RW5 menu 107/);await click(216,215);await sleep(1700);await shot('choice-skip-guard');
 assert.deepEqual(fs.readFileSync(path.join(out,'choice-loaded-cold.png')),fs.readFileSync(path.join(out,'choice-skip-guard.png')));
 await expected(216,135,/STELLA_RW5 frame 107 424/);await menu();
 const ending=await expected(216,215,/STELLA_RW5 background loaded title/);assert.match(ending,/STELLA_RW5 ending 107 AFTER STORY/);assert.ok(!/STELLA_RW5 frame 108/.test(ending));
 await shot('after-ending-title');checks.push('cold upgrade restores old slots 01 and 30, including pending confirmation','chapter skip cannot bypass pending confirmation','after-story AE completes at scene 107 and automatically returns to title without replaying scene 108');
 // Read a real long source paragraph, preserving its exact content.
 await click(125,304);await shot('routes');await click(216,218);await shot('after-chapters-first');await click(354,474);await shot('after-chapters-second');
 await expected(216,310,/STELLA_RW5 frame 107 0/);
 for(let i=1;i<=110;i++){await expected(354,488,new RegExp('STELLA_RW5 frame 107 '+i+'(?:\\r|\\n|$)'));if(i%25===0)console.log('LONG_DIALOGUE_POSITION',i);}
 await shot('long-standard-top');
 let at=logs().length;await drag();const scrolled=logs().slice(at);
 assert.match(scrolled,/STELLA_RW5 dialogue scroll 107 110 [1-9]/);assert.ok(!/STELLA_RW5 frame/.test(scrolled));await shot('long-standard-bottom');
 at=logs().length;await expected(210,370,/STELLA_RW5 frame 107 111/);await shot('long-next-reset');
 await expected(65,488,/STELLA_RW5 frame 107 110/);await shot('long-standard-return');
 await menu();await click(216,331);await click(216,389);await shot('long-large-top');
 at=logs().length;await drag();assert.match(logs().slice(at),/STELLA_RW5 dialogue scroll 107 110 [1-9]/);assert.ok(!/STELLA_RW5 frame/.test(logs().slice(at)));await shot('long-large-bottom');
 await expected(210,370,/STELLA_RW5 frame 107 111/);await menu();await shot('menu');await click(216,331);await click(216,447);
 checks.push('real 71-character paragraph 107:110 wraps and scrolls at 24px and 28px','vertical drag keeps the story cursor unchanged; a fresh dialogue tap advances','returning to the paragraph resets its scroll position');
 // The original main epilogue remains independently accessible.
 await click(125,304);await click(216,126);for(let i=0;i<5;i++)await click(354,474);
 await expected(216,126,/STELLA_RW5 frame 21 0/);await shot('main-epilogue');await menu();await expected(216,215,/STELLA_RW5 ending 21/);await shot('main-ending');await click(216,280);
 await click(125,376);await shot('settings');await click(216,240);
 await click(125,412);await wait(begin,/STELLA_RW5 gallery ready/);await shot('gallery');await click(108,146);await shot('cg');await click(216,487);await click(216,474);
 await expected(125,448,/STELLA_RW5 app destroyed/);await sleep(2500);const reopenedAt=logs().length;await request('start',90000);await wait(reopenedAt,/STELLA_RW5 background loaded title/);await wait(reopenedAt,/PageCallHook, name:onShow/);await sleep(500);await wakeIfBlack();await shot('title-after-exit');
 await expected(125,232,/STELLA_RW5 frame 101 0/);await title();
 checks.push('original main epilogue scene 21 remains intact and reaches its own ending','title, chapter list, menu, CONFIG and grouped CG gallery render','EXIT completes native app lifecycle and app reopens after teardown','unlocked first-row AFTER STORY works after app restart');
 const recent=logs().slice(begin);assert.ok(!/STELLA_RW5 error|STELLA_RW5 background failed|ASSERTION FAILED|PANIC!!!|coredump/.test(recent));
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'src/manifest.json'),'utf8')),rpk=path.join(root,'dist',manifest.package+'.debug.'+manifest.versionName+'.rpk');
 const report={version:manifest.versionName,result:'passed',runtime:'official vela-watch-5.0 emulator; not REDMI Watch 5 firmware',screen:[432,514],packageBytes:fs.statSync(rpk).size,packageSha256:crypto.createHash('sha256').update(fs.readFileSync(rpk)).digest('hex'),coldUpgradeRepresentativeSlots:[1,30],initialLockedStateOnThisPackage:!alreadyUnlocked,lockedStateEvidence:'17 automated tests and candidate c246905d native title-locked/main-clear-unlock screenshots in v021-second',historicalFull30SlotReport:'native-test-results/v020/report.json',physicalDeviceTested:false,checks};
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log('UI_NATIVE_PASSED',JSON.stringify(report));
})().catch(e=>{fs.writeFileSync(path.join(out,'failure.txt'),e.stack);console.error(e.stack);process.exitCode=1;});
