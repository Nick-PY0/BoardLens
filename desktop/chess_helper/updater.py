"""Manual, verified updates from BoardLens's public GitHub releases."""
import hashlib,json,re,shutil,subprocess,sys,threading,time,urllib.error,urllib.request,uuid
from pathlib import Path
from urllib.parse import urlparse
from PySide6.QtCore import QObject,Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton
from . import __version__
from .core import data_dir

REPOSITORY='Nick-PY0/BoardLens'
RELEASES='https://github.com/'+REPOSITORY+'/releases'
API='https://api.github.com/repos/'+REPOSITORY+'/releases/latest'
ASSET='BoardLens-Mac-Windows.zip'


def asset_url(value):
    url=urlparse(value)
    if url.scheme!='https' or url.netloc!='github.com' or not url.path.startswith('/'+REPOSITORY+'/releases/download/') or url.username or url.query or url.fragment:raise ValueError('Unexpected update download URL.')
    return value


def read_url(url,limit):
    request=urllib.request.Request(url,headers={'User-Agent':'BoardLens/'+__version__,'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request,timeout=12) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise ValueError('Update response is too large.')
    return data


def newer(value,current=__version__):
    def parts(text):
        if not isinstance(text,str) or not re.fullmatch(r'\d+\.\d+\.\d+',text):raise ValueError('Unsupported update version.')
        return tuple(map(int,text.split('.')))
    return parts(value)>parts(current)


def latest_release():
    try:release=json.loads(read_url(API,2*1024*1024))
    except urllib.error.HTTPError as error:
        if error.code==404:raise ValueError('The first GitHub release is not published yet. Try again later.') from error
        raise
    if release.get('draft') or release.get('prerelease'):raise ValueError('No stable release is available.')
    assets={a['name']:a for a in release.get('assets',[])}
    manifest=assets.get('boardlens-update.json')
    if not manifest:raise ValueError('This release has no update manifest.')
    data=json.loads(read_url(asset_url(manifest['browser_download_url']),65536))
    if data.get('schema')!=1:raise ValueError('Unsupported update manifest.')
    desktop=data['desktop'];asset=assets.get(ASSET)
    if not asset or desktop.get('asset')!=ASSET or not re.fullmatch('[0-9a-f]{64}',desktop.get('sha256','')):raise ValueError('Desktop update is incomplete.')
    newer(desktop['version'])
    return dict(desktop,url=asset_url(asset['browser_download_url']))


def download_update(info,target,cancel=None):
    target=Path(target);temporary=target.with_suffix('.partial');digest=hashlib.sha256();size=0
    try:
        with urllib.request.urlopen(urllib.request.Request(asset_url(info['url']),headers={'User-Agent':'BoardLens/'+__version__}),timeout=20) as response,temporary.open('wb') as output:
            while True:
                if cancel and cancel.is_set():raise ValueError('Update cancelled.')
                chunk=response.read(262144)
                if not chunk:break
                size+=len(chunk)
                if size>100*1024*1024:raise ValueError('Update is too large.')
                digest.update(chunk);output.write(chunk)
        if digest.hexdigest()!=info['sha256']:raise ValueError('Checksum did not match. No application files changed.')
        temporary.replace(target);return target
    finally:temporary.unlink(missing_ok=True)


class Results(QObject):
    done=Signal(object,str,int)


class UpdateDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.info=None;self.cancel=threading.Event();self.busy=False;self.downloading=False;self.generation=0
        self.signals=Results(self);self.signals.done.connect(self.finished_job)
        self.setWindowTitle('BoardLens updates');self.resize(440,230)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Installed version '+__version__))
        self.status=QLabel('Check for the latest public release.');self.status.setWordWrap(True);layout.addWidget(self.status,1)
        row=QHBoxLayout();self.check=QPushButton('Check again');self.check.clicked.connect(self.start_check);row.addWidget(self.check)
        self.install=QPushButton('Download and restart');self.install.setEnabled(False);self.install.clicked.connect(self.start_download);row.addWidget(self.install);layout.addLayout(row)
        notes=QPushButton('Release notes');notes.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(RELEASES)));layout.addWidget(notes)
    def work(self,operation):
        self.busy=True;self.check.setEnabled(False);self.install.setEnabled(False);self.cancel=threading.Event();self.generation+=1;generation=self.generation;cancel=self.cancel
        def run():
            try:value,error=operation(),''
            except Exception as exc:value,error=None,str(exc)
            if not cancel.is_set():self.signals.done.emit(value,error,generation)
        threading.Thread(target=run,daemon=True).start()
    def start_check(self):
        if self.busy:return
        self.status.setText('Checking GitHub…');self.downloading=False;self.work(latest_release)
    def start_download(self):
        if self.busy or not self.info:return
        self.status.setText('Downloading and checking the update. BoardLens will restart; your settings and engines stay saved.')
        self.downloading=True;folder=data_dir()/'updates';folder.mkdir(parents=True,exist_ok=True)
        self.work(lambda:download_update(self.info,folder/'BoardLens-update.zip',self.cancel))
    def finished_job(self,value,error,generation):
        if generation!=self.generation:return
        self.busy=False;self.check.setEnabled(True)
        if error:self.status.setText(error);return
        if not self.downloading:
            self.info=value;available=newer(value['version']);self.install.setEnabled(available)
            self.status.setText('Version '+value['version']+' is available.' if available else 'You have the latest version.');return
        root=Path(__file__).resolve().parent.parent;folder=data_dir()/'updates';helper=folder/('apply-'+uuid.uuid4().hex+'.py');shutil.copy2(Path(__file__).with_name('update_apply.py'),helper)
        import os
        command=[sys.executable,str(helper),'--archive',str(value),'--app',str(root),'--backup',str(folder/'backups'/str(time.time_ns())),'--python',sys.executable,'--pid',str(os.getpid())]
        subprocess.Popen(command,start_new_session=True);self.window.close()
    def closeEvent(self,event):
        self.cancel.set();self.generation+=1;self.busy=False;super().closeEvent(event)
