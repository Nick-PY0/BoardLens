"""Package the complete signed Android build and tracked sources, independently of desktop."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zipfile,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--apk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
project=ET.parse(root/'mobile/android/tiny-runtime/BoardLens.Android.csproj');version=project.findtext('./PropertyGroup/ApplicationDisplayVersion');code=int(project.findtext('./PropertyGroup/ApplicationVersion'))
apk=args.output/'BoardLens-Companion-Android.apk'
if args.apk.resolve()!=apk.resolve():apk.write_bytes(args.apk.read_bytes())
tracked=subprocess.check_output(['git','ls-files','-z','--','mobile'],cwd=root).decode().split('\0')
with zipfile.ZipFile(args.output/'BoardLens-Mobile-Source.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
 for name in sorted(filter(None,tracked)):
  path=Path(name)
  if any(part in {'bin','obj','build','.gradle','.git'} for part in path.parts):continue
  archive.write(root/path,Path('BoardLens-Mobile')/path.relative_to('mobile'))
hashfile=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
data={'schema':1,'android':{'version':version,'version_code':code,'asset':apk.name,'sha256':hashfile(apk)}}
(args.output/'boardlens-update.json').write_text(json.dumps(data,indent=2)+'\n')
(args.output/'SHA256SUMS.txt').write_text(''.join(hashfile(path)+'  '+path.name+'\n' for path in sorted(args.output.iterdir()) if path.is_file() and path.name!='SHA256SUMS.txt'))
print(json.dumps(data))
