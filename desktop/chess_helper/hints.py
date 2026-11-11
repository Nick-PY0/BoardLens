"""Steady provisional hints without delaying the first or final recommendation."""
from copy import deepcopy
import time

class LiveHintFilter:
    def __init__(self,hold=.25):self.hold=hold;self.reset()
    def reset(self):
        self.displayed=None;self.pending=None;self.since=0.;self.last_input=None
    @staticmethod
    def signature(result):
        return tuple((line['move'],line.get('reply_move','')) for line in result['lines'])
    def select(self,result,enabled,now=None):
        if result is None:return None
        if not enabled:
            self.reset();return result
        if self.displayed and self.displayed['fen']!=result['fen']:self.reset()
        if result is self.last_input:return self.displayed
        self.last_input=result;now=time.monotonic() if now is None else now
        key=self.signature(result)
        if self.displayed is None or not result.get('provisional') or key==self.signature(self.displayed):
            self.displayed=deepcopy(result);self.pending=None
        elif key!=self.pending:self.pending=key;self.since=now
        elif now-self.since>=self.hold:self.displayed=deepcopy(result);self.pending=None
        return self.displayed
