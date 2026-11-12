"""Create a styled drag-to-Applications installer from a verified Mac bundle."""
from pathlib import Path
import argparse,hashlib,json,os,platform,plistlib,subprocess,sys,tempfile
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
# File Provider can mark Qt's plugins hidden; Qt skips those files.
if sys.platform=='darwin' and hasattr(os,'chflags'):
    import PySide6,stat
    plugins=Path(PySide6.__file__).parent/'Qt/plugins'
    for item in [plugins,*plugins.rglob('*')]:
        try:
            flags=item.stat().st_flags
            if flags&stat.UF_HIDDEN:os.chflags(item,flags&~stat.UF_HIDDEN)
        except OSError:pass
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QImage,QPainter,QFont,QColor,QPen,QPainterPath
import dmgbuild

def font(size,weight=QFont.Weight.Normal):
    value=QFont('Arial');value.setPixelSize(size);value.setWeight(weight);return value

def background(path,icon,arch):
    app=QApplication.instance() or QApplication([])
    image=QImage(1360,860,QImage.Format.Format_ARGB32_Premultiplied);image.fill(QColor('#eef3f1'))
    p=QPainter(image);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform);p.scale(2,2)
    p.drawImage(QRectF(44,34,48,48),QImage(str(icon)))
    p.setPen(QColor('#17362b'));p.setFont(font(28,QFont.Weight.Bold));p.drawText(QRectF(106,34,510,36),Qt.AlignmentFlag.AlignVCenter,'BoardLens')
    p.setFont(font(13));p.setPen(QColor('#5b7168'));p.drawText(QRectF(108,74,510,22),'Install on your Mac')
    p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#ffffff'))
    for x in (108,428):p.drawRoundedRect(QRectF(x,152,144,172),22,22)
    p.setPen(QPen(QColor('#2a8f65'),4,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap));p.drawLine(QPointF(294,222),QPointF(386,222));p.drawLine(QPointF(374,210),QPointF(386,222));p.drawLine(QPointF(374,234),QPointF(386,222))
    p.setFont(font(16,QFont.Weight.DemiBold));p.setPen(QColor('#17362b'));p.drawText(QRectF(28,344,624,28),Qt.AlignmentFlag.AlignCenter,'Drag BoardLens into Applications')
    p.setFont(font(12));p.setPen(QColor('#5b7168'));p.drawText(QRectF(28,378,624,24),Qt.AlignmentFlag.AlignCenter,'Then open BoardLens from Applications.')
    p.setFont(font(10));p.setPen(QColor('#71897e'));p.drawText(QRectF(28,411,624,16),Qt.AlignmentFlag.AlignCenter,'macOS 14 or later · '+arch)
    p.end()
    one=path.with_name('install@1x.png');two=path.with_name('install@2x.png')
    image.setDotsPerMeterX(5669);image.setDotsPerMeterY(5669);assert image.save(str(two))
    small=image.scaled(680,430,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation);small.setDotsPerMeterX(2835);small.setDotsPerMeterY(2835);assert small.save(str(one))
    subprocess.run(['/usr/bin/tiffutil','-cathidpicheck',str(one),str(two),'-out',str(path)],check=True,stdout=subprocess.DEVNULL)
    from AppKit import NSImage
    dimensions=NSImage.alloc().initWithContentsOfFile_(str(path)).size()
    assert round(dimensions.width)==680 and round(dimensions.height)==430,dimensions

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--app',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if sys.platform!='darwin':raise SystemExit('Build the Mac installer on macOS.')
    app=args.app.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    subprocess.run(['/usr/bin/codesign','--verify','--strict',str(app)],check=True)
    arm=platform.machine()=='arm64';name='Mac-AppleSilicon' if arm else 'Mac-Intel';destination=out/('BoardLens-'+name+'.dmg');destination.unlink(missing_ok=True)
    icon=Path(__file__).resolve().parents[1]/'chess_helper/assets/ui/boardlens-icon-rounded.png'
    with tempfile.TemporaryDirectory(prefix='boardlens-installer-') as folder:
        art=Path(folder)/'install.tiff';background(art,icon,'Apple silicon' if arm else 'Intel')
        settings={'format':'ULFO','files':[str(app)],'symlinks':{'Applications':'/Applications'},'background':str(art),'icon':str(app/'Contents/Resources/BoardLens.icns'),'icon_locations':{'BoardLens.app':(180,222),'Applications':(500,222)},'show_status_bar':False,'show_tab_view':False,'show_toolbar':False,'show_pathbar':False,'show_sidebar':False,'window_rect':((200,200),(680,462)),'default_view':'icon-view','include_icon_view_settings':True,'icon_size':104,'text_size':14,'arrange_by':None,'grid_offset':(0,0),'scroll_position':(0,0)}
        dmgbuild.build_dmg(str(destination),'Install BoardLens',settings=settings)
    subprocess.run(['/usr/bin/hdiutil','verify',str(destination)],check=True,stdout=subprocess.DEVNULL)
    with tempfile.TemporaryDirectory(prefix='boardlens-verify-') as folder:
        mount=Path(folder)/'mounted';mount.mkdir()
        subprocess.run(['/usr/bin/hdiutil','attach','-readonly','-nobrowse','-mountpoint',str(mount),str(destination)],check=True,stdout=subprocess.DEVNULL)
        try:
            assert (mount/'Applications').resolve()==Path('/Applications')
            subprocess.run(['/usr/bin/codesign','--verify','--strict',str(mount/'BoardLens.app')],check=True)
        finally:subprocess.run(['/usr/bin/hdiutil','detach',str(mount)],check=True,stdout=subprocess.DEVNULL)
    record={'asset':destination.name,'sha256':sha(destination),'architecture':platform.machine()}
    metadata=out/'native-build.json'
    if metadata.exists():
        data=json.loads(metadata.read_text());data.update(dmg_asset=record['asset'],dmg_sha256=record['sha256']);metadata.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()
