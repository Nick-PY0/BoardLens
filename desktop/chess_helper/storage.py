"""Atomic persistence shared by local preferences."""
import json
from pathlib import Path


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    temporary.replace(path)
