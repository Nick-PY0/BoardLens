"""Read macOS Chess.app's accessible squares independently of its artwork."""
from __future__ import annotations
import re,sys,time
import chess
from .direct_boards import exact_read
PIECES={'pawn':'p','knight':'n','bishop':'b','rook':'r','queen':'q','king':'k'}


def projected_center(position,size,primary_height):
    # Apple's MBCBoardMTLAccessibilityProxy returns AppKit global coordinates,
    # whose vertical origin is at the bottom. Qt uses top-left coordinates.
    return position.x+size.width/2,primary_height-position.y-size.height/2


class NativeChessReader:
    def __init__(self):
        self.cached=[];self.at=0;self.nodes={};self.status='Enable macOS Accessibility for BoardLens/Python to read Chess.app.'
    def reads(self):
        if sys.platform!='darwin':return []
        if time.monotonic()-self.at<.075:return self.cached
        self.at=time.monotonic();self.cached=[]
        try:
            import ApplicationServices as AX
            from AppKit import NSRunningApplication,NSScreen
            if not AX.AXIsProcessTrusted():return []
            primary_height=NSScreen.screens()[0].frame().size.height
            def attr(node,name):
                error,value=AX.AXUIElementCopyAttributeValue(node,name,None)
                return value if error==0 else None
            def children(node):return attr(node,'AXChildren') or []
            def coordinate(node,name,kind):
                value=attr(node,name)
                if value is None:return None
                ok,result=AX.AXValueGetValue(value,kind,None)
                return result if ok else None
            for app in NSRunningApplication.runningApplicationsWithBundleIdentifier_('com.apple.Chess'):
                if app.isHidden():continue
                root=AX.AXUIElementCreateApplication(app.processIdentifier())
                for index,window in enumerate(attr(root,'AXWindows') or []):
                    if attr(window,'AXMinimized'):continue
                    identity=(app.processIdentifier(),index);cached=self.nodes.get(identity)
                    title=attr(window,'AXTitle') or '';squares={};points={}
                    if cached:tile_nodes=cached['nodes']
                    else:
                        pending=list(children(window));tile_nodes=[]
                        for _ in range(1200):
                            if not pending:break
                            node=pending.pop();desc=attr(node,'AXDescription') or ''
                            if re.search(r'\b[a-h][1-8]\b',desc) and attr(node,'AXRole')=='AXButton':tile_nodes.append(node)
                            pending.extend(children(node))
                    pos=coordinate(window,'AXPosition',AX.kAXValueCGPointType);size=coordinate(window,'AXSize',AX.kAXValueCGSizeType)
                    frame=(pos.x,pos.y,size.width,size.height) if pos and size else None
                    refresh_points=not cached or cached['frame']!=frame or time.monotonic()-cached['at']>.25
                    if not refresh_points:points=dict(cached['points'])
                    for node in tile_nodes:
                        desc=attr(node,'AXDescription') or '';match=re.search(r'\b([a-h][1-8])\b',desc)
                        if not match:continue
                        square=match.group(1);piece=next((symbol for name,symbol in PIECES.items() if name in desc.lower()),None)
                        squares[square]=piece.upper() if piece and 'white' in desc.lower() else piece
                        if refresh_points:
                            p=coordinate(node,'AXPosition',AX.kAXValueCGPointType);s=coordinate(node,'AXSize',AX.kAXValueCGSizeType)
                            if p and s:points[square]=projected_center(p,s,primary_height)
                    if len(squares)!=64:self.nodes.pop(identity,None);continue
                    self.nodes[identity]={'nodes':tile_nodes,'points':points,'frame':frame,'at':time.monotonic() if refresh_points else cached['at']}
                    board=chess.Board(None)
                    for square,symbol in squares.items():
                        if symbol:board.set_piece_at(chess.parse_square(square),chess.Piece.from_symbol(symbol))
                    board.turn='black to move' not in title.lower()
                    if board.board_fen()==chess.Board().board_fen():board=chess.Board()
                    bottom=points.get('a1',(0,1))[1]>points.get('a8',(0,0))[1]
                    rect=None;normalized=None
                    if len(points)==64:
                        xs,ys=zip(*points.values());pad=max(12,(max(xs)-min(xs))/14)
                        rect=(min(xs)-pad,min(ys)-pad,max(xs)-min(xs)+2*pad,max(ys)-min(ys)+2*pad)
                        normalized={chess.parse_square(k):((x-rect[0])/rect[2],(y-rect[1])/rect[3]) for k,(x,y) in points.items()}
                    key=f'native:{identity[0]}:{identity[1]}'
                    read=exact_read(board.fen(),bottom,key,normalized,rect);read.exact_fen=None
                    self.cached.append((key,'macOS Chess · 3D reader',read,256,256))
            self.status='Chess.app reader ready' if self.cached else 'No complete accessible Chess.app board found.'
        except Exception as exc:self.status='Chess.app reader: '+str(exc)
        return self.cached


def request_access():
    if sys.platform!='darwin':return False
    import ApplicationServices as AX
    return bool(AX.AXIsProcessTrustedWithOptions({AX.kAXTrustedCheckOptionPrompt:True}))
