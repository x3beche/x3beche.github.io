#!/usr/bin/env python3
"""
deck_proxy.py — x3beche-decks YEREL BİLGİ SUNUCUSU (offline, tek süreç)

Tek bir stdio MCP sunucusu; küçük yerel modeller (LM Studio Qwen3-4B vb.) için
72 deck-tool'u yerine SADE bir arayüz sunar:

  ÇEKIRDEK
    list_decks()                        → deck'ler (açık/kapalı durumu + sayı)
    search(query, deck=None, limit=5)   → AÇIK deck'lerde skorlu arama
    get_article(deck, slug)             → bir makalenin tam metni
  GRAF (ilişkiler — graph.json)
    related(deck, slug, limit=6)        → en ilgili rehberler
    graph_around(deck, slug, depth=1)   → konu komşuluğu (harita)
    path(a_deck, a_slug, b_deck, b_slug)→ iki konu arası bağlantı yolu

+ Kullanıcı KONTROL PANELİ (yerel web UI): hangi deck'lerin kullanılacağını
  aç/kapa. http://127.0.0.1:8765  (X3BECHE_UI=0 ile kapat, X3BECHE_UI_PORT ile port).
+ OTOMATİK SYNC: belli aralıkla `git pull` (senin repo/site) + index & graf rebuild.
  X3BECHE_SYNC=0 kapatır, X3BECHE_SYNC_SEC aralık (vars. 60).

Genel: yeni bir deck (stm32l4, usblib, herhangi bir kart...) klasörü + içine
`layout: tutorial` HTML koy → otomatik keşfedilir, indekslenir, graf'a girer,
panelde çıkar. Ek kod yok. Her şey offline / bağımlılıksız (fastmcp + stdlib).
"""

import os
import re
import sys
import json
import time
import threading
import subprocess
import html as _html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from fastmcp import FastMCP

REPO_ROOT = os.environ.get(
    "X3BECHE_REPO_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_state.json")
GRAPH_PATH = os.path.join(REPO_ROOT, "graph.json")

SKIP = {
    "_site", ".jekyll-cache", ".git", ".github", ".claude",
    "_layouts", "assets", "scripts", "mcp", "node_modules", "deck-assets",
}

_CACHE = {}   # folder -> (mtime, index.json data)
_GRAPH = {}   # "g" -> (mtime, {data, adj})
_STATE = {}   # "s" -> (mtime, state dict)


# ──────────────────────────────────────────────────────────────
# Deck keşfi / kimlik
# ──────────────────────────────────────────────────────────────

def discover_decks():
    out = []
    for e in sorted(os.scandir(REPO_ROOT), key=lambda e: e.name):
        if not e.is_dir() or e.name in SKIP or e.name.startswith("."):
            continue
        if os.path.isfile(os.path.join(e.path, "index.json")):
            out.append(e.name)
    return out


def deck_id(folder):
    return re.sub(r"-deck$", "", folder) or folder


def _norm(s):
    return re.sub(r"[_-]+", "-", (s or "").strip().lower())


def folder_map():
    """deck-id ve klasör adı → klasör (tire/alt-çizgi toleranslı)."""
    m = {}
    for f in discover_decks():
        m[_norm(f)] = f
        m[_norm(deck_id(f))] = f
    return m


def resolve_deck(x):
    if not x:
        return None
    m = folder_map()
    n = _norm(x)
    return m.get(n) or m.get(_norm(n + "-deck"))


# ──────────────────────────────────────────────────────────────
# index.json / graph.json / state — mtime önbellekli
# ──────────────────────────────────────────────────────────────

def load_index(folder):
    path = os.path.join(REPO_ROOT, folder, "index.json")
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return None
    c = _CACHE.get(folder)
    if c and c[0] == mt:
        return c[1]
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    _CACHE[folder] = (mt, data)
    return data


def load_graph():
    try:
        mt = os.path.getmtime(GRAPH_PATH)
    except OSError:
        return {"nodes": {}, "related": {}, "adj": {}}
    c = _GRAPH.get("g")
    if c and c[0] == mt:
        return c[1]
    try:
        data = json.load(open(GRAPH_PATH, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"nodes": {}, "related": {}, "adj": {}}
    adj = {}
    for k, lst in data.get("related", {}).items():
        adj[k] = [f"{n['deck']}/{n['slug']}" for n in lst]
    data["adj"] = adj
    _GRAPH["g"] = (mt, data)
    return data


def load_state():
    """{'decks': {deck_id: bool}}. Dosya yoksa boş (hepsi açık varsayılan)."""
    try:
        mt = os.path.getmtime(STATE_PATH)
    except OSError:
        return {"decks": {}}
    c = _STATE.get("s")
    if c and c[0] == mt:
        return c[1]
    try:
        data = json.load(open(STATE_PATH, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {"decks": {}}
    data.setdefault("decks", {})
    _STATE["s"] = (mt, data)
    return data


def save_state(state):
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)
    _STATE.pop("s", None)


def is_enabled(did):
    """Bir deck açık mı? state'te açıkça False değilse AÇIK (varsayılan)."""
    return load_state()["decks"].get(did, True)


def enabled_folders():
    return [f for f in discover_decks() if is_enabled(deck_id(f))]


def set_enabled(did, on):
    st = json.loads(json.dumps(load_state()))  # kopya
    st["decks"][did] = bool(on)
    save_state(st)


# ──────────────────────────────────────────────────────────────
# Arama skorlama (deck_mcp.py ile aynı)
# ──────────────────────────────────────────────────────────────

def _tokens(t):
    return [x for x in re.split(r"\W+", t.casefold()) if x]


def _score(a, qt, qp):
    title = (a.get("title") or "").casefold()
    summary = (a.get("summary") or "").casefold()
    tags = " ".join([a.get("category", ""), a.get("topic", ""),
                     " ".join(a.get("sections", []))]).casefold()
    content = (a.get("content") or "").casefold()
    s = 0
    if qp and qp in title:   s += 25
    if qp and qp in summary: s += 12
    if qp and qp in tags:    s += 8
    if qp and qp in content: s += 4
    for t in qt:
        if t in title:   s += 5
        if t in summary: s += 3
        if t in tags:    s += 2
        if t in content: s += 1
    return s


# ──────────────────────────────────────────────────────────────
# Çekirdek mantık (hem MCP tool'ları hem web UI kullanır)
# ──────────────────────────────────────────────────────────────

def core_list_decks():
    out = []
    for f in discover_decks():
        idx = load_index(f)
        if not idx:
            continue
        did = deck_id(f)
        out.append({
            "deck": did,
            "title": idx.get("title", f),
            "summary": idx.get("summary", ""),
            "count": idx.get("count", len(idx.get("articles", []))),
            "enabled": is_enabled(did),
        })
    return out


def core_search(query, deck=None, limit=5):
    qt, qp = _tokens(query), query.casefold().strip()
    if deck:
        f = resolve_deck(deck)
        if not f:
            return {"error": f"deck bulunamadı: '{deck}'. list_decks()."}
        folders = [f]
    else:
        folders = enabled_folders()
        if not folders:
            return {"error": "Hiç AÇIK deck yok. Kontrol panelinden (localhost:8765) "
                             "deck aç veya search'e 'deck' ver."}
    scored = []
    for f in folders:
        idx = load_index(f)
        if not idx:
            continue
        did = deck_id(f)
        for a in idx["articles"]:
            sc = _score(a, qt, qp)
            if sc > 0:
                scored.append((sc, did, a))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{
        "deck": did, "slug": a["slug"], "title": a["title"],
        "summary": a.get("summary", ""), "category": a.get("category", ""),
        "url": a["url"], "score": sc,
    } for sc, did, a in scored[: max(1, int(limit))]]


def core_get_article(deck, slug):
    f = resolve_deck(deck)
    if not f:
        return {"error": f"deck bulunamadı: '{deck}'.", "deck": deck, "slug": slug}
    idx = load_index(f)
    if not idx:
        return {"error": f"'{f}' index.json yok.", "deck": deck, "slug": slug}
    for a in idx["articles"]:
        if a["slug"] == slug:
            return {"deck": deck_id(f), "slug": a["slug"], "title": a["title"],
                    "category": a.get("category", ""), "topic": a.get("topic", ""),
                    "summary": a.get("summary", ""), "url": a["url"],
                    "sections": a.get("sections", []), "content": a.get("content", "")}
    return {"error": f"slug bulunamadı: '{slug}'.", "deck": deck, "slug": slug}


def _node_enabled(key):
    return is_enabled(key.split("/", 1)[0])


def core_related(deck, slug, limit=6):
    f = resolve_deck(deck)
    if not f:
        return {"error": f"deck bulunamadı: '{deck}'."}
    key = f"{deck_id(f)}/{slug}"
    g = load_graph()
    lst = g.get("related", {}).get(key)
    if lst is None:
        return {"error": f"graf düğümü yok: '{key}'. graph.json güncel mi? (build.py)"}
    out = [n for n in lst if is_enabled(n["deck"])]
    return out[: max(1, int(limit))]


def core_graph_around(deck, slug, depth=1, limit=15):
    f = resolve_deck(deck)
    if not f:
        return {"error": f"deck bulunamadı: '{deck}'."}
    start = f"{deck_id(f)}/{slug}"
    g = load_graph()
    adj, nodes = g.get("adj", {}), g.get("nodes", {})
    if start not in nodes:
        return {"error": f"graf düğümü yok: '{start}'."}
    seen = {start: 0}
    frontier = [start]
    for d in range(1, int(depth) + 1):
        nxt = []
        for k in frontier:
            for nb in adj.get(k, []):
                if nb not in seen and _node_enabled(nb):
                    seen[nb] = d
                    nxt.append(nb)
        frontier = nxt
    out = []
    for k, dist in sorted(seen.items(), key=lambda x: x[1]):
        if k == start:
            continue
        meta = nodes.get(k, {})
        out.append({"deck": meta.get("deck"), "slug": meta.get("slug"),
                    "title": meta.get("title"), "distance": dist})
        if len(out) >= limit:
            break
    return out


def core_path(a_deck, a_slug, b_deck, b_slug, max_hops=6):
    fa, fb = resolve_deck(a_deck), resolve_deck(b_deck)
    if not fa or not fb:
        return {"error": "deck bulunamadı."}
    start = f"{deck_id(fa)}/{a_slug}"
    goal = f"{deck_id(fb)}/{b_slug}"
    g = load_graph()
    adj, nodes = g.get("adj", {}), g.get("nodes", {})
    if start not in nodes or goal not in nodes:
        return {"error": "başlangıç/hedef graf düğümü yok."}
    # BFS (açık düğümler üzerinden)
    prev = {start: None}
    q = [start]
    while q:
        cur = q.pop(0)
        if cur == goal:
            break
        for nb in adj.get(cur, []):
            if nb not in prev and _node_enabled(nb):
                prev[nb] = cur
                q.append(nb)
    if goal not in prev:
        return {"error": "bağlantı yolu bulunamadı (açık deck'ler içinde)."}
    chain, cur = [], goal
    while cur is not None:
        chain.append(cur)
        cur = prev[cur]
    chain.reverse()
    if len(chain) - 1 > max_hops:
        return {"error": f"yol {max_hops} adımdan uzun ({len(chain)-1})."}
    return [{"deck": nodes[k]["deck"], "slug": nodes[k]["slug"],
             "title": nodes[k]["title"]} for k in chain]


# ──────────────────────────────────────────────────────────────
# MCP tool'ları (ince sarmalayıcılar)
# ──────────────────────────────────────────────────────────────

mcp = FastMCP(name="x3beche-decks")


@mcp.tool
def list_decks() -> list:
    """Tüm deck'leri (konu setlerini) + AÇIK/KAPALI durumlarını + rehber sayısını
    listeler. search yalnızca AÇIK deck'lerde arar. Deck'ler kullanıcı tarafından
    kontrol panelinden (http://127.0.0.1:8765) açılıp kapatılır.

    Döner: {deck, title, summary, count, enabled} listesi.
    """
    return core_list_decks()


@mcp.tool
def search(query: str, deck: str = None, limit: int = 5) -> list:
    """AÇIK deck'lerdeki Türkçe teknik rehberlerde arama (tam metin DÖNMEZ; onun
    için get_article). `deck` verilirse (örn. "stm32l4", "rust") sadece o deck'te
    ve açık/kapalı durumuna bakmadan arar; boşsa yalnızca AÇIK deck'lerde.

    Döner: {deck, slug, title, summary, category, url, score} listesi.
    """
    return core_search(query, deck, limit)


@mcp.tool
def get_article(deck: str, slug: str) -> dict:
    """Bir makalenin TAM metnini döndürür (search sonucundaki {deck, slug} ile).
    Döner: {deck, slug, title, category, topic, summary, url, sections, content}.
    """
    return core_get_article(deck, slug)


@mcp.tool
def related(deck: str, slug: str, limit: int = 6) -> list:
    """Bir rehbere içerik olarak en YAKIN rehberleri (ilişki grafından) döndürür —
    deck'ler arası, sadece AÇIK deck'lerden. "buna bağlı başka ne var?" için.

    Döner: {deck, slug, title, weight, shared[], link} listesi (yakınlığa göre).
    """
    return core_related(deck, slug, limit)


@mcp.tool
def graph_around(deck: str, slug: str, depth: int = 1, limit: int = 15) -> list:
    """Bir konunun etrafındaki KOMŞULUĞU (konu haritası) döndürür — `depth` adım
    uzağa kadar, AÇIK deck'lerden. Döner: {deck, slug, title, distance} listesi.
    """
    return core_graph_around(deck, slug, depth, limit)


@mcp.tool
def path(a_deck: str, a_slug: str, b_deck: str, b_slug: str, max_hops: int = 6) -> list:
    """İki konu arasındaki en kısa BAĞLANTI YOLUNU (ilişki grafında) döndürür —
    "X ile Y nasıl bağlanıyor?". Döner: yol üzerindeki {deck, slug, title} zinciri.
    """
    return core_path(a_deck, a_slug, b_deck, b_slug, max_hops)


# ──────────────────────────────────────────────────────────────
# Otomatik sync + rebuild (git pull → build.py --if-stale)
# ──────────────────────────────────────────────────────────────

_SYNC_ON = os.environ.get("X3BECHE_SYNC", "1") != "0"
_SYNC_SEC = max(10, int(os.environ.get("X3BECHE_SYNC_SEC", "60")))
_stop = threading.Event()


def sync_once():
    """Bir kez: git pull (senin repo/site) + gerekiyorsa index & graf rebuild."""
    try:
        subprocess.run(["git", "-C", REPO_ROOT, "pull", "--ff-only", "--quiet"],
                       capture_output=True, text=True, timeout=45)
    except Exception as e:
        print(f"[proxy] git pull atlandı: {e}", file=sys.stderr)
    try:
        subprocess.run([sys.executable, os.path.join(REPO_ROOT, "scripts", "build.py"),
                        "--if-stale"], capture_output=True, text=True, timeout=120)
    except Exception as e:
        print(f"[proxy] rebuild atlandı: {e}", file=sys.stderr)


def _sync_loop():
    while not _stop.is_set():
        sync_once()
        _stop.wait(_SYNC_SEC)


def start_sync():
    if not _SYNC_ON:
        return
    threading.Thread(target=_sync_loop, name="x3beche-sync", daemon=True).start()


# ──────────────────────────────────────────────────────────────
# Yerel kontrol paneli (web UI) — deck aç/kapa
# ──────────────────────────────────────────────────────────────

_UI_ON = os.environ.get("X3BECHE_UI", "1") != "0"
_UI_PORT = int(os.environ.get("X3BECHE_UI_PORT", "8765"))

_PAGE = """<!doctype html><html lang=tr><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>x3beche decks — kontrol</title>
<style>
:root{color-scheme:light dark;--bg:#0f1115;--fg:#e6e6e6;--mut:#8a93a0;--card:#181b22;--acc:#4f9cf9;--on:#2ecc71;--bd:#262b34}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
.wrap{max-width:860px;margin:0 auto;padding:28px 18px}h1{font-size:20px;margin:0 0 2px}
.sub{color:var(--mut);font-size:13px;margin-bottom:18px}
.bar{display:flex;gap:8px;margin:14px 0}.bar input{flex:1;padding:9px 12px;border:1px solid var(--bd);border-radius:8px;background:var(--card);color:var(--fg)}
.bar button{padding:9px 14px;border:0;border-radius:8px;background:var(--acc);color:#fff;cursor:pointer}
.tools{color:var(--mut);font-size:12px;margin:0 0 16px}
.deck{display:flex;align-items:center;gap:12px;padding:11px 13px;border:1px solid var(--bd);border-radius:10px;background:var(--card);margin-bottom:8px}
.deck .meta{flex:1;min-width:0}.deck .t{font-weight:600}.deck .d{color:var(--mut);font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cnt{color:var(--mut);font-size:12px;font-variant-numeric:tabular-nums}
.sw{position:relative;width:44px;height:24px;flex:none;cursor:pointer}
.sw input{display:none}.sw span{position:absolute;inset:0;background:#3a3f4a;border-radius:99px;transition:.15s}
.sw span:before{content:"";position:absolute;width:18px;height:18px;left:3px;top:3px;background:#fff;border-radius:99px;transition:.15s}
.sw input:checked+span{background:var(--on)}.sw input:checked+span:before{transform:translateX(20px)}
#res{margin-top:14px}.hit{padding:9px 12px;border:1px solid var(--bd);border-radius:8px;margin-bottom:7px;background:var(--card)}
.hit .h{font-weight:600}.hit .m{color:var(--mut);font-size:12.5px}.badge{font-size:11px;color:var(--acc)}
.count{color:var(--mut);font-size:12px;margin:6px 2px}
</style></head><body><div class=wrap>
<h1>x3beche decks — kontrol paneli</h1>
<div class=sub>Hangi veri (deck) kullanılsın? Kapalı deck'ler aramaya girmez. Değişiklik anında geçerli.</div>
<div class=bar><input id=q placeholder="Ara (açık deck'lerde)…" autocomplete=off><button onclick=go()>Ara</button></div>
<div class=tools>MCP tool'ları: <b>search · get_article · list_decks · related · graph_around · path</b></div>
<div id=res></div><div id=decks></div>
<script>
async function load(){let s=await (await fetch('/api/state')).json();
 let el=document.getElementById('decks');el.innerHTML='<div class=count>'+s.decks.length+' deck · '+s.decks.filter(d=>d.enabled).length+' açık</div>';
 for(const d of s.decks){let row=document.createElement('div');row.className='deck';
  row.innerHTML=`<label class=sw><input type=checkbox ${d.enabled?'checked':''} onchange="tog('${d.deck}',this.checked)"><span></span></label>
   <div class=meta><div class=t>${d.deck} <span class=cnt>· ${d.count}</span></div><div class=d>${esc(d.title)}</div></div>`;
  el.appendChild(row);}}
async function tog(deck,on){await fetch('/api/toggle?deck='+encodeURIComponent(deck)+'&on='+(on?1:0),{method:'POST'});load();}
async function go(){let q=document.getElementById('q').value.trim();if(!q)return;
 let r=await (await fetch('/api/search?limit=8&q='+encodeURIComponent(q))).json();let el=document.getElementById('res');
 if(r.error){el.innerHTML='<div class=hit>'+esc(r.error)+'</div>';return;}
 el.innerHTML=r.length?'':'<div class=hit>sonuç yok</div>';
 for(const h of r){let d=document.createElement('div');d.className='hit';
  d.innerHTML=`<div class=h>${esc(h.title)} <span class=badge>${h.deck}</span></div><div class=m>${esc(h.summary||'')}</div>`;el.appendChild(d);}}
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')go()});
load();
</script></div></body></html>"""


class Panel(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):  # sessiz
        pass

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/" or u.path == "/index.html":
            return self._send(200, _PAGE, "text/html")
        if u.path == "/api/state":
            return self._send(200, json.dumps({"decks": core_list_decks(),
                                               "sync": {"on": _SYNC_ON, "sec": _SYNC_SEC}},
                                              ensure_ascii=False))
        if u.path == "/api/search":
            r = core_search(q.get("q", [""])[0], None, int(q.get("limit", ["8"])[0]))
            return self._send(200, json.dumps(r, ensure_ascii=False))
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/toggle":
            deck = q.get("deck", [""])[0]
            on = q.get("on", ["1"])[0] not in ("0", "false", "")
            if deck:
                set_enabled(deck, on)
                return self._send(200, json.dumps({"ok": True, "deck": deck, "enabled": on}))
        return self._send(404, json.dumps({"error": "not found"}))


def start_ui():
    if not _UI_ON:
        return
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", _UI_PORT), Panel)
    except OSError as e:
        print(f"[proxy] UI başlatılamadı ({_UI_PORT}): {e}", file=sys.stderr)
        return
    threading.Thread(target=srv.serve_forever, name="x3beche-ui", daemon=True).start()
    print(f"[proxy] kontrol paneli: http://127.0.0.1:{_UI_PORT}", file=sys.stderr)


# ──────────────────────────────────────────────────────────────

_HTTP = os.environ.get("X3BECHE_HTTP", "0") != "0"
_HTTP_PORT = int(os.environ.get("X3BECHE_HTTP_PORT", "8000"))


if __name__ == "__main__":
    n = len(discover_decks())
    transport = f"http 127.0.0.1:{_HTTP_PORT}/mcp" if _HTTP else "stdio"
    print(f"[x3beche-decks] {n} deck | 6 tool "
          f"(list_decks/search/get_article/related/graph_around/path) | "
          f"MCP {transport} | "
          f"sync {'AÇIK '+str(_SYNC_SEC)+'s' if _SYNC_ON else 'KAPALI'} | "
          f"UI {'127.0.0.1:'+str(_UI_PORT) if _UI_ON else 'KAPALI'}", file=sys.stderr)
    start_sync()
    start_ui()
    if _HTTP:
        # Her zaman açık YEREL SERVİS: Kilo/LM Studio URL ile bağlanır
        mcp.run(transport="http", host="127.0.0.1", port=_HTTP_PORT)
    else:
        # Kilo/LM Studio süreci başlatır (stdio)
        mcp.run()
