from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chess
import cv2
import numpy as np

from .core import ordered_symbols


@dataclass(frozen=True)
class Detection:
    x: int
    y: int
    size: int
    score: float


def board_colors(image):
    h,w=image.shape[:2]
    if min(h,w)<160:return None
    cells=np.indices((8,8)).reshape(2,-1).T
    corners=np.array(((.13,.13),(.13,.87),(.87,.13),(.87,.87)))
    centers=(cells[:,None,:]+corners[None,:,:])*np.array((h/8,w/8))
    centers=centers.astype(int)
    offsets=np.array([(y,x) for y in (-1,0,1) for x in (-1,0,1)])
    coords=centers[:,:,None,:]+offsets[None,None,:,:]
    colors=image[coords[...,0],coords[...,1]].mean(axis=2)
    return np.median(colors,axis=1).reshape(8,8,3)


def checker_score(image):
    """Validate all squares, sampling corners without a Python pixel loop."""
    samples=board_colors(image)
    if samples is None:return 0.
    parity=np.indices((8,8)).sum(axis=0)%2
    a,b=np.median(samples[parity==0],axis=0),np.median(samples[parity==1],axis=0)
    contrast=np.linalg.norm(a-b)
    if contrast<22:return 0.
    errors=np.linalg.norm(samples-np.where(parity[...,None]==0,a,b),axis=2)
    return float(np.mean(errors<max(20,contrast*.32)))


def complete_grid(image):
    """A one-file shift reverses the light top-left corner of a chessboard."""
    samples=board_colors(image)
    if samples is None:return False
    parity=np.indices((8,8)).sum(axis=0)%2
    a,b=np.median(samples[parity==0],axis=0),np.median(samples[parity==1],axis=0)
    luma=np.array((.114,.587,.299))
    return float((a-b)@luma)>=-5 and checker_score(image)>=.90


def detect_boards(image, limit=8):
    """Find flat checkerboards using background-color components, then validate all 64 cells."""
    scale = min(1., 1400 / max(image.shape[:2]))
    small = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else image
    h, w = small.shape[:2]
    sample = small[::3, ::3]
    quant = (sample.astype(np.int32) // 20).reshape(-1, 3)
    bins, counts = np.unique(quant, axis=0, return_counts=True)
    tiles = []
    for idx in np.argsort(counts)[-16:]:
        color = bins[idx] * 20 + 10
        mask = cv2.inRange(small, np.clip(color - 24, 0, 255).astype(np.uint8),
                           np.clip(color + 24, 0, 255).astype(np.uint8))
        n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)
        for x, y, tw, th, area in stats[1:]:
            if 20 <= tw <= min(w, h) / 5 and .94 <= tw / max(th, 1) <= 1.06 and area > tw * th * .42:
                tiles.append((int(x), int(y), int(round((tw + th) / 2))))
    votes = {}
    for x, y, cell in tiles:
        for row in range(8):
            yy = y - row * cell
            if yy < -2 or yy + 8 * cell > h + 2:
                continue
            for col in range(8):
                xx = x - col * cell
                if xx < -2 or xx + 8 * cell > w + 2:
                    continue
                key = (round(xx / 4), round(yy / 4), round(cell / 2))
                if key not in votes:
                    votes[key] = [0, max(0, xx), max(0, yy), cell * 8]
                votes[key][0] += 1
    found = []
    for _, x, y, size in sorted(votes.values(), reverse=True)[:70]:
        if x + size > w or y + size > h:
            continue
        if any(abs(x - d.x * scale) < size * .12 and abs(y - d.y * scale) < size * .12
               and abs(size - d.size * scale) < size * .12 for d in found):
            continue
        score = checker_score(small[y:y+size, x:x+size])
        if score >= .86:
            found.append(Detection(round(x / scale), round(y / scale), round(size / scale), score))
    return sorted(found, key=lambda d: (d.score, d.size), reverse=True)[:limit]


def split_tiles(image):
    normalized = cv2.resize(image, (512, 512), interpolation=cv2.INTER_AREA)
    return [normalized[r*64:(r+1)*64, c*64:(c+1)*64] for r in range(8) for c in range(8)]


def feature(tile):
    tile = cv2.resize(tile, (48, 48), interpolation=cv2.INTER_AREA).astype(np.float32)
    corners = np.concatenate([tile[3:9, 3:9].reshape(-1, 3), tile[3:9, -9:-3].reshape(-1, 3),
                              tile[-9:-3, 3:9].reshape(-1, 3), tile[-9:-3, -9:-3].reshape(-1, 3)])
    bg = np.median(corners, axis=0)
    distance = np.linalg.norm(tile - bg, axis=2)
    mask = (distance > 36).astype(np.uint8)
    mask[:4, :] = 0
    mask[-4:, :] = 0
    mask[:, :4] = 0
    mask[:, -4:] = 0
    # Discard coordinate labels, speckles and arrows at the square's edge.
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    clean = np.zeros_like(mask)
    for idx in range(1, n):
        if stats[idx, cv2.CC_STAT_AREA] >= 12:
            clean[labels == idx] = 1
    gray = cv2.cvtColor(tile.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    return np.stack([clean.astype(np.float32), gray], axis=0)


def distance(a, b):
    union = np.maximum(a[0], b[0])
    area = float(union.sum())
    if area < 10:
        return 0.0
    shape = float(np.abs(a[0] - b[0]).sum()) / area
    color = float((np.abs(a[1] - b[1]) * np.minimum(a[0], b[0])).sum()) / area
    return shape * .70 + color * .60


class Templates:
    def __init__(self, symbols=None, features=None):
        self.symbols = list(symbols) if symbols is not None else []
        self.features = list(features) if features is not None else []

    @property
    def complete(self):
        return set("PNBRQKpnbrqk.").issubset(self.symbols)

    @classmethod
    def learn(cls, image, board, white_bottom):
        symbols = ordered_symbols(board, white_bottom)
        result = cls(symbols, [feature(t) for t in split_tiles(image)])
        # Catch an empty/incorrect crop rather than declaring calibration successful.
        occupied = [f[0].sum() for s, f in zip(symbols, result.features) if s != "."]
        empty = [f[0].sum() for s, f in zip(symbols, result.features) if s == "."]
        if not occupied or np.median(occupied) < 60 or (empty and np.median(empty) > 50):
            raise ValueError("This does not look like the selected position. Use an unhighlighted starting board and crop exactly its 64 squares.")
        return result

    def read(self, image):
        if not self.complete:
            raise ValueError("Learn a starting board first so all twelve piece types are available.")
        symbols, confidence = [], []
        labels = list(".PNBRQKpnbrqk")
        for tile in split_tiles(image):
            observed = feature(tile)
            scores = [min(distance(observed, f) for s, f in zip(self.symbols, self.features) if s == label)
                      for label in labels]
            order = np.argsort(scores)
            best, runner = int(order[0]), int(order[1])
            symbols.append(labels[best])
            confidence.append((float(scores[best]), float(scores[runner] - scores[best])))
        reliable = all(error <= .29 and margin >= .025 for error, margin in confidence)
        return symbols, reliable, confidence

    def save(self, path):
        np.savez_compressed(path, symbols=np.asarray(self.symbols), features=np.asarray(self.features))

    @classmethod
    def load(cls, path: Path):
        with np.load(path, allow_pickle=False) as data:
            return cls(data["symbols"].tolist(), data["features"])
