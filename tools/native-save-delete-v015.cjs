const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const environment = process.env.STARRY_EMULATOR_HOME || path.resolve(root, '../stella-save-delete-environment');
const url = process.env.STELLA_CONTROL_URL || 'http://127.0.0.1:43156/';
const log = path.join(environment, 'emulator.log');
const out = path.join(root, 'native-test-results/save-delete-v015');
const packageFile = path.join(root, 'dist/com.codex.stella.band8pro.debug.0.1.5.rpk');
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
  assert.equal(png.readUInt32BE(16), 336);
  assert.equal(png.readUInt32BE(20), 480);
  fs.writeFileSync(path.join(out, name+'.png'), png);
  return png;
}

async function menu() {
  await expectPress(168,448,/STELLA_BAND8PRO menu/);
}

async function openSlots(role) {
  await expectPress(168,role==='save'?71:115,new RegExp('STELLA_BAND8PRO slots ready '+role));
}

async function prepareSlots() {
  const begin = logs().length;
  await get('wake');
  await sleep(700);
  await screenshot('title');
  await expectPress(110,221,/STELLA_BAND8PRO frame 1 0/);
  await menu();
  await openSlots('save');
  const beforeEmptyHold = logs().length;
  await press(168,118,true);
  assert.doesNotMatch(logs().slice(beforeEmptyHold),/slot saved|delete confirmation/);
  await expectPress(168,118,/slot saved 1 1 0/);
  await expectPress(285,448,/frame 1 1/);
  await menu();
  await openSlots('save');
  await expectPress(168,204,/slot saved 2 1 1/);
  await menu();
  await openSlots('load');
  await sleep(1700);
  await screenshot('load-populated');
  await expectPress(168,204,/delete confirmation 2/,true);
  await screenshot('confirm-delete');
  const afterHold = logs().slice(begin);
  assert.doesNotMatch(afterHold,/slot deleted|slot loaded/);
}

async function verifyDeletion() {
  const begin = logs().length;
  await press(168,265);
  const afterCancel = await screenshot('cancel-keeps-saves');
  assert.doesNotMatch(logs().slice(begin),/slot deleted/);
  await expectPress(168,204,/slot loaded 2 1 1/);
  await menu();
  await openSlots('load');

  await expectPress(168,204,/delete confirmation 2/,true);
  await expectPress(168,210,/slot deleted 2/);
  await sleep(1700);
  const cleared = await screenshot('load-cleared');
  assert.ok(!cleared.equals(afterCancel),'Deleted slot should visibly change');
  await expectPress(168,118,/slot loaded 1 1 0/);

  await menu();
  await openSlots('save');
  await expectPress(168,204,/slot saved 2 1 0/);
  await menu();
  await openSlots('save');
  await expectPress(168,204,/overwrite 2/);
  await screenshot('short-tap-overwrite');
  await press(168,265);
  await expectPress(168,204,/delete confirmation 2/,true);
  await expectPress(168,210,/slot deleted 2/);
  await sleep(1700);
  await screenshot('save-cleared');

  let at = logs().length;
  await get('stop');
  await wait(at,/STELLA_BAND8PRO app destroyed/);
  await sleep(1400);
  at = logs().length;
  await get('start',90000);
  await wait(at,/STELLA_BAND8PRO background loaded title/);
  await sleep(600);
  await expectPress(110,289,/slots ready load/);
  const afterRestart = await screenshot('load-cleared-after-restart');
  assert.ok(afterRestart.equals(cleared),'Restart should still show the same empty slot');
  at = logs().length;
  await press(168,204);
  assert.doesNotMatch(logs().slice(at),/slot loaded/);
  await expectPress(168,118,/slot loaded 1 1 0/);
  assert.doesNotMatch(logs().slice(begin),/STELLA_BAND8PRO error|ASSERTION FAILED|PANIC!!!|coredump_dump_dev/);
  const report = {
    result: 'passed', version: '0.1.5',
    runtime: 'official generic Vela Watch 5.0 simulator, 336×480',
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
  if (!process.argv.includes('--continue')) await prepareSlots();
  await verifyDeletion();
})().catch(error => {console.error(error);process.exitCode=1;});

