"""
generate_data.py
================
Roda o pipeline completo do "Oveview Crédito.py" e salva TODOS os dados
como public/data/dashboard.json que o Next.js lê.

Uso:
    python scripts/generate_data.py          # modo completo (API ComDinheiro)
    python scripts/generate_data.py --offline  # modo offline (Excel salvos)

Execute na raiz do projeto Next.js (pasta Lançamento/).
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path

# ── Localiza o script principal ────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent          # pasta Lançamento/
SCRIPT_PY    = PROJECT_ROOT / "Oveview Crédito.py"
OUTPUT_DIR   = PROJECT_ROOT / "public" / "data"
OUTPUT_FILE  = OUTPUT_DIR / "dashboard.json"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Usa Excel salvos (sem API)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Simula a seleção de modo do script original ──────────────────────────
    # O script original usa input() — aqui sobreescrevemos para não travar.
    import builtins
    _modo = "3" if args.offline else "1"
    builtins.input = lambda _prompt="": _modo

    # ── Carrega o script principal em namespace isolado ──────────────────────
    ns = {"__file__": str(SCRIPT_PY), "__name__": "__main__"}
    print(f"\n{'='*52}")
    print(f"  generate_data.py — modo {'offline' if args.offline else 'completo'}")
    print(f"  Script: {SCRIPT_PY}")
    print(f"  Saída:  {OUTPUT_FILE}")
    print(f"{'='*52}\n")

    with open(SCRIPT_PY, "r", encoding="utf-8-sig") as f:
        src = f.read()

    # Remove a parte final que gera o HTML e abre o browser (não precisa aqui)
    # O corte é antes do HTML_TEMPLATE para evitar executar o format() gigante
    # e evitar que o webbrowser.open() seja chamado.
    CUT_MARKER = "\nHTML_TEMPLATE"
    cut_pos = src.find(CUT_MARKER)
    if cut_pos == -1:
        # Fallback: executa tudo mas substitui webbrowser.open por no-op
        src = src.replace("webbrowser.open(", "print('(webbrowser.open suprimido)') #")
    else:
        src = src[:cut_pos]

    # Executa o pipeline de dados
    exec(compile(src, str(SCRIPT_PY), "exec"), ns)

    # ── Extrai variáveis do namespace ─────────────────────────────────────────
    def g(name, default=None):
        return ns.get(name, default)

    # Logo em base64
    logo_html = g("logo_html", '<div style="font-size:17px;font-weight:700;color:#b69d74">DOURO CAPITAL</div>')

    # Carteiras/setores/officers
    df_cart = g("df_cart")
    carteiras = []
    officers  = []
    if df_cart is not None:
        import pandas as pd
        carteiras = sorted(df_cart["carteira"].dropna().unique().tolist())
        if "officer" in df_cart.columns:
            officers = sorted(
                df_cart["officer"].dropna().replace("N/D", pd.NA).dropna().unique().tolist()
            )

    # Monta o payload
    payload = {
        "ativos":           json.loads(g("ativos_js", "[]")),
        "fin_series":       json.loads(g("fin_series_js", "{}")),
        "rank_corp":        json.loads(g("rank_corp_js", "[]")),
        "rank_bancos":      json.loads(g("rank_bancos_js", "[]")),
        "spreads_ts":       json.loads(g("spreads_ts_js", "{}")),
        "perf_data":        json.loads(g("perf_js", '{"datas":[],"ativos":{},"correlacao":{"labels":[],"values":[]}}')),
        "bonds_info":       json.loads(g("bonds_info_js", "[]")),
        "bonds_ts":         json.loads(g("bonds_ts_js", "{}")),
        "setores":          json.loads(g("setores_js", "[]")),
        "pl_total":         json.loads(g("pl_total_js", "0")),
        "pl_por_carteira":  json.loads(g("pl_por_carteira_js", "{}")),
        "news_data":        json.loads(g("news_js", "{}")),
        "alertas":          json.loads(g("alertas_js", "[]")),
        "fatos_relevantes": json.loads(g("fatos_relevantes_js", "[]")),
        "bcb_live":         json.loads(g("bcb_bancos_js", "{}")),
        "build_info":       json.loads(g("build_info_js", "{}")),
        "carteiras":        carteiras,
        "officers":         officers,
        "logo_html":        logo_html,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, default=str)

    size_mb = OUTPUT_FILE.stat().st_size / 1024 / 1024
    print(f"\n{'='*52}")
    print(f"  ✓ dashboard.json gerado com sucesso!")
    print(f"  Tamanho: {size_mb:.1f} MB")
    print(f"  Ativos:  {len(payload['ativos'])}")
    print(f"  Alertas: {len(payload['alertas'])}")
    print(f"  Notícias:{len(payload['news_data'].get('noticias', []))}")
    print(f"{'='*52}")
    print("\n  Próximo passo: python scripts/extract_js.py")
    print("  Depois:        npm run dev\n")

if __name__ == "__main__":
    main()
