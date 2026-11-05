const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),zlib=require('zlib');
const root=path.resolve(__dirname,'..'),url=process.env.STELLA_CONTROL_URL||'http://127.0.0.1:43154/';
const environment=process.env.STARRY_EMULATOR_HOME||path.resolve(root,'../stella-layout-environment');
const baseline=process.argv.includes('--baseline'),out=path.join(root,'native-test-results/layout-v013',baseline?'before':'after');
fs.mkdirSync(out,{recursive:true});const log=path.join(environment,'emulator.log');
const sleep=ms=>new Promise(r=>setTimeout(r,ms)),logs=()=>fs.readFileSync(log,'utf8');
async function get(p,timeout=30000){const r=await fetch(url+p,{signal:AbortSignal.timeout(timeout)});if(!r.ok)throw Error(await r.text());return r;}
async function wait(at,re){for(let i=0;i<160;i++){if(re.test(logs().slice(at)))return logs().slice(at);await sleep(180);}throw Error('Timeout: '+re);}
async function click(x,y){await get(`click?x=${x}&y=${y}`);await sleep(180);}
async function expected(x,y,re){const at=logs().length;await click(x,y);return wait(at,re);}
async function shot(name){await sleep(350);const data=Buffer.from(await(await get('screen')).arrayBuffer());fs.writeFileSync(path.join(out,name+'.png'),data);return data;}
async function menu(){return expected(168,448,/STELLA_BAND8PRO menu/);}
async function title(){await menu();await expected(168,423,/STELLA_BAND8PRO background loaded title/);}
async function drag(){return get('drag?x0=168&y0=395&x1=168&y1=310');}
async function ensureAwake(){
 const png=await shot('initial');if(png.length<2000){await get('wake');await sleep(1200);}
}
(async()=>{
 if(process.argv.includes('--install')){
  const name=baseline?'0.1.2':'0.1.3';
  const binary=baseline?path.resolve(process.env.STELLA_BASELINE_BIN||path.join(root,'dist','com.codex.stella.band8pro.debug.0.1.2.rpk')):path.join(root,'dist','com.codex.stella.band8pro.debug.'+name+'.rpk');
  await get('stop').catch(()=>{});console.log('INSTALL',await(await get('install?rpk='+encodeURIComponent(binary),240000)).text());
  const at=logs().length;await get('start',90000);await wait(at,/STELLA_BAND8PRO background loaded title/);await sleep(800);await ensureAwake();
 }
 if(process.argv.includes('--fresh')){
  await expected(110,221,/STELLA_BAND8PRO frame 1 0/);await menu();await click(168,291);await click(168,379);
  for(let i=1;i<=21;i++){await menu();await expected(168,159,i<21?new RegExp('STELLA_BAND8PRO frame '+(i+1)+' 0(?:\\r|\\n|$)'):/STELLA_BAND8PRO ending 21/);}
  await expected(168,274,/STELLA_BAND8PRO background loaded title/);
 }
 // Follow the reported path: scroll both long introduction paragraphs, then continue.
 if(!process.argv.includes('--in-after'))await expected(110,221,/STELLA_BAND8PRO frame 101 0(?:\r|\n|$)/);
 for(let i=1;i<=8;i++){
  await expected(285,448,new RegExp('STELLA_BAND8PRO frame 101 '+i+'(?:\\r|\\n|$)'));
  if(i===1||i===4){await drag();await shot('intro-scrolled-'+i);}
 }
 await expected(285,448,/STELLA_BAND8PRO frame 102 0(?:\r|\n|$)/);await shot('102-0');
 await expected(285,448,/STELLA_BAND8PRO frame 102 1(?:\r|\n|$)/);await shot('reported-102-1');
 await expected(285,448,/STELLA_BAND8PRO frame 102 2(?:\r|\n|$)/);await shot('102-2');
 await expected(45,448,/STELLA_BAND8PRO frame 102 1(?:\r|\n|$)/);await shot('reported-102-1-back');
 console.log('REPORTED_PATH_CAPTURED',out);
})().catch(e=>{fs.writeFileSync(path.join(out,'failure.txt'),e.stack);console.error(e.stack);process.exitCode=1;});
