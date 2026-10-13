const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'native-test-results/v020'),url='http://127.0.0.1:43135';
fs.mkdirSync(out,{recursive:true});
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function get(endpoint,timeout=30000){const response=await fetch(url+'/'+endpoint,{signal:AbortSignal.timeout(timeout)});if(!response.ok)throw Error(await response.text());return response;}
(async()=>{
 for(let i=0;i<30;i++){try{const response=await get('info',3000);console.log('INFO',await response.text());break;}catch(error){if(i===29)throw error;await sleep(1000);}}
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'src/manifest.json'),'utf8'));
 const rpk=path.join(root,'dist',manifest.package+'.debug.'+manifest.versionName+'.rpk');
 console.log('INSTALL',await(await get('install?rpk='+encodeURIComponent(rpk),120000)).text());
 console.log('START',await(await get('start',90000)).text());
 await sleep(2500);
 fs.writeFileSync(path.join(out,'title.png'),Buffer.from(await(await get('screen')).arrayBuffer()));
 await get('click?x=125&y=268');await sleep(1500);
 fs.writeFileSync(path.join(out,'after-intro.png'),Buffer.from(await(await get('screen')).arrayBuffer()));
 console.log('BOOTSTRAP_PASSED');
})().catch(error=>{console.error(error.message);process.exitCode=1;});
