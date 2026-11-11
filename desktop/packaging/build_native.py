"""Build windowed Mac/Windows launchers with a private, relocatable Python runtime."""
from pathlib import Path
import argparse,hashlib,json,os,platform,re,shutil,stat,subprocess,sys,tempfile,zipfile

SOURCE=Path(__file__).resolve().parents[1]
SKIP={'.venv','.git','__pycache__','.pytest_cache','build','dist','.gradle'}
def included(path):return not any(p in SKIP for p in path.parts) and path.suffix not in ('.pyc','.p12','.keystore','.jks') and path.name not in ('.DS_Store','local.properties')
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def run(args,**kwargs):subprocess.run([str(x) for x in args],check=True,**kwargs)
def prepare(runtime):
 python=runtime/('python.exe' if os.name=='nt' else 'bin/python3')
 if not python.exists():
  if runtime.exists():raise RuntimeError('The runtime folder is incomplete.')
  shutil.copytree(Path(sys.base_prefix),runtime,symlinks=True)
 prefix=subprocess.check_output([str(python),'-c','import sys;print(sys.prefix)'],text=True).strip()
 if Path(prefix).resolve()!=runtime.resolve():raise RuntimeError('The copied Python is not relocatable: '+prefix)
 # This is an application-owned copy, never the OS or the developer's Python.
 for marker in (runtime/'lib').glob('python*/EXTERNALLY-MANAGED'):marker.unlink()
 run([python,'-m','ensurepip','--upgrade'])
 marker=runtime/'boardlens-requirements.txt';requirements=SOURCE/'requirements.txt'
 if not marker.exists() or marker.read_bytes()!=requirements.read_bytes():
  run([python,'-m','pip','install','--disable-pip-version-check','-r',requirements]);shutil.copy2(requirements,marker)
 return python

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--runtime',type=Path);args=parser.parse_args()
 work=args.work.resolve();out=args.out.resolve();work.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True);payload=work/'payload';payload.mkdir(exist_ok=True)
 runtime=args.runtime.resolve() if args.runtime else payload/'runtime'
 if runtime!=payload/'runtime':
  if (payload/'runtime').exists():raise RuntimeError('Choose a fresh work directory when passing --runtime.')
  shutil.copytree(runtime,payload/'runtime',symlinks=True);runtime=payload/'runtime'
 prepare(runtime)
 version=re.search(r'__version__\s*=\s*"([^"]+)"',(SOURCE/'chess_helper/__init__.py').read_text()).group(1)
 files=[p for p in sorted(SOURCE.rglob('*')) if p.is_file() and included(p.relative_to(SOURCE))]
 owned=SOURCE/'release-files.json';owned.write_text(json.dumps(sorted(set(p.relative_to(SOURCE).as_posix() for p in files)|{'release-files.json'}),indent=2)+'\n')
 files=[p for p in sorted(SOURCE.rglob('*')) if p.is_file() and included(p.relative_to(SOURCE))]
 with zipfile.ZipFile(payload/'source.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
  for p in files:archive.write(p,'BoardLens/'+p.relative_to(SOURCE).as_posix())
 for src,dest in [(SOURCE/'packaging/native/start.py',payload/'start.py'),(SOURCE/'chess_helper/update_apply.py',payload/'update_apply.py'),(SOURCE/'LICENSE',payload/'LICENSE'),(SOURCE/'THIRD-PARTY.txt',payload/'THIRD-PARTY.txt')]:shutil.copy2(src,dest)
 sys.path.insert(0,str(SOURCE));from chess_helper.installer import install_stockfish
 engine=payload/'engine';engine.mkdir(exist_ok=True)
 candidates=[p for p in engine.iterdir() if p.is_file() and p.name.startswith('stockfish')]
 if not candidates:install_stockfish(engine)
 # Corresponding source for the bundled GPL engine, alongside its license.
 engine_source=SOURCE.parent/'BoardLens-Mobile/android/engine-source/Stockfish-edb0d9d-source.tar.gz'
 if not engine_source.exists():engine_source=SOURCE.parent/'mobile/android/engine-source/Stockfish-edb0d9d-source.tar.gz'
 if not engine_source.exists():raise RuntimeError('The corresponding Stockfish source archive is missing.')
 shutil.copy2(engine_source,payload/'Stockfish-corresponding-source.tar.gz');shutil.copy2(SOURCE/'chess_helper/assets/licenses/Stockfish-GPL3.txt' if (SOURCE/'chess_helper/assets/licenses/Stockfish-GPL3.txt').exists() else SOURCE/'LICENSE',payload/'Stockfish-GPL3.txt')
 metadata={'version':version,'platform':platform.system(),'architecture':platform.machine(),'source_sha256':sha(payload/'source.zip')};(payload/'metadata.json').write_text(json.dumps(metadata,indent=2))
 archive=work/'payload.zip';archive.unlink(missing_ok=True)
 if sys.platform=='darwin':run(['/usr/bin/ditto','-c','-k',payload,archive])
 else:
  with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for p in sorted(payload.rglob('*')):
    if p.is_file():z.write(p,p.relative_to(payload).as_posix())
 digest=sha(archive);meta=dict(metadata,payload_sha256=digest)
 icon=SOURCE/'chess_helper/assets/ui/boardlens-icon.png'
 if sys.platform=='darwin':
  app=Path(tempfile.mkdtemp(prefix='boardlens-native-'))/'BoardLens.app'
  if app.exists():shutil.rmtree(app)
  resources=app/'Contents/Resources';binary=app/'Contents/MacOS';resources.mkdir(parents=True);binary.mkdir()
  shutil.copy2(archive,resources/'payload.zip');(resources/'metadata.json').write_text(json.dumps(meta))
  iconset=work/'BoardLens.iconset';iconset.mkdir(exist_ok=True)
  for n in [16,32,128,256,512]:
   for scale in [1,2]:run(['/usr/bin/sips','-z',n*scale,n*scale,icon,'--out',iconset/(f'icon_{n}x{n}'+('@2x.png' if scale==2 else '.png'))],stdout=subprocess.DEVNULL)
  run(['/usr/bin/iconutil','-c','icns',iconset,'-o',resources/'BoardLens.icns'])
  import plistlib
  info={'CFBundleName':'BoardLens','CFBundleDisplayName':'BoardLens','CFBundleIdentifier':'app.boardlens.desktop','CFBundleExecutable':'BoardLens','CFBundlePackageType':'APPL','CFBundleShortVersionString':version,'CFBundleVersion':version,'CFBundleIconFile':'BoardLens.icns','LSMinimumSystemVersion':'14.0','NSHighResolutionCapable':True,'NSPrincipalClass':'NSApplication','NSAppleEventsUsageDescription':'BoardLens reads supported local chess positions when you enable that connection.'}
  with (app/'Contents/Info.plist').open('wb') as f:plistlib.dump(info,f)
  run(['/usr/bin/clang','-arch',platform.machine(),'-mmacosx-version-min=14.0','-fobjc-arc','-framework','Cocoa','-Wno-deprecated-declarations',SOURCE/'packaging/native/Launcher.m','-o',binary/'BoardLens'])
  for name in ('com.apple.FinderInfo','com.apple.ResourceFork'):
   subprocess.run(['/usr/bin/xattr','-dr',name,str(app)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  run(['/usr/bin/codesign','--force','--sign','-',app])
  run(['/usr/bin/codesign','--verify','--strict',app])
  meta['app_path']=str(app)
  destination=out/('BoardLens-Mac-'+('AppleSilicon' if platform.machine()=='arm64' else 'Intel')+'.zip');destination.unlink(missing_ok=True);run(['/usr/bin/ditto','-c','-k','--keepParent',app,destination])
 else:
  app=out/'BoardLens-Windows';resources=app/'Resources';resources.mkdir(parents=True,exist_ok=True);shutil.copy2(archive,resources/'payload.zip')
  from PIL import Image
  Image.open(icon).save(work/'BoardLens.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
  cs=work/'Launcher.cs';cs.write_text((SOURCE/'packaging/native/Launcher.cs').read_text().replace('@PAYLOAD_SHA@',digest))
  compiler=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
  run([compiler,'/nologo','/target:winexe','/platform:x64','/optimize+','/win32icon:'+str(work/'BoardLens.ico'),'/win32manifest:'+str(SOURCE/'packaging/native/Launcher.manifest'),'/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll','/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll','/out:'+str(app/'BoardLens.exe'),cs])
  meta['app_path']=str(app/'BoardLens.exe')
  (app/'READ-ME.txt').write_text('Unzip the complete folder, then open BoardLens.exe. No Python install or Terminal is needed. Keep the Resources folder beside the app. Settings use your normal BoardLens app-data folder.\n')
  destination=out/'BoardLens-Windows-x64.zip'
  with zipfile.ZipFile(destination,'w',zipfile.ZIP_STORED) as z:
   for p in app.rglob('*'):
    if p.is_file():z.write(p,(Path('BoardLens')/p.relative_to(app)).as_posix())
 meta.update(asset=destination.name,sha256=sha(destination));(out/'native-build.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
