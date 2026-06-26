#!/usr/bin/env python3
"""
gen-deck-index.py — x3beche.github.io generic deck index üreticisi

Her deck'i (embedded-deck, ai-deck, project-deck, rust-deck ve gelecekte
eklenecekler) AI'ın tüketebileceği makine-okunabilir bir veri kaynağına çevirir.

Üretilen dosyalar (hepsi TÜRETİLMİŞ — elle düzenlenmez):
    <deck>/index.json      → yapısal makale dizini (MCP sunucusu bunu okur)
    <deck>/llms.txt        → llms.txt standardı: başlık + makale linki/özet listesi
    <deck>/llms-full.txt   → tüm makalelerin tam metni tek dosyada
    /llms.txt              → kök index: tüm deck'leri ve deck-başına llms.txt'i linkler

Tasarım ilkesi: HER ŞEY GENERIC. Hiçbir parça tek bir deck'e özel değil.
Yeni deck klasörü eklenince (içinde `layout: tutorial` HTML'ler varsa)
ek kod yazmadan otomatik keşfedilir.

Kullanım:
    python scripts/gen-deck-index.py            # tüm deck'leri yeniden üret
    python scripts/gen-deck-index.py --check    # üret ama yazma; değişiklik varsa exit 1

Bağımlılık: yalnızca Python stdlib (idempotent, CLAUDE.md "Round N" akışına uyumlu).
"""

import os
import re
import sys
import json
from html.parser import HTMLParser

# ──────────────────────────────────────────────────────────────
# Konfig
# ──────────────────────────────────────────────────────────────

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Boş bırakılırsa otomatik keşfedilir (içinde tutorial-layout HTML olan kök
# dizinler). Sabit bir liste vermek istersen buraya yaz: ["embedded-deck", ...]
DECKS_OVERRIDE = []

# Deck adayı olmayan kök dizinler
SKIP_DIRS = {
    "_site", ".jekyll-cache", ".git", ".github", ".claude",
    "_layouts", "assets", "scripts", "mcp", "node_modules",
}

# Makaleyi (tutorial) katalogdan (page) ayıran front-matter layout değerleri
ARTICLE_LAYOUT = "tutorial"
CATALOG_LAYOUT = "page"


# ──────────────────────────────────────────────────────────────
# Site URL'i (_config.yml'den)
# ──────────────────────────────────────────────────────────────

def read_site_url():
    """_config.yml'den url + baseurl okur. Bulamazsa makul varsayılan döner."""
    url, baseurl = "https://x3beche.github.io", ""
    cfg = os.path.join(REPO_ROOT, "_config.yml")
    try:
        with open(cfg, encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r'\s*url:\s*["\']?([^"\'\s#]+)', line)
                if m:
                    url = m.group(1).rstrip("/")
                m = re.match(r'\s*baseurl:\s*["\']?([^"\'#]*)', line)
                if m:
                    baseurl = m.group(1).strip().strip('"\'').rstrip("/")
    except OSError:
        pass
    return url + baseurl


SITE_URL = read_site_url()


# ──────────────────────────────────────────────────────────────
# HTML → düz metin sıyırıcı
# ──────────────────────────────────────────────────────────────

class TextExtractor(HTMLParser):
    """<main> içeriğinin düz metnini toplar.

    Atlananlar: <script>, <style>, <nav class="toc"> (içindekiler — duplicate).
    convert_charrefs=True (varsayılan) HTML entity'lerini otomatik çözer.
    <main> yoksa tüm gövde metni toplanır.
    """

    SKIP_TAGS = {"script", "style"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._in_toc = False
        self._toc_depth = 0
        self._in_main = False
        self._main_depth = 0
        self._saw_main = False
        self.parts = []         # tüm gövde metni
        self.main_parts = []    # yalnızca <main> içi

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)

        if tag == "main":
            self._in_main = True
            self._saw_main = True
            self._main_depth = 1
            return
        if self._in_main and tag == "main":
            self._main_depth += 1

        if tag == "nav" and "toc" in attr.get("class", "").split():
            self._in_toc = True
            self._toc_depth = 1
            return
        if self._in_toc:
            self._toc_depth += 1
            return

        if tag in self.SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if self._in_toc:
            self._toc_depth -= 1
            if self._toc_depth <= 0:
                self._in_toc = False
            return
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if tag == "main" and self._in_main:
            self._main_depth -= 1
            if self._main_depth <= 0:
                self._in_main = False

    def handle_data(self, data):
        if self._skip_depth > 0 or self._in_toc:
            return
        text = data.strip()
        if not text:
            return
        self.parts.append(text)
        if self._in_main:
            self.main_parts.append(text)

    def get_text(self):
        # <main> varsa yalnızca onun prose'unu döndür (başlık/özet zaten ayrı
        # alanlarda); yoksa tüm gövdeye düş.
        chosen = self.main_parts if self._saw_main else self.parts
        return collapse_ws(" ".join(chosen))


def collapse_ws(text):
    return re.sub(r'\s+', ' ', text).strip()


# ──────────────────────────────────────────────────────────────
# Front-matter & Liquid temizleme
# ──────────────────────────────────────────────────────────────

def split_front_matter(content):
    """(front_matter_dict, body) döndürür."""
    fm = {}
    body = content
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            block = content[3:end]
            body = content[end + 4:]
            for line in block.splitlines():
                m = re.match(r'\s*([A-Za-z0-9_-]+)\s*:\s*(.*)$', line)
                if m:
                    key = m.group(1).strip()
                    val = m.group(2).strip().strip('"\'')
                    fm[key] = val
    return fm, body


def strip_liquid(text):
    """Liquid kabuğunu temizler ama {% raw %} bloklarının İÇERİĞİNİ korur
    (kod örnekleri aramada değerli). Yalnızca raw/endraw etiketlerini atar."""
    text = re.sub(r'\{%-?\s*(end)?raw\s*-?%\}', ' ', text)
    text = re.sub(r'\{%[^%]*%\}', ' ', text)
    text = re.sub(r'\{\{[^}]*\}\}', ' ', text)
    return text


# ──────────────────────────────────────────────────────────────
# Yapısal alan çıkarıcılar (raw HTML üzerinde)
# ──────────────────────────────────────────────────────────────

def tags_to_text(html):
    """Küçük bir HTML parçasındaki etiketleri atıp düz metin döndürür."""
    ex = TextExtractor()
    try:
        ex.feed(html)
    except Exception:
        pass
    return collapse_ws(" ".join(ex.parts))


def extract_meta_chips(html):
    """<div class="meta"> içindeki <span> metinlerini sırayla döndürür."""
    m = re.search(r'<div\s+class=["\'][^"\']*\bmeta\b[^"\']*["\'][^>]*>(.*?)</div>',
                  html, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    spans = re.findall(r'<span[^>]*>(.*?)</span>', m.group(1), re.DOTALL | re.IGNORECASE)
    chips = [collapse_ws(re.sub(r'<[^>]+>', '', s)) for s in spans]
    return [c for c in chips if c]


def extract_subtitle(html):
    m = re.search(r'<p\s+class=["\'][^"\']*\bsubtitle\b[^"\']*["\'][^>]*>(.*?)</p>',
                  html, re.DOTALL | re.IGNORECASE)
    return collapse_ws(re.sub(r'<[^>]+>', '', m.group(1))) if m else ""


def extract_section_titles(html):
    """<h2>...</h2> başlıklarından <span class="num">NN</span> numarasını
    sıyırıp temiz bölüm adlarını döndürür."""
    titles = []
    for m in re.finditer(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL | re.IGNORECASE):
        inner = re.sub(r'<span[^>]*class=["\'][^"\']*\bnum\b[^"\']*["\'][^>]*>.*?</span>',
                       ' ', m.group(1), flags=re.DOTALL | re.IGNORECASE)
        title = collapse_ws(re.sub(r'<[^>]+>', '', inner))
        if title:
            titles.append(title)
    return titles


def extract_h1(html):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    inner = re.sub(r'<br\s*/?>', ' — ', m.group(1), flags=re.IGNORECASE)
    return collapse_ws(re.sub(r'<[^>]+>', '', inner))


# ──────────────────────────────────────────────────────────────
# Deck keşfi
# ──────────────────────────────────────────────────────────────

def iter_html_files(deck_path):
    for root, dirs, files in os.walk(deck_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".html"):
                yield os.path.join(root, f)


def file_layout(path):
    """Bir HTML dosyasının front-matter `layout` değerini döndürür ('' olabilir)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            head = fh.read(2048)
    except OSError:
        return ""
    fm, _ = split_front_matter(head if head.startswith("---") else "")
    return fm.get("layout", "")


def discover_decks():
    if DECKS_OVERRIDE:
        return list(DECKS_OVERRIDE)
    decks = []
    for entry in sorted(os.scandir(REPO_ROOT), key=lambda e: e.name):
        if not entry.is_dir() or entry.name in SKIP_DIRS or entry.name.startswith("."):
            continue
        # İçinde en az bir tutorial-layout HTML varsa burası bir deck'tir.
        for html in iter_html_files(entry.path):
            if file_layout(html) == ARTICLE_LAYOUT:
                decks.append(entry.name)
                break
    return decks


def short_name(deck):
    """embedded-deck → embedded, ai-deck → ai (MCP prefix'i için)."""
    return re.sub(r'-deck$', '', deck) or deck


# ──────────────────────────────────────────────────────────────
# Makale çıkarımı
# ──────────────────────────────────────────────────────────────

def slug_for(deck_path, file_path):
    """yocto/index.html → 'yocto' ; bash-tools/curl.html → 'bash-tools/curl'."""
    rel = os.path.relpath(file_path, deck_path).replace(os.sep, "/")
    if rel.endswith("/index.html"):
        return rel[:-len("/index.html")]
    if rel == "index.html":
        return ""
    return rel[:-len(".html")] if rel.endswith(".html") else rel


def url_for(deck, file_path, deck_path):
    rel = os.path.relpath(file_path, deck_path).replace(os.sep, "/")
    if rel.endswith("index.html"):
        rel = rel[:-len("index.html")]  # temiz dizin URL'i
    return f"{SITE_URL}/{deck}/{rel}"


def parse_article(deck, deck_path, file_path):
    try:
        with open(file_path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError:
        return None

    fm, body = split_front_matter(content)
    body = strip_liquid(body)

    title = fm.get("title", "") or extract_h1(body)
    chips = extract_meta_chips(body)
    # chips: [tür, kategori, konu, yıl?]. Kategori = ikinci chip, konu = üçüncü.
    category = chips[1] if len(chips) > 1 else (chips[0] if chips else "")
    topic = chips[2] if len(chips) > 2 else ""
    summary = extract_subtitle(body)
    sections = extract_section_titles(body)

    ex = TextExtractor()
    try:
        ex.feed(body)
    except Exception:
        pass
    text = ex.get_text()

    return {
        "slug": slug_for(deck_path, file_path),
        "title": title,
        "category": category,
        "topic": topic,
        "summary": summary,
        "url": url_for(deck, file_path, deck_path),
        "sections": sections,
        "content": text,
    }


# ──────────────────────────────────────────────────────────────
# Deck meta (başlık/özet)
# ──────────────────────────────────────────────────────────────

def load_deck_meta(deck, deck_path):
    """Sıra: deck.yml > deck-kökü index.html hero > deck adı."""
    title, summary = deck, ""

    yml = os.path.join(deck_path, "deck.yml")
    if os.path.isfile(yml):
        try:
            with open(yml, encoding="utf-8") as fh:
                for line in fh:
                    m = re.match(r'\s*title:\s*(.+)$', line)
                    if m:
                        title = m.group(1).strip().strip('"\'')
                    m = re.match(r'\s*summary:\s*(.+)$', line)
                    if m:
                        summary = m.group(1).strip().strip('"\'')
        except OSError:
            pass
        return title, summary

    root_index = os.path.join(deck_path, "index.html")
    if os.path.isfile(root_index):
        try:
            with open(root_index, encoding="utf-8", errors="replace") as fh:
                html = strip_liquid(split_front_matter(fh.read())[1])
            h1 = extract_h1(html)
            if h1:
                title = h1
            sub = extract_subtitle(html)
            if sub:
                summary = sub
        except OSError:
            pass
    return title, summary


# ──────────────────────────────────────────────────────────────
# Deck işleme + çıktı üretimi
# ──────────────────────────────────────────────────────────────

def build_deck(deck):
    deck_path = os.path.join(REPO_ROOT, deck)
    title, summary = load_deck_meta(deck, deck_path)

    articles = []
    for fp in iter_html_files(deck_path):
        if file_layout(fp) != ARTICLE_LAYOUT:
            continue  # katalog (page) veya layout'suz dosyaları atla
        art = parse_article(deck, deck_path, fp)
        if art:
            articles.append(art)

    articles.sort(key=lambda a: a["slug"])

    index = {
        "deck": deck,
        "title": title,
        "summary": summary,
        "base_url": f"{SITE_URL}/{deck}",
        "count": len(articles),
        "articles": articles,
    }
    return index


def render_deck_llms(index):
    lines = [f"# {index['title']}", ""]
    if index["summary"]:
        lines += [f"> {index['summary']}", ""]
    lines += [f"Bu deck {index['count']} Türkçe teknik rehber içerir.", "",
              "## Rehberler", ""]
    for a in index["articles"]:
        desc = a["summary"] or a["title"]
        lines.append(f"- [{a['title']}]({a['url']}): {desc}")
    return "\n".join(lines) + "\n"


def render_deck_llms_full(index):
    out = [f"# {index['title']} — Tam Metin", ""]
    if index["summary"]:
        out += [f"> {index['summary']}", ""]
    for a in index["articles"]:
        out += [
            "=" * 70,
            f"## {a['title']}",
            f"URL: {a['url']}",
            f"Kategori: {a['category']} · Konu: {a['topic']}",
        ]
        if a["summary"]:
            out.append(f"Özet: {a['summary']}")
        if a["sections"]:
            out.append("Bölümler: " + " · ".join(a["sections"]))
        out += ["", a["content"], ""]
    return "\n".join(out) + "\n"


def render_root_llms(indices):
    lines = [
        "# x3beche.github.io — Teknik Eğitim Setleri",
        "",
        "> Emirhan Pehlevan (TÜBİTAK BİLGEM, Embedded Linux Research Scholar) "
        "tarafından hazırlanan Türkçe teknik eğitim platformu. Her \"deck\" bir "
        "alanı kapsayan rehber setidir.",
        "",
        "## Deck'ler",
        "",
    ]
    for idx in indices:
        lines.append(
            f"- [{idx['title']}]({SITE_URL}/{idx['deck']}/llms.txt) "
            f"({idx['count']} rehber): {idx['summary'] or idx['deck']}"
        )
    lines += [
        "",
        "## Makine-okunabilir kaynaklar",
        "",
        "Her deck için şu dosyalar üretilir:",
        "",
        "- `<deck>/llms.txt` — rehber listesi + özetler",
        "- `<deck>/llms-full.txt` — tüm rehberlerin tam metni",
        "- `<deck>/index.json` — yapısal makale dizini (MCP sunucusu bunu okur)",
    ]
    return "\n".join(lines) + "\n"


# ──────────────────────────────────────────────────────────────
# Yazma yardımcıları (idempotent / --check)
# ──────────────────────────────────────────────────────────────

def write_if_changed(path, data, check_only, changed):
    existing = None
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            existing = fh.read()
    if existing == data:
        return
    changed.append(os.path.relpath(path, REPO_ROOT).replace(os.sep, "/"))
    if not check_only:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(data)


def main():
    check_only = "--check" in sys.argv
    decks = discover_decks()
    if not decks:
        print("Hiç deck bulunamadı (içinde 'layout: tutorial' HTML olan kök dizin yok).")
        return 1

    print(f"Site URL : {SITE_URL}")
    print(f"Deck'ler : {', '.join(decks)}\n")

    changed = []
    indices = []
    for deck in decks:
        idx = build_deck(deck)
        indices.append(idx)
        deck_path = os.path.join(REPO_ROOT, deck)

        json_data = json.dumps(idx, ensure_ascii=False, indent=2) + "\n"
        write_if_changed(os.path.join(deck_path, "index.json"), json_data, check_only, changed)
        write_if_changed(os.path.join(deck_path, "llms.txt"),
                         render_deck_llms(idx), check_only, changed)
        write_if_changed(os.path.join(deck_path, "llms-full.txt"),
                         render_deck_llms_full(idx), check_only, changed)

        kb = len(json_data.encode("utf-8")) / 1024
        print(f"  {deck:<16} {idx['count']:>3} rehber | index.json {kb:>7.1f} KB")

    write_if_changed(os.path.join(REPO_ROOT, "llms.txt"),
                     render_root_llms(indices), check_only, changed)

    print()
    if check_only:
        if changed:
            print("GÜNCEL DEĞİL — yeniden üretilmesi gereken dosyalar:")
            for c in changed:
                print(f"  ~ {c}")
            return 1
        print("Tüm index dosyaları güncel.")
        return 0

    if changed:
        print(f"{len(changed)} dosya yazıldı/güncellendi.")
    else:
        print("Değişiklik yok — tüm dosyalar zaten güncel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
