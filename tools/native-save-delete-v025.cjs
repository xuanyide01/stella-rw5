const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const environment = process.env.STARRY_EMULATOR_HOME || path.resolve(root, '../../../2026-11-02/stella-rw5-delete-environment');
const url = process.env.STELLA_CONTROL_URL || 'http://127.0.0.1:43157/';
const log = path.join(environment, 'emulator.log');
const out = path.join(root, 'native-test-results/save-delete-v025');
const packageFile = path.join(root, 'dist/com.codex.stella.rw5.debug.0.2.5.rpk');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const logs = () => fs.readFileSync(log, 'utf8');

async function get(endpoint, timeout=25000) {
  const res = await fetch(url + endpoint, {signal: AbortSignal.timeout(timeout)});
  if (!res.ok) throw Error(await res.text());
  return res;
}

async function press(x, y, hold=false) {
  const endpoint = hold ? 'drag?x0='+x+'&y0='+y+'&x1='+x+'&y1='+y : 'click?x='+x+'&y='+y;
  await get(endpoint);
  await sleep(240);
}

async function wait(at, pattern) {
  for (let i=0; i<110; i++) {
    if (pattern.test(logs().slice(at))) return;
    await sleep(180);
  }
  throw Error('Simulator did not emit '+pattern+'; recent log: '+logs().slice(at).slice(-1600));
}

async function expectPress(x, y, pattern, hold=false) {
  const at = logs().length;
  await press(x, y, hold);
  await wait(at, pattern);
}

async function screenshot(name) {
  await sleep(250);
  const png = Buffer.from(await (await get('screen')).arrayBuffer());
  assert.equal(png.readUInt32BE(16), 432);
  assert.equal(png.readUInt32BE(20), 514);
  fs.writeFileSync(path.join(out, name+'.png'), png);
  return png;
}

async function menu() {
  await expectPress(216,488,/STELLA_RW5 menu/);
}

async function openSlots(role) {
  await expectPress(216,role==='save'?81:128,new RegExp('STELLA_RW5 slots ready '+role));
}

async function prepareSlots() {
  const begin = logs().length;
  const title = await screenshot('title');
  if (title.length < 2200) {
    await get('wake');
    await sleep(700);
    await screenshot('title');
  }
  await expectPress(125,232,/STELLA_RW5 frame 1 0/);
  await menu();
  await openSlots('save');
  const beforeEmptyHold = logs().length;
  await press(216,126,true);
  assert.doesNotMatch(logs().slice(beforeEmptyHold),/slot saved|delete confirmation/);
  await expectPress(216,126,/slot saved 1 1 0/);
  await expectPress(354,488,/frame 1 1/);
  await menu();
  await openSlots('save');
  await expectPress(216,218,/slot saved 2 1 1/);
  await menu();
  await openSlots('load');
  await sleep(1700);
  await screenshot('load-populated');
  await expectPress(216,218,/delete confirmation 2/,true);
  await screenshot('confirm-delete');
  const afterHold = logs().slice(begin);
  assert.doesNotMatch(afterHold,/slot deleted|slot loaded/);
}

async function verifyDeletion() {
  const begin = logs().length;
  await press(216,272);
  const afterCancel = await screenshot('cancel-keeps-saves');
  assert.doesNotMatch(logs().slice(begin),/slot deleted/);
  await expectPress(216,218,/slot loaded 2 1 1/);
  await menu();
  await openSlots('load');

  await expectPress(216,218,/delete confirmation 2/,true);
  await expectPress(216,215,/slot deleted 2/);
  await sleep(1700);
  const cleared = await screenshot('load-cleared');
  assert.ok(!cleared.equals(afterCancel),'Deleted slot should visibly change');
  await expectPress(216,126,/slot loaded 1 1 0/);

  await menu();
  await openSlots('save');
  await expectPress(216,218,/slot saved 2 1 0/);
  await menu();
  await openSlots('save');
  await expectPress(216,218,/overwrite 2/);
  await screenshot('short-tap-overwrite');
  await press(216,272);
  await expectPress(216,218,/delete confirmation 2/,true);
  await expectPress(216,215,/slot deleted 2/);
  await sleep(1700);
  await screenshot('save-cleared');

  let at = logs().length;
  await get('stop');
  await wait(at,/STELLA_RW5 app destroyed/);
  await sleep(1400);
  at = logs().length;
  await get('start',90000);
  await wait(at,/STELLA_RW5 background loaded title/);
  await sleep(600);
  await expectPress(125,304,/slots ready load/);
  const afterRestart = await screenshot('load-cleared-after-restart');
  assert.ok(afterRestart.equals(cleared),'Restart should still show the same empty slot');
  at = logs().length;
  await press(216,218);
  assert.doesNotMatch(logs().slice(at),/slot loaded/);
  await expectPress(216,126,/slot loaded 1 1 0/);
  assert.doesNotMatch(logs().slice(begin),/STELLA_RW5 error|ASSERTION FAILED|PANIC!!!|coredump_dump_dev/);
  const report = {
    result: 'passed', version: '0.2.5', variant: 'standard',
    runtime: 'official generic Vela Watch 5.0 simulator, 432×514',
    packageSha256: crypto.createHash('sha256').update(fs.readFileSync(packageFile)).digest('hex'),
    physicalDeviceTested: false,
    checks: [
      'Long press on empty slot does not save; short press saves to 01 and 02',
      'Long press on occupied LOAD row opens confirmation without activating its confirm button',
      'Cancel preserves both saves; confirm clears only 02; short press loads 01',
      'Slot 02 can be saved again; short press on occupied SAVE row opens overwrite confirmation',
      'Long press and confirm in SAVE clears 02; deletion persists after app restart',
    ],
  };
  fs.writeFileSync(path.join(out,'report.json'), JSON.stringify(report,null,2)+'\n');
  console.log('NATIVE_SAVE_DELETE_PASSED', JSON.stringify(report));
}

(async () => {
  fs.mkdirSync(out, {recursive:true});
  if (process.argv.includes('--install')) {
    const at = logs().length;
    await get('install?rpk='+encodeURIComponent(packageFile),210000);
    await get('start',90000);
    await wait(at,/STELLA_RW5 background loaded title/);
  }
  if (!process.argv.includes('--continue')) await prepareSlots();
  await verifyDeletion();
})().catch(error => {console.error(error);process.exitCode=1;});

