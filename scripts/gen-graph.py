#!/usr/bin/env python3
"""
gen-graph.py — rehberler arası İLİŞKİ GRAFI üreticisi (offline, bağımlılıksız)

Rehberler elle neredeyse hiç linklenmemiş; bu yüzden grafı İÇERİKTEN türetir:

  1. TF-IDF içerik benzerliği (kosinüs)      → ana kenar ağırlığı
  2. Ortak kategori                          → küçük boost
  3. Mevcut gerçek HTML linkleri             → güçlü boost (varsa)

Çıktı: repo kökünde `graph.json` (TÜRETİLMİŞ — elle düzenlenmez):

  {
    "count": <düğüm sayısı>,
    "nodes":   { "<deck>/<slug>": {deck, slug, title, category, url} , ... },
    "related": { "<deck>/<slug>": [ {deck, slug, title, weight, shared[], link} , ... ] }
  }

Düğüm anahtarı = "<deck-id>/<slug>" (deck-id = klasör eksi '-deck'; ilk '/'de böl).
Yeni rehber/deck eklenince ek kod olmadan otomatik dahil olur.

Kullanım:
    python scripts/gen-graph.py            # graph.json üret (değişmişse yaz)
    python scripts/gen-graph.py --check    # üretme; güncel değilse exit 1
"""

import os
import re
import sys
import json
import math
import collections

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP = {
    "_site", ".jekyll-cache", ".git", ".github", ".claude",
    "_layouts", "assets", "scripts", "mcp", "node_modules", "deck-assets",
}

K = 8              # düğüm başına komşu sayısı
MIN_W = 0.045      # bir kenarı tutmak için minimum ağırlık
CAT_BOOST = 0.12   # ortak kategori boost'u (mevcut benzerlik kenarına)
LINK_BOOST = 0.6   # gerçek HTML linki boost'u
MAX_TOK = 3000     # doc başına token tavanı (uzun metinde gürültüyü sınırla)
MAX_DF_RATIO = 0.5 # bir term bu orandan çok doc'ta ise atla (near-stopword)

# Küçük Türkçe + genel durak kelime listesi (kaba; TF-IDF zaten çoğunu bastırır)
STOP = set((
    "ve veya ile bir bu şu için gibi olan olarak da de ki mi mı mu mü çok daha "
    "en her ya ama fakat ise the and for you with this that are can not your from "
    "olur olarak yani ayrıca ancak hem tüm bütün nasıl neden hangi kadar sonra önce "
    "var yok gerekir gerekli örnek örneğin adım aşağıdaki yukarıdaki burada şöyle böyle"
).split())


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


def key_of(did, slug):
    return f"{did}/{slug}"


def slug_to_relpath(slug):
    """slug 'af-packet' → 'af-packet/index.html' ; 'bash-tools/curl' → 'bash-tools/curl.html'."""
    return f"{slug}/index.html" if "/" not in slug else f"{slug}.html"


def tokens(text):
    out = []
    for t in re.split(r"\W+", (text or "").casefold()):
        if len(t) > 2 and t not in STOP and not t.isdigit():
            out.append(t)
    return out


# ──────────────────────────────────────────────────────────────
# Yükleme: index.json'lardan düğümler + gerçek HTML linkleri
# ──────────────────────────────────────────────────────────────

def load_nodes(folders):
    nodes = []          # {key, deck, slug, title, category, url, folder, toks(Counter)}
    path2key = {}       # repo-göreli tutorial path -> key (link çözümü için)
    for f in folders:
        try:
            idx = json.load(open(os.path.join(REPO_ROOT, f, "index.json"), encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        did = deck_id(f)
        for a in idx.get("articles", []):
            slug = a["slug"]
            key = key_of(did, slug)
            toks = tokens(" ".join([
                a.get("title", ""), a.get("title", ""),        # başlık 2× ağırlık
                a.get("summary", ""),
                " ".join(a.get("sections", [])),
                a.get("content", ""),
            ]))[:MAX_TOK]
            nodes.append({
                "key": key, "deck": did, "slug": slug,
                "title": a.get("title", ""), "category": a.get("category", ""),
                "url": a.get("url", ""), "folder": f,
                "tf": collections.Counter(toks),
            })
            rel = f"{f}/{slug_to_relpath(slug)}"
            path2key[os.path.normpath(rel)] = key
    return nodes, path2key


def extract_links(nodes, path2key):
    """Gerçek rehber↔rehber HTML linklerini (key_a, key_b) kümesi olarak döndür."""
    edges = set()
    href_re = re.compile(r'href="([^"]+)"')
    for n in nodes:
        fp = os.path.join(REPO_ROOT, n["folder"], slug_to_relpath(n["slug"]))
        try:
            body = open(fp, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        base = os.path.dirname(os.path.normpath(f"{n['folder']}/{slug_to_relpath(n['slug'])}"))
        for h in href_re.findall(body):
            h = h.split("#")[0].split("?")[0]
            if (not h or h.startswith(("http", "//", "mailto:", "#", "tel:"))
                    or "assets" in h or h in ("index.html", "../index.html", "../", "./")):
                continue
            tgt = os.path.normpath(os.path.join(base, h))
            if os.path.isdir(os.path.join(REPO_ROOT, tgt)):
                tgt = os.path.join(tgt, "index.html")
            tk = path2key.get(os.path.normpath(tgt))
            if tk and tk != n["key"]:
                edges.add((n["key"], tk))
    return edges


# ──────────────────────────────────────────────────────────────
# TF-IDF + kosinüs (ters indeks ile)
# ──────────────────────────────────────────────────────────────

def build_related(nodes, link_edges):
    N = len(nodes)
    df = collections.Counter()
    for n in nodes:
        for term in n["tf"]:
            df[term] += 1

    # tf-idf ağırlıklı, normalize vektörler
    vecs = []
    for n in nodes:
        v = {}
        for term, c in n["tf"].items():
            d = df[term]
            if d > N * MAX_DF_RATIO:      # near-stopword: atla
                continue
            idf = math.log((1 + N) / (1 + d)) + 1.0
            v[term] = (1 + math.log(c)) * idf
        norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
        vecs.append({t: w / norm for t, w in v.items()})

    # ters indeks
    inv = collections.defaultdict(list)   # term -> [(i, w)]
    for i, v in enumerate(vecs):
        for t, w in v.items():
            inv[t].append((i, w))

    # kosinüs birikimi (yalnız ortak term'i olan çiftler)
    sim = collections.defaultdict(lambda: collections.defaultdict(float))
    for t, postings in inv.items():
        if len(postings) < 2 or len(postings) > N * MAX_DF_RATIO:
            continue
        for a in range(len(postings)):
            ia, wa = postings[a]
            for b in range(a + 1, len(postings)):
                ib, wb = postings[b]
                sim[ia][ib] += wa * wb

    cat = [(_norm_cat(n["category"])) for n in nodes]
    linkset = set()
    for a, b in link_edges:
        linkset.add((a, b)); linkset.add((b, a))
    keys = [n["key"] for n in nodes]

    # ağırlıkları topla (simetrik) + boost'lar
    weight = collections.defaultdict(dict)   # i -> {j: w}
    def add(i, j, w):
        weight[i][j] = max(weight[i].get(j, 0.0), w)
    for i in sim:
        for j, s in sim[i].items():
            add(i, j, s); add(j, i, s)
    # kategori boost (sadece mevcut benzerlik kenarına)
    for i in list(weight):
        for j in list(weight[i]):
            if cat[i] and cat[i] == cat[j]:
                weight[i][j] += CAT_BOOST
    # gerçek link boost (kenar yoksa bile ekle)
    key2i = {k: i for i, k in enumerate(keys)}
    for (a, b) in linkset:
        i, j = key2i.get(a), key2i.get(b)
        if i is not None and j is not None:
            weight[i][j] = weight[i].get(j, 0.0) + LINK_BOOST

    related = {}
    for i, n in enumerate(nodes):
        nbrs = sorted(weight.get(i, {}).items(), key=lambda x: x[1], reverse=True)
        lst = []
        for j, w in nbrs:
            if w < MIN_W:
                break
            m = nodes[j]
            shared = _shared_terms(nodes[i]["tf"], nodes[j]["tf"], df, N)
            lst.append({
                "deck": m["deck"], "slug": m["slug"], "title": m["title"],
                "weight": round(w, 4), "shared": shared,
                "link": (keys[i], keys[j]) in linkset,
            })
            if len(lst) >= K:
                break
        related[n["key"]] = lst
    return related


def _norm_cat(c):
    return re.sub(r"\s+", " ", (c or "").strip().casefold())


def _shared_terms(tfa, tfb, df, N, top=5):
    common = set(tfa) & set(tfb)
    scored = []
    for t in common:
        d = df.get(t, N)
        if d > N * MAX_DF_RATIO:
            continue
        idf = math.log((1 + N) / (1 + d)) + 1.0
        scored.append((idf * min(tfa[t], tfb[t]), t))
    scored.sort(reverse=True)
    return [t for _, t in scored[:top]]


# ──────────────────────────────────────────────────────────────
# Ana
# ──────────────────────────────────────────────────────────────

def build():
    folders = discover_decks()
    nodes, path2key = load_nodes(folders)
    link_edges = extract_links(nodes, path2key)
    related = build_related(nodes, link_edges)
    node_meta = {
        n["key"]: {"deck": n["deck"], "slug": n["slug"], "title": n["title"],
                   "category": n["category"], "url": n["url"]}
        for n in nodes
    }
    return {
        "count": len(nodes),
        "explicit_links": len(link_edges),
        "nodes": node_meta,
        "related": related,
    }


def main():
    check = "--check" in sys.argv
    data = build()
    out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path = os.path.join(REPO_ROOT, "graph.json")
    old = open(path, encoding="utf-8").read() if os.path.isfile(path) else None
    if old == out:
        print(f"graph.json güncel ({data['count']} düğüm).")
        return 0
    if check:
        print("graph.json GÜNCEL DEĞİL — yeniden üret.")
        return 1
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    edges = sum(len(v) for v in data["related"].values())
    print(f"graph.json yazıldı: {data['count']} düğüm, {edges} yönlü kenar, "
          f"{data['explicit_links']} gerçek link.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
