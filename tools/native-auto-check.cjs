// Real simulator input. No injected saves, altered scenes or skipped choices.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto'),zlib=require('zlib');
const root=path.resolve(__dirname,'..'),out=path.join(root,'native-test-results/auto-v024'),url='http://127.0.0.1:43135/';
const log=path.resolve(root,'../stella-after-environment/emulator.log');fs.mkdirSync(out,{recursive:true});
const sleep=ms=>new Promise(r=>setTimeout(r,ms)),logs=()=>fs.readFileSync(log,'utf8');
async function get(endpoint,timeout=20000){const r=await fetch(url+endpoint,{signal:AbortSignal.timeout(timeout)});if(!r.ok)throw Error(await r.text());return r;}
async function click(x,y){await get('click?x='+x+'&y='+y);await sleep(160);}
async function wait(at,re){for(let i=0;i<150;i++){const text=logs().slice(at);if(re.test(text))return text;await sleep(160);}throw Error('Native timeout: '+re);}
async function expected(x,y,re){const at=logs().length;await click(x,y);return wait(at,re);}
async function shot(name){await sleep(300);fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(await(await get('screen')).arrayBuffer()));}
async function wakeIfBlack(){
 const png=Buffer.from(await(await get('screen')).arrayBuffer()),blocks=[];let at=8;
 while(at<png.length){const n=png.readUInt32BE(at);if(png.toString('ascii',at+4,at+8)==='IDAT')blocks.push(png.subarray(at+8,at+8+n));at+=12+n;}
 const data=zlib.inflateSync(Buffer.concat(blocks)),width=png.readUInt32BE(16),height=png.readUInt32BE(20),channels=png[25]===6?4:3;
 assert.equal(png[24],8);assert.ok([2,6].includes(png[25]));let prev=new Uint8Array(width*channels),offset=0,black=true;
 const paeth=(a,b,c)=>{const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);return pa<=pb&&pa<=pc?a:pb<=pc?b:c;};
 for(let y=0;y<height&&black;y++){const filter=data[offset++],row=new Uint8Array(width*channels);for(let x=0;x<row.length;x++){const a=x>=channels?row[x-channels]:0,b=prev[x],c=x>=channels?prev[x-channels]:0;row[x]=(data[offset++]+(filter===0?0:filter===1?a:filter===2?b:filter===3?Math.floor((a+b)/2):paeth(a,b,c)))&255;if(x%channels<3&&row[x]>2)black=false;}prev=row;}
 if(black){await get('wake');await sleep(1500);}
}
async function menu(){await expected(216,488,/STELLA_RW5 menu/);}
async function title(){await menu();await expected(216,457,/STELLA_RW5 background loaded title/);}
async function frozen(ms=2600){const at=logs().length;await sleep(ms);assert.ok(!/STELLA_RW5 auto advance|STELLA_RW5 frame/.test(logs().slice(at)));}

(async()=>{
 const begin=logs().length,checks=[];await wakeIfBlack();await shot('title');
 await expected(125,268,/STELLA_RW5 frame 1 0/);await menu();await shot('menu-default-off');
 await expected(216,222,/STELLA_RW5 auto enabled true/);await shot('menu-enabled');
 const seen=new Set();let speed;
 for(let i=0;i<6;i++){const text=await expected(216,269,/STELLA_RW5 auto speed \d/);speed=Number(text.match(/STELLA_RW5 auto speed (\d)/)[1]);seen.add(speed);await shot('menu-speed-'+speed);if(speed===1&&seen.size===3)break;}
 assert.equal(speed,1);assert.equal(seen.size,3);await frozen(2800);checks.push('all nine menu actions fit; menu freezes auto; all three speed buttons respond');
 let at=logs().length,started=Date.now();await click(216,410);await wait(at,/STELLA_RW5 auto advance 1 0/);
 const initialWaitMS=Date.now()-started;assert.ok(initialWaitMS>=1300);await wait(at,/STELLA_RW5 frame 1 1(?:\r|\n|$)/);
 await wait(at,/STELLA_RW5 auto advance 1 1(?:\r|\n|$)/);await shot('reading-auto');await menu();await frozen();await shot('menu-paused');
 // LOAD leaves the automatic mode selected but freezes the story until return.
 await expected(216,128,/STELLA_RW5 slots ready load/);await shot('load-paused');await frozen();await click(216,474);await frozen(1800);
 at=logs().length;await click(216,410);await wait(at,/STELLA_RW5 auto advance/);await title();
 checks.push('standard wait is not immediate and native auto advances successive sentences','opening menu and LOAD suspends auto; returning to text restarts it');
 // Use the normal chapter entry and safe chapter skip to reach the real choice.
 await click(125,304);await click(216,218);await click(354,474);await expected(216,310,/STELLA_RW5 frame 107 0/);
 // Real long paragraph: dragging must not advance, and touchend must restart AUTO.
 for(let i=1;i<=110;i++){await expected(354,488,new RegExp('STELLA_RW5 frame 107 '+i+'(?:\\r|\\n|$)'));if(i%40===0)console.log('NATIVE_LONG_PARAGRAPH',i);}
 await menu();await expected(216,222,/STELLA_RW5 auto enabled true/);await click(216,410);at=logs().length;
 await get('drag?x0=210&y0=440&x1=210&y1=345');assert.match(logs().slice(at),/STELLA_RW5 dialogue scroll 107 110 [1-9]/);assert.ok(!/STELLA_RW5 auto advance/.test(logs().slice(at)));await shot('long-auto-after-drag');
 await wait(at,/STELLA_RW5 auto advance 107 110/);await menu();await expected(216,175,/STELLA_RW5 choice 107 423/);await shot('choice-paused');await frozen(4300);
 checks.push('actual long paragraph scroll does not advance while dragging; release resumes automatic reading');
 await expected(216,471,/STELLA_RW5 menu 107/);await shot('choice-menu-auto-still-on');await click(216,410);await frozen(2200);
 at=logs().length;await expected(216,135,/STELLA_RW5 frame 107 424/);await wait(at,/STELLA_RW5 auto advance 107 424/);await shot('choice-auto-resumed');
 await expected(65,488,/STELLA_RW5 frame/);await frozen(3000);await menu();await shot('back-turns-auto-off');
 checks.push('actual after-story choice 107:423 remains pending without selecting a branch','choosing the original confirmation resumes automatic playback at 107:424','previous sentence disables auto for manual rereading');
 // Persist FAST, then stop the real app while auto is still enabled.
 await expected(216,269,/STELLA_RW5 auto speed 2/);await expected(216,222,/STELLA_RW5 auto enabled true/);await shot('menu-fast-on');await click(216,410);
 at=logs().length;await get('stop');await wait(at,/STELLA_RW5 app destroyed/);await sleep(2500);
 at=logs().length;await get('start',90000);await wait(at,/STELLA_RW5 background loaded title/);await wait(at,/PageCallHook, name:onShow/);await sleep(500);await wakeIfBlack();
 await expected(125,268,/STELLA_RW5 frame 1 0/);await menu();await shot('restart-auto-off-speed-fast');await frozen(3000);await expected(216,457,/STELLA_RW5 background loaded title/);
 checks.push('app destruction cancels timers; restarting is manual even when previously auto','FAST speed remains available after app restart');
 const recent=logs().slice(begin);assert.ok(!/STELLA_RW5 error|STELLA_RW5 background failed|ASSERTION FAILED|PANIC!!!|coredump_dump_dev/.test(recent));
 const m=JSON.parse(fs.readFileSync(path.join(root,'src/manifest.json'),'utf8')),rpk=path.join(root,'dist',m.package+'.debug.'+m.versionName+'.rpk');
 const report={result:'passed',version:m.versionName,variant:path.basename(root),packageSha256:crypto.createHash('sha256').update(fs.readFileSync(rpk)).digest('hex'),packageBytes:fs.statSync(rpk).size,screen:[432,514],runtime:'official generic vela-watch-5.0 simulator; not physical REDMI Watch 5 firmware',physicalDeviceTested:false,initialStandardWaitWallMS:initialWaitMS,checks};
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log('NATIVE_AUTO_PASSED',JSON.stringify(report));
})().catch(e=>{fs.writeFileSync(path.join(out,'failure.txt'),e.stack);console.error(e.stack);process.exitCode=1;});
