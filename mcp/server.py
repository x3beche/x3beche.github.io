#!/usr/bin/env python3
"""
server.py — x3beche-decks parent MCP sunucusu

Repo kökündeki her deck'i (içinde üretilmiş `index.json` olan dizin) keşfeder ve
her birini kendi prefix'iyle parent sunucuya mount eder. AI istemcisi şu tool'ları
görür:

    embedded_search, embedded_get_article, embedded_list
    ai_search,       ai_get_article,       ai_list
    project_search,  ...
    rust_search,     ...   (rust-deck eklenince OTOMATİK)

"Deck başına bir MCP" ilkesi: tek kod tabanı, deck başına sıfır ek kod. Yeni bir
deck için sadece içeriği ekle + `scripts/gen-deck-index.py` çalıştır.

Çalıştırma:
    python mcp/server.py                 # stdio (yerel istemciler)
    fastmcp run mcp/server.py:main       # fastmcp CLI ile
    fastmcp dev mcp/server.py:main       # MCP Inspector ile tool'ları doğrula

HTTP olarak yayınlamak için aşağıdaki `main.run(...)` satırına bak.
"""

import os
import re
import sys
import inspect

from fastmcp import FastMCP

from deck_mcp import build_deck_server, REPO_ROOT


# ──────────────────────────────────────────────────────────────
# Deck keşfi — index.json olan dizinler "hazır" deck'lerdir
# ──────────────────────────────────────────────────────────────

SKIP = {
    "_site", ".jekyll-cache", ".git", ".github", ".claude",
    "_layouts", "assets", "scripts", "mcp", "node_modules",
}


def discover_decks():
    decks = []
    for entry in sorted(os.scandir(REPO_ROOT), key=lambda e: e.name):
        if not entry.is_dir() or entry.name in SKIP or entry.name.startswith("."):
            continue
        if os.path.isfile(os.path.join(entry.path, "index.json")):
            decks.append(entry.name)
    return decks


def short_name(deck):
    """embedded-deck → embedded ; cli-tools-deck → cli_tools (MCP prefix'i).
    Tire → alt çizgi: MCP tool adları için güvenli (cli_tools_search)."""
    base = re.sub(r'-deck$', '', deck) or deck
    return base.replace('-', '_')


# ──────────────────────────────────────────────────────────────
# Sürümden-bağımsız mount (FastMCP 2.x `prefix=` / 3.x `namespace=`)
# ──────────────────────────────────────────────────────────────

def mount_deck(parent, child, ns):
    """FastMCP sürümleri mount imzasında farklılık gösterir
    (2.x: prefix=, 3.x: namespace=, eski: pozisyonel). Hepsini dener."""
    # Önce imzaya bakarak doğru anahtarı seç (yan etkisiz).
    # 3.x'te `namespace` tercih edilir (`prefix` deprecated); 2.x'te yalnızca
    # `prefix` vardır — bu yüzden önce namespace'i dene.
    try:
        params = inspect.signature(parent.mount).parameters
        if "namespace" in params:
            return parent.mount(child, namespace=ns)
        if "prefix" in params:
            return parent.mount(child, prefix=ns)
    except (ValueError, TypeError):
        pass
    # İmza okunamadıysa sırayla dene.
    for attempt in (
        lambda: parent.mount(child, namespace=ns),
        lambda: parent.mount(child, prefix=ns),
        lambda: parent.mount(ns, child),   # çok eski API: mount(prefix, server)
        lambda: parent.mount(child),       # son çare: prefix'siz
    ):
        try:
            return attempt()
        except TypeError:
            continue
    raise RuntimeError("FastMCP.mount() imzası tanınamadı")


# ──────────────────────────────────────────────────────────────
# Parent sunucu
# ──────────────────────────────────────────────────────────────

main = FastMCP(name="x3beche-decks")

_decks = discover_decks()
for _deck in _decks:
    mount_deck(main, build_deck_server(_deck), short_name(_deck))

# Keşif bilgisini stderr'e yaz (stdout MCP protokolüne ait — kirletme).
print(
    f"[x3beche-decks] {len(_decks)} deck mount edildi: "
    + ", ".join(short_name(d) for d in _decks)
    if _decks else
    "[x3beche-decks] UYARI: index.json'lı deck yok. Önce: python scripts/gen-deck-index.py",
    file=sys.stderr,
)


if __name__ == "__main__":
    # Yerel istemciler için stdio (varsayılan).
    main.run()
    # HTTP olarak yayınlamak için yukarıyı kapatıp şunu kullan:
    #   main.run(transport="http", host="127.0.0.1", port=8000)
