"""Ask macOS for native Chess reader access; the user controls the OS grant."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chess_helper.native_chess import request_access
print('Accessibility ready.' if request_access() else 'Enable BoardLens/Python in System Settings → Privacy & Security → Accessibility.')
