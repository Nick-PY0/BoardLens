"""Cooperative macOS hotkeys, without recording other keyboard input."""
from __future__ import annotations

import ctypes as C


class HotKeyID(C.Structure):
    _fields_ = [('signature', C.c_uint32), ('id', C.c_uint32)]


class EventType(C.Structure):
    _fields_ = [('event_class', C.c_uint32), ('kind', C.c_uint32)]


KEYS = dict(zip('asdfhgzxcvbqwerty', [0,1,2,3,4,5,6,7,8,9,11,12,13,14,15,17,16]))
KEYS.update({'1':18,'2':19,'3':20,'4':21,'6':22,'5':23,'=':24,'9':25,'7':26,
             '-':27,'8':28,'0':29,']':30,'o':31,'u':32,'[':33,'i':34,'p':35,
             "'":39,'l':37,'j':38,'k':40,';':41,'\\':42,',':43,'/':44,'n':45,'m':46,'.':47})
KEYS.update(space=49, enter=36, return_=36, tab=48, esc=53, escape=53,
            left=123, right=124, down=125, up=126, home=115, end=119,
            page_up=116, page_down=121, delete=51, backspace=51)
KEYS.update({f'f{i}': code for i,code in enumerate([122,120,99,118,96,97,98,100,101,109,103,111],1)})
MODIFIERS = {'cmd':256, 'command':256, 'shift':512, 'alt':2048, 'option':2048, 'ctrl':4096, 'control':4096}
SIGNATURE = 0x424C4E53
HANDLER = C.CFUNCTYPE(C.c_int32,C.c_void_p,C.c_void_p,C.c_void_p)


def parse_combo(combo):
    parts=[p.strip().strip('<>') for p in combo.lower().split('+')]
    modifiers=0
    keys=[]
    for part in parts:
        if part in MODIFIERS:modifiers |= MODIFIERS[part]
        else:keys.append(part)
    if len(keys)!=1 or keys[0] not in KEYS:
        raise ValueError(f'Unsupported shortcut: {combo}. Use modifiers and one letter, arrow or function key.')
    if not modifiers:
        raise ValueError('Global shortcuts need a modifier such as <ctrl> or <alt>.')
    return KEYS[keys[0]],modifiers


class NativeHotkeys:
    def __init__(self,emit):
        self.emit=emit
        self.refs=[]
        self.handler=C.c_void_p()
        self.actions={}
        self.api=C.CDLL('/System/Library/Frameworks/Carbon.framework/Carbon')
        api=self.api
        api.GetApplicationEventTarget.restype=C.c_void_p
        api.InstallEventHandler.argtypes=[C.c_void_p,HANDLER,C.c_uint32,C.POINTER(EventType),C.c_void_p,C.POINTER(C.c_void_p)]
        api.RegisterEventHotKey.argtypes=[C.c_uint32,C.c_uint32,HotKeyID,C.c_void_p,C.c_uint32,C.POINTER(C.c_void_p)]
        api.GetEventParameter.argtypes=[C.c_void_p,C.c_uint32,C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_void_p]
        api.UnregisterEventHotKey.argtypes=[C.c_void_p]
        api.RemoveEventHandler.argtypes=[C.c_void_p]
        self.callback=HANDLER(self._event)

    def start(self,bindings):
        parsed=[(action,*parse_combo(combo)) for action,combo in bindings.items()]
        if len({(key,mods) for _,key,mods in parsed})!=len(parsed):
            raise ValueError('Two shortcuts resolve to the same key combination.')
        self.stop()
        api=self.api
        target=api.GetApplicationEventTarget()
        event=EventType(0x6B657962,6)
        status=api.InstallEventHandler(target,self.callback,1,C.byref(event),None,C.byref(self.handler))
        if status:raise RuntimeError(f'Could not install shortcut handler ({status}).')
        try:
            for index,(action,key,modifiers) in enumerate(parsed,1):
                ref=C.c_void_p()
                status=api.RegisterEventHotKey(key,modifiers,HotKeyID(SIGNATURE,index),target,0,C.byref(ref))
                if status:raise RuntimeError(f'Could not register {action} ({status}). Try another combination.')
                self.refs.append(ref)
                self.actions[index]=action
        except Exception:
            self.stop()
            raise

    def _event(self,_,event,__):
        identity=HotKeyID()
        status=self.api.GetEventParameter(event,0x2D2D2D2D,0x686B6964,None,C.sizeof(identity),None,C.byref(identity))
        if status==0 and identity.signature==SIGNATURE and identity.id in self.actions:
            self.emit(self.actions[identity.id])
            return 0
        return -9874

    def stop(self):
        for ref in self.refs:self.api.UnregisterEventHotKey(ref)
        self.refs.clear()
        self.actions.clear()
        if self.handler.value:
            self.api.RemoveEventHandler(self.handler)
            self.handler=C.c_void_p()
