// Real input, screenshots and persisted saves in the isolated official simulator.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const root=path.resolve(__dirname,'..'),out=path.join(root,'native-test-results/v020'),url='http://127.0.0.1:43135';
const log=path.resolve(root,'../stella-after-environment/emulator.log');
const sleep=ms=>new Promise(r=>setTimeout(r,ms)),logs=()=>fs.readFileSync(log,'utf8');
async function request(endpoint,timeout=20000){const r=await fetch(url+'/'+endpoint,{signal:AbortSignal.timeout(timeout)});if(!r.ok)throw Error(await r.text());return r;}
async function click(x,y){await request('click?x='+x+'&y='+y);await sleep(160);}
async function wait(at,re){for(let i=0;i<100;i++){const text=logs().slice(at);if(re.test(text))return text;await sleep(200);}throw Error('Native timeout: '+re);}
async function expected(x,y,re){const at=logs().length;await click(x,y);return wait(at,re);}
async function shot(name){await sleep(300);fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(await(await request('screen')).arrayBuffer()));}
async function menu(){await expected(216,488,/STELLA_RW5 menu/);}
async function title(){await menu();await expected(216,447,/STELLA_RW5 background loaded title/);}
async function openSlots(role){await expected(216,role==='save'?99:157,new RegExp('STELLA_RW5 slots ready '+role));}
async function slot(index,re){for(let page=0;page<Math.floor(index/4);page++)await click(354,474);return expected(216,126+(index%4)*92,re);}
async function save(index){await menu();await openSlots('save');const re=new RegExp('STELLA_RW5 (?:overwrite|slot saved) '+(index+1)+'(?:\\s|$)');let text=await slot(index,re);if(text.includes('STELLA_RW5 overwrite'))text=await expected(216,240,new RegExp('STELLA_RW5 slot saved '+(index+1)+' '));await sleep(1550);return text.match(new RegExp('STELLA_RW5 slot saved '+(index+1)+' (\\d+) (\\d+)')).slice(1).map(Number);}

async function prepare(){
 const begin=logs().length,positions=[];
 if(process.argv.includes('--resume-tests')){
  const rows=Array.from(logs().matchAll(/STELLA_RW5 slot saved (\d+) (\d+) (\d+)/g)).slice(-30);
  assert.equal(rows.length,30);rows.forEach((row,i)=>{assert.equal(Number(row[1]),i+1);positions.push([Number(row[2]),Number(row[3])]);});
  assert.equal(new Set(positions.map(p=>p.join(':'))).size,30);
  return finishChoice(positions,begin);
 }
 await shot('title');
 await expected(125,268,/STELLA_RW5 frame 101 0/);await shot('after-intro');
 await menu();await click(216,273);await click(216,389);
 for(let i=0;i<30;i++){
  if(i)await expected(354,488,/STELLA_RW5 frame/);
  positions.push(await save(i));
  if(i%5===4)console.log('AFTER_NATIVE_SAVES',i+1);
 }
 assert.equal(new Set(positions.map(p=>p.join(':'))).size,30);
 await shot('after-dialogue');await title();
 // New CHAPTER entry presents the two stories, with fresh first pages.
 await click(125,304);await shot('routes');await click(216,218);await shot('after-chapters-first');
 await click(354,474);await shot('after-chapters-second');await click(65,474);await shot('after-chapters-first-return');
 await click(216,474);await shot('routes-return');await click(216,126);await shot('main-chapters-first');
 await click(216,126);await wait(begin,/STELLA_RW5 frame 1 0/);await shot('main-dialogue');await title();
 await click(125,376);await shot('settings');await click(216,240);
 await click(125,412);await wait(begin,/STELLA_RW5 gallery ready/);await shot('gallery');
 await click(108,146);await wait(begin,/STELLA_RW5 cg/);await shot('cg');await click(216,205);await shot('cg-difference');
 await click(216,487);await click(216,474);
 // Route 1, second chapter page, row 3 is after-story chapter six.
 await click(125,304);await click(216,218);await click(354,474);
 await expected(216,310,/STELLA_RW5 frame 107 0/);await menu();
 await expected(216,215,/STELLA_RW5 choice 107 423/);await shot('after-choice');
 await finishChoice(positions,begin);
}
async function finishChoice(positions,begin){
 for(let i=0;i<2;i++){
  await expected(216,471,/STELLA_RW5 menu 107/);const at=logs().length;await click(216,215);await sleep(1700);await shot('after-choice-repeat-'+i);
  assert.ok(!/STELLA_RW5 frame 107 424/.test(logs().slice(at)));
  assert.deepEqual(fs.readFileSync(path.join(out,'after-choice-repeat-'+i+'.png')),fs.readFileSync(path.join(out,'after-choice.png')));
 }
 // Slot 30 preserves the still-pending confirmation, replacing its preparation save.
 await expected(216,471,/STELLA_RW5 menu 107/);await openSlots('save');
 await slot(29,/STELLA_RW5 overwrite 30/);await expected(216,240,/STELLA_RW5 slot saved 30 107 423/);await sleep(1550);
 positions[29]=[107,423];
 await expected(216,135,/STELLA_RW5 frame 107 424/);await menu();await expected(216,215,/STELLA_RW5 frame 108 0/);await shot('after-final-chapter');
 await menu();await expected(216,215,/STELLA_RW5 ending 108 AFTER STORY/);await shot('after-ending');
 await expected(216,280,/STELLA_RW5 background loaded title/);
 // EXIT ends the real app lifecycle and it can subsequently reopen.
 await expected(125,448,/STELLA_RW5 app destroyed/);await request('start',90000);await sleep(1000);await shot('title-after-exit');
 const recent=logs().slice(begin);assert.ok(!/STELLA_RW5 error|STELLA_RW5 background failed|ASSERTION FAILED|PANIC!!!/.test(recent));
 fs.writeFileSync(path.join(out,'save-preparation.json'),JSON.stringify({positions,distinctSlots:30,slot30Mode:'choice',requiresColdBoot:true,checks:['native title START and AFTER STORY entries','white dialogue on forest green','two-story first-page navigation','main story opens independently','CONFIG and grouped CG gallery','chapter skip stops at actual after-story choice twice','choice save and correct target 107:424','after-story final chapter and ending','EXIT app lifecycle and reopen']},null,2));
 console.log('AFTER_NATIVE_PREPARE_PASSED');
}

async function cold(){
 const begin=logs().length,data=JSON.parse(fs.readFileSync(path.join(out,'save-preparation.json'),'utf8'));
 const status=await(await request('status')).json();assert.equal(status.hardware['hw.lcd.width'],'432');assert.equal(status.hardware['hw.lcd.height'],'514');assert.equal(status.hardware['hw.ramSize'],'128');
 await expected(125,340,/STELLA_RW5 slots ready load/);
 for(let i=29;i>=0;i--){
  if(i!==29){if(i===28)await expected(216,471,/STELLA_RW5 menu 107/);else await menu();await openSlots('load');}
  await slot(i,new RegExp('STELLA_RW5 slot loaded '+(i+1)+' '+data.positions[i].join(' ')));
  if(i===29){await shot('choice-loaded-cold');assert.match(logs().slice(begin),/STELLA_RW5 choice 107 423/);}
  if(i%5===0)console.log('AFTER_NATIVE_COLD_RESTORED',30-i);
 }
 await title();await shot('title-cold');
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'src/manifest.json'),'utf8')),rpk=path.join(root,'dist',manifest.package+'.debug.'+manifest.versionName+'.rpk');
 assert.ok(!/STELLA_RW5 error|STELLA_RW5 background failed|ASSERTION FAILED|PANIC!!!/.test(logs().slice(begin)));
 const report={version:manifest.versionName,result:'passed',runtime:'official vela-watch-5.0 emulator; not REDMI Watch 5 firmware',screen:[432,514],emulatorRAMMB:128,packageBytes:fs.statSync(rpk).size,packageSha256:crypto.createHash('sha256').update(fs.readFileSync(rpk)).digest('hex'),coldBoot30Slots:true,coldPendingAfterChoicePreserved:true,physicalDeviceTested:false,checks:data.checks.concat(['all 30 distinct saves restored after complete simulator restart','pending after-story confirmation restored with correct text and target','no application errors or image load failures in successful runs']),emulatorDisplayNote:'The isolated virtual screen initially needed a simulated Power key wake; early failed/black captures are kept separately.'};
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log('AFTER_NATIVE_PASSED',JSON.stringify(report));
}
(process.argv.includes('--cold')?cold():prepare()).catch(e=>{console.error(e.message);process.exitCode=1;});
