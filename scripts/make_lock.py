"""requirements.txt'ten gecisli (transitive) pinli requirements.lock uretir (yalniz runtime bagimliliklari).

Kullanim (proje kokunden, guncel venv ile): .venv/Scripts/python.exe scripts/make_lock.py
Once `pip install -U -r requirements.txt` ve testleri calistirin; sonra `pip check`."""
import re
import sys
from importlib import metadata

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

direct = []
for line in open("requirements.txt", encoding="utf-8"):
    line = line.split("#")[0].strip()
    if line:
        direct.append(Requirement(line))

seen: dict[str, str] = {}
display: dict[str, str] = {}


def visit(name: str) -> None:
    key = canonicalize_name(name)
    if key in seen:
        return
    dist = metadata.distribution(name)
    seen[key] = dist.version
    display[key] = dist.metadata["Name"]
    for raw in dist.requires or []:
        req = Requirement(raw)
        if req.marker is not None and not req.marker.evaluate({"extra": ""}):
            continue
        try:
            visit(req.name)
        except metadata.PackageNotFoundError:
            print("UYARI: kurulu degil (atlandi):", req.name, file=sys.stderr)


for req in direct:
    visit(req.name)

lines = sorted((f"{display[k]}=={v}" for k, v in seen.items()), key=str.lower)
open("requirements.lock", "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print(len(lines), "paket")
