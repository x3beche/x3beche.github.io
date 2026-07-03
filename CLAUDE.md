# CLAUDE.md — x3beche.github.io

## What this repo is

Personal portfolio + Turkish-language technical tutorial platform for Emirhan Pehlevan (TÜBİTAK BİLGEM, Embedded Linux Research Scholar). Hosted on GitHub Pages at `https://x3beche.github.io` via Jekyll.

**All content is in Turkish** — HTML `lang="tr"`, UI strings, commit messages.

The tutorials are organized as **decks** — self-contained thematic sets, each its own top-level folder and each served as an MCP data source. As of 2026-07 there are **24 decks / 334 tutorials** (the old monolithic `embedded-deck` was split into 21 domain decks; `ai-deck`, `rust-deck`, `project-deck` kept as-is).

---

## Repo layout

```
index.html              # Resume/portfolio (layout: page) — lists all decks (#deckler grid)
_config.yml             # Minimal Jekyll config (kramdown+GFM, no theme)
_layouts/
  page.html             # Generic layout — injects page.css from front-matter
  tutorial.html         # Tutorial layout — hardcodes /deck-assets/ CSS+JS (see Gotchas)
deck-assets/            # SHARED assets for every deck's tutorials + generated catalogs
  tutorial.css          #   tutorial page styles (used by ALL decks)
  copy-button.js        #   code copy button (used by ALL decks)
  catalog.css           #   deck catalog (card grid) styles
  bash-tools-index.css  #   cli-tools-deck/bash-tools hub sub-catalog styles
assets/main.css         # Portfolio (root index.html) CSS only
<deck>-deck/            # one folder per deck (network-deck, kernel-deck, ai-deck, …)
  deck.yml              #   deck meta: title + summary (gen-deck-index.py reads this)
  index.html            #   deck catalog (layout: page) — searchable card grid
  index.json            #   DERIVED: structural article index (MCP reads this)
  llms.txt / llms-full.txt  # DERIVED: llms.txt standard + full text
  <topic>/index.html    #   a tutorial (clean dir URL /<deck>/<topic>/)
  <hub>/index.html      #   optional hub sub-catalog (layout: page) + <hub>/<name>.html tutorials
scripts/
  gen-deck-index.py     #   generic: index.json + llms.txt + llms-full.txt + root llms.txt
  compute_stats.py      #   platform stats (pages/topics/sections/words)
mcp/                    #   FastMCP server: auto-mounts every deck as <prefix>_search/_get_article/_list
```

`ai-deck`, `rust-deck`, `project-deck` have **bespoke, hand-written catalogs** with their own `<deck>/assets/<deck>.css` and no `deck.yml` — do NOT regenerate or overwrite these. The other 21 decks have generated catalogs (`/deck-assets/catalog.css` + self-contained search JS) and a `deck.yml`.

No `Gemfile` committed — GitHub Pages does its own native Jekyll build.
`_config.yml` excludes `.claude/`, `*.md`, Gemfiles, `scripts/`, `mcp/` from the build.

---

## Tutorial file shape

Every tutorial follows this skeleton (reference: `yocto-deck/yocto/index.html`, `ai-deck/transformer/index.html`):

```html
---
layout: tutorial
title: "Konu Başlığı"
back_url: "../index.html"      # single-topic dirs point at their deck catalog
back_label: "Tüm eğitimler"
---
<header class="header">
  <div class="meta">
    <span>TEKNİK REHBER</span><span>KATEGORİ</span><span>KONU</span><span>2026</span>
  </div>
  <h1>Başlık<br><em>Alt başlık</em></h1>
  <p class="subtitle">Kısa açıklama.</p>
</header>

<nav class="toc"> … </nav>
<main>
  <section id="s0"><h2><span class="num">01</span> Bölüm Başlığı</h2> … </section>
</main>
```

Sections anchor with `#sN` (zero-indexed). `<span class="num">` is zero-padded two digits.
The **2nd `<div class="meta">` span is the category, the 3rd is the topic** — `gen-deck-index.py` parses these into `index.json`.

Two physical shapes: **single-topic** `<deck>/<topic>/index.html` (`back_url: "../index.html"`), and **hub** files `<deck>/<hub>/<name>.html` with a `<hub>/index.html` sub-catalog (`back_url: "index.html"`, `back_label: "← <hub>"`).

---

## Adding / moving tutorials

- New tutorial: drop a `layout: tutorial` HTML under a deck (single-topic dir or a hub), then run `python scripts/gen-deck-index.py`. Add a card to that deck's `index.html` catalog if it's a generated deck.
- New deck: create `<name>-deck/` with at least one `layout: tutorial` HTML + a `deck.yml` (title+summary). It is auto-discovered by `gen-deck-index.py`, `compute_stats.py`, and the MCP server — zero extra code.
- Always regenerate derived files after content changes: `python scripts/gen-deck-index.py` (use `--check` in CI).

---

## MCP (mcp/)

`mcp/server.py` auto-discovers every folder that contains an `index.json` and mounts it, exposing `<prefix>_search` / `<prefix>_get_article` / `<prefix>_list`. The prefix = deck folder minus `-deck`, with hyphens → underscores (`cli-tools-deck` → `cli_tools_search`). Runs stdio by default (offline/local LLMs). `index.json` embeds full article text, so the server is self-contained per deck.

---

## Gotchas

### 1. Liquid escaping in code examples (critical)
Jekyll parses `{{ }}` and `{% %}` inside `<pre><code>`. Any Jinja/Ansible/Helm/template syntax breaks the build. **Fix:** wrap with `{%- raw -%}` / `{%- endraw -%}`.

### 2. Shared tutorial assets live in /deck-assets/
`_layouts/tutorial.html` hardcodes `/deck-assets/tutorial.css` and `/deck-assets/copy-button.js`, used by **every deck's tutorials**. Generated catalogs use `/deck-assets/catalog.css`. Do not rename/move these without updating the layout and catalogs. (`deck-assets/` is in the scripts' SKIP lists so it isn't mistaken for a deck.)

### 3. Validation
`jekyll build` (native, exit 0) is the primary validator; also `python scripts/gen-deck-index.py --check` (index freshness) and a link-integrity pass (every catalog card href + tutorial `back_url` must resolve). Broken counts/links are otherwise silent.

---

## Commit & workflow conventions

- Commits in **Turkish**, loose Conventional Commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `chore(stats):`, or freeform `Round N: …`
- Bulk additions use **"Round N" passes**: add HTML → update catalog cards → regenerate indexes → update root stats.

---

## Do not touch

- `_site/`, `.jekyll-cache/` — build artifacts (local only, gitignored)
- `.claude/`, `memory.md` — excluded from build / gitignored (local secrets)
- `<deck>/index.json`, `llms.txt`, `llms-full.txt`, root `llms.txt` — DERIVED, regenerate via the script
- `ai-deck` / `rust-deck` / `project-deck` bespoke `index.html` catalogs
- CV PDF and personal files (see `.gitignore`)
