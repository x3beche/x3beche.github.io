# embedded-deck

Türkçe, sıfır bağımlılıklı teknik eğitim platformu. Tarayıcıda açılır, çalışır.

[**→ Canlı Demo**](https://emirpehlevan.github.io/embedded-deck/) <!-- URL'yi kendi GitHub Pages adresinle güncelle -->

---

## Kapsam

| Konu | İçerik |
|------|--------|
| **mTLS & TLS** | Sertifika oluşturma, TLS 1.3 el sıkışması, PKI, RSA matematiği |
| **Kriptografi Temelleri** | Simetrik/asimetrik şifreleme, dijital imzalar, X.509 |
| **gRPC** | .proto tanımı, 4 RPC türü (unary, streaming), Python örneği |
| **Protocol Buffers** | Şema, wire format, kod üretimi, geriye/ileriye uyumluluk |
| **Linux cron** | Sözdizimi, anacron, flock, sessiz hatalar, hata ayıklama |
| **Cython** | Python → C derleme, GIL, prange, memoryview, performans |
| **Bash Araçları** | 23 komut rehberi: grep, sed, awk, find, curl, ssh ve daha fazlası |

Toplam **7 ana rehber · 255 bölüm · 0 dış bağımlılık**

---

## Nasıl Kullanılır

```bash
git clone https://github.com/emirpehlevan/embedded-deck.git
cd embedded-deck
# index.html'i tarayıcıda aç
open index.html          # macOS
xdg-open index.html      # Linux
start index.html         # Windows
```

Sunucu gerekmez. Her HTML dosyası bağımsız olarak açılabilir.

---

## Proje Yapısı

```
embedded-deck/
├── index.html          # Ana portal — arama & kategori filtreleme
├── assets/
│   ├── tutorial.css    # Paylaşılan stil
│   └── copy-button.js  # Kod bloğu kopyalama
├── mtls/               # mTLS kurulumu + kriptografi teorisi + demo sertifikalar
├── grpc/               # gRPC servis yazımı
├── protobuf/           # Protocol Buffers
├── cron/               # Linux cron
├── cython/             # Cython ile Python hızlandırma
└── bash-tools/         # 23 Bash komut rehberi
```

---

## Özellikler

- **Sıfır bağımlılık** — CDN yok, build adımı yok, framework yok
- **Gerçek zamanlı arama** — Başlık, konu ve anahtar kelimelerde filtreleme
- **Kategori filtreleme** — Security, Network, Linux, Python, Serialization, Performance
- **Kopyala butonu** — Tüm kod bloklarında
- **Klavye kısayolları** — `/` arama odağı, `Esc` temizle
- **Tamamen Türkçe** içerik

---

## Yakında

`Kubernetes` · `Kafka` · `Docker` · `WebRTC` · `OpenTelemetry` · `eBPF`

---

## Lisans

MIT — İstediğin gibi kullan, değiştir, dağıt.
