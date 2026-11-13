"""Normalize ILSpy 11.2.0.10050 output from the verified recovery assembly."""
from pathlib import Path
import re,sys
source=Path(sys.argv[1]).read_text()
source=re.sub(r"^.*Not supported: data.*\n","",source,flags=re.M)
source=re.sub(r"^\[assembly:.*\n","",source,flags=re.M)
source=source.replace("using ChessChallenge.API;","using ChessChallenge.API;\nusing Timer=ChessChallenge.API.Timer;")
source=source.replace("internal static class ime","namespace auto_Bot_610_original;\n\ninternal static class ime")
for old,new in [("ime","Tables"),("me","EvaluationState"),("time","DataBlock"),("e","Search")]:source=re.sub(r"\b"+old+r"\b",new,source)
source=source.replace("262144","BoardLens.Mobile.TinyMemory.HashEntries")
header="// TinyHugeBot, Popax21 and atpx8. MIT challenge submission.\n// Decompiled from the verified submitted payload for normal Android compilation.\n// Reproduction and adaptations: ../Vendor/TinyHuge/README.md.\n"
Path(sys.argv[2]).write_text(header+source)
