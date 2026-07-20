#!/usr/bin/env bash
set -e

echo ""
echo " ==================================================="
echo "  GameFlow Connect — Iniciando..."
echo " ==================================================="
echo ""

# Verifica se o venv existe
if [ ! -f "venv/bin/activate" ]; then
    echo "[ERRO] Ambiente virtual não encontrado."
    echo "Execute: python -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

source venv/bin/activate
python src/main.py
