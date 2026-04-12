# CLAUDE.md — x3beche.github.io

## What this repo is

Personal portfolio + Turkish-language technical tutorial platform for Emirhan Pehlevan (TÜBİTAK BİLGEM, Embedded Linux Research Scholar). Hosted on GitHub Pages at `https://x3beche.github.io` via Jekyll.

**All content is in Turkish** — HTML `lang="tr"`, UI strings, commit messages.

---

## Repo layout

```
index.html              # Resume/portfolio (layout: page)
_config.yml             # Minimal Jekyll config (kramdown+GFM, no theme)
_layouts/
  page.html             # Generic layout — injects page.css from front-matter
  tutorial.html         # Tutorial layout — hardcodes embedded-deck CSS (see Gotchas)
assets/main.css         # Portfolio CSS only
embedded-deck/
  index.html            # Searchable catalog (244 tutorials, 100 topic dirs)
  assets/               # catalog.css, tutorial.css, copy-button.js, bash-tools-index.css
  <topic>/index.html    # Tutorial files (and hub dirs with many HTMLs)
ai-deck/
  index.html            # Searchable catalog (45 tutorials, 30 topic dirs)
  assets/ai-deck.css
  <topic>/index.html
```

No `Gemfile` committed — GitHub Pages does its own native Jekyll build.
`_config.yml` excludes `.claude/`, `*.md`, Gemfiles from the build — so this file is not published.

---

## Tutorial file shape

Every tutorial follows this skeleton (reference: `embedded-deck/yocto/index.html`, `ai-deck/transformer/index.html`):

```html
---
layout: tutorial
title: "Konu Başlığı"
back_url: "../index.html"
back_label: "Tüm eğitimler"
---
<header class="header">
  <div class="meta">
    <span>TEKNİK REHBER</span><span>KATEGORİ</span><span>KONU</span><span>2026</span>
  </div>
  <h1>Başlık<br><em>Alt başlık</em></h1>
  <p class="subtitle">Kısa açıklama.</p>
</header>

<nav class="toc">
  <div class="toc-label">İçindekiler</div>
  <ol>
    <li><a href="#s0">Bölüm adı</a></li>
    ...
  </ol>
</nav>

<main>
  <section id="s0">
    <h2><span class="num">01</span> Bölüm Başlığı</h2>
    ...
  </section>
</main>
```

Sections anchor with `#sN` (zero-indexed). Section numbers in `<span class="num">` are zero-padded two digits.

---

## Catalog pattern

Both `embedded-deck/index.html` and `ai-deck/index.html` are searchable card grids. Each card has:

- `data-cats="..."` — space-separated category tokens for chip filtering
- `data-search="..."` — full keyword haystack for real-time search

**Chip counts and `result-count` are manually maintained.** Update them whenever you add or remove tutorials (see `embedded-deck/index.html:55–64`).

Embedded-deck has two tiers:
- **Hub rehber setleri** — multi-guide bundles (e.g. `bash-tools/`, `seri-protokoller/`, `kernel-debug/`)
- **Tekil rehber** — single-topic tutorials

---

## Gotchas

### 1. Liquid escaping in code examples (critical)
Jekyll parses `{{ }}` and `{% %}` inside `<pre><code>` blocks. Any Jinja, Ansible, Helm, or template syntax will break the build silently or produce garbled output.

**Fix:** wrap the block with `{%- raw -%}` / `{%- endraw -%}` tags.

Past incident: commit `89ffc45` ("Fix Liquid syntax errors: escape {{ }} and {% %} in code examples").

### 2. Cross-deck CSS & JS dependency
`_layouts/tutorial.html:10` hardcodes `/embedded-deck/assets/tutorial.css`.
`_layouts/tutorial.html:18` hardcodes `/embedded-deck/assets/copy-button.js`.

Both are used by **ai-deck tutorials too**. Do not rename or move these files without updating the layout.

### 3. No automated tests
Jekyll build is the only validator. A broken Liquid tag fails the build; everything else (broken links, wrong counts) is silent. Always visually verify catalog counts after bulk adds.

---

## Commit & workflow conventions

- Commits in **Turkish**, loose Conventional Commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `chore(stats):`, or freeform `Round N: …`
- Bulk content additions use **"Round N" passes**: add HTML files → update catalog cards → update stats counters
- Commit messages track stats: HTML count, section count, word count

---

## Do not touch

- `_site/`, `.jekyll-cache/` — build artifacts (local only)
- `.claude/` — excluded from build and git
- CV PDF and personal files (see `.gitignore`)
