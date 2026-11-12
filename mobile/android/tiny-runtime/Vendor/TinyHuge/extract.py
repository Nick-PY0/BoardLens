from pathlib import Path
import struct
import re,decimal,hashlib,sys
source=Path(__file__).parent/'Bot_610.original.cs.txt'
text=source.read_text().split('BEGIN ENCODED ASSEMBLY')[1].split('END ENCODED ASSEMBLY')[0]
b=bytearray(10752);offset=parity=accum=0
for token in re.findall(r'([0-9]+(?:\.[0-9]+)?)M',text):
 value=decimal.Decimal(token);scale=max(0,-value.as_tuple().exponent);digits=int(''.join(map(str,value.as_tuple().digits)))
 if scale==16:offset+=digits&255
 else:
  accum=((accum<<4)|scale)&255;b[offset]=accum;offset+=1;parity^=1;offset-=parity
 for index in range(scale>>4,12):b[offset]=(digits>>(index*8))&255;offset+=1
assert hashlib.sha256(b).hexdigest()=='2269e8215864e794a7f53826ef7eeed687a9a4163c0ca53dc8f86c84f26aa757'
pe=struct.unpack_from('<I',b,60)[0];ns=struct.unpack_from('<H',b,pe+6)[0];os=struct.unpack_from('<H',b,pe+20)[0];opt=pe+24;dirs=opt+(112 if struct.unpack_from('<H',b,opt)[0]==0x20b else 96);mapping=[]
for i in range(ns):
 vs,va,rs,rp=struct.unpack_from('<IIII',b,opt+os+40*i+8);mapping.append((va,max(vs,rs),rp))
def at(rva):return next(rp+rva-va for va,size,rp in mapping if va<=rva<va+size)
cli=at(struct.unpack_from('<I',b,dirs+14*8)[0]);meta=at(struct.unpack_from('<I',b,cli+8)[0]);vl=struct.unpack_from('<I',b,meta+12)[0];cursor=(meta+16+vl+3)&~3;prefix=bytes(b[meta:cursor]);flags,n=struct.unpack_from('<HH',b,cursor);cursor+=4;streams=[]
for _ in range(n):
 off,size=struct.unpack_from('<II',b,cursor);end=b.index(0,cursor+8);streams.append((bytes(b[cursor+8:end]),bytes(b[meta+off:meta+off+size])));cursor=(end+4)&~3
streams.append((b'#GUID',bytes(32)));header_len=len(prefix)+4+sum(8+((len(name)+4)//4)*4 for name,data in streams);headers=bytearray();payload=bytearray();offset=header_len
for name,data in streams:
 headers+=struct.pack('<II',offset,len(data))+name+b'\0'+bytes((-(len(name)+1))%4);payload+=data;pad=(-len(data))%4;payload+=bytes(pad);offset+=len(data)+pad
metadata=prefix+struct.pack('<HH',flags,len(streams))+headers+payload
fa,sa=struct.unpack_from('<II',b,opt+36)[0],struct.unpack_from('<I',b,opt+32)[0];new_offset=(len(b)+fa-1)//fa*fa;section=opt+os+(ns-1)*40;va,rp=struct.unpack_from('<I',b,section+12)[0],struct.unpack_from('<I',b,section+20)[0];rva=va+new_offset-rp;length=new_offset+len(metadata)-rp;raw=(length+fa-1)//fa*fa
struct.pack_into('<II',b,cli+8,rva,len(metadata));struct.pack_into('<I',b,section+8,length);struct.pack_into('<I',b,section+16,raw);struct.pack_into('<I',b,opt+56,(va+length+sa-1)//sa*sa);b+=bytes(new_offset-len(b))+metadata;b+=bytes(rp+raw-len(b));Path(sys.argv[1]).write_bytes(b)
