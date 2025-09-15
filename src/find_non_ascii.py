import pathlib, re
bad = re.compile(r"[^\x00-\x7F]")
for p in pathlib.Path(".").rglob("*.*"):
    if p.suffix.lower() in {".py",".md",".json",".txt"}:
        t = p.read_text(encoding="utf-8", errors="ignore")
        if bad.search(t):
            print("Non-ASCII in:", p)
