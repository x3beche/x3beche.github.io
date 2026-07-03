#!/usr/bin/env bash
# serve-proxy.sh — x3beche-decks'i HER ZAMAN AÇIK yerel servis olarak çalıştır.
#
# Tek süreç: HTTP MCP (Kilo/LM Studio URL ile bağlanır) + kontrol paneli (deck
# aç/kapa) + dakikada bir git pull & otomatik rebuild. Kilo'nun süreci başlatmasına
# gerek kalmaz; panel Kilo kapalıyken de açık kalır.
#
#   MCP   : http://127.0.0.1:8000/mcp   (X3BECHE_HTTP_PORT ile değiştir)
#   Panel : http://127.0.0.1:8765       (X3BECHE_UI_PORT ile değiştir)
#
# Kullanım:
#   ./scripts/serve-proxy.sh            # ön planda
#   nohup ./scripts/serve-proxy.sh >/tmp/x3beche-proxy.log 2>&1 &   # arka planda

cd "$(dirname "$0")/.."
export X3BECHE_HTTP=1
export X3BECHE_HTTP_PORT="${X3BECHE_HTTP_PORT:-8000}"
export X3BECHE_UI_PORT="${X3BECHE_UI_PORT:-8765}"
export X3BECHE_SYNC="${X3BECHE_SYNC:-1}"
export X3BECHE_SYNC_SEC="${X3BECHE_SYNC_SEC:-60}"

exec ./.venv/bin/python mcp/deck_proxy.py
