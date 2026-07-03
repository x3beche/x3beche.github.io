#!/usr/bin/env python3
"""
build.py — veri değişince TÜRETİLMİŞ dosyaları yeniden kurar.

Sırayla çalıştırır:
    scripts/gen-deck-index.py   → <deck>/index.json + llms.txt + llms-full.txt + kök llms.txt
    scripts/gen-graph.py        → kök graph.json (ilişki grafı)

Yeni rehber/deck ekledikten SONRA bir kez çalıştır. Proxy'nin sync döngüsü de
`--if-stale` ile çağırır (yalnızca bir HTML dosyası graph.json'dan yeniyse yeniden
kurar — aksi halde bedava no-op).

Kullanım:
    python scripts/build.py             # her zaman yeniden kur
    python scripts/build.py --if-stale  # sadece bayatsa (ucuz kontrol)
"""

import os
import sys
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"_site", ".jekyll-cache", ".git", ".github", ".claude",
        "_layouts", "assets", "scripts", "mcp", "node_modules", "deck-assets"}
GRAPH = os.path.join(REPO_ROOT, "graph.json")


def newest_html_mtime():
    newest = 0.0
    for name in os.listdir(REPO_ROOT):
        p = os.path.join(REPO_ROOT, name)
        if not os.path.isdir(p) or name in SKIP or name.startswith("."):
            continue
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in SKIP]
            for f in files:
                if f.endswith(".html"):
                    try:
                        newest = max(newest, os.path.getmtime(os.path.join(root, f)))
                    except OSError:
                        pass
    return newest


def is_stale():
    if not os.path.isfile(GRAPH):
        return True
    return newest_html_mtime() > os.path.getmtime(GRAPH)


def _run(script):
    r = subprocess.run([sys.executable, os.path.join(REPO_ROOT, "scripts", script)],
                       capture_output=True, text=True)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.returncode != 0 and r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr)
    return r.returncode


def main():
    if "--if-stale" in sys.argv and not is_stale():
        return 0
    rc = _run("gen-deck-index.py")
    rc = _run("gen-graph.py") or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
