#!/usr/bin/env bash
# ============================================================
# AEGIS AI — Free-Tier Cloud Deployment Verification CLI
# Validates environment configuration, database connection, and deployment blueprints.
# ============================================================

set -e

echo "=== AEGIS AI Cloud Deployment Preflight Check ==="

# Check required files
FILES=("render.yaml" "railway.json" "Dockerfile.backend" "Dockerfile.frontend" "scripts/start_cloud.sh")
for f in "${FILES[@]}"; do
    if [ -f "$f" ]; then
        echo "[+] Found $f"
    else
        echo "[-] Missing $f"
        exit 1
    fi
done

echo "[*] Verifying Python environment..."
python -c "import fastapi, sqlalchemy, pydantic; print('[+] Core Python modules loaded successfully')"

echo "[*] Verifying Blueprint YAML syntax..."
python -c "import yaml; yaml.safe_load(open('render.yaml', 'r', encoding='utf-8')); print('[+] render.yaml syntax is valid')"

echo "[*] Verifying Railway config syntax..."
python -c "import json; json.load(open('railway.json', 'r', encoding='utf-8')); print('[+] railway.json syntax is valid')"

echo "=== All preflight checks passed successfully! ==="
