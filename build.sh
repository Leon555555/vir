#!/usr/bin/env bash
echo "==> Instalando dependencias..."
pip install -r requirements.txt

echo "==> Aplicando migraciones..."
flask db upgrade

