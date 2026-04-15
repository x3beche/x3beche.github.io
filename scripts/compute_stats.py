#!/usr/bin/env python3
"""
compute_stats.py — x3beche.github.io analytics hesaplayıcı

Kullanım:
    python scripts/compute_stats.py

Çıktı:
    - Her deck için sayfa, konu, bölüm, kelime sayısı
    - Genel toplam
    - index.html'e yazılacak hazır değerler

Kelime sayımı yöntemi:
    - Jekyll front-matter çıkarılır (--- ... --- arası)
    - <script>, <style>, <nav class="toc">, <!-- --> atlanır
    - Liquid etiketleri temizlenir
    - Kalan metin düz yazı (prose) olarak sayılır
"""

import os
import re
import json
from html.parser import HTMLParser


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECKS = ["embedded-deck", "ai-deck", "project-deck"]

# Katalog sayfaları (kart gridi) — bölüm/kelime sayımından dışlanır
CATALOG_PAGES = {"index.html"}


# ──────────────────────────────────────────────
# HTML prose sıyırıcı
# ──────────────────────────────────────────────

class ProseExtractor(HTMLParser):
    """HTML etiketlerini atlayıp sadece metin içeriğini toplar.
    <script>, <style>, <nav class="toc">, <!-- --> bloklarını atlar.
    """

    SKIP_TAGS = {"script", "style"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0         # skip_tag içinde derinlik
        self._skip_tag_name = None   # hangi tag'i atlıyoruz
        self._in_toc_nav = False     # <nav class="toc"> içinde miyiz?
        self._toc_nav_depth = 0
        self.prose_parts = []        # toplanan metin parçaları

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)

        # <nav class="toc"> — içindekiler menüsü, içeriği duplicate, atla
        if tag == "nav":
            classes = attr_dict.get("class", "")
            if "toc" in classes.split():
                self._in_toc_nav = True
                self._toc_nav_depth = 1
                return

        if self._in_toc_nav:
            self._toc_nav_depth += 1
            return

        # <script> / <style> atlama
        if tag in self.SKIP_TAGS:
            if self._skip_depth == 0:
                self._skip_tag_name = tag
            self._skip_depth += 1
            return

        if self._skip_depth > 0:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if self._in_toc_nav:
            if tag == "nav":
                self._toc_nav_depth -= 1
                if self._toc_nav_depth <= 0:
                    self._in_toc_nav = False
            else:
                self._toc_nav_depth -= 1 if tag != "nav" else 0
            return

        if self._skip_depth > 0:
            self._skip_depth -= 1
            return

    def handle_data(self, data):
        if self._skip_depth > 0 or self._in_toc_nav:
            return
        text = data.strip()
        if text:
            self.prose_parts.append(text)

    def handle_comment(self, data):
        pass  # yorumları atla


def strip_front_matter(content: str) -> str:
    """Jekyll YAML front-matter'ını (--- ... ---) çıkarır."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:]
    return content


def strip_liquid(text: str) -> str:
    """Liquid etiketlerini ({% %}, {{ }}, raw/endraw) temizler."""
    # {%- raw -%} ... {%- endraw -%} bloklarını at (içerikleri ham HTML/text, prose değil)
    text = re.sub(r'\{%-?\s*raw\s*-?%\}.*?\{%-?\s*endraw\s*-?%\}', ' ', text, flags=re.DOTALL)
    # Kalan Liquid tag'leri
    text = re.sub(r'\{%[^%]*%\}', ' ', text)
    text = re.sub(r'\{\{[^}]*\}\}', ' ', text)
    return text


def count_prose_words(html_content: str) -> int:
    """Bir HTML dosyasındaki makale kelimelerini sayar."""
    content = strip_front_matter(html_content)
    content = strip_liquid(content)

    parser = ProseExtractor()
    try:
        parser.feed(content)
    except Exception:
        pass

    full_text = " ".join(parser.prose_parts)
    words = re.split(r'\s+', full_text)
    return len([w for w in words if w])


def count_sections(html_content: str) -> int:
    """<section id="sN"> kalıplarını sayar (N = rakam)."""
    return len(re.findall(r'<section\s[^>]*id=["\']s\d+["\']', html_content, re.IGNORECASE))


# ──────────────────────────────────────────────
# Deck tarama
# ──────────────────────────────────────────────

def scan_deck(deck_name: str) -> dict:
    deck_path = os.path.join(REPO_ROOT, deck_name)
    if not os.path.isdir(deck_path):
        return {"pages": 0, "topics": 0, "sections": 0, "words": 0}

    # Konu sayısı: HTML dosyası içeren doğrudan alt dizinler (assets/ gibi CSS dizinleri hariç)
    topics = sum(
        1 for entry in os.scandir(deck_path)
        if entry.is_dir() and any(
            f.endswith(".html")
            for f in os.listdir(entry.path)
            if os.path.isfile(os.path.join(entry.path, f))
        )
    )

    all_html = []
    for root, dirs, files in os.walk(deck_path):
        # _site çıktısını atla (varsa)
        dirs[:] = [d for d in dirs if d not in ("_site", ".jekyll-cache")]
        for f in files:
            if f.endswith(".html"):
                all_html.append(os.path.join(root, f))

    pages = len(all_html)
    total_sections = 0
    total_words = 0

    for fpath in all_html:
        # Deck kökündeki index.html = katalog → bölüm/kelime sayımından dışla
        rel = os.path.relpath(fpath, deck_path)
        is_catalog = (rel == "index.html")

        try:
            with open(fpath, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except Exception:
            continue

        if not is_catalog:
            total_sections += count_sections(content)
            total_words += count_prose_words(content)

    return {
        "pages": pages,
        "topics": topics,
        "sections": total_sections,
        "words": total_words,
    }


# ──────────────────────────────────────────────
# Rehber sayısı
# ──────────────────────────────────────────────

def count_guides(per_deck: dict) -> int:
    """Her deck'teki katalog index.html dışındaki tüm HTML = rehber."""
    total = sum(d["pages"] for d in per_deck.values())
    catalog_pages = len(DECKS)  # her deck'in 1 adet kök index.html'i
    return total - catalog_pages


# ──────────────────────────────────────────────
# Ana
# ──────────────────────────────────────────────

def format_words(n: int) -> str:
    """835240 → ~835k (en yakın 5k'ya yuvarla)"""
    k = round(n / 5000) * 5
    return f"~{k}k"


def main():
    per_deck = {}
    for deck in DECKS:
        print(f"  Taranıyor: {deck}...", flush=True)  # noqa
        per_deck[deck] = scan_deck(deck)

    total_pages    = sum(d["pages"]    for d in per_deck.values())
    total_sections = sum(d["sections"] for d in per_deck.values())
    total_topics   = sum(d["topics"]   for d in per_deck.values())
    total_words    = sum(d["words"]    for d in per_deck.values())
    total_guides   = count_guides(per_deck)

    result = {
        "total_pages":         total_pages,
        "total_sections":      total_sections,
        "total_guides":        total_guides,
        "total_topics":        total_topics,
        "total_words":         total_words,
        "total_words_rounded": format_words(total_words),
        "per_deck":            per_deck,
    }

    print("\n" + "=" * 52)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 52)

    # index.html güncelleme için özet
    print("\n  -- index.html guncelleme degerleri --")
    print(f"  Rehber       : {total_guides}")
    print(f"  Bolum        : {total_sections}")
    print(f"  HTML Sayfa   : {total_pages}")
    print(f"  Kelime       : {format_words(total_words)}  (ham: {total_words:,})")
    print(f"  Bagimlilik   : 0  (degismez)")
    print()
    print("  -- Arsiv kartlari --")
    for deck in DECKS:
        d = per_deck[deck]
        print(f"  {deck:<20}: {d['pages']} sayfa . {d['topics']} konu")


if __name__ == "__main__":
    main()
