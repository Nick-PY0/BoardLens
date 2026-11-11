"""Standalone portable updater; preserves runtime, user files and rollback copies."""
import argparse,json,os,shutil,stat,subprocess,tempfile,time,zipfile
from pathlib import Path,PurePosixPath


def safe_name(name):
    parts=PurePosixPath(name).parts
    return bool(parts) and not name.startswith('/') and '\\' not in name and ':' not in name and all(p not in ('..','.venv','.git','__pycache__') for p in parts)


def apply_archive(archive,root,backup):
    root=Path(root).resolve();backup=Path(backup);changed=[]
    with tempfile.TemporaryDirectory(prefix='boardlens-stage-') as temp:
        stage=Path(temp)
        with zipfile.ZipFile(archive) as source:
            entries={}
            for info in source.infolist():
                if info.is_dir():continue
                if not info.filename.startswith('BoardLens/'):raise ValueError('Unexpected archive root.')
                name=info.filename[len('BoardLens/'):]
                if not safe_name(name) or name in entries or stat.S_ISLNK(info.external_attr>>16):raise ValueError('Unsafe update entry.')
                entries[name]=info
            if len(entries)>2000 or sum(i.file_size for i in entries.values())>250*1024*1024:raise ValueError('Update is too large.')
            names=json.loads(source.read('BoardLens/release-files.json'))
            if not isinstance(names,list) or set(names)!=set(entries):raise ValueError('Incomplete update manifest.')
            for name,info in entries.items():
                dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True)
                with source.open(info) as inp,dest.open('wb') as out:shutil.copyfileobj(inp,out)
                dest.chmod(0o755 if (info.external_attr>>16)&0o111 else 0o644)
        try:old=json.loads((root/'release-files.json').read_text())
        except (OSError,ValueError):old=[]
        if not isinstance(old,list) or any(not isinstance(n,str) or not safe_name(n) for n in old):raise ValueError('Invalid installed file manifest.')
        targets=set(names)|set(old)
        for name in targets:
            dest=root/name
            if not dest.resolve().is_relative_to(root):raise ValueError('Update would leave the application folder.')
            if dest.is_file():
                saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved)
        try:
            for name in names:
                dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);temporary=dest.with_name(dest.name+'.boardlens-update')
                try:shutil.copy2(stage/name,temporary);os.replace(temporary,dest)
                finally:temporary.unlink(missing_ok=True)
                changed.append(name)
            for name in set(old)-set(names):
                dest=root/name
                if dest.is_file():dest.unlink();changed.append(name)
        except Exception:
            for name in reversed(changed):
                dest=root/name;saved=backup/name
                if saved.is_file():shutil.copy2(saved,dest)
                else:dest.unlink(missing_ok=True)
            raise
    return len(names)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',required=True);parser.add_argument('--app',required=True);parser.add_argument('--backup',required=True);parser.add_argument('--python',required=True);parser.add_argument('--pid',type=int,required=True)
    args=parser.parse_args();root=Path(args.app);log=Path(args.backup).parent/'last-update.txt';log.parent.mkdir(parents=True,exist_ok=True)
    try:
        if os.name=='nt':
            import ctypes
            kernel=ctypes.windll.kernel32
            kernel.OpenProcess.restype=ctypes.c_void_p
            kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
            kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            handle=kernel.OpenProcess(0x100000,False,args.pid)
            if handle:
                try:
                    if kernel.WaitForSingleObject(handle,20000)!=0:raise RuntimeError('Close BoardLens before applying this update.')
                finally:kernel.CloseHandle(handle)
        else:
            for _ in range(200):
                try:os.kill(args.pid,0)
                except OSError:break
                time.sleep(.1)
            else:raise RuntimeError('Close BoardLens before applying this update.')
        count=apply_archive(args.archive,root,args.backup);log.write_text(f'Updated {count} files. Previous files: {args.backup}\n')
    except Exception as error:log.write_text('Update failed; previous files retained: '+str(error)+'\n')
    subprocess.Popen([args.python,'-m','chess_helper'],cwd=root,start_new_session=True)


if __name__=='__main__':main()
