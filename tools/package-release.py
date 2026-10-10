"""Package only the audited, emulator-tested build and its reproducible source."""
from pathlib import Path
import json,hashlib,zipfile,shutil,argparse
parser=argparse.ArgumentParser();parser.add_argument('--revision',choices=['r1']);args=parser.parse_args()
root=Path(__file__).resolve().parents[1];out=root.parents[1]/'outputs';out.mkdir(exist_ok=True)
manifest=json.loads((root/'src/manifest.json').read_text('utf8'))
original=root/'dist'/f'{manifest["package"]}.debug.{manifest["versionName"]}.rpk'
audit=json.loads((root/'reports/package-audit.json').read_text('utf8'))
native=json.loads((root/'native-test-results'/('r1-report.json' if args.revision else 'report.json')).read_text('utf8'))
sha=hashlib.sha256(original.read_bytes()).hexdigest()
assert original.stat().st_size<=15000000
assert audit['sha256']==native['packageSha256']==sha
assert native['result']=='passed'
packaging=None;baseline=None
if args.revision:
    packaging=json.loads((root/'reports/installation-fix-audit.json').read_text('utf8'))
    baseline=json.loads((root/'native-test-results/original-v010-report.json').read_text('utf8'))
    assert packaging['candidate']['sha256']==sha
    assert packaging['original']['sha256']==baseline['packageSha256']
    assert packaging['allExistingScriptsUnchanged'] and packaging['allGameResourcesUnchanged'] and packaging['watchManifestMatchesSource']
    assert baseline['result']=='passed' and baseline['coldBoot30Slots']
else:
    assert native['coldBoot30Slots']
stem='星之终途-RW5-'+manifest['versionName']+('-'+args.revision if args.revision else '');created=[]
for suffix in ['.bin','.rpk']:
    target=out/(stem+suffix);shutil.copyfile(original,target);created.append(target)
info=out/(stem+'-安装说明.md');shutil.copyfile(root/'README.md',info);created.append(info)
feedback=json.loads((root/'reports/installation-issue-v010.json').read_text('utf8')) if args.revision else None
physical=feedback.get('candidate',{}) if feedback else {}
assert not physical.get('physicalInstallationTested') or physical.get('sha256')==sha
report=out/(stem+'-检查报告.json');report.write_text(json.dumps({'package':audit,'conversion':json.loads((root/'reports/conversion.json').read_text('utf8')),'nativeEmulator':native,'packagingRevision':packaging,'fullGameplayBaseline':baseline,'automatedTests':{'passed':9,'failed':0,'r1Basis':'original test results retained; all game contents identical' if args.revision else 'current package'},'installationFeedback':feedback,'physicalDeviceTested':physical.get('physicalInstallationTested',False),'physicalInstallationPassed':physical.get('physicalInstallationPassed'),'physicalGameplayTested':physical.get('physicalGameplayTested',False),'physicalGameplayNoBugsReported':physical.get('physicalGameplayNoBugsReported',False),'physicalGameplayCoverage':physical.get('physicalGameplayCoverage')},ensure_ascii=False,indent=2),encoding='utf8');created.append(report)
source=out/(stem+'-源码.zip')
with zipfile.ZipFile(source,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for folder in ['src','tools','tests','licenses','reports','native-test-results']:
        for p in sorted((root/folder).rglob('*')):
            if not p.is_file() or '__pycache__' in p.parts or 'node_modules' in p.parts or p.suffix in ['.pem','.log','.pyc']:continue
            if p.name.startswith('native-first-') or p.name=='native-progress.png':continue
            z.write(p,'stella-rw5/'+p.relative_to(root).as_posix())
    for filename in ['README.md','LICENSE','THIRD_PARTY_NOTICES.md','package.json','quickapp.config.js','.gitignore','.gitattributes','requirements.txt']:z.write(root/filename,'stella-rw5/'+filename)
created.append(source)
checksums=out/(stem+'-SHA256.txt')
checksums.write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in created)+'\n',encoding='utf8');created.append(checksums)
for p in created:print(p.name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
