const fs=require('fs'),path=require('path'),root=path.resolve(__dirname,'..'),url='http://127.0.0.1:43135';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function get(endpoint){const r=await fetch(url+'/'+endpoint,{signal:AbortSignal.timeout(120000)});if(!r.ok)throw Error(await r.text());return r;}
(async()=>{
 await get('stop');
 const baseline=path.resolve(root,'../../outputs/星之终途-RW5-0.1.0-r1.rpk');
 console.log('BASELINE_INSTALL',await(await get('install?rpk='+encodeURIComponent(baseline))).text());
 console.log('BASELINE_START',await(await get('start')).text());await sleep(1500);
 fs.writeFileSync(path.join(root,'native-test-results/v020/baseline-display.png'),Buffer.from(await(await get('screen')).arrayBuffer()));
 console.log('BASELINE_CAPTURED');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
