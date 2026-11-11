"""Pin one source; covered pixel targets pause rather than reading another app."""
from __future__ import annotations
import os,sys
from dataclasses import asdict
from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication
from .capture import BoardRegion,screen_key,input_point


def window_at(rect,owner=None):
    if sys.platform=='darwin':
        import Quartz as CG
        for window in CG.CGWindowListCopyWindowInfo(CG.kCGWindowListOptionOnScreenOnly,0):
            if window.get('kCGWindowLayer',0)!=0 or window.get('kCGWindowAlpha',1)<.9:continue
            pid=int(window.get('kCGWindowOwnerPID',0))
            if pid==os.getpid() or owner is not None and pid!=owner:continue
            b=window.get('kCGWindowBounds',{});frame=QRect(*[round(b.get(k,0)) for k in ('X','Y','Width','Height')])
            if frame.contains(rect.center()):return {'id':int(window['kCGWindowNumber']),'pid':pid,'name':window.get('kCGWindowOwnerName','Target app'),'frame':list(frame.getRect())}
    elif sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        api=ctypes.windll.user32;api.GetTopWindow.restype=wintypes.HWND;api.GetWindow.restype=wintypes.HWND
        api.GetWindow.argtypes=[wintypes.HWND,wintypes.UINT];api.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)];api.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
        api.IsWindowVisible.argtypes=[wintypes.HWND];api.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        screen=next((s for s in QGuiApplication.screens() if s.geometry().contains(rect.center())),QGuiApplication.primaryScreen())
        px,py=input_point((rect.center().x(),rect.center().y()),screen);hwnd=api.GetTopWindow(None)
        while hwnd:
            pid=wintypes.DWORD();api.GetWindowThreadProcessId(hwnd,ctypes.byref(pid));b=wintypes.RECT()
            if api.IsWindowVisible(hwnd) and pid.value!=os.getpid() and (owner is None or pid.value==owner) and api.GetWindowRect(hwnd,ctypes.byref(b)):
                if b.left<=px<b.right and b.top<=py<b.bottom:
                    title=ctypes.create_unicode_buffer(300);api.GetWindowTextW(hwnd,title,300)
                    return {'id':int(hwnd),'pid':pid.value,'name':title.value or 'Target app','frame':[b.left,b.top,b.right-b.left,b.bottom-b.top]}
            hwnd=api.GetWindow(hwnd,2)
    return None


class TargetLock:
    def __init__(self):self.target=None
    @property
    def active(self):return self.target is not None
    @property
    def route(self):return self.target.get('route') if self.target else None
    def clear(self):self.target=None
    def restore(self,value):
        try:
            if not isinstance(value,dict) or value.get('route') not in ('browser','native','other'):return False
            if value.get('source') is not None and (not isinstance(value['source'],str) or len(value['source'])>512):return False
            region=BoardRegion(**value['region'])
            if not isinstance(region.screen_name,str) or not all(isinstance(v,(int,float)) and v>=0 for v in (region.x,region.y,region.size)) or region.size<80:return False
            if value.get('rect') is not None and (not isinstance(value['rect'],list) or len(value['rect'])!=4 or not all(isinstance(v,int) for v in value['rect'])):return False
            if value.get('window') is not None and (not isinstance(value['window'],dict) or not isinstance(value['window'].get('id'),int)):return False
            self.target=value;return True
        except (TypeError,ValueError,KeyError):return False
    def capture(self,read,region,route):
        if read is None or region is None:raise ValueError('Read a board before locking it.')
        source=getattr(read,'source_id',None);rect=None;owner=None
        if getattr(read,'desktop_rect',None):rect=QRect(*[round(v) for v in read.desktop_rect])
        elif not source:
            screen=next((s for s in QGuiApplication.screens() if screen_key(s)==region.screen_name),None)
            if screen:rect=region.desktop_rect(screen.geometry())
        if source and source.startswith('native:'):owner=int(source.split(':')[1])
        if source and source.startswith('native:'):route='native'
        elif source and source.startswith('browser:'):route='browser'
        window=window_at(rect,owner) if rect else None
        self.target={'source':source,'region':asdict(region),'route':route,'window':window,'rect':list(rect.getRect()) if rect else None}
    def filter(self,answers):
        if not self.target:return answers
        target=self.target;result=[]
        for answer in answers:
            key,_,read,width,height=answer
            if target['source']:
                if getattr(read,'source_id',None)==target['source']:result.append(answer)
            else:
                region=BoardRegion(**target['region']);d=read.detection
                if key==region.screen_name and abs(d.x-region.x)<max(8,region.size*.12) and abs(d.y-region.y)<max(8,region.size*.12) and abs(d.size-region.size)<region.size*.15:result.append(answer)
        return result[:1]
    def overlay_visible(self):
        if not self.target or not self.target.get('window') or not self.target.get('rect'):return True
        visible=window_at(QRect(*self.target['rect']))
        return bool(visible and visible['id']==self.target['window']['id'])
    def pixel_visible(self):return self.overlay_visible()
