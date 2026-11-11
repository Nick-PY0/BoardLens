"""Gradient grid detection adapted from Fenshot (MIT) and tensorflow_chessbot.

The model and upstream licenses are bundled under assets/licenses. This module
uses NumPy for the row/column Hough responses, keeping detection off the UI thread.
"""
from __future__ import annotations

import cv2
import numpy as np

from .vision import Detection, checker_score, detect_boards


def _sequences(response):
    peak = cv2.dilate(response.reshape(1, -1), np.ones((1, 9), np.uint8)).ravel()
    indexes = np.flatnonzero((response >= peak) & (response > response.max() * .17))
    if len(indexes) > 100:
        indexes = np.sort(indexes[np.argsort(response[indexes])[-100:]])
    sequences, seen = [], set()
    for i, first in enumerate(indexes[:-6]):
        for second in indexes[i+1:]:
            spacing = int(second - first)
            if spacing < 12:
                continue
            if first + 6 * spacing > len(response) + 5:
                break
            line = [int(first), int(second)]
            while True:
                target = line[-1] + spacing
                k = int(np.searchsorted(indexes, target))
                choices = indexes[max(0, k-1):k+1]
                if not len(choices):
                    break
                candidate = int(min(choices, key=lambda value: abs(value - target)))
                if abs(candidate - target) >= max(3, spacing * .045) or candidate <= line[-1]:
                    break
                line.append(candidate)
            if len(line) >= 7 and tuple(line) not in seen:
                seen.add(tuple(line))
                sequences.append(line)
    sequences.sort(key=lambda line: np.mean(response[line]), reverse=True)
    return sequences[:8]


def _extents(sequences):
    result = []
    for line in sequences:
        spacing = float(np.median(np.diff(line)))
        for start in range(len(line) - 6):
            a, b = round(line[start] - spacing), round(line[start+6] + spacing)
            if (a, b) not in result:
                result.append((a, b))
    return result


def grid_candidates(image, cancelled=None, limit=8):
    scale = min(1., 1600 / max(image.shape[:2]))
    small = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else image
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gy, gx = np.gradient(gray)
    rows = np.maximum(gy, 0).sum(1) * np.maximum(-gy, 0).sum(1)
    cols = np.maximum(gx, 0).sum(0) * np.maximum(-gx, 0).sum(0)
    xs, ys = _extents(_sequences(cols)), _extents(_sequences(rows))
    boxes = []
    for x0, x1 in xs:
        for y0, y1 in ys:
            if cancelled and cancelled.is_set():
                return []
            size = round(((x1 - x0) + (y1 - y0)) / 2)
            if size < 160 or abs((x1 - x0) - (y1 - y0)) > size * .025:
                continue
            x, y = round((x0 + x1 - size) / 2), round((y0 + y1 - size) / 2)
            if min(x, y) < -3 or x + size > small.shape[1] + 3 or y + size > small.shape[0] + 3:
                continue
            x, y = max(0, x), max(0, y)
            if x+size > small.shape[1] or y+size > small.shape[0]:
                continue
            score = checker_score(small[y:y+size, x:x+size])
            if score < .65:
                continue
            if any(abs(x - b.x) < size * .04 and abs(y - b.y) < size * .04 and abs(size-b.size) < size * .04 for b in boxes):
                continue
            boxes.append(Detection(x, y, size, score))
    # A plausible but offset gradient grid must not suppress a better color
    # component box. Native display scaling can shift the strongest edge peaks.
    if not (cancelled and cancelled.is_set()):
        # Resize once from the original frame. Resizing 4K -> gradient size ->
        # component size can merge tile-color components at fractional scales.
        boxes.extend(Detection(b.x*scale,b.y*scale,b.size*scale,b.score)
                     for b in detect_boards(image,limit=limit))
    boxes.sort(key=lambda box: (box.score, box.size), reverse=True)
    unique=[]
    for box in boxes:
        if not any(abs(box.x-u.x)<box.size*.035 and abs(box.y-u.y)<box.size*.035
                   and abs(box.size-u.size)<box.size*.035 for u in unique):
            unique.append(box)
    return [Detection(round(box.x/scale), round(box.y/scale), round(box.size/scale), box.score)
            for box in unique[:limit]]


def refine_grid(image,detection):
    """Recover outer edges when resized component widths undershoot by a pixel."""
    from .vision import board_colors
    d=detection
    tile=d.size/8
    pad=round(tile*.45)
    x0,y0=max(0,d.x-pad),max(0,d.y-pad)
    x1,y1=min(image.shape[1],d.x+d.size+pad),min(image.shape[0],d.y+d.size+pad)
    crop=image[d.y:d.y+d.size,d.x:d.x+d.size]
    samples=board_colors(crop)
    if samples is None:return d
    parity=np.indices((8,8)).sum(0)%2
    colors=[np.median(samples[parity==p],axis=0) for p in (0,1)]
    roi=image[y0:y1,x0:x1]
    mask=np.zeros(roi.shape[:2],np.uint8)
    for color in colors:
        mask|=cv2.inRange(roi,np.clip(color-18,0,255).astype(np.uint8),np.clip(color+18,0,255).astype(np.uint8))
    left,right=round(d.x+d.size*.25)-x0,round(d.x+d.size*.75)-x0
    top,bottom=round(d.y+d.size*.25)-y0,round(d.y+d.size*.75)-y0
    columns=(mask[top:bottom].mean(0)>255*.38).astype(np.uint8)
    rows=(mask[:,left:right].mean(1)>255*.38).astype(np.uint8)
    kernel=max(3,round(tile*.45))
    columns=cv2.morphologyEx(columns[None,:],cv2.MORPH_CLOSE,np.ones((1,kernel),np.uint8)).ravel()
    rows=cv2.morphologyEx(rows[:,None],cv2.MORPH_CLOSE,np.ones((kernel,1),np.uint8)).ravel()
    xs,ys=np.flatnonzero(columns),np.flatnonzero(rows)
    if not len(xs) or not len(ys):return d
    width,height=int(xs[-1]-xs[0]+1),int(ys[-1]-ys[0]+1)
    size=round((width+height)/2)
    x,y=x0+int(xs[0]),y0+int(ys[0])
    if abs(width-height)>d.size*.025 or abs(size-d.size)>d.size*.05:return d
    if x+size>image.shape[1] or y+size>image.shape[0]:return d
    return Detection(x,y,size,d.score)
