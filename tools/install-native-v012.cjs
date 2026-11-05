const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..'),url='http://127.0.0.1:43152/';
const manifest=JSON.parse(fs.readFileSync(path.join(root,'src/manifest.json'),'utf8'));
const rpk=path.join(root,'dist',manifest.package+'.debug.'+manifest.versionName+'.rpk');
async function get(p){const r=await fetch(url+p,{signal:AbortSignal.timeout(240000)});if(!r.ok)throw Error(await r.text());return r;}
(async()=>{
 console.log('INSTALL',await(await get('install?rpk='+encodeURIComponent(rpk))).text());
 console.log('START',await(await get('start')).text());
 await new Promise(r=>setTimeout(r,2500));
 fs.mkdirSync(path.join(root,'native-test-results/band-v012'),{recursive:true});
 fs.writeFileSync(path.join(root,'native-test-results/band-v012/initial.png'),Buffer.from(await(await get('screen')).arrayBuffer()));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
