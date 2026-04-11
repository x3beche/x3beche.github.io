/**
 * ════════════════════════════════════════════════════════════════════
 *  COPY BUTTON COMPONENT  ·  tutorials/assets/copy-button.js
 * ════════════════════════════════════════════════════════════════════
 *
 *  Sayfadaki tüm .code-block elementlerine otomatik kopyalama
 *  butonu ekler. Kendi CSS'ini enjekte eder, başka bir dosyaya
 *  ihtiyaç yoktur. Tek bir <script> satırı yeterli.
 *
 *  KULLANIM
 *  ────────
 *    <script src="path/to/copy-button.js" defer></script>
 *
 *  BEKLENEN HTML YAPISI
 *  ────────────────────
 *    <div class="code-block">
 *      <div class="code-header">
 *        <span>bash</span>
 *        <span class="dot">●</span>        ← buton bu dot'u değiştirir
 *      </div>
 *      <pre><code>...</code></pre>
 *    </div>
 *
 *  ÖZELLEŞTİRME
 *  ────────────
 *    LABELS   → buton metinlerini değiştir (dil çevirisi için)
 *    CSS      → görünümü değiştir (CSS variables: --accent, --border)
 *    *_ICON   → SVG ikonlarını değiştir
 *
 *  TARAYICI DESTEĞİ
 *  ────────────────
 *    Modern:   navigator.clipboard API (https veya localhost)
 *    Fallback: document.execCommand('copy') — file:// ve eski tarayıcı
 *
 * ════════════════════════════════════════════════════════════════════
 */

(function () {
  'use strict';

  /* ══════════ Metinler (Türkçe) ══════════ */
  var LABELS = {
    copy:      'kopyala',
    copied:    'kopyalandı',
    error:     'hata',
    ariaLabel: 'Komutu panoya kopyala'
  };

  /* ══════════ Buton CSS'i ══════════ */
  var CSS = [
    '.copy-btn {',
    '  background: transparent;',
    '  border: 1px solid var(--border, #1a1a1a);',
    '  color: var(--text-faint, #555555);',
    '  font-family: "JetBrains Mono", "Courier New", monospace;',
    '  font-size: 10px;',
    '  font-weight: 500;',
    '  letter-spacing: 0.12em;',
    '  text-transform: uppercase;',
    '  padding: 4px 10px;',
    '  border-radius: 3px;',
    '  cursor: pointer;',
    '  display: inline-flex;',
    '  align-items: center;',
    '  justify-content: center;',
    '  gap: 6px;',
    '  min-width: 102px;',
    '  line-height: 1;',
    '  transition: color .15s, border-color .15s, background .15s, transform .1s;',
    '  user-select: none;',
    '  -webkit-user-select: none;',
    '  -webkit-tap-highlight-color: transparent;',
    '}',
    '.copy-btn:hover {',
    '  border-color: var(--accent, #00ff9c);',
    '  color: var(--accent, #00ff9c);',
    '}',
    '.copy-btn:active { transform: scale(0.96); }',
    '.copy-btn:focus-visible {',
    '  outline: 1px solid var(--accent, #00ff9c);',
    '  outline-offset: 2px;',
    '}',
    '.copy-btn.copied {',
    '  border-color: var(--accent, #00ff9c);',
    '  color: var(--accent, #00ff9c);',
    '  background: rgba(0, 255, 156, 0.08);',
    '}',
    '.copy-btn.error {',
    '  border-color: var(--danger, #ff4545);',
    '  color: var(--danger, #ff4545);',
    '}',
    '.copy-btn svg { flex-shrink: 0; display: block; }'
  ].join('\n');

  /* ══════════ SVG ikonları (Feather) ══════════ */
  var COPY_ICON =
    '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>' +
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>' +
    '</svg>';

  var CHECK_ICON =
    '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<polyline points="20 6 9 17 4 12"/>' +
    '</svg>';

  /* ══════════ CSS'i head'e enjekte et ══════════ */
  function injectStyles() {
    if (document.getElementById('copy-btn-styles')) return;
    var style = document.createElement('style');
    style.id = 'copy-btn-styles';
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  /* ══════════ Buton elementi oluştur ══════════ */
  function createButton() {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'copy-btn';
    btn.setAttribute('aria-label', LABELS.ariaLabel);
    btn.innerHTML = COPY_ICON + '<span>' + LABELS.copy + '</span>';
    return btn;
  }

  /* ══════════ Durum değiştir (idle / copied / error) ══════════ */
  function setState(btn, state) {
    btn.classList.remove('copied', 'error');
    if (state === 'copied') {
      btn.classList.add('copied');
      btn.innerHTML = CHECK_ICON + '<span>' + LABELS.copied + '</span>';
    } else if (state === 'error') {
      btn.classList.add('error');
      btn.innerHTML = '<span>' + LABELS.error + '</span>';
    } else {
      btn.innerHTML = COPY_ICON + '<span>' + LABELS.copy + '</span>';
    }
  }

  /* ══════════ Metni panoya kopyala ══════════ */
  async function copyText(text) {
    // Modern yöntem: Clipboard API (https veya localhost gerekir)
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    // Fallback: geçici textarea + execCommand (file:// için kritik)
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.top = '-9999px';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      var ok = document.execCommand('copy');
      if (!ok) throw new Error('execCommand copy başarısız');
    } finally {
      document.body.removeChild(ta);
    }
  }

  /* ══════════ Tüm .code-block'lara buton ekle ══════════ */
  function init() {
    injectStyles();

    var blocks = document.querySelectorAll('.code-block');
    blocks.forEach(function (block) {
      var header = block.querySelector('.code-header');
      var code   = block.querySelector('pre code');
      if (!header || !code) return;

      // Aynı blokta birden fazla buton olmasın
      if (header.querySelector('.copy-btn')) return;

      var btn = createButton();

      btn.addEventListener('click', async function () {
        try {
          // innerText: span'lardaki metni düz yazıya çevirir, satır
          // sonlarını <pre> kurallarına göre korur — panoya tam
          // olarak kullanıcının gördüğü metin gider.
          await copyText(code.innerText);
          setState(btn, 'copied');
        } catch (err) {
          console.error('[copy-button]', err);
          setState(btn, 'error');
        }
        setTimeout(function () { setState(btn, 'idle'); }, 1800);
      });

      // .dot süs elemanını butonla değiştir (sağda yer alsın)
      var dot = header.querySelector('.dot');
      if (dot) {
        dot.replaceWith(btn);
      } else {
        header.appendChild(btn);
      }
    });
  }

  /* ══════════ DOM hazır olduğunda çalıştır ══════════ */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
