import {catalog} from './catalog.js';
function clone(o){return JSON.parse(JSON.stringify(o));}
export function newState(chapter,story){const id=chapter||catalog.initial;return {chapter:id,rootChapter:id,cursor:0,background:'',regularBackground:'',body:'',bodies:[],sprites:{},speaker:'',text:'',choices:[],history:[],variables:{},stack:[],ended:false,progression:story?'story':'chapter'};}
export function checkpoint(s){const o=Object.assign({},s);delete o.history;return clone(o);}
export function restore(saved){
 if(!saved||!catalog.scenes[String(saved.chapter)]||!Number.isInteger(saved.cursor)||saved.cursor<0||saved.cursor>=catalog.scenes[String(saved.chapter)].length)throw Error('存档位置无效');
 if(!saved.variables||typeof saved.variables!=='object'||Array.isArray(saved.variables)||!Array.isArray(saved.bodies)||saved.bodies.length>3)throw Error('存档状态无效');
 const s=Object.assign(newState(),clone(saved),{history:[]});if(!catalog.scenes[String(s.rootChapter)])throw Error('存档篇章无效');return s;
}
export function readFrame(ops,s,base,total){
 base=base||0;total=total===undefined?ops.length:total;
 if(s.cursor>=total){s.ended=true;return {type:'end'};}
 const local=s.cursor-base;if(local<0||local>=ops.length)return {type:'yield'};
 const o=ops[local];
 if(o.op==='text'){s.speaker=o.speaker;s.text=o.text;s.background=o.background;s.regularBackground=o.background;s.bodies=(o.bodies||[]).slice(0,3);s.body=s.bodies[0]||'';return {type:'text',speaker:o.speaker,text:o.text};}
 if(o.op==='choice')return {type:'choice',items:o.items};
 if(o.op==='jumpScene'){if(!catalog.scenes[String(o.scene)]||!Number.isInteger(o.to))throw Error('剧情跳转无效');s.chapter=o.scene;s.rootChapter=o.scene;s.cursor=o.to;return {type:'jump'};}
 if(o.op==='end'){s.ended=true;return {type:'end'};}
 throw Error('剧情指令无效');
}
function remember(s){s.history.push(checkpoint(s));if(s.history.length>8)s.history.shift();}
export function next(s){if(s.ended)return;remember(s);s.cursor++;}
export function choose(s,item,index){if(!item||!Number.isInteger(item.to)||item.to<0||item.to>=catalog.scenes[String(s.chapter)].length)throw Error('选项无效');remember(s);s.choices.push(index);s.cursor=item.to;s.ended=false;}
export function previous(s){const last=s.history.pop();if(!last)return false;const history=s.history;Object.assign(s,last,{history});return true;}
export function nextChapter(s){if(s.ended)return null;remember(s);return {chapter:s.rootChapter};}
export function readChapterSkip(ops,s,context,base,total){for(let count=0;count<64;count++){const frame=readFrame(ops,s,base,total);if(frame.type!=='text'||s.rootChapter!==context.chapter)return frame;s.cursor++;}return {type:'yield'};}
export function previewMap(){return [];}
