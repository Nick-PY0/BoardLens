"""Build portable release archives and a checksum manifest; no user data included."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,zipfile

ROOT=Path(__file__).resolve().parents[1]
SKIP={'.venv','.git','.gradle','build','.idea','__pycache__','.pytest_cache','xcuserdata'}
def include(path):
    return not any(p in SKIP for p in path.parts) and path.name not in {'local.properties','.DS_Store'} and path.suffix not in {'.pyc','.xcuserstate','.jks','.keystore'}
def files(root):return [p for p in sorted(root.rglob('*')) if p.is_file() and include(p.relative_to(root))]
def archive(destination,root,prefix):
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for path in files(root):out.write(path,str(Path(prefix)/path.relative_to(root)))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apk',type=Path,default=ROOT/'mobile/android/app/build/outputs/apk/debug/app-debug.apk');parser.add_argument('--output',type=Path,default=ROOT/'dist');args=parser.parse_args()
    target=args.output;target.mkdir(parents=True,exist_ok=True);desktop=ROOT/'desktop';mobile=ROOT/'mobile'
    if not args.apk.is_file():raise SystemExit('Build the signed Android APK first, then pass --apk.')
    owned=desktop/'release-files.json';owned.write_text(json.dumps(sorted(set(str(p.relative_to(desktop)) for p in files(desktop))|{'release-files.json'}),indent=2)+'\n')
    archive(target/'BoardLens-Mac-Windows.zip',desktop,'BoardLens');archive(target/'BoardLens-Mobile-Source.zip',mobile,'BoardLens-Mobile');archive(target/'BoardLens-iPhone-iPad-Source.zip',mobile/'ios','BoardLens-iOS')
    with zipfile.ZipFile(target/'BoardLens-iPhone-iPad-Source.zip','a',zipfile.ZIP_DEFLATED) as out:
        for name in ('LICENSE','START-HERE.txt','TEST-REPORT.txt'):out.write(mobile/name,'BoardLens-iOS/'+name)
    shutil.copy2(args.apk,target/'BoardLens-Companion-Android.apk')
    version=re.search(r'__version__\s*=\s*"([^"]+)"',(desktop/'chess_helper/__init__.py').read_text()).group(1)
    gradle=(mobile/'android/app/build.gradle').read_text();android=re.search(r"versionName '([^']+)'",gradle).group(1);code=int(re.search(r"boardlensVersionCode'\) \?: '(\d+)'",gradle).group(1))
    data={'schema':1,'desktop':{'version':version,'asset':'BoardLens-Mac-Windows.zip','sha256':digest(target/'BoardLens-Mac-Windows.zip')},'android':{'version':android,'version_code':code,'asset':'BoardLens-Companion-Android.apk','sha256':digest(target/'BoardLens-Companion-Android.apk')}}
    (target/'boardlens-update.json').write_text(json.dumps(data,indent=2)+'\n')
    (target/'SHA256SUMS.txt').write_text(''.join(digest(path)+'  '+path.name+'\n' for path in sorted(target.iterdir()) if path.is_file() and path.name!='SHA256SUMS.txt'))
    print(json.dumps(data,indent=2))
if __name__=='__main__':main()
