const fs=require('fs'),path=require('path');
const {getRunningAvdConfigByName}=require('@aiot-toolkit/emulator/lib/emulatorutil/running');
const {createGrpcClient}=require('@aiot-toolkit/emulator/lib/vvd/grpc');
(async()=>{
 const config=getRunningAvdConfigByName('StellaAfterRW5-432x514');if(!config)throw Error('Isolated emulator is not running');
 const agent=createGrpcClient(config);await agent.waitForReady();
 agent.sendKey({key:'Power',eventType:2});await new Promise(r=>setTimeout(r,1200));
 const response=await fetch('http://127.0.0.1:43135/screen',{signal:AbortSignal.timeout(10000)});
 if(!response.ok)throw Error(await response.text());
 const output=process.env.WATCH_WAKE_OUTPUT||path.resolve(__dirname,'../native-test-results/v021/wake-screen.png');
 fs.writeFileSync(output,Buffer.from(await response.arrayBuffer()));
 agent.close();console.log('WAKE_CAPTURED');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
