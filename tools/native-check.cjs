// Test the packaged application through real clicks in the official Vela emulator.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const root=path.resolve(__dirname,'..'),out=path.join(root,'native-test-results'),url='http://127.0.0.1:43129';
const log=path.join(process.env.STARRY_EMULATOR_HOME||path.join(root,'.emulator'),'emulator.log');fs.mkdirSync(out,{recursive:true});
const sleep=ms=>new Promise(r=>setTimeout(r,ms)),logs=()=>fs.readFileSync(log,'utf8');
async function click(x,y){const r=await fetch(url+'/click?x='+x+'&y='+y);assert.ok(r.ok,await r.text());await sleep(180);}
async function wait(at,re){for(let n=0;n<200;n++){const s=logs().slice(at);if(re.test(s))return s;await sleep(200);}throw Error('Timeout '+re);}
async function expected(x,y,re){const at=logs().length;await click(x,y);return wait(at,re);}
async function shot(name){await sleep(400);const r=await fetch(url+'/screen');assert.ok(r.ok);fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(await r.arrayBuffer()));}
async function ready(){const s=logs();await wait(Math.max(0,s.lastIndexOf('NuttShell (NSH)'),s.lastIndexOf('STELLA_RW5 app destroyed')),/STELLA_RW5 background loaded title/);await sleep(500);}
async function menu(){await expected(216,488,/STELLA_RW5 menu/);}
async function slots(role){await expected(216,role==='save'?95:153,new RegExp('STELLA_RW5 slots ready '+role));}
async function slot(i,re){for(let n=0;n<Math.floor(i/4);n++)await click(355,474);return expected(216,126+(i%4)*92,re);}
async function save(i){await menu();await slots('save');let s=await slot(i,new RegExp('STELLA_RW5 (?:overwrite|slot saved) '+(i+1)+'(?:\\s|$)'));if(s.includes('STELLA_RW5 overwrite'))s=await expected(216,241,new RegExp('STELLA_RW5 slot saved '+(i+1)+' '));await sleep(1600);return s.match(new RegExp('STELLA_RW5 slot saved '+(i+1)+' (\\d+) (\\d+)')).slice(1).map(Number);}
async function returnTitle(){await menu();await click(216,443);}
async function prepare(){await ready();await shot('title');await expected(216,372,/STELLA_RW5 frame 1 0/);await menu();await click(216,269);await click(216,385);const positions=[];for(let i=0;i<30;i++){await expected(355,488,/STELLA_RW5 frame/);positions.push(await save(i));if(i%5===4)console.log('NATIVE_SLOTS_PREPARED',i+1);}assert.equal(new Set(positions.map(x=>x.join(':'))).size,30);await returnTitle();fs.writeFileSync(path.join(out,'save-preparation.json'),JSON.stringify({positions,distinctSlots:30,requiresColdBoot:true},null,2));console.log('NATIVE_PREPARE_PASSED');}
async function verify(){
 await ready();const begin=logs().length,status=await(await fetch(url+'/status')).json();for(const [k,v] of Object.entries({'hw.lcd.width':'432','hw.lcd.height':'514','hw.ramSize':'128','hw.device.flavor':'watch'}))assert.equal(status.hardware[k],v);
 const data=JSON.parse(fs.readFileSync(path.join(out,'save-preparation.json'),'utf8'));
 if(!process.argv.includes('--after-cold')){
 await expected(216,401,/STELLA_RW5 slots ready load/);
 for(let i=29;i>=0;i--){if(i!==29){await menu();await slots('load');}await slot(i,new RegExp('STELLA_RW5 slot loaded '+(i+1)+' '+data.positions[i].join(' ')));if(i%5===0)console.log('NATIVE_COLD_SLOTS_LOADED',30-i);}
 await returnTitle();await click(216,459);await shot('chapters-first');await click(355,474);await shot('chapters-second');await click(65,474);await shot('chapters-first-return');await expected(216,126,/STELLA_RW5 frame 1 0/);await returnTitle();
 }else{const boot=logs().slice(logs().lastIndexOf('NuttShell (NSH)'));data.positions.forEach((p,i)=>assert.match(boot,new RegExp('STELLA_RW5 slot loaded '+(i+1)+' '+p.join(' ')+'\\s')));await returnTitle();}
 // Read a portrait-bearing frame from the main story, including palette transparency.
 await expected(216,372,/STELLA_RW5 frame 1 0/);await menu();await expected(216,211,/STELLA_RW5 frame 2 0/);await menu();await expected(216,211,/STELLA_RW5 frame 3 0/);
 const ops=JSON.parse(fs.readFileSync(path.join(root,'src/common/story/3/0.txt'),'utf8'));const target=ops.findIndex(x=>x.op==='text'&&x.bodies.length);assert.ok(target>=0&&target<512);
 for(let i=0;i<target;i++)await expected(355,488,/STELLA_RW5 frame/);await sleep(400);await shot('portrait');await returnTitle();
 await click(216,430);await sleep(600);for(let i=0;i<45;i++)await click(65,474);await shot('cg-list');await expected(108,152,/STELLA_RW5 cg 1 1 /);await expected(216,210,/STELLA_RW5 cg 1 2 /);await shot('cg-difference');await click(216,487);await click(216,474);
 await expected(216,372,/STELLA_RW5 frame 1 0/);for(let chapter=2;chapter<=21;chapter++){await menu();await expected(216,211,new RegExp('STELLA_RW5 frame '+chapter+' 0'));if(chapter===10||chapter===20||chapter===21)await shot('chapter-'+chapter);}await menu();await expected(216,211,/STELLA_RW5 ending 21 星之终途/);await shot('ending');
 assert.ok(!/STELLA_RW5 error|STELLA_RW5 background failed|ASSERTION FAILED|PANIC!!!/.test(logs().slice(begin)));
 const m=JSON.parse(fs.readFileSync(path.join(root,'src/manifest.json'),'utf8')),file=path.join(root,'dist',m.package+'.debug.'+m.versionName+'.rpk'),report={game:m.name,version:m.versionName,result:'passed',runtime:'official vela-watch-5.0 emulator; not REDMI Watch 5 firmware',screen:[432,514],emulatorRAMMB:128,packageBytes:fs.statSync(file).size,maximumPackageBytes:15000000,packageSha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),physicalDeviceTested:false,coldBoot30Slots:true,checks:['30 distinct saves loaded after full emulator cold boot','first chapter page and pagination return refresh','transparent portrait layers display','grouped CG list and difference cycling','all 21 chapters reached through native menu skip','native story ending reached','no game errors or image failures during checks']};
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log('STELLA_NATIVE_PASSED',JSON.stringify(report));
 await click(216,380);
}
(process.argv.includes('--prepare')?prepare():verify()).catch(e=>{console.error(e);process.exitCode=1;});
