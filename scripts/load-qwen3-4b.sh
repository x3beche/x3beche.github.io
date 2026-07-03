#!/usr/bin/env bash
# load-qwen3-4b.sh — qwen3-4b-2507'yi 4GB GPU'ya MAX sığacak + MAX context ile yükle.
#
# Ölçüm (lms --estimate-only, bu makine): --gpu max (full offload) ile 4GB'a sığan
# en büyük context ≈ 16384 (~3.5 GiB). 32768 ≈ 4.67 GiB → full-offload'da SIĞMAZ.
# Daha fazla context istiyorsan:
#   (a) context'i büyüt + --gpu'yu düşür (kısmi offload; KV RAM'e taşar, yavaşlar):
#         ./load-qwen3-4b.sh 32768 0.6
#   (b) LM Studio GUI'de "K/V Cache Quantization = Q4_0" + "Flash Attention" aç
#       (bunlar lms CLI'da yok) → 32k+ GPU'da sığar.
#
# Kullanım:
#   ./scripts/load-qwen3-4b.sh [context=16384] [gpu=max]
#   ./scripts/load-qwen3-4b.sh --estimate 32768   # sadece tahmin, yükleme

set -euo pipefail
export PATH="$HOME/.lmstudio/bin:$PATH"

MODEL="qwen/qwen3-4b-2507"
ID="x3beche-qwen"

if [[ "${1:-}" == "--estimate" ]]; then
  lms load "$MODEL" --gpu "${3:-max}" -c "${2:-16384}" --estimate-only
  exit 0
fi

CTX="${1:-16384}"
GPU="${2:-max}"

echo "» LM Studio server başlatılıyor…"
lms server start >/dev/null 2>&1 || true

echo "» $MODEL yükleniyor — context=$CTX  gpu=$GPU  id=$ID"
# aynı id yüklüyse kaldır (idempotent)
lms unload "$ID" >/dev/null 2>&1 || true
lms load "$MODEL" --gpu "$GPU" --context-length "$CTX" --identifier "$ID" -y

echo "✓ Yüklendi.  API: http://localhost:1234  (model: $ID)"
echo "  Kilo Code → LM Studio sağlayıcı, model: $ID"
