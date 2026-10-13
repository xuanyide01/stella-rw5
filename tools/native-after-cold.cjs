const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..'),url='http://127.0.0.1:43135';
(async()=>{
 const environment=path.resolve(root,'../stella-after-environment');
 const raw=fs.readFileSync(path.join(environment,'emulator.log'),'utf8');
 fs.writeFileSync(path.join(root,'reports/native-v020-first-boot.json'),JSON.stringify({result:'not_verified',firstScreens:'black; inputs not observed in app log',hotReinstall:'runtime coredump during comparison with the historical package',scope:'isolated official emulator only',requires:'full cold restart and current-package retest',physicalDeviceTested:false},null,2));
 fs.writeFileSync(path.join(root,'native-test-results/v020/first-boot-emulator.log'),raw);
 const response=await fetch(url+'/shutdown',{signal:AbortSignal.timeout(20000)});console.log('SHUTDOWN',response.status,await response.text());
})().catch(e=>{console.error(e.message);process.exitCode=1;});
