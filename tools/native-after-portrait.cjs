const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve(__dirname,'..'),url='http://127.0.0.1:43135',log=path.resolve(root,'../stella-after-environment/emulator.log');
const sleep=ms=>new Promise(r=>setTimeout(r,ms)),logs=()=>fs.readFileSync(log,'utf8');
async function get(endpoint){const r=await fetch(url+'/'+endpoint,{signal:AbortSignal.timeout(10000)});if(!r.ok)throw Error(await r.text());return r;}
async function click(x,y){await get('click?x='+x+'&y='+y);await sleep(130);}
async function expected(x,y,re){const at=logs().length;await click(x,y);for(let i=0;i<75;i++){if(re.test(logs().slice(at)))return;await sleep(100);}throw Error('Portrait check timeout '+re);}
(async()=>{
 await click(125,304);await click(216,218);await expected(216,218,/STELLA_RW5 frame 102 0/);
 const ops=JSON.parse(fs.readFileSync(path.join(root,'src/common/story/102/0.txt'),'utf8')),target=ops.findIndex(x=>x.bodies?.length);assert.equal(target,99);
 for(let i=1;i<=target;i++)await expected(354,488,new RegExp('STELLA_RW5 frame 102 '+i+'\\s'));
 await sleep(400);const out=path.join(root,'native-test-results/v020');
 fs.writeFileSync(path.join(out,'after-portrait.png'),Buffer.from(await(await get('screen')).arrayBuffer()));
 const reportPath=path.join(out,'report.json'),report=JSON.parse(fs.readFileSync(reportPath,'utf8'));report.checks.push('after-story transparent portrait displayed at 102:99');
 fs.writeFileSync(reportPath,JSON.stringify(report,null,2));console.log('AFTER_PORTRAIT_PASSED');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
