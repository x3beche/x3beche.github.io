# x3beche.github.io

Kişisel portföy + Türkçe teknik rehber platformu — [Emirhan Pehlevan](https://www.linkedin.com/in/emirhanpehlevan/) · TÜBİTAK BİLGEM, Embedded Linux Research Scholar

**→ [x3beche.github.io](https://x3beche.github.io)**

---

## İki katman

1. **Portföy** — `index.html`: özgeçmiş; iş, staj, proje ve yarışma geçmişi
2. **Rehber platformu** — 4 "deck" halinde **~358 Türkçe teknik rehber**, tamamı tarayıcıda çalışan sıfır-bağımlılık HTML

---

## Portföy içeriği

| Bölüm | Kapsam |
|-------|--------|
| **İş** | Update Solutions (Fransa), Kraftgase (Almanya) |
| **Staj** | Aselsan, Baykar, Tübitak Bilgem ×2 |
| **Proje** | Pathology Slide Scanner, Flow Core, Agile Robotics, AX45-S |
| **Yarışma** | Teknofest Finali ×2 — Rakun Robotics, Momentum Hyperloop |
| **Eğitim** | Istanbul Medipol Üniversitesi · BSc EEE · GPA 3.58 |

---

## Rehber deck'leri

| Deck | Rehber | Konu | Kapsam |
|------|:------:|:----:|--------|
| **[embedded-deck](https://x3beche.github.io/embedded-deck/)** | 295 | 149 | Ağ protokolleri, kriptografi, sistem araçları, Linux yönetimi, serializasyon, performans optimizasyonu |
| **[ai-deck](https://x3beche.github.io/ai-deck/)** | 44 | 29 | LLM mimarisi, inference optimizasyonu, fine-tuning, RAG sistemleri |
| **[rust-deck](https://x3beche.github.io/rust-deck/)** | 17 | 17 | C/C++ geçmişinden gelenler için Rust — ownership, trait, borrow checker, iterator |
| **[project-deck](https://x3beche.github.io/project-deck/)** | 2 | 2 | Gerçek projelerin tersine mühendislik + derin protokol analizleri |

**Toplam:** ~358 rehber · 197 konu · 3.048 bölüm · ~910k kelime

---

## Makine-okunabilir kaynaklar (LLM / MCP)

- Kök indeks: [`/llms.txt`](https://x3beche.github.io/llms.txt)
- Her deck için: `llms.txt` (liste + özetler), `llms-full.txt` (tam metin), `index.json` (yapısal dizin)
- `mcp/` — FastMCP tabanlı sunucu; deck içeriğini MCP araçları olarak sunar (GitMCP uyumlu)

---

## Teknik

- **Jekyll + GitHub Pages** · tema yok, kendi `_layouts/` dosyaları (`page`, `tutorial`)
- Sıfır JS bağımlılığı — gerçek zamanlı arama + kategori filtreleme saf JavaScript
- [embedded-deck](https://github.com/x3beche/embedded-deck) tasarım sistemi
- Klavye kısayolları: `/` arama odağı, `Esc` temizle
- Betikler: `scripts/compute_stats.py` (istatistik), `scripts/gen-deck-index.py` (indeks üretimi)

---

## Lisans

MIT
