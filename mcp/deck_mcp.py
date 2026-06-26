"""
deck_mcp.py — generic FastMCP alt-sunucu fabrikası

`build_deck_server(deck)` bir deck'in `<deck>/index.json` dosyasını okuyan ve
üç yapısal tool sunan bir FastMCP alt-sunucusu döndürür:

    search(query, limit)   → skorlu arama
    get_article(slug)      → tek makalenin tam metni
    list()                 → tüm makaleler (slug + başlık + özet)

Tasarım: deck'e ÖZEL kod yok. Aynı fabrika her deck için çağrılır.
Tool adları (`search`, `get_article`, `list`) sade tutulur; parent sunucu
bunları deck adıyla önekler (örn. `rust_search`, `embedded_get_article`).

index.json mtime'a göre önbelleğe alınır; jeneratör dosyayı yeniden üretince
tool'lar otomatik taze veriyi okur (yeniden başlatmaya gerek yok).
"""

import os
import re
import json

from fastmcp import FastMCP

# Repo kökü: mcp/ bir üst dizin. Ortam değişkeniyle override edilebilir.
REPO_ROOT = os.environ.get(
    "X3BECHE_REPO_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)

_CACHE = {}  # deck -> (mtime, data)


# ──────────────────────────────────────────────────────────────
# index.json yükleme (mtime önbellekli)
# ──────────────────────────────────────────────────────────────

def _index_path(deck):
    return os.path.join(REPO_ROOT, deck, "index.json")


def load_index(deck):
    """Deck'in index.json'unu taze okur; değişmemişse önbellekten döner.
    Dosya yoksa None döner (jeneratör henüz çalışmamış olabilir)."""
    path = _index_path(deck)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    cached = _CACHE.get(deck)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    _CACHE[deck] = (mtime, data)
    return data


# ──────────────────────────────────────────────────────────────
# Arama skorlama
# ──────────────────────────────────────────────────────────────

def _tokens(text):
    return [t for t in re.split(r'\W+', text.casefold()) if t]


def _score_article(article, q_tokens, q_phrase):
    """Başlık/özet eşleşmesine yüksek, içeriğe düşük ağırlık veren basit skor."""
    title = (article.get("title") or "").casefold()
    summary = (article.get("summary") or "").casefold()
    tags = " ".join([
        article.get("category", ""), article.get("topic", ""),
        " ".join(article.get("sections", [])),
    ]).casefold()
    content = (article.get("content") or "").casefold()

    score = 0
    # Tam ifade eşleşmesi — güçlü sinyal
    if q_phrase and q_phrase in title:
        score += 25
    if q_phrase and q_phrase in summary:
        score += 12
    if q_phrase and q_phrase in tags:
        score += 8
    if q_phrase and q_phrase in content:
        score += 4

    # Token bazlı
    for tok in q_tokens:
        if tok in title:
            score += 5
        if tok in summary:
            score += 3
        if tok in tags:
            score += 2
        if tok in content:
            score += 1
    return score


# ──────────────────────────────────────────────────────────────
# Fabrika
# ──────────────────────────────────────────────────────────────

def build_deck_server(deck):
    """Bir deck için search/get_article/list tool'larını sunan FastMCP döndürür."""
    mcp = FastMCP(name=f"{deck}-docs")

    @mcp.tool
    def search(query: str, limit: int = 5) -> list:
        """Bu deck'teki Türkçe teknik rehberlerde arama yapar. Başlık, özet,
        kategori, bölüm başlıkları ve tam metin üzerinde skorlu eşleştirme uygular;
        en alakalı `limit` sonucu döndürür.

        Argümanlar:
            query: Aranacak terim/ifade (Türkçe veya İngilizce anahtar kelimeler).
            limit: Döndürülecek maksimum sonuç sayısı (varsayılan 5).

        Döner: {slug, title, summary, category, url, score} listesi (skora göre sıralı).
        """
        idx = load_index(deck)
        if not idx:
            return []
        q_tokens = _tokens(query)
        q_phrase = query.casefold().strip()
        scored = []
        for a in idx["articles"]:
            s = _score_article(a, q_tokens, q_phrase)
            if s > 0:
                scored.append((s, a))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for s, a in scored[: max(1, int(limit))]:
            out.append({
                "slug": a["slug"],
                "title": a["title"],
                "summary": a.get("summary", ""),
                "category": a.get("category", ""),
                "url": a["url"],
                "score": s,
            })
        return out

    @mcp.tool
    def get_article(slug: str) -> dict:
        """Verilen slug'a sahip makalenin TAM metnini döndürür. Önce `search`
        ile slug bul, sonra bu tool ile tüm içeriği al.

        Argümanlar:
            slug: Makale kimliği (örn. "transformer" veya "bash-tools/curl").

        Döner: {slug, title, category, topic, summary, url, sections, content}
        Bulunamazsa: {error, slug}.
        """
        idx = load_index(deck)
        if not idx:
            return {"error": f"'{deck}' index.json bulunamadı — jeneratörü çalıştır.",
                    "slug": slug}
        for a in idx["articles"]:
            if a["slug"] == slug:
                return {
                    "slug": a["slug"],
                    "title": a["title"],
                    "category": a.get("category", ""),
                    "topic": a.get("topic", ""),
                    "summary": a.get("summary", ""),
                    "url": a["url"],
                    "sections": a.get("sections", []),
                    "content": a.get("content", ""),
                }
        return {"error": f"slug bulunamadı: {slug}", "slug": slug}

    @mcp.tool(name="list")
    def list_articles() -> list:
        """Bu deck'teki tüm rehberleri listeler (içeriğe inmeden gezinmek için).

        Döner: {slug, title, summary} listesi.
        """
        idx = load_index(deck)
        if not idx:
            return []
        return [
            {"slug": a["slug"], "title": a["title"], "summary": a.get("summary", "")}
            for a in idx["articles"]
        ]

    return mcp
