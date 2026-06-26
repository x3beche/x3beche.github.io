# x3beche-decks — Deck başına bir MCP

Bu klasör, `x3beche.github.io` sitesindeki her **deck**'i (embedded-deck, ai-deck,
project-deck, rust-deck ve gelecekte eklenecekler) AI'ın tüketebileceği bir **veri
MCP'sine** çevirir. İlke: **deck başına bir MCP** — ama tek kod tabanı, deck başına
sıfır ek kod.

```
makaleler ──▶ scripts/gen-deck-index.py ──▶ <deck>/index.json + llms.txt + llms-full.txt
                                                      │
                          ┌───────────────────────────┼───────────────────────────┐
                          ▼                            ▼                            ▼
                   GitMCP (sıfır kod)         FastMCP deck sunucusu          probelabs/docs-mcp
                   (llms.txt okur)            (yapısal arama — bu klasör)    (deck başına npx)
```

Tek bir generic boru hattı, üç tüketim yolu. Hepsi aynı `index.json`/`llms.txt`
temelini paylaşır.

---

## 0. Önce index'i üret

MCP sunucusu `<deck>/index.json` dosyalarını okur. Bunları jeneratör üretir:

```bash
python scripts/gen-deck-index.py
```

Her deck için `index.json`, `llms.txt`, `llms-full.txt` ve kökte birleştiren bir
`/llms.txt` üretilir. Bu dosyalar **türetilmiştir** — elle düzenleme, içerik değişince
jeneratörü tekrar çalıştır. Yeni bir deck (içinde `layout: tutorial` HTML'ler olan
dizin) eklenince **ek kod olmadan** otomatik keşfedilir.

---

## 1. FastMCP deck sunucusu (önerilen — yapısal arama)

Tek generic sunucu her deck'i kendi prefix'iyle mount eder ve şu tool'ları sunar:

| Tool                  | İş                                                         |
|-----------------------|------------------------------------------------------------|
| `<deck>_search`       | başlık/özet/etiket/içerikte skorlu arama                   |
| `<deck>_get_article`  | bir makalenin tam metni (slug ile)                         |
| `<deck>_list`         | deck'teki tüm rehberler (slug + başlık + özet)             |

Örnek: `rust_search`, `embedded_get_article`, `ai_list` …

### Kurulum

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r mcp/requirements.txt
```

### Çalıştırma / doğrulama

```bash
python mcp/server.py                 # stdio (yerel istemciler)
fastmcp run mcp/server.py:main       # fastmcp CLI ile aynısı
fastmcp dev mcp/server.py:main       # MCP Inspector — tool'ları gör/test et
```

### İstemciye bağlama

**Claude Code**
```bash
claude mcp add x3beche-decks -- python /MUTLAK/YOL/x3beche.github.io/mcp/server.py
```

**Claude Desktop** (`claude_desktop_config.json`) veya **Cursor** (`~/.cursor/mcp.json`)
```jsonc
{
  "mcpServers": {
    "x3beche-decks": {
      "command": "python",
      "args": ["/MUTLAK/YOL/x3beche.github.io/mcp/server.py"]
    }
  }
}
```
`fastmcp install mcp/server.py:main --client claude` komutu da Claude Desktop'a
otomatik ekler.

> Not: Sunucu repo kökünü `mcp/`'nin bir üstü olarak bulur. Farklı bir konumdan
> çalıştırıyorsan `X3BECHE_REPO_ROOT` ortam değişkenini repo köküne ayarla.

---

## 2. GitMCP (sıfır kod, anında)

`gitmcp.io` herhangi bir public repoyu/GitHub Pages sitesini uzaktan MCP'ye çevirir
ve `llms.txt`'i önceliklendirir. Hiçbir kurulum gerekmez — sadece `llms.txt`'in
yayınlanmış olması yeter.

İstemciye eklenecek MCP URL'i:
```
https://gitmcp.io/x3beche/x3beche.github.io
```

[![Add to MCP](https://img.shields.io/badge/MCP-gitmcp.io-blue)](https://gitmcp.io/x3beche/x3beche.github.io)

**Sınır:** repo başına tek endpoint; "deck başına ayrı tool" vermez — ayrım kök
`llms.txt`'teki deck bölümleri + arama ile sağlanır. Gerçek deck-başına tool için
(1) numaralı FastMCP sunucusunu kullan.

---

## 3. probelabs/docs-mcp (ara seçenek — deck başına npx)

Kod yazmadan, deck başına ayrı bir sunucu + özel tool adı isteniyorsa:

```jsonc
{
  "mcpServers": {
    "rust-deck": {
      "command": "npx",
      "args": ["-y", "@probelabs/docs-mcp@latest",
               "--gitUrl", "https://github.com/x3beche/x3beche.github.io",
               "--toolName", "search_rust_docs",
               "--toolDescription", "Türkçe Rust eğitim setinde arama yapar"]
    }
  }
}
```

Her deck için `--toolName search_<deck>_docs` ile bir giriş ekle. Otomatik git
güncellemesiyle içerik taze kalır.

---

## Dosyalar

| Dosya                         | İş                                                          |
|-------------------------------|-------------------------------------------------------------|
| `scripts/gen-deck-index.py`   | generic üretici → `index.json` + `llms.txt` + `llms-full.txt` |
| `mcp/deck_mcp.py`             | `build_deck_server(deck)` — generic alt-sunucu fabrikası     |
| `mcp/server.py`               | deck'leri keşfeder, her birini prefix'le mount eder          |
| `mcp/fastmcp.json`            | `fastmcp run/deploy` konfigürasyonu                          |
| `mcp/requirements.txt`        | `fastmcp>=3.0`                                                |

## Yeni deck ekleme

1. `<deck>/` altına `layout: tutorial` HTML makaleler koy (mevcut deck şablonuyla).
2. `python scripts/gen-deck-index.py` çalıştır.
3. Hepsi bu — `<deck>_search`/`<deck>_get_article`/`<deck>_list` tool'ları kendiliğinden çıkar.
