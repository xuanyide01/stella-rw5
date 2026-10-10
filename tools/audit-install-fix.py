"""Compare the full watch-manifest repair with the failed original release."""
from pathlib import Path
import json, struct, sys, zipfile
from rpk_signature import audit

root=Path(__file__).resolve().parents[1]
original=Path(sys.argv[1]); candidate=Path(sys.argv[2])
old,new=audit(original),audit(candidate)
assert new['bytes']<=15000000 and new['bytes']%16==1
assert old['certificateSha256']==new['certificateSha256']
z0,z1=zipfile.ZipFile(original),zipfile.ZipFile(candidate)
assert set(z1.namelist())-set(z0.namelist())=={'manifest-watch.json'}
assert not set(z0.namelist())-set(z1.namelist())
source=json.loads((root/'src/manifest.json').read_text('utf8'))
assert json.loads(z1.read('manifest-watch.json'))==source
changed=[n for n in z0.namelist() if z0.read(n)!=z1.read(n)]
assert set(changed)<= {'manifest.json','META-INF/CERT','META-INF/build.txt'},changed
m0,m1=json.loads(z0.read('manifest.json')),json.loads(z1.read('manifest.json'))
m0.pop('packageInfo',None);m1.pop('packageInfo',None)
assert m0==m1

def compressed(raw,entry):
    at=entry.header_offset
    length,extra=struct.unpack_from('<HH',raw,at+26)
    start=at+30+length+extra
    return raw[start:start+entry.compress_size]

raw0,raw1=original.read_bytes(),candidate.read_bytes()
same=[n for n in z0.namelist() if n not in changed]
assert all(compressed(raw0,z0.getinfo(n))==compressed(raw1,z1.getinfo(n)) for n in same)
report={'revision':'r1','original':old,'candidate':new,
 'watchManifestMissingInOriginal':True,'addedFiles':['manifest-watch.json'],
 'watchManifestMatchesSource':True,'changedExistingFiles':changed,
 'allExistingScriptsUnchanged':True,'allGameResourcesUnchanged':True,
 'unchangedFilesCompressedStreamsUnchanged':True,'unchangedEntries':len(same),
 'mainManifestChangesOnlyBuildMetadata':True,
 'compatibleTailWrapping':True,'zipCommentBytes':len(z1.comment),
 'finding':'Missing src/config-watch.json prevented DeviceTypePlugin from emitting manifest-watch.json; all physically tested reference ports include it',
 'failureCause':'Unidentified; missing watch metadata is a package structure difference, not an established cause of the reported physical installation failure',
 'physicalInstallationPassed':None}
(root/'reports/installation-fix-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
