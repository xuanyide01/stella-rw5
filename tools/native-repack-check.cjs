// Run after an emulator cold boot, before starting the game, to avoid inspector restart races.
// Reinstall the exact r1 artifact and smoke-test it; full gameplay baseline stays separate.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const root=path.resolve(__dirname,'..'),out=path.join(root,'native-test-results'),base='http://127.0.0.1:43129';
const log=path.join(process.env.STARRY_EMULATOR_HOME||path.join(root,'.emulator'),'emulator.log');
const m=JSON.parse(fs.readFileSync(path.join(root,'src/manifest.json'),'utf8'));
const file=path.join(root,'dist',m.package+'.debug.'+m.versionName+'.rpk');
const sha=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const audit=JSON.parse(fs.readFileSync(path.join(root,'reports/installation-fix-audit.json'),'utf8'));
assert.equal(sha,audit.candidate.sha256);
const sleep=ms=>new Promise(r=>setTimeout(r,ms)),logs=()=>fs.readFileSync(log,'utf8');
async function request(endpoint){const r=await fetch(base+endpoint);assert.ok(r.ok,await r.clone().text());return r;}
async function click(x,y){await request('/click?x='+x+'&y='+y);await sleep(250);}
async function wait(at,re){for(let n=0;n<200;n++){const s=logs().slice(at);if(re.test(s))return s;await sleep(200);}throw Error('Timeout '+re);}
async function expected(x,y,re){const at=logs().length;await click(x,y);return wait(at,re);}
async function shot(name){await sleep(500);fs.writeFileSync(path.join(out,'r1-'+name+'.png'),Buffer.from(await(await request('/screen')).arrayBuffer()));}
async function menu(){await expected(216,488,/STELLA_RW5 menu/);}
async function title(){await menu();await expected(216,443,/STELLA_RW5 background loaded title/);}
(async()=>{
 for(let i=0;i<200;i++){const s=logs();if(s.lastIndexOf('NuttShell (NSH)')>s.lastIndexOf('Setting display: 0'))break;await sleep(200);}
 assert.ok(logs().lastIndexOf('NuttShell (NSH)')>logs().lastIndexOf('Setting display: 0'),'Emulator has not completed boot');
 const begin=logs().length;
 // am stop only backgrounds an activity in this SDK; do not race a live JS runtime.
 const boot=logs().slice(logs().lastIndexOf('NuttShell (NSH)'));
 assert.ok(!/STELLA_RW5 app created/.test(boot),'Cold boot the emulator before this check');
 const installation=await(await request('/install?rpk='+encodeURIComponent(file))).json();
 assert.match(installation,/success 0/);
 const start=logs().length;await request('/start');await wait(start,/STELLA_RW5 background loaded title/);await shot('title');
 const status=await(await request('/status')).json();
 for(const [key,value] of Object.entries({'hw.lcd.width':'432','hw.lcd.height':'514','hw.ramSize':'128'}))assert.equal(status.hardware[key],value);
 const saved=JSON.parse(fs.readFileSync(path.join(out,'save-preparation.json'),'utf8'));
 await expected(216,401,/STELLA_RW5 slots ready load/);
 await expected(216,126,new RegExp('STELLA_RW5 slot loaded 1 '+saved.positions[0].join(' ')));
 await menu();await expected(216,153,/STELLA_RW5 slots ready load/);
 for(let i=0;i<7;i++)await click(355,474);
 await expected(216,218,new RegExp('STELLA_RW5 slot loaded 30 '+saved.positions[29].join(' ')));
 await menu();await expected(216,95,/STELLA_RW5 slots ready save/);
 for(let i=0;i<7;i++)await click(355,474);
 await expected(216,218,/STELLA_RW5 overwrite 30/);
 await expected(216,241,new RegExp('STELLA_RW5 slot saved 30 '+saved.positions[29].join(' ')));await sleep(1200);
 await title();await click(216,459);await shot('chapters-first');await click(355,474);await shot('chapters-second');await click(65,474);await shot('chapters-first-return');
 await expected(216,402,/STELLA_RW5 frame 4 0/);
 const ops=JSON.parse(fs.readFileSync(path.join(root,'src/common/story/4/0.txt'),'utf8'));
 const target=ops.findIndex(x=>x.op==='text'&&x.bodies.length);assert.ok(target>=0&&target<16);
 for(let i=0;i<target;i++)await expected(355,488,/STELLA_RW5 frame/);await shot('portrait');
 await menu();await expected(216,211,/STELLA_RW5 frame 5 0/);await title();
 await expected(216,430,/STELLA_RW5 gallery ready 177 308/);await shot('cg-list');
 await expected(108,152,/STELLA_RW5 cg 1 1 /);await expected(216,210,/STELLA_RW5 cg 1 2 /);await shot('cg-difference');
 await click(216,487);await expected(216,474,/STELLA_RW5 background loaded title/);
 assert.ok(!/STELLA_RW5 error|STELLA_RW5 background failed|ASSERTION FAILED|PANIC!!!/.test(logs().slice(begin)));
 const report={revision:'r1',result:'passed',runtime:'official vela-watch-5.0 emulator; not REDMI Watch 5 firmware',screen:[432,514],emulatorRAMMB:128,
  packageBytes:fs.statSync(file).size,packageSha256:sha,installationType:'reinstallation of com.codex.stella.rw5 version 0.1.0 after cold boot; existing saves retained',installationResponse:installation.trim(),
  checks:['exact signed r1 file installed and launched after emulator cold boot','title background loaded','original save slots 1 and 30 loaded after cold boot','slot 30 saved again','first chapter page and pagination return refreshed','transparent portrait displayed','menu chapter skip reached next chapter','CG image and grouped difference displayed','no app or image errors during this run'],
  fullGameplayBaseline:{report:'original-v010-report.json',sha256:audit.original.sha256,retainedByIdenticalGameContents:true,coldBootRepeatedForR1:true,all30SlotsRepeatedForR1:false,coldBootSlotsVerified:[1,30]},
  physicalInstallationTested:false,physicalInstallationPassed:null};
 fs.writeFileSync(path.join(out,'r1-report.json'),JSON.stringify(report,null,2)+'\n');console.log('STELLA_R1_NATIVE_PASSED',JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1;});
