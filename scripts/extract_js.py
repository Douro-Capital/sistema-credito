'''
extract_js.py
=============
Extrai o JavaScript do HTML_TEMPLATE do script Python e salva em
public/dashboard-init.js para ser carregado pelo Next.js.

O processo:
  1. Lê o HTML_TEMPLATE do script Python (string entre """ e """)
  2. Converte {{ → { e }} → } (desfaz o escape do Python .format())
  3. Extrai apenas os blocos <script>...</script>
  4. Remove o bloco de dados injetados pelo Python ({ativos_js} etc.)
     porque esses dados agora são injetados pelo React via window.*
  5. Adiciona a função initDashboard() que o React chama após setar os dados
  6. Salva em public/dashboard-init.js

Uso:
    python scripts/extract_js.py

Execute na raiz do projeto Next.js (pasta Lançamento/).
'''

import re
import sys
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCRIPT_PY    = PROJECT_ROOT / "Oveview Crédito.py"
OUTPUT_FILE  = PROJECT_ROOT / "public" / "dashboard-init.js"

# Bloco que o Python injeta — substituído por window.* no React
DATA_INJECTION_PATTERN = re.compile(
    r'//\s*──\s*DADOS INJETADOS PELO PYTHON.*?(?=//\s*──\s*CONSTANTES|const COLORS)',
    re.DOTALL
)

def extract():
    print(f"\n{'='*52}")
    print("  extract_js.py — extraindo JavaScript do template")
    print(f"  Origem: {SCRIPT_PY.name}")
    print(f"  Saída:  public/dashboard-init.js")
    print(f"{'='*52}\n")

    with open(SCRIPT_PY, "r", encoding="utf-8-sig") as f:
        src = f.read()

    # ── 1. Encontra o HTML_TEMPLATE ────────────────────────────────────────
    # O template começa em: HTML_TEMPLATE = """
    # e termina em:         """
    m = re.search(r'HTML_TEMPLATE\s*=\s*"""', src)
    if not m:
        print("  ✗ HTML_TEMPLATE não encontrado no script!")
        sys.exit(1)

    template_start = m.end()
    # Encontra o fechamento do triple-quote (""" no início de uma linha)
    template_end = src.find('\n"""', template_start)
    if template_end == -1:
        print("  ✗ Fim do HTML_TEMPLATE não encontrado!")
        sys.exit(1)

    html_template_raw = src[template_start:template_end]
    print(f"  Template extraído: {len(html_template_raw):,} chars")

    # ── 2. Converte {{ → { e }} → } (desfaz o escape do .format()) ──────────
    html = html_template_raw.replace("{{", "{").replace("}}", "}")
    print(f"  Após conversão de braces: {len(html):,} chars")

    # ── 3. Extrai blocos <script>...</script> ─────────────────────────────
    script_blocks = re.findall(
        r'<script[^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE
    )
    print(f"  Blocos <script> encontrados: {len(script_blocks)}")

    combined_js = "\n\n".join(block.strip() for block in script_blocks if block.strip())

    # ── 4. Remove o bloco de dados injetados pelo Python ─────────────────────
    # Esse bloco tem a forma:
    #   const ATIVOS = {ativos_js};
    #   const FIN_SERIES = {fin_series_js};
    #   ...
    # Esses dados agora vêm do React (window.*)
    # Remove tudo entre o comentário "DADOS INJETADOS PELO PYTHON" e "CONSTANTES"
    combined_js = DATA_INJECTION_PATTERN.sub("", combined_js)

    # Remove declarações individuais de variáveis injetadas que ainda restarem
    injected_vars = [
        "ATIVOS", "FIN_SERIES", "RANK_CORP", "RANK_BANCOS",
        "SPREADS_TS", "PERF_DATA", "BONDS_INFO", "BONDS_TS",
        "setores", "PL_TOTAL", "PL_POR_CARTEIRA", "NEWS_DATA",
        "ALERTAS_NOTIF", "FATOS_RELEVANTES", "SCORECARD_SRC",
        "BCB_LIVE", "BUILD_INFO",
    ]
    for var in injected_vars:
        # Remove linhas do tipo: const VAR = {python_var};
        combined_js = re.sub(
            rf'^\s*const {var}\s*=\s*\{{[^;]*\}};\s*$',
            f'// {var} injetado pelo React via window.{var}',
            combined_js,
            flags=re.MULTILINE
        )
        # Versão alternativa com aspas
        combined_js = re.sub(
            rf'^\s*const {var}\s*=\s*"[^"]*";\s*$',
            f'// {var} injetado pelo React via window.{var}',
            combined_js,
            flags=re.MULTILINE
        )

    # ── 5. Adiciona wrapper initDashboard() que o React chama ────────────────
    init_wrapper = """
// ──────────────────────────────────────────────────────────────────────────
// initDashboard() — chamado pelo React após injetar os dados em window.*
// ──────────────────────────────────────────────────────────────────────────
window.initDashboard = function() {
  // Aguarda Chart.js estar disponível
  if (typeof Chart === 'undefined') {
    setTimeout(window.initDashboard, 150);
    return;
  }
  // Inicializa o dashboard na página home
  try {
    // Configura filtros searchable (ss-*)
    if (typeof initSSFilters === 'function') initSSFilters();
    // Abre a página inicial
    showPage('home', null);
    // Popula badges de notificações
    if (typeof buildNotifBadge === 'function') buildNotifBadge();
    // Configura sidebar rail
    if (typeof _setSidebarRail === 'function') _setSidebarRail(false);
    // Configura evento do botão Dourado
    const btn = document.getElementById('douradoBtn');
    if (btn) {
      btn.onclick = function() {
        const panel = document.getElementById('douradoPanel');
        if (panel) panel.classList.toggle('open');
      };
    }
    // Configura botão pin da sidebar
    const pinBtn = document.getElementById('sidebarPinBtn');
    if (pinBtn) {
      pinBtn.onclick = function() { toggleSidebarPin(); };
    }
    // Configura botão info
    const infoBtn = document.getElementById('sysInfoBtn');
    if (infoBtn) {
      infoBtn.onclick = function() { if (typeof openSysInfo === 'function') openSysInfo(); };
    }
    // Configura os filtros searchable
    document.querySelectorAll('.filter-pill[id^="ss-"]').forEach(function(pill) {
      const search = pill.querySelector('.ss-search');
      const list   = pill.querySelector('.ss-list');
      const label  = pill.querySelector('.ss-label');
      const prefix = pill.dataset.prefix || '';
      const allLbl = pill.dataset.all || 'Todos';
      // Toggle dropdown
      pill.addEventListener('click', function(e) {
        if (e.target.closest('.ss-dropdown')) return;
        const isOpen = pill.classList.contains('ss-open');
        document.querySelectorAll('.filter-pill.ss-open').forEach(function(p) { p.classList.remove('ss-open'); });
        if (!isOpen) { pill.classList.add('ss-open'); search && search.focus(); }
      });
      // Search
      if (search) {
        search.addEventListener('input', function() {
          const q = search.value.toLowerCase();
          list.querySelectorAll('.ss-opt').forEach(function(opt) {
            opt.classList.toggle('ss-hidden', q && !opt.textContent.toLowerCase().includes(q));
          });
        });
      }
      // Select option
      list && list.querySelectorAll('.ss-opt').forEach(function(opt) {
        opt.addEventListener('click', function() {
          const val = opt.dataset.value || '';
          list.querySelectorAll('.ss-opt').forEach(function(o) { o.classList.remove('ss-active'); });
          opt.classList.add('ss-active');
          if (label) label.textContent = prefix + (val || allLbl);
          pill.classList.remove('ss-open');
          // Sincroniza com o <select> oculto
          const pillId = pill.id.replace('ss-', '');
          const sel = document.getElementById(pillId + 'Filter');
          if (sel) { sel.value = val; if (typeof applyFilters === 'function') applyFilters(); }
        });
      });
    });
    // Fecha dropdowns ao clicar fora
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.filter-pill')) {
        document.querySelectorAll('.filter-pill.ss-open').forEach(function(p) { p.classList.remove('ss-open'); });
      }
    });
  } catch(err) {
    console.error('[Douro] Erro na inicialização:', err);
  }
};
"""

    final_js = init_wrapper + "\n" + combined_js

    # ── 6. Salva o arquivo ────────────────────────────────────────────────────
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_js)

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print("  OK dashboard-init.js gerado!")
    print(f"  Tamanho: {size_kb:.0f} KB")
    print(f"\n{'='*52}")
    print("  Próximo passo: npm run dev")
    print(f"{'='*52}\n")

if __name__ == "__main__":
    extract()
