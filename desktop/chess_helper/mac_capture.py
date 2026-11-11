"""Compositor snapshots exclude our panel without hiding it on screen.

Called by the vision worker, never by Qt's UI thread. Cancellation stays bounded
even when the system capture API is waiting for a frame or permission.
"""
from __future__ import annotations

import os
import threading
import time

import cv2
import numpy as np

_cached_content = None
_cached_at = 0.
_cached_exclusions = set()


class CaptureCancelled(Exception):
    pass


def _await(start, cancelled, timeout=2):
    completed = threading.Event()
    result = []
    def callback(value, error):
        result.extend((value, error))
        completed.set()
    start(callback)
    deadline = time.monotonic()+timeout
    while not completed.wait(.03):
        if cancelled.is_set():
            raise CaptureCancelled()
        if time.monotonic()>deadline:
            raise RuntimeError('Screen capture timed out. Check Screen Recording access for your launcher.')
    if cancelled.is_set():
        raise CaptureCancelled()
    value, error = result
    if error or value is None:
        raise RuntimeError(f'Screen capture is unavailable: {error or "no image"}. Check Screen Recording access.')
    return value


def _bgr(image):
    import Quartz as CG
    width, height = CG.CGImageGetWidth(image), CG.CGImageGetHeight(image)
    stride = CG.CGImageGetBytesPerRow(image)
    info = CG.CGImageGetBitmapInfo(image)
    raw = CG.CGDataProviderCopyData(CG.CGImageGetDataProvider(image))
    if CG.CGImageGetBitsPerPixel(image)==32:
        # IOSurface providers can include allocation padding after the last row.
        pixels = np.frombuffer(raw, np.uint8, count=height*stride).reshape(height, stride)[:, :width*4].reshape(height,width,4)
        # ScreenCaptureKit delivers BGRA, premultiplied first, little endian.
        if (info & CG.kCGBitmapByteOrderMask)==CG.kCGBitmapByteOrder32Little:
            return pixels[:,:,:3].copy()
        return cv2.cvtColor(pixels, cv2.COLOR_RGBA2BGR)
    # Handle less common OS pixel formats through Apple's image decoder.
    import AppKit
    rep = AppKit.NSBitmapImageRep.alloc().initWithCGImage_(image)
    png = rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG,{})
    return cv2.imdecode(np.frombuffer(png,np.uint8),cv2.IMREAD_COLOR)


def capture_frames(specs, excluded_window_ids, cancelled):
    global _cached_content, _cached_at, _cached_exclusions
    import objc
    import Quartz  # Register CGImage's CoreFoundation bridge before callbacks.
    with objc.autorelease_pool():
        if not Quartz.CGPreflightScreenCaptureAccess():
            raise RuntimeError('Screen Recording access is required for your launcher. Allow it and restart BoardLens.')
        import ScreenCaptureKit as SC
        # The synchronous compositor snapshot avoids creating a new screenshot
        # session on each refresh. Explicit window IDs omit only our panel.
        # Run it here on the worker, so capture never blocks the UI.
        if (os.environ.get('BOARDLENS_LEGACY_CAPTURE')=='1' or not hasattr(SC,'SCScreenshotManager')) and hasattr(Quartz,'CGWindowListCreateImageFromArray'):
            windows=Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly,0)
            frames=[]
            for spec in specs:
                if cancelled.is_set():
                    raise CaptureCancelled()
                full_spec=spec
                crop=spec.get('crop')
                if crop:
                    x,y,size=crop
                    gx,gy,gw,gh=spec['geometry']
                    spec=dict(spec,geometry=(gx+x*gw/spec['width'],gy+y*gh/spec['height'],
                                             size*gw/spec['width'],size*gh/spec['height']),width=size,height=size)
                gx,gy,gw,gh=spec['geometry']
                helper_masks=[]
                if 'owner_pid' in spec:
                    # A helper behind the browser does not obscure the board.
                    # Mask only parts of our UI which are actually visible.
                    helper_masks=_visible_helper_masks(windows,spec['owner_pid'],excluded_window_ids)
                    spec=dict(spec,masks=helper_masks)
                flags=Quartz.kCGWindowImageBoundsIgnoreFraming|Quartz.kCGWindowImageBestResolution
                obscured=any(rx<gx+gw and rx+rw>gx and ry<gy+gh and ry+rh>gy
                             for rx,ry,rw,rh in helper_masks)
                if 'owner_pid' in spec or obscured or len(excluded_window_ids)>1:
                    # Recompose without any of our UI, so opening Settings or
                    # expanding the helper cannot black out the target board.
                    ids=[int(w['kCGWindowNumber']) for w in windows
                         if int(w.get('kCGWindowOwnerPID',0))!=spec.get('owner_pid')
                         and int(w['kCGWindowNumber']) not in excluded_window_ids]
                    image=Quartz.CGWindowListCreateImageFromArray(Quartz.CGRectMake(gx,gy,gw,gh),ids,flags)
                    spec=dict(spec,masks=[])
                elif excluded_window_ids:
                    # Capture the composited windows underneath our floating
                    # panel, rather than re-rendering every app window separately.
                    image=Quartz.CGWindowListCreateImage(Quartz.CGRectMake(gx,gy,gw,gh),
                        Quartz.kCGWindowListOptionOnScreenBelowWindow,next(iter(excluded_window_ids)),flags)
                else:
                    image=Quartz.CGWindowListCreateImage(Quartz.CGRectMake(gx,gy,gw,gh),
                        Quartz.kCGWindowListOptionOnScreenOnly,0,flags)
                if image is None:
                    break
                pixels=_bgr(image)
                pixels=_normalize_and_mask(pixels,spec)
                frame=(spec['key'],spec['name'],pixels)
                if crop:frame+=(tuple(crop)+(full_spec['width'],full_spec['height']),)
                frames.append(frame)
            if len(frames)==len(specs):
                return frames
        import ScreenCaptureKit as SC
        if (_cached_content is None or time.monotonic()-_cached_at>.25
                or excluded_window_ids!=_cached_exclusions):
            _cached_content = _await(lambda cb: SC.SCShareableContent.
                getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(True,True,cb), cancelled)
            _cached_at=time.monotonic()
            _cached_exclusions=set(excluded_window_ids)
        content=_cached_content
        owners={spec.get('owner_pid') for spec in specs}
        excluded = [w for w in content.windows() if int(w.windowID()) in excluded_window_ids
                    or (w.owningApplication() and int(w.owningApplication().processID()) in owners)]
        frames = []
        for spec in specs:
            if cancelled.is_set():
                raise CaptureCancelled()
            full_spec=spec
            if spec.get('owner_pid'):spec=dict(spec,masks=[])
            crop=spec.get('crop')
            gx,gy,gw,gh = spec['geometry']
            displays = [d for d in content.displays() if abs(d.frame().origin.x-gx)<2
                        and abs(d.frame().origin.y-gy)<2 and abs(d.frame().size.width-gw)<2
                        and abs(d.frame().size.height-gh)<2]
            if len(displays)!=1:
                raise RuntimeError('The display layout changed. Choose its monitor again.')
            filter = SC.SCContentFilter.alloc().initWithDisplay_excludingWindows_(displays[0],excluded)
            config = SC.SCStreamConfiguration.alloc().init()
            config.setWidth_(spec['width'])
            config.setHeight_(spec['height'])
            config.setShowsCursor_(False)
            if crop:
                x,y,size=crop
                config.setSourceRect_(((x*gw/spec['width'],y*gh/spec['height']),
                                      (size*gw/spec['width'],size*gh/spec['height'])))
                config.setWidth_(size);config.setHeight_(size)
                spec=dict(spec,geometry=(gx+x*gw/spec['width'],gy+y*gh/spec['height'],
                                         size*gw/spec['width'],size*gh/spec['height']),width=size,height=size)
            image = _await(lambda cb: SC.SCScreenshotManager.
                captureImageWithFilter_configuration_completionHandler_(filter,config,cb),cancelled)
            pixels = _normalize_and_mask(_bgr(image),spec)
            frame=(spec['key'],spec['name'],pixels)
            if crop:frame+=(tuple(crop)+(full_spec['width'],full_spec['height']),)
            frames.append(frame)
        return frames


def _normalize_and_mask(pixels,spec):
    if pixels.shape[:2]!=(spec['height'],spec['width']):
        pixels=cv2.resize(pixels,(spec['width'],spec['height']),interpolation=cv2.INTER_LINEAR)
    h,w=pixels.shape[:2]
    gx,gy,gw,gh=spec['geometry']
    for rx,ry,rw,rh in spec['masks']:
        x0,y0=max(0,round((rx-gx)*w/gw)),max(0,round((ry-gy)*h/gh))
        x1,y1=min(w,round((rx+rw-gx)*w/gw)),min(h,round((ry+rh-gy)*h/gh))
        pixels[y0:y1,x0:x1]=(24,30,36)
    return pixels


def _subtract_rect(rect, cover):
    x,y,w,h=rect;cx,cy,cw,ch=cover
    left,top=max(x,cx),max(y,cy)
    right,bottom=min(x+w,cx+cw),min(y+h,cy+ch)
    if right<=left or bottom<=top:
        return [rect]
    result=[]
    if top>y:result.append((x,y,w,top-y))
    if bottom<y+h:result.append((x,bottom,w,y+h-bottom))
    if left>x:result.append((x,top,left-x,bottom-top))
    if right<x+w:result.append((right,top,x+w-right,bottom-top))
    return result


def _visible_helper_masks(windows, owner_pid, excluded):
    covers=[];masks=[]
    for window in windows:
        if int(window.get('kCGWindowNumber',0)) in excluded:
            continue
        bounds=window.get('kCGWindowBounds',{})
        rect=tuple(float(bounds.get(key,0)) for key in ('X','Y','Width','Height'))
        if rect[2]<=0 or rect[3]<=0:
            continue
        if int(window.get('kCGWindowOwnerPID',0))==owner_pid:
            parts=[rect]
            for cover in covers:
                parts=[piece for part in parts for piece in _subtract_rect(part,cover)]
            masks.extend(parts)
        elif window.get('kCGWindowLayer',0)==0 and window.get('kCGWindowAlpha',1)>=.99:
            covers.append(rect)
    return masks
