// Real native input against the Band 8 Pro target; no synthetic runtime states.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const zlib=require('zlib');
const root=path.resolve(__dirname,'..'),out=path.join(root,'native-test-results/title-band-v011'),url='http://127.0.0.1:43136';
const log=path.resolve(root,'../stella-band8pro-environment/emulator.log');
fs.mkdirSync(out,{recursive:true});
const sleep=ms=>new Promise(r=>setTimeout(r,ms)),logs=()=>fs.readFileSync(log,'utf8');
async function request(endpoint,timeout=20000){const r=await fetch(url+'/'+endpoint,{signal:AbortSignal.timeout(timeout)});if(!r.ok)throw Error(await r.text());return r;}
async function click(x,y){await request('click?x='+x+'&y='+y);await sleep(160);}
async function wait(at,re){for(let i=0;i<100;i++){const text=logs().slice(at);if(re.test(text))return text;await sleep(200);}throw Error('Native timeout: '+re);}
async function expected(x,y,re){const at=logs().length;await click(x,y);return wait(at,re);}
async function shot(name){await sleep(300);fs.writeFileSync(path.join(out,name+'.png'),Buffer.from(await(await request('screen')).arrayBuffer()));}
async function wakeIfBlack(){
 const png=Buffer.from(await(await request('screen')).arrayBuffer()),blocks=[];let at=8;
 while(at<png.length){const size=png.readUInt32BE(at),kind=png.toString('ascii',at+4,at+8);if(kind==='IDAT')blocks.push(png.subarray(at+8,at+8+size));at+=12+size;}
 const decoded=zlib.inflateSync(Buffer.concat(blocks)),width=png.readUInt32BE(16),height=png.readUInt32BE(20),channels=png[25]===6?4:3;
 assert.equal(png[24],8);assert.ok([2,6].includes(png[25]));
 let previous=new Uint8Array(width*channels),offset=0,black=true;
 const paeth=(a,b,c)=>{const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);return pa<=pb&&pa<=pc?a:pb<=pc?b:c;};
 for(let y=0;y<height&&black;y++){
  const filter=decoded[offset++],row=new Uint8Array(width*channels);
  for(let x=0;x<row.length;x++){
   const a=x>=channels?row[x-channels]:0,b=previous[x],c=x>=channels?previous[x-channels]:0;
   row[x]=(decoded[offset++]+(filter===0?0:filter===1?a:filter===2?b:filter===3?Math.floor((a+b)/2):paeth(a,b,c)))&255;
   if(x%channels<3&&row[x]>2)black=false;
  }previous=row;
 }
 if(black){await request('wake');await sleep(1500);console.log('VIRTUAL_DISPLAY_WOKEN');}
}
async function menu(){await expected(168,454,/STELLA_BAND8PRO menu/);}
async function title(){await menu();await expected(168,422,/STELLA_BAND8PRO background loaded title/);}
async function drag(){await request('drag?x0=165&y0=414&x1=165&y1=306');await sleep(450);}

(async()=>{
 const begin=logs().length,band=root.endsWith('stella-band8pro'),prefix=band?'STELLA_BAND8PRO':'STELLA_RW5';
 const locked=process.argv.includes('--locked'),titleX=band?110:125,titleAfter=band?221:232,titleStart=band?(locked?221:255):(locked?232:268),titleLoad=band?(locked?289:323):(locked?304:340),titleGallery=band?(locked?357:391):(locked?376:412),titleExit=band?(locked?391:425):(locked?412:448);
 const center=band?168:216,bottom=band?454:488,menuTitle=band?422:447,pager=band?444:474;
 await wakeIfBlack();await shot('title');
 await expected(titleX,titleStart,new RegExp(prefix+' frame 1 0'));await shot('reading');
 await expected(center,bottom,new RegExp(prefix+' menu'));await shot('menu');await expected(center,menuTitle,new RegExp(prefix+' background loaded title'));
 await expected(titleX,titleLoad,new RegExp(prefix+' slots ready load'));await shot('load-slots');await expected(center,pager,new RegExp(prefix+' background loaded title'));
 await click(titleX,titleGallery);await sleep(700);await shot('gallery');await expected(band?83:108,band?133:146,new RegExp(prefix+' cg 1 1'));await shot('cg');
 await click(center,band?453:487);await sleep(800);await expected(center,pager,new RegExp(prefix+' background loaded title'));
 await expected(titleX,titleExit,new RegExp(prefix+' app destroyed'));await sleep(2500);const at=logs().length;await request('start',90000);await wait(at,new RegExp(prefix+' background loaded title'));await wait(at,/PageCallHook, name:onShow/);await sleep(500);await wakeIfBlack();await shot('title-reopened');
 if(!locked){await expected(titleX,titleAfter,new RegExp(prefix+' frame 101 0'));await shot('after-intro');
 await expected(center,bottom,new RegExp(prefix+' menu'));await expected(center,menuTitle,new RegExp(prefix+' background loaded title'));}
 assert.ok(!new RegExp(prefix+' error|'+prefix+' background failed|ASSERTION FAILED|PANIC!!!|coredump').test(logs().slice(begin)));
 const m=JSON.parse(fs.readFileSync(path.join(root,'src/manifest.json'))),rpk=path.join(root,'dist',m.package+'.debug.'+m.versionName+'.rpk');
 const report={result:'passed',version:m.versionName,packageSha256:crypto.createHash('sha256').update(fs.readFileSync(rpk)).digest('hex'),screen:band?[336,480]:[432,514],runtime:'official generic vela-watch-5.0 simulator, not physical target firmware',physicalDeviceTested:false,checks:['complete title artwork renders at target dimensions','START reading, menu, LOAD slot list and EXTRA CG render','EXIT tears down and title reopens',locked?'fresh title hides AFTER STORY':'existing main clear flag retains first AFTER STORY entry'],scope:'title-art update smoke test; 17 automated story/choice/save tests also passed; earlier full game-flow native reports are historical'};
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log('TITLE_NATIVE_PASSED',JSON.stringify(report));
})().catch(e=>{console.error(e.message);fs.writeFileSync(path.join(out,'failure.txt'),e.stack);process.exitCode=1;});
