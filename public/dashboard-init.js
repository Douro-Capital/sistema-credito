
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

/* ── CONTEÚDO DIDÁTICO do painel direito ── */
  const _SYS_PROSE = [
    {
      title: 'Inicialização &amp; Modo',
      html: '<p class="sdg-prose-body">Quando você executa o script, ele começa fazendo uma única pergunta: <strong>modo 1</strong> (relatório completo) ou <strong>modo 2</strong> (só notícias rápidas)?</p><div class="sdg-prose-highlight">No modo 2, tudo termina em segundos — busca os feeds RSS, pontua as notícias e gera um HTML leve. No modo 1, todos os outros módulos são ativados em sequência.</div><p class="sdg-prose-body" style="margin-top:8px;">Antes de prosseguir, valida que os arquivos Excel existem, que as credenciais Comdinheiro estão configuradas e que o usuário é reconhecido — evitando falhas silenciosas mais tarde.</p>'
    },
    {
      title: 'Extração Paralela de Dados',
      html: '<p class="sdg-prose-body">Em vez de baixar uma fonte de cada vez, o sistema dispara <strong>10+ conexões ao mesmo tempo</strong> usando duas tecnologias:</p><div class="sdg-prose-highlight"><strong>ThreadPoolExecutor</strong> para tarefas pesadas de I/O (ler Excel, chamar Comdinheiro).<br><strong>asyncio + aiohttp</strong> para downloads de rede (CVM, Tesouro Direto).</div><p class="sdg-prose-body" style="margin-top:8px;">O resultado: o que levaria ~40 segundos sequencial termina em ~4 segundos. Os ZIPs da CVM cobrem demonstrativos financeiros de <strong>2011 até hoje</strong> — DRE, Balanço Ativo, Passivo e Fluxo de Caixa.</p>'
    },
    {
      title: 'Cálculos Financeiros',
      html: '<p class="sdg-prose-body">Com os dados brutos em mãos, o sistema monta todos os indicadores que aparecem na plataforma:</p><div class="sdg-prose-highlight">EBITDA · Dívida Líquida · FCF · ROE · ROIC — calculados em janela TTM (últimos 12 meses) e 36 meses.</div><p class="sdg-prose-body" style="margin-top:8px;">Para o spread, compara a taxa de cada ativo de crédito com a NTN-B de referência mais próxima, e calcula o z-score histórico para detectar se o spread está caro ou barato versus o próprio histórico.</p><div class="sdg-prose-highlight">Uma regra importante: D&A é sempre identificado pelo <strong>nome da conta</strong> (ex: "DEPRECIA"), nunca pelo código contábil — que muda de empresa para empresa.</div>'
    },
    {
      title: 'Indicadores Bancários — BCB IF.data',
      html: '<p class="sdg-prose-body">Para a aba <strong>Bancos</strong>, o sistema consulta diretamente a <strong>API pública do Banco Central</strong> (olinda.bcb.gov.br/IFDATA) — sem scraping, sem planilha manual:</p><div class="sdg-prose-highlight">Relatório 2 (Ativo) · Relatório 3 (Passivo) · Relatório 4 (DRE) · Relatório 5 (Estrutura de Capital) — para <strong>27 bancos</strong> do portfólio, de 2021 a 2024.</div><p class="sdg-prose-body" style="margin-top:8px;">Os nomes dos bancos são mapeados por similaridade contra o <em>Watch List Bancos.xlsm</em>, garantindo que <strong>BTG Pactual</strong>, <strong>Banco ABC</strong>, <strong>Daycoval</strong> etc. batam com os nomes exatos da planilha de rating. Dados reais têm prioridade; os valores estáticos de referência são usados só como fallback se a API estiver fora do ar.</p>'
    },
    {
      title: 'News Pipeline',
      html: '<p class="sdg-prose-body">4 feeds RSS são lidos em paralelo. Cada notícia passa por um <strong>sistema de pontuação</strong> antes de entrar na plataforma:</p><div class="sdg-prose-highlight">+pontos: fonte confiável · notícia recente · menciona R$ · verbos de evento ("anuncia", "corta", "revisa") · emissor está na carteira.</div><p class="sdg-prose-body" style="margin-top:8px;">No final, duplicatas são removidas por <strong>similaridade de Jaccard</strong> — se dois títulos compartilham mais de 65% das palavras, só o de maior score entra. O resultado são as notícias curadas que aparecem na aba Douro News.</p>'
    },
    {
      title: 'Geração do HTML Final',
      html: '<p class="sdg-prose-body">Todos os dados calculados são injetados como variáveis JavaScript dentro de um único template HTML gigante:</p><div class="sdg-prose-highlight">window.ATIVOS · window.SPREADS_TS · window.FIN_SERIES · window.NEWS — embutidos diretamente no arquivo, sem servidor.</div><p class="sdg-prose-body" style="margin-top:8px;">O resultado é um arquivo <strong>standalone</strong>: logo em base64, gráficos, SPA com 10 telas, o chatbot Dourado — tudo em um único .html que abre com dois cliques em qualquer PC da equipe, sem instalar nada.</p>'
    },
    {
      title: 'Motor NLQ — Dourado',
      html: '<p class="sdg-prose-body">O Dourado é um motor de <strong>linguagem natural 100% offline</strong>, sem GPT nem OpenAI. Funciona em 4 etapas:</p><div class="sdg-prose-highlight"><strong>1. Normaliza</strong> o texto (remove acentos, caixa)<br><strong>2. Extrai entidades</strong> (emissor por fuzzy match, setor, rating)<br><strong>3. Classifica a intenção</strong> por scoring de palavras-chave<br><strong>4. Consulta os dados</strong> e devolve resposta + gráfico</div><p class="sdg-prose-body" style="margin-top:8px;">São <strong>20 intents</strong> diferentes — de "qual o spread da Klabin?" até "quais empresas de energia estão aprovadas com duration acima de 4?". Zero custo por query, zero latência de rede.</p>'
    },
  ];

  /* ── DADOS dos módulos (para o terminal) ── */
  const _SYS_MODS = [
    {
      label:'Inicialização', color:'gold',
      logs:[
        {t:'ok', tx:'[BOOT] overview_credito.py iniciado'},
        {t:'info', tx:'[BOOT] Python 3.11 · pandas 2.x · aiohttp 3.x'},
        {t:'dim', tx:'[INPUT] Modo de execução? (1=completo / 2=news)'},
        {t:'gold', tx:'[INPUT] → modo 1 selecionado'},
        {t:'ok', tx:'[BOOT] caminhos validados · usuário confirmado'},
      ],
      prose:'<h4>Você escolhe o que o sistema faz</h4><p>O script pergunta: <strong style="color:#9a7e52">relatório completo</strong> (modo 1) ou só <strong style="color:#9a7e52">notícias rápidas</strong> (modo 2). No modo 2, encerra em segundos. No modo 1, dispara todos os módulos abaixo em sequência.</p>'
    },
    {
      label:'Extração Paralela', color:'teal',
      logs:[
        {t:'section', tx:'── EXTRAÇÃO DE DADOS ──'},
        {t:'info', tx:'[THREAD] ThreadPoolExecutor · workers=12'},
        {t:'ok', tx:'[OK] Carteira CP · Comdinheiro API · 847 linhas'},
        {t:'ok', tx:'[OK] Bonds offshore · 36M preços'},
        {t:'ok', tx:'[OK] Rankings Excel · scorecard · rating'},
        {t:'ok', tx:'[OK] Watch list · bancos · status'},
        {t:'info', tx:'[ASYNC] asyncio + aiohttp'},
        {t:'ok', tx:'[OK] Tesouro CSV · NTN-B · LFT'},
        {t:'ok', tx:'[OK] Cadastro CVM · CNPJ · setor'},
        {t:'ok', tx:'[OK] ZIPs CVM · DRE·BPA·BPP·DFC 2011-2026'},
        {t:'gold', tx:'[DONE] 10 fontes · ~4.2s total (paralelo)'},
      ],
      prose:'<h4>Ele busca tudo ao mesmo tempo, em paralelo</h4><p>Dispara <strong style="color:#0082a0">10+ conexões simultâneas</strong>: Comdinheiro, Excel local, Tesouro Nacional, CVM (demonstrativos de 2011 até hoje) — sem esperar uma de cada vez. ThreadPool cuida do IO-bound; asyncio cuida do network-bound.</p>'
    },
    {
      label:'Cálculos Financeiros', color:'blue',
      logs:[
        {t:'section', tx:'── TRATAMENTO E CÁLCULOS ──'},
        {t:'info', tx:'[PROC] tratar() · D\\u0026A por nome da conta'},
        {t:'dim', tx:'[D\\u0026A] "DEPRECIA" no nome → prioridade sobre 3.06.01'},
        {t:'ok', tx:'[OK] Trimestralizado ITR+DFP · sem duplicatas'},
        {t:'ok', tx:'[OK] KPIs TTM/36M · EBITDA · DivLíq · FCF · ROE · ROIC'},
        {t:'ok', tx:'[SPREAD] ntnb_ref merge · .dt.normalize()'},
        {t:'ok', tx:'[SPREAD] z-score · MAD · mediana · MM21'},
        {t:'ok', tx:'[EXPORT] ativos.json · spreads_ts.json · fin_series.json'},
      ],
      prose:'<h4>Todos os cálculos financeiros acontecem aqui</h4><p>Dados brutos da CVM viram indicadores: <strong style="color:#3174b8">EBITDA, Dívida Líquida, FCF, ROE, ROIC</strong>. Spreads são comparados com a NTN-B do dia, gerando z-scores para detectar distorções. D&A sempre pelo <em>nome da conta</em> — nunca pelo código contábil, que muda por empresa.</p>'
    },
    {
      label:'Indicadores BCB', color:'purple',
      logs:[
        {t:'section', tx:'── BCB IF.data — BANCOS ──'},
        {t:'info', tx:'[BCB] olinda.bcb.gov.br/IFDATA · 27 bancos'},
        {t:'info', tx:'[BCB] Relatório 2 → Ativo (operações de crédito, PL)'},
        {t:'info', tx:'[BCB] Relatório 3 → Passivo (PL fallback)'},
        {t:'info', tx:'[BCB] Relatório 4 → DRE (lucro, eficiência, provisão)'},
        {t:'info', tx:'[BCB] Relatório 5 → Estrutura Capital (Basileia, alav., imob.)'},
        {t:'ok', tx:'[OK] 2021 · 2022 · 2023 · 2024 coletados'},
        {t:'ok', tx:'[OK] Match por similaridade → Watch List Bancos.xlsm'},
        {t:'ok', tx:'[INJECT] BCB_LIVE → window.BCB_LIVE · substitui fallback estático'},
        {t:'gold', tx:'[DONE] Dados reais p/ aba Bancos: Basileia · ROE · PDD · Eficiência'},
      ],
      prose:'<h4>Dados bancários direto do Banco Central</h4><p>A API pública do BCB (<strong style="color:#6b5ca5">IF.data</strong>) retorna demonstrativos oficiais de 27 bancos do portfólio. Relatórios 2/3/4/5 cobrem Ativo, Passivo, DRE e Estrutura de Capital. Os nomes são mapeados por similaridade ao Watch List interno — dados reais sempre têm prioridade sobre os valores de referência estáticos.</p>'
    },
    {
      label:'News Pipeline', color:'gold',
      logs:[
        {t:'section', tx:'── NEWS PIPELINE ──'},
        {t:'info', tx:'[RSS] _rss() × 4 feeds · ThreadPool'},
        {t:'ok', tx:'[RSS] Valor Econômico · 38 itens'},
        {t:'ok', tx:'[RSS] Exame · 22 itens'},
        {t:'ok', tx:'[RSS] InfoMoney · 29 itens'},
        {t:'ok', tx:'[RSS] Reuters BR · 18 itens'},
        {t:'info', tx:'[SCORE] _classif() · Macro / Empresas / Mercado'},
        {t:'info', tx:'[SCORE] fonte + recência + R$ + verbos evento'},
        {t:'ok', tx:'[DEDUP] Jaccard 65% · 31 duplicatas removidas'},
        {t:'gold', tx:'[DONE] 76 notícias únicas curadas'},
      ],
      prose:'<h4>Notícias curadas automaticamente</h4><p>4 feeds RSS lidos em paralelo. Cada notícia ganha um <strong style="color:#9a7e52">score</strong>: peso da fonte, recência, presença de valores em R$, verbos de evento ("anuncia", "corta", "revisa") e se o emissor está na carteira. Duplicatas filtradas por similaridade de Jaccard ≥ 65%.</p>'
    },
    {
      label:'Geração HTML', color:'green',
      logs:[
        {t:'section', tx:'── GERAÇÃO HTML FINAL ──'},
        {t:'info', tx:'[HTML] HTML_TEMPLATE · 4.800 linhas'},
        {t:'ok', tx:'[INJECT] ATIVOS_JSON → window.ATIVOS'},
        {t:'ok', tx:'[INJECT] SPREADS_TS → window.SPREADS_TS'},
        {t:'ok', tx:'[INJECT] FIN_SERIES → window.FIN_SERIES'},
        {t:'ok', tx:'[INJECT] NEWS_JSON → window.NEWS'},
        {t:'ok', tx:'[BUILD] SPA 10 views · logo base64 embutida'},
        {t:'ok', tx:'[SAVE] overview_credito_2026-05-22.html'},
        {t:'gold', tx:'[OPEN] webbrowser.open() → Chrome'},
      ],
      prose:'<h4>Um único arquivo HTML — sem servidor</h4><p>Logo em base64, todos os dados embutidos como variáveis JS, gráficos Plotly/Chart.js, SPA com 10 telas — tudo num HTML <strong style="color:#2fa874">standalone</strong>. Qualquer PC da equipe abre com duplo clique, sem instalar nada, sem rede.</p>'
    },
    {
      label:'Motor NLQ', color:'gold',
      logs:[
        {t:'section', tx:'── MOTOR NLQ — DOURADO ──'},
        {t:'gold', tx:'[NLQ] 0 APIs externas · 100% offline'},
        {t:'info', tx:'[NLQ] _norm() · NFD · remove acentos'},
        {t:'info', tx:'[NLQ] _detectEmissor() · fuzzy match 847 ativos'},
        {t:'info', tx:'[NLQ] _matchIntent() · KW scoring + sim. cosseno'},
        {t:'ok', tx:'[NLQ] 20 intents registrados'},
        {t:'dim', tx:'[NLQ] intents: exposicao_emissor exposicao_setor'},
        {t:'dim', tx:'[NLQ]   query_param multi_filtro fund_delta'},
        {t:'dim', tx:'[NLQ]   spread_delta sintese_emissor grafico_spread'},
        {t:'dim', tx:'[NLQ]   mapa_risco risco_estresse + 11 mais'},
        {t:'gold', tx:'[READY] Dourado pronto para perguntas em PT-BR'},
      ],
      prose:'<h4>Dourado entende português — zero API externa</h4><p>Motor NLQ 100% offline: normaliza texto (NFD, acentos, caixa), extrai entidades (emissor por fuzzy match, setor, rating), classifica intenção por scoring de keywords + similaridade, consulta os dados da carteira em tempo real. Sem GPT, sem OpenAI, sem custo por query.</p>'
    },
  ];
  let _sysCurrentMod = 0;
  let _sysView = 'diagram';
  let _termTyping = null;

  function sysView(v) {
    _sysView = v;
    const dg=document.getElementById('sysViewDiagram');
    const tm=document.getElementById('sysViewTerminal');
    const sk=document.getElementById('sysViewShortcuts');
    const bD=document.getElementById('sysToggleDiagram');
    const bT=document.getElementById('sysToggleTerminal');
    const bS=document.getElementById('sysToggleShortcuts');
    // reset all
    [bD,bT,bS].forEach(b=>{ b.style.background='transparent'; b.style.color='#9a8a76'; b.style.boxShadow='none'; });
    dg.style.display='none'; tm.style.display='none'; sk.style.display='none';
    if(v==='diagram') {
      dg.style.display='flex';
      bD.style.background='linear-gradient(135deg,#b69d74,#d4b47a)'; bD.style.color='#fff'; bD.style.boxShadow='0 2px 8px rgba(182,157,116,.4)';
    } else if(v==='terminal') {
      tm.style.display='flex';
      bT.style.background='#0d1117'; bT.style.color='#e6edf3'; bT.style.boxShadow='0 2px 8px rgba(0,0,0,.4)';
      sysRenderTerminalAll();
    } else {
      sk.style.display='block';
      bS.style.background='linear-gradient(135deg,#3174b8,#5b9bd5)'; bS.style.color='#fff'; bS.style.boxShadow='0 2px 8px rgba(49,116,184,.35)';
    }
  }

  function sysSelectMod(idx) {
    _sysCurrentMod = idx;
    // highlight cards do diagrama
    document.querySelectorAll('.sdg-card,.sdg-card--half').forEach(el => {
      const modVal = el.closest('[data-mod]') ? parseInt(el.closest('[data-mod]').dataset.mod) : parseInt(el.dataset&&el.dataset.mod);
      el.classList.toggle('sdg-card-active', modVal===idx);
    });
    document.querySelectorAll('[data-mod]').forEach(el => {
      el.querySelectorAll('.sdg-card').forEach(c => {
        c.classList.toggle('sdg-card-active', parseInt(el.dataset.mod)===idx);
      });
    });
    // painel didático direito
    const prose = _SYS_PROSE[idx];
    if(prose) {
      document.getElementById('sdgPanelTitle').innerHTML = prose.title;
      const body = document.getElementById('sdgPanelBody');
      body.style.animation='none';
      body.innerHTML = prose.html;
      body.style.animation='sdgCardIn .22s ease';
    }
    // terminal (se ativo, rola até a seção)
    if(_sysView==='terminal') {
      const sec = document.getElementById('termSec'+idx);
      if(sec) sec.scrollIntoView({behavior:'smooth',block:'start'});
    }
  }

  /* Terminal: tipa TODOS os módulos em sequência ao abrir */
  function sysRenderTerminalAll() {
    if(_termTyping) { clearInterval(_termTyping); _termTyping=null; }
    const logEl = document.getElementById('sysTermLog');
    const proseEl = document.getElementById('sysTermProse');
    logEl.innerHTML = '';
    proseEl.innerHTML = '';
    // achata todas as linhas de todos os módulos com marcadores de seção
    const allLines = [];
    _SYS_MODS.forEach(function(mod, mi) {
      // separador de seção com ancora
      allLines.push({t:'_anchor', id:'termSec'+mi});
      mod.logs.forEach(function(ln) { allLines.push(ln); });
    });
    // popula prose de todos os módulos de uma vez (scroll serve como contexto)
    _SYS_MODS.forEach(function(mod, mi) {
      const prose = _SYS_PROSE[mi];
      if(!prose) return;
      const div = document.createElement('div');
      div.className = 'tprose-card';
      div.id = 'termProse'+mi;
      div.style.cssText = 'border-color:rgba(182,157,116,.18);background:#faf7f2;margin-bottom:14px;';
      div.innerHTML = '<h4>'+prose.title+'</h4>'+prose.html.replace(/<p class="sdg-prose-body"[^>]*>/g,'<p>').replace(/<div class="sdg-prose-highlight">/g,'<p style="font-style:italic;font-size:9.5px;color:#5a4a38;background:rgba(182,157,116,.08);border-left:2px solid #b69d74;padding:7px 10px;margin:8px 0;border-radius:0 5px 5px 0;">').replace(/<\/div>/g,'</p>');
      proseEl.appendChild(div);
    });
    // tipa as linhas de log
    let i=0;
    _termTyping = setInterval(function() {
      if(i>=allLines.length) { clearInterval(_termTyping); _termTyping=null; return; }
      const ln = allLines[i++];
      if(ln.t==='_anchor') {
        const anc = document.createElement('div');
        anc.id = ln.id;
        logEl.appendChild(anc);
      } else {
        const div = document.createElement('div');
        div.className = 'tlog-'+ln.t;
        div.style.margin='0';
        div.textContent = ln.tx;
        logEl.appendChild(div);
        logEl.scrollTop = logEl.scrollHeight;
      }
    }, 55);
  }

  function openSysInfo() {
    document.getElementById('sysInfoModal').style.display='flex';
    sysView('diagram');
    sysSelectMod(0);
  }
  function closeSysInfo() {
    document.getElementById('sysInfoModal').style.display='none';
    if(_termTyping) { clearInterval(_termTyping); _termTyping=null; }
  }
  document.getElementById('sysInfoModal').addEventListener('click', e => { if(e.target.id==='sysInfoModal') closeSysInfo(); });
  document.addEventListener('keydown', e => { if(e.key==='Escape'&&document.getElementById('sysInfoModal').style.display!=='none') closeSysInfo(); });

// ── DOURADO FULLSCREEN ────────────────────────────────────────────────────
const DF_HINTS = [
  { label:'SÍNTESE',     title:'Síntese de Emissor',
    examples:['Análise completa da Klabin','Me fala tudo sobre a Equatorial','Perfil completo da Rumo: fundamentos e spread'] },
  { label:'FUNDAMENTOS', title:'Filtro por Fundamento',
    examples:['Emissores com DL/EBITDA acima de 3.5x','Quais têm ROE abaixo de 8%?','Margem EBITDA maior que 25%'] },
  { label:'TEMPORAL',    title:'Evolução Temporal de KPI',
    examples:['Como evoluiu a alavancagem da Suzano?','Trajetória do EBITDA da Eneva nos últimos 12 meses','Como progrediu o FCF da Klabin?'] },
  { label:'COMPARATIVO', title:'Comparação de Emissores',
    examples:['Comparar Eneva e Engie em DL/EBITDA','Klabin vs Suzano: spread e alavancagem','Compare Energisa vs Cemig vs Copel'] },
  { label:'ESTRESSE',    title:'Estresse de Liquidez',
    examples:['Quais emissores em risco de refinanciamento?','Quais nomes com pressão de liquidez no setor elétrico?','Quem fica em apuros com juros altos?'] },
  { label:'Z-SCORE',     title:'Análise de Spread',
    examples:['Quais spreads mais subiram na carteira?','Quais spreads estão acima da mediana?','Quais emissores com spread mais alto por setor?'] },
  { label:'BENCHMARK',   title:'Benchmark Setorial',
    examples:['Equatorial vs média do setor elétrico em DL/EBITDA','Como a Raízen se compara ao setor?','Rumo vs peers de logística em alavancagem'] },
  { label:'VENCIMENTOS', title:'Mapa de Vencimentos',
    examples:['Perfil de vencimentos da carteira','Quais ativos vencem nos próximos 12 meses?','Estrutura de vencimentos da carteira'] },
  { label:'RANKING',     title:'Ranking Dinâmico',
    examples:['Quais spreads mais subiram no último ano?','Maiores posições por emissor','Ranking de alavancagem — maior para menor'] },
  { label:'MULTI-FILTRO',title:'Query Multi-Critério',
    examples:['Energia elétrica aprovada com duration acima de 4','Emissores rating AA com spread abaixo de 1.2%','Watch e saneamento com DL/EBITDA acima de 3x'] },
];

// glyphs SVG minimalistas — sem emojis
const DF_GLYPHS = [
  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><line x1="12" y1="3" x2="12" y2="21"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/></svg>',
  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polyline points="3 18 9 12 13 16 21 6"/><polyline points="17 6 21 6 21 10"/></svg>',
  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="18" y1="7" x2="6" y2="7"/><line x1="6" y1="17" x2="18" y2="17"/><polyline points="14 3 18 7 14 11"/><polyline points="10 21 6 17 10 13"/></svg>',
  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><line x1="3" y1="12" x2="8" y2="12"/><line x1="16" y1="12" x2="21" y2="12"/></svg>',
  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="8" y1="4" x2="8" y2="20"/><line x1="16" y1="4" x2="16" y2="20"/><line x1="3" y1="12" x2="21" y2="12"/></svg>',
  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="12" y1="20" x2="12" y2="4"/><polyline points="4 8 12 4 20 8"/><line x1="4" y1="12" x2="12" y2="16"/><line x1="20" y1="12" x2="12" y2="16"/></svg>',
  '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="18" r="3"/><line x1="9" y1="6" x2="15" y2="6"/><line x1="9" y1="18" x2="15" y2="18"/><line x1="6" y1="9" x2="6" y2="15"/><line x1="18" y1="9" x2="18" y2="15"/></svg>',
];

let _dfOpen = false;
let _dfHintsVisible = false;
let _dfInitialized = false;
let _orbAnim = null;

// ── ORB CANVAS ────────────────────────────────────────────────────────────
function _initOrb() {
  const cv = document.getElementById('dfOrbCanvas');
  if (!cv || cv._orbRunning) return;
  cv._orbRunning = true;
  const ctx = cv.getContext('2d');
  const W=34, H=34, cx=W/2, cy=H/2;
  let t=0;
  const pts = Array.from({length:5},(_,i)=>{
    const a=(i/5)*Math.PI*2;
    return { a, r:5+Math.random()*5, sp:.01+Math.random()*.015, sz:.7+Math.random()*1, al:.35+Math.random()*.45 };
  });
  function draw() {
    ctx.clearRect(0,0,W,H);
    const g=ctx.createRadialGradient(cx,cy,1,cx,cy,13);
    g.addColorStop(0,'rgba(212,180,122,.85)'); g.addColorStop(.5,'rgba(182,157,116,.45)');
    g.addColorStop(.85,'rgba(140,110,60,.15)'); g.addColorStop(1,'rgba(100,70,30,0)');
    ctx.beginPath(); ctx.arc(cx,cy,13,0,Math.PI*2); ctx.fillStyle=g; ctx.fill();
    const g2=ctx.createRadialGradient(cx-3,cy-3,0,cx,cy,7);
    g2.addColorStop(0,'rgba(255,240,200,.5)'); g2.addColorStop(1,'rgba(255,240,200,0)');
    ctx.beginPath(); ctx.arc(cx,cy,13,0,Math.PI*2); ctx.fillStyle=g2; ctx.fill();
    for(const p of pts) {
      p.a+=p.sp;
      ctx.beginPath(); ctx.arc(cx+Math.cos(p.a)*p.r, cy+Math.sin(p.a)*p.r, p.sz,0,Math.PI*2);
      ctx.fillStyle=`rgba(255,225,150,${p.al*(.7+.3*Math.sin(t*.04+p.a))})`;
      ctx.fill();
    }
    t++; _orbAnim=requestAnimationFrame(draw);
  }
  draw();
}

// ── RENDER LIQUID GLASS CARDS ─────────────────────────────────────────────
function _renderLGCards() {
  const list=document.getElementById('dfHintsList');
  if(!list||list._lgRendered) return;
  list._lgRendered=true;
  list.innerHTML=DF_HINTS.map((h,i)=>`
    <div class="df-lg-card" style="animation-delay:${i*.04}s">
      <div style="display:flex;align-items:center;gap:9px;margin-bottom:8px;">
        <div class="df-lg-icon" style="color:rgba(182,157,116,.85)">${DF_GLYPHS[i%DF_GLYPHS.length]}</div>
        <span class="df-lg-title">${h.label}</span>
      </div>
      ${h.examples.map(ex=>`
        <div class="df-lg-ex" onclick="dfUseHint(${JSON.stringify(ex)})">
          <span class="df-lg-arr">›</span>
          <span>${ex}</span>
        </div>`).join('')}
    </div>`).join('');
}

// ── EXPAND / COLLAPSE / TOGGLE ────────────────────────────────────────────
function douradoExpand() {
  const full=document.getElementById('douradoFull');
  full.style.display='flex'; _dfOpen=true; _initOrb();
  if(!_dfInitialized) {
    _dfInitialized=true;
    const src=document.getElementById('douradoMsgs'), dst=document.getElementById('douradoFullMsgs');
    if(src&&dst) { dst.innerHTML=src.innerHTML; dst.scrollTop=dst.scrollHeight; }
    _renderLGCards();
  }
}
function douradoCollapse() {
  document.getElementById('douradoFull').style.display='none';
  _dfOpen=false; _dfHintsVisible=false;
  document.getElementById('dfHintsPanel').style.display='none';
  if(_orbAnim){cancelAnimationFrame(_orbAnim);_orbAnim=null;}
  const cv=document.getElementById('dfOrbCanvas'); if(cv) cv._orbRunning=false;
}
function toggleDFHints() {
  _dfHintsVisible=!_dfHintsVisible;
  const panel=document.getElementById('dfHintsPanel');
  panel.style.display=_dfHintsVisible?'block':'none';
  if(_dfHintsVisible) _renderLGCards();
}
function dfUseHint(ex) {
  const inp=document.getElementById('douradoInputFull');
  if(inp){inp.value=ex;inp.focus();}
  // Force-collapse the hints panel without toggling the flag through toggleDFHints
  _dfHintsVisible=false;
  const panel=document.getElementById('dfHintsPanel');
  if(panel) panel.style.display='none';
  douradoSendFull();
}
function _douradoAddMsgBoth(role, text) {
  douradoAddMsg(role, text);
  const fullMsgs = document.getElementById('douradoFullMsgs');
  if (!fullMsgs || !_dfOpen) return;
  const div = document.createElement('div');
  div.className = `dourado-msg ${role==='user'?'user':''}`;
  if (role === 'bot') {
    div.innerHTML = `<div class="dourado-avatar" style="width:28px;height:28px;font-size:12px;flex-shrink:0;">D</div><div class="dourado-bubble">${_renderMd(text)}</div>`;
  } else {
    div.innerHTML = `<div class="dourado-bubble">${text.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>`;
  }
  fullMsgs.appendChild(div);
  fullMsgs.scrollTop = fullMsgs.scrollHeight;
}
function douradoSendFull() {
  _dspHide();
  const inp = document.getElementById('douradoInputFull');
  const txt = (inp.value || '').trim();
  if (!txt) return;
  inp.value = '';
  if(_dfHintsVisible) toggleDFHints();
  if(txt.startsWith('/')) { if(_douradoCmd(txt)) return; }
  _douradoAddMsgBoth('user', txt);
  setTimeout(() => {
    const resp = _nlqRespond(txt);
    if (resp && resp.text) {
      _douradoAddMsgBoth('bot', resp.text);
      if (resp.chart) _addChatChart(resp.chartTitulo || '', resp.chart);
    } else if (typeof resp === 'string') {
      _douradoAddMsgBoth('bot', resp);
    }
  }, 320);
}
function douradoChipFull(txt) {
  const inp = document.getElementById('douradoInputFull');
  if (inp) { inp.value = txt; inp.focus(); inp.setSelectionRange(txt.length, txt.length); }
}
document.getElementById('douradoFull').addEventListener('click', e => { if(e.target.id==='douradoFull') douradoCollapse(); });

// ── CONSTANTES ────────────────────────────────────────────────────────────
const COLORS = ['#b69d74','#00677b','#1f2839','#2fa874','#d94141','#3174b8','#a78bd4','#e0c44a','#60b85a','#d47aa7','#5ab8d4','#d4a77a'];
/* ── CROSSHAIR PLUGIN (linha vertical que snapa em X para todas as séries) ── */
const _crosshairPlugin = {
  id: 'crosshair',
  afterDraw(chart) {
    if (chart.config.type !== 'line') return;
    if (!chart._crosshairX) return;
    const {ctx, chartArea:{top,bottom}} = chart;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(chart._crosshairX, top);
    ctx.lineTo(chart._crosshairX, bottom);
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(182,157,116,.55)';
    ctx.setLineDash([4,3]);
    ctx.stroke();
    ctx.restore();
  },
  afterEvent(chart, args) {
    if (chart.config.type !== 'line') return;
    const e = args.event;
    if (e.type === 'mousemove') {
      chart._crosshairX = e.x;
    } else if (e.type === 'mouseout') {
      chart._crosshairX = null;
    }
    chart.draw();
  }
};
Chart.register(_crosshairPlugin);

/* opções comuns para gráficos com crosshair */
const _CROSSHAIR_OPTS = {
  interaction: { mode:'index', intersect:false, axis:'x' },
  plugins: {
    tooltip: {
      mode: 'index',
      intersect: false,
      backgroundColor: 'rgba(15,20,35,.88)',
      titleColor: '#d4b47a',
      bodyColor: '#c8c0b4',
      borderColor: 'rgba(182,157,116,.3)',
      borderWidth: 1,
      padding: 10,
      titleFont: { family:"'DM Mono',monospace", size:10 },
      bodyFont: { family:"'DM Mono',monospace", size:10 },
      callbacks: {
        label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}%`
      }
    }
  }
};

const CHART_DEFAULTS = {
  responsive:true,
  maintainAspectRatio:false,
  plugins:{ legend:{ labels:{ color:'#718096', font:{size:11, family:"'Montserrat', sans-serif"}, boxWidth:12 } } },
  scales:{
    x:{ ticks:{ color:'#718096', font:{size:10, family:"'DM Mono', monospace"}, maxTicksLimit:12 }, grid:{ color:'rgba(31,40,57,.05)' } },
    y:{ ticks:{ color:'#718096', font:{size:10, family:"'DM Mono', monospace"} }, grid:{ color:'rgba(31,40,57,.05)' } }
  }
};
const DOUGHNUT_OPTS = {
  responsive:true, maintainAspectRatio:false, cutout:'65%',
  plugins:{ legend:{ position:'bottom', labels:{ color:'#718096', font:{size:11, family:"'Montserrat', sans-serif"}, boxWidth:12, padding:12, filter:(item,data)=>data.datasets[0].data[item.index]>0 } } }
};
let activeCharts = {};
function mk(id, cfg) {
  const canvas = document.getElementById(id);
  if (!canvas) return null;
  if (activeCharts[id]) {
    try { activeCharts[id].destroy(); } catch(e) {}
    delete activeCharts[id];
  }
  canvas.width  = canvas.offsetWidth  || canvas.width;
  canvas.height = canvas.offsetHeight || canvas.height;
  try {
    const c = new Chart(canvas, cfg);
    activeCharts[id] = c;
    return c;
  } catch(e) {
    console.warn('Chart.js erro em "' + id + '":', e);
    return null;
  }
}
// ── HELPERS ───────────────────────────────────────────────────────────────
const fmtBRL = v => v==null?'—': v>=1e9?`R$ ${(v/1e9).toFixed(2)}Bi`: v>=1e6?`R$ ${(v/1e6).toFixed(1)}Mi`: v>=1e3?`R$ ${(v/1e3).toFixed(0)}K`:`R$ ${Number(v).toFixed(0)}`;
const fmtPct = v => v==null?'—':`${(v*100).toFixed(1)}%`;
const fmtX   = v => v==null?'—':`${Number(v).toFixed(2)}x`;
const badgeStatus = s => {
  const m = {Aprovado:'badge-green', Reprovado:'badge-red', 'Em análise':'badge-gold', Watch:'badge-gold', Monitoramento:'badge-gold'};
  return `<span class="badge ${m[s]||'badge-muted'}">${s||'—'}</span>`;
};
const badgeExposure = v => {
  return v ? '<span class="badge badge-red">Acima</span>' : '<span class="badge badge-muted">—</span>';
};
const badgeRating = r => {
  if (!r || r === 'N/D') return '<span class="badge badge-muted">—</span>';
  const aaa=['AAA'], aa=['AA+','AA','AA-'], a=['A+','A','A-'], bbb=['BBB+','BBB','BBB-'], bb=['BB+','BB','BB-'];
  const cls = aaa.includes(r)?'badge-blue': aa.includes(r)||a.includes(r)?'badge-teal': bbb.includes(r)||bb.includes(r)?'badge-gold': 'badge-red';
  return `<span class="badge ${cls}">${r}</span>`;
};
const htmlEncode = s => String(s||'')
  .replace(/&/g,'&amp;')
  .replace(/</g,'&lt;')
  .replace(/>/g,'&gt;')
  .replace(/"/g,'&quot;')
  .replace(/'/g,'&#39;');
// ── FILTROS ───────────────────────────────────────────────────────────────
function getFiltered() {
  const cart    = document.getElementById('carteiraFilter').value;
  const setor   = document.getElementById('setorFilter').value;
  const officer = document.getElementById('officerFilter')?.value || '';
  return ATIVOS.filter(a =>
    (!cart    || a.carteira === cart)   &&
    (!setor   || a.setor   === setor)  &&
    (!officer || a.officer === officer)
  );
}
function applyFilters() {
  buildComposicao();
  buildRating();
  spInicializado = false;
  buildSpreads();
  buildTunel();
}
// ── NAVEGAÇÃO ─────────────────────────────────────────────────────────────
const initializedPages = {};
const loadedPages = {};
function showPage(id, el) {
  const current = document.querySelector('.page.active');
  const pg      = document.getElementById('page-' + id);
  if (current && current !== pg) {
    current.classList.add('page-exit');
    current.addEventListener('animationend', () => {
      current.classList.remove('active', 'page-exit');
    }, { once: true });
  } else if (current) {
    current.classList.remove('active');
  }
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  pg.classList.remove('page-enter');
  void pg.offsetWidth;
  pg.classList.add('active', 'page-enter');
  pg.addEventListener('animationend', () => pg.classList.remove('page-enter'), { once: true });
  if(el) el.classList.add('active');
  // Esconde filtros na home (Panorama)
  const tRight = document.querySelector('.topbar-right');
  if (tRight) tRight.style.display = id === 'home' ? 'none' : '';
  const builders = {
    home: buildHome,
    composicao: buildComposicao,
    rating: buildRating,
    spreads: buildSpreads,
    tunel: buildTunel,
    bonds: buildBonds,
    ranking: buildRanking,
    performance: buildPerformance,
    financeiros: buildFinanceiros,
    fundamentos: buildFundamentos,
    timeline: buildTimeline,
    bancos: buildBancos,
    'douro-news': buildDouroNews,
    notificacoes: buildNotificacoes,
    scorecard: buildScorecard,
    'compras-vendas': buildComprasVendas
  };
  const hBtn = document.getElementById('homeBtnTopbar');
  if (hBtn) hBtn.classList.toggle('active', id === 'home');
  _setSidebarRail(id !== 'home');
  if (builders[id]) {
    requestAnimationFrame(() => {
      builders[id]();
      setTimeout(() => {
        Object.values(activeCharts).forEach(c => {
          try { c.resize(); c.update(); } catch(e){}
        });
      }, 80);
    });
  }
}
// ── HOME PAGE NAVIGATION ───────────────────────────────────────────────────
function homeSelectEmp(empresa) {
  showPage('fundamentos', document.querySelector('.nav-item[onclick*="fundamentos"]'));
  setTimeout(() => {
    const sel = document.getElementById('fundEmpSel');
    if (sel) {
      sel.value = empresa;
      sel.dispatchEvent(new Event('change'));
    }
  }, 100);
}
function homeSelectBanco(banco) {
  showPage('bancos', document.querySelector('.nav-item[onclick*="bancos"]'));
  setTimeout(() => {
    const sel = document.getElementById('bancosEmpSel');
    if (sel) {
      sel.value = banco;
      sel.dispatchEvent(new Event('change'));
    }
    buildBancos(banco);
  }, 100);
}
function homeDiveScorecard(tipo) {
  if (tipo === 'corp') {
    showPage('scorecard', document.querySelector('.nav-item[onclick*="scorecard"]'));
  } else if (tipo === 'banco') {
    showPage('scorecard', document.querySelector('.nav-item[onclick*="scorecard"]'));
  }
}
// ── COMPOSIÇÃO HELPERS ────────────────────────────────────────────────────
function getCorStatus(nomeEmissor) {
  const match = ATIVOS.find(a => a.emissor === nomeEmissor);
  const st = (match?.Status||'').trim();
  if (st==='Aprovado')  return '#00677b';
  if (st==='Reprovado') return '#d94141';
  return '#b69d74';
}

// ── BAR-CLICK EMISSOR FILTER ───────────────────────────────────────────────
let _emFiltroBar = null;
let _cachedAtivos = [], _cachedTotalCred = 0, _cachedPLFilt = 0;
let _ativosAcimaLimite = false;
function _toggleAcimaLimite() {
  _ativosAcimaLimite = !_ativosAcimaLimite;
  const btn = document.getElementById('btnAcimaLimite');
  if (btn) {
    btn.style.background = _ativosAcimaLimite ? 'rgba(217,65,65,.12)' : 'var(--surface2)';
    btn.style.borderColor = _ativosAcimaLimite ? '#d94141' : 'var(--border)';
    btn.style.color = _ativosAcimaLimite ? '#d94141' : 'var(--text3)';
  }
  _renderTbodyAtivos();
}
let _setorFiltroDonut = null;
let _ratingFilter = { classe: null, ratingMkt: null, ratingDouro: null };

let _ativosSortCol = 'saldo';
let _ativosSortAsc = false;
function _ativosSort(col) {
  if (_ativosSortCol === col) { _ativosSortAsc = !_ativosSortAsc; }
  else { _ativosSortCol = col; _ativosSortAsc = col === 'carteira' || col === 'ticker' || col === 'emissor' || col === 'setor' || col === 'classe' || col === 'status'; }
  _renderTbodyAtivos();
  _renderTbodyAtivosRating();
}
function _ativosSortReset() {
  _ativosSortCol = 'saldo'; _ativosSortAsc = false;
  const inp = document.getElementById('ativosSearch');
  if (inp) inp.value = '';
  const inpRating = document.getElementById('ativosSearchRating');
  if (inpRating) inpRating.value = '';
  _renderTbodyAtivos();
  _renderTbodyAtivosRating();
}
function _renderTbodyAtivos() {
  const q = (document.getElementById('ativosSearch')?.value || '').toLowerCase().trim();
  // Pre-compute emissor saldo totals from full cached set
  const _emissorSaldo = {};
  _cachedAtivos.forEach(a => {
    const em = a.emissor || '—';
    _emissorSaldo[em] = (_emissorSaldo[em] || 0) + (a.saldo || 0);
  });
  const _expMaxPct = a => {
    const raw = a.Status === 'Reprovado' ? 0 : (a.exposicao_maxima_rating || 0);
    return raw > 0 && raw < 1 ? raw * 100 : raw;
  };
  const _emissorCarteiraSaldo = {};

_cachedAtivos.forEach(a => {
    const key = `${a.carteira}|||${a.emissor}`;

    _emissorCarteiraSaldo[key] =
        (_emissorCarteiraSaldo[key] || 0) +
        (a.saldo || 0);
});
  const _pctEmissor = a => {
    const key = `${a.carteira}|||${a.emissor}`;
    const plCart = (typeof PL_POR_CARTEIRA !== 'undefined' && PL_POR_CARTEIRA[a.carteira]) ? PL_POR_CARTEIRA[a.carteira] : _cachedPLFilt;
    return plCart > 0
        ? (_emissorCarteiraSaldo[key] || 0) / plCart * 100
        : 0;
};
  const _isAcima = a => {
    const pct = _pctEmissor(a);
    const exp = _expMaxPct(a);
    return (a.Status === 'Reprovado' && pct > 0) || (exp > 0 && pct > exp);
  };
  let source = _cachedAtivos;
  if (_setorFiltroDonut) source = source.filter(a => (a.setor||'N/D') === _setorFiltroDonut);
  if (_emFiltroBar) source = source.filter(a => (a.emissor||'').toLowerCase() === _emFiltroBar.toLowerCase());
  if (_ativosAcimaLimite) source = source.filter(a => _isAcima(a));
  if (q) {
    source = source.filter(a => {
      const fields = [a.carteira,a.ticker,a.emissor,a.setor,a.classe,a.Status,a['Rating base S&P'],a['Rating Douro']];
      return fields.some(f => f && String(f).toLowerCase().includes(q));
    });
  }
  const cmpStr = (a, b) => (a||'').localeCompare(b||'', 'pt-BR');
  const cmpNum = (a, b) => (a||0) - (b||0);
  const dir = _ativosSortAsc ? 1 : -1;
  source = [...source].sort((a, b) => {
    switch(_ativosSortCol) {
      case 'carteira':  return dir * cmpStr(a.carteira, b.carteira);
      case 'ticker':    return dir * cmpStr(a.ticker, b.ticker);
      case 'emissor':   return dir * cmpStr(a.emissor, b.emissor);
      case 'setor':     return dir * cmpStr(a.setor, b.setor);
      case 'saldo':     return dir * cmpNum(a.saldo, b.saldo);
      case 'pctCred':   return dir * cmpNum(_pctEmissorR(a), _pctEmissorR(b));
      case 'pctPL':     return dir * cmpNum(_expMaxPctR(a), _expMaxPctR(b));
      case 'duration':  return dir * cmpNum(a.duration, b.duration);
      case 'classe':    return dir * cmpStr(a.classe, b.classe);
      case 'status':    return dir * cmpStr(a.Status, b.Status);
      default:          return dir * cmpNum(b.saldo, a.saldo);
    }
  });
  ['carteira','ticker','emissor','setor','saldo','pctCred','pctPL','duration','classe','status'].forEach(col => {
    const el = document.getElementById('_sh_'+col);
    const el2 = document.getElementById('_sh_'+col+'_rating');
    const text = col === _ativosSortCol ? (_ativosSortAsc ? '↑' : '↓') : '↕';
    const style = col === _ativosSortCol ? 'var(--teal)' : '';
    if (el) { el.textContent = text; el.style.opacity = col === _ativosSortCol ? '1' : '.4'; el.style.color = style; }
    if (el2) { el2.textContent = text; el2.style.opacity = col === _ativosSortCol ? '1' : '.4'; el2.style.color = style; }
  });
  const tag = document.getElementById('emFiltroTag');
  if (tag) {
    let tagHtml = '';
    if (_setorFiltroDonut) tagHtml += `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(182,157,116,.12);border:1px solid rgba(182,157,116,.4);border-radius:12px;padding:2px 10px 2px 8px;font-size:10px;font-weight:600;color:#b69d74;margin-left:8px;cursor:pointer" onclick="_clearSetorFiltro()">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/></svg>
        Setor: ${_setorFiltroDonut}&nbsp;<span style="font-size:13px;line-height:1;opacity:.7">×</span></span>`;
    if (_emFiltroBar) tagHtml += `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.3);border-radius:12px;padding:2px 10px 2px 8px;font-size:10px;font-weight:600;color:var(--teal);margin-left:8px;cursor:pointer" onclick="_clearEmFiltroBar()">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/></svg>
        ${_emFiltroBar}&nbsp;<span style="font-size:13px;line-height:1;opacity:.7">×</span></span>`;
    tag.innerHTML = tagHtml;
  }
  const hasFilter = _setorFiltroDonut || _emFiltroBar;
  document.getElementById('countAtivos').textContent =
    hasFilter ? `— ${source.length} posição(ões) · ${_cachedAtivos.length} total` : `— ${source.length} de ${_cachedAtivos.length} posições`;
  document.getElementById('tbodyAtivos').innerHTML = source
    .map(a => {
      const pctEm = _pctEmissor(a);
      const expMax = _expMaxPct(a);
      const acima = _isAcima(a);
      const rowBg = acima ? 'background:rgba(217,65,65,.05);' : '';
      const pctEmStyle = acima ? 'color:#d94141;font-weight:700;' : '';
      const expMaxStr = a.Status === 'Reprovado' ? '0,00%' : (expMax > 0 ? expMax.toFixed(2)+'%' : '—');
      return `<tr style="${rowBg}">
        <td class="td-muted">${a.carteira||'—'}</td>
        <td style="font-weight:700">${a.ticker||'—'}</td>
        <td>${a.emissor||'—'}</td>
        <td class="td-muted">${a.setor||'—'}</td>
        <td style="font-family:var(--mono)">${fmtBRL(a.saldo)}</td>
        <td style="font-family:var(--mono);${pctEmStyle}">${pctEm.toFixed(2)}%</td>
        <td style="font-family:var(--mono)">${expMaxStr}</td>
        <td style="font-family:var(--mono)">${a.duration?Number(a.duration).toFixed(1)+'a':'—'}</td>
        <td class="td-muted">${a.classe||'—'}</td>
        <td>${badgeRating(a['Rating base S&P'])}</td>
        <td>${badgeRating(a['Rating Douro'])}</td>
        <td>${badgeStatus(a.Status)}</td>
      </tr>`;
    }).join('');
}

function _renderTbodyAtivosRating() {
  const q = (document.getElementById('ativosSearchRating')?.value || '').toLowerCase().trim();
  const _emissorSaldoR = {};
  _cachedAtivos.forEach(a => {
    const em = a.emissor || '—';
    _emissorSaldoR[em] = (_emissorSaldoR[em] || 0) + (a.saldo || 0);
  });
  const _expMaxPctR = a => {
    const raw = a.Status === 'Reprovado' ? 0 : (a.exposicao_maxima_rating || 0);
    return raw > 0 && raw < 1 ? raw * 100 : raw;
  };
  const _emissorCarteiraSaldo = {};
_cachedAtivos.forEach(a => {
    const key = `${a.carteira}|||${a.emissor}`;
    _emissorCarteiraSaldo[key] =
        (_emissorCarteiraSaldo[key] || 0) +
        (a.saldo || 0);
});
  const _pctEmissorR = a => {
    const key = `${a.carteira}|||${a.emissor}`;
    const plCart = (typeof PL_POR_CARTEIRA !== 'undefined' && PL_POR_CARTEIRA[a.carteira]) ? PL_POR_CARTEIRA[a.carteira] : _cachedPLFilt;
    return plCart > 0
        ? (_emissorCarteiraSaldo[key] || 0) / plCart * 100
        : 0;
  };
  let source = _cachedAtivos;
  if (_ratingFilter.classe) source = source.filter(a => (a.classe||'') === _ratingFilter.classe);
  if (_ratingFilter.ratingMkt) source = source.filter(a => (a['Rating base S&P']||'') === _ratingFilter.ratingMkt);
  if (_ratingFilter.ratingDouro) source = source.filter(a => (a['Rating Douro']||'') === _ratingFilter.ratingDouro);
  if (q) {
    source = source.filter(a => {
      const fields = [a.carteira,a.ticker,a.emissor,a.setor,a.classe,a.Status,a['Rating base S&P'],a['Rating Douro']];
      return fields.some(f => f && String(f).toLowerCase().includes(q));
    });
  }
  const cmpStr = (a, b) => (a||'').localeCompare(b||'', 'pt-BR');
  const cmpNum = (a, b) => (a||0) - (b||0);
  const dir = _ativosSortAsc ? 1 : -1;
  source = [...source].sort((a, b) => {
    switch(_ativosSortCol) {
      case 'carteira':  return dir * cmpStr(a.carteira, b.carteira);
      case 'ticker':    return dir * cmpStr(a.ticker, b.ticker);
      case 'emissor':   return dir * cmpStr(a.emissor, b.emissor);
      case 'setor':     return dir * cmpStr(a.setor, b.setor);
      case 'saldo':     return dir * cmpNum(a.saldo, b.saldo);
      case 'pctCred':   return dir * cmpNum(_pctEmissor(a), _pctEmissor(b));
      case 'pctPL':     return dir * cmpNum(_expMaxPct(a), _expMaxPct(b));
      case 'duration':  return dir * cmpNum(a.duration, b.duration);
      case 'classe':    return dir * cmpStr(a.classe, b.classe);
      case 'status':    return dir * cmpStr(a.Status, b.Status);
      default:          return dir * cmpNum(b.saldo, a.saldo);
    }
  });
  const tag = document.getElementById('emFiltroTagRating');
  if (tag) {
    let tagHtml = '';
    if (_ratingFilter.classe) tagHtml += `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(182,157,116,.12);border:1px solid rgba(182,157,116,.4);border-radius:12px;padding:2px 10px 2px 8px;font-size:10px;font-weight:600;color:#b69d74;margin-left:8px;cursor:pointer" onclick="_clearRatingFiltro()">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/></svg>
        Classe: ${_ratingFilter.classe}&nbsp;<span style="font-size:13px;line-height:1;opacity:.7">×</span></span>`;
    if (_ratingFilter.ratingMkt) tagHtml += `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.3);border-radius:12px;padding:2px 10px 2px 8px;font-size:10px;font-weight:600;color:var(--teal);margin-left:8px;cursor:pointer" onclick="_clearRatingFiltro()">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/></svg>
        Rating Mkt: ${_ratingFilter.ratingMkt}&nbsp;<span style="font-size:13px;line-height:1;opacity:.7">×</span></span>`;
    if (_ratingFilter.ratingDouro) tagHtml += `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(182,157,116,.12);border:1px solid rgba(182,157,116,.4);border-radius:12px;padding:2px 10px 2px 8px;font-size:10px;font-weight:600;color:#b69d74;margin-left:8px;cursor:pointer" onclick="_clearRatingFiltro()">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/></svg>
        Rating Douro: ${_ratingFilter.ratingDouro}&nbsp;<span style="font-size:13px;line-height:1;opacity:.7">×</span></span>`;
    tag.innerHTML = tagHtml;
  }
  const hasFilter = _ratingFilter.classe || _ratingFilter.ratingMkt || _ratingFilter.ratingDouro;
  document.getElementById('countAtivosRating').textContent =
    hasFilter ? `— ${source.length} posição(ões) · ${_cachedAtivos.length} total` : `— ${source.length} de ${_cachedAtivos.length} posições`;
  document.getElementById('tbodyAtivosRating').innerHTML = source
    .map(a => {
      const pctEmR = _pctEmissorR(a);
      const expMaxR = _expMaxPctR(a);
      const acimaR = (a.Status === 'Reprovado' && pctEmR > 0) || (expMaxR > 0 && pctEmR > expMaxR);
      const rowBgR = acimaR ? 'background:rgba(217,65,65,.05);' : '';
      const pctEmStyleR = acimaR ? 'color:#d94141;font-weight:700;' : '';
      const expMaxStrR = a.Status === 'Reprovado' ? '0,00%' : (expMaxR > 0 ? expMaxR.toFixed(2)+'%' : '—');
      return `<tr style="${rowBgR}">
        <td class="td-muted">${a.carteira||'—'}</td>
        <td style="font-weight:700">${a.ticker||'—'}</td>
        <td>${a.emissor||'—'}</td>
        <td class="td-muted">${a.setor||'—'}</td>
        <td style="font-family:var(--mono)">${fmtBRL(a.saldo)}</td>
        <td style="font-family:var(--mono);${pctEmStyleR}">${pctEmR.toFixed(2)}%</td>
        <td style="font-family:var(--mono)">${expMaxStrR}</td>
        <td style="font-family:var(--mono)">${a.duration?Number(a.duration).toFixed(1)+'a':'—'}</td>
        <td class="td-muted">${a.classe||'—'}</td>
        <td>${badgeRating(a['Rating base S&P'])}</td>
        <td>${badgeRating(a['Rating Douro'])}</td>
        <td>${badgeStatus(a.Status)}</td>
      </tr>`;
    }).join('');
}

function _clearRatingFiltro() {
  _ratingFilter = { classe: null, ratingMkt: null, ratingDouro: null };
  ['chartClasse', 'chartRatingMkt', 'chartRatingDouro'].forEach(id => {
    const chart = Chart.getChart(id);
    if (chart) {
      chart.data.datasets[0].backgroundColor = chart.data.labels.map((_,i) => COLORS[i%COLORS.length] + 'ee');
      chart.update('none');
    }
  });
  _renderTbodyAtivosRating();
}

function _clearEmFiltroBar() {
  _emFiltroBar = null;
  const chart = Chart.getChart('chartEmissor');
  if (chart) {
    chart.data.datasets[0].backgroundColor = chart.data.labels.map(l => getCorStatus(l)+'cc');
    chart.data.datasets[0].borderColor     = chart.data.labels.map(l => getCorStatus(l));
    chart.update('none');
  }
  _renderTbodyAtivos();
  _renderTbodyAtivosRating();
}

function _clearSetorFiltro() {
  _setorFiltroDonut = null;
  const donut = Chart.getChart('chartSetor');
  if (donut) {
    const orig = donut.data.labels.map((_,i) => COLORS[i%COLORS.length]+'ee');
    donut.data.datasets[0].backgroundColor = orig;
    donut.data.datasets[0].borderWidth = 2;
    donut.update('none');
  }
  _renderBarEmissor();
  _renderTbodyAtivos();
  _renderTbodyAtivosRating();
}

function _renderBarEmissor() {
  const src = _setorFiltroDonut
    ? _cachedAtivos.filter(a => (a.setor||'N/D') === _setorFiltroDonut)
    : _cachedAtivos;
  const byE = {};
  src.forEach(a => { const em = a.emissor||'Sem emissor'; byE[em]=(byE[em]||0)+(a.saldo||0); });
  const emSort = Object.entries(byE).sort((a,b)=>b[1]-a[1]);
  const chart = Chart.getChart('chartEmissor');
  if (!chart) return;
  chart.data.labels = emSort.map(e=>e[0]);
  chart.data.datasets[0].data = emSort.map(e=>+((e[1]/1e6).toFixed(2)));
  chart.data.datasets[0].backgroundColor = emSort.map(e=>getCorStatus(e[0])+'cc');
  chart.data.datasets[0].borderColor = emSort.map(e=>getCorStatus(e[0]));
  chart.update('none');
  _emFiltroBar = null;
}

function homeDiveEmp(empresa) {
  const navEl = document.querySelector('.nav-item[onclick*="fundamentos"]');
  showPage('fundamentos', navEl);
  if (navEl) navEl.classList.add('active');
  requestAnimationFrame(() => {
    setTimeout(() => {
      const sel = document.getElementById('fundEmpSel');
      if (!sel) return;
      const normaliza = s => (s||'').toString().normalize('NFD').replace(/[̀-ͯ]/g,'').trim().toUpperCase();
      const opts = [...sel.options];
      const match = opts.find(o => normaliza(o.text) === normaliza(empresa) || normaliza(o.text).includes(normaliza(empresa).split(' ')[0]));
      if (match) { sel.value = match.value; buildFundamentos(); }
    }, 100);
  });
}

// ── HOME — COMMAND CENTER ─────────────────────────────────────────────────
function buildHome() {
  const cartSel    = document.getElementById('carteiraFilter').value;
  const ativosBase = cartSel ? ATIVOS.filter(a => a.carteira === cartSel) : ATIVOS;
  const ativos     = ativosBase.filter(a => (a.saldo || 0) > 0);
  const totalCred  = ativos.reduce((s, a) => s + (a.saldo || 0), 0);

  const dataRef = document.getElementById('homeDataRef');
  if (dataRef) dataRef.textContent = 'Dados de ' + new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'short', year:'numeric' });

  const STATUS_ANALISE  = ['Em análise','Watch','Monitoramento'];
  const STATUS_COBERTOS = ['Aprovado','Reprovado',...STATUS_ANALISE];
  const aprovados    = ativos.filter(a => a.Status === 'Aprovado').reduce((s,a) => s+(a.saldo||0), 0);
  const analise      = ativos.filter(a => STATUS_ANALISE.includes(a.Status)).reduce((s,a) => s+(a.saldo||0), 0);
  const durPond      = totalCred > 0
    ? (ativos.reduce((s,a) => s+(a.duration||0)*(a.saldo||0), 0) / totalCred).toFixed(1) : '—';
  const nEmissores   = new Set(ativos.map(a => a.emissor).filter(Boolean)).size;

  document.getElementById('homeKpiRow').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Crédito Privado</div><div class="kpi-value">${fmtBRL(totalCred)}</div><div class="kpi-sub">${ativos.length} ativos · ${nEmissores} emissores</div></div>
    <div class="kpi-card"><div class="kpi-label">Duration Média</div><div class="kpi-value">${durPond}a</div><div class="kpi-sub">Ponderada por saldo</div></div>
    <div class="kpi-card"><div class="kpi-label">Aprovados</div><div class="kpi-value">${totalCred>0?((aprovados/totalCred)*100).toFixed(1):0}%</div><span class="kpi-badge green">${fmtBRL(aprovados)}</span></div>`;

  const byE = {};
  ativos.forEach(a => { byE[a.emissor||'S/N'] = (byE[a.emissor||'S/N']||0) + (a.saldo||0); });
  const emSort   = Object.entries(byE).sort((a,b) => b[1]-a[1]).slice(0, 10);
  const saldosMi = emSort.map(e => +((e[1]/1e6).toFixed(2)));
  const pctPL    = emSort.map(e => PL_TOTAL > 0 ? +((e[1]/PL_TOTAL)*100).toFixed(2) : 0);
  const getCorSt = em => {
    const match = ATIVOS.find(a => a.emissor === em);
    const st    = (match?.Status||'').trim();
    if (st === 'Aprovado')  return '#00677b';
    if (st === 'Reprovado') return '#d94141';
    return '#b69d74';
  };
  const wrapHome = document.getElementById('homeChartEmissorWrap');
  if (wrapHome) { wrapHome.style.width = '100%'; wrapHome.style.removeProperty('overflow-x'); }
  const canvasHomeEm = document.getElementById('homeChartEmissor');
  if (canvasHomeEm) { canvasHomeEm.removeAttribute('width'); canvasHomeEm.removeAttribute('height'); }
  mk('homeChartEmissor', {
    type: 'bar',
    data: { labels: emSort.map(e => e[0]), datasets: [{
      label: 'Saldo (R$ Mi)', data: saldosMi,
      backgroundColor: emSort.map(e => getCorSt(e[0])+'cc'),
      borderColor: emSort.map(e => getCorSt(e[0])),
      borderWidth:1.5, borderRadius:4, yAxisID:'y'
    }] },
    options: {
      ...CHART_DEFAULTS,
      responsive: true, maintainAspectRatio: false,
      layout:{ padding:{ bottom:4 } }, interaction:{ mode:'index', intersect:false },
      plugins: { ...CHART_DEFAULTS.plugins, legend:{ display:false },
        tooltip:{ callbacks:{ label: ctx => 'Saldo: R$ '+ctx.raw+' Mi',
          afterBody: items => items?.length ? '% PL: '+pctPL[items[0].dataIndex]+'%' : '' } } },
      scales: {
        x: { ...CHART_DEFAULTS.scales.x, ticks:{ color:'#718096', font:{ size:11, family:"'DM Mono',monospace" }, maxRotation:0, minRotation:0, autoSkip:false } },
        y: { ...CHART_DEFAULTS.scales.y, type:'linear', position:'left', beginAtZero:true,
          ticks:{ ...CHART_DEFAULTS.scales.y.ticks, callback: v => 'R$ '+v+' Mi' } }
      }
    }
  });

  const byClasse = {};
  ativos.forEach(a => { byClasse[a.classe||'Outros'] = (byClasse[a.classe||'Outros']||0)+(a.saldo||0); });
  const clSort = Object.entries(byClasse).sort((a,b) => b[1]-a[1]);
  mk('homeChartClasse', {
    type:'doughnut',
    data:{ labels: clSort.map(e=>e[0]), datasets:[{
      data: clSort.map(e=>+((e[1]/totalCred)*100).toFixed(1)),
      backgroundColor: clSort.map((_,i)=>COLORS[i%COLORS.length]+'ee'),
      borderColor:'#ffffff', borderWidth:2
    }] },
    options:{ ...DOUGHNUT_OPTS,
      plugins:{ ...DOUGHNUT_OPTS.plugins, tooltip:{ callbacks:{ label: c => {
        const mi = (clSort[c.dataIndex][1]/1e6).toFixed(2);
        return c.label+': '+c.raw+'% — R$ '+mi+' Mi';
      } } } }
    }
  });

  const top5Corp = RANK_CORP.slice(0,5);
  document.getElementById('homeTop5Corp').innerHTML = top5Corp.map((rankInfo, i) => {
    const em    = rankInfo.empresa || '—';
    const setor = rankInfo.setor || '—';
    const saldo = ativos.filter(a=>a.emissor===em).reduce((s,a)=>s+(a.saldo||0),0);
    return `<div style="display:flex;flex-direction:column;gap:0;margin-bottom:8px;padding:10px 12px;border-radius:8px;border:1px solid transparent;background:transparent;transition:background .15s;border:1px solid transparent;">
      <div style="display:flex;align-items:center;gap:12px;padding:0;cursor:pointer;transition:background .15s;"
        onmouseover="this.style.background='rgba(0,103,123,.05)';this.parentElement.style.borderColor='rgba(0,103,123,.15)'"
        onmouseout="this.style.background='';this.parentElement.style.borderColor='transparent'"
        onclick="homeSelectEmp('${em}')">
        <span class="rank-num">${i+1}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${em}</div>
          <div style="font-size:10px;color:var(--text3);margin-top:2px">${setor}</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
          ${badgeRating(rankInfo.ratingDouro||'—')}
          ${badgeStatus(rankInfo.status||'—')}
          <div style="font-family:var(--mono);font-size:11px;color:var(--text2)">${saldo>0?fmtBRL(saldo):'—'}</div>
        </div>
        <div style="font-size:10px;color:var(--teal);font-weight:600;white-space:nowrap">→</div>
      </div>
    </div>`;
  }).join('');

  const top5Bancos = RANK_BANCOS.slice(0,5);
  document.getElementById('homeTop5Bancos').innerHTML = top5Bancos.map((rankInfo, i) => {
    const em    = rankInfo.empresa || '—';
    const saldo = ativos.filter(a=>a.emissor===em).reduce((s,a)=>s+(a.saldo||0),0);
    return `<div style="display:flex;flex-direction:column;gap:0;margin-bottom:8px;padding:10px 12px;border-radius:8px;border:1px solid transparent;background:transparent;transition:background .15s;border:1px solid transparent;">
      <div style="display:flex;align-items:center;gap:12px;padding:0;cursor:pointer;transition:background .15s;"
        onmouseover="this.style.background='rgba(0,103,123,.05)';this.parentElement.style.borderColor='rgba(0,103,123,.15)'"
        onmouseout="this.style.background='';this.parentElement.style.borderColor='transparent'"
        onclick="homeSelectBanco('${em}')">
        <span class="rank-num">${i+1}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${em}</div>
          <div style="font-size:10px;color:var(--text3);margin-top:2px">${rankInfo.tipo||'Banco'}</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
          ${badgeRating(rankInfo.ratingDouro||'—')}
          ${badgeStatus(rankInfo.status||'—')}
          <div style="font-family:var(--mono);font-size:11px;color:var(--text2)">${saldo>0?fmtBRL(saldo):'—'}</div>
        </div>
        <div style="font-size:10px;color:var(--teal);font-weight:600;white-space:nowrap">→</div>
      </div>
    </div>`;
  }).join('');

  const atvsPerf = Object.keys(PERF_DATA.ativos || {});
  if (atvsPerf.length) {
    const dsPerf = atvsPerf.map((a,i) => ({
      label: a, data: PERF_DATA.ativos[a].retorno_acum.map(v=>+(v*100).toFixed(2)),
      borderColor: COLORS[i%COLORS.length], backgroundColor:'transparent',
      tension:.3, pointRadius:0, borderWidth:1.8
    }));
    mk('homeChartPerf', {
      type:'line',
      data:{ labels: PERF_DATA.datas, datasets: dsPerf },
      options:{
        ...CHART_DEFAULTS,
        ..._CROSSHAIR_OPTS,
        plugins:{ ...CHART_DEFAULTS.plugins, ..._CROSSHAIR_OPTS.plugins,
          legend:{ display:true, position:'bottom', labels:{ color:'#718096', font:{ size:9 }, boxWidth:8, padding:10 } } },
        scales:{
          x:{ ...CHART_DEFAULTS.scales.x, ticks:{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:6 } },
          y:{ ...CHART_DEFAULTS.scales.y, ticks:{ ...CHART_DEFAULTS.scales.y.ticks, callback: v=>v.toFixed(1)+'%' } }
        }
      }
    });
  }
}

// ── COMPOSIÇÃO ─────────────────────────────────────────────────────────────
function buildComposicao() {
  const ativos = getFiltered();
const carteiraSelecionada =
  document.getElementById('carteiraFilter')?.value || '';
const plFiltrado =
  carteiraSelecionada
    ? (PL_POR_CARTEIRA[carteiraSelecionada] || 0)
    : PL_TOTAL;
const totalCredito =
  ativos.reduce((s,a) => s + (a.saldo || 0), 0);
  // Cache para o filtro de barra
  _cachedAtivos    = ativos;
  _cachedTotalCred = totalCredito;
  _cachedPLFilt    = plFiltrado;
  _emFiltroBar     = null; // reset ao reconstruir composição
  _setorFiltroDonut = null;
  const STATUS_ANALISE  = ['Em análise', 'Watch', 'Monitoramento'];
  const STATUS_COBERTOS = ['Aprovado', 'Reprovado', ...STATUS_ANALISE];
  const aprovados    = ativos.filter(a => a.Status === 'Aprovado').reduce((s,a) => s+(a.saldo||0), 0);
  const reprovados   = ativos.filter(a => a.Status === 'Reprovado').reduce((s,a) => s+(a.saldo||0), 0);
  const analise      = ativos.filter(a => STATUS_ANALISE.includes(a.Status)).reduce((s,a) => s+(a.saldo||0), 0);
  const semCobertura = ativos.filter(a => !STATUS_COBERTOS.includes(a.Status)).reduce((s,a) => s+(a.saldo||0), 0);
  const uniqueTickers = new Set(ativos.map(a => a.ticker).filter(Boolean)).size;
  document.getElementById('kpiRow').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Saldo Crédito Privado</div><div class="kpi-value">${fmtBRL(totalCredito)}</div><div class="kpi-sub">${ativos.length} posições · ${uniqueTickers} tickers</div></div>
    <div class="kpi-card"><div class="kpi-label">% do PL Total</div><div class="kpi-value">${plFiltrado>0?(totalCredito/plFiltrado*100).toFixed(1):0}%</div><div class="kpi-sub">PL: ${fmtBRL(plFiltrado)}</div></div>
    <div class="kpi-card"><div class="kpi-label">Aprovados</div><div class="kpi-value">${totalCredito>0?(aprovados/totalCredito*100).toFixed(1):0}%</div><span class="kpi-badge green">${fmtBRL(aprovados)}</span></div>
    <div class="kpi-card"><div class="kpi-label">Em Análise / Watch</div><div class="kpi-value">${totalCredito>0?(analise/totalCredito*100).toFixed(1):0}%</div><span class="kpi-badge gold">${fmtBRL(analise)}</span></div>
    <div class="kpi-card"><div class="kpi-label">Reprovados</div><div class="kpi-value">${totalCredito>0?(reprovados/totalCredito*100).toFixed(1):0}%</div><span class="kpi-badge red">${fmtBRL(reprovados)}</span></div>
    <div class="kpi-card"><div class="kpi-label">Sem Cobertura</div><div class="kpi-value">${totalCredito>0?(semCobertura/totalCredito*100).toFixed(1):0}%</div><span class="kpi-badge" style="background:rgba(113,128,150,.12);color:var(--text3)">${fmtBRL(semCobertura)}</span></div>
    <div class="kpi-card"><div class="kpi-label">Duration Média</div><div class="kpi-value">${(ativos.reduce((s,a)=>s+((a.duration||0)*(a.saldo||0)),0)/Math.max(totalCredito,1)).toFixed(1)}a</div><div class="kpi-sub">Ponderada por saldo</div></div>`;

  const byE = {};
  ativos.forEach(a => {
    const em = a.emissor || 'Sem emissor';
    byE[em] = (byE[em]||0) + (a.saldo||0);
  });
  const emSort   = Object.entries(byE).sort((a,b) => b[1]-a[1]);
  const emSort10 = emSort.slice(0, 10);
  const saldosMi = emSort10.map(e => +((e[1]/1e6).toFixed(2)));
  const pctPL    = emSort10.map(e => plFiltrado > 0 ? +((e[1]/plFiltrado)*100).toFixed(2) : 0);

  const chipVer = document.getElementById('emissorVerTodosChip');
  if (chipVer) {
    if (emSort.length > 10) {
      chipVer.style.display = 'block';
      chipVer.textContent = `+ ${emSort.length - 10} outros emissores — ver todos na tabela ↓`;
    } else { chipVer.style.display = 'none'; }
  }

const BAR_MIN_PX = 80;
const CHART_H    = 320;
const larguraGrafico = Math.max(emSort10.length * BAR_MIN_PX, 600);

const inner = document.getElementById('chartEmissorWrap');
if (inner) {
  inner.style.minWidth = larguraGrafico + 'px';
  inner.style.maxWidth = 'none';
  const chartDiv = inner.querySelector('div');
  if (chartDiv) { chartDiv.style.width = larguraGrafico + 'px'; chartDiv.style.height = CHART_H + 'px'; }
}
const canvasEmissor = document.getElementById('chartEmissor');
if (canvasEmissor) { canvasEmissor.width = larguraGrafico; canvasEmissor.height = CHART_H; canvasEmissor.style.width = larguraGrafico + 'px'; canvasEmissor.style.height = CHART_H + 'px'; }

  const legendaStatus = [
    { label:'Aprovado',   cor:'#00677b' },
    { label:'Em análise', cor:'#b69d74' },
    { label:'Reprovado',  cor:'#d94141' },
  ];

  mk('chartEmissor', {
    type: 'bar',
    data: {
      labels: emSort10.map(e => e[0]),
      datasets: [
        {
          type:            'bar',
          label:           'Saldo (R$ Mi)',
          data:            saldosMi,
          backgroundColor: emSort10.map(e => getCorStatus(e[0]) + 'cc'),
          borderColor:     emSort10.map(e => getCorStatus(e[0])),
          borderWidth:     1.5,
          borderRadius:    4,
          yAxisID:         'y',
          order:           1,
          barThickness:    'flex',
          maxBarThickness: 64
        },
        ...legendaStatus.map(ls => ({
          type:            'bar',
          label:           ls.label,
          data:            [],
          backgroundColor: ls.cor + 'cc',
          borderColor:     ls.cor,
          borderWidth:     1.5,
          yAxisID:         'y',
          order:           2
        }))
      ]
    },
    options: {
      ...CHART_DEFAULTS,
      responsive: false,
      maintainAspectRatio: false,
      layout: { padding: { bottom: 8 } },
      interaction: { mode:'index', intersect:false },
      onClick: (evt, elements) => {
        if (!elements || !elements.length) return;
        const clickedLabel = emSort10[elements[0].index][0];
        _emFiltroBar = _emFiltroBar === clickedLabel ? null : clickedLabel;
        const chart = Chart.getChart('chartEmissor');
        if (chart) {
          chart.data.datasets[0].backgroundColor = emSort10.map(e =>
            !_emFiltroBar || e[0] === _emFiltroBar ? getCorStatus(e[0])+'cc' : getCorStatus(e[0])+'33'
          );
          chart.data.datasets[0].borderColor = emSort10.map(e =>
            !_emFiltroBar || e[0] === _emFiltroBar ? getCorStatus(e[0]) : getCorStatus(e[0])+'55'
          );
          chart.update('none');
        }
        _renderTbodyAtivos();
      },
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: {
          display:  true,
          position: 'top',
          labels: {
            color:    '#718096',
            font:     { size:11, family:"'Montserrat', sans-serif" },
            boxWidth: 12,
            padding:  16,
            filter:   (item) => item.text !== 'Saldo (R$ Mi)'
          }
        },
        tooltip: {
          filter: (ctx) => ctx.datasetIndex === 0,
          callbacks: {
            label:     ctx => `Saldo: R$${ctx.raw} Mi`,
            afterBody: items => {
              if (!items || !items.length) return '';
              const idx = items[0].dataIndex;
              const pct = pctPL[idx];
              return pct != null ? `% PL Total: ${pct}%` : '';
            }
          }
        }
      },
      scales: {
        x: {
          ...CHART_DEFAULTS.scales.x,
          ticks: {
            color:       '#718096',
            font:        { size:9, family:"'DM Mono', monospace" },
            maxRotation: 45,
            minRotation: 30,
            autoSkip:    false
          }
        },
        y: {
          ...CHART_DEFAULTS.scales.y,
          type:        'linear',
          position:    'left',
          beginAtZero: true,
          title: { display:true, text:'Saldo (R$ Mi)', color:'#718096', font:{ size:10 } },
          ticks: { ...CHART_DEFAULTS.scales.y.ticks, callback: v => `R$ ${v} Mi` }
        },
        y2: {
          type:        'linear',
          position:    'right',
          beginAtZero: true,
          grid:        { drawOnChartArea: false },
          title: { display:true, text:'% PL Total', color:'#718096', font:{ size:10 } },
          ticks: { color:'#718096', font:{ size:10, family:"'DM Mono', monospace" }, callback: v => v + '%' }
        }
      }
    }
  });

  // Setor doughnut
  const byS = {};
  ativos.forEach(a => { byS[a.setor||'N/D'] = (byS[a.setor||'N/D']||0) + (a.saldo||0); });
  const sSort = Object.entries(byS).sort((a,b) => b[1]-a[1]);
  mk('chartSetor', {
    type: 'doughnut',
    data: {
      labels: sSort.map(e => e[0]),
      datasets: [{
        data:            sSort.map(e => +(e[1]/totalCredito*100).toFixed(1)),
        backgroundColor: sSort.map((_,i) => COLORS[i%COLORS.length]+'ee'),
        borderColor:     '#ffffff',
        borderWidth:     2
      }]
    },
    options: {
      ...DOUGHNUT_OPTS,
      onClick: (evt, elements) => {
        const chart = Chart.getChart('chartSetor');
        if (!chart || !elements || !elements.length) {
          _setorFiltroDonut = null;
          if (chart) { chart.data.datasets[0].backgroundColor = sSort.map((_,i)=>COLORS[i%COLORS.length]+'ee'); chart.data.datasets[0].borderWidth=2; chart.update('none'); }
          _renderBarEmissor(); _renderTbodyAtivos(); return;
        }
        const idx = elements[0].index;
        const setor = sSort[idx][0];
        if (_setorFiltroDonut === setor) {
          _setorFiltroDonut = null;
          chart.data.datasets[0].backgroundColor = sSort.map((_,i)=>COLORS[i%COLORS.length]+'ee');
          chart.data.datasets[0].borderWidth = 2;
        } else {
          _setorFiltroDonut = setor;
          chart.data.datasets[0].backgroundColor = sSort.map((e,i)=>
            e[0]===setor ? '#b69d74ee' : COLORS[i%COLORS.length]+'44'
          );
          chart.data.datasets[0].borderWidth = sSort.map(e=>e[0]===setor?3:1);
        }
        chart.update('none');
        _emFiltroBar = null;
        _renderBarEmissor();
        _renderTbodyAtivos();
      },
      plugins: { ...DOUGHNUT_OPTS.plugins, tooltip: { callbacks: { label: c => {
        const mi = (sSort[c.dataIndex][1]/1e6).toFixed(2);
        return `${c.label}: ${c.raw}% — R$ ${mi} Mi`;
      } } } }
    }
  });

  _renderTbodyAtivos();
}

// ── RATING ─────────────────────────────────────────────────────────────────
function buildRating() {
  const carteiraSelecionada = document.getElementById('carteiraFilter')?.value || '';
  const plFiltrado = carteiraSelecionada ? (PL_POR_CARTEIRA[carteiraSelecionada] || 0) : PL_TOTAL;
  const ativos       = getFiltered();
  const totalCredito = ativos.reduce((s,a) => s+(a.saldo||0), 0);
  _cachedAtivos    = ativos;
  _cachedTotalCred = totalCredito;
  _cachedPLFilt    = plFiltrado;
  _ratingFilter    = { classe: null, ratingMkt: null, ratingDouro: null };
  const byClasse={}, byRMkt={}, byRD={};
  ativos.forEach(a => {
    byClasse[a.classe||'Outros']             = (byClasse[a.classe||'Outros']||0)             + (a.saldo||0);
    byRMkt[a['Rating base S&P']||'N/D']      = (byRMkt[a['Rating base S&P']||'N/D']||0)      + (a.saldo||0);
    byRD[a['Rating Douro']||'N/D']           = (byRD[a['Rating Douro']||'N/D']||0)           + (a.saldo||0);
  });
  const donut = (id, obj) => {
    const e = Object.entries(obj).sort((a,b) => b[1]-a[1]);
    mk(id, {
      type:'doughnut',
      data:{ labels:e.map(x=>x[0]), datasets:[{ data:e.map(x=>+(x[1]/totalCredito*100).toFixed(1)), backgroundColor:e.map((_,i)=>COLORS[i%COLORS.length]+'ee'), borderColor:'#ffffff', borderWidth:2 }]},
      options:{ ...DOUGHNUT_OPTS,
        onClick: (evt, elements) => {
          const chart = Chart.getChart(id);
          if (!chart) return;
          if (!elements || !elements.length) {
            _clearRatingFiltro();
            return;
          }
          const idx = elements[0].index;
          const label = e[idx][0];
          const selected = id === 'chartClasse' ? _ratingFilter.classe : id === 'chartRatingMkt' ? _ratingFilter.ratingMkt : _ratingFilter.ratingDouro;
          const same = selected === label;
          _ratingFilter = { classe:null, ratingMkt:null, ratingDouro:null };
          if (!same) {
            if (id === 'chartClasse') _ratingFilter.classe = label;
            if (id === 'chartRatingMkt') _ratingFilter.ratingMkt = label;
            if (id === 'chartRatingDouro') _ratingFilter.ratingDouro = label;
          }
          chart.data.datasets[0].backgroundColor = e.map((item,i) => {
            if (same) return COLORS[i%COLORS.length]+'ee';
            return item[0] === label ? COLORS[i%COLORS.length]+'ee' : COLORS[i%COLORS.length]+'44';
          });
          chart.update('none');
          _renderTbodyAtivosRating();
        },
        plugins:{ ...DOUGHNUT_OPTS.plugins, tooltip:{ callbacks:{ label: c => {
          const mi = (e[c.dataIndex][1]/1e6).toFixed(2);
          return `${c.label}: ${c.raw}% — R$ ${mi} Mi`;
        } } } }
      }
    });
  };
  donut('chartClasse',      byClasse);
  donut('chartRatingMkt',   byRMkt);
  donut('chartRatingDouro', byRD);
  _renderTbodyAtivosRating();

}
// ── DADOS FINANCEIROS ─────────────────────────────────────────────────────
const finSelecionadas = new Set();
let finInicializado = false;
let _timelineInitialized = false;
let _finAllDates = [];
let _finDateMin = 0;
let _finDateMax = Infinity;

function finRangeInit() {
  const allTs = [];
  Object.values(FIN_SERIES).forEach(d => {
    (d.datas || []).forEach(dt => {
      const ts = parseBRDate(dt);
      if (ts) allTs.push(ts);
    });
  });
  _finAllDates = [...new Set(allTs)].sort((a,b) => a-b);
  if (!_finAllDates.length) return;
  const rMin = document.getElementById('finRangeMin');
  const rMax = document.getElementById('finRangeMax');
  if (!rMin || !rMax) return;
  const N = _finAllDates.length - 1;
  rMin.max = N; rMin.value = 0;
  rMax.max = N; rMax.value = N;
  _finDateMin = _finAllDates[0];
  _finDateMax = _finAllDates[N];
  _finRangeLabel(); _finRangeFill();
}

function finRangeUpdate(ev) {
  const rMin = document.getElementById('finRangeMin');
  const rMax = document.getElementById('finRangeMax');
  if (!rMin || !rMax) return;
  let vMin = parseInt(rMin.value), vMax = parseInt(rMax.value);
  if (vMin >= vMax) {
    if (ev && ev.target === rMin) { rMin.value = Math.max(0, vMax - 1); vMin = parseInt(rMin.value); }
    else { rMax.value = Math.min(parseInt(rMax.max), vMin + 1); vMax = parseInt(rMax.value); }
  }
  _finDateMin = _finAllDates[vMin] || 0;
  _finDateMax = _finAllDates[vMax] || Infinity;
  _finRangeLabel(); _finRangeFill();
  buildFinanceiros();
}

function _finRangeLabel() {
  const label = document.getElementById('finDateRangeLabel');
  if (!label || !_finAllDates.length) return;
  const rMin = document.getElementById('finRangeMin');
  const rMax = document.getElementById('finRangeMax');
  const vMin = parseInt(rMin?.value || 0);
  const vMax = parseInt(rMax?.value || _finAllDates.length - 1);
  const fmt = ts => new Date(ts).getFullYear();
  label.textContent = fmt(_finAllDates[vMin]) + ' – ' + fmt(_finAllDates[vMax]);
}

function _finRangeFill() {
  const rMin = document.getElementById('finRangeMin');
  const rMax = document.getElementById('finRangeMax');
  const fill = document.getElementById('finRangeFill');
  if (!fill || !rMin || !rMax) return;
  const total = parseInt(rMin.max) || 1;
  const l = (parseInt(rMin.value) / total) * 100;
  const r = (parseInt(rMax.value) / total) * 100;
  fill.style.left = l + '%';
  fill.style.width = (r - l) + '%';
}

// ── FUNDAMENTOS DATE RANGE ──────────────────────────────────────────────────
let _fundAllDates = [];
let _fundDateMin = 0;
let _fundDateMax = Infinity;

function fundRangeInit() {
  const allTs = [];
  Object.values(FIN_SERIES).forEach(d => {
    (d.datas || []).forEach(dt => {
      const ts = parseBRDate(dt);
      if (ts) allTs.push(ts);
    });
  });
  _fundAllDates = [...new Set(allTs)].sort((a,b) => a-b);
  if (!_fundAllDates.length) return;
  const rMin = document.getElementById('fundRangeMin');
  const rMax = document.getElementById('fundRangeMax');
  if (!rMin || !rMax) return;
  const N = _fundAllDates.length - 1;
  rMin.max = N; rMin.value = 0;
  rMax.max = N; rMax.value = N;
  _fundDateMin = _fundAllDates[0];
  _fundDateMax = _fundAllDates[N];
  _fundRangeLabel(); _fundRangeFill();
}

function fundRangeUpdate(ev) {
  const rMin = document.getElementById('fundRangeMin');
  const rMax = document.getElementById('fundRangeMax');
  if (!rMin || !rMax) return;
  let vMin = parseInt(rMin.value), vMax = parseInt(rMax.value);
  if (vMin >= vMax) {
    if (ev && ev.target === rMin) { rMin.value = Math.max(0, vMax - 1); vMin = parseInt(rMin.value); }
    else { rMax.value = Math.min(parseInt(rMax.max), vMin + 1); vMax = parseInt(rMax.value); }
  }
  _fundDateMin = _fundAllDates[vMin] || 0;
  _fundDateMax = _fundAllDates[vMax] || Infinity;
  _fundRangeLabel(); _fundRangeFill();
  buildFundamentos();
}

function _fundRangeLabel() {
  const label = document.getElementById('fundDateRangeLabel');
  if (!label || !_fundAllDates.length) return;
  const rMin = document.getElementById('fundRangeMin');
  const rMax = document.getElementById('fundRangeMax');
  const vMin = parseInt(rMin?.value || 0);
  const vMax = parseInt(rMax?.value || _fundAllDates.length - 1);
  const fmt = ts => new Date(ts).getFullYear();
  label.textContent = fmt(_fundAllDates[vMin]) + ' – ' + fmt(_fundAllDates[vMax]);
}

function _fundRangeFill() {
  const rMin = document.getElementById('fundRangeMin');
  const rMax = document.getElementById('fundRangeMax');
  const fill = document.getElementById('fundRangeFill');
  if (!fill || !rMin || !rMax) return;
  const total = parseInt(rMin.max) || 1;
  const l = (parseInt(rMin.value) / total) * 100;
  const r = (parseInt(rMax.value) / total) * 100;
  fill.style.left = l + '%';
  fill.style.width = (r - l) + '%';
}

function timelineInitSels() {
  if (_timelineInitialized) return;
  _timelineInitialized = true;
  const sel = document.getElementById('timelineCompanyFilter');
  if (!sel) return;
  const companies = [...new Set(FATOS_RJ.map(e => e.empresa).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'pt-BR'));
  sel.innerHTML = '<option value="">Todas as empresas</option>' + companies.map(c => `<option value="${htmlEncode(c)}">${htmlEncode(c)}</option>`).join('');
}

let _timelineDesign = 6;
let _tl10Anim = null;
function setTimelineDesign(n) {
  _timelineDesign = n;
  if (_tl10Anim) { cancelAnimationFrame(_tl10Anim); _tl10Anim = null; }
  buildTimeline();
}
function buildTimeline() {
  timelineInitSels();
  const company = document.getElementById('timelineCompanyFilter')?.value || '';
  const query = (document.getElementById('timelineSearch')?.value || '').toLowerCase().trim();
  let items = FATOS_RJ.filter(item => {
    if (company && item.empresa !== company) return false;
    if (!query) return true;
    return (item.fato||'').toLowerCase().includes(query)||(item.detalhes||'').toLowerCase().includes(query);
  }).map(item => ({...item, ts: parseBRDate(item.data)||0})).sort((a,b)=>a.ts-b.ts);
  const wrap = document.getElementById('timelineList');
  const cnt = document.getElementById('timelineCount');
  if (!wrap||!cnt) return;
  cnt.textContent = items.length ? `${items.length} evento(s)` : '0 eventos';
  if (!items.length) {
    wrap.innerHTML = '<div style="padding:18px;color:var(--text3);background:var(--surface2);border:1px solid var(--border);border-radius:14px">Nenhum evento encontrado.</div>';
    return;
  }
  if (_tl10Anim) { cancelAnimationFrame(_tl10Anim); _tl10Anim = null; }
  switch(_timelineDesign) {
    case 1: _tlD1(wrap,items); break;
    case 2: _tlD2(wrap,items); break;
    case 3: _tlD3(wrap,items); break;
    case 4: _tlD4(wrap,items); break;
    case 5: _tlD5(wrap,items); break;
    case 6: _tlD6(wrap,items); break;
    case 7: _tlD7(wrap,items); break;
    case 8: _tlD8(wrap,items); break;
    case 9: _tlD9(wrap,items); break;
    case 10: _tlD10(wrap,items); break;
    default: _tlD1(wrap,items);
  }
}
/* ── Design 1: Clássico Vertical ── */
function _tlD1(wrap,items) {
  wrap.className='';
  wrap.innerHTML='<div class="tl1-container">'+items.map(item=>`
<div class="tl1-event">
  <span class="tl1-date">${formatDateBR(item.data)}</span>
  <div style="display:flex;flex-direction:column;align-items:center;padding-top:14px;position:relative;z-index:1"><div class="tl1-dot"></div></div>
  <div class="tl1-card">
    <div class="tl1-fato">${htmlEncode(item.fato||'—')}</div>
    <div class="tl1-empresa">${htmlEncode(item.empresa||'—')}</div>
    <div class="tl1-detalhe">${htmlEncode(item.detalhes||'—')}</div>
  </div>
</div>`).join('')+'</div>';
}
/* ── Design 2: Accordion por empresa ── */
function _tlD2(wrap,items) {
  wrap.className='';
  const byEmp={};
  items.forEach(it=>{ if(!byEmp[it.empresa||'—']) byEmp[it.empresa||'—']=[]; byEmp[it.empresa||'—'].push(it); });
  let html='';
  Object.keys(byEmp).sort((a,b)=>a.localeCompare(b,'pt-BR')).forEach((emp,i)=>{
    const evts=byEmp[emp];
    html+=`<div class="tl2-company${i===0?' open':''}" id="tl2co_${i}">
<div class="tl2-header" onclick="(()=>{const el=document.getElementById('tl2co_${i}');el.classList.toggle('open')})()">
  <span class="tl2-hname">${htmlEncode(emp)}</span>
  <span class="tl2-hbadge">${evts.length}</span>
  <svg class="tl2-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
</div>
<div class="tl2-body"><div class="tl2-inner">
${evts.map(it=>`<div class="tl2-item">
  <div class="tl2-idate">${formatDateBR(it.data)}</div>
  <div class="tl2-ifato">${htmlEncode(it.fato||'—')}</div>
  <div class="tl2-idet">${htmlEncode(it.detalhes||'—')}</div>
</div>`).join('')}
</div></div></div>`;
  });
  wrap.innerHTML=html;
}
/* ── Design 3: Kanban por fase ── */
function _tlD3(wrap,items) {
  wrap.className='';
  const COLS=[
    {id:'rj',label:'Pedido RJ',kw:['pedido','requerimento','ajuiz']},
    {id:'def',label:'Deferimento',kw:['deferimento','deferida','deferido']},
    {id:'plan',label:'Plano',kw:['plano','aprovação','aprovado','apresentação']},
    {id:'hom',label:'Homologação',kw:['homologação','homologado']},
    {id:'enc',label:'Encerrado',kw:['encerramento','encerrado','extinção','extinta']},
    {id:'out',label:'Outros',kw:[]}
  ];
  const buckets={};
  COLS.forEach(c=>{buckets[c.id]=[];});
  items.forEach(it=>{
    const txt=((it.fato||'')+' '+(it.detalhes||'')).toLowerCase();
    let placed=false;
    for(let i=0;i<COLS.length-1;i++) {
      if(COLS[i].kw.some(k=>txt.includes(k))) { buckets[COLS[i].id].push(it); placed=true; break; }
    }
    if(!placed) buckets['out'].push(it);
  });
  wrap.innerHTML='<div class="tl3-board">'+COLS.map(col=>`
<div class="tl3-col">
  <div class="tl3-colhead">${col.label} <span style="font-weight:400;opacity:.6">(${buckets[col.id].length})</span></div>
  ${buckets[col.id].map(it=>`<div class="tl3-card">
    <div class="tl3-cname">${htmlEncode(it.empresa||'—')}</div>
    <div class="tl3-cdate">${formatDateBR(it.data)}</div>
    <div class="tl3-cdet">${htmlEncode(it.detalhes||'—')}</div>
  </div>`).join('')}
</div>`).join('')+'</div>';
}
/* ── Design 4: Heatmap calendário ── */
function _tlD4(wrap,items) {
  wrap.className='';
  const MNAMES=['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ'];
  const byYM={};
  items.forEach(it=>{
    const d=parseBRDate(it.data);
    if(!d) return;
    const dt=new Date(d);
    const k=`${dt.getFullYear()}-${dt.getMonth()}`;
    if(!byYM[k]) byYM[k]=[];
    byYM[k].push(it);
  });
  const years=[...new Set(items.map(it=>{const d=parseBRDate(it.data);return d?new Date(d).getFullYear():null;}).filter(Boolean))].sort();
  if(!years.length){wrap.innerHTML='<p style="color:var(--text3)">Sem dados com data válida.</p>';return;}
  let selKey=null;
  const maxCount=Math.max(1,...Object.values(byYM).map(a=>a.length));
  function lvl(n){if(!n)return 0;const r=n/maxCount;return r<.25?1:r<.5?2:r<.75?3:4;}
  function render(){
    let html='<div style="margin-bottom:16px">';
    html+='<div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:16px;">';
    years.forEach(yr=>{
      for(let m=0;m<12;m++){
        const k=`${yr}-${m}`;
        const n=(byYM[k]||[]).length;
        const l=lvl(n);
        const isActive=selKey===k;
        html+=`<div class="tl4-cell tl4-c${l}${isActive?' active':''}" onclick="_tl4sel('${k}')" title="${yr} ${MNAMES[m]}">
          <span class="tl4-cmon">${MNAMES[m]}</span>
          <span class="tl4-cyear">${yr}</span>
          <span class="tl4-cnum">${n||'·'}</span>
        </div>`;
      }
    });
    html+='</div>';
    html+='<div class="tl4-detail" id="tl4detail">';
    if(!selKey){
      html+='<div style="color:var(--text3);font-size:12px;text-align:center;padding:12px">Clique em um mês para ver os eventos</div>';
    } else {
      const evts=byYM[selKey]||[];
      const [yr,m]=selKey.split('-');
      html+=`<div class="tl4-detail-title">${MNAMES[parseInt(m)]} ${yr} — ${evts.length} evento(s)</div>`;
      html+=evts.map(it=>`<div class="tl4-ditem">
        <div class="tl4-dname">${htmlEncode(it.empresa||'—')}</div>
        <div class="tl4-dfato">${htmlEncode(it.fato||'—')}</div>
        <div class="tl4-ddet">${htmlEncode(it.detalhes||'—')}</div>
      </div>`).join('');
    }
    html+='</div></div>';
    wrap.innerHTML=html;
  }
  window._tl4sel=function(k){selKey=(selKey===k)?null:k;render();};
  render();
}
/* ── Design 5: Multi-track horizontal ── */
function _tlD5(wrap,items) {
  wrap.className='';
  const tracks={};
  items.forEach(it=>{const e=it.empresa||'—';if(!tracks[e])tracks[e]=[];tracks[e].push(it);});
  const allTs=items.map(it=>it.ts).filter(Boolean);
  if(!allTs.length){wrap.innerHTML='<p style="color:var(--text3)">Sem dados.</p>';return;}
  const tMin=Math.min(...allTs), tMax=Math.max(...allTs);
  const span=tMax-tMin||1;
  const W=900;
  function xPct(ts){return((ts-tMin)/span*W).toFixed(1)+'px';}
  const years=[...new Set(items.map(it=>{const d=parseBRDate(it.data);return d?new Date(d).getFullYear():null;}).filter(Boolean))].sort();
  let html=`<div class="tl5-outer" style="max-height:480px;overflow-y:auto">
<div style="min-width:${W+140}px">
<div class="tl5-axis-row">
  <div class="tl5-axis-label">Empresa</div>
  <div class="tl5-axis-ticks" style="position:relative;height:100%;min-width:${W}px">
    ${years.map(yr=>{
      const d=new Date(yr,0,1);
      const t=d.getTime();
      if(t<tMin-86400000*180||t>tMax+86400000*180) return '';
      const x=((t-tMin)/span*W).toFixed(1);
      return `<div class="tl5-tick-mark" style="left:${x}px"></div><div class="tl5-tick-label" style="left:${x}px">${yr}</div>`;
    }).join('')}
  </div>
</div>
${Object.keys(tracks).sort((a,b)=>a.localeCompare(b,'pt-BR')).map(emp=>`
<div class="tl5-track">
  <div class="tl5-track-name" title="${htmlEncode(emp)}">${htmlEncode(emp)}</div>
  <div class="tl5-track-events" style="min-width:${W}px">
    <div class="tl5-track-line"></div>
    ${tracks[emp].map(it=>{
      if(!it.ts) return '';
      const x=((it.ts-tMin)/span*W).toFixed(1);
      return `<div class="tl5-node-wrap" style="left:${x}px">
        <div class="tl5-node"></div>
        <div class="tl5-popup">
          <div class="tl5-popup-date">${formatDateBR(it.data)}</div>
          <div class="tl5-popup-fato">${htmlEncode(it.fato||'—')}</div>
          <div class="tl5-popup-det">${htmlEncode(it.detalhes||'—')}</div>
        </div>
      </div>`;
    }).join('')}
  </div>
</div>`).join('')}
</div></div>`;
  wrap.innerHTML=html;
}
/* ── Design 6: Glass Morphism ── */
function _tlD6(wrap,items) {
  wrap.className='';
  const MONTHS=['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ'];
  wrap.innerHTML='<div class="tl6-bg">'+items.map(item=>{
    const d=parseBRDate(item.data);
    const dt=d?new Date(d):null;
    const dd=dt?String(dt.getDate()).padStart(2,'0'):'—';
    const mm=dt?MONTHS[dt.getMonth()]:'';
    const yy=dt?dt.getFullYear():'';
    return `<div class="tl6-card">
  <div class="tl6-badge"><div class="tl6-bd">${dd}</div><div class="tl6-bm">${mm}</div><div class="tl6-by">${yy}</div></div>
  <div>
    <div class="tl6-fato">${htmlEncode(item.fato||'—')}</div>
    <div class="tl6-empresa">${htmlEncode(item.empresa||'—')}</div>
    <div class="tl6-detalhe">${htmlEncode(item.detalhes||'—')}</div>
  </div>
</div>`;
  }).join('')+'</div>';
}
/* ── Design 7: Radial SVG ── */
function _tlD7(wrap,items) {
  wrap.className='';
  const total=items.length;
  const R=130, cx=160, cy=160, r=8;
  let selIdx=0;
  function renderSVG(){
    const pts=items.map((it,i)=>{
      const angle=(i/total)*2*Math.PI-Math.PI/2;
      return {x:cx+R*Math.cos(angle),y:cy+R*Math.sin(angle),i};
    });
    let svgLines=pts.map(p=>`<line x1="${cx}" y1="${cy}" x2="${p.x.toFixed(1)}" y2="${p.y.toFixed(1)}" stroke="rgba(0,103,123,0.18)" stroke-width="1"/>`).join('');
    let svgDots=pts.map(p=>{
      const active=p.i===selIdx;
      return `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${active?r+3:r}" fill="${active?'#00677b':'rgba(0,103,123,.5)'}" stroke="${active?'#b69d74':'rgba(0,103,123,.4)'}" stroke-width="${active?2:1}" style="cursor:pointer;transition:all .2s" onclick="_tl7sel(${p.i})"/>`;
    }).join('');
    const it=items[selIdx];
    const centerText=htmlEncode((it.empresa||'').split(' ').slice(0,2).join(' '));
    return `<svg viewBox="0 0 320 320" width="320" height="320" xmlns="http://www.w3.org/2000/svg">
  <circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="rgba(0,103,123,.15)" stroke-width="1" stroke-dasharray="4 3"/>
  <circle cx="${cx}" cy="${cy}" r="42" fill="rgba(0,103,123,.08)" stroke="rgba(0,103,123,.2)" stroke-width="1"/>
  ${svgLines}${svgDots}
  <text x="${cx}" y="${cy-8}" text-anchor="middle" font-size="11" font-weight="700" fill="#f5f5ef" font-family="inherit">${centerText}</text>
  <text x="${cx}" y="${cy+10}" text-anchor="middle" font-size="9" fill="rgba(245,245,239,.45)" font-family="inherit">${total} eventos</text>
</svg>`;
  }
  function renderList(){
    return items.map((it,i)=>`<div class="tl7-item${i===selIdx?' sel':''}" onclick="_tl7sel(${i})">
  <div class="tl7-idate">${formatDateBR(it.data)}</div>
  <div class="tl7-iname">${htmlEncode(it.empresa||'—')}</div>
  <div class="tl7-idet">${htmlEncode(it.fato||'—')}</div>
</div>`).join('');
  }
  function render(){
    wrap.innerHTML=`<div class="tl7-wrap">
  <div class="tl7-svg-wrap" id="tl7svgwrap">${renderSVG()}</div>
  <div>
    <div style="padding:10px 12px 14px;background:var(--surface2);border:1px solid var(--border);border-radius:10px;margin-bottom:12px">
      <div style="font-size:10px;color:var(--teal);font-family:var(--mono);font-weight:700;margin-bottom:4px">${formatDateBR(items[selIdx].data)}</div>
      <div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:4px">${htmlEncode(items[selIdx].empresa||'—')}</div>
      <div style="font-size:10px;color:var(--teal);font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">${htmlEncode(items[selIdx].fato||'—')}</div>
      <div style="font-size:12px;color:var(--text3);line-height:1.6">${htmlEncode(items[selIdx].detalhes||'—')}</div>
    </div>
    <div class="tl7-list">${renderList()}</div>
  </div>
</div>`;
  }
  window._tl7sel=function(i){selIdx=i;render();};
  render();
}
/* ── Design 8: Film Roll ── */
function _tlD8(wrap,items) {
  wrap.className='';
  const holes=Array.from({length:8},()=>'<div class="tl8-hole"></div>').join('');
  const left='<div class="tl8-sprocket">'+holes+'</div>';
  const right='<div class="tl8-sprocket">'+holes+'</div>';
  const frames=items.map((it,i)=>`<div class="tl8-frame">
  <div class="tl8-fnum">#${String(i+1).padStart(3,'0')}</div>
  <div class="tl8-date">${formatDateBR(it.data)}</div>
  <div class="tl8-empresa">${htmlEncode(it.empresa||'—')}</div>
  <div><span class="tl8-fato">${htmlEncode(it.fato||'—')}</span></div>
  <div class="tl8-det">${htmlEncode(it.detalhes||'—')}</div>
</div>`).join('');
  wrap.innerHTML=`<div class="tl8-strip">${left}${frames}${right}</div>`;
}
/* ── Design 9: Editorial / Jornal ── */
function _tlD9(wrap,items) {
  wrap.className='';
  const now=new Date();
  const articles=items.map(it=>{
    const d=parseBRDate(it.data);
    const isRecent=d&&(now-d)<1000*60*60*24*90;
    return `<div class="tl9-article">
  <div class="tl9-date">${isRecent?'<span class="tl9-breaking">Recente</span> ':''}${formatDateBR(it.data)}</div>
  <div class="tl9-headline">${htmlEncode(it.empresa||'—')}</div>
  <div class="tl9-byline">${htmlEncode(it.fato||'—')}</div>
  <div class="tl9-body">${htmlEncode(it.detalhes||'—')}</div>
</div>`;
  }).join('');
  wrap.innerHTML=`<div class="tl9-wrap">
<div class="tl9-masthead">
  <div class="tl9-pub">Douro Capital — Monitor de Crédito</div>
  <div class="tl9-title">Eventos de Recuperação Judicial</div>
  <div class="tl9-sub">${items.length} registros · Atualizado em ${new Date().toLocaleDateString('pt-BR')}</div>
</div>
<div class="tl9-cols">${articles}</div>
</div>`;
}
/* ── Design 10: Neural Network Canvas ── */
function _tlD10(wrap,items) {
  wrap.className='';
  wrap.innerHTML='<div class="tl10-wrap" id="tl10Outer"><canvas id="tl10Canvas"></canvas></div>';
  const tooltip=document.getElementById('tl10Tooltip');
  requestAnimationFrame(()=>{
    const outer=document.getElementById('tl10Outer');
    const canvas=document.getElementById('tl10Canvas');
    if(!canvas||!outer) return;
    const W=outer.clientWidth, H=outer.clientHeight||520;
    canvas.width=W; canvas.height=H;
    const ctx=canvas.getContext('2d');
    /* Assign positions: cluster by company */
    const companies=[...new Set(items.map(i=>i.empresa||'—'))];
    const compColor={};
    const palette=['#00677b','#b69d74','#4a9abe','#7c6c5a','#2a8f7a','#9b7ab0','#c47a3d','#5b8fb9','#a87c52','#3d9e8c'];
    companies.forEach((c,i)=>{compColor[c]=palette[i%palette.length];});
    /* Layout: companies in clusters arranged in a circle */
    const nodes=[];
    const clusterR=Math.min(W,H)*0.32;
    companies.forEach((emp,ci)=>{
      const ca=(ci/companies.length)*2*Math.PI;
      const cx=W/2+clusterR*Math.cos(ca), cy=H/2+clusterR*Math.sin(ca);
      const empItems=items.filter(it=>(it.empresa||'—')===emp);
      empItems.forEach((it,j)=>{
        const spread=30+empItems.length*8;
        const a=(j/Math.max(1,empItems.length))*2*Math.PI;
        nodes.push({
          x:cx+Math.cos(a)*spread*(0.4+Math.random()*0.6),
          y:cy+Math.sin(a)*spread*(0.4+Math.random()*0.6),
          vx:(Math.random()-.5)*0.3,
          vy:(Math.random()-.5)*0.3,
          r:6+Math.random()*3,
          item:it,
          color:compColor[emp],
          emp,
          ox:cx+Math.cos(a)*spread*(0.4+Math.random()*0.6),
          oy:cy+Math.sin(a)*spread*(0.4+Math.random()*0.6),
        });
      });
    });
    /* Particle stars */
    const stars=Array.from({length:60},()=>({x:Math.random()*W,y:Math.random()*H,r:Math.random()*1.2+.2,op:Math.random()}));
    let mouse={x:-999,y:-999};
    canvas.addEventListener('mousemove',e=>{
      const rect=canvas.getBoundingClientRect();
      mouse.x=e.clientX-rect.left; mouse.y=e.clientY-rect.top;
      let hit=null;
      nodes.forEach(n=>{ const dx=n.x-mouse.x,dy=n.y-mouse.y; if(Math.sqrt(dx*dx+dy*dy)<n.r+6) hit=n; });
      if(hit){
        tooltip.style.display='block';
        tooltip.style.left=(e.clientX+16)+'px';
        tooltip.style.top=(e.clientY-20)+'px';
        tooltip.innerHTML=`<div class="tl10-tt-date">${formatDateBR(hit.item.data)}</div><div class="tl10-tt-name">${htmlEncode(hit.item.empresa||'—')}</div><div class="tl10-tt-fato">${htmlEncode(hit.item.fato||'—')}</div><div class="tl10-tt-det">${htmlEncode(hit.item.detalhes||'—')}</div>`;
      } else { tooltip.style.display='none'; }
    });
    canvas.addEventListener('mouseleave',()=>{tooltip.style.display='none';});
    let frame=0;
    function draw(){
      _tl10Anim=requestAnimationFrame(draw);
      ctx.clearRect(0,0,W,H);
      /* stars */
      stars.forEach(s=>{
        s.op+=.008*(Math.random()-.5);
        s.op=Math.max(.05,Math.min(.7,s.op));
        ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,2*Math.PI);
        ctx.fillStyle=`rgba(245,245,239,${s.op.toFixed(2)})`;ctx.fill();
      });
      /* edges between same company nodes */
      for(let i=0;i<nodes.length;i++){
        for(let j=i+1;j<nodes.length;j++){
          if(nodes[i].emp!==nodes[j].emp) continue;
          const dx=nodes[i].x-nodes[j].x,dy=nodes[i].y-nodes[j].y;
          const dist=Math.sqrt(dx*dx+dy*dy);
          if(dist>160) continue;
          const alpha=(1-dist/160)*0.25;
          ctx.beginPath();ctx.moveTo(nodes[i].x,nodes[i].y);ctx.lineTo(nodes[j].x,nodes[j].y);
          ctx.strokeStyle=nodes[i].color.replace('#','rgba(').replace(/([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})/i,(m,r,g,b)=>`rgba(${parseInt(r,16)},${parseInt(g,16)},${parseInt(b,16)},${alpha.toFixed(2)})`);
          try{
            ctx.strokeStyle=`rgba(${parseInt(nodes[i].color.slice(1,3),16)},${parseInt(nodes[i].color.slice(3,5),16)},${parseInt(nodes[i].color.slice(5,7),16)},${alpha.toFixed(2)})`;
          }catch(e){}
          ctx.lineWidth=1;ctx.stroke();
        }
      }
      /* nodes */
      nodes.forEach(n=>{
        /* gentle float */
        n.x+=n.vx; n.y+=n.vy;
        const dx=n.x-n.ox,dy=n.y-n.oy;
        n.vx-=dx*0.001; n.vy-=dy*0.001;
        n.vx*=0.98; n.vy*=0.98;
        /* clamp */
        n.x=Math.max(n.r,Math.min(W-n.r,n.x));
        n.y=Math.max(n.r,Math.min(H-n.r,n.y));
        /* mouse repel */
        const mdx=n.x-mouse.x,mdy=n.y-mouse.y;
        const md=Math.sqrt(mdx*mdx+mdy*mdy);
        if(md<80) { n.vx+=mdx/md*1.2; n.vy+=mdy/md*1.2; }
        const isHover=md<n.r+6;
        /* glow */
        const grd=ctx.createRadialGradient(n.x,n.y,0,n.x,n.y,n.r*(isHover?3:2));
        try{
          const cr=parseInt(n.color.slice(1,3),16),cg=parseInt(n.color.slice(3,5),16),cb=parseInt(n.color.slice(5,7),16);
          grd.addColorStop(0,`rgba(${cr},${cg},${cb},0.35)`);
          grd.addColorStop(1,`rgba(${cr},${cg},${cb},0)`);
          ctx.beginPath();ctx.arc(n.x,n.y,n.r*(isHover?3:2),0,2*Math.PI);
          ctx.fillStyle=grd;ctx.fill();
          /* core */
          ctx.beginPath();ctx.arc(n.x,n.y,n.r*(isHover?1.4:1),0,2*Math.PI);
          ctx.fillStyle=n.color;ctx.fill();
          ctx.strokeStyle='rgba(245,245,239,0.25)';ctx.lineWidth=1;ctx.stroke();
        }catch(e){}
      });
      /* pulse ring on random node every 90 frames */
      if(frame%90===0 && nodes.length){
        const n=nodes[Math.floor(Math.random()*nodes.length)];
        (function pulse(pr){
          if(pr>n.r*5) return;
          try{
            const cr=parseInt(n.color.slice(1,3),16),cg=parseInt(n.color.slice(3,5),16),cb=parseInt(n.color.slice(5,7),16);
            ctx.beginPath();ctx.arc(n.x,n.y,pr,0,2*Math.PI);
            ctx.strokeStyle=`rgba(${cr},${cg},${cb},${(1-pr/(n.r*5)).toFixed(2)})`;
            ctx.lineWidth=1;ctx.stroke();
          }catch(e){}
          requestAnimationFrame(()=>pulse(pr+1));
        })(n.r);
      }
      frame++;
    }
    draw();
  });
}

function finInitSels() {
  if (finInicializado) return;
  finInicializado = true;
  const selSetor = document.getElementById('setorFinSel');
  selSetor.innerHTML = '<option value="">Todos os Setores</option>';
  setores.forEach(s => {
    const o = document.createElement('option');
    o.value = s; o.textContent = s;
    selSetor.appendChild(o);
  });
  finRangeInit();
  finRenderEmpList();
}
function parseBRDate(str) {
  if (!str || typeof str !== 'string') return null;
  if (str.includes('-')) {
    const parts = str.split('T')[0].split(' ')[0].split('-').map(Number);
    if (parts.length !== 3 || !parts[0] || !parts[1] || !parts[2]) return null;
    const ts = new Date(parts[0], parts[1]-1, parts[2]).getTime();
    return isNaN(ts) ? null : ts;
  }
  const parts = str.split('/');
  if (parts.length !== 3) return null;
  const [d, m, y] = parts.map(Number);
  if (!d || !m || !y) return null;
  const ts = new Date(y, m-1, d).getTime();
  return isNaN(ts) ? null : ts;
}
function formatDateBR(str){
  const ts = parseBRDate(str);
  if(!ts) return str || '—';
  const d = new Date(ts);
  const meses = [
    'jan','fev','mar','abr','mai','jun',
    'jul','ago','set','out','nov','dez'
  ];
  return (
    String(d.getDate()).padStart(2,'0') +
    '/' +
    meses[d.getMonth()] +
    '/' +
    d.getFullYear()
  );
}
function finGetEmpsDisp() {
  const setor = document.getElementById('setorFinSel')?.value || '';
  const q = (document.getElementById('finEmpSearch')?.value || '').toLowerCase().trim();
  return Object.keys(FIN_SERIES).filter(e => {
    if (setor && (FIN_SERIES[e]?.setor || 'Não Informado') !== setor) return false;
    if (!q) return true;
    return e.toLowerCase().includes(q);
  });
}
function finRenderEmpList() {
  const disponiveis = finGetEmpsDisp();
  const countEl = document.getElementById('finEmpCount');
  if (countEl) countEl.textContent = `(${disponiveis.length})`;
  const wrap = document.getElementById('finEmpList');
  if (!wrap) return;
  wrap.innerHTML = '';
  disponiveis.sort().forEach(e => {
    const sel = finSelecionadas.has(e);
    const btn = document.createElement('button');
    btn.textContent = e;
    btn.style.cssText = `padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600;transition:all .15s;border:1px solid ${sel?'var(--teal)':'var(--border)'};background:${sel?'rgba(0,103,123,.12)':'var(--surface2)'};color:${sel?'var(--teal)':'var(--text3)'};`;
    btn.onclick = () => finToggle(e);
    wrap.appendChild(btn);
  });
  finRenderChips();
}
function finToggle(e) {
  if (finSelecionadas.has(e)) finSelecionadas.delete(e); else finSelecionadas.add(e);
  finRenderEmpList(); buildFinanceiros();
}
function finRenderChips() {
  const wrap = document.getElementById('finChipsWrap');
  if (!wrap) return;
  if (!finSelecionadas.size) { wrap.innerHTML = '<span style="color:var(--text3);font-size:11px">Nenhuma selecionada</span>'; return; }
  wrap.innerHTML = [...finSelecionadas].map(e => `<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.25);border-radius:4px;padding:3px 8px;font-size:10px;font-weight:600;color:var(--teal)">${e}<span onclick="finToggle('${e}')" style="cursor:pointer;opacity:.7;font-size:12px;line-height:1">×</span></span>`).join('');
}
function finAddAll()    { finGetEmpsDisp().forEach(e => finSelecionadas.add(e)); finRenderEmpList(); buildFinanceiros(); }
function finRemoveAll() { finSelecionadas.clear(); finRenderEmpList(); buildFinanceiros(); }
function finOnSetorChange() { finRenderEmpList(); }
function buildFinanceiros() {
  if (!finInicializado) { finInitSels(); finInicializado = true; }
  finRenderEmpList();
  const ind      = document.getElementById('indFinSel').value;
  const empresas = [...finSelecionadas];
  if (!empresas.length) {
    if (activeCharts['chartFinMain']) { activeCharts['chartFinMain'].destroy(); delete activeCharts['chartFinMain']; }
    _finPainelRender();
    return;
  }
  document.getElementById('finTitle').textContent = ind.replace('_',' ').replace('TTM','TTM (R$ Mi)');
  const isPct = ['Mg EBITDA 36M','Mg Bruta 36M','Mg Liquida 36M','Estrutura de Capital (D/D+E)','ROE','ROA','ROIC'].includes(ind);
  const isVal = ['Receita_TTM','EBITDA_TTM','FCF_TTM'].includes(ind);
  const datasets = empresas.map((emp, i) => {
    const d = FIN_SERIES[emp];
    if (!d) return null;
    const raw   = d[ind] || [];
    const datas = d.datas || [];
    const dados = datas.map((dt, j) => {
      const v = raw[j];
      if (v == null || v !== v) return null;
      const dtParsed = parseBRDate(dt);
      if (!dtParsed) return null;
      if (dtParsed < _finDateMin || dtParsed > _finDateMax) return null;
      const yv = isVal ? +(v/1e6).toFixed(1) : v;
      if (yv !== yv) return null;
      return { x: dtParsed, y: yv };
    }).filter(p => p !== null);
    return { label:emp, data:dados, borderColor:COLORS[i%COLORS.length], backgroundColor:'transparent', tension:0.3, fill:false, pointRadius:empresas.length<=2?3:0, pointHoverRadius:5, borderWidth:empresas.length<=5?2:1.3 };
  }).filter(Boolean);
  const yUnit   = isPct ? '%' : isVal ? 'R$ Mi' : 'x';
  const yTickCb = isPct ? (v=>(v*100).toFixed(1)+'%') : isVal ? (v=>'R$ '+v.toFixed(0)+' Mi') : (v=>Number(v).toFixed(2)+'x');
  const yTicks  = { color:'#718096', font:{size:10,family:"'DM Mono',monospace"}, callback: yTickCb };
  mk('chartFinMain', {
    type: 'line', data: { datasets },
    options: {
      ...CHART_DEFAULTS, maintainAspectRatio:false, parsing:false,
      interaction: { mode:'nearest', intersect:false },
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: { display:true, position:'bottom', labels:{ color:'#718096', font:{size:10}, boxWidth:10 } },
        tooltip: { callbacks: { label: ctx => {
          const v = ctx.parsed.y;
          if (v == null) return null;
          if (isPct) return ctx.dataset.label+': '+(v*100).toFixed(1)+'%';
          if (isVal) return ctx.dataset.label+': R$ '+v.toFixed(1)+' Mi';
          return ctx.dataset.label+': '+v.toFixed(2)+'x';
        } } }
      },
      scales: {
        x: { type:'time', time:{ unit:'month', displayFormats:{ month:'MMM/yy' }, tooltipFormat:'dd/MM/yyyy' }, ...CHART_DEFAULTS.scales.x, ticks:{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:12 } },
        y: { ...CHART_DEFAULTS.scales.y, ticks:yTicks, title:{ display:true, text:yUnit, color:'#718096', font:{size:10} } }
      }
    }
  });
  const last = arr => arr?.length ? arr.slice().reverse().find(v => v != null) : null;
  const gc   = (v, g, w) => v == null ? '' : v >= g ? 'col-good' : v >= w ? 'col-warn' : 'col-bad';
  _finPainelRender();
}

let _fpSortCol='empresa', _fpSortAsc=true;
function _finPainelSort(col){if(_fpSortCol===col)_fpSortAsc=!_fpSortAsc;else{_fpSortCol=col;_fpSortAsc=(col==='empresa'||col==='setor');}_finPainelRender();}
function _finPainelRender(){
  const q=(document.getElementById('finPainelSearch')?.value||'').toLowerCase();
  const last=arr=>arr?.length?arr.slice().reverse().find(v=>v!=null):null;
  const getRow=nome=>{
    const fd=FIN_SERIES[nome]; if(!fd) return null;
    return {nome, setor:fd.setor||'Não Informado',
      rec:last(fd['Receita_TTM']), ebt:last(fd['EBITDA_TTM']),
      mg:last(fd['Mg EBITDA 36M']), dl:last(fd['DivLiquida/EBITDA']),
      ec:last(fd['Estrutura de Capital (D/D+E)']), roe:last(fd['ROE']),
      lc:last(fd['Liquidez Corrente'])};
  };
  let src=Object.keys(FIN_SERIES).map(getRow).filter(Boolean);
  if(q) src=src.filter(r=>[r.nome,r.setor].some(f=>f&&f.toLowerCase().includes(q)));
  const dir=_fpSortAsc?1:-1;
  const cmpStr=(a,b)=>(a||'').localeCompare(b||'','pt-BR');
  const cmpNum=(a,b)=>(a??-Infinity)-(b??-Infinity);
  src=[...src].sort((a,b)=>{
    switch(_fpSortCol){
      case 'empresa': return dir*cmpStr(a.nome,b.nome);
      case 'setor':   return dir*cmpStr(a.setor,b.setor);
      case 'rec':     return dir*cmpNum(a.rec,b.rec);
      case 'ebt':     return dir*cmpNum(a.ebt,b.ebt);
      case 'mg':      return dir*cmpNum(a.mg,b.mg);
      case 'dl':      return dir*cmpNum(a.dl,b.dl);
      case 'ec':      return dir*cmpNum(a.ec,b.ec);
      case 'roe':     return dir*cmpNum(a.roe,b.roe);
      case 'lc':      return dir*cmpNum(a.lc,b.lc);
      default:        return 0;
    }
  });
  ['empresa','setor','rec','ebt','mg','dl','ec','roe','lc'].forEach(col=>{
    const el=document.getElementById('_fpsh_'+col);if(!el)return;
    if(col===_fpSortCol){el.textContent=_fpSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}
    else{el.textContent='↕';el.style.opacity='.4';el.style.color='';}
  });
  document.getElementById('tbodyFin').innerHTML=src.map(r=>`<tr>
    <td style="font-weight:600">${r.nome}</td>
    <td class="td-muted">${r.setor}</td>
    <td style="font-family:var(--mono)">${r.rec!=null?fmtBRL(r.rec):'—'}</td>
    <td style="font-family:var(--mono)">${r.ebt!=null?fmtBRL(r.ebt):'—'}</td>
    <td class="${gc(r.mg,.35,.2)}" style="font-family:var(--mono)">${r.mg!=null?fmtPct(r.mg):'—'}</td>
    <td class="${r.dl!=null?(r.dl<3?'col-good':r.dl<5?'col-warn':'col-bad'):''}" style="font-family:var(--mono)">${r.dl!=null?fmtX(r.dl):'—'}</td>
    <td class="${gc(-((r.ec||0)),-.6,-.75)}" style="font-family:var(--mono)">${r.ec!=null?fmtPct(r.ec):'—'}</td>
    <td class="${gc(r.roe,.1,.05)}" style="font-family:var(--mono)">${r.roe!=null?fmtPct(r.roe):'—'}</td>
    <td class="${gc(r.lc,1.2,.9)}" style="font-family:var(--mono)">${r.lc!=null?fmtX(r.lc):'—'}</td>
  </tr>`).join('');
}
// ── FUNDAMENTOS ────────────────────────────────────────────────────────────
let _fundIniciado = false;

function fundFilterList() {
  const q  = (document.getElementById('fundSearch')?.value || '').toLowerCase();
  const sel = document.getElementById('fundEmpSel');
  if (!sel) return;
  [...sel.options].forEach(o => {
    o.hidden = q ? !o.text.toLowerCase().includes(q) : false;
  });
  // Select first visible if current selection is hidden
  const cur = sel.options[sel.selectedIndex];
  if (cur && cur.hidden) {
    const first = [...sel.options].find(o => !o.hidden);
    if (first) { sel.value = first.value; buildFundamentos(); }
  }
}

function _fundInitSel() {
  const sel = document.getElementById('fundEmpSel');
  if (!sel) return;
  const empresas = Object.keys(FIN_SERIES).sort();
  sel.innerHTML = empresas.map(e => `<option value="${e}">${e}</option>`).join('');
}

function buildFundamentos() {
  if (!_fundIniciado) { _fundInitSel(); _fundIniciado = true; fundRangeInit(); }
  const sel  = document.getElementById('fundEmpSel');
  if (!sel || !sel.value) return;
  const emp  = sel.value;
  const d    = FIN_SERIES[emp];
  if (!d) return;

  // Apply date range filter
  const rawDatas = d.datas || [];
  const rawTs    = rawDatas.map(dt => parseBRDate(dt));
  const idxKeep  = rawTs.map((ts,i) => (ts && ts >= _fundDateMin && ts <= _fundDateMax) ? i : -1).filter(i=>i>=0);
  const filtDatas = idxKeep.length ? idxKeep.map(i=>rawDatas[i]) : rawDatas;
  const filtTs    = idxKeep.length ? idxKeep.map(i=>rawTs[i])    : rawTs;
  const filterArr = arr => (arr||[]).length ? (idxKeep.length ? idxKeep.map(i=>(arr||[])[i]) : (arr||[])) : [];

  const datas  = filtTs;
  const labels = filtDatas.map(dt => {
    const p = parseBRDate(dt);
    return p ? new Date(p).toLocaleDateString('pt-BR',{month:'short',year:'2-digit'}) : dt;
  });
  const last = arr => arr?.length ? arr.slice().reverse().find(v => v != null) : null;
  const mi   = v => v != null ? +(v/1e3).toFixed(1) : null;
  const pct  = v => v != null ? +(v*100).toFixed(2) : null;
  const safe = arr => (arr||[]).map(v => (v == null || v !== v) ? null : v);

  // ── Info card ──
  document.getElementById('fundInfoSetor').textContent = d.setor || '—';
  document.getElementById('fundInfoData').textContent  = d.datas?.length ? 'Último balanço: ' + d.datas[d.datas.length-1] : '—';
  const rec  = last(d['Receita_TTM']);
  const ebt  = last(d['EBITDA_TTM']);
  const dl   = last(d['DivLiquida/EBITDA']);
  const lc   = last(d['Liquidez Corrente']);
  document.getElementById('fundKpiRec').textContent = rec != null ? 'R$ '+mi(rec)+' Mi' : '—';
  document.getElementById('fundKpiEbt').textContent = ebt != null ? 'R$ '+mi(ebt)+' Mi' : '—';
  document.getElementById('fundKpiDl').textContent  = dl  != null ? Number(dl).toFixed(1)+'x'  : '—';
  document.getElementById('fundKpiLc').textContent  = lc  != null ? Number(lc).toFixed(2)+'x'  : '—';

  const LOPT = {
    type:'line',
    options: {
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction: { mode:'index', intersect:false },
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: { display:true, position:'bottom', labels:{ color:'#718096', font:{size:10}, boxWidth:10 } }
      }
    }
  };

  // ── Chart 1: P&L (LTM) ──
  const recMi  = safe(filterArr(d['Receita_TTM'])).map(mi);
  const ebtMi  = safe(filterArr(d['EBITDA_TTM'])).map(mi);
  const llMi   = safe(filterArr(d['Lucro Liquido_TTM'])).map(mi);
  mk('fundChartPL', {
    type:'bar',
    data:{ labels,
      datasets:[
        { label:'Receita TTM',      data:recMi, type:'bar',  backgroundColor:'rgba(182,157,116,.45)', borderColor:'#b69d74', borderWidth:1, order:2 },
        { label:'EBITDA TTM',       data:ebtMi, type:'bar',  backgroundColor:'rgba(0,103,123,.5)',    borderColor:'#00677b', borderWidth:1, order:3 },
        { label:'Lucro Líquido TTM',data:llMi,  type:'line', borderColor:'#2fa874', backgroundColor:'transparent', tension:0.3, pointRadius:3, pointHoverRadius:5, borderWidth:2, order:1 }
      ]
    },
    options:{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        ...CHART_DEFAULTS.plugins,
        legend:{display:true,position:'bottom',labels:{color:'#718096',font:{size:10},boxWidth:10}},
        tooltip:{callbacks:{label:ctx => ctx.dataset.label+': R$ '+Number(ctx.parsed.y||0).toFixed(1)+' Mi'}}
      },
      scales:{
        x:{ ...CHART_DEFAULTS.scales.x, ticks:{...CHART_DEFAULTS.scales.x.ticks,maxRotation:45} },
        y:{ ...CHART_DEFAULTS.scales.y, title:{display:true,text:'R$ Mi',color:'#718096',font:{size:10}},
             ticks:{...CHART_DEFAULTS.scales.y.ticks,callback:v=>'R$ '+Number(v).toFixed(0)+' Mi'} }
      }
    }
  });

  // ── Chart 2: Margens (LTM) ──
  const mgB  = safe(filterArr(d['Mg Bruta TTM']  || d['Mg Bruta 36M'])).map(pct);
  const mgE  = safe(filterArr(d['Mg EBITDA TTM'] || d['Mg EBITDA 36M'])).map(pct);
  const mgL  = safe(filterArr(d['Mg Liquida TTM'])).map(pct);
  mk('fundChartMg', {
    type:'line',
    data:{ labels,
      datasets:[
        { label:'Margem Bruta',   data:mgB, borderColor:'#b69d74', backgroundColor:'rgba(182,157,116,.1)', tension:0.3, fill:true,  pointRadius:3, pointHoverRadius:5, borderWidth:2 },
        { label:'Margem EBITDA',  data:mgE, borderColor:'#00677b', backgroundColor:'rgba(0,103,123,.08)',  tension:0.3, fill:true,  pointRadius:3, pointHoverRadius:5, borderWidth:2 },
        { label:'Margem Líquida', data:mgL, borderColor:'#2fa874', backgroundColor:'transparent',          tension:0.3, fill:false, pointRadius:3, pointHoverRadius:5, borderWidth:2 }
      ]
    },
    options:{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        ...CHART_DEFAULTS.plugins,
        legend:{display:true,position:'bottom',labels:{color:'#718096',font:{size:10},boxWidth:10}},
        tooltip:{callbacks:{label:ctx => ctx.dataset.label+': '+(ctx.parsed.y!=null?Number(ctx.parsed.y).toFixed(1)+'%':'—')}}
      },
      scales:{
        x:{ ...CHART_DEFAULTS.scales.x, ticks:{...CHART_DEFAULTS.scales.x.ticks,maxRotation:45} },
        y:{ ...CHART_DEFAULTS.scales.y, title:{display:true,text:'%',color:'#718096',font:{size:10}},
             ticks:{...CHART_DEFAULTS.scales.y.ticks,callback:v=>Number(v).toFixed(1)+'%'} }
      }
    }
  });

  // ── Chart 3: Alavancagem ──
  const dlEbt  = safe(filterArr(d['DivLiquida/EBITDA'])).map(v => v!=null?+Number(v).toFixed(2):null);
  const dbEbt  = safe(filterArr(d['DivBruta_EBITDA'])).map(v => v!=null?+Number(v).toFixed(2):null);
  const dlMi   = safe(filterArr(d['Divida Liquida'])).map(mi);
  const dbMi   = safe(filterArr(d['Divida Bruta'])).map(mi);
  mk('fundChartLev', {
    type:'bar',
    data:{ labels,
      datasets:[
        { label:'Dív. Líquida (R$ Mi)', data:dlMi, type:'bar',  backgroundColor:'rgba(217,65,65,.4)',   borderColor:'#d94141', borderWidth:1, yAxisID:'yMi', order:3 },
        { label:'Dív. Bruta (R$ Mi)',   data:dbMi, type:'bar',  backgroundColor:'rgba(182,157,116,.4)', borderColor:'#b69d74', borderWidth:1, yAxisID:'yMi', order:4 },
        { label:'Dív. Líq/EBITDA (x)',  data:dlEbt,type:'line', borderColor:'#d94141', backgroundColor:'transparent', tension:0.3, pointRadius:3, pointHoverRadius:5, borderWidth:2.5, yAxisID:'yX', order:1 },
        { label:'Dív. Bruta/EBITDA (x)',data:dbEbt,type:'line', borderColor:'#3174b8', backgroundColor:'transparent', tension:0.3, pointRadius:3, pointHoverRadius:5, borderWidth:2,   yAxisID:'yX', order:2 }
      ]
    },
    options:{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        ...CHART_DEFAULTS.plugins,
        legend:{display:true,position:'bottom',labels:{color:'#718096',font:{size:10},boxWidth:10}},
        tooltip:{callbacks:{label:ctx => {
          const v = ctx.parsed.y;
          if(v==null) return null;
          return ctx.dataset.yAxisID==='yX' ? ctx.dataset.label+': '+Number(v).toFixed(2)+'x' : ctx.dataset.label+': R$ '+Number(v).toFixed(1)+' Mi';
        }}}
      },
      scales:{
        x:{ ...CHART_DEFAULTS.scales.x, ticks:{...CHART_DEFAULTS.scales.x.ticks,maxRotation:45} },
        yMi:{ type:'linear', position:'left',  display:true, title:{display:true,text:'R$ Mi',color:'#718096',font:{size:10}},
               ticks:{color:'#718096',font:{size:9,family:"'DM Mono',monospace"},callback:v=>'R$'+Number(v).toFixed(0)+'Mi'},
               grid:{color:'rgba(31,40,57,.05)'} },
        yX:{  type:'linear', position:'right', display:true, title:{display:true,text:'Vezes (x)',color:'#718096',font:{size:10}},
               ticks:{color:'#718096',font:{size:9,family:"'DM Mono',monospace"},callback:v=>Number(v).toFixed(1)+'x'},
               grid:{drawOnChartArea:false} }
      }
    }
  });

  // ── Chart 4: Liquidez ──
  const liq1 = safe(filterArr(d['Liquidez Corrente'])).map(v => v!=null?+Number(v).toFixed(3):null);
  const liq2 = safe(filterArr(d['Liquidez Seca'])).map(v => v!=null?+Number(v).toFixed(3):null);
  const liq3 = safe(filterArr(d['Liquidez Imediata'])).map(v => v!=null?+Number(v).toFixed(3):null);
  mk('fundChartLiq', {
    type:'line',
    data:{ labels,
      datasets:[
        { label:'Liq. Corrente', data:liq1, borderColor:'#00677b', backgroundColor:'rgba(0,103,123,.08)', tension:0.3, fill:true,  pointRadius:3, pointHoverRadius:5, borderWidth:2 },
        { label:'Liq. Seca',     data:liq2, borderColor:'#b69d74', backgroundColor:'transparent',         tension:0.3, fill:false, pointRadius:3, pointHoverRadius:5, borderWidth:2 },
        { label:'Liq. Imediata', data:liq3, borderColor:'#2fa874', backgroundColor:'transparent',         tension:0.3, fill:false, pointRadius:3, pointHoverRadius:5, borderWidth:2, borderDash:[4,3] }
      ]
    },
    options:{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        ...CHART_DEFAULTS.plugins,
        legend:{display:true,position:'bottom',labels:{color:'#718096',font:{size:10},boxWidth:10}},
        tooltip:{callbacks:{label:ctx => ctx.dataset.label+': '+(ctx.parsed.y!=null?Number(ctx.parsed.y).toFixed(2)+'x':'—')}}
      },
      scales:{
        x:{ ...CHART_DEFAULTS.scales.x, ticks:{...CHART_DEFAULTS.scales.x.ticks,maxRotation:45} },
        y:{ ...CHART_DEFAULTS.scales.y, title:{display:true,text:'Vezes (x)',color:'#718096',font:{size:10}},
             ticks:{...CHART_DEFAULTS.scales.y.ticks,callback:v=>Number(v).toFixed(2)+'x'} }
      }
    }
  });

  // ── Chart 5: Fluxo de Caixa ──
  const fco = safe(filterArr(d['FCO'])).map(mi);
  const fci = safe(filterArr(d['FCI'])).map(mi);
  const fcf = safe(filterArr(d['FCF'])).map(mi);
  mk('fundChartCF', {
    type:'bar',
    data:{ labels,
      datasets:[
        { label:'FCO — Operacional',       data:fco, backgroundColor:'rgba(0,103,123,.55)',    borderColor:'#00677b', borderWidth:1 },
        { label:'FCI — Investimentos',      data:fci, backgroundColor:'rgba(217,65,65,.45)',    borderColor:'#d94141', borderWidth:1 },
        { label:'FCF — FCO + FCI',          data:fcf, type:'line', borderColor:'#2fa874', backgroundColor:'transparent', tension:0.3, pointRadius:3, pointHoverRadius:5, borderWidth:2.5 }
      ]
    },
    options:{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        ...CHART_DEFAULTS.plugins,
        legend:{display:true,position:'bottom',labels:{color:'#718096',font:{size:10},boxWidth:10}},
        tooltip:{callbacks:{label:ctx => ctx.dataset.label+': R$ '+(ctx.parsed.y!=null?Number(ctx.parsed.y).toFixed(1):'—')+' Mi'}}
      },
      scales:{
        x:{ ...CHART_DEFAULTS.scales.x, ticks:{...CHART_DEFAULTS.scales.x.ticks,maxRotation:45} },
        y:{ ...CHART_DEFAULTS.scales.y, title:{display:true,text:'R$ Mi',color:'#718096',font:{size:10}},
             ticks:{...CHART_DEFAULTS.scales.y.ticks,callback:v=>'R$ '+Number(v).toFixed(0)+' Mi'} }
      }
    }
  });
}

async function exportarPDFFundamentos() {
  const sel = document.getElementById('fundEmpSel');
  if (!sel || !sel.value) { alert('Selecione uma empresa primeiro'); return; }

  const empName   = sel.options[sel.selectedIndex]?.text || sel.value;
  const container = document.getElementById('page-fundamentos');
  if (!container) { alert('Container nao encontrado.'); return; }

  const btn = document.querySelector('button[onclick="exportarPDFFundamentos()"]');
  const textoOriginal = btn ? btn.innerHTML : '';
  if (btn) { btn.innerHTML = 'Gerando...'; btn.disabled = true; btn.style.opacity = '0.5'; }

  // Monkey-patch createPattern: html2canvas 1.4.1 lanca erro fatal quando
  // encontra qualquer canvas (interno ou do usuario) com width=0 ou height=0.
  // Interceptamos a chamada e substituimos por um canvas 1x1 transparente.
  const _origCP = CanvasRenderingContext2D.prototype.createPattern;
  CanvasRenderingContext2D.prototype.createPattern = function(img, rep) {
    if (img instanceof HTMLCanvasElement && (img.width === 0 || img.height === 0)) {
      const dummy = document.createElement('canvas'); dummy.width = 1; dummy.height = 1;
      return _origCP.call(this, dummy, rep);
    }
    return _origCP.call(this, img, rep);
  };

  try {
    // ── Pre-fix: forca dimensoes reais em canvas zerados e resize dos charts ──
    const canvasCorrigidos = [];
    container.querySelectorAll('canvas').forEach(c => {
      if (c.width === 0 || c.height === 0) {
        const w = c.offsetWidth  || c.parentElement?.offsetWidth  || 600;
        const h = c.offsetHeight || c.parentElement?.offsetHeight || 320;
        canvasCorrigidos.push({ el: c, w: c.width, h: c.height });
        c.width = w > 0 ? w : 600; c.height = h > 0 ? h : 320;
      }
    });
    if (window.Chart && Chart.instances) {
      Object.values(Chart.instances).forEach(chart => {
        try { if (chart.canvas && container.contains(chart.canvas)) chart.resize(); } catch(e) {}
      });
    }
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

    const snap = await html2canvas(container, {
      useCORS:        true,
      scale:          2,
      backgroundColor:'#f4f5f0',
      logging:        false,
      allowTaint:     true,
      imageTimeout:   20000,
      onclone: clonedDoc => {
        clonedDoc.querySelectorAll('canvas').forEach(c => {
          if (c.width === 0 || c.height === 0) { c.width = 1; c.height = 1; }
        });
      },
      ignoreElements: el => {
        try {
          if (el.id === 'douradoBtn' || el.id === 'douradoPanel') return true;
          const oc = el.getAttribute && el.getAttribute('onclick');
          return !!(oc && oc.includes('exportarPDFFundamentos'));
        } catch(e) { return false; }
      }
    });

    canvasCorrigidos.forEach(({el, w, h}) => { el.width = w; el.height = h; });

    const { jsPDF } = window.jspdf;
    const pdf   = new jsPDF({ orientation:'portrait', unit:'mm', format:'a4', compress:true });
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const mTop  = 14; const mL = 6; const mRod = 8;
    const areaW = pageW - mL * 2;
    const areaH = pageH - mTop - mRod;
    const dataHoje = new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'2-digit', year:'numeric' });

    const _cabecalho = () => {
      pdf.setFillColor(31, 40, 57);
      pdf.rect(0, 0, pageW, mTop - 2, 'F');
      pdf.setTextColor(182, 157, 116); pdf.setFontSize(8); pdf.setFont('helvetica', 'bold');
      pdf.text('DOURO CAPITAL', mL + 2, mTop - 5);
      pdf.setTextColor(210, 210, 210); pdf.setFont('helvetica', 'normal');
      pdf.text(empName, pageW / 2, mTop - 5, { align:'center' });
      pdf.text(dataHoje, pageW - mL - 2, mTop - 5, { align:'right' });
    };
    const _rodape = () => {
      pdf.setTextColor(150, 150, 150); pdf.setFontSize(6);
      pdf.text('Douro Capital Gestora de Recursos · Uso Interno · Gerado automaticamente', pageW / 2, pageH - 3, { align:'center' });
    };

    // Fatia a imagem capturada em paginas A4
    const snapW  = snap.width;
    const snapH  = snap.height;
    const pxPerMm = snapW / areaW;
    const sliceH  = Math.round(areaH * pxPerMm);
    let offsetY = 0; let pagina = 0;

    while (offsetY < snapH) {
      if (pagina > 0) pdf.addPage();
      const h = Math.min(sliceH, snapH - offsetY);
      const fatia = document.createElement('canvas');
      fatia.width = snapW; fatia.height = h;
      fatia.getContext('2d').drawImage(snap, 0, offsetY, snapW, h, 0, 0, snapW, h);
      const imgD    = fatia.toDataURL('image/jpeg', 0.93);
      const renderH = h / pxPerMm;
      _cabecalho();
      pdf.addImage(imgD, 'JPEG', mL, mTop, areaW, renderH);
      _rodape();
      offsetY += h; pagina++;
    }

    const nomeArq = 'Empresas_' + empName.replace(/[^a-zA-Z0-9\s]/g,'').replace(/\s+/g,'_') + '_' + dataHoje.replace(/\//g,'-') + '.pdf';
    pdf.save(nomeArq);
  } catch(err) {
    console.error('Erro ao gerar PDF:', err);
    alert('Erro ao gerar PDF: ' + (err && err.message ? err.message : String(err)));
  } finally {
    // Restaura createPattern original e dimensoes dos canvas
    CanvasRenderingContext2D.prototype.createPattern = _origCP;
    if (typeof canvasCorrigidos !== 'undefined') {
      canvasCorrigidos.forEach(({el, w, h}) => { el.width = w; el.height = h; });
    }
    if (btn) { btn.innerHTML = textoOriginal; btn.disabled = false; btn.style.opacity = ''; }
  }
}

async function exportarPDFBancos() {
  const sel = document.getElementById('bancosEmpSel');
  if (!sel || !sel.value) { alert('Selecione um banco primeiro'); return; }
  const empName   = sel.options[sel.selectedIndex]?.text || sel.value;
  const container = document.getElementById('page-bancos');
  if (!container) { alert('Container nao encontrado.'); return; }
  const btn = document.querySelector('button[onclick="exportarPDFBancos()"]');
  const textoOriginal = btn ? btn.innerHTML : '';
  if (btn) { btn.innerHTML = 'Gerando...'; btn.disabled = true; btn.style.opacity = '0.5'; }
  const _origCP = CanvasRenderingContext2D.prototype.createPattern;
  CanvasRenderingContext2D.prototype.createPattern = function(img, rep) {
    if (img instanceof HTMLCanvasElement && (img.width === 0 || img.height === 0)) {
      const dummy = document.createElement('canvas'); dummy.width = 1; dummy.height = 1;
      return _origCP.call(this, dummy, rep);
    }
    return _origCP.call(this, img, rep);
  };
  try {
    const canvasCorrigidos = [];
    container.querySelectorAll('canvas').forEach(c => {
      if (c.width === 0 || c.height === 0) {
        const w = c.offsetWidth  || c.parentElement?.offsetWidth  || 600;
        const h = c.offsetHeight || c.parentElement?.offsetHeight || 320;
        canvasCorrigidos.push({ el: c, w: c.width, h: c.height });
        c.width = w > 0 ? w : 600; c.height = h > 0 ? h : 320;
      }
    });
    if (window.Chart && Chart.instances) {
      Object.values(Chart.instances).forEach(chart => {
        try { if (chart.canvas && container.contains(chart.canvas)) chart.resize(); } catch(e) {}
      });
    }
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const snap = await html2canvas(container, {
      useCORS: true, scale: 2, backgroundColor: '#f4f5f0',
      logging: false, allowTaint: true, imageTimeout: 20000,
      onclone: clonedDoc => {
        clonedDoc.querySelectorAll('canvas').forEach(c => {
          if (c.width === 0 || c.height === 0) { c.width = 1; c.height = 1; }
        });
      },
      ignoreElements: el => {
        try {
          if (el.id === 'douradoBtn' || el.id === 'douradoPanel') return true;
          const oc = el.getAttribute && el.getAttribute('onclick');
          return !!(oc && oc.includes('exportarPDFBancos'));
        } catch(e) { return false; }
      }
    });
    canvasCorrigidos.forEach(({el, w, h}) => { el.width = w; el.height = h; });
    const { jsPDF } = window.jspdf;
    const pdf   = new jsPDF({ orientation:'portrait', unit:'mm', format:'a4', compress:true });
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const mTop  = 14; const mL = 6; const mRod = 8;
    const areaW = pageW - mL * 2;
    const areaH = pageH - mTop - mRod;
    const dataHoje = new Date().toLocaleDateString('pt-BR', { day:'2-digit', month:'2-digit', year:'numeric' });
    const _cabecalho = () => {
      pdf.setFillColor(31, 40, 57);
      pdf.rect(0, 0, pageW, mTop - 2, 'F');
      pdf.setTextColor(182, 157, 116); pdf.setFontSize(8); pdf.setFont('helvetica', 'bold');
      pdf.text('DOURO CAPITAL', mL + 2, mTop - 5);
      pdf.setTextColor(210, 210, 210); pdf.setFont('helvetica', 'normal');
      pdf.text(empName, pageW / 2, mTop - 5, { align:'center' });
      pdf.text(dataHoje, pageW - mL - 2, mTop - 5, { align:'right' });
    };
    const _rodape = () => {
      pdf.setTextColor(150, 150, 150); pdf.setFontSize(6);
      pdf.text('Douro Capital Gestora de Recursos · Uso Interno · Gerado automaticamente', pageW / 2, pageH - 3, { align:'center' });
    };
    const snapW = snap.width, snapH = snap.height;
    const pxPerMm = snapW / areaW;
    const sliceH  = Math.round(areaH * pxPerMm);
    let offsetY = 0, pagina = 0;
    while (offsetY < snapH) {
      if (pagina > 0) pdf.addPage();
      const h = Math.min(sliceH, snapH - offsetY);
      const fatia = document.createElement('canvas');
      fatia.width = snapW; fatia.height = h;
      fatia.getContext('2d').drawImage(snap, 0, offsetY, snapW, h, 0, 0, snapW, h);
      const imgD    = fatia.toDataURL('image/jpeg', 0.93);
      const renderH = h / pxPerMm;
      _cabecalho();
      pdf.addImage(imgD, 'JPEG', mL, mTop, areaW, renderH);
      _rodape();
      offsetY += h; pagina++;
    }
    const nomeArq = 'Bancos_' + empName.replace(/[^a-zA-Z0-9\s]/g,'').replace(/\s+/g,'_') + '_' + dataHoje.replace(/\//g,'-') + '.pdf';
    pdf.save(nomeArq);
  } catch(err) {
    console.error('Erro ao gerar PDF:', err);
    alert('Erro ao gerar PDF: ' + (err && err.message ? err.message : String(err)));
  } finally {
    CanvasRenderingContext2D.prototype.createPattern = _origCP;
    if (typeof canvasCorrigidos !== 'undefined') {
      canvasCorrigidos.forEach(({el, w, h}) => { el.width = w; el.height = h; });
    }
    if (btn) { btn.innerHTML = textoOriginal; btn.disabled = false; btn.style.opacity = ''; }
  }
}

// ── SPREADS ────────────────────────────────────────────────────────────────
const spSelecionados = new Set();
let spInicializado = false;
function spInitSels() {
  const cart       = getFiltered();
  const ativosDisp = Object.keys(SPREADS_TS).filter(a =>
    cart.some(c => c.ticker === a)
  );
  // Classes
  const classesDisp = [...new Set(
    ativosDisp
      .map(a => cart.find(x => x.ticker === a)?.classe)
      .filter(Boolean)
  )].sort();
  const selClasse = document.getElementById('spClasseSel');
  selClasse.innerHTML = '<option value="">Todas as Classes</option>';
  classesDisp.forEach(c => {
    const o = document.createElement('option');
    o.value = c; o.textContent = c;
    selClasse.appendChild(o);
  });
  // Setores
  const setoresDisp = [...new Set(
    ativosDisp
      .map(a => cart.find(x => x.ticker === a)?.setor)
      .filter(Boolean)
  )].sort();
  const selSetor = document.getElementById('spSetorSel');
  selSetor.innerHTML = '<option value="">Todos os Setores</option>';
  setoresDisp.forEach(s => {
    const o = document.createElement('option');
    o.value = s; o.textContent = s;
    selSetor.appendChild(o);
  });
  // Emissores
  const emissoresDisp = [...new Set(
    ativosDisp
      .map(a => cart.find(x => x.ticker === a)?.emissor)
      .filter(Boolean)
  )].sort();
  const selEms = document.getElementById('spEmsSel');
  selEms.innerHTML = '<option value="">Todos os Emissores</option>';
  emissoresDisp.forEach(e => {
    const o = document.createElement('option');
    o.value = e; o.textContent = e;
    selEms.appendChild(o);
  });

  spRenderAtivoList();
}
function formatAtivoLabel(ticker) {
  const cart = typeof getFiltered === 'function' ? getFiltered() : [];
  const c = ATIVOS.find(a => a.ticker === ticker) || cart.find(x => x.ticker === ticker);
  if (!c) return ticker;
  const parts = [ticker];
  if (c.emissor) parts.push(c.emissor);
  if (c.duration != null && c.duration !== '' && !isNaN(Number(c.duration))) {
    parts.push(Number(c.duration).toFixed(1) + 'a');
  }
  return parts.join(' ');
}
function spFormatLabel(ativo) {
  return formatAtivoLabel(ativo);
}
function spGetAtivosDisp() {
  const cart    = getFiltered();
  const classe  = document.getElementById('spClasseSel')?.value || '';
  const setor   = document.getElementById('spSetorSel')?.value  || '';
  const emissor = document.getElementById('spEmsSel')?.value    || '';

  return Object.keys(SPREADS_TS).filter(a => {
    const c = cart.find(x => x.ticker === a);
    if (!c) return false;
    if (classe  && c.classe  !== classe)  return false;
    if (setor   && c.setor   !== setor)   return false;
    if (emissor && c.emissor !== emissor)  return false;
    return true;
  });
}
function spRenderAtivoList() {
  const disponiveis = spGetAtivosDisp();
  document.getElementById('spAtivoCount').textContent = `(${disponiveis.length})`;
  const wrap = document.getElementById('spAtivoList');
  wrap.innerHTML = '';
  disponiveis.sort().forEach(a => {
    const sel = spSelecionados.has(a);
    const btn = document.createElement('button');
    btn.textContent = spFormatLabel(a);
    btn.title = a;
    btn.style.cssText = `padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600;transition:all .15s;border:1px solid ${sel?'var(--teal)':'var(--border)'};background:${sel?'rgba(0,103,123,.12)':'var(--surface2)'};color:${sel?'var(--teal)':'var(--text3)'};`;
    btn.onclick = () => spToggle(a);
    wrap.appendChild(btn);
  });
  spRenderChips();
}
function spToggle(a) {
  if (spSelecionados.has(a)) spSelecionados.delete(a); else spSelecionados.add(a);
  spRenderAtivoList(); buildSpreads();
}
function spRenderChips() {
  const wrap = document.getElementById('spChipsWrap');
  if (!spSelecionados.size) { wrap.innerHTML = '<span style="color:var(--text3);font-size:11px">Nenhum selecionado</span>'; return; }
  wrap.innerHTML = [...spSelecionados].map(a => `<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.25);border-radius:4px;padding:3px 8px;font-size:10px;font-weight:600;color:var(--teal)">${spFormatLabel(a)}<span onclick="spToggle('${a}')" style="cursor:pointer;opacity:.7;font-size:12px;line-height:1">×</span></span>`).join('');
}
function spAddAll()    { spGetAtivosDisp().forEach(a => spSelecionados.add(a)); spRenderAtivoList(); buildSpreads(); }
function spRemoveAll() { spSelecionados.clear(); spRenderAtivoList(); buildSpreads(); }
function spOnClasseChange() {
  const cart   = getFiltered();
  const classe = document.getElementById('spClasseSel').value;
  // Re-popula Setores filtrando pela classe
  const ativosClasse = Object.keys(SPREADS_TS).filter(a => {
    const c = cart.find(x => x.ticker === a);
    return c && (!classe || c.classe === classe);
  });
  const setores = [...new Set(ativosClasse.map(a => cart.find(x => x.ticker===a)?.setor).filter(Boolean))].sort();
  const selSetor = document.getElementById('spSetorSel');
  selSetor.innerHTML = '<option value="">Todos os Setores</option>';
  setores.forEach(s => { const o = document.createElement('option'); o.value=s; o.textContent=s; selSetor.appendChild(o); });
  // Re-popula Emissores
  const emissores = [...new Set(ativosClasse.map(a => cart.find(x => x.ticker===a)?.emissor).filter(Boolean))].sort();
  const selEms = document.getElementById('spEmsSel');
  selEms.innerHTML = '<option value="">Todos os Emissores</option>';
  emissores.forEach(e => { const o = document.createElement('option'); o.value=e; o.textContent=e; selEms.appendChild(o); });
  spRenderAtivoList();
}
function spOnSetorChange() {
  const cart   = getFiltered();
  const classe = document.getElementById('spClasseSel').value;
  const setor  = document.getElementById('spSetorSel').value;
  const ativosDisp = Object.keys(SPREADS_TS).filter(a => {
    const c = cart.find(x => x.ticker === a);
    return c && (!classe || c.classe === classe) && (!setor || c.setor === setor);
  });
  const emissores = [...new Set(ativosDisp.map(a => cart.find(x => x.ticker===a)?.emissor).filter(Boolean))].sort();
  const selEms = document.getElementById('spEmsSel');
  selEms.innerHTML = '<option value="">Todos os Emissores</option>';
  emissores.forEach(e => { const o = document.createElement('option'); o.value=e; o.textContent=e; selEms.appendChild(o); });
  spRenderAtivoList();
}
function spOnEmsChange() { spRenderAtivoList(); }
// ── BANCOS ─────────────────────────────────────────────────────────────────
// Fallback estático (chaves = nomes exatos do Watch List Bancos.xlsm)
// Sobrescrito pelos dados reais do BCB via BCB_LIVE abaixo
const _BCB_DATA = {
  'Itaú': {
    anos:['2021','2022','2023','2024'],
    basileia:[14.5,14.7,15.2,16.1], tier1:[12.8,13.2,13.8,14.5],
    roe:[18.5,19.8,20.4,21.2], nim:[7.2,7.8,8.1,7.9],
    inadimpl:[2.8,3.1,3.4,2.9], eficiencia:[42.1,41.5,40.8,40.2],
    pdd:[4.1,4.5,4.8,4.2]
  },
  'Bradesco': {
    anos:['2021','2022','2023','2024'],
    basileia:[15.3,14.8,14.1,14.9], tier1:[13.1,12.6,12.2,13.0],
    roe:[19.2,18.1,12.3,14.8], nim:[7.8,8.2,8.6,8.1],
    inadimpl:[3.4,4.1,5.8,4.9], eficiencia:[44.5,45.2,50.1,47.3],
    pdd:[5.2,6.1,8.2,6.8]
  },
  'SANTANDER': {
    anos:['2021','2022','2023','2024'],
    basileia:[14.2,14.0,14.8,15.3], tier1:[12.2,12.0,12.8,13.2],
    roe:[20.1,19.5,14.2,16.8], nim:[8.1,8.9,9.2,8.7],
    inadimpl:[3.2,3.8,5.1,4.3], eficiencia:[43.2,44.1,47.8,45.6],
    pdd:[5.1,5.8,7.4,6.2]
  },
  'BTG Pactual': {
    anos:['2021','2022','2023','2024'],
    basileia:[17.8,18.1,18.9,19.4], tier1:[15.2,15.8,16.4,17.1],
    roe:[22.4,23.1,24.8,26.2], nim:[4.2,4.8,5.1,5.4],
    inadimpl:[0.8,0.9,1.1,0.9], eficiencia:[38.2,37.5,36.8,35.9],
    pdd:[1.2,1.4,1.6,1.3]
  },
  'BANCO SAFRA': {
    anos:['2021','2022','2023','2024'],
    basileia:[16.2,16.8,17.1,17.5], tier1:[14.1,14.5,14.9,15.3],
    roe:[14.8,15.2,14.9,15.4], nim:[5.8,6.1,6.4,6.2],
    inadimpl:[1.8,2.1,2.4,2.1], eficiencia:[46.1,45.8,45.2,44.9],
    pdd:[2.8,3.1,3.4,3.1]
  },
  'BANCO INTER': {
    anos:['2021','2022','2023','2024'],
    basileia:[20.1,16.8,15.2,16.4], tier1:[18.5,14.9,13.5,14.8],
    roe:[-8.2,2.1,8.4,12.1], nim:[8.8,9.2,10.1,10.8],
    inadimpl:[4.2,5.8,6.2,5.4], eficiencia:[72.1,65.8,58.2,52.4],
    pdd:[6.8,8.2,9.1,8.1]
  },
  'Daycoval': {
    anos:['2021','2022','2023','2024'],
    basileia:[16.8,17.2,17.8,18.1], tier1:[14.8,15.1,15.6,15.9],
    roe:[18.2,19.1,20.4,21.2], nim:[9.2,9.8,10.2,10.1],
    inadimpl:[2.1,2.4,2.8,2.5], eficiencia:[39.8,39.2,38.5,38.1],
    pdd:[3.4,3.8,4.2,3.9]
  },
  'Banco ABC': {
    anos:['2021','2022','2023','2024'],
    basileia:[15.8,15.4,16.1,16.8], tier1:[13.8,13.5,14.2,14.8],
    roe:[16.2,17.8,18.4,19.1], nim:[4.8,5.2,5.6,5.4],
    inadimpl:[1.2,1.4,1.8,1.5], eficiencia:[42.8,41.5,40.2,39.8],
    pdd:[2.1,2.4,2.8,2.5]
  },
  'Banco BMG': {
    anos:['2021','2022','2023','2024'],
    basileia:[13.2,13.8,14.1,14.8], tier1:[11.4,12.1,12.4,13.1],
    roe:[10.8,12.1,13.8,14.2], nim:[18.4,19.2,20.1,19.8],
    inadimpl:[6.2,6.8,7.2,6.8], eficiencia:[55.2,53.8,51.4,50.2],
    pdd:[9.8,10.4,11.2,10.8]
  }
};

// ── Injeção BCB_LIVE: dados reais substituem o fallback estático ──────────
// BCB_LIVE tem chaves = nomes exatos do Watch List (definidos no BANCOS_BCB do Python)
// O lookup é exato — sem fuzzy — porque Python e Watch List usam a mesma grafia
(function() {
  const live = (typeof BCB_LIVE !== 'undefined') ? BCB_LIVE : {};
  Object.keys(live).forEach(nome => {
    const lv = live[nome];
    _BCB_DATA[nome] = {
      anos:       lv.anos       || [],
      basileia:   lv.basileia   || [],
      tier1:      lv.alav       || [],
      roe:        lv.roe        || [],
      nim:        lv.ml         || [],
      inadimpl:   lv.npl        || [],   // NPL: carteira vencida >90d / carteira total (Rel. 6)
      pdd:        lv.prov_ratio || [],   // PDD/Carteira: provisão DRE / operações de crédito (Rel. 2+4)
      eficiencia: lv.eficiencia || []
    };
  });
})();

// Busca em _BCB_DATA: exato primeiro, depois case-insensitive como fallback
// Os nomes já vêm do Watch List via Python, então hit exato deve ser a regra
function _bcbLookup(nome) {
  if (!nome) return undefined;
  // 1. hit exato (nomes já alinhados Python → Watch List)
  if (_BCB_DATA[nome] !== undefined) return _BCB_DATA[nome];
  // 2. fallback case-insensitive (para variações de caixa residuais)
  const nq = nome.toLowerCase();
  const k = Object.keys(_BCB_DATA).find(k => k.toLowerCase() === nq);
  return k ? _BCB_DATA[k] : undefined;
}

let _bancosIniciado = false;

function buildBancos(preselect) {
  const sel = document.getElementById('bancosEmpSel');
  if (!sel) return;
  if (!_bancosIniciado) {
    _bancosIniciado = true;
    const bancos = RANK_BANCOS.length
      ? RANK_BANCOS.map(b=>b.empresa).filter(b => _bcbLookup(b) !== undefined)
      : Object.keys(_BCB_DATA);
    sel.innerHTML = bancos.map(b=>`<option value="${b}">${b}</option>`).join('');
  }
  if (preselect) sel.value = preselect;
  const banco = sel.value || sel.options[0]?.value;
  if (!banco) return;
  const rankInfo = (RANK_BANCOS||[]).find(b=>b.empresa===banco)||{};
  const d = _bcbLookup(banco);

  // KPIs (last period)
  const last = arr => arr?.length ? arr[arr.length-1] : null;
  if (d) {
    const basLast = last(d.basileia);
    const roeLast = last(d.roe);
    const nplLast = last(d.inadimpl);
    document.getElementById('bancoKpiBasileia').textContent = basLast!=null ? Number(basLast).toFixed(1)+'%' : '—';
    document.getElementById('bancoKpiROE').textContent      = roeLast!=null ? Number(roeLast).toFixed(1)+'%' : '—';
    document.getElementById('bancoKpiNPL').textContent      = nplLast!=null ? Number(nplLast).toFixed(1)+'%' : '—';
  } else {
    ['bancoKpiBasileia','bancoKpiROE','bancoKpiNPL'].forEach(id=>{document.getElementById(id).textContent='N/D';});
    // Sem dados BCB: limpa gráficos e exibe aviso
    ['bancoChartBasileia','bancoChartRent','bancoChartCredit','bancoChartEfic'].forEach(id=>{
      if(activeCharts[id]){activeCharts[id].destroy();delete activeCharts[id];}
      const canvas=document.getElementById(id);
      if(canvas){
        const ctx=canvas.getContext('2d');
        ctx.clearRect(0,0,canvas.width,canvas.height);
        ctx.fillStyle='#718096';
        ctx.font='12px Montserrat,sans-serif';
        ctx.textAlign='center';
        ctx.fillText('Sem dados BCB IF.data para este banco',canvas.width/2,canvas.height/2-8);
        ctx.font='10px Montserrat,sans-serif';
        ctx.fillStyle='#a0aec0';
        ctx.fillText('Indicadores regulatórios não disponíveis publicamente',canvas.width/2,canvas.height/2+10);
      }
    });
    _bancosCurrentBanco = banco;
    _renderTbodyBancosComp();
    return;
  }

  const anos = d?.anos || [];
  const lineOpts = {
    ...CHART_DEFAULTS, maintainAspectRatio:false,
    interaction:{mode:'index',intersect:false},
    plugins:{ ...CHART_DEFAULTS.plugins, legend:{display:true,position:'bottom',labels:{color:'#718096',font:{size:10},boxWidth:10}} }
  };

  // Chart 1: Basileia + Tier 1
  mk('bancoChartBasileia', {
    type:'line',
    data:{ labels:anos, datasets:[
      { label:'Índice de Basileia (%)', data:d?.basileia||[], borderColor:'#00677b', backgroundColor:'rgba(0,103,123,.12)', tension:0.3, fill:true, pointRadius:4, pointHoverRadius:6, borderWidth:2.5 },
      { label:'Tier 1 Capital (%)',     data:d?.tier1||[],    borderColor:'#b69d74', backgroundColor:'transparent',          tension:0.3, fill:false,pointRadius:4, pointHoverRadius:6, borderWidth:2 }
    ]},
    options:{ ...lineOpts, scales:{ x:CHART_DEFAULTS.scales.x, y:{ ...CHART_DEFAULTS.scales.y, title:{display:true,text:'%',color:'#718096',font:{size:10}}, ticks:{...CHART_DEFAULTS.scales.y.ticks,callback:v=>v+'%'}, beginAtZero:false } } }
  });

  // Chart 2: ROE + NIM
  mk('bancoChartRent', {
    type:'line',
    data:{ labels:anos, datasets:[
      { label:'ROE (%)',data:d?.roe||[], borderColor:'#2fa874', backgroundColor:'rgba(47,168,116,.1)', tension:0.3, fill:true, pointRadius:4, pointHoverRadius:6, borderWidth:2.5 },
      { label:'NIM (%)',data:d?.nim||[], borderColor:'#3174b8', backgroundColor:'transparent',          tension:0.3, fill:false,pointRadius:4, pointHoverRadius:6, borderWidth:2 }
    ]},
    options:{ ...lineOpts, scales:{ x:CHART_DEFAULTS.scales.x, y:{ ...CHART_DEFAULTS.scales.y, title:{display:true,text:'%',color:'#718096',font:{size:10}}, ticks:{...CHART_DEFAULTS.scales.y.ticks,callback:v=>v+'%'} } } }
  });

  // Chart 3: Inadimplência + PDD/Carteira (omite série se todos os valores forem null)
  const _hasData = arr => (arr||[]).some(v => v != null);
  const _creditDS = [];
  if (_hasData(d?.inadimpl)) _creditDS.push({ label:'Cobertura PDD (%)',        data:d.inadimpl, borderColor:'#d94141', backgroundColor:'rgba(217,65,65,.1)', tension:0.3, fill:true, pointRadius:4, pointHoverRadius:6, borderWidth:2.5 });
  if (_hasData(d?.pdd))      _creditDS.push({ label:'Desp. Provisão/Carteira (%)', data:d.pdd,  borderColor:'#e0c44a', backgroundColor:'transparent',        tension:0.3, fill:false,pointRadius:4, pointHoverRadius:6, borderWidth:2 });
  mk('bancoChartCredit', {
    type:'line',
    data:{ labels:anos, datasets:_creditDS },
    options:{ ...lineOpts, scales:{ x:CHART_DEFAULTS.scales.x, y:{ ...CHART_DEFAULTS.scales.y, title:{display:true,text:'%',color:'#718096',font:{size:10}}, ticks:{...CHART_DEFAULTS.scales.y.ticks,callback:v=>v+'%'}, beginAtZero:true } } }
  });

  // Chart 4: Eficiência (lower = better)
  mk('bancoChartEfic', {
    type:'bar',
    data:{ labels:anos, datasets:[
      { label:'Índice de Eficiência (%)', data:d?.eficiencia||[], backgroundColor:'rgba(182,157,116,.5)', borderColor:'#b69d74', borderWidth:1.5, borderRadius:4 }
    ]},
    options:{ ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{ ...CHART_DEFAULTS.plugins, legend:{display:false},
        tooltip:{callbacks:{label:ctx=>ctx.dataset.label+': '+Number(ctx.parsed.y).toFixed(1)+'%'}}
      },
      scales:{ x:CHART_DEFAULTS.scales.x, y:{ ...CHART_DEFAULTS.scales.y, title:{display:true,text:'% (menor = melhor)',color:'#718096',font:{size:10}}, ticks:{...CHART_DEFAULTS.scales.y.ticks,callback:v=>v+'%'}, beginAtZero:true } }
    }
  });

  _bancosCurrentBanco = banco;
  _renderTbodyBancosComp();
}

let _bancosCurrentBanco = '', _bcSortCol='inadimpl', _bcSortAsc=false;
function _bancosCompSort(col){if(_bcSortCol===col)_bcSortAsc=!_bcSortAsc;else{_bcSortCol=col;_bcSortAsc=(col==='nome'||col==='rating'||col==='status');}_renderTbodyBancosComp();}
function _renderTbodyBancosComp(){
  if(!document.getElementById('tbodyBancos'))return;
  const q=(document.getElementById('bancosSearch')?.value||'').toLowerCase();
  const l=arr=>{const v=arr?.length?arr[arr.length-1]:null;return v!=null?Number(v).toFixed(1)+'%':'—';};
  const lv=arr=>arr?.length?arr[arr.length-1]:null;
  const rOrd=['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC','CC','C','D','N/D'];
  const sOrd=['Aprovado','Em análise','Watch','Monitoramento','Reprovado','N/D'];
  const dir=_bcSortAsc?1:-1;
  const allBancos=RANK_BANCOS.length?RANK_BANCOS.map(b=>b.empresa).filter(b=>_bcbLookup(b)!==undefined):Object.keys(_BCB_DATA);
  let src=allBancos.map(b=>{const bd=_bcbLookup(b);const ri=(RANK_BANCOS||[]).find(x=>x.empresa===b)||{};return{b,bd,ri};});
  if(q) src=src.filter(x=>[x.b,x.ri.ratingDouro,x.ri.status].some(f=>f&&String(f).toLowerCase().includes(q)));
  src=[...src].sort((a,b)=>{
    const aV=col=>{const bd=a.bd;switch(col){case 'basileia':return lv(bd?.basileia)??-Infinity;case 'tier1':return lv(bd?.tier1)??-Infinity;case 'roe':return lv(bd?.roe)??-Infinity;case 'nim':return lv(bd?.nim)??-Infinity;case 'inadimpl':return lv(bd?.inadimpl)??-Infinity;case 'eficiencia':return lv(bd?.eficiencia)??-Infinity;default:return 0;}};
    const bV=col=>{const bd=b.bd;switch(col){case 'basileia':return lv(bd?.basileia)??-Infinity;case 'tier1':return lv(bd?.tier1)??-Infinity;case 'roe':return lv(bd?.roe)??-Infinity;case 'nim':return lv(bd?.nim)??-Infinity;case 'inadimpl':return lv(bd?.inadimpl)??-Infinity;case 'eficiencia':return lv(bd?.eficiencia)??-Infinity;default:return 0;}};
    if(_bcSortCol==='nome') return dir*(a.b||'').localeCompare(b.b||'','pt-BR');
    if(_bcSortCol==='rating') return dir*((rOrd.indexOf(a.ri.ratingDouro||'N/D')<0?99:rOrd.indexOf(a.ri.ratingDouro||'N/D'))-(rOrd.indexOf(b.ri.ratingDouro||'N/D')<0?99:rOrd.indexOf(b.ri.ratingDouro||'N/D')));
    if(_bcSortCol==='status') return dir*((sOrd.indexOf(a.ri.status||'N/D')<0?99:sOrd.indexOf(a.ri.status||'N/D'))-(sOrd.indexOf(b.ri.status||'N/D')<0?99:sOrd.indexOf(b.ri.status||'N/D')));
    return dir*(aV(_bcSortCol)-bV(_bcSortCol));
  });
  ['nome','basileia','tier1','roe','nim','inadimpl','eficiencia','rating','status'].forEach(col=>{
    const el=document.getElementById('_bcsh_'+col);if(!el)return;
    if(col===_bcSortCol){el.textContent=_bcSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}
    else{el.textContent='↕';el.style.opacity='.4';el.style.color='';}
  });
  document.getElementById('tbodyBancos').innerHTML=src.map(x=>{
    const {b,bd,ri}=x;
    const isCurrent=b===_bancosCurrentBanco;
    const roeV=lv(bd?.roe);const nplV=lv(bd?.inadimpl);
    return `<tr style="${isCurrent?'background:rgba(182,157,116,.08)':''}">
      <td style="font-weight:600;color:${isCurrent?'var(--teal)':'inherit'}">${b}</td>
      <td style="font-family:var(--mono)">${bd?l(bd.basileia):'—'}</td>
      <td style="font-family:var(--mono)">${bd?l(bd.tier1):'—'}</td>
      <td style="font-family:var(--mono);color:${roeV!=null?(roeV>15?'var(--teal)':roeV<10?'#d94141':'inherit'):'inherit'}">${bd?l(bd.roe):'—'}</td>
      <td style="font-family:var(--mono)">${bd?l(bd.nim):'—'}</td>
      <td style="font-family:var(--mono);color:${nplV!=null?(nplV>5?'#d94141':nplV<3?'var(--teal)':'inherit'):'inherit'}">${bd?l(bd.inadimpl):'—'}</td>
      <td style="font-family:var(--mono)">${bd?l(bd.eficiencia):'—'}</td>
      <td>${badgeRating(ri.ratingDouro)}</td>
      <td>${badgeStatus(ri.status)}</td>
    </tr>`;
  }).join('');
}

function buildSpreads() {
  // NÃO chame spInitSels() aqui — só popula na primeira vez
  if (!spInicializado) {
    spInitSels();
    spInicializado = true;
  }
  const cart       = getFiltered();
  const ativosUsar = [...spSelecionados].filter(a => SPREADS_TS[a]);
  if (!ativosUsar.length) {
    ['chartSpTaxa','chartSpSpread','chartSpScatter'].forEach(id => {
      if (activeCharts[id]) { activeCharts[id].destroy(); delete activeCharts[id]; }
    });
    document.getElementById('tbodySpreads').innerHTML = '<tr><td colspan="11" style="text-align:center;color:var(--text3);padding:40px 32px;font-size:13px">Selecione ativos usando os filtros acima</td></tr>';
    return;
  }
  const dsTaxa = ativosUsar.map((a, i) => {
    const ts   = SPREADS_TS[a];
    const dados = (ts.datas||[]).map((d,j) => {
      const dt = parseBRDate(d); if (!dt) return null;
      const yv = ts.valor?.[j]; if (yv==null||yv!==yv) return null;
      return { x:dt, y:yv };
    }).filter(p => p !== null);
    return { label:spFormatLabel(a), data:dados, borderColor:COLORS[i%COLORS.length], backgroundColor:'transparent', tension:.3, pointRadius:0, borderWidth:2 };
  });
  mk('chartSpTaxa', {
    type:'line', data:{ datasets:dsTaxa },
    options:{ ...CHART_DEFAULTS, parsing:false, interaction:{ mode:'nearest', intersect:false },
      plugins:{ ...CHART_DEFAULTS.plugins, legend:{ display:true, position:'bottom', labels:{ color:'#718096', font:{size:10}, boxWidth:10 } }, tooltip:{ callbacks:{ label: ctx => ctx.dataset.label+': '+(ctx.parsed.y!=null?ctx.parsed.y.toFixed(3)+'%':'—') } } },
      scales:{ x:{ type:'time', time:{ unit:'month', displayFormats:{ month:'MMM/yy' }, tooltipFormat:'dd/MM/yyyy' }, ...CHART_DEFAULTS.scales.x, ticks:{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:12 } }, y:{ ...CHART_DEFAULTS.scales.y, title:{ display:true, text:'Taxa (%)', color:'#718096', font:{size:10} }, ticks:{ ...CHART_DEFAULTS.scales.y.ticks, callback: v => v.toFixed(2)+'%' } } }
    }
  });
  const dsSpread = ativosUsar.map((a, i) => {
    const ts   = SPREADS_TS[a];
    const dados = (ts.datas||[]).map((d,j) => {
      const dt = parseBRDate(d); if (!dt) return null;
      const yv = ts.spread?.[j]; if (yv==null||yv!==yv) return null;
      return { x:dt, y:yv };
    }).filter(p => p !== null);
    return { label:spFormatLabel(a), data:dados, borderColor:COLORS[i%COLORS.length], backgroundColor:COLORS[i%COLORS.length]+'18', tension:.3, pointRadius:0, borderWidth:2, fill:false };
  });
  mk('chartSpSpread', {
    type:'line', data:{ datasets:dsSpread },
    options:{ ...CHART_DEFAULTS, parsing:false, interaction:{ mode:'nearest', intersect:false },
      plugins:{ ...CHART_DEFAULTS.plugins, legend:{ display:true, position:'bottom', labels:{ color:'#718096', font:{size:10}, boxWidth:10 } }, tooltip:{ callbacks:{ label: ctx => ctx.dataset.label+': '+(ctx.parsed.y!=null?ctx.parsed.y.toFixed(3)+'%':'—') } } },
      scales:{ x:{ type:'time', time:{ unit:'month', displayFormats:{ month:'MMM/yy' }, tooltipFormat:'dd/MM/yyyy' }, ...CHART_DEFAULTS.scales.x, ticks:{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:12 } }, y:{ ...CHART_DEFAULTS.scales.y, title:{ display:true, text:'Spread s/ NTN-B (%)', color:'#718096', font:{size:10} }, ticks:{ ...CHART_DEFAULTS.scales.y.ticks, callback: v => v.toFixed(2)+'%' } } }
    }
  });
  const scatterPts = ativosUsar.map((a, i) => {
    const c = cart.find(x => x.ticker === a);
    const ts = SPREADS_TS[a];
    const spread = ts?.spread?.filter(v => v!=null).slice(-1)[0] ?? null;
    const dur    = c?.duration ?? null;
    if (spread == null || dur == null) return null;
    return { ticker:a, x:dur, y:spread, color:COLORS[i%COLORS.length] };
  }).filter(Boolean);
  const _sxVals = scatterPts.map(p=>p.x), _syVals = scatterPts.map(p=>p.y);
  const _sxMin  = _sxVals.length ? Math.max(0, Math.min(..._sxVals) - 0.3) : 0;
  const _sxMax  = _sxVals.length ? Math.max(..._sxVals) + 0.3 : 5;
  const _syRng  = _syVals.length ? Math.max(..._syVals) - Math.min(..._syVals) : 0;
  const _syPad  = Math.max(_syRng * 0.18, 0.002);
  const _syMin  = _syVals.length ? Math.min(..._syVals) - _syPad : 0;
  const _syMax  = _syVals.length ? Math.max(..._syVals) + _syPad : 1;
  mk('chartSpScatter', {
    type:'scatter',
    data:{ datasets:[{ label:'Ativos', data:scatterPts.map(p=>({ x:p.x, y:p.y, ticker:p.ticker })), backgroundColor:scatterPts.map(p=>p.color+'cc'), pointRadius:8, pointHoverRadius:11 }] },
    options:{ ...CHART_DEFAULTS, plugins:{ ...CHART_DEFAULTS.plugins, legend:{ display:false }, tooltip:{ callbacks:{ label: c=>`${spFormatLabel(c.raw.ticker)}: dur=${c.raw.x?.toFixed(1)}a | spread=${c.raw.y?.toFixed(3)}%` } } }, scales:{ x:{ ...CHART_DEFAULTS.scales.x, title:{ display:true, text:'Duration (anos)', color:'#718096', font:{size:10} }, min:_sxMin, max:_sxMax }, y:{ ...CHART_DEFAULTS.scales.y, title:{ display:true, text:'Spread (%)', color:'#718096', font:{size:10} }, min:_syMin, max:_syMax, ticks:{ ...CHART_DEFAULTS.scales.y.ticks, callback: v=>v.toFixed(3)+'%' } } } }
  });
  _spCache = [...new Map(cart.filter(a => SPREADS_TS[a.ticker]).map(a => [a.ticker, a])).values()];
  _renderTbodySpreads();
}

let _spCache = [];
let _spSortCol = 'spread', _spSortAsc = false;

function _spSort(col) {
  if (_spSortCol===col) _spSortAsc=!_spSortAsc; else { _spSortCol=col; _spSortAsc=(col==='ticker'||col==='emissor'||col==='setor'||col==='ntnb'||col==='status'); }
  _renderTbodySpreads();
}

function _renderTbodySpreads() {
  const q=(document.getElementById('spreadsSearch')?.value||'').toLowerCase().trim();
  const soSel=document.getElementById('spSoSelecionados')?.checked;
  const classeSel = document.getElementById('spClasseSel')?.value || '';
  const setorSel  = document.getElementById('spSetorSel')?.value || '';
  const emsSel    = document.getElementById('spEmsSel')?.value || '';
  const cart = getFiltered();
  let src=_spCache;
  // Aplica filtro "Só selecionados"
  if(soSel) src=src.filter(a=>spSelecionados.has(a.ticker));
  // Aplica filtros de classe / setor / emissor (os mesmos usados pelos gráficos)
  if(classeSel || setorSel || emsSel) {
    src = src.filter(a => {
      const c = cart.find(x => x.ticker === a.ticker);
      if (!c) return false;
      if (classeSel && c.classe !== classeSel) return false;
      if (setorSel  && c.setor  !== setorSel)  return false;
      if (emsSel    && c.emissor !== emsSel)   return false;
      return true;
    });
  }
  if(q) src=src.filter(a=>[a.ticker,a.emissor,a.setor,a.ntnb_ref,a.Status].some(f=>f&&String(f).toLowerCase().includes(q)));
  const getV=a=>{
    const ts=SPREADS_TS[a.ticker];
    return {
      taxa: ts?.valor?.filter(v=>v!=null).slice(-1)[0]??null,
      spread: ts?.spread?.filter(v=>v!=null).slice(-1)[0]??null,
      mediana: ts?.mediana_spread??null,
      p1mad: ts?.mediana_mais_1mad_spread??null,
      m1mad: ts?.mediana_menos_1mad_spread??null,
    };
  };
  const cmpStr=(a,b)=>(a||'').localeCompare(b||'','pt-BR');
  const cmpNum=(a,b)=>(a??-Infinity)-(b??-Infinity);
  const dir=_spSortAsc?1:-1;
  src=[...src].sort((a,b)=>{
    const av=getV(a), bv=getV(b);
    switch(_spSortCol){
      case 'ticker':   return dir*cmpStr(a.ticker,b.ticker);
      case 'emissor':  return dir*cmpStr(a.emissor,b.emissor);
      case 'setor':    return dir*cmpStr(a.setor,b.setor);
      case 'taxa':     return dir*cmpNum(av.taxa,bv.taxa);
      case 'spread':   return dir*cmpNum(av.spread,bv.spread);
      case 'mediana':  return dir*cmpNum(av.mediana,bv.mediana);
      case 'ntnb':     return dir*cmpStr(a.ntnb_ref,b.ntnb_ref);
      case 'duration': return dir*cmpNum(a.duration,b.duration);
      case 'status':   return dir*cmpStr(a.Status,b.Status);
      default:         return dir*cmpNum(av.spread,bv.spread);
    }
  });
  ['ticker','emissor','setor','taxa','spread','mediana','ntnb','duration','status'].forEach(col=>{
    const el=document.getElementById('_spsh_'+col); if(!el) return;
    if(col===_spSortCol){el.textContent=_spSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}
    else{el.textContent='↕';el.style.opacity='.4';el.style.color='';}
  });
  const tb=document.getElementById('tbodySpreads');
  if(!src.length){tb.innerHTML='<tr><td colspan="11" style="text-align:center;color:var(--text3);padding:32px">Sem dados.</td></tr>';return;}
  tb.innerHTML=src.map(a=>{
    const v=getV(a);
    const sc=v.spread==null?'':v.spread>(v.p1mad??Infinity)?'col-bad':v.spread<(v.m1mad??-Infinity)?'col-good':'col-warn';
    const label = `${a.ticker||''}${a.emissor?(' '+a.emissor):''}${a.duration?(' '+Number(a.duration).toFixed(1)+'a'):''}` || '—';
    return `<tr>
      <td style="font-weight:700;font-family:var(--mono);font-size:11px">${label}</td>
      <td>${a.emissor||'—'}</td><td class="td-muted">${a.setor||'—'}</td>
      <td style="font-family:var(--mono)">${v.taxa!=null?Number(v.taxa).toFixed(3):'—'}</td>
      <td class="${sc}" style="font-family:var(--mono)">${v.spread!=null?Number(v.spread).toFixed(3):'—'}</td>
      <td style="font-family:var(--mono)">${v.mediana!=null?Number(v.mediana).toFixed(3):'—'}</td>
      <td style="font-family:var(--mono);color:var(--green)">${v.p1mad!=null?Number(v.p1mad).toFixed(3):'—'}</td>
      <td style="font-family:var(--mono);color:var(--red)">${v.m1mad!=null?Number(v.m1mad).toFixed(3):'—'}</td>
      <td class="td-muted">${a.ntnb_ref||'—'}</td>
      <td style="font-family:var(--mono)">${a.duration?Number(a.duration).toFixed(1)+'a':'—'}</td>
      <td>${badgeStatus(a.Status)}</td>
    </tr>`;
  }).join('');
}
// ── TÚNEL ─────────────────────────────────────────────────────────────────
function calcDistribuicao(valores, pontos=60) {
  const vals = (valores||[]).filter(v => v!=null && !isNaN(v));
  if (!vals.length) return { xs:[], ys:[] };
  const min = Math.min(...vals), max = Math.max(...vals);
  const largura = (max-min)||1, bandwidth = largura/8;
  const xs=[], ys=[];
  for (let i=0; i<pontos; i++) {
    const x = min + (largura*i/(pontos-1));
    let soma = 0;
    vals.forEach(v => { const u=(x-v)/bandwidth; soma+=Math.exp(-0.5*u*u); });
    xs.push(x); ys.push(soma/(vals.length*bandwidth*Math.sqrt(2*Math.PI)));
  }
  return { xs, ys };
}
function buildTunel() {
  const ativosCarteira = getFiltered().map(a => a.ticker);
  const ativos = Object.keys(SPREADS_TS).filter(a => ativosCarteira.includes(a));
  const sel = document.getElementById('ativoTunelSel');
  if (!sel) return;
  const anterior = sel.value;
  sel.innerHTML = '';
  ativos.forEach(a => { const o=document.createElement('option'); o.value=a; o.textContent=a; sel.appendChild(o); });
  if (ativos.includes(anterior)) sel.value = anterior;
  const ativo = sel.value || ativos[0];
  if (!ativo || !SPREADS_TS[ativo]) {
    if (activeCharts['chartTunelTaxa'])   activeCharts['chartTunelTaxa'].destroy();
    if (activeCharts['chartTunelSpread']) activeCharts['chartTunelSpread'].destroy();
    document.getElementById('tbodyTunel').innerHTML = '<tr><td colspan="12" style="text-align:center;color:var(--text3);padding:32px">Nenhum ativo disponível.</td></tr>';
    return;
  }
  const ts   = SPREADS_TS[ativo];
  const cart = getFiltered();
  const info = cart.find(a => a.ticker === ativo) || {};
  const dadosValidos = (ts.datas||[]).map((d,i) => ({ data:d, valor:ts.valor?.[i]??null, spread:ts.spread?.[i]??null, mm21v:ts.mm21_valor?.[i]??null, mm21s:ts.mm21_spread?.[i]??null })).filter(x => x.data!=null && (x.valor!=null || x.spread!=null));
  const datas  = dadosValidos.map(x => { const raw=x.data; if (!raw) return null; if (raw.includes('-')) return raw.split('T')[0]; const p=raw.split('/'); return p.length===3?`${p[2]}-${p[1].padStart(2,'0')}-${p[0].padStart(2,'0')}`:null; });
  const valores = dadosValidos.map(x => x.valor);
  const spreads = dadosValidos.map(x => x.spread);
  const mm21v   = dadosValidos.map(x => x.mm21v);
  const mm21s   = dadosValidos.map(x => x.mm21s);
  const hline   = (val, color, label) => ({ label, data:datas.map(()=>val), borderColor:color, backgroundColor:'transparent', borderDash:[4,4], borderWidth:1.5, pointRadius:0 });
  mk('chartTunelTaxa', {
    type:'line', data:{ labels:datas, datasets:[
      { label:'Taxa', data:valores, borderColor:'#b69d74', backgroundColor:'rgba(182,157,116,.12)', tension:.3, pointRadius:0, borderWidth:2, fill:true },
      ...(mm21v.some(v=>v!=null)?[{ label:'MM21 Taxa', data:mm21v, borderColor:'#00677b', backgroundColor:'transparent', tension:.4, pointRadius:0, borderDash:[2,2] }]:[]),
      ...(ts.mediana_valor!=null?[hline(ts.mediana_valor,'#4a90d9','Mediana')]:[]),
      ...(ts.mediana_mais_1mad_valor!=null?[hline(ts.mediana_mais_1mad_valor,'#3ec98e','+1 MAD')]:[]),
      ...(ts.mediana_menos_1mad_valor!=null?[hline(ts.mediana_menos_1mad_valor,'#e05252','−1 MAD')]:[])
    ]},
    options:{ ...CHART_DEFAULTS, scales:{ x:{ type:'time', time:{ unit:'month', displayFormats:{ month:'MMM/yy' }, tooltipFormat:'dd/MM/yyyy' }, ...CHART_DEFAULTS.scales.x, ticks:{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:10 } }, y:{ ...CHART_DEFAULTS.scales.y, title:{ display:true, text:'Taxa (%)', color:'#8a9ab5', font:{size:10} } } } }
  });
  const distTaxa = calcDistribuicao(valores.filter(v=>v!=null));
  mk('chartHistTunelTaxa', { type:'line', data:{ labels:distTaxa.xs.map(v=>v.toFixed(2)), datasets:[{ label:'Distribuição Taxa', data:distTaxa.ys, borderColor:'#b69d74', backgroundColor:'rgba(182,157,116,.12)', fill:true, tension:.35, pointRadius:0, borderWidth:2 }] }, options:{ ...CHART_DEFAULTS, plugins:{ ...CHART_DEFAULTS.plugins, legend:{ display:false } } } });
  mk('chartTunelSpread', {
    type:'line', data:{ labels:datas, datasets:[
      { label:'Spread', data:spreads, borderColor:'#4a90d9', backgroundColor:'rgba(74,144,217,.12)', tension:.3, pointRadius:0, borderWidth:2, fill:true },
      ...(mm21s.some(v=>v!=null)?[{ label:'MM21 Spread', data:mm21s, borderColor:'#00677b', backgroundColor:'transparent', tension:.4, pointRadius:0, borderDash:[2,2] }]:[]),
      ...(ts.mediana_spread!=null?[hline(ts.mediana_spread,'#b69d74','Mediana')]:[]),
      ...(ts.mediana_mais_1mad_spread!=null?[hline(ts.mediana_mais_1mad_spread,'#3ec98e','+1 MAD')]:[]),
      ...(ts.mediana_menos_1mad_spread!=null?[hline(ts.mediana_menos_1mad_spread,'#e05252','−1 MAD')]:[])
    ]},
    options:{ ...CHART_DEFAULTS, scales:{ x:{ type:'time', time:{ unit:'month', displayFormats:{ month:'MMM/yy' }, tooltipFormat:'dd/MM/yyyy' }, ...CHART_DEFAULTS.scales.x, ticks:{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:10 } }, y:{ ...CHART_DEFAULTS.scales.y, title:{ display:true, text:'Spread (%)', color:'#8a9ab5', font:{size:10} } } } }
  });
  const distSpread = calcDistribuicao(spreads.filter(v=>v!=null));
  mk('chartHistTunelSpread', { type:'line', data:{ labels:distSpread.xs.map(v=>v.toFixed(2)), datasets:[{ label:'Distribuição Spread', data:distSpread.ys, borderColor:'#4a90d9', backgroundColor:'rgba(74,144,217,.12)', fill:true, tension:.35, pointRadius:0, borderWidth:2 }] }, options:{ ...CHART_DEFAULTS, plugins:{ ...CHART_DEFAULTS.plugins, legend:{ display:false } } } });
  const taxaAtual   = valores.filter(v=>v!=null).slice(-1)[0]  ?? null;
  const spreadAtual = spreads.filter(v=>v!=null).slice(-1)[0]  ?? null;
  const med    = ts.mediana_spread ?? null;
  const p1mad  = ts.mediana_mais_1mad_spread  ?? null;
  const m1mad  = ts.mediana_menos_1mad_spread ?? null;
  const volSpread = ts.std_spread ?? null;
  let zscore = null;
  if (spreadAtual!=null && med!=null && p1mad!=null) {
    const madVal = p1mad - med, stdAprox = madVal * 1.4826;
    zscore = stdAprox > 0 ? (spreadAtual - med) / stdAprox : null;
  }
  const zCls  = zscore==null?'': zscore>2?'col-bad': zscore>1?'col-warn': zscore<-1?'col-good':'';
  const scSp  = spreadAtual==null?'': spreadAtual>(p1mad??Infinity)?'col-bad': spreadAtual<(m1mad??-Infinity)?'col-good':'col-warn';
  document.getElementById('tbodyTunel').innerHTML = `<tr>
    <td style="font-weight:600;font-size:11px">${ativo}</td>
    <td>${info.emissor||'—'}</td><td class="td-muted">${info.setor||'—'}</td>
    <td style="font-family:var(--mono)">${info.duration?Number(info.duration).toFixed(1)+'a':'—'}</td>
    <td style="font-family:var(--mono)">${taxaAtual!=null?Number(taxaAtual).toFixed(3):'—'}</td>
    <td class="${scSp}" style="font-family:var(--mono)">${spreadAtual!=null?Number(spreadAtual).toFixed(3):'—'}</td>
    <td style="font-family:var(--mono)">${med!=null?Number(med).toFixed(3):'—'}</td>
    <td style="font-family:var(--mono);color:var(--green)">${p1mad!=null?Number(p1mad).toFixed(3):'—'}</td>
    <td style="font-family:var(--mono);color:var(--red)">${m1mad!=null?Number(m1mad).toFixed(3):'—'}</td>
    <td class="${zCls}" style="font-family:var(--mono)">${zscore!=null?Number(zscore).toFixed(2):'—'}</td>
    <td style="font-family:var(--mono)">${volSpread!=null?Number(volSpread).toFixed(4):'—'}</td>
    <td>${badgeStatus(info.Status)}</td>
  </tr>`;
}
// ── BONDS ─────────────────────────────────────────────────────────────────
const bondsSelecionados = new Set();
let bondsFiltrados = [], bondsInicializado = false;
function bondInitSels() {
  bondsFiltrados = Object.keys(BONDS_TS).sort();
  if (bondsSelecionados.size===0 && bondsFiltrados.length>0) bondsFiltrados.slice(0,3).forEach(b => bondsSelecionados.add(b));
  bondRenderList();
}
function bondFilterList() {
  const termo = document.getElementById('bondSearch').value.toLowerCase();
  bondsFiltrados = Object.keys(BONDS_TS).filter(b => b.toLowerCase().includes(termo)).sort();
  bondRenderList();
}
function bondRenderList() {
  const wrap = document.getElementById('bondList'); if (!wrap) return;
  wrap.innerHTML = '';
  bondsFiltrados.forEach(b => {
    const sel = bondsSelecionados.has(b);
    const btn = document.createElement('button');
    btn.textContent = b;
    btn.style.cssText = `padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600;transition:all .15s;border:1px solid ${sel?'var(--teal)':'var(--border)'};background:${sel?'rgba(0,103,123,.12)':'var(--surface2)'};color:${sel?'var(--teal)':'var(--text3)'};`;
    btn.onclick = () => bondToggle(b);
    wrap.appendChild(btn);
  });
  bondRenderChips();
}
function bondToggle(b) { if (bondsSelecionados.has(b)) bondsSelecionados.delete(b); else bondsSelecionados.add(b); bondRenderList(); buildBonds(); }
function bondRenderChips() {
  const wrap=document.getElementById('bondChipsWrap'), countEl=document.getElementById('bondCount');
  if (!wrap) return;
  if (countEl) countEl.textContent = `(${bondsSelecionados.size})`;
  if (!bondsSelecionados.size) { wrap.innerHTML='<span style="color:var(--text3);font-size:11px">Nenhum selecionado — use a busca</span>'; return; }
  wrap.innerHTML = [...bondsSelecionados].map(b=>`<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.25);border-radius:4px;padding:3px 8px;font-size:10px;font-weight:600;color:var(--teal)">${b}<span onclick="bondToggle('${b}')" style="cursor:pointer;opacity:.7;font-size:12px;line-height:1">×</span></span>`).join('');
}
function bondAddAll()    { bondsFiltrados.forEach(b=>bondsSelecionados.add(b)); bondRenderList(); buildBonds(); }
function bondRemoveAll() { bondsSelecionados.clear(); bondRenderList(); buildBonds(); }
function buildBonds() {
  if (!bondsInicializado) { bondInitSels(); bondsInicializado=true; } else bondRenderList();
  const bondsPlot = [...bondsSelecionados];
  if (!bondsPlot.length) {
    if (activeCharts['chartBondsPreco']) { activeCharts['chartBondsPreco'].destroy(); delete activeCharts['chartBondsPreco']; }
    const tb=document.getElementById('tbodyBonds'); if(tb) tb.innerHTML='<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:32px">Selecione bonds para visualizar dados.</td></tr>';
    return;
  }
  const datasetsPreco = bondsPlot.map((b,i) => {
    const ts=BONDS_TS[b]; if(!ts) return null;
    const dados=(ts.datas||[]).map((d,j)=>{ const dt=parseBRDate(d); if(!dt) return null; return { x:dt, y:ts.valor?.[j]??null }; }).filter(p=>p&&p.y!=null);
    return { label:b, data:dados, borderColor:COLORS[i%COLORS.length], backgroundColor:'transparent', tension:0.25, pointRadius:0, borderWidth:2 };
  }).filter(Boolean);
  mk('chartBondsPreco', {
    type:'line', data:{ datasets:datasetsPreco },
    options:{ ...CHART_DEFAULTS, parsing:false, maintainAspectRatio:false, interaction:{ mode:'nearest', intersect:false },
      plugins:{ ...CHART_DEFAULTS.plugins, legend:{ display:true, position:'bottom', labels:{ color:'#718096', font:{size:10}, boxWidth:10 } }, tooltip:{ callbacks:{ label: ctx=>ctx.dataset.label+': '+(ctx.parsed.y!=null?ctx.parsed.y.toFixed(2):'—') } } },
      scales:{ x:{ type:'time', time:{ unit:'month', displayFormats:{ month:'MMM/yy' }, tooltipFormat:'dd/MM/yyyy' }, ...CHART_DEFAULTS.scales.x, ticks:{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:12 } }, y:{ ...CHART_DEFAULTS.scales.y, title:{ display:true, text:'Preço (% PU)', color:'#718096', font:{size:10} }, ticks:{ ...CHART_DEFAULTS.scales.y.ticks, callback: v=>v.toFixed(2) } } }
    }
  });
  _bondsCachePlot = bondsPlot;
  _renderTbodyBonds();
}

let _bondsCachePlot=[], _bondsSortCol='ticker', _bondsSortAsc=true;
function _bondsSort(col){if(_bondsSortCol===col)_bondsSortAsc=!_bondsSortAsc;else{_bondsSortCol=col;_bondsSortAsc=(col==='ticker'||col==='emissor'||col==='status');}_renderTbodyBonds();}
function _renderTbodyBonds(){
  const q=(document.getElementById('bondsSearch')?.value||'').toLowerCase();
  const dir=_bondsSortAsc?1:-1;
  let src=_bondsCachePlot.map(b=>{
    const info=BONDS_INFO.find(x=>x.ativo===b)||{};
    const ts=BONDS_TS[b];
    const preco=ts?.valor?.filter(v=>v!=null).slice(-1)[0]??null;
    return {b,info,preco};
  });
  if(q) src=src.filter(x=>[x.b,x.info.emissor,x.info.status].some(f=>f&&String(f).toLowerCase().includes(q)));
  src=[...src].sort((a,b)=>{
    if(_bondsSortCol==='ticker') return dir*(a.b||'').localeCompare(b.b||'','pt-BR');
    if(_bondsSortCol==='emissor') return dir*(a.info.emissor||'').localeCompare(b.info.emissor||'','pt-BR');
    if(_bondsSortCol==='status') return dir*(a.info.status||'').localeCompare(b.info.status||'','pt-BR');
    if(_bondsSortCol==='preco') return dir*((a.preco??-Infinity)-(b.preco??-Infinity));
    return 0;
  });
  ['ticker','emissor','status','preco'].forEach(col=>{
    const el=document.getElementById('_bsh_'+col);if(!el)return;
    if(col===_bondsSortCol){el.textContent=_bondsSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}
    else{el.textContent='↕';el.style.opacity='.4';el.style.color='';}
  });
  const tb=document.getElementById('tbodyBonds');
  if(!tb) return;
  if(!src.length){tb.innerHTML='<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:32px">Sem dados.</td></tr>';return;}
  tb.innerHTML=src.map(x=>`<tr><td style="font-weight:700;font-family:var(--mono);font-size:11px">${x.b}</td><td>${x.info.emissor||'—'}</td><td>${badgeStatus(x.info.status)}</td><td style="font-family:var(--mono);color:var(--teal)">${x.preco!=null?Number(x.preco).toFixed(2):'—'}</td></tr>`).join('');
}
// ── RANKING ───────────────────────────────────────────────────────────────
let _rcSortCol='status',_rcSortAsc=false;
function _rankCorpSort(col){if(_rcSortCol===col)_rcSortAsc=!_rcSortAsc;else{_rcSortCol=col;_rcSortAsc=col!=='status';}_renderRankCorp();}
function _renderRankCorp(){
  const q=(document.getElementById('rankCorpSearch')?.value||'').toLowerCase();
  const rOrd=['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC','CC','C','D','N/D'];
  const sOrd=['Aprovado','Em análise','Watch','Monitoramento','Reprovado','N/D'];
  const cmpStr=(a,b)=>(a||'').localeCompare(b||'','pt-BR');
  const cmpRat=(a,b)=>(rOrd.indexOf(a||'N/D')<0?99:rOrd.indexOf(a||'N/D'))-(rOrd.indexOf(b||'N/D')<0?99:rOrd.indexOf(b||'N/D'));
  const cmpSt=(a,b)=>(sOrd.indexOf(a||'N/D')<0?99:sOrd.indexOf(a||'N/D'))-(sOrd.indexOf(b||'N/D')<0?99:sOrd.indexOf(b||'N/D'));
  const dir=_rcSortAsc?1:-1;
  let src=RANK_CORP.filter(e=>!q||[e.empresa,e.setor,e.ratingMkt,e.ratingDouro,e.status].some(f=>f&&String(f).toLowerCase().includes(q)));
  src=[...src].sort((a,b)=>{
    switch(_rcSortCol){
      case 'empresa': return dir*cmpStr(a.empresa,b.empresa);
      case 'setor': return dir*cmpStr(a.setor,b.setor);
      case 'ratingMkt': return dir*cmpRat(a.ratingMkt,b.ratingMkt);
      case 'ratingDouro': return dir*cmpRat(a.ratingDouro,b.ratingDouro);
      default: return dir*cmpSt(a.status,b.status);
    }
  });
  ['empresa','setor','ratingMkt','ratingDouro','status'].forEach(col=>{
    const el=document.getElementById('_rcsh_'+col);if(!el)return;
    if(col===_rcSortCol){el.textContent=_rcSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}
    else{el.textContent='↕';el.style.opacity='.4';el.style.color='';}
  });
  document.getElementById('tbodyRankCorp').innerHTML=src.map(e=>`<tr><td style="font-weight:600">${e.empresa}</td><td class="td-muted">${e.setor}</td><td>${badgeRating(e.ratingMkt)}</td><td>${badgeRating(e.ratingDouro)}</td><td>${badgeStatus(e.status)}</td></tr>`).join('');
}
function buildRankingCorp() {
  _renderRankCorp();
  const byStatus={};
  RANK_CORP.forEach(e=>{ const s=e.status||'N/D'; byStatus[s]=(byStatus[s]||0)+1; });
  const statusEntries=Object.entries(byStatus);
  const statusColor=s=>s==='Aprovado'?'#00677b':s==='Em análise'?'#b69d74':s==='Reprovado'?'#d94141':'#718096';
  mk('chartRankingStatus', {
    type:'doughnut',
    data:{ labels:statusEntries.map(e=>e[0]), datasets:[{ data:statusEntries.map(e=>e[1]), backgroundColor:statusEntries.map(e=>statusColor(e[0])+'ee'), borderColor:'#ffffff', borderWidth:2 }] },
    options:{ ...DOUGHNUT_OPTS, plugins:{ ...DOUGHNUT_OPTS.plugins, tooltip:{ callbacks:{ label: c=>`${c.label}: ${c.raw} emissor(es)` } } } }
  });
}

let _rbSortCol='status',_rbSortAsc=false;
function _rankBancosSort(col){if(_rbSortCol===col)_rbSortAsc=!_rbSortAsc;else{_rbSortCol=col;_rbSortAsc=col!=='status';}_renderRankBancos();}
function _renderRankBancos(){
  const q=(document.getElementById('rankBancosSearch')?.value||'').toLowerCase();
  const rOrd=['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC','CC','C','D','N/D'];
  const sOrd=['Aprovado','Em análise','Watch','Monitoramento','Reprovado','N/D'];
  const dir=_rbSortAsc?1:-1;
  let src=RANK_BANCOS.filter(b=>!q||[b.empresa,b.ratingDouro,b.status].some(f=>f&&String(f).toLowerCase().includes(q)));
  src=[...src].sort((a,b)=>{
    if(_rbSortCol==='empresa') return dir*(a.empresa||'').localeCompare(b.empresa||'','pt-BR');
    if(_rbSortCol==='ratingDouro') return dir*((rOrd.indexOf(a.ratingDouro||'N/D')<0?99:rOrd.indexOf(a.ratingDouro||'N/D'))-(rOrd.indexOf(b.ratingDouro||'N/D')<0?99:rOrd.indexOf(b.ratingDouro||'N/D')));
    return dir*((sOrd.indexOf(a.status||'N/D')<0?99:sOrd.indexOf(a.status||'N/D'))-(sOrd.indexOf(b.status||'N/D')<0?99:sOrd.indexOf(b.status||'N/D')));
  });
  ['empresa','ratingDouro','status'].forEach(col=>{
    const el=document.getElementById('_rbsh_'+col);if(!el)return;
    if(col===_rbSortCol){el.textContent=_rbSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}
    else{el.textContent='↕';el.style.opacity='.4';el.style.color='';}
  });
  document.getElementById('tbodyRankBancos').innerHTML=src.map(b=>`<tr><td style="font-weight:600">${b.empresa}</td><td>${badgeRating(b.ratingDouro)}</td><td>${badgeStatus(b.status)}</td></tr>`).join('');
}
function buildRankingBancos() {
  _renderRankBancos();
  const byRD={};
  RANK_BANCOS.forEach(b=>{ byRD[b.ratingDouro||'N/D']=(byRD[b.ratingDouro||'N/D']||0)+1; });
  const ord=['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC','CC','C','D','N/D'];
  const rde=Object.entries(byRD).sort((a,b)=>ord.indexOf(a[0])-ord.indexOf(b[0]));
  mk('chartRankingBancosBar',{ type:'bar', data:{ labels:rde.map(e=>e[0]), datasets:[{ data:rde.map(e=>e[1]), backgroundColor:rde.map((_,i)=>COLORS[i%COLORS.length]+'ee'), borderColor:rde.map((_,i)=>COLORS[i%COLORS.length]), borderWidth:1, borderRadius:4 }]}, options:{...CHART_DEFAULTS, plugins:{...CHART_DEFAULTS.plugins, legend:{display:false}}, scales:{ x:{...CHART_DEFAULTS.scales.x}, y:{...CHART_DEFAULTS.scales.y, ticks:{...CHART_DEFAULTS.scales.y.ticks, stepSize:1}}}} });
}
function buildRankingComparativo() {
  document.getElementById('tbodyCompCorp').innerHTML   = RANK_CORP.map(e=>`<tr><td style="font-weight:600">${e.empresa}</td><td class="td-muted">${e.setor}</td><td>${badgeRating(e.ratingMkt)}</td><td>${badgeRating(e.ratingDouro)}</td><td>${badgeStatus(e.status)}</td></tr>`).join('');
  document.getElementById('tbodyCompBancos').innerHTML = RANK_BANCOS.map(b=>`<tr><td style="font-weight:600">${b.empresa}</td><td>${badgeRating(b.ratingDouro)}</td><td>${badgeStatus(b.status)}</td></tr>`).join('');
  const ord=['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC','CC','C','D','N/D'];
  const byRdCorp={}, byRdBanc={};
  RANK_CORP.forEach(e=>{ byRdCorp[e.ratingDouro||'N/D']=(byRdCorp[e.ratingDouro||'N/D']||0)+1; });
  RANK_BANCOS.forEach(b=>{ byRdBanc[b.ratingDouro||'N/D']=(byRdBanc[b.ratingDouro||'N/D']||0)+1; });
  const allRatings=[...new Set([...Object.keys(byRdCorp),...Object.keys(byRdBanc)])].sort((a,b)=>ord.indexOf(a)-ord.indexOf(b));
  mk('chartCompRating',{type:'bar',data:{labels:allRatings,datasets:[{label:'Corporativos',data:allRatings.map(r=>byRdCorp[r]||0),backgroundColor:'rgba(0,103,123,.75)',borderColor:'#00677b',borderWidth:1,borderRadius:3},{label:'Bancos',data:allRatings.map(r=>byRdBanc[r]||0),backgroundColor:'rgba(182,157,116,.75)',borderColor:'#b69d74',borderWidth:1,borderRadius:3}]},options:{...CHART_DEFAULTS,plugins:{...CHART_DEFAULTS.plugins,legend:{display:true,position:'bottom',labels:{color:'#718096',font:{size:10},boxWidth:10}}},scales:{x:{...CHART_DEFAULTS.scales.x},y:{...CHART_DEFAULTS.scales.y,ticks:{...CHART_DEFAULTS.scales.y.ticks,stepSize:1}}}}});
  const statusOrd=['Aprovado','Em análise','Watch','Monitoramento','Reprovado'];
  const byStCorp={}, byStBanc={};
  RANK_CORP.forEach(e=>{ const s=e.status||'N/D'; byStCorp[s]=(byStCorp[s]||0)+1; });
  RANK_BANCOS.forEach(b=>{ const s=b.status||'N/D'; byStBanc[s]=(byStBanc[s]||0)+1; });
  const statusColor=s=>s==='Aprovado'?'#00677b':s==='Reprovado'?'#d94141':'#b69d74';
  const allStatus=[...new Set([...Object.keys(byStCorp),...Object.keys(byStBanc)])].sort((a,b)=>{const i=statusOrd.indexOf(a),j=statusOrd.indexOf(b);return(i<0?99:i)-(j<0?99:j);});
  mk('chartCompStatus',{type:'bar',data:{labels:allStatus,datasets:[{label:'Corporativos',data:allStatus.map(s=>byStCorp[s]||0),backgroundColor:allStatus.map(s=>statusColor(s)+'aa'),borderColor:allStatus.map(s=>statusColor(s)),borderWidth:1,borderRadius:3},{label:'Bancos',data:allStatus.map(s=>byStBanc[s]||0),backgroundColor:allStatus.map(s=>statusColor(s)+'55'),borderColor:allStatus.map(s=>statusColor(s)),borderWidth:1,borderRadius:3}]},options:{...CHART_DEFAULTS,plugins:{...CHART_DEFAULTS.plugins,legend:{display:true,position:'bottom',labels:{color:'#718096',font:{size:10},boxWidth:10}}},scales:{x:{...CHART_DEFAULTS.scales.x},y:{...CHART_DEFAULTS.scales.y,ticks:{...CHART_DEFAULTS.scales.y.ticks,stepSize:1}}}}});
}
function buildRanking() { buildRankingCorp(); buildRankingBancos(); }
function showRankingPage(sub, el) {
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  const pg=document.getElementById('page-ranking');
  pg.classList.add('active'); pg.classList.remove('fade-in'); void pg.offsetWidth; pg.classList.add('fade-in');
  if(el) el.classList.add('active');
  document.getElementById('subpage-corporativo').style.display='none';
  document.getElementById('subpage-bancario').style.display='none';
  document.getElementById('subpage-comparativo').style.display='none';
  if (sub==='corporativo')  { document.getElementById('subpage-corporativo').style.display=''; requestAnimationFrame(()=>buildRankingCorp()); }
  else if (sub==='bancario'){ document.getElementById('subpage-bancario').style.display='';   requestAnimationFrame(()=>buildRankingBancos()); }
  else                      { document.getElementById('subpage-comparativo').style.display=''; requestAnimationFrame(()=>buildRankingComparativo()); }
  loadedPages['ranking']=true;
}
// ── PERFORMANCE ───────────────────────────────────────────────────────────
function buildPerformance() {
  const ativos = Object.keys(PERF_DATA.ativos);
  const datasets = ativos.map((a,i)=>({ label:a, data:PERF_DATA.ativos[a].retorno_acum.map(v=>v*100), borderColor:COLORS[i%COLORS.length], backgroundColor:'transparent', tension:.3, pointRadius:0, borderWidth:2 }));
  mk('chartPerfAcum',{ type:'line', data:{ labels:PERF_DATA.datas, datasets }, options:{
    ...CHART_DEFAULTS,
    ..._CROSSHAIR_OPTS,
    plugins:{ ...CHART_DEFAULTS.plugins, ..._CROSSHAIR_OPTS.plugins },
    scales:{
      x:{ ...CHART_DEFAULTS.scales.x },
      y:{ ...CHART_DEFAULTS.scales.y, ticks:{ ...CHART_DEFAULTS.scales.y.ticks, callback: v=>v.toFixed(1)+'%' } }
    }
  } });
  const janela=parseInt(document.getElementById('janelaPerf').value);
  const rollingDs = ativos.map((a,i)=>{
    const rets=PERF_DATA.ativos[a].retornos, rolling=[];
    for(let j=janela;j<rets.length;j++){ let acc=1; for(let k=j-janela;k<j;k++) acc*=(1+rets[k]); rolling.push((acc-1)*100); }
    return { label:a, data:rolling, borderColor:COLORS[i%COLORS.length], backgroundColor:'transparent', tension:.3, pointRadius:0, borderWidth:2 };
  });
  mk('chartRolling',{ type:'line', data:{ labels:PERF_DATA.datas.slice(janela), datasets:rollingDs }, options:{
    ...CHART_DEFAULTS,
    ..._CROSSHAIR_OPTS,
    plugins:{ ...CHART_DEFAULTS.plugins, ..._CROSSHAIR_OPTS.plugins },
    scales:{
      x:{ ...CHART_DEFAULTS.scales.x },
      y:{ ...CHART_DEFAULTS.scales.y, ticks:{ ...CHART_DEFAULTS.scales.y.ticks, callback: v=>v.toFixed(1)+'%' } }
    }
  } });
  document.getElementById('tbodyPerf').innerHTML = ativos.map(a=>{
    const d=PERF_DATA.ativos[a];
    return `<tr><td style="font-weight:700">${a}</td><td style="font-family:var(--mono)">${(d.vol*100).toFixed(2)}%</td><td class="${d.drawdown<-0.1?'col-bad':'col-good'}" style="font-family:var(--mono)">${(d.drawdown*100).toFixed(2)}%</td><td class="${d.ret_total>0?'col-good':'col-bad'}" style="font-family:var(--mono)">${(d.ret_total*100).toFixed(2)}%</td></tr>`;
  }).join('');
  const corr=PERF_DATA.correlacao;
  let html='<thead><tr><th></th>';
  corr.labels.forEach(l=>{ html+=`<th>${l}</th>`; });
  html+='</tr></thead><tbody>';
  corr.values.forEach((row,i)=>{ html+=`<tr><td style="font-weight:700">${corr.labels[i]}</td>`; row.forEach(v=>{ html+=`<td style="font-family:var(--mono)">${v.toFixed(2)}</td>`; }); html+='</tr>'; });
  html+='</tbody>';
  document.getElementById('corrTable').innerHTML=html;
}
// ── DOURO NEWS ────────────────────────────────────────────────────────────
function buildDouroNews() {
  const nd   = typeof NEWS_DATA !== 'undefined' ? NEWS_DATA : {};
  const news = nd.noticias || [];
  const ctx  = nd.ctx      || {};
  const rf   = nd.rf       || {};
  const ins  = nd.insight  || {};
  const liv  = nd.livro    || {};
  const fil  = nd.filme    || null;

  // ── Insight ───────────────────────────────────────────────────────
  const insEl = document.getElementById('newsInsight');
  if (insEl && ins.insight) {
    insEl.innerHTML = `
      <p style="font-size:14px;line-height:1.8;font-style:italic;color:var(--text);margin-bottom:8px;">"${ins.insight}"</p>
      <p style="font-size:12px;color:var(--text3);">— ${ins.gestor}</p>`;
  }

  // ── Market bar ────────────────────────────────────────────────────
  const mktEl = document.getElementById('newsMarket');
  if (mktEl) {
    const UP='#2fa874', DN='#d94141';
    const wtiPart = ctx.wti && ctx.wti!=='—' ? `
      <div style="display:flex;flex-direction:column;gap:4px;">
        <span style="font-size:9px;letter-spacing:1.8px;text-transform:uppercase;color:#d5d8c9;opacity:.45;">Petróleo WTI</span>
        <span style="font-size:14px;font-weight:500;color:#fff;">${ctx.wti} <span style="color:${ctx.wti_up?UP:DN};font-size:11px">${ctx.wti_var}</span></span>
      </div>` : '';
    mktEl.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:4px;">
        <span style="font-size:9px;letter-spacing:1.8px;text-transform:uppercase;color:#d5d8c9;opacity:.45;">Ibovespa</span>
        <span style="font-size:14px;font-weight:500;color:#fff;">${ctx.ibov||'—'} <span style="color:${ctx.ibov_up?UP:DN};font-size:11px">${ctx.ibov_var||''}</span></span>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;">
        <span style="font-size:9px;letter-spacing:1.8px;text-transform:uppercase;color:#d5d8c9;opacity:.45;">Dólar</span>
        <span style="font-size:14px;font-weight:500;color:#fff;">${ctx.dolar||'—'} <span style="color:${ctx.dolar_up?UP:DN};font-size:11px">${ctx.dolar_var||''}</span></span>
      </div>
      ${wtiPart}`;
  }

  // ── News cards ────────────────────────────────────────────────────
  const ORDEM = ['Empresas','Macro','Mercados','Política','Geral'];
  const LIMITS = {Empresas:6,Macro:4,Mercados:3,'Política':3,Geral:2};
  const byCat = {};
  news.forEach(n => {
    (n.categorias||['Geral']).forEach(cat => {
      if (!byCat[cat]) byCat[cat] = [];
      if (!byCat[cat].find(x=>x.link===n.link)) byCat[cat].push(n);
    });
  });
  let newsHtml = '';
  ORDEM.forEach(cat => {
    const items = (byCat[cat]||[]).slice(0, LIMITS[cat]||3);
    if (!items.length) return;
    newsHtml += `<div style="margin-top:28px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
        <div style="width:3px;height:3px;border-radius:50%;background:#b69d74;flex-shrink:0;"></div>
        <span style="font-size:10px;font-weight:600;letter-spacing:2.8px;text-transform:uppercase;color:var(--text3);white-space:nowrap;">${cat}</span>
        <div style="flex:1;height:1px;background:var(--border);"></div>
      </div>`;
    items.forEach((n,i) => {
      const tag = (n.tickers||[])[0] || '';
      if (i===0) {
        newsHtml += `<div style="background:#1f2839;border-radius:8px;padding:20px 22px;margin-bottom:10px;">
          ${tag?`<div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:700;margin-bottom:8px">${tag}</div>`:''}
          <div style="font-size:14.5px;font-weight:600;color:#fff;line-height:1.55;margin-bottom:12px;">${n.titulo}</div>
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <span style="font-size:11px;color:#d5d8c9;opacity:.5;">${n.fonte}</span>
            <a href="${n.link}" target="_blank" style="font-size:11px;color:#b69d74;text-decoration:none;">ler →</a>
          </div></div>`;
      } else {
        newsHtml += `<div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px 18px;margin-bottom:8px;">
          ${tag?`<div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:6px">${tag}</div>`:''}
          <div style="font-size:13px;font-weight:500;color:var(--text);line-height:1.6;margin-bottom:10px;">${n.titulo}</div>
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <span style="font-size:11px;color:var(--text3);">${n.fonte}</span>
            <a href="${n.link}" target="_blank" style="font-size:11px;color:var(--text3);text-decoration:none;opacity:.7;">ler →</a>
          </div></div>`;
      }
    });
    newsHtml += '</div>';
  });
  const cardsEl = document.getElementById('newsCards');
  if (cardsEl) cardsEl.innerHTML = newsHtml || '<p style="color:var(--text3);font-style:italic;text-align:center;padding:40px;">Nenhuma notícia disponível no momento.</p>';

  // ── RF Termômetro ─────────────────────────────────────────────────
  const rfEl = document.getElementById('newsRF');
  if (rfEl) {
    const rfRow = (o,fn,ft) => {
      const label=(o||{}).n||fn, taxa=(o||{}).t||ft;
      return `<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:10px;"><span style="color:var(--text2);font-weight:500;">${label}</span><span style="font-weight:700;color:var(--text);">${taxa}</span></div>`;
    };
    rfEl.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
        <div style="width:3px;height:3px;border-radius:50%;background:#b69d74;flex-shrink:0;"></div>
        <span style="font-size:10px;font-weight:600;letter-spacing:2.8px;text-transform:uppercase;color:var(--text3);white-space:nowrap;">Termômetro Renda Fixa</span>
        <div style="flex:1;height:1px;background:var(--border);"></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="card">
          <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:12px;">Curva DI Futuro</div>
          ${rfRow(rf.di_curto,'DI Jan 27','N/D')}${rfRow(rf.di_medio,'DI Jan 29','N/D')}${rfRow(rf.di_longo,'DI Jan 33','N/D')}
        </div>
        <div class="card">
          <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:12px;">Curva Real (ETFs)</div>
          ${rfRow(rf.ntnb_curta,'B5P211 (Curta)','N/D')}${rfRow(rf.ntnb_media,'IMAB11 (Geral)','N/D')}${rfRow(rf.ntnb_longa,'B5MB11 (Longa)','N/D')}
        </div>
      </div>`;
  }

  // ── Literatura + Filme ────────────────────────────────────────────
  const wkEl = document.getElementById('newsWeekly');
  if (wkEl) {
    const filmePart = fil ? `
      <div class="card" style="border-left:3px solid #b69d74;margin-top:12px;">
        <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:14px;">Dica de Fim de Semana</div>
        <div style="font-size:16px;font-weight:700;color:var(--text);margin-bottom:4px;">${fil.titulo}</div>
        <div style="font-size:12px;color:var(--text3);margin-bottom:10px;">${fil.categoria}</div>
        <div style="font-size:13px;color:var(--text2);line-height:1.6;">${fil.insight}</div>
      </div>` : '';
    wkEl.innerHTML = `
      <div class="card" style="border-left:3px solid #b69d74;">
        <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:14px;">Literatura da Semana</div>
        <div style="font-size:16px;font-weight:700;color:var(--text);margin-bottom:4px;">${liv.titulo||'—'}</div>
        <div style="font-size:12px;color:var(--text3);margin-bottom:10px;">por ${liv.autor||'—'}</div>
        <div style="font-size:13px;color:var(--text2);line-height:1.6;">${liv.desc||''}</div>
      </div>${filmePart}`;
  }

  // ── Fatos Relevantes CVM — bloco "Empresas" dentro do Douro News ──
  const wkEl2 = document.getElementById('newsWeekly');
  if (wkEl2) {
    const fatos = typeof FATOS_RELEVANTES !== 'undefined' ? FATOS_RELEVANTES : [];
    if (fatos.length > 0) {
      // Ordena por data_sort (YYYY-MM-DD) e mostra os 6 mais recentes no News
      const fatos_sorted = [...fatos].sort((a,b) => (b.data_sort||'').localeCompare(a.data_sort||''));
      const top = fatos_sorted.slice(0, 6);
      let frHtml = `<div style="margin-top:20px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
          <div style="width:3px;height:3px;border-radius:50%;background:#00677b;flex-shrink:0;"></div>
          <span style="font-size:10px;font-weight:600;letter-spacing:2.8px;text-transform:uppercase;color:var(--text3);">Fatos Relevantes CVM</span>
          <div style="flex:1;height:1px;background:var(--border);"></div>
          <span onclick="showPage('notificacoes',document.getElementById('navNotifItem'))" style="font-size:10px;color:#00677b;cursor:pointer;font-weight:600;">ver todos →</span>
        </div>`;
      top.forEach(f => {
        const linkPart = f.link
          ? `<a href="${f.link}" target="_blank" style="font-size:10px;color:#00677b;text-decoration:none;font-weight:600;">doc →</a>`
          : '';
        frHtml += `<div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:13px 16px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
          <div style="flex:1;min-width:0;">
            <div style="font-size:10px;letter-spacing:1.4px;text-transform:uppercase;color:#00677b;font-weight:700;margin-bottom:4px">${f.empresa}</div>
            <div style="font-size:12.5px;font-weight:500;color:var(--text);line-height:1.55;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${f.assunto}</div>
          </div>
          <div style="text-align:right;flex-shrink:0;">
            <div style="font-size:10px;${f.recente?'color:#00677b;font-weight:700':' color:var(--text3)'};font-family:var(--mono);margin-bottom:4px">${f.data}</div>
            ${linkPart}
          </div>
        </div>`;
      });
      frHtml += '</div>';
      wkEl2.innerHTML += frHtml;
    }
  }
}
// ── NOTIFICAÇÕES ──────────────────────────────────────────────────────────
let _notifJanelaFiltro = 'all';
let _notifTipoFiltro   = 'all';

function _notifSetJanela(janela, btn) {
  _notifJanelaFiltro = janela;
  document.querySelectorAll('.notif-janela-btn[data-janela]').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  _notifRenderAlertas();
}
function _notifSetTipo(tipo, btn) {
  _notifTipoFiltro = tipo;
  document.querySelectorAll('.notif-janela-btn[data-tipo]').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  _notifRenderAlertas();
}

function _notifRenderAlertas() {
  const alertas = typeof ALERTAS_NOTIF !== 'undefined' ? ALERTAS_NOTIF : [];
  let src = alertas;
  if (_notifJanelaFiltro !== 'all') src = src.filter(a => a.janela === _notifJanelaFiltro);
  if (_notifTipoFiltro   !== 'all') src = src.filter(a => a.tipo  === _notifTipoFiltro);

  // KPI strip — top movers per janela
  const kpiEl = document.getElementById('notifKpiStrip');
  if (kpiEl) {
    const byJanela = {'1d': [], '7d': [], '21d': []};
    alertas.forEach(a => { if (byJanela[a.janela]) byJanela[a.janela].push(a); });
    kpiEl.innerHTML = ['1d','7d','21d'].map(j => {
      const cnt = byJanela[j].length;
      const worst = byJanela[j][0]; // already sorted by abs variacao
      const varStr = worst ? (worst.variacao >= 0 ? `+${worst.variacao.toFixed(2)}%` : `${worst.variacao.toFixed(2)}%`) : '—';
      const varCol = worst ? (worst.variacao > 0 ? '#d94141' : '#00677b') : 'var(--text3)';
      return `<div class="card" style="padding:14px 16px;border-left:3px solid rgba(0,103,123,.2);">
        <div style="font-size:9px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.10em;margin-bottom:8px">Janela ${j}</div>
        <div style="font-size:22px;font-weight:700;color:#00677b;font-family:var(--mono);margin-bottom:4px">${cnt}</div>
        <div style="font-size:11px;color:var(--text3);">alertas</div>
        ${worst ? `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:11px;display:flex;justify-content:space-between;align-items:center;"><span style="font-weight:600">${formatAtivoLabel(worst.ticker)}</span><span style="color:${varCol};font-family:var(--mono);font-weight:700">${varStr}</span></div>` : ''}
      </div>`;
    }).join('');
  }

  const countEl = document.getElementById('notifAlertasCount');
  if (countEl) countEl.textContent = `${src.length} alerta(s)`;

  const grid = document.getElementById('notifAlertasGrid');
  if (!grid) return;
  if (!src.length) {
    grid.innerHTML = `<div class="card" style="grid-column:1/-1;text-align:center;color:var(--text3);padding:40px;">Nenhum alerta para os filtros selecionados.</div>`;
    return;
  }
  // Badge for sidebar — hidden by design
  const badge = document.getElementById('notifBadgeNav');
  if (badge) badge.style.display = 'none';
  grid.innerHTML = src.slice(0, 60).map(a => {
    const isUp  = a.variacao > 0;
    const clr   = isUp ? '#d94141' : '#00677b';
    const arrow = isUp ? '▲' : '▼';
    const varStr = `${isUp?'+':''}${a.variacao.toFixed(2)}%`;
    const badgeTxt = a.tipo === 'spread' ? 'SPREAD' : 'TAXA';
    const badgeJanela = a.janela.toUpperCase();
    const _expMaxPct = raw => (raw > 0 && raw < 1) ? raw * 100 : raw;
    const expMax = a.exposicao_maxima_rating != null ? _expMaxPct(a.exposicao_maxima_rating) : null;
    return `<div class="alerta-card ${isUp?'alerta-up':'alerta-dn'}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
        <div>
          <div style="font-size:13px;font-weight:700;color:var(--text);font-family:var(--mono)">${formatAtivoLabel(a.ticker)}</div>
          <div style="display:flex;gap:5px;margin-top:4px">
            <span style="font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;background:rgba(0,103,123,.1);color:#00677b;letter-spacing:.08em">${badgeTxt}</span>
            <span style="font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;background:rgba(113,128,150,.1);color:var(--text3);letter-spacing:.08em">${badgeJanela}</span>
            ${a.rating_douro ? `<span style="font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;background:rgba(182,157,116,.12);color:#b69d74;letter-spacing:.08em">${a.rating_douro}</span>` : ''}
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-size:18px;font-weight:800;color:${clr};font-family:var(--mono)">${arrow} ${varStr}</div>
          <div style="font-size:10px;color:var(--text3);margin-top:2px">${a.data_ref} → ${a.data_atual}</div>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text3);border-top:1px solid var(--border);padding-top:8px;margin-top:4px">
        <span>Atual: <strong style="color:var(--text);font-family:var(--mono)">${a.atual.toFixed(3)}%</strong></span>
        <span>Ref: <strong style="color:var(--text);font-family:var(--mono)">${a.ref.toFixed(3)}%</strong></span>
      </div>
      ${expMax != null ? `<div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text3);margin-top:6px;padding-top:6px;border-top:1px dashed rgba(0,0,0,.08)"><span>Lim. Exp. Rating</span><strong style="font-family:var(--mono);color:var(--text)">${expMax.toFixed(2)}%</strong></div>` : ''}
    </div>`;
  }).join('');
}

let _notifFRJanela = 0; // 0=todos, 7=últimos 7 dias, 15=últimos 15 dias, 30=último mês
function _notifFRSetJanela(dias, btn) {
  _notifFRJanela = dias;
  document.querySelectorAll('.notif-janela-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  _notifRenderFR();
}

function _notifRenderFR() {
  const fatos = typeof FATOS_RELEVANTES !== 'undefined' ? FATOS_RELEVANTES : [];
  const q = (document.getElementById('notifFRSearch')?.value || '').toLowerCase().trim();
  let src = fatos;
  if (q) src = src.filter(f =>
    (f.empresa||'').toLowerCase().includes(q) ||
    (f.assunto||'').toLowerCase().includes(q) ||
    (f.denom_cvm||'').toLowerCase().includes(q)
  );
  if (_notifFRJanela > 0) {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - _notifFRJanela);
    const cutoffStr = cutoff.toISOString().slice(0, 10); // YYYY-MM-DD
    src = src.filter(f => (f.data_sort || '') >= cutoffStr);
  }
  src = [...src].sort((a, b) => (b.data_sort || '').localeCompare(a.data_sort || ''));

  const nRecentes = fatos.filter(f => f.recente).length;
  const countEl = document.getElementById('notifFRCount');
  if (countEl) countEl.textContent = src.length !== fatos.length
    ? `${src.length} de ${fatos.length} fato(s)${nRecentes > 0 ? ' · ' + nRecentes + ' nos últ. 7 dias' : ''}`
    : `${src.length} fato(s)${nRecentes > 0 ? ' · ' + nRecentes + ' nos últ. 7 dias' : ''}`;

  const el = document.getElementById('notifFRTable');
  if (!el) return;
  if (!src.length) {
    el.innerHTML = `<div style="text-align:center;color:var(--text3);padding:40px;font-size:13px;">${fatos.length ? 'Nenhum resultado para a busca.' : 'Nenhum Fato Relevante encontrado para os emissores da carteira.'}</div>`;
    return;
  }

  // Dispatch para o design selecionado
  if (_notifDesign === 2) { _notifRenderFRDesign2(src); return; }
  if (_notifDesign === 3) { _notifRenderFRDesign3(src); return; }
  if (_notifDesign === 4) { _notifRenderFRDesign4(src); return; }
  if (_notifDesign === 5) { _notifRenderFRDesign5(src); return; }
  if (_notifDesign === 6) { _notifRenderFRDesign6(src); return; }
  if (_notifDesign === 7) { _notifRenderFRDesign7(src); return; }
  if (_notifDesign === 8) { _notifRenderFRDesign8(src); return; }
  if (_notifDesign === 9) { _notifRenderFRDesign9(src); return; }
  if (_notifDesign === 10) { _notifRenderFRDesign10(src); return; }

  // Design 1 — padrão: tabela + timeline
  el.innerHTML = src.map((f, i) => {
    const recBadge = f.recente
      ? `<span style="background:linear-gradient(135deg,#1f2839,#00677b);color:#f5f5ef;font-size:8px;font-weight:800;padding:2px 6px;border-radius:4px;letter-spacing:.06em;margin-left:6px;vertical-align:middle;">7D</span>`
      : '';
    const dotColor = f.recente ? '#00677b' : 'var(--border)';
    const linkBtn = f.link
      ? `<a href="${f.link}" target="_blank" onclick="event.stopPropagation()" style="font-size:11px;color:#00677b;text-decoration:none;font-weight:600;white-space:nowrap;">Abrir →</a>`
      : `<span style="font-size:11px;color:var(--text3);opacity:.4">—</span>`;
    const rowBg = f.recente ? 'background:rgba(0,103,123,.025);' : '';
    const expandId = `frexp_${i}`;
    return `<div onclick="_frToggleRow('${expandId}')" style="${rowBg}cursor:pointer;">
      <div style="display:grid;grid-template-columns:28px 140px 1fr 100px 90px;align-items:center;border-bottom:1px solid var(--border);transition:background .15s;" onmouseover="this.style.background='rgba(0,103,123,.04)'" onmouseout="this.style.background=''">
        <div style="display:flex;flex-direction:column;align-items:center;padding:10px 0 10px 10px;">
          <div style="width:8px;height:8px;border-radius:50%;background:${dotColor};flex-shrink:0;"></div>
          ${i < src.length-1 ? `<div style="width:1px;flex:1;min-height:14px;background:var(--border);margin-top:3px;"></div>` : ''}
        </div>
        <div style="padding:10px 12px;font-size:11px;font-weight:700;color:#00677b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${f.empresa}${recBadge}</div>
        <div style="padding:10px 12px;font-size:12px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${f.assunto}</div>
        <div style="padding:10px 12px;font-size:11px;color:var(--text3);font-family:var(--mono);${f.recente?'color:#00677b;font-weight:700':''}">${f.data}</div>
        <div style="padding:10px 12px;">${linkBtn}</div>
      </div>
      <div id="${expandId}" style="display:none;background:rgba(0,103,123,.03);border-bottom:1px solid var(--border);padding:14px 18px 14px 38px;font-size:12px;color:var(--text);line-height:1.7;animation:frSlide .18s ease;">
        <div style="font-size:10px;color:var(--text3);font-style:italic;margin-bottom:6px;">${f.denom_cvm || ''}</div>
        <div style="font-size:13px;font-weight:500;line-height:1.65;margin-bottom:10px;">${f.assunto}</div>
        ${f.link ? `<a href="${f.link}" target="_blank" style="font-size:11px;color:#00677b;text-decoration:none;font-weight:600;">Abrir documento completo →</a>` : ''}
      </div>
    </div>`;
  }).join('');
}

function _frToggleRow(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const open = el.style.display !== 'none';
  el.style.display = open ? 'none' : 'block';
}

let _notifTab = 'alertas';

function _notifSetTab(tab) {
  _notifTab = tab;
  const tabs = { fatos: 'notifTabFatos', alertas: 'notifTabAlertas', exposicao: 'notifTabExposicao' };
  const panels = { fatos: 'notifPanelFatos', alertas: 'notifPanelAlertas', exposicao: 'notifPanelExposicao' };
  Object.entries(tabs).forEach(([k, id]) => {
    const el = document.getElementById(id);
    if (!el) return;
    const active = k === tab;
    el.style.borderBottomColor = active ? '#00677b' : 'transparent';
    el.style.color = active ? '#00677b' : 'var(--text3)';
  });
  Object.entries(panels).forEach(([k, id]) => {
    const el = document.getElementById(id);
    if (el) el.style.display = k === tab ? '' : 'none';
  });
  if (tab === 'alertas') _notifRenderAlertas();
  if (tab === 'exposicao') _notifRenderExposicao();
  if (tab === 'fatos') _notifRenderFR();
}

function _notifRenderExposicao() {
  const ativos = typeof ATIVOS !== 'undefined' ? ATIVOS : [];
  const plPorCarteira = typeof PL_POR_CARTEIRA !== 'undefined' ? PL_POR_CARTEIRA : {};
  const _expMaxPct = raw => (raw > 0 && raw < 1) ? raw * 100 : raw;

  // Agregar saldo por (carteira, emissor)
  const ceMap = {};
  ativos.forEach(a => {
    if (!a.emissor || !a.carteira) return;
    const key = a.carteira + '|||' + a.emissor;
    if (!ceMap[key]) {
      ceMap[key] = {
        carteira: a.carteira,
        emissor: a.emissor,
        saldo: 0,
        rating_douro: a['Rating Douro'] || '—',
        exposicao_maxima_rating: a.exposicao_maxima_rating,
        status: a.Status || '—',
      };
    }
    ceMap[key].saldo += (a.saldo || 0);
  });

  // Filtrar pares (carteira, emissor) acima do limite de exposição do respectivo PL
  const acimaLimite = Object.values(ceMap).filter(ce => {
    const plCart = plPorCarteira[ce.carteira] || 0;
    if (plCart <= 0) return false;
    const pct = ce.saldo / plCart * 100;
    const expMax = _expMaxPct(ce.exposicao_maxima_rating || 0);
    const isReprovado = ce.status === 'Reprovado';
    return (expMax > 0 && pct > expMax) || (isReprovado && pct > 0);
  });

  // Ordenar pelo maior excesso relativo
  acimaLimite.sort((a, b) => {
    const pA = (plPorCarteira[a.carteira] || 1); const pB = (plPorCarteira[b.carteira] || 1);
    return (b.saldo / pB) - (a.saldo / pA);
  });

  const countEl = document.getElementById('notifExpCount');
  if (countEl) countEl.textContent = `${acimaLimite.length} alerta(s)`;
  const badge = document.getElementById('notifBadgeExposicao');
  if (badge) {
    badge.style.display = acimaLimite.length ? 'inline-block' : 'none';
    badge.textContent = acimaLimite.length;
  }
  const grid = document.getElementById('notifExpGrid');
  if (!grid) return;
  if (!acimaLimite.length) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text3);padding:40px;font-size:13px;">Nenhum emissor acima do limite de exposição por carteira.</div>';
    return;
  }
  grid.innerHTML = acimaLimite.map(ce => {
    const plCart = plPorCarteira[ce.carteira] || 0;
    const pctEm = plCart > 0 ? (ce.saldo / plCart * 100).toFixed(2) : '—';
    const expMax = _expMaxPct(ce.exposicao_maxima_rating || 0);
    const excessoNum = plCart > 0 && expMax > 0 ? (ce.saldo / plCart * 100 - expMax) : null;
    const excessoStr = excessoNum !== null ? (excessoNum >= 0 ? '+' : '') + excessoNum.toFixed(2) + '%' : '—';
    const excessoColor = excessoNum !== null && excessoNum > 0 ? '#d94141' : '#b69d74';
    const excessoLabel = excessoNum !== null && excessoNum <= 0 ? 'Margem' : 'Excesso';
    const isReprovado = ce.status === 'Reprovado';
    return `<div style="background:var(--surface);border:1px solid rgba(217,65,65,.35);border-left:3px solid #d94141;border-radius:10px;padding:16px 18px;">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:10px;">
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--text)">${ce.emissor}</div>
          <div style="margin-top:5px;display:flex;gap:4px;flex-wrap:wrap;">
            <span style="font-size:9px;font-weight:700;padding:2px 8px;border-radius:3px;background:rgba(31,40,57,.12);color:var(--text3);border:1px solid var(--border);letter-spacing:.06em">${ce.carteira}</span>
            ${isReprovado ? '<span style="font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;background:rgba(217,65,65,.12);color:#d94141;letter-spacing:.06em;">REPROVADO</span>' : ''}
          </div>
        </div>
        <span style="background:rgba(217,65,65,.12);color:#d94141;border:1px solid rgba(217,65,65,.3);border-radius:4px;padding:2px 8px;font-size:10px;font-weight:700;white-space:nowrap;">⚠ ACIMA DO LIMITE</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px;">
        <div><div style="font-size:9px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.06em;margin-bottom:3px;">% do PL Cart.</div><div style="font-size:15px;font-weight:700;color:#d94141;font-family:var(--mono)">${pctEm}%</div></div>
        <div><div style="font-size:9px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.06em;margin-bottom:3px;">Limite (Rating)</div><div style="font-size:15px;font-weight:700;color:var(--text3);font-family:var(--mono)">${expMax > 0 ? expMax.toFixed(2)+'%' : '—'}</div></div>
        <div><div style="font-size:9px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.06em;margin-bottom:3px;">${excessoLabel}</div><div style="font-size:15px;font-weight:700;color:${excessoColor};font-family:var(--mono)">${excessoStr}</div></div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:10px;color:var(--text3)">Saldo: ${fmtBRL(ce.saldo)} · Rating: ${ce.rating_douro} · Status: ${ce.status}</span>
        <button onclick="showPage('composicao',document.getElementById('navComposicaoItem'));setTimeout(()=>{document.getElementById('ativosSearch').value='${ce.emissor}'.replace(/'/g,\\"\\");_renderTbodyAtivos();},200)" style="font-size:10px;color:#00677b;background:none;border:1px solid rgba(0,103,123,.3);border-radius:4px;padding:3px 8px;cursor:pointer;font-weight:600;">Ver na composição →</button>
      </div>
    </div>`;
  }).join('');
}

// ── DESIGN SWITCHER ───────────────────────────────────────────────────────
let _notifDesign = 1;
function _notifApplyDesign(val) {
  _notifDesign = parseInt(val) || 1;
  _notifSetTab('fatos');
}

function _notifRenderFRDesign2(src) {
  const el = document.getElementById('notifFRTable');
  if (!el) return;
  el.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;padding:14px;">`
    + src.map((f,i) => {
      const recBadge = f.recente ? `<span style="background:linear-gradient(135deg,#1f2839,#00677b);color:#f5f5ef;font-size:8px;font-weight:800;padding:2px 6px;border-radius:4px;letter-spacing:.06em;margin-left:6px;">7D</span>` : '';
      const expandId = `frexp2_${i}`;
      return `<div class="nd2-card" onclick="_frToggleRow('${expandId}')">
        <div class="nd2-em">${f.empresa}${recBadge}</div>
        <div class="nd2-assunto">${f.assunto}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:10px;color:var(--text3);font-family:var(--mono)">${f.data}</span>
          ${f.link ? `<a href="${f.link}" target="_blank" onclick="event.stopPropagation()" style="font-size:11px;color:#00677b;text-decoration:none;font-weight:600;">Abrir →</a>` : ''}
        </div>
        <div id="${expandId}" style="display:none;margin-top:10px;padding-top:10px;border-top:1px solid rgba(0,103,123,.15);font-size:11px;color:var(--text3);font-style:italic;animation:frSlide .18s ease;">${f.denom_cvm || ''}</div>
      </div>`;
    }).join('') + `</div>`;
}

function _notifRenderFRDesign3(src) {
  const el = document.getElementById('notifFRTable');
  if (!el) return;
  el.innerHTML = `<div style="padding:6px 14px;">` + src.map((f,i) => {
    const dotColor = f.recente ? '#00677b' : '#b69d74';
    const expandId = `frexp3_${i}`;
    return `<div class="nd3-item" onclick="_frToggleRow('${expandId}')">
      <div class="nd3-dot" style="background:${dotColor};${f.recente ? 'box-shadow:0 0 8px rgba(0,103,123,.5)' : ''}"></div>
      <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:2px;">
          <span style="font-size:11px;font-weight:700;color:#00677b;text-transform:uppercase;letter-spacing:.06em;">${f.empresa}</span>
          ${f.recente ? `<span style="background:rgba(0,103,123,.12);color:#00677b;border:1px solid rgba(0,103,123,.25);border-radius:10px;padding:1px 8px;font-size:9px;font-weight:700;">NOVO</span>` : ''}
          <span style="margin-left:auto;font-size:10px;color:var(--text3);font-family:var(--mono)">${f.data}</span>
        </div>
        <div style="font-size:12px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${f.assunto}</div>
        <div id="${expandId}" style="display:none;margin-top:8px;font-size:11px;color:var(--text3);line-height:1.6;animation:frSlide .18s ease;">
          ${f.denom_cvm ? `<div style="font-style:italic;margin-bottom:4px;">${f.denom_cvm}</div>` : ''}
          ${f.link ? `<a href="${f.link}" target="_blank" style="font-size:11px;color:#00677b;text-decoration:none;font-weight:600;">Abrir documento →</a>` : ''}
        </div>
      </div>
    </div>`;
  }).join('') + `</div>`;
}

function _notifRenderFRDesign4(src) {
  const el = document.getElementById('notifFRTable');
  if (!el) return;
  el.innerHTML = `<div style="padding:8px 16px;">` + src.map(f => `
    <div class="nd4-row">
      <span class="nd4-em">${f.empresa}</span>
      <span style="font-size:12px;color:var(--text);flex:1;">${f.assunto}</span>
      ${f.link ? `<a href="${f.link}" target="_blank" style="font-size:11px;color:#00677b;text-decoration:none;font-weight:600;margin:0 8px;">↗</a>` : ''}
      <span class="nd4-date">${f.data}</span>
    </div>`).join('') + `</div>`;
}

function _notifRenderFRDesign5(src) {
  const el = document.getElementById('notifFRTable');
  if (!el) return;
  const recentes  = src.filter(f => f.recente);
  const anteriores = src.filter(f => !f.recente);
  const colHtml = (title, color, bg, items) => `
    <div class="nd5-col">
      <div class="nd5-col-title" style="background:${bg};color:${color};">${title} <span style="opacity:.6">${items.length}</span></div>
      ${items.slice(0,12).map((f,i) => {
        const expandId = `frexp5_${title}_${i}`;
        return `<div class="nd5-card" onclick="_frToggleRow('${expandId}')">
          <div style="font-size:10px;font-weight:700;color:${color};text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">${f.empresa}</div>
          <div style="font-size:12px;color:var(--text);line-height:1.45;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">${f.assunto}</div>
          <div style="font-size:10px;color:var(--text3);margin-top:4px;font-family:var(--mono)">${f.data}</div>
          <div id="${expandId}" style="display:none;margin-top:8px;font-size:11px;color:var(--text3);animation:frSlide .18s ease;">
            ${f.link ? `<a href="${f.link}" target="_blank" style="color:#00677b;text-decoration:none;font-weight:600;">Abrir →</a>` : ''}
          </div>
        </div>`;
      }).join('')}
    </div>`;
  el.innerHTML = `<div style="display:flex;gap:12px;padding:12px;overflow-x:auto;">
    ${colHtml('Últimos 7 dias','#00677b','rgba(0,103,123,.1)',recentes)}
    ${colHtml('Anteriores','#b69d74','rgba(182,157,116,.1)',anteriores)}
  </div>`;
}

function _notifRenderFRDesign6(src) {
  const el = document.getElementById('notifFRTable');
  if (!el) return;
  const hero = src[0];
  const rest = src.slice(1);
  el.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;padding:14px;">
    ${hero ? `<div class="nd6-hero">
      <div style="font-size:9px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#00677b;margin-bottom:8px;">DESTAQUE</div>
      <div style="font-size:13px;font-weight:700;color:var(--text);line-height:1.5;margin-bottom:6px;">${hero.assunto}</div>
      <div style="font-size:11px;color:var(--text3)">${hero.empresa} · ${hero.data}</div>
      ${hero.link ? `<a href="${hero.link}" target="_blank" style="display:inline-block;margin-top:10px;font-size:11px;color:#00677b;text-decoration:none;font-weight:600;border:1px solid rgba(0,103,123,.3);border-radius:4px;padding:3px 10px;">Abrir →</a>` : ''}
    </div>` : ''}
    ${rest.map((f,i) => {
      const expandId = `frexp6_${i}`;
      return `<div class="nd6-card" onclick="_frToggleRow('${expandId}')">
        <div style="font-size:10px;font-weight:700;color:#00677b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">${f.empresa} ${f.recente ? '●' : ''}</div>
        <div style="font-size:12px;color:var(--text);line-height:1.5;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;">${f.assunto}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
          <span style="font-size:10px;color:var(--text3);font-family:var(--mono)">${f.data}</span>
          ${f.link ? `<a href="${f.link}" target="_blank" onclick="event.stopPropagation()" style="font-size:11px;color:#00677b;text-decoration:none;font-weight:600;">Abrir →</a>` : ''}
        </div>
        <div id="${expandId}" style="display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:11px;color:var(--text3);font-style:italic;animation:frSlide .18s ease;">${f.denom_cvm || ''}</div>
      </div>`;
    }).join('')}
  </div>`;
}

function _notifRenderFRDesign7(src) {
  const el = document.getElementById('notifFRTable');
  if (!el) return;
  el.innerHTML = `<div class="nd7-wrap" style="max-height:500px;overflow-y:auto;">
    <div style="font-size:10px;color:#2a5a40;margin-bottom:10px;border-bottom:1px solid rgba(122,255,178,.08);padding-bottom:8px;">// fatos_relevantes[${src.length}] — carteira douro capital</div>
    ${src.map((f,i) => {
      const expandId = `frexp7_${i}`;
      return `<div class="nd7-line" onclick="_frToggleRow('${expandId}');event.currentTarget.style.background='rgba(122,255,178,.04)'" style="flex-direction:column;cursor:pointer;">
        <div style="display:flex;gap:10px;align-items:baseline;">
          <span class="nd7-ts">${f.data}</span>
          <span class="nd7-em">${f.empresa}</span>
          <span class="nd7-msg">${f.assunto}</span>
          ${f.recente ? `<span class="nd7-tag">NEW</span>` : ''}
        </div>
        <div id="${expandId}" style="display:none;padding:6px 0 2px 60px;color:#4a8a6a;font-size:11px;animation:frSlide .18s ease;">
          ↳ ${f.denom_cvm || f.assunto}
          ${f.link ? ` &nbsp;<a href="${f.link}" target="_blank" style="color:#7affb2;text-decoration:none;">[link]</a>` : ''}
        </div>
      </div>`;
    }).join('')}
  </div>`;
}

function _notifRenderFRDesign8(src) {
  const el = document.getElementById('notifFRTable');
  if (!el) return;
  el.innerHTML = `<div class="nd8-wrap" style="max-height:520px;overflow-y:auto;">
    <div style="position:absolute;top:-60px;right:-60px;width:200px;height:200px;background:radial-gradient(circle,rgba(0,103,123,.15),transparent 70%);border-radius:50%;pointer-events:none;"></div>
    ${src.map((f,i) => {
      const expandId = `frexp8_${i}`;
      return `<div class="nd8-card" onclick="_frToggleRow('${expandId}')">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
          <span class="nd8-em">${f.empresa} ${f.recente ? '<span style="font-size:8px;vertical-align:middle;background:rgba(0,180,200,.15);border:1px solid rgba(0,180,200,.3);border-radius:3px;padding:1px 5px;margin-left:4px;">NOVO</span>' : ''}</span>
          <span style="font-size:10px;color:rgba(200,210,220,.4);font-family:var(--mono)">${f.data}</span>
        </div>
        <div style="font-size:12px;color:rgba(230,235,240,.8);line-height:1.55;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">${f.assunto}</div>
        <div id="${expandId}" style="display:none;margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,.06);font-size:11px;color:rgba(200,210,220,.55);animation:frSlide .18s ease;">
          ${f.denom_cvm ? `<div style="font-style:italic;margin-bottom:4px;">${f.denom_cvm}</div>` : ''}
          ${f.link ? `<a href="${f.link}" target="_blank" style="color:rgba(0,180,200,.8);text-decoration:none;font-weight:600;font-size:11px;">Abrir documento →</a>` : ''}
        </div>
      </div>`;
    }).join('')}
  </div>`;
}

function _notifRenderFRDesign9(src) {
  const el = document.getElementById('notifFRTable');
  if (!el) return;
  const colors = ['#00c8ff','#00e5a0','#b69d74','#ff6b9d','#a78bfa'];
  el.innerHTML = `<div class="nd9-wrap" style="max-height:520px;overflow-y:auto;">
    <div class="nd9-glow" style="top:-50px;left:-50px;"></div>
    ${src.map((f,i) => {
      const c = colors[i % colors.length];
      const expandId = `frexp9_${i}`;
      return `<div class="nd9-row" onclick="_frToggleRow('${expandId}')">
        <div class="nd9-indicator" style="background:linear-gradient(${c},${c}44);box-shadow:0 0 6px ${c}55;"></div>
        <span class="nd9-em" style="color:${c}">${f.empresa}</span>
        <span class="nd9-assunto">${f.assunto}</span>
        ${f.recente ? `<span style="background:rgba(0,200,255,.1);border:1px solid rgba(0,200,255,.25);color:#00c8ff;border-radius:3px;padding:1px 7px;font-size:9px;font-weight:700;white-space:nowrap;">NOVO</span>` : ''}
        ${f.link ? `<a href="${f.link}" target="_blank" onclick="event.stopPropagation()" style="font-size:11px;color:${c};text-decoration:none;font-weight:600;white-space:nowrap;">↗</a>` : ''}
        <span class="nd9-date">${f.data}</span>
      </div>
      <div id="${expandId}" style="display:none;padding:8px 8px 8px 23px;font-size:11px;color:rgba(200,210,220,.55);background:rgba(0,200,255,.03);animation:frSlide .18s ease;">
        ${f.denom_cvm || f.assunto}
      </div>`;
    }).join('')}
  </div>`;
}

function _notifRenderFRDesign10(src) {
  const el = document.getElementById('notifFRTable');
  if (!el) return;
  // Orbital: mostra até 14 nós em órbitas, resto em lista
  const orbNos = src.slice(0, 14);
  const rest   = src.slice(14);
  const W = 560, H = 480, cx = W/2, cy = H/2;
  const rings = [
    { r: 90,  items: orbNos.slice(0, 4),  color: '#d94141' },
    { r: 165, items: orbNos.slice(4, 9),  color: '#b69d74' },
    { r: 230, items: orbNos.slice(9, 14), color: '#00677b' },
  ];
  let nodesHtml = '';
  rings.forEach(ring => {
    ring.items.forEach((f, idx) => {
      const angle = (2 * Math.PI / ring.items.length) * idx - Math.PI/2;
      const x = cx + ring.r * Math.cos(angle);
      const y = cy + ring.r * Math.sin(angle);
      const initials = (f.empresa || '?').slice(0,3).toUpperCase();
      nodesHtml += `<div class="nd10-node" style="left:${x}px;top:${y}px;">
        <div class="nd10-node-dot" style="background:linear-gradient(135deg,${ring.color}44,${ring.color}22);border:2px solid ${ring.color};color:${ring.color};box-shadow:0 0 ${f.recente?'14px':'6px'} ${ring.color}55;">${initials}</div>
        <div class="nd10-tooltip">
          <div style="font-size:10px;font-weight:700;color:${ring.color};letter-spacing:.06em;text-transform:uppercase;margin-bottom:3px;">${f.empresa}</div>
          <div style="font-size:11px;color:#c8d0dc;line-height:1.5;margin-bottom:4px;">${f.assunto.slice(0,80)}${f.assunto.length>80?'…':''}</div>
          <div style="font-size:10px;color:rgba(200,210,220,.5)">${f.data}</div>
          ${f.link ? `<a href="${f.link}" target="_blank" style="font-size:11px;color:${ring.color};text-decoration:none;font-weight:600;display:block;margin-top:4px;">Abrir →</a>` : ''}
        </div>
      </div>`;
    });
  });
  const ringsHtml = rings.map(ring =>
    `<div class="nd10-ring" style="width:${ring.r*2}px;height:${ring.r*2}px;border-color:${ring.color}22;"></div>`
  ).join('');
  const listHtml = rest.length ? `<div style="margin-top:12px;font-size:11px;color:var(--text3);text-align:center;padding:8px 0 4px;">
    + ${rest.length} fatos adicionais &nbsp;<button onclick="this.closest('.nd10-list').querySelector('.nd10-rest').style.display='block';this.remove()" style="font-size:11px;color:#00677b;background:none;border:none;cursor:pointer;font-weight:600;">Ver todos</button>
    <div class="nd10-rest" style="display:none;margin-top:8px;text-align:left;">
      ${rest.map(f => `<div style="padding:6px 0;border-bottom:1px solid var(--border);font-size:12px;color:var(--text);">
        <span style="font-size:10px;font-weight:700;color:#00677b;text-transform:uppercase;margin-right:8px;">${f.empresa}</span>${f.assunto}
        <span style="font-size:10px;color:var(--text3);margin-left:8px;font-family:var(--mono)">${f.data}</span>
      </div>`).join('')}
    </div>
  </div>` : '';
  el.innerHTML = `<div style="padding:14px;">
    <div class="nd10-wrap" style="height:${H}px;width:${W}px;max-width:100%;margin:0 auto;">
      ${ringsHtml}
      <div class="nd10-center">
        <div style="font-size:9px;font-weight:700;letter-spacing:.08em;color:#f5f5ef;text-transform:uppercase;line-height:1.3;text-align:center;">Fatos<br>Relevantes</div>
        <div style="font-size:16px;font-weight:800;color:#b69d74;margin-top:2px;">${src.length}</div>
      </div>
      ${nodesHtml}
    </div>
    <div class="nd10-list">${listHtml}</div>
  </div>`;
}

function _notifBuildBriefing() {
  const fatos   = typeof FATOS_RELEVANTES !== 'undefined' ? FATOS_RELEVANTES : [];
  const alertas = typeof ALERTAS_NOTIF    !== 'undefined' ? ALERTAS_NOTIF    : [];
  const ativos  = typeof ATIVOS           !== 'undefined' ? ATIVOS           : [];

  const nFR       = fatos.length;
  const nRecentes = fatos.filter(f => f.recente).length;
  const nAlertas  = alertas.length;
  const nCrit1d   = alertas.filter(a => a.janela === '1d').length;
  const nExp      = ativos.filter(a => a.acima_exposicao_maxima).length;

  const partes = [];
  if (nRecentes > 0) partes.push(`<strong>${nRecentes} fato(s) relevante(s)</strong> publicado(s) nos últimos 7 dias`);
  else if (nFR > 0)  partes.push(`<strong>${nFR} fato(s) relevante(s)</strong> disponíveis para os emissores da carteira`);
  else               partes.push(`<strong>Nenhum fato relevante</strong> encontrado para os emissores da carteira`);

  if (nAlertas > 0) {
    partes.push(`<strong>${nAlertas} alerta(s) de spread/taxa</strong>${nCrit1d > 0 ? ` (${nCrit1d} no último dia)` : ''}`);
  } else {
    partes.push(`<strong>nenhum alerta</strong> de spread/taxa no momento`);
  }

  if (nExp > 0) {
    partes.push(`<strong style="color:#d94141">${nExp} emissor(es) acima do limite de exposição</strong> — ação recomendada`);
  } else {
    partes.push(`<strong>nenhum emissor</strong> acima do limite de exposição`);
  }

  const el = document.getElementById('notifBriefingText');
  if (el) el.innerHTML = partes.join(' · ') + '.';
}

function buildNotificacoes() {
  _notifSetTab('alertas');
  _notifBuildBriefing();
  // Count badges
  const ativos = typeof ATIVOS !== 'undefined' ? ATIVOS : [];
  const nExp = ativos.filter(a => a.acima_exposicao_maxima).length;
  const badgeExp = document.getElementById('notifBadgeExposicao');
  if (badgeExp) { badgeExp.style.display = nExp ? 'inline-block' : 'none'; badgeExp.textContent = nExp; }
  const alertas = typeof ALERTAS_NOTIF !== 'undefined' ? ALERTAS_NOTIF : [];
  const badgeAl = document.getElementById('notifBadgeAlertas');
  if (badgeAl) { badgeAl.style.display = alertas.length ? 'inline-block' : 'none'; badgeAl.textContent = alertas.length; }
}

// ── SCORECARD ─────────────────────────────────────────────────────────────
function buildScorecard() {
  const frame = document.getElementById('scorecardFrame');
  if (!frame) return;
  // Só carrega o src na primeira vez que a página é aberta
  // Nas visitas seguintes o iframe já está carregado — não recarrega
  if (!frame.src || frame.src === window.location.href || frame.src === 'about:blank') {
    if (SCORECARD_SRC && SCORECARD_SRC !== 'null') {
      frame.src = SCORECARD_SRC;
    } else {
      // Fallback: scorecard não encontrado — exibir mensagem dentro do iframe
      frame.srcdoc = '<html><body style="font-family:Montserrat,sans-serif;display:flex;'
        + 'align-items:center;justify-content:center;height:100vh;margin:0;'
        + 'background:#f4f5f0;color:#718096;flex-direction:column;gap:12px">'
        + '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#dde0d8" stroke-width="1.5">'
        + '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>'
        + '<p style="font-size:13px;font-weight:500">scorecard.html não encontrado.</p>'
        + '<p style="font-size:11px;opacity:.6">Execute gerar_scorecard.py primeiro.</p>'
        + '</body></html>';
    }
  }
}
// ══════════════════════════════════════════════════════════════════════════
// COMPRAS E VENDAS
// ══════════════════════════════════════════════════════════════════════════
let _cvFilOp  = 'todos';
let _cvSortKey = 'data_operacao';
let _cvSortAsc = false;
let _cvSelAtivos = new Set();
let _cvSelAtivoDates = new Map();   // ativo → timestamp da data_operacao clicada
let _cvChart = null;
let _cvCarteiraSel = new Set();

function _opNorm(op) {
  const u = (op || '').toString().trim().toUpperCase();
  if (u === 'C' || u === 'COMPRA' || u.startsWith('COMPR')) return 'C';
  if (u === 'V' || u === 'VENDA'  || u.startsWith('VEND'))  return 'V';
  return u || null;
}

function _parseCvDate(v) {
  if (!v || v === 'None' || v === '—') return -Infinity;
  const s = String(v).trim();
  const p = s.split('/');
  if (p.length === 3) return new Date(+p[2], +p[1]-1, +p[0]).getTime();
  const d = new Date(s);
  return isNaN(d) ? -Infinity : d.getTime();
}

function _cvFmt(v) {
  if (v == null || v === '' || v === 'None') return '—';
  const n = parseFloat(v);
  if (isNaN(n)) return v;
  return n.toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});
}
function _cvFmtQtd(v) {
  if (v == null || v === '' || v === 'None') return '—';
  const n = parseFloat(v);
  if (isNaN(n)) return v;
  return n.toLocaleString('pt-BR', {minimumFractionDigits:0, maximumFractionDigits:4});
}

function _cvFiltered() {
  const search   = (document.getElementById('cvSearch')      || {}).value || '';
  const tipo     = (document.getElementById('cvTipoAtivoSel')|| {}).value || '';
  const dtIni    = (document.getElementById('cvDtIni')       || {}).value || '';
  const dtFim    = (document.getElementById('cvDtFim')       || {}).value || '';
  return (COMPRAS_VENDAS || []).filter(r => {
    if (_cvFilOp !== 'todos' && _opNorm(r.operacao) !== _cvFilOp.toUpperCase()) return false;
    if (tipo && !(r.tipo_ativo || '').toLowerCase().includes(tipo.toLowerCase())) return false;
    if (search) {
      const q = search.toLowerCase();
      if (!(r.ativo || '').toLowerCase().includes(q) &&
          !(r.nome_portfolio || '').toLowerCase().includes(q)) return false;
    }
    if (dtIni || dtFim) {
      const raw = r.data_operacao || '';
      let dt = null;
      if (raw.includes('/')) {
        const p = raw.split('/');
        dt = new Date(+p[2], +p[1]-1, +p[0]);
      } else {
        dt = new Date(raw);
      }
      if (!isNaN(dt)) {
        if (dtIni && dt < new Date(dtIni)) return false;
        if (dtFim && dt > new Date(dtFim)) return false;
      }
    }
    return true;
  });
}

function _cvRender() {
  const rows   = _cvFiltered();
  const _DATE_COLS = ['data_operacao','data_liquidacao','data_cadastro'];
  const sorted = [...rows].sort((a, b) => {
    const va = a[_cvSortKey], vb = b[_cvSortKey];
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    let cmp;
    if (_DATE_COLS.includes(_cvSortKey)) {
      cmp = _parseCvDate(va) - _parseCvDate(vb);
    } else {
      const na = parseFloat(va), nb = parseFloat(vb);
      cmp = (!isNaN(na) && !isNaN(nb)) ? na - nb : String(va).localeCompare(String(vb), 'pt-BR');
    }
    return _cvSortAsc ? cmp : -cmp;
  });

  // KPI
  let totC = 0, totV = 0, nOp = rows.length;
  rows.forEach(r => {
    const v = parseFloat(r.total_bruto) || 0;
    if (_opNorm(r.operacao) === 'C') totC += v;
    else if (_opNorm(r.operacao) === 'V') totV += v;
  });
  const saldo = totC - totV;
  const kpiEl = document.getElementById('cvKpiStrip');
  if (kpiEl) {
    const fmt = v => 'R$ ' + Math.abs(v).toLocaleString('pt-BR', {minimumFractionDigits:0, maximumFractionDigits:0});
    kpiEl.innerHTML = [
      ['Total Comprado', fmt(totC), '#2fa874'],
      ['Total Vendido',  fmt(totV), '#d94141'],
      ['Saldo Líquido',  (saldo >= 0 ? '' : '–') + fmt(saldo), saldo >= 0 ? '#2fa874' : '#d94141'],
      ['Nº Operações',   nOp, 'var(--teal)'],
    ].map(([l,v,c]) => `<div class="card" style="padding:14px 18px;">
      <div style="font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px">${l}</div>
      <div style="font-size:20px;font-weight:700;color:${c}">${v}</div>
    </div>`).join('');
  }

  const cnt = document.getElementById('cvCount');
  if (cnt) cnt.textContent = nOp + ' operaç' + (nOp === 1 ? 'ão' : 'ões');

  const tbody = document.getElementById('tbodyCv');
  if (!tbody) { _cvUpdateChart(); return; }
  if (!sorted.length) {
    tbody.innerHTML = '<tr><td colspan="13" style="text-align:center;color:var(--text3);padding:24px">Nenhuma operação encontrada.</td></tr>';
    _cvUpdateChart();
    return;
  }

  const opColor = op => _opNorm(op) === 'C' ? '#2fa874' : _opNorm(op) === 'V' ? '#d94141' : '#718096';
  const opLabel = op => _opNorm(op) === 'C' ? 'Compra' : _opNorm(op) === 'V' ? 'Venda' : (op || '—');

  // Render helper: converte uma linha em HTML
  function _cvRowHtml(r) {
    const isSelected = _cvSelAtivos.has(r.ativo);
    const pctEm   = r.pct_emissor_carteira  != null ? parseFloat(r.pct_emissor_carteira)  : null;
    const excesso = r.excesso_limite_pct    != null ? parseFloat(r.excesso_limite_pct)    : null;
    const expMax  = r.exposicao_maxima_rating != null ? parseFloat(r.exposicao_maxima_rating) : null;
    const pctStr  = pctEm != null ? pctEm.toFixed(2) + '%' : '—';
    const pctColor = (pctEm != null && expMax != null) ? (pctEm > expMax ? '#d94141' : '#2fa874') : 'var(--text3)';
    let excStr = '—', excColor = 'var(--text3)', excBg = 'transparent';
    if (excesso != null) {
      excStr   = (excesso >= 0 ? '+' : '') + excesso.toFixed(2) + '%';
      excColor = excesso > 0 ? '#d94141' : '#2fa874';
      excBg    = excesso > 0 ? 'rgba(217,65,65,.08)' : 'rgba(47,168,116,.08)';
    }
    return `<tr style="cursor:pointer;${isSelected ? 'background:rgba(0,103,123,.08);' : ''}" onclick="_cvToggleAtivo('${(r.ativo||'').replace(/'/g,"\\'")}','${(r.data_operacao||'').replace(/'/g,"\\'")}')" title="Clique para ver evolução de PU">
      <td style="white-space:nowrap">${r.data_operacao||'—'}</td>
      <td style="font-weight:600;color:var(--teal)">${r.ativo||'—'}</td>
      <td style="font-size:10px;background:var(--surface2);border-radius:4px;padding:2px 6px;white-space:nowrap">${(r.tipo_ativo||'—').toUpperCase()}</td>
      <td><span style="background:${opColor(r.operacao)}22;color:${opColor(r.operacao)};border:1px solid ${opColor(r.operacao)}44;border-radius:4px;padding:2px 8px;font-size:10px;font-weight:700">${opLabel(r.operacao)}</span></td>
      <td style="text-align:right">${_cvFmtQtd(r.quantidade)}</td>
      <td style="text-align:right">${_cvFmt(r.preco_unitario)}</td>
      <td style="text-align:right;font-weight:600">${_cvFmt(r.total_bruto)}</td>
      <td style="white-space:nowrap;color:var(--text3)">${r.data_liquidacao||'—'}</td>
      <td style="font-size:10px;color:var(--text3)">${r.nome_portfolio||'—'}</td>
      <td style="font-size:10px;font-weight:700;color:var(--teal)">${r['Rating Douro']||'—'}</td>
      <td style="text-align:right;font-size:11px;color:var(--text3)">${expMax != null ? expMax.toFixed(2)+'%' : '—'}</td>
      <td style="text-align:right;font-size:11px;font-weight:600;color:${pctColor}">${pctStr}</td>
      <td style="text-align:right;font-size:11px;font-weight:700;color:${excColor};background:${excBg};border-radius:4px;padding:2px 6px;">${excStr}</td>
    </tr>`;
  }

  // Paginação: renderiza as primeiras _CV_PAGE_SIZE linhas imediatamente,
  // as restantes são injetadas logo após via rAF para não bloquear o UI.
  const _CV_PAGE_SIZE = 60;
  const firstBatch  = sorted.slice(0, _CV_PAGE_SIZE);
  const restBatch   = sorted.slice(_CV_PAGE_SIZE);

  tbody.innerHTML = firstBatch.map(_cvRowHtml).join('');

  if (restBatch.length) {
    // Injeta o resto em dois micro-tasks para liberar o thread principal
    requestAnimationFrame(() => {
      const frag = document.createDocumentFragment();
      restBatch.forEach(r => {
        const tmp = document.createElement('template');
        tmp.innerHTML = _cvRowHtml(r);
        frag.appendChild(tmp.content);
      });
      tbody.appendChild(frag);
      _cvUpdateChart();
    });
  } else {
    _cvUpdateChart();
  }
}

function _cvSort(key) {
  if (_cvSortKey === key) {
    _cvSortAsc = !_cvSortAsc;
  } else {
    _cvSortKey = key;
    _cvSortAsc = false;
  }
  document.querySelectorAll('[id^="_cvsh_"]').forEach(el => {
    el.style.opacity = '.4'; el.innerHTML = '&#8597;';
  });
  const hdr = document.getElementById('_cvsh_' + key);
  if (hdr) { hdr.style.opacity = '1'; hdr.innerHTML = _cvSortAsc ? '&#8593;' : '&#8595;'; }
  _cvRender();
}

function _cvSetFil(val, el) {
  _cvFilOp = val;
  document.querySelectorAll('.cv-fil-btn').forEach(b => b.classList.remove('active'));
  if (el) el.classList.add('active');
  _cvRender();
}

function _cvResetFil() {
  _cvFilOp = 'todos';
  document.querySelectorAll('.cv-fil-btn').forEach(b => b.classList.remove('active'));
  const allBtn = document.querySelector('.cv-fil-btn[data-cv-fil="todos"]');
  if (allBtn) allBtn.classList.add('active');
  const sel = document.getElementById('cvTipoAtivoSel');
  if (sel) sel.value = '';
  const srch = document.getElementById('cvSearch');
  if (srch) srch.value = '';
  const dtIni = document.getElementById('cvDtIni');
  if (dtIni) dtIni.value = '';
  const dtFim = document.getElementById('cvDtFim');
  if (dtFim) dtFim.value = '';
  _cvSelAtivos.clear();
  _cvSelAtivoDates.clear();
  _cvRender();
}

function _cvToggleAtivo(ativo, dateStr) {
  if (!ativo || ativo === 'None') return;
  if (_cvSelAtivos.has(ativo)) {
    _cvSelAtivos.delete(ativo);
    _cvSelAtivoDates.delete(ativo);
  } else {
    _cvSelAtivos.add(ativo);
    if (dateStr) _cvSelAtivoDates.set(ativo, _parseCvDate(dateStr));
  }
  // Re-render table highlighting, then update chart
  _cvRender();
  // Scroll to chart so user sees it
  requestAnimationFrame(() => {
    const chartCard = document.getElementById('chartCvPU');
    if (chartCard) chartCard.closest('.card')?.scrollIntoView({behavior:'smooth', block:'nearest'});
  });
}

// Resolve ativo key against RETORNO_DIARIO_TS, tolerating CETIP_ prefix differences
function _cvFindTs(ativo) {
  const map = RETORNO_DIARIO_TS || {};
  if (map[ativo]) return map[ativo];
  // try with CETIP_ prefix
  const withPrefix = 'CETIP_' + ativo;
  if (map[withPrefix]) return map[withPrefix];
  // try stripping CETIP_ prefix from ativo
  const stripped = ativo.replace(/^CETIP_/i, '');
  if (map[stripped]) return map[stripped];
  // fuzzy: find first key that contains the ativo string or vice-versa
  const lc = ativo.toLowerCase();
  const match = Object.keys(map).find(k => k.toLowerCase().includes(lc) || lc.includes(k.toLowerCase().replace(/^cetip_/,'').replace(/\.pu_.+$/,'')));
  return match ? map[match] : null;
}

function _cvUpdateChart() {
  const chips = document.getElementById('cvChartChips');
  if (chips) {
    chips.innerHTML = [..._cvSelAtivos].map(p =>
      `<span onclick="_cvToggleAtivo('${p.replace(/'/g,"\\'")}');event.stopPropagation()"
        style="background:rgba(0,103,123,.15);border:1px solid rgba(0,103,123,.35);color:var(--teal);
               border-radius:20px;padding:3px 10px;font-size:10px;font-weight:600;cursor:pointer;
               display:inline-flex;align-items:center;gap:5px;">
        ${p} <span style="opacity:.6;font-size:11px">×</span>
      </span>`
    ).join('');
  }

  const canvas = document.getElementById('chartCvPU');
  if (!canvas) return;

  const datasets = [];
  let colorIdx = 0;

  // ── Ativos selecionados na tabela ──────────────────────────────────────
  [..._cvSelAtivos].forEach((ativo) => {
    const ts = _cvFindTs(ativo);
    if (!ts || !ts.datas || ts.datas.length < 2) return;

    const startTs = _cvSelAtivoDates.has(ativo) ? _cvSelAtivoDates.get(ativo) : -Infinity;

    // Primeiro índice cujo dia >= data da operação
    let startIdx = 0;
    if (startTs > -Infinity) {
      for (let i = 0; i < ts.datas.length; i++) {
        if (new Date(ts.datas[i]).getTime() >= startTs) { startIdx = i; break; }
      }
    }

    // Retorno acumulado a partir de startIdx (retornos diários discretos)
    let cumprod = 1.0;
    const data = ts.datas.slice(startIdx).map((d, i) => {
      const r = ts.valor[startIdx + i];
      if (r != null && !isNaN(r)) cumprod *= (1 + r);
      return { x: d, y: +((cumprod - 1) * 100).toFixed(4) };
    });

    datasets.push({
      label: ativo,
      data,
      borderColor: COLORS[colorIdx % COLORS.length],
      backgroundColor: 'transparent',
      borderWidth: 1.5,
      pointRadius: 0,
      tension: 0.2,
    });
    colorIdx++;
  });

  // ── Data de início = mínimo entre os ativos selecionados ───────────────
  const _chartStartTs = _cvSelAtivoDates.size
    ? Math.min(..._cvSelAtivoDates.values())
    : -Infinity;

  // ── Séries comparadoras (PERF_DATA) ────────────────────────────────────
  [..._cvCarteiraSel].forEach((serie) => {
    const pd = (PERF_DATA?.ativos || {})[serie];
    if (!pd || !pd.datas || !pd.retorno_acum) return;

    // Primeiro índice >= _chartStartTs (busca o próximo dia disponível)
    let startIdx = 0;
    if (_chartStartTs > -Infinity) {
      startIdx = pd.datas.length - 1;           // fallback: último ponto
      for (let i = 0; i < pd.datas.length; i++) {
        if (new Date(pd.datas[i]).getTime() >= _chartStartTs) {
          startIdx = i;
          break;
        }
      }
    }

    // Rebasa o retorno acumulado: (1 + rv) / (1 + base) - 1
    const baseRetVal = pd.retorno_acum[startIdx] ?? 0;
    const data = pd.datas.slice(startIdx).map((d, i) => {
      const rv = pd.retorno_acum[startIdx + i];
      return { x: d, y: +(((1 + rv) / (1 + baseRetVal) - 1) * 100).toFixed(4) };
    });

    datasets.push({
      label: serie + ' (carteira)',
      data,
      borderColor: COLORS[colorIdx % COLORS.length],
      backgroundColor: 'transparent',
      borderWidth: 1.5,
      borderDash: [4, 3],
      pointRadius: 0,
      tension: 0.2,
    });
    colorIdx++;
  });

  // ── Renderiza ──────────────────────────────────────────────────────────
  if (_cvChart) { try { _cvChart.destroy(); } catch(e){} _cvChart = null; }

  if (!datasets.length) {
    canvas.parentElement.style.display = 'none';
    return;
  }
  canvas.parentElement.style.display = '';

  _cvChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: { datasets },
    options: {
      ...(_CROSSHAIR_OPTS || {}),
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'time',
          time: { unit: 'month', tooltipFormat: 'dd/MM/yyyy', displayFormats: { month: 'MMM yy' } },
          grid: { color: 'rgba(255,255,255,.04)' },
          ticks: { color: 'var(--text3)', maxTicksLimit: 14, font: { size: 10 } },
        },
        y: {
          grid: { color: 'rgba(255,255,255,.04)' },
          ticks: { color: 'var(--text3)', font: { size: 10 },
            callback: v => (v >= 0 ? '+' : '') + v.toFixed(2) + '%' },
        },
      },
      plugins: {
        annotation: {
          annotations: {
            zeroLine: { type: 'line', yMin: 0, yMax: 0, borderColor: 'rgba(255,255,255,.18)', borderWidth: 1, borderDash: [4,4] }
          }
        },
        legend: { position: 'top', labels: { color: 'var(--text)', font: { size: 10 }, boxWidth: 10 } },
        tooltip: {
          callbacks: {
            label: ctx => ' ' + ctx.dataset.label + ': ' + (ctx.parsed.y >= 0 ? '+' : '') + (ctx.parsed.y || 0).toFixed(2) + '%',
          },
        },
      },
    },
  });
}

function _cvAddCarteira() {
  const sel = document.getElementById('cvCarteiraComparSel');
  if (!sel || !sel.value) return;
  _cvCarteiraSel.add(sel.value);
  sel.value = '';
  _cvRenderCarteiraChips();
  _cvUpdateChart();
}

function _cvRemoveCarteira(serie) {
  _cvCarteiraSel.delete(serie);
  _cvRenderCarteiraChips();
  _cvUpdateChart();
}

function _cvRenderCarteiraChips() {
  const wrap = document.getElementById('cvCarteiraChips');
  if (!wrap) return;
  wrap.innerHTML = [..._cvCarteiraSel].map(s =>
    `<span onclick="_cvRemoveCarteira('${s.replace(/'/g,"\\'")}');event.stopPropagation()"
      style="background:rgba(182,157,116,.15);border:1px solid rgba(182,157,116,.4);color:#b69d74;
             border-radius:20px;padding:3px 10px;font-size:10px;font-weight:600;cursor:pointer;
             display:inline-flex;align-items:center;gap:5px;">
      ${s} <span style="opacity:.6;font-size:11px">×</span>
    </span>`
  ).join('');
}

let _cvDebounceTimer = null;
function _cvDebounceRender() {
  clearTimeout(_cvDebounceTimer);
  _cvDebounceTimer = setTimeout(_cvRender, 220);
}

function _cvPopulateCarteiraCompar() {
  const sel = document.getElementById('cvCarteiraComparSel');
  if (!sel || sel.children.length > 1) return;
  const ativos = Object.keys(PERF_DATA?.ativos || {});
  ativos.forEach(a => {
    const opt = document.createElement('option');
    opt.value = a; opt.textContent = a;
    sel.appendChild(opt);
  });
}

let _cvBuilt = false;
function buildComprasVendas() {
  _cvPopulateCarteiraCompar();
  if (!_cvBuilt) {
    _cvBuilt = true;
    const dtIni = document.getElementById('cvDtIni');
    if (dtIni && !dtIni.value) {
      const d = new Date();
      d.setDate(d.getDate() - 90);
      dtIni.value = d.toISOString().slice(0, 10);
    }
  }
  _cvRender();
}

// ── DOURADO CHATBOT ───────────────────────────────────────────────────────
let douradoOpen = false;
function douradoToggle() {
  douradoOpen = !douradoOpen;
  document.getElementById('douradoPanel').classList.toggle('open', douradoOpen);
  if (douradoOpen && document.querySelectorAll('.dourado-msg').length === 0) douradoWelcome();
  const dBtn = document.getElementById('douradoBtn');
  if (dBtn) dBtn.classList.toggle('pulsing', !douradoOpen);
}
function douradoWelcome() {
  douradoAddMsg('bot', 'Dourado aqui. Tenho acesso à carteira completa — posso comparar emissores, checar concentrações, revisar status de cobertura ou discutir qualquer posição. O que você quer analisar?');
}
function _renderMd(raw) {
  let t = raw
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/^### (.+)$/gm,'<div style="margin:10px 0 3px;color:#b69d74;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px">$1</div>')
    .replace(/^## (.+)$/gm,'<div style="margin:12px 0 4px;color:#d4b47a;font-size:13px;font-weight:700">$1</div>')
    .replace(/\*\*(.+?)\*\*/g,'<strong style="color:#e8d5b0">$1</strong>')
    .replace(/\*(.+?)\*/g,'<em style="color:#a0b4c8">$1</em>')
    .replace(/\x60([^\x60]+)\x60/g,'<code style="background:#0d1117;padding:1px 5px;border-radius:3px;font-family:monospace;font-size:11px;color:#7dd3fc">$1</code>');
  const lines = t.split(/\\n/);
  const out = [];
  let inList = false;
  for (const line of lines) {
    const bullet = line.match(/^[-•]\s(.+)/);
    const num    = line.match(/^(\d+)\.\s(.+)/);
    if (bullet) {
      if (!inList) { out.push('<ul style="margin:4px 0;padding:0;list-style:none">'); inList=true; }
      out.push(`<li style="margin:2px 0;padding-left:12px;position:relative"><span style="position:absolute;left:0;color:#b69d74">▸</span>${bullet[1]}</li>`);
    } else if (num) {
      if (!inList) { out.push('<ul style="margin:4px 0;padding:0;list-style:none">'); inList=true; }
      out.push(`<li style="margin:2px 0;padding-left:16px;position:relative"><span style="position:absolute;left:0;color:#b69d74">${num[1]}.</span>${num[2]}</li>`);
    } else {
      if (inList) { out.push('</ul>'); inList=false; }
      out.push(line === '' ? '<br>' : `<span>${line}</span><br>`);
    }
  }
  if (inList) out.push('</ul>');
  return out.join('');
}
function douradoAddMsg(role, text, thinking=false) {
  const msgs = document.getElementById('douradoMsgs');
  const div = document.createElement('div');
  div.className = `dourado-msg ${role==='user'?'user':''}`;
  if (role === 'bot') {
    div.innerHTML = `<div class="dourado-avatar" style="width:28px;height:28px;font-size:12px;flex-shrink:0;">D</div>
      <div class="dourado-bubble" id="${thinking?'douradoThinking':''}">
        ${thinking
          ? '<div class="dourado-thinking"><div class="dourado-dot"></div><div class="dourado-dot"></div><div class="dourado-dot"></div></div>'
          : _renderMd(text)
        }</div>`;
  } else {
    div.innerHTML = `<div class="dourado-bubble">${text.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>`;
  }
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}
function douradoChip(txt) {
  const inp = document.getElementById('douradoInput');
  inp.value = txt;
  inp.focus();
  inp.setSelectionRange(txt.length, txt.length);
}
// ── SLASH COMMAND PALETTE ─────────────────────────────────────────────────
const _SLASH_CMDS = [
  {cmd:'/resumo',         desc:'Resumo geral da carteira'},
  {cmd:'/spread',         desc:'Spreads e alertas MAD'},
  {cmd:'/rating',         desc:'Distribuição de rating da carteira'},
  {cmd:'/setor',          desc:'Concentração por setor'},
  {cmd:'/duration',       desc:'Duration média ponderada'},
  {cmd:'/watch',          desc:'Emissores em watch / análise'},
  {cmd:'/stress',         desc:'Cenário de estresse: refinanciamento'},
  {cmd:'/vencimentos',    desc:'Perfil de vencimentos da carteira'},
  {cmd:'/alavancagem',    desc:'Ranking Dív.Liq/EBITDA (maior → menor)'},
  {cmd:'/cobertura',      desc:'Status de cobertura dos emissores'},
  {cmd:'/top',            desc:'Top N posições — ex: /top 5'},
  {cmd:'/carteira',       desc:'Filtra por carteira — ex: /carteira FI'},
  {cmd:'/emissor',        desc:'Síntese completa — ex: /emissor Klabin'},
  {cmd:'/comparar',       desc:'Compara emissores — ex: /comparar Klabin vs Suzano'},
  {cmd:'/grafico setor',  desc:'Gráfico de exposição por setor'},
  {cmd:'/clear',          desc:'Limpa o histórico do chat'},
  {cmd:'/help',           desc:'Lista todos os comandos disponíveis'},
];
let _dspIdx=-1, _dspInp=null;
function _dspShow(inp){
  const val=inp.value;
  if(!val.startsWith('/')){_dspHide();return;}
  const q=val.toLowerCase().trim();
  const list=q==='/'?_SLASH_CMDS:_SLASH_CMDS.filter(c=>c.cmd.startsWith(q));
  const pal=document.getElementById('dSlashPal');
  if(!pal||!list.length){_dspHide();return;}
  _dspInp=inp; _dspIdx=-1;
  const r=inp.getBoundingClientRect();
  pal.style.left=r.left+'px';
  pal.style.width=Math.max(r.width,320)+'px';
  pal.style.top=r.top+'px';
  pal.style.transform='translateY(-100%) translateY(-6px)';
  pal.innerHTML=list.map((c,i)=>
    `<div class="dsp-item" data-cmd="${c.cmd}" onmousedown="event.preventDefault();_dspPick('${c.cmd}')">
      <span class="dsp-cmd">${c.cmd}</span><span class="dsp-desc">${c.desc}</span>
    </div>`).join('');
  pal.style.display='block';
}
function _dspHide(){
  const pal=document.getElementById('dSlashPal');
  if(pal)pal.style.display='none';
  _dspIdx=-1; _dspInp=null;
}
function _dspPick(cmd){
  if(_dspInp){_dspInp.value=cmd+' ';_dspInp.focus();_dspShow(_dspInp);}
  else{const i=document.getElementById('douradoInput');if(i){i.value=cmd+' ';i.focus();}}
  _dspHide();
}
function _dspKeyNav(e,inp){
  const pal=document.getElementById('dSlashPal');
  if(!pal||pal.style.display==='none')return false;
  const items=pal.querySelectorAll('.dsp-item');
  if(!items.length)return false;
  if(e.key==='ArrowDown'){e.preventDefault();_dspIdx=Math.min(_dspIdx+1,items.length-1);items.forEach((el,i)=>el.classList.toggle('dsp-active',i===_dspIdx));return true;}
  if(e.key==='ArrowUp'){e.preventDefault();_dspIdx=Math.max(_dspIdx-1,0);items.forEach((el,i)=>el.classList.toggle('dsp-active',i===_dspIdx));return true;}
  if(e.key==='Enter'&&_dspIdx>=0){const item=items[_dspIdx];if(item){_dspPick(item.dataset.cmd);e.preventDefault();return true;}}
  if(e.key==='Escape'){_dspHide();return true;}
  return false;
}
document.addEventListener('click',e=>{
  if(!e.target.closest('#dSlashPal')&&!e.target.closest('.dourado-input'))_dspHide();
});
// ── NLQ FRONTEND ENGINE v2 ───────────────────────────────────────────────
function _norm(s) { return (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^a-z0-9 ]/g,' '); }

function _simRatio(a, b) {
  if (!a||!b) return 0;
  const la=a.split(' ').filter(w=>w.length>1), lb=b.split(' ').filter(w=>w.length>1);
  if (!la.length||!lb.length) return 0;
  let hits=0;
  for (const wa of la) for (const wb of lb) {
    if (wa===wb) hits+=1;
    else if (wa.length>3&&wb.length>3&&(wa.includes(wb)||wb.includes(wa))) hits+=0.7;
  }
  return hits/Math.max(la.length,lb.length);
}

function _ww(tok, norm) {
  // whole-word check: tok must appear as a standalone word in norm (not as a substring)
  return new RegExp('(?:^|[\\\\s\\\\-\\\\/,])' + tok.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&') + '(?=[\\\\s\\\\-\\\\/,]|$)').test(norm);
}

function _extractEmissorMulti(norm) {
  // Returns all emissores mentioned in the input (for comparison queries)
  const emissores=[...new Set(ATIVOS.map(a=>a.emissor).filter(Boolean))];
  const found=[];
  // Pass 1: exact normalized full name as whole-word sequence
  for (const em of emissores) {
    const emN=_norm(em);
    if(emN.length<3) continue;
    // require the full normalized name to appear as a whole-word phrase
    if(_ww(emN, norm)) { found.push(em); continue; }
    // also check each word of the name independently as whole-word (all must match)
    const words=emN.split(' ').filter(w=>w.length>=4);
    if(words.length>0 && words.every(w=>_ww(w,norm))) found.push(em);
  }
  if(found.length>=2) return found;
  // Pass 2: single dominant token (≥5 chars) as whole word — only if no ambiguity
  const candidates=[];
  for (const em of emissores) {
    if(found.includes(em)) continue;
    const toks=_norm(em).split(' ').filter(w=>w.length>=5);
    if(toks.length>0 && toks.some(tok=>_ww(tok,norm))) candidates.push(em);
  }
  // Filter out candidates whose token is a substring of another candidate's token
  const safe=candidates.filter(em=>{
    const toks=_norm(em).split(' ').filter(w=>w.length>=5);
    return !candidates.some(other=>{
      if(other===em) return false;
      const oN=_norm(other);
      return toks.some(tok=>oN.includes(tok)&&oN!==tok);
    });
  });
  safe.forEach(em=>{ if(!found.includes(em)) found.push(em); });
  return found;
}

function _extractEmissor(norm) {
  const emissores=[...new Set(ATIVOS.map(a=>a.emissor).filter(Boolean))];
  // Pass 1: exact normalized full name as whole-word sequence
  for (const em of emissores) {
    const emN=_norm(em);
    if(emN.length<3) continue;
    if(_ww(emN,norm)) return em;
    const words=emN.split(' ').filter(w=>w.length>=4);
    if(words.length>0 && words.every(w=>_ww(w,norm))) return em;
  }
  // Pass 2: all significant tokens (≥5 chars) match as whole words
  for (const em of emissores) {
    const toks=_norm(em).split(' ').filter(w=>w.length>=5);
    if(!toks.length) continue;
    if(toks.every(tok=>_ww(tok,norm))) return em;
  }
  // Pass 3: fuzzy — only exact whole-word token equality, threshold 0.65
  let best=null,bestScore=0;
  for (const em of emissores) {
    const emToks=_norm(em).split(' ').filter(w=>w.length>=4);
    if(!emToks.length) continue;
    let hits=0;
    for(const et of emToks){ if(_ww(et,norm)) hits+=1; }
    const score=hits/emToks.length;
    if(score>bestScore&&score>=0.65){bestScore=score;best=em;}
  }
  return best;
}

// ── Geração dinâmica de frases por emissor ────────────────────────────────
// Para cada emissor da carteira, gera automaticamente frases para cada intent.
// Isso garante cobertura total sem precisar hardcodar cada nome.
function _buildEmissorPhrases() {
  const _ativos = typeof ATIVOS !== 'undefined' ? ATIVOS : [];
  const emissores = [...new Set(_ativos.map(a=>a.emissor).filter(Boolean))];
  const n = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').trim();

  const sintese_kw   = [], sintese_ex   = [];
  const detalhe_kw   = [], detalhe_ex   = [];
  const grafico_kw   = [], grafico_ex   = [];
  const exposicao_kw = [], exposicao_ex = [];
  const evolucao_kw  = [], evolucao_ex  = [];
  const comparar_kw  = [];

  for (const em of emissores) {
    const e = n(em);
    if (!e || e.length < 3) continue;

    // sintese_emissor: frases de análise completa/perfil
    sintese_kw.push(
      `analise completa de ${e}`, `analise completa da ${e}`, `analise completa do ${e}`,
      `perfil completo de ${e}`, `me conta tudo sobre ${e}`, `tudo sobre ${e}`,
      `como anda ${e}`, `como esta ${e}`, `o que ta acontecendo com ${e}`,
      `o que acontece com ${e}`, `me fala tudo sobre ${e}`, `due diligence de ${e}`,
      `deep dive em ${e}`, `quero tudo sobre ${e}`, `resume tudo de ${e}`,
      `briefing de ${e}`, `panorama de ${e}`, `situacao de ${e}`, `o que sei sobre ${e}`
    );
    sintese_ex.push(
      `analise completa de ${e}`, `me conta tudo sobre ${e}`, `como anda ${e}`,
      `o que ta acontecendo com ${e}`, `briefing de ${e}`
    );

    // detalhe_ativo: spread, yield, ntnb, caro/barato
    detalhe_kw.push(
      `spread de ${e}`, `spread da ${e}`, `spread do ${e}`,
      `yield de ${e}`, `yield da ${e}`, `quanto rende ${e}`,
      `ntnb de ${e}`, `ntnb da ${e}`, `ntnb ref de ${e}`,
      `${e} ta caro`, `${e} ta barato`, `${e} esta caro`, `${e} esta barato`,
      `${e} esta esticado`, `${e} esta comprimido`, `${e} esta atrativo`,
      `spread de ${e} esta caro`, `o papel de ${e} esta caro`
    );
    detalhe_ex.push(`spread de ${e}`, `ntnb de ${e}`, `${e} ta caro`);

    // grafico_spread: "plota spread de X", "grafico de spread de X"
    grafico_kw.push(
      `grafico de spread de ${e}`, `grafico do spread de ${e}`,
      `historico de spread de ${e}`, `historico spread de ${e}`,
      `plota spread de ${e}`, `plote spread de ${e}`, `mostra spread de ${e}`,
      `ver spread de ${e}`, `quero ver spread de ${e}`,
      `evolucao do spread de ${e}`, `serie de spread de ${e}`,
      `curva de spread de ${e}`, `timeline de spread de ${e}`
    );
    grafico_ex.push(
      `grafico de spread de ${e}`, `historico de spread de ${e}`
    );

    // exposicao_emissor: "quanto em X", "posicao em X"
    exposicao_kw.push(
      `posicao em ${e}`, `exposicao a ${e}`, `exposicao em ${e}`,
      `quanto em ${e}`, `quanto temos de ${e}`, `quanto tenho em ${e}`,
      `peso de ${e}`, `alocacao em ${e}`, `nossa posicao em ${e}`,
      `minha posicao em ${e}`, `saldo de ${e}`, `saldo em ${e}`
    );
    exposicao_ex.push(`posicao em ${e}`, `quanto em ${e}`);

    // evolucao_fundamento: "como evoluiu o ebitda de X"
    evolucao_kw.push(
      `evolucao do ebitda de ${e}`, `evolucao da margem de ${e}`,
      `evolucao do dl ebitda de ${e}`, `evolucao da alavancagem de ${e}`,
      `historico de ebitda de ${e}`, `tendencia de alavancagem de ${e}`,
      `como evoluiu o ebitda de ${e}`, `como foi a alavancagem de ${e}`,
      `vem caindo a margem de ${e}`, `vem subindo o ebitda de ${e}`,
      `foi melhorando o roe de ${e}`, `foi piorando o dl ebitda de ${e}`,
      `trajetoria financeira de ${e}`, `dl ebitda de ${e} historico`
    );
    evolucao_ex.push(
      `evolucao do ebitda de ${e}`, `tendencia de alavancagem de ${e}`
    );

    // comparar_emissores: "X vs", "X ou Y"
    comparar_kw.push(`${e} vs`, `${e} ou `);
  }

  return {
    sintese_kw, sintese_ex, detalhe_kw, detalhe_ex,
    grafico_kw, grafico_ex, exposicao_kw, exposicao_ex,
    evolucao_kw, evolucao_ex, comparar_kw
  };
}
let _EP = _buildEmissorPhrases();

let _INTENT_KW = {
  exposicao_setor:    [
    // setores nomeados
    'utilities','infraestrutura','energia eletrica','setor eletrico','papel e celulose','celulose','papel','saneamento basico','saneamento','logistica','transporte','telecomunicacoes','telecom','construcao civil','incorporacao','educacao','mineracao','quimica','petroquimica','farma','farmaceutico','bancario','banco','seguros','credito privado','consumo','luxo','tecnologia','agronegocio','agro','petroleo','gas','oleo e gas','saude','varejo','imobiliario','financeiro',
    // setores específicos do book
    'transmissao','distribuicao de energia','geracao de energia','rodovias','concessoes','portos','ferrovias','frigorifico','aco','siderurgia','varejo alimentar','varejo de moda','shopping','shopping center','incorporadora','real estate','locacao de veiculos','locacao pesada','aluguel de veiculos','healthcare','hospitalar','laboratorio','diagnostico','meios de pagamento','fintech','seguradora','atacarejo','bebidas','alimentos','proteina','quimicos','plasticos','autopecas','combustivel','etanol','acucar','energia renovavel','energia eolica','energia solar','telecom e midia','midia','tech',
    // formas de perguntar
    'exposicao em','exposicao ao setor','exposicao no setor','quanto tenho no setor','posicao no setor','percentual no setor','peso do setor','alocacao no setor','quanto esta no setor','qual e o peso do setor','quanta exposicao ao setor','o que tenho em','o que temos em','quanto em renda fixa','renda fixa','quanto em ipca','quanto em cdi','quanto em prefixado','quanto em debenture incentivada','quanto em cri','quanto em cra','quanto em letra financeira','quanto em pre','indexador','indexadores','breakdown setorial','quebra setorial','distribuicao setorial','composicao setorial','peso por setor','distribuicao por setor','breakdown por setor','alocacao por setor','exposicao por setor','exposicao setorial'
  ],
  exposicao_rating:   [
    'rating aaa','rating aa+','rating aa','rating aa-','rating a+','rating a','rating a-','rating bbb+','rating bbb','rating bbb-','rating bb+','rating bb','rating bb-','rating b+','rating b','rating ccc','aaa br','aa br','a br','bbb br','bb br','braaa','braa','bra','brbbb','brbb','investment grade','high grade','high yield','grau de investimento','grau especulativo','subinvestimento','junk','lixo','nota de credito','classificacao de credito',
    'exposicao em aaa','posicao em aa','quanto em investment grade','quanto em high yield','emissores com rating','posicao rating','peso por rating','alocacao por rating','distribuicao por rating','breakdown por rating','quebra por rating','rating medio','rating medio ponderado','rating average','peso de high yield','peso de investment grade','exposicao a credito ig','exposicao a credito hy','quanto em rating aa','quanto em rating a','quanto em rating bbb','quanto em rating bb','rating mais comum','rating mais frequente','rating predominante','nota mais comum','distribuicao de notas','distribuicao das notas'
  ],
  exposicao_emissor:  [
    'posicao em','exposicao a','exposicao em','quanto em','peso de','alocacao em','temos de','tenho em','temos em','quanto tenho de','quanto temos de','como esta a posicao de','qual a exposicao a','qual o tamanho de','qual o peso de','qual o saldo de','temos posicao em','tenho posicao em','posicao total em','posicao consolidada em',
    'quanto vale a posicao','qual o valor da posicao','saldo do emissor','qual o montante em','quanto investido em','quanto investido no emissor','quanto temos investido em','quanto temos alocado em','nossa posicao em','minha posicao em','nossa exposicao a','minha exposicao a','o que temos em','quanto temos do emissor','saldo bruto em','saldo bruto de','peso do emissor','posicao no nome','exposicao ao nome','exposicao ao emissor','exposicao a empresa','posicao na empresa','quanto na empresa',
    ..._EP.exposicao_kw
  ],
  overview_carteira:  [
    'resumo da carteira','resumo geral','overview da carteira','composicao da carteira','visao geral da carteira','como esta a carteira','estado da carteira','situacao da carteira','carteira toda','panorama geral','panorama da carteira','consolidado da carteira','fotografia da carteira','snapshot da carteira','sumario da carteira','retrato da carteira','quadro geral da carteira','book de credito atual','book consolidado',
    'me conta a carteira','como vai a carteira','como anda a carteira','qual e a carteira','me mostra a carteira','o que temos na carteira','o que tem na carteira','como esta o portfolio','visao do portfolio','status do portfolio','overview do portfolio','o que temos hoje','o que temos atualmente','resume a carteira','me da um resumo','overview geral','qual a composicao','composicao geral',
    'carteira vs cdi','carteira vs benchmark','estamos batendo o benchmark','estamos batendo o cdi','estamos acima do cdi','estamos abaixo do cdi','retorno acumulado da carteira','performance da carteira','rentabilidade da carteira','quanto rendeu a carteira','quanto a carteira rendeu','como foi a carteira no ano','como foi a carteira no mes','como foi a carteira no trimestre','o que estamos fazendo','como estamos no ano','principais numeros','numeros da carteira','estatisticas da carteira'
  ],
  top_exposicoes:     [
    'maiores posicoes','top emissores','top posicoes','maiores concentracoes','maior concentracao','mais alocado','top 5 emissores','top 10 emissores','top 15 emissores','top 20 emissores','top5','top10','maiores apostas','maiores nomes','maior alocacao','maior saldo','maior saldo bruto','mais investido','onde esta mais exposto','onde estamos mais expostos','onde estamos mais concentrados','quais os maiores emissores','quem tem mais saldo','quem tem mais saldo no book','emissores mais relevantes','nomes mais relevantes','top por saldo','top por mtm','ranking por saldo','ranking por mtm',
    'maiores nomes da carteira','principais emissores da carteira','quais os principais emissores','quem representa mais','quem tem maior peso','quem domina a carteira','quem domina','quem carrega mais peso','quais nomes pesam mais','os 5 maiores','os 10 maiores','os 15 maiores','os 20 maiores','quais dominam a carteira','quais sao as maiores apostas','maior fatia','maior fatia da carteira','maior parcela','maior parcela do book','concentracao de risco','concentracao de risco por nome','principais nomes do book'
  ],
  status_cobertura:   [
    'em watch','em analise','reprovado','aprovado','sem cobertura','sob monitoramento','em acompanhamento','com restricao','restricted','sem analise','pendente de cobertura','nao coberto','descoberto','em watchlist','em watch list','em observacao','em alerta','status watch','status aprovado','status reprovado',
    'quais estao em watch','quais foram aprovados','quais foram reprovados','quais sem cobertura','quais com restricao','status de cobertura','cobertura dos emissores','status dos emissores','quem esta sob monitoramento','nomes em watch','nomes em analise','quem foi reprovado','quem foi aprovado','quem nao tem cobertura','quem esta descoberto','nomes pendentes','nomes pendentes de cobertura','quais ativos em watch','quais ativos sem cobertura','quais aprovados pelo comite','quais reprovados pelo comite','quem o comite aprovou','quem o comite reprovou','status do credito','o que tem status'
  ],
  divergencia_rating: [
    'divergencia de rating','discordancia de rating','conflito de rating','rating douro diferente','rating interno diferente','rating proprio diferente','rating sp diferente','rating mercado diferente','rating moodys diferente','rating fitch diferente','rating douro vs sp','rating douro vs moodys','rating douro vs fitch','rating douro vs mercado',
    'onde o douro discorda','onde douro discorda','onde ha divergencia','onde ha discordancia','rating diferente do mercado','visao propria diferente','douro vs mercado','douro x sp','douro x mercado','douro x moodys','inconsistencia de rating','discrepancia de rating','nao concordam no rating','opiniao diferente sobre rating','rating diverge','onde o douro e mais conservador','onde o douro e mais agressivo','rating interno mais alto','rating interno mais baixo','quem tem rating divergente','nossa avaliacao e diferente','nossa nota e diferente'
  ],
  duration_carteira:  [
    'duration da carteira','duration medio','duration ponderado','duration modificado da carteira','duration efetivo','prazo medio da carteira','prazo medio ponderado','sensibilidade a juros da carteira','dv01 da carteira','sensibilidade da carteira a juros',
    'qual o duration','quanto e o duration','qual o prazo medio','duration total','duration dos ativos','prazo de vencimento medio','prazo dos ativos','prazo ponderado','maturidade media','quanto tempo em media','qual a maturidade da carteira','duration modificado','risco de duration','wal da carteira','weighted average life','vida media da carteira','vida media dos ativos','horizonte medio da carteira','duration esta longo ou curto','duration medio dos papeis','duration mtm','duration por saldo','duration ponderado por mtm','duration ponderado por saldo','quanto sofre com juros','quanto perde com juros','sensibilidade a 100 bps'
  ],
  comparar_emissores: [
    'comparar','versus','vs ','lado a lado','side by side','contrastar','head to head',
    'compara klabin','compara suzano','compara equatorial','compara eneva','compara rumo','compara vale','compara petrobras','compara jbs','compara cosan','compara raizen','compara braskem',
    'qual melhor entre','diferenca entre','qual prefiro','escolher entre','qual ganha','qual e melhor entre','quem ganha entre','quem e melhor entre','prefiro x ou y','comparativo entre','batalha entre','contraste entre',
    'benchmarking entre','comparacao entre',
    // pares vs por emissor (todos os emissores relevantes)
    'klabin vs','suzano vs','vale vs','petrobras vs','equatorial vs','eneva vs','rumo vs','taesa vs','isa vs','auren vs','energisa vs','cemig vs','copel vs','sabesp vs','aegea vs','jbs vs','localiza vs',
    'raizen vs','vibra vs','cosan vs','ultrapar vs','prio vs','petrorio vs','braskem vs','gerdau vs','csn vs','usiminas vs','marfrig vs','brf vs','minerva vs','3tentos vs','slc vs','sao martinho vs','jalles vs','cyrela vs','mrv vs','direcional vs','eztec vs','jhsf vs','movida vs','vamos vs','simpar vs','hidrovias vs','ecorodovias vs','arteris vs','motiva vs','ccr vs','aes brasil vs','alupar vs','cpfl vs','eletrobras vs','neoenergia vs','light vs','engie vs','sanepar vs','copasa vs','corsan vs','brk vs','hapvida vs','rede dor vs','fleury vs','dasa vs','oncoclinicas vs','allos vs','multiplan vs','iguatemi vs','lojas renner vs','magazine luiza vs','assai vs','atacadao vs','grupo mateus vs','americanas vs','casas bahia vs','telefonica vs','vivo vs','oi vs','banco inter vs','daycoval vs','banco master vs','banco bmg vs','banco abc vs','bradesco vs','itau vs','santander vs','safra vs','btg vs','ambev vs','weg vs','gpa vs','pao de acucar vs','azzas vs','quero quero vs','nubank vs','pagbank vs','picpay vs','mercado livre vs','globo vs',
    // forma "X ou Y"
    'klabin ou suzano','vale ou gerdau','petrobras ou prio','prio ou petrorio','raizen ou cosan','vibra ou ipiranga','cosan ou ultrapar','jbs ou marfrig','jbs ou minerva','marfrig ou brf','localiza ou movida','movida ou vamos','rumo ou hidrovias','engie ou aes','copel ou cemig','equatorial ou neoenergia','taesa ou alupar','isa ou alupar','aegea ou sabesp','sabesp ou sanepar','cyrela ou mrv','mrv ou direcional','direcional ou cury','allos ou multiplan','assai ou atacadao','grupo mateus ou assai','hapvida ou rede dor','telefonica ou oi','bradesco ou itau','itau ou santander','banco inter ou nubank',
    // forma "X com Y"
    'comparar klabin com suzano','comparar vale com gerdau','comparar petrobras com prio','comparar jbs com marfrig','comparar rumo com hidrovias','comparar cemig com copel',
    ..._EP.comparar_kw
  ],
  detalhe_ativo:      [
    'qual o spread de','spread atual de','spread de ','taxa de spread','spread do papel','spread do ativo','quanto rende ','yield de ','yield do papel','yield atual','quanto rende o papel de',
    'duration de ','duration do ativo','duration do papel','como esta o spread de','spread esta caro','spread esta barato','esta caro o spread','ta caro','ta barato','caro ou barato','esticado','comprimido','esta esticado','esta comprimido','esta justo','esta atrativo','esta inflado','esta apertado',
    'detalhe do ativo','detalhe de ','detalhe do papel','detalhe do spread de','me conta sobre o ativo','me explica esse ativo','me explica esse papel',
    'taxa atual de','retorno atual de','quanto esta rendendo','quanto e o spread de','NTN-B de ','ntnb de ','ntnb ref','ntnb ref de','referencia de ntnb','referencia da ntnb','referencia de spread','spread sobre ntnb','spread sobre cdi','spread sobre dixu','spread di',
    'vale a pena entrar em','vale a pena montar posicao em','vale a pena comprar','vale a pena vender','spread justo de','spread fair de','fair spread de',
    'taxa indicativa','indicativa de spread','indicativa de taxa','spread indicativo',
    ..._EP.detalhe_kw
  ],
  analise_spreads:    [
    // movimento de spread
    'spreads mais subiram','spreads que abriram','spreads alargaram','spreads comprimiram','spread subiu','spread caiu','spread abriu','spread fechou','spread widening','spread tightening','spread em widening','spread em tightening','spread em compressao','spread em estresse',
    'maior abertura de spread','maior alta de spread','maior queda de spread','maior fechamento de spread','spread que mais abriu','spread que mais subiu','spread que mais fechou','spread que mais caiu','spread que mais comprimiu','abertura de spread no','fechamento de spread no','salto de spread','disparo de spread','explosao de spread',
    // qualitativo
    'piores spreads','melhores spreads','spread mais alto','spreads mais altos','spread elevado','spread alto na carteira','spread acima da mediana','spread abaixo da mediana','spread acima da mediana setorial','spread abaixo da mediana setorial','spread historicamente elevado','spread fora da banda','spread mais desviado','spread deteriorou','spread piorou','spread se deteriorou','spread se comprimiu','spread se alargou',
    // z-score
    'z score','zscore','z-score','spread com z score','spread acima do z','spread fora do z','desvio padrao do spread','desviado do historico','fora da banda historica',
    // variação temporal
    'evolucao dos spreads','variacao dos spreads','movimento dos spreads','abertura de spread no semestre','abertura de spread no trimestre','abertura de spread no ano','abertura de spread no mes','spread escalou','spread saltou','spread disparou','spread explodiu','spread voltou','spread caiu no mes','spread caiu no ano',
    // ranking
    'ranking de spread','ranking de abertura','ranking de fechamento','top spreads','quais spreads','top abertura','top fechamento','top widening','top tightening'
  ],
  grafico_spread:     [
    'grafico de spread','grafico do spread','historico de spread','serie de spread','serie historica de spread','curva de spread','curva historica de spread','curva temporal de spread',
    'ver spread de','mostrar spread de','plotar spread de','plota spread de','mostra spread de','plote spread de','quero ver spread de','exibe spread de','apresenta spread de',
    'visualizar spread de','grafico spread de','timeline de spread','linha do tempo do spread','historico spread de','evolucao spread de','me mostre o spread de','quero o grafico de spread','quero ver o spread historico','plota o spread historico','plote o historico de spread','mostra o spread historico','exibe o spread historico','quero visualizar o spread','quero ver a curva de spread','quero ver a serie de spread','quero ver a evolucao do spread','mostre o grafico de spread','desenha o spread',
    ..._EP.grafico_kw
  ],
  grafico_setor:      [
    'grafico por setor','grafico de exposicao por setor','grafico de alocacao por setor','distribuicao setorial em grafico','pizza por setor','torta por setor','torta setorial','donut setorial','grafico de alocacao','grafico de exposicao','grafico de concentracao','grafico de concentracao setorial',
    'visual da carteira por setor','chart setorial','chart por setor','pizza chart','visualizacao setorial','grafico setorial','alocacao por setor em grafico','mostre a distribuicao setorial','mostra a composicao por setor','mostra a alocacao setorial','exibe a alocacao setorial','plota a distribuicao setorial','quero ver o grafico por setor','quero ver a torta da carteira','quero ver a pizza da carteira','quero o grafico da carteira por setor','grafico de composicao','grafico de composicao da carteira','grafico da composicao da carteira','grafico da carteira por setor','pizza da carteira','visualizacao por setor','breakdown setorial em grafico','quebra setorial em pizza','quebra setorial em grafico'
  ],
  risco_estresse:     [
    'estresse','stress test','risco de refinanciamento','cenario de choque','risco de default','probabilidade de default','default','calote','inadimplencia','alerta de risco','cenario adverso','cenario de crise','cenario de alta de juros','cenario de selic alta','choque de juros','choque de selic',
    'vulneravel','vulnerabilidade','pressao de liquidez','wall de divida','muro de divida','cliff de divida','maturity wall','maturity cliff','problema de refinanciamento','problema de rolagem','covenant','covenant breach','liquidez em estresse',
    'quem fica em apuros','quem tem problema','quem esta em risco','quem fica mal','quem quebraria','quem sofre mais','quem nao resiste','nomes em risco','alerta de covenant','rompe covenant','rompe convenant','quem rompe covenant','quem fica sem caixa','quem fica em apuros com juros altos','quem nao consegue rolar','quem nao consegue refinanciar','quem precisa renegociar',
    'quem tem vencimento curto e rating baixo','duration curta com rating baixo','refinanciamento proximo','quem tem muro de divida','quem tem cliff','quem tem maturity wall','sensibilidade a juros','vulneravel a juros','vulneravel a selic','sensibilidade a choque','quem sofre em recessao','quem sofre com selic alta','quem sofre em juros altos'
  ],
  mapa_risco:         [
    'mapa de risco','mapa risco','mapa de credito','mapa de calor de credito','heat map de credito','heatmap de credito','ordena por risco','ordenar por risco','classifica por risco','classificar por risco',
    'mais arriscados','pior rating','piores ratings','rating critico','credito mais fraco','credito mais fragil','mais fragil','mais vulneravel','risco elevado','emissores de maior risco','nomes mais frageis','nomes com balanco fraco','balanco fraco',
    'quem tem pior credito','quem tem pior balanco','quem e mais arriscado','quais os mais arriscados','ranking de risco','ranking de credito','risco por emissor','high yield na carteira','junk bonds na carteira','nomes high yield','quais sao os high yield','emissores high yield',
    'do mais arriscado','do mais arriscado ao menos','do mais fragil ao mais solido','do pior ao melhor','do pior credito','do pior credito ao melhor','do pior balanco ao melhor','grafico de risco','grafico de credito','visualizacao de risco'
  ],
  evolucao_fundamento:[
    // verbos de evolução + campo (o campo é detectado pelo _detectCampo)
    'como evoluiu','como foi a evolucao','trajetoria de','progressao de','tendencia de','historico de','historico financeiro de','trajetoria financeira de','evolucao financeira de',
    'subiu ao longo','caiu ao longo','cresceu ao longo','decresceu ao longo','como progrediu','como mudou','como variou','como foi','como andou','o que aconteceu com',
    'serie temporal de','ao longo do tempo','ao longo dos anos','ao longo dos trimestres','ao longo dos anos','nos ultimos anos','nos ultimos trimestres','nos ultimos 3 anos','nos ultimos 5 anos','nos ultimos 12 meses',
    'track record de','resultado ao longo','dados historicos de','progressao historica de','historicamente','ao longo do tempo','no longo prazo',
    'como caminhou','como se comportou','a trajetoria de','a evolucao de','linha do tempo de','timeline de','grafico historico de','grafico de evolucao de',
    'subiu ou caiu','cresceu ou caiu','melhorou ou piorou','aumentou ou diminuiu','foi melhorando','foi piorando','vem caindo','vem subindo','vem crescendo','vem melhorando','vem piorando','esta melhorando','esta piorando','esta subindo','esta caindo','tem caido','tem subido','tem crescido','tem aumentado',
    ..._EP.evolucao_kw
  ],
  comparar_setor:     [
    'vs setor','vs media do setor','vs a media do setor','vs a media setorial','frente ao setor','comparado ao setor','comparada ao setor','contra a media do setor','contra a media setorial',
    'benchmark setorial','peer comparison','peers do setor','pares do setor','comparativo setorial','em relacao ao setor','relativo ao setor','relativa ao setor','em relacao a media',
    'vs peers','vs pares','vs benchmark','relativo aos pares','relativa aos pares','relativo aos peers','melhor que o setor','pior que o setor','acima dos peers','abaixo dos peers','acima da media setorial','abaixo da media setorial','acima do setor','abaixo do setor','acima dos pares','abaixo dos pares',
    'como se posiciona no setor','se posiciona frente','como se posiciona frente','como se compara ao setor','em comparacao com o setor','frente aos pares','frente aos peers','como esta frente ao setor','vs peers de','vs peers do setor','vs media de','peers de','quanto acima do setor','quanto abaixo do setor','quanto acima dos peers','quanto abaixo dos peers'
  ],
  sintese_emissor:    [
    'analise completa de','analise completa da','analise completa do','sintese de','sintese do emissor','perfil completo de','me fala tudo sobre','overview do emissor','overview de ','due diligence de','deep dive de','deep dive em',
    'o que voce sabe sobre','analise de credito de','analise detalhada de','me conta tudo de','me conta tudo sobre','tudo sobre','full analysis de','analise aprofundada de','briefing de','briefing do emissor','briefing completo de',
    'quadro completo de','retrato de','fotografia de','full picture de','contexto completo de','visao completa de','panorama de','panorama do emissor','panorama completo de',
    'como esta a situacao de','o que acontece com','o que ta acontecendo com','como anda','como esta indo','o que esta acontecendo com','me da o panorama de','situacao atual de','situacao de','status de','status do emissor','status completo de',
    'resume tudo de','resume tudo sobre','resume a situacao de','me explica tudo de','me explica esse emissor','quero tudo sobre','quero saber tudo de','quero saber tudo sobre','me passa o panorama de','o que ha com','o que ha de novo em','o que tem de novo em','update de ','novidades de ','o que sei sobre',
    ..._EP.sintese_kw
  ],
  mapa_vencimentos:   [
    'mapa de vencimentos','perfil de vencimentos','estrutura de vencimentos','cronograma de vencimentos','distribuicao de vencimentos','curva de vencimentos','breakdown de vencimentos','quebra de vencimentos','perfil de amortizacao','perfil de amortizacao da carteira',
    'quais vencem','quando vencem','proximos vencimentos','ativos com vencimento proximo','ativos vencendo','papeis vencendo','papeis vencendo em breve','vencimentos da carteira',
    'wall de vencimentos','muro de vencimentos','cliff de vencimentos','maturity wall','maturity cliff','concentracao de vencimentos','onde concentram os vencimentos','onde tem concentracao de vencimentos',
    'calendar de vencimento','calendario de vencimentos','agenda de vencimentos','agenda de pagamentos','agenda de juros','agenda de amortizacao','agenda de amortizacoes','pipeline de amortizacao','schedule de amortizacao','rolagem da carteira','quando preciso rolar',
    'ativos que vencem em','ativos com duration menor que 1','duration abaixo de 1','duration acima de 5','quem vence primeiro','quais vencem em 2026','quais vencem em 2027','quais vencem em 2028','vencimentos em 2026','vencimentos em 2027',
    'quem tem vencimento mais curto','quem vence em breve','prazo de vencimento','vencimentos no curto prazo','vencimentos no longo prazo','o que vence no curto prazo','o que vence em ate 12 meses','o que vence em ate 24 meses','quando recebo juros','quando recebo amortizacao'
  ],
  multi_filtro:       [
    // combinações status + filtro
    'aprovado com duration','aprovada com duration','aprovado com spread','aprovado com rating','aprovado com dl ebitda','aprovado com alavancagem','aprovada com spread','aprovada com rating',
    'em watch com','watch com duration','watch com spread','watch com rating','watch com dl ebitda','reprovado com','watch e ','aprovado e ','aprovada e ',
    // filtros numéricos em campo financeiro
    'dl ebitda acima de','dl ebitda abaixo de','dl ebitda maior que','dl ebitda menor que',
    'alavancagem acima de','alavancagem abaixo de','alavancagem maior que','alavancagem menor que','spread acima de','spread abaixo de','spread maior que','spread menor que',
    'duration acima de','duration abaixo de','duration maior que','duration menor que',
    'rating aa com','rating aaa com','rating bb com','rating a com','rating bbb com','rating bb e spread','rating aa e spread','rating aaa e spread','rating bb e duration','rating aaa e duration',
    // ranking de variação
    'maior alta da divida liquida','maior alta do dl ebitda','maior alta de alavancagem','maior alta da alavancagem',
    'maior piora de alavancagem','ranking de piora de alavancagem','quem mais alavancou','quem mais se alavancou',
    'maior deterioracao de dl','quem teve maior alta de alavancagem','mais se alavancaram',
    'maior alta do spread no','maior abertura de spread no','quais tiveram maior alta de spread','quais tiveram maior abertura de spread',
    // ranking por setor
    'ranking de alta de alavancagem em','ranking de alta de spread em','ranking de abertura de spread em','quem mais se alavancou em','quem teve maior abertura de spread em','quais tiveram maior alta do dl ebitda em','quais tiveram maior queda de margem em',
    // setor + filtro
    'energia aprovada com','saneamento aprovado com','eletrico aprovado com','logistica com spread','papel com rating','proteina aprovada com','agro aprovado com','varejo aprovado com','financeiro aprovado com','rodovias aprovadas com','transmissao com rating','energia em watch com','saneamento em watch com','logistica em watch com','proteina em watch com','aprovados em ipca','aprovados em cdi','aprovados em prefixado','watch em proteina','watch em construcao','watch em real estate','setor eletrico aprovado e','setor de saneamento aprovado e','setor de papel aprovado e','setor de proteina aprovado e','setor de logistica aprovado e','spread alto em high yield'
  ]
};
function _rebuildDouradoKW() {
  if (typeof ATIVOS === 'undefined') return;
  if ((_EP.sintese_kw||[]).length > 0) return;
  _EP = _buildEmissorPhrases();
  _INTENT_KW.exposicao_emissor.push(..._EP.exposicao_kw);
  _INTENT_KW.comparar_emissores.push(..._EP.comparar_kw);
  _INTENT_KW.detalhe_ativo.push(..._EP.detalhe_kw);
  _INTENT_KW.grafico_spread.push(..._EP.grafico_kw);
  _INTENT_KW.evolucao_fundamento.push(..._EP.evolucao_kw);
  _INTENT_KW.sintese_emissor.push(..._EP.sintese_kw);
}

const _EXEMPLOS = {
  exposicao_setor:    ['qual exposicao em energia','quanto tenho em utilities','posicao no setor financeiro','percentual em infraestrutura','peso de energia','quanto esta alocado em financeiro','exposicao em papel','quanto em saude','quanto esta no setor eletrico','qual o peso em saneamento','quanta exposicao em logistica','o que tenho em telecomunicacoes','alocacao em celulose','posicao em construcao','quanto em mineracao','quanto em transmissao','quanto em distribuicao de energia','quanto em geracao de energia','quanto em rodovias','quanto em concessoes','quanto em portos','quanto em ferrovias','quanto em proteina','quanto em agro','quanto em alimentos','quanto em bebidas','quanto em frigorifico','quanto em quimica','quanto em petroquimica','quanto em oleo e gas','quanto em mineracao e siderurgia','quanto em aco','quanto em varejo alimentar','quanto em varejo de moda','quanto em shopping','quanto em construcao civil','quanto em incorporadora','quanto em real estate','quanto em transporte','quanto em locacao de veiculos','quanto em educacao','quanto em healthcare','quanto em hospitalar','quanto em farma','quanto em tecnologia','quanto em fintech','quanto em bancos','quanto em seguros','quanto em meios de pagamento','peso de energia eletrica','peso de saneamento','peso de papel e celulose','peso de proteina','peso do agro','peso da industria','exposicao em renda fixa','exposicao em ipca','exposicao em cdi','exposicao em prefixado','quanto em debenture incentivada','quanto em cri','quanto em cra','quanto em letra financeira'],
  exposicao_rating:   ['exposicao em aaa','quanto tenho em braa','posicao em high grade','percentual em rating aa','alocacao em bb','emissores com rating a','exposicao investment grade','quanto em grau de investimento','posicao em high yield','quanto em junk','emissores com nota baixa','emissores com grau especulativo','quanto em subinvestimento','quanto em aaa br','quanto em aa br','quanto em a br','quanto em bbb br','quanto em bb br','peso por rating na carteira','distribuicao por rating','breakdown por rating','quebra por rating','rating average da carteira','rating medio ponderado','quais emissores rating aaa','quais emissores rating aa+','quais rating a-','quais rating bbb+','quais rating abaixo de bbb','quantos emissores high yield','peso de high yield','peso de investment grade','exposicao a credito ig','exposicao a credito hy','quanto em grau especulativo','quanto em rating de transito','quanto em nota baixa','rating mais frequente na carteira','rating mais comum'],
  exposicao_emissor:  [..._EP.exposicao_ex,'quanto tenho em petrobras','posicao em vale','exposicao a localiza','qual o peso de klabin','quanto esta alocado em suzano','posicao em rumo','tamanho da posicao em equatorial','quanto em jbs','qual o saldo em eneva','quanto temos de taesa','posicao em auren','qual a exposicao a isa','como esta a posicao de energisa','nossa posicao em cemig','minha posicao em sabesp','quanto investido em aegea'],
  overview_carteira:  ['resumo da carteira','overview da carteira','composicao atual','como esta a carteira','me da um resumo geral','qual o estado da carteira','visao geral','resumo geral','fotografia da carteira','snapshot da carteira','me conta a carteira','quadro geral da carteira','retrato da carteira','como vai a carteira','sumario da carteira','panorama da carteira','como anda a carteira','carteira vs cdi','estamos batendo o benchmark','estamos batendo o cdi','estamos acima do cdi','estamos abaixo do cdi','retorno acumulado da carteira','performance da carteira','como foi a carteira no mes','como foi a carteira no ano','como foi a carteira no trimestre','rentabilidade da carteira','quanto rendeu a carteira','quanto a carteira rendeu','o que estamos fazendo','como estamos no ano','overview geral','composicao geral','me da o panorama','quadro consolidado','estatisticas da carteira','numeros da carteira','principais numeros','como vai o portfolio','status do portfolio','overview do portfolio','o que temos hoje','o que temos atualmente','como esta o book','book de credito atual'],
  top_exposicoes:     ['maiores posicoes','top emissores','maiores concentracoes','onde esta mais concentrado','top 5 posicoes','maiores emissores por saldo','ranking de emissores','quais as maiores apostas','emissores mais relevantes','onde esta o maior risco','maior alocacao por emissor','quem tem mais saldo','maiores nomes na carteira','top 10 emissores','maiores nomes da carteira','os 5 maiores emissores','os 10 maiores emissores','top 20 posicoes','quem domina a carteira','quem representa mais','maior fatia da carteira','maior parcela do book','concentracao de risco por nome','principais emissores da carteira','nomes mais relevantes','quais nomes pesam mais','quem tem mais saldo no book','ranking por mtm','ranking por saldo','top exposicoes da carteira','quem sao as maiores apostas','onde estamos mais concentrados','onde temos mais risco de credito','maior saldo bruto por emissor','principais nomes do book','quais nomes carregam mais peso'],
  status_cobertura:   ['quais estao em analise','emissores em watch','o que esta reprovado','nomes sem cobertura','quais foram aprovados','status dos emissores','quais em watch list','quem esta sob monitoramento','emissores em acompanhamento','quais com restricao','quais descobertos','quais sem cobertura','quem nao tem cobertura','nomes pendentes','quais em watchlist','quais estao em watch list','o que esta em monitoramento','quais estao restritos','status de cobertura dos emissores','quem nao tem analise','nomes sem analise','quais tem cobertura aprovada','quais com cobertura ativa','emissores com restricao na carteira','nomes em alerta','status do credito','o que tem status watch','o que tem status aprovado','o que tem status reprovado','nomes em observacao','nomes pendentes de cobertura','quais ativos em watch','quais ativos sem cobertura','quais emissores aprovados pelo comite','quais emissores reprovados pelo comite','quem esta com restricao'],
  divergencia_rating: ['quais tem divergencia de rating','rating douro diferente do mercado','emissores com rating diferente','onde o douro discorda do mercado','conflito de rating','onde ha discordancia de nota','rating interno diferente do externo','visao propria diferente','douro x mercado','onde o rating proprio discorda','rating douro vs sp','rating douro vs moodys','rating douro vs fitch','onde o douro e mais conservador','onde o douro e mais agressivo','rating interno mais alto que externo','rating interno mais baixo que externo','divergencia entre rating proprio e mercado','discrepancia de rating','quais emissores com rating divergente','quem tem visao diferente do mercado','nomes com rating em conflito','onde nossa nota e diferente','quem o douro discorda','quem o douro concorda menos','nomes onde nossa avaliacao e diferente'],
  duration_carteira:  ['qual o duration medio','duration da carteira','prazo medio ponderado','quanto e o duration','qual o prazo medio','duration ponderado da carteira','sensibilidade a juros da carteira','quanto tempo em media','duration medio dos ativos','qual o prazo dos ativos','duration modificado da carteira','duration efetivo','dv01 da carteira','quanto e a sensibilidade da carteira a juros','quanto a carteira sofre com juros','prazo medio dos papeis','vida media da carteira','maturidade media','quantos anos de duration','duration esta longo ou curto','carteira esta com duration longo','duration esta acima de quanto','quanto e o prazo da carteira','horizonte medio da carteira','wal da carteira','weighted average life','prazo ponderado por saldo','duration mtm','duration por saldo'],
  comparar_emissores: ['comparar klabin com suzano','klabin vs suzano','qual melhor entre klabin e suzano','diferenca entre klabin e petrobras','compara equatorial com engie','qual prefiro klabin ou vale','side by side klabin suzano','klabin lado a lado com suzano','contrastar eneva e engie','qual ganha klabin ou suzano em alavancagem','vale vs gerdau','csn vs usiminas','petrobras vs prio','prio vs petrorio','raizen vs cosan','vibra vs ipiranga','ultrapar vs cosan','braskem vs unipar','jbs vs marfrig','jbs vs minerva','marfrig vs brf','brf vs jbs','3tentos vs slc agricola','sao martinho vs jalles machado','localiza vs movida','movida vs vamos','rumo vs hidrovias','ecorodovias vs arteris','ccr vs motiva','engie vs aes brasil','engie vs auren','copel vs cemig','cemig vs energisa','equatorial vs neoenergia','taesa vs alupar','taesa vs isa','isa vs alupar','aegea vs sabesp','sabesp vs sanepar','copasa vs sanepar','cyrela vs mrv','mrv vs direcional','direcional vs cury','eztec vs cyrela','allos vs multiplan','multiplan vs iguatemi','lojas renner vs magazine luiza','assai vs atacadao','grupo mateus vs assai','americanas vs casas bahia','hapvida vs rede dor','rede dor vs fleury','dasa vs oncoclinicas','telefonica vs oi','bradesco vs itau','itau vs santander','banco inter vs nubank','daycoval vs banco abc','banco master vs banco bmg','klabin vs suzano em alavancagem','klabin vs suzano em ebitda','klabin vs suzano em margem','vale vs gerdau em duration','vale vs gerdau em spread','petrobras vs prio em fcf','jbs vs marfrig em divida','rumo vs hidrovias em duration','taesa vs isa em rating','aegea vs sabesp em alavancagem','quem ganha entre klabin e suzano','quem e melhor entre vale e gerdau','quem ta mais alavancado klabin ou suzano','prefiro klabin ou suzano','prefiro vale ou gerdau','prefiro petrobras ou prio','prefiro jbs ou marfrig','comparativo klabin x suzano','comparativo vale x gerdau','batalha entre klabin e suzano','contraste entre jbs e marfrig','head to head klabin suzano'],
  detalhe_ativo:      [..._EP.detalhe_ex,'qual o spread de klabin','spread atual da suzano','taxa da posicao em rumo','duration do klabin','spread de petrobras','como esta o spread de vale','quanto rende equatorial','taxa atual de taesa','spread da isa','retorno da auren','yield da eneva','klabin ta caro ou barato','o spread de suzano esta caro','ntnb ref de equatorial','qual a ntnb de taesa','spread de vale esta esticado','o spread de rumo esta comprimido'],
  analise_spreads:    ['quais spreads mais subiram','quais abriram mais spread','spread que mais subiu na carteira','quais emissores com spread mais alto','spread mais alto em energia','piores spreads do setor financeiro','quais estao acima da mediana','quais spreads fecharam','melhores spreads da carteira','top spreads mais altos','quais empresas tiveram a maior alta do spread no ultimo semestre','quais tiveram maior abertura de spread no trimestre','ranking de abertura de spread','spread que mais abriu no semestre','quem teve maior alta de spread','quais emissores com spread mais deteriorado','top abertura de spread no ano','maior widening de spread','quais spreads mais alargaram no ultimo ano','spread que mais subiu nos ultimos 6 meses','quais spreads deram um salto','quais spreads escalaram mais','spread que mais disparou','spread que mais explodiu','quem teve o maior salto de spread','spread com maior subida no trimestre','evolucao dos spreads na carteira','spreads que mais se deterioraram','spreads que mais comprimiram','spreads com maior queda no semestre','quais spreads abriram no mes','spreads que mais fecharam no mes','spreads que mais comprimiram no trimestre','spread que mais caiu no semestre','spread que mais caiu no ano','top fechamento de spread','top abertura de spread','quem teve a maior queda de spread','spreads no top de abertura','spreads no top de fechamento','spreads em widening','spreads em tightening','spreads em compressao','spreads em estresse','spreads acima da mediana setorial','spreads abaixo da mediana setorial','spreads acima do z score','spreads desviados do historico','spread mais desviado da carteira','spread mais fora da banda','spreads com z score acima de 2','spreads com z score acima de 1','spreads fora da banda historica','quem esta com spread fora da banda','melhores spreads do book','piores spreads do book','spreads que mais escalaram em energia','spreads que mais escalaram em saneamento','spreads que mais escalaram em logistica','spreads que mais subiram em proteina','spreads que mais subiram em papel','quem tem o spread mais elevado em utilities','spreads no setor de bancos','spreads no setor de varejo','spreads mais altos em real estate','quem teve maior abertura no trimestre','quem teve maior fechamento no trimestre','spreads mais voláteis','spread historicamente elevado','spread historicamente comprimido','quem esta com spread caro','quem esta com spread barato'],
  grafico_spread:     [..._EP.grafico_ex,'grafico de spread da klabin','historico spread suzano','evolucao do spread petrobras','ver spread de vale','plota spread de rumo','mostre o spread historico de equatorial','serie de spread da localiza','grafico spread de klabin','timeline de spread de taesa','linha do tempo do spread de isa','me mostra a evolucao do spread de auren','quero ver o historico de spread da eneva','plote a serie de spread de jbs'],
  grafico_setor:      ['grafico de exposicao por setor','mostre a distribuicao setorial','quero ver o grafico por setor','distribuicao setorial em grafico','pizza por setor','visual da carteira por setor','chart de alocacao por setor','visualizacao setorial','grafico de concentracao setorial','grafico de alocacao da carteira','grafico setorial','breakdown setorial em grafico','quebra setorial em pizza','torta setorial','donut setorial','visual da composicao setorial','mostra a composicao por setor','exibe a alocacao setorial','plota a distribuicao setorial','quero ver a torta da carteira','quero ver a pizza da carteira','quero o grafico da carteira por setor','grafico de exposicao setorial','grafico de concentracao por setor','visualizacao por setor da carteira','grafico de carteira por setor','grafico da composicao da carteira','chart por setor','pizza chart por setor'],
  risco_estresse:     ['quais emissores em risco de refinanciamento','cenario de estresse na carteira','quem pode ter problema sob estresse de juros','stress test da carteira','liquidez em estresse de cdi','quais teriam problema num choque de taxa','covenant stress test','alerta de covenant na carteira','quem fica em apuros com juros altos','vulnerabilidade da carteira a choques','quem tem wall de divida proximo','nomes com pressao de liquidez','quem tem cliff de divida','quais emissores vulneraveis a crise','quais nomes mais sensiveis a alta de juros','quem fica em risco num cenario adverso','quem quebraria em um cenario de juros altos','quem sofre mais com selic em 15','quem nao aguenta selic alta','nomes mais expostos a choque de juros','quem tem muro de divida proximo','quem tem mais divida vencendo','quem ta na corda bamba','quem corre risco de default','nomes em risco de default','probabilidade de default','quais emissores podem dar calote','quem nao consegue rolar a divida','quem nao consegue refinanciar','quem fica sem caixa em estresse','quais teriam covenant breach','quem rompe covenant','quem rompe convenant em cenario estressado','alerta de covenant em juros altos','quem precisa renegociar divida em breve','quem tem maturity wall em 2026','quem tem maturity wall em 2027','quem tem cliff em 2026','quem corre risco em cenario adverso','vulnerabilidade a choque de selic','sensibilidade a choque de juros','quem sofre em recessao','quem fica em apuros em recessao'],
  mapa_risco:         ['mapa de risco dos emissores','quais os emissores mais arriscados','ordena por risco de credito','quem tem pior rating','emissores com rating critico','ranking de risco da carteira','quais emissores com mais risco','quem tem pior credito','nomes mais frageis','emissores high yield na carteira','quais tem credito mais fraco','ranking do pior ao melhor rating','quem e mais vulneravel','mapa de credito','ordena por risco','quem sao os high yield da carteira','nomes high yield no book','junk bonds na carteira','quais sao os piores creditos','ordena por nota de credito','classifica por risco','ranking do pior credito ao melhor','do mais arriscado ao menos arriscado','do mais fragil ao mais solido','quem tem o pior balanco','nomes com balanco mais fraco','quem ta mais alavancado','quem tem mais risco financeiro','nomes em rating critico','quem tem rating ccc','quem tem rating bb','quem tem rating b','quem esta abaixo do investment grade','heat map de credito','grafico de risco da carteira','mapa de calor de credito'],
  evolucao_fundamento:['como evoluiu o ebitda da klabin','tendencia de alavancagem da suzano','historico de roe da petrobras','evolucao da margem ebitda da vale','serie temporal de divida liquida da equatorial','como foi o fluxo de caixa da rumo nos ultimos 3 anos','trajetoria da liquidez da klabin','como caminhou o dl ebitda da eneva','como progrediu o roe de taesa','subiu o ebitda da auren','caiu a margem de jbs','como variou o fcf de petrobras','trajetoria historica do lucro de suzano','como mudou a divida de klabin ao longo do tempo','crescimento do ebitda de equatorial','progressao da alavancagem de rumo','o ebitda da cemig vem subindo','a alavancagem da sabesp foi melhorando','como andou a margem da aegea','divida liquida de copel ao longo do tempo','o roe de energisa vem caindo','vem melhorando a liquidez da isa','foi piorando o dl ebitda da localiza','como mudou o fcf da taesa nos ultimos anos','a cobertura de juros da eneva cresceu','como foi o lucro de auren ao longo dos trimestres','evolucao do ebitda de raizen','evolucao do ebitda de vibra','evolucao do ebitda de cosan','evolucao do ebitda de prio','evolucao da margem de braskem','evolucao da margem de gerdau','evolucao do dl ebitda de csn','evolucao do dl ebitda de jbs','evolucao do dl ebitda de marfrig','evolucao do dl ebitda de brf','evolucao do roe de minerva','evolucao da alavancagem de 3tentos','evolucao da margem de slc agricola','evolucao do ebitda de cyrela','evolucao da divida de mrv','evolucao da divida de direcional','evolucao do roe de eztec','tendencia da alavancagem de localiza','tendencia da alavancagem de movida','tendencia de divida de vamos','tendencia do ebitda de simpar','historico do ebitda de hidrovias','historico do ebitda de ecorodovias','historico de divida de arteris','historico de fcf de motiva','como foi o ebitda de aes brasil','como foi a alavancagem de alupar','como foi o ebitda de copel','como foi o ebitda de cemig','como foi o ebitda de cpfl','como evoluiu a divida de eletrobras','como evoluiu a margem de neoenergia','como evoluiu o fcf de energisa','como evoluiu o lucro de light','como evoluiu o ebitda de engie','como evoluiu o ebitda de aegea','como evoluiu o dl ebitda de sabesp','como evoluiu o dl ebitda de sanepar','como evoluiu a divida de copasa','tendencia de roe de hapvida','tendencia de divida de rede dor','tendencia de margem de fleury','tendencia de ebitda de dasa','margem de allos ao longo do tempo','divida de multiplan ao longo do tempo','ebitda de magazine luiza ao longo do tempo','divida de assai ao longo do tempo','margem de lojas renner historicamente','ebitda de telefonica historicamente','divida de oi historicamente','divida do banco inter historicamente','margem de daycoval historicamente','ebitda da klabin subiu ou caiu','dl ebitda da suzano cresceu ou caiu','alavancagem da vale aumentou ou diminuiu','margem de petrobras melhorou ou piorou','roe de jbs vem subindo ou caindo','o que aconteceu com o ebitda de klabin','o que aconteceu com a divida de suzano','o que aconteceu com a margem de vale','o que aconteceu com a alavancagem de jbs','como foi a evolucao financeira de klabin','como foi a evolucao financeira de suzano','trajetoria financeira de petrobras','trajetoria financeira de vale','trajetoria financeira de rumo','vem caindo a margem da klabin','vem subindo a alavancagem da suzano','foi melhorando o roe da petrobras','foi piorando o fcf da vale'],
  comparar_setor:     ['klabin vs media do setor de papel','como a suzano se compara ao setor','alavancagem da vale vs media do setor','como esta a petrobras frente ao setor','comparar equatorial com a media do setor eletrico','benchmarking setorial de alavancagem','taesa relativa ao setor eletrico','eneva vs peers de energia','isa vs media do setor de transmissao','como a auren se posiciona no setor','rumo frente aos pares de logistica','como a klabin se compara aos peers de papel','cemig vs media do setor eletrico','sabesp frente aos pares de saneamento','energisa vs benchmark do setor','copel relativa ao setor de distribuicao','aegea vs media de saneamento','como a localiza se compara ao setor','jbs frente ao setor de proteina','como a engie se posiciona frente aos pares','a alavancagem da vale esta acima dos peers','spread da klabin vs media do setor','spread de suzano frente ao setor de celulose','raizen vs media do setor de combustivel','vibra vs media do setor de combustivel','cosan vs media do setor de combustivel','prio vs media de oleo e gas','braskem vs peers de petroquimica','gerdau vs peers de siderurgia','csn vs media do setor de aco','usiminas vs peers de aco','jbs vs peers de proteina','marfrig vs media de frigorifico','brf vs media de proteina','minerva vs peers de carne','3tentos vs peers de agro','slc vs peers de agronegocio','sao martinho vs peers de acucar','jalles machado vs peers de etanol','cyrela vs peers de construtora','mrv vs media de incorporadora','direcional vs media de construtora','localiza vs peers de aluguel de veiculos','movida vs media de locacao','vamos vs peers de locacao pesada','rumo vs peers de ferrovia','hidrovias vs peers de logistica fluvial','ecorodovias vs peers de rodovia','arteris vs media de concessao rodoviaria','motiva vs peers de rodovia','aes brasil vs media de energia eletrica','alupar vs peers de transmissao','copel vs media do setor eletrico','cpfl vs peers de distribuicao','eletrobras vs media do setor','neoenergia vs peers de eletrica','energisa vs media de distribuicao','equatorial vs peers de eletrica','engie vs peers de geracao','aegea vs media do setor de saneamento','sabesp vs peers de saneamento','sanepar vs media do setor','copasa vs peers de utilities','hapvida vs peers de healthcare','rede dor vs media de hospital','fleury vs peers de diagnostico','dasa vs media de saude','allos vs peers de shopping','multiplan vs media do setor','iguatemi vs peers de shopping','magazine luiza vs peers de varejo','lojas renner vs media de moda','assai vs peers de varejo alimentar','grupo mateus vs peers de atacarejo','telefonica vs peers de telecom','oi vs media de telecom','banco inter vs media de bancos digitais','daycoval vs peers de bancos medios','bradesco vs peers de bancos grandes','itau vs media de bancos','como esta a vale comparada aos peers','como a petrobras se compara ao setor','como a klabin se compara aos peers','como a suzano esta frente ao setor','klabin esta acima da media setorial','suzano esta abaixo da media setorial','vale esta melhor que o setor','vale esta pior que o setor','rumo esta melhor que peers','rumo esta pior que peers','aegea esta acima dos pares','sabesp esta acima dos pares','quanto a klabin esta acima do setor','quanto a vale esta abaixo do setor','dl ebitda de klabin vs peers','margem de suzano vs setor','roe de petrobras vs setor','spread de jbs vs media setorial','spread de marfrig vs setor de proteina'],
  sintese_emissor:    ['analise completa da klabin','me fala tudo sobre a suzano','perfil completo de petrobras','overview do emissor vale','due diligence de equatorial','analise de credito da rumo','o que voce sabe sobre localiza','analise detalhada da jbs','me conta tudo de taesa','tudo sobre eneva','full analysis de isa','quadro completo de auren','retrato de energisa','fotografia de cemig','contexto completo de copel','visao completa de sabesp','snapshot de aegea','como anda a cemig','como esta indo a sabesp','o que esta acontecendo com a rumo','me passa o panorama da equatorial','resume tudo de klabin','resume a situacao da suzano','como esta a engie','quero tudo sobre taesa','me da o panorama da isa','situacao atual da vale','o que acontece com a jbs','como anda a localiza','me explica tudo de energisa','o que ha com a copel','como esta a auren hoje','deep dive em aegea','analise completa de raizen','analise completa de vibra','analise completa de cosan','analise completa de ultrapar','analise completa de prio','analise completa de petrorio','analise completa de braskem','analise completa de gerdau','analise completa de csn','analise completa de usiminas','analise completa de marfrig','analise completa de brf','analise completa de minerva','analise completa de 3tentos','analise completa de slc agricola','analise completa de sao martinho','analise completa de cyrela','analise completa de mrv','analise completa de direcional','analise completa de eztec','analise completa de jhsf','analise completa de movida','analise completa de vamos','analise completa de simpar','analise completa de hidrovias','analise completa de ecorodovias','analise completa de arteris','analise completa de motiva','analise completa de aes brasil','analise completa de alupar','analise completa de cpfl','analise completa de eletrobras','analise completa de neoenergia','analise completa de light','analise completa de engie','analise completa de aegea','analise completa de sanepar','analise completa de copasa','analise completa de hapvida','analise completa de rede dor','analise completa de fleury','analise completa de dasa','analise completa de oncoclinicas','analise completa de allos','analise completa de multiplan','analise completa de iguatemi','analise completa de magazine luiza','analise completa de lojas renner','analise completa de assai','analise completa de atacadao','analise completa de grupo mateus','analise completa de telefonica','analise completa de oi','analise completa de banco inter','analise completa de daycoval','analise completa de banco master','analise completa de banco bmg','analise completa de bradesco','analise completa de itau','analise completa de safra','analise completa de btg pactual','perfil completo de raizen','perfil completo de vibra','perfil completo de cosan','perfil completo de prio','perfil completo de braskem','perfil completo de gerdau','perfil completo de jbs','perfil completo de marfrig','perfil completo de brf','perfil completo de cyrela','perfil completo de mrv','perfil completo de localiza','perfil completo de movida','perfil completo de rumo','perfil completo de hidrovias','perfil completo de aes brasil','perfil completo de alupar','perfil completo de copel','perfil completo de cemig','perfil completo de cpfl','perfil completo de aegea','perfil completo de sabesp','perfil completo de hapvida','perfil completo de magazine luiza','perfil completo de assai','perfil completo de telefonica','perfil completo de banco inter','perfil completo de bradesco','perfil completo de itau','me conta tudo sobre raizen','me conta tudo sobre vibra','me conta tudo sobre cosan','me conta tudo sobre prio','me conta tudo sobre braskem','me conta tudo sobre gerdau','me conta tudo sobre csn','me conta tudo sobre jbs','me conta tudo sobre marfrig','me conta tudo sobre brf','me conta tudo sobre cyrela','me conta tudo sobre mrv','me conta tudo sobre direcional','me conta tudo sobre movida','me conta tudo sobre vamos','me conta tudo sobre rumo','me conta tudo sobre ecorodovias','me conta tudo sobre arteris','me conta tudo sobre aes brasil','me conta tudo sobre copel','me conta tudo sobre cemig','me conta tudo sobre eletrobras','me conta tudo sobre engie','me conta tudo sobre aegea','me conta tudo sobre sabesp','me conta tudo sobre hapvida','me conta tudo sobre rede dor','me conta tudo sobre magazine luiza','me conta tudo sobre lojas renner','me conta tudo sobre assai','me conta tudo sobre telefonica','me conta tudo sobre banco inter','me conta tudo sobre bradesco','me conta tudo sobre itau','como anda raizen','como anda vibra','como anda cosan','como anda prio','como anda braskem','como anda gerdau','como anda jbs','como anda marfrig','como anda brf','como anda cyrela','como anda mrv','como anda movida','como anda vamos','como anda rumo','como anda hidrovias','como anda aes brasil','como anda copel','como anda cpfl','como anda eletrobras','como anda neoenergia','como anda engie','como anda aegea','como anda sanepar','como anda hapvida','como anda rede dor','como anda allos','como anda multiplan','como anda magazine luiza','como anda assai','como anda telefonica','como anda oi','como anda banco inter','como anda daycoval','o que ta acontecendo com vale','o que ta acontecendo com petrobras','o que ta acontecendo com klabin','o que ta acontecendo com suzano','o que ta acontecendo com jbs','o que ta acontecendo com prio','o que ta acontecendo com cosan','o que ta acontecendo com raizen','o que ta acontecendo com vibra','o que ta acontecendo com cemig','o que ta acontecendo com copel','o que ta acontecendo com eletrobras','o que ta acontecendo com engie','o que ta acontecendo com aegea','o que ta acontecendo com sabesp','o que ta acontecendo com magazine luiza','o que ta acontecendo com americanas','o que ta acontecendo com casas bahia','o que ta acontecendo com hapvida','o que ta acontecendo com banco master','o que ta acontecendo com light','due diligence de raizen','due diligence de cosan','due diligence de prio','due diligence de braskem','due diligence de gerdau','due diligence de jbs','due diligence de marfrig','due diligence de cyrela','due diligence de mrv','due diligence de movida','due diligence de rumo','due diligence de aes brasil','due diligence de copel','due diligence de cemig','due diligence de aegea','due diligence de hapvida','due diligence de magazine luiza','due diligence de telefonica','due diligence de banco inter','tudo sobre vale','tudo sobre petrobras','tudo sobre raizen','tudo sobre prio','tudo sobre braskem','tudo sobre cyrela','tudo sobre mrv','tudo sobre movida','tudo sobre vamos','tudo sobre rumo','tudo sobre copel','tudo sobre cemig','tudo sobre aegea','tudo sobre hapvida','tudo sobre magazine luiza','tudo sobre assai','tudo sobre banco inter','tudo sobre daycoval','o que sei sobre vale','o que sei sobre petrobras','o que sei sobre klabin','o que sei sobre suzano','o que sei sobre raizen','o que sei sobre prio','o que sei sobre cosan','o que sei sobre braskem','o que sei sobre jbs','o que sei sobre marfrig','o que sei sobre cyrela','o que sei sobre rumo','o que sei sobre aegea','o que sei sobre copel','o que sei sobre cemig','quero o briefing de klabin','quero o briefing de suzano','quero o briefing de raizen','quero o briefing de prio','quero o briefing de jbs','quero o briefing de rumo'],
  mapa_vencimentos:   ['quais ativos vencem nos proximos 12 meses','perfil de vencimentos da carteira','mapa de vencimentos','cronograma de vencimento da carteira','quando vencem os ativos','ativos com vencimento proximo','wall de vencimentos','muro de vencimentos da carteira','calendario de vencimentos','agenda de amortizacoes','quais ativos expiram em breve','vencimentos concentrados','cliff de vencimentos','proximos vencimentos da carteira','estrutura de vencimentos da carteira','schedule de amortizacao','quando vencem os papeis','quais papeis vencem em 2026','quais papeis vencem em 2027','quais papeis vencem em 2028','quais papeis vencem nos proximos 24 meses','quais papeis vencem nos proximos 6 meses','vencimento por ano da carteira','distribuicao de vencimentos por ano','breakdown por ano de vencimento','quando concentram os vencimentos','onde tem concentracao de vencimentos','curva de vencimentos da carteira','perfil de amortizacao','perfil de amortizacao da carteira','agenda de pagamentos','agenda de juros','quando recebo os juros','quando recebo amortizacao','calendario de juros da carteira','linha do tempo de vencimentos','timeline de vencimentos','rolagem da carteira','quando preciso rolar a carteira','o que vence no curto prazo','vencimentos no curto prazo','vencimentos no longo prazo','quais ativos com duration curta','quais ativos com duration longa','papeis vencendo em breve','papeis com vencimento em ate 1 ano','papeis com vencimento de 1 a 3 anos','papeis com vencimento acima de 5 anos','ativos com duration menor que 1','ativos com duration acima de 5'],
  multi_filtro:       ['energia eletrica aprovada com duration acima de 4','emissores rating aa+ e spread abaixo de 1.2%','watch e saneamento e dl ebitda acima de 3x','ativos aprovados com duration maior que 3','emissores em watch no setor eletrico','spread abaixo de 1% com rating aa','quais emissores aprovados no setor de papel','ativos com duration menor que 2 e em watch','emissores com spread acima de 2% aprovados','quais empresas tiveram a maior alta da divida liquida ebitda no trimestre','quais tiveram maior alta de alavancagem no trimestre','ranking de piora de alavancagem no semestre','quem mais alavancou no ultimo trimestre','maior deterioracao de dl ebitda no ano','quem teve maior alta do dl ebitda nos ultimos 6 meses','quais emissores mais se alavancaram','desalavancagem no semestre quem liderou','quais tiveram maior alta do spread no ultimo semestre','ranking de abertura de spread no trimestre','quais emissores com maior alta de spread no ano','quais tiveram salto de spread no trimestre','quais spreads escalaram mais no semestre','quem teve o maior salto de dl ebitda','quais tiveram subida de alavancagem acima de 1x','emissores com escalada de spread no ultimo ano','quais tiveram piora de alavancagem e watch','aprovados com spread alto e duration longo','watch com rating baixo e spread elevado','saneamento com dl ebitda acima de 4 aprovado','energia eletrica aprovada com spread acima de 1','saneamento aprovado com duration acima de 5','logistica aprovada com rating aa','papel e celulose com rating aaa','proteina aprovada com dl ebitda abaixo de 3','agro aprovado com duration acima de 4','varejo aprovado com spread acima de 2','financeiro aprovado com rating aaa','rodovias aprovadas com duration acima de 6','transmissao com rating aa e spread abaixo de 1','energia em watch com spread acima de 2','saneamento em watch com dl ebitda acima de 4','logistica em watch com rating baixo','proteina em watch com alavancagem acima de 3','energia eletrica com rating aaa e spread baixo','setor eletrico aprovado e duration longo','setor eletrico aprovado e spread elevado','setor de saneamento aprovado e duration acima de 5','setor de papel aprovado e rating aa','setor de proteina aprovado e dl ebitda abaixo de 3','setor de logistica aprovado e duration longa','rating aa e spread abaixo de 1','rating aaa e duration maior que 5','rating aaa e spread baixo','rating bb e spread alto','rating bbb e duration curta','rating bb com spread acima de 3','spread acima de 2 e rating bb','spread alto em high yield','aprovados com duration longo','aprovados com duration curto','aprovados com rating alto','aprovados com rating baixo','watch com duration curta','watch com rating baixo','watch com spread alto','watch em proteina','watch em construcao','watch em real estate','aprovados em ipca','aprovados em cdi','aprovados em prefixado','ranking de alta de alavancagem em proteina','ranking de alta de alavancagem em saneamento','ranking de alta de spread em energia','ranking de alta de spread em saneamento','quem mais se alavancou em logistica','quem mais se alavancou em proteina','quem mais se alavancou em construcao','quem teve maior abertura de spread em energia','quem teve maior abertura de spread em proteina','quem teve maior abertura de spread em logistica','quais tiveram maior alta do dl ebitda em saneamento','quais tiveram maior alta do dl ebitda em proteina','quais tiveram maior queda de margem em energia','quais tiveram maior queda de margem em proteina']
};

function _matchIntent(norm) {
  // Detecta query de delta/variação temporal de fundamentais ou spread → query_param
  const _hasDeltaKW = [
    'maior alta','maior queda','maior abertura','maior fechamento',
    'mais subiram','mais caiu','mais aumentou','mais deteriorou',
    'variacao da','variacao do','variacao de',
    'piora de','piora do','piora da',
    'desalavancagem','alavancagem subiu','alavancagem aumentou',
    'quais empresas tiveram','quem mais aumentou','quem mais reduziu',
    'quem teve maior','ranking de variacao','ranking de abertura','ranking de piora',
    'salto de','salto da','salto do',
    'escalada de','escalada da','escalada do',
    'subida de','subida da','subida do',
    'alta de','alta da','alta do',
    'disparo de','disparo da','disparo do',
    'explosao de','explosao da',
    'deterioracao de','deterioracao da','deterioracao do',
    'crescimento de','crescimento da',
    'expansao de','expansao da',
    'compressao de','compressao da',
    'queda de','queda da','queda do',
    'reducao de','reducao da',
    'melhora de','melhora da',
    'widening','tightening',
    'que mais subiram','que mais cairam','que mais aumentaram','que mais reduziram',
    'quem mais se alavancou','quais mais se alavancaram',
    'ranking de subida','ranking de queda','ranking de alta',
    'mais se deteriorou','mais se deterioraram',
    'maior deterioracao','maior subida','maior crescimento','maior reducao'
  ].some(w=>norm.includes(w));
  const _hasCampo = _detectCampo(norm)!==null;
  if(_hasDeltaKW&&_hasCampo) return {intent:'query_param',confidence:10};
  // Detecta multi-filtro por presença de ≥2 critérios combinados
  const _hasFiltroNum = /acima de|abaixo de|maior que|menor que|acima|abaixo|\d+[,.]?\d*x|\d+[,.]?\d*%/.test(norm);
  const _hasStatus = ['aprovad','watch','em analise','reprovad','monitoramento','sob monitoramento','em acompanhamento','restricao','restricted','descoberto','sem cobertura'].some(w=>norm.includes(w));
  const _hasDuration = ['duration','prazo medio','maturidade','life','dv01'].some(w=>norm.includes(w));
  const _hasSpread = ['spread','yield','taxa de spread','taxa do spread','taxa cdix','taxa ipca','taxa selic','spreads'].some(w=>norm.includes(w));
  const _hasRating = ['rating aaa','rating aa','rating a','rating bbb','rating bb','rating b','rating','grau de investimento','high yield','junk','investment grade','grau especulativo','nota de credito'].some(w=>norm.includes(w));
  const _hasSetor = [...new Set(ATIVOS.map(a=>a.setor).filter(Boolean))].some(s=>norm.includes(_norm(s)));
  const _critCount = [_hasFiltroNum,_hasStatus,_hasDuration,_hasSpread,_hasRating].filter(Boolean).length;
  if(_critCount>=2||(_hasSetor&&(_hasStatus||_hasDuration||_hasSpread||_hasRating||_hasFiltroNum))) {
    return {intent:'multi_filtro',confidence:10};
  }
  const scores={};
  for (const [intent,kws] of Object.entries(_INTENT_KW)) {
    scores[intent]=(scores[intent]||0);
    for (const kw of kws) { if(norm.includes(_norm(kw))) scores[intent]+=kw.includes(' ')?2:1; }
  }
  for (const [intent,exs] of Object.entries(_EXEMPLOS)) {
    for (const ex of exs) { const sim=_simRatio(norm,_norm(ex)); if(sim>0.4) scores[intent]=(scores[intent]||0)+sim*2; }
  }
  const best=Object.entries(scores).sort((a,b)=>b[1]-a[1])[0];
  if(!best||best[1]<1) return {intent:'fallback',confidence:0};
  return {intent:best[0],confidence:best[1]};
}

const _FALLBACKS=[
  'Posso ajudar com:\\n- **Análise completa** de emissor (ex: "análise completa da Klabin")\\n- **Evolução temporal** (ex: "como evoluiu o EBITDA da Suzano?")\\n- **Comparar vs setor** (ex: "Klabin vs média do setor de papel")\\n- **Mapa de vencimentos** (ex: "perfil de vencimentos da carteira")\\n- **Gráfico de spread** · **Gráfico por setor** · **Estresse**\\n- Exposição por **emissor**, **setor**, **rating** · **Top posições** · **Duration**\\n- Parâmetros: "DL/EBITDA > 3.5x no setor elétrico", "spread que mais abriu em 1 ano"\\n\\nComo quer começar?',
  'Não reconheci o contexto. Tenta: "posição em Equatorial", "gráfico spread de Klabin", "estresse da carteira" ou "mapa de risco".',
  'Hmm, não encontrei esse ponto. Tenta um emissor, setor, "estresse", "gráfico spread de X" ou "overview da carteira".'
];

const _SAUDACOES_IN=['oi','ola','opa','oi dourado','ola dourado','opa dourado','bom dia','boa tarde','boa noite','bom dia dourado','e ai','e ai dourado','tudo bem','tudo bom','tudo certo','hey','hi','hello','salve','fala dourado','fala','prazer','como vai','como voce esta','como vc ta'];
const _SAUDACOES_OUT=[
  'Prazer! Dourado aqui. Tenho acesso completo à carteira — emissores, spreads, ratings e posições. Diz o que precisa.',
  'E aí! Dourado à disposição. Pode mandar — emissor, setor, spread ou overview da carteira.',
  'Tudo certo! Dourado aqui. O que você quer analisar hoje?',
  'Oi! Dourado pronto. Diz o nome de um emissor, setor ou o que quiser checar.',
  'Salve! Dourado no ar. Fala o que precisa — posição, spread, rating, overview... é só pedir.',
  'Bom dia! Dourado aqui. Carteira carregada e pronta. O que vamos analisar?',
  'Boa tarde! Dourado à disposição. Emissor, setor, spread — manda ver.',
  'Boa noite! Dourado aqui. Pode perguntar — tenho todos os dados da carteira.'
];
const _AGRADECIMENTOS_IN=['obrigado','obrigada','valeu','vlw','thanks','thank you','brigadao','muito obrigado','muito obrigada','show','perfeito','otimo','excelente','legal','top','massa','bacana','ok','okay'];
const _AGRADECIMENTOS_OUT=['Disponha! Se precisar de mais alguma análise, é só chamar.','Por nada. Qualquer dúvida sobre a carteira, estou aqui.','Figurinha! Precisa de mais alguma coisa?','Fico feliz que ajudou. Qualquer análise, é só pedir.','Tmj. Se quiser detalhar mais algum ponto, estou aqui.'];
const _DESPEDIDAS_IN=['tchau','ate logo','ate mais','flw','falou','xau','bye','goodbye','encerra','pode fechar','foi isso','era isso'];
const _DESPEDIDAS_OUT=['Até mais! Qualquer análise, é só abrir o chat.','Falou! Estou aqui quando precisar.','Até logo! Carteira monitorada.','Foi! Qualquer dúvida, só chamar o Dourado.','Até! Bons negócios.'];
const _IDENTIDADE_IN=['quem e voce','quem es tu','voce e um bot','voce e uma ia','o que voce faz','para que serve','o que e o dourado','como voce funciona','voce e humano','voce e robo','qual e sua funcao','me fala de voce'];
const _IDENTIDADE_OUT=[
  'Sou o **Dourado**, assistente de análise de crédito da Douro Capital. Tenho acesso direto à carteira — posso consultar exposições por emissor, setor ou rating, checar spreads, duration, status de cobertura e comparar ativos. Sem API externa, sem delay — os dados são os da carteira mesmo.',
  'Dourado aqui — analista de crédito embutido no sistema da Douro Capital. Consulto posições, spreads, ratings e faço comparativos de emissores em tempo real. Pode perguntar como se fosse a um colega que conhece toda a carteira.',
  'Sou o **Dourado**, motor de análise de crédito local. Opero diretamente sobre os dados da carteira — sem conexão externa, sem alucinação. O que eu te digo é o que está na base. Fala o que quer saber.'
];

let _ctx={lastIntent:null,lastEntities:{},pendingParam:null,lastList:null};

function _resolveRef(norm) {
  const REFS_PRONOMES=['isso','esse','esses','ela','ele','eles','elas','desse','dele','deles','nesse'];
  const REFS_DETALHE =['spread','taxa','duration','quanto rende','yield','retorno','spread dele','spread dela'];
  const REFS_FOLLOWUP=['e quanto','e o','e a','mais detalhes','me conta mais','aprofunda','detalha'];
  const ent=_ctx.lastEntities||{};
  const temP=REFS_PRONOMES.some(r=>norm.includes(_norm(r)));
  const temD=REFS_DETALHE.some(r=>norm.includes(_norm(r)));
  const temF=REFS_FOLLOWUP.some(r=>norm.includes(_norm(r)));
  if(!temP&&!temD&&!temF) return norm;
  if(Object.keys(ent).length===0) return norm;
  let aug=norm;
  if(temD&&ent.emissor&&!_extractEmissor(norm)) aug+=' '+_norm(ent.emissor);
  if(temP||temF) {
    if(ent.setor)    aug+=' '+_norm(ent.setor);
    if(ent.emissor)  aug+=' '+_norm(ent.emissor);
    if(ent.carteira) aug+=' '+_norm(ent.carteira);
  }
  return aug;
}

// ═══════════════════════════════════════════════════════════════════════════════
// MOTOR PARAMÉTRICO — extrai indicador + operador + valor + período das queries
// Suporta: "DivLíq/EBITDA > 3.5x no setor elétrico", "spread que mais abriu em 2 anos"
// ═══════════════════════════════════════════════════════════════════════════════

const _FIN_CAMPOS = {
  'divida liquida ebitda':  {campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'},
  'divliquida ebitda':      {campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'},
  'dl ebitda':              {campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'},
  'dl/ebitda':              {campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'},
  'alavancagem':            {campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'},
  'leverage':               {campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'},
  'liquidez corrente':      {campo:'Liquidez Corrente',   label:'Liquidez Corrente', fmt:'x',   tipo:'fund', limiar:1.0, limiarDir:'<'},
  'liquidez':               {campo:'Liquidez Corrente',   label:'Liquidez Corrente', fmt:'x',   tipo:'fund', limiar:1.0, limiarDir:'<'},
  'roe':                    {campo:'ROE',                  label:'ROE',               fmt:'%',   tipo:'fund', limiar:null},
  'roa':                    {campo:'ROA',                  label:'ROA',               fmt:'%',   tipo:'fund', limiar:null},
  'roic':                   {campo:'ROIC',                 label:'ROIC',              fmt:'%',   tipo:'fund', limiar:null},
  'margem ebitda':          {campo:'Mg EBITDA 36M',        label:'Mg EBITDA',         fmt:'%',   tipo:'fund', limiar:null},
  'mg ebitda':              {campo:'Mg EBITDA 36M',        label:'Mg EBITDA',         fmt:'%',   tipo:'fund', limiar:null},
  'margem liquida':         {campo:'Mg Liquida TTM',       label:'Mg Líquida',        fmt:'%',   tipo:'fund', limiar:null},
  'margem bruta':           {campo:'Mg Bruta 36M',         label:'Mg Bruta',          fmt:'%',   tipo:'fund', limiar:null},
  'fcf':                    {campo:'FCF_TTM',              label:'FCF TTM',           fmt:'mi',  tipo:'fund', limiar:null},
  'fluxo de caixa livre':   {campo:'FCF_TTM',              label:'FCF TTM',           fmt:'mi',  tipo:'fund', limiar:null},
  'fluxo de caixa':         {campo:'FCF_TTM',              label:'FCF TTM',           fmt:'mi',  tipo:'fund', limiar:null},
  'receita':                {campo:'Receita_TTM',          label:'Receita TTM',       fmt:'mi',  tipo:'fund', limiar:null},
  'ebitda':                 {campo:'EBITDA_TTM',           label:'EBITDA TTM',        fmt:'mi',  tipo:'fund', limiar:null},
  'divida liquida':         {campo:'Divida Liquida',       label:'Dív. Líquida',      fmt:'mi',  tipo:'fund', limiar:null},
  'divida bruta':           {campo:'Divida Bruta',         label:'Dív. Bruta',        fmt:'mi',  tipo:'fund', limiar:null},
  'divida':                 {campo:'Divida Liquida',       label:'Dív. Líquida',      fmt:'mi',  tipo:'fund', limiar:null},
  'lucro':                  {campo:'Lucro Liquido_TTM',    label:'Lucro Líq. TTM',    fmt:'mi',  tipo:'fund', limiar:null},
  'lucro liquido':          {campo:'Lucro Liquido_TTM',    label:'Lucro Líq. TTM',    fmt:'mi',  tipo:'fund', limiar:null},
  'despesa financeira':     {campo:'Despesa Financeira_TTM',label:'Desp. Fin. TTM',   fmt:'mi',  tipo:'fund', limiar:null},
  'spread delta':                {campo:'spread',               label:'Δ Spread',              fmt:'bps', tipo:'spread_delta',  limiar:null},
  'spread historico':            {campo:'spread',               label:'Spread Histórico',      fmt:'bps', tipo:'spread_hist',   limiar:null},
  'maior alta do spread':        {campo:'spread',               label:'Maior Alta do Spread',  fmt:'bps', tipo:'spread_delta',  limiar:null},
  'maior alta de spread':        {campo:'spread',               label:'Maior Alta do Spread',  fmt:'bps', tipo:'spread_delta',  limiar:null},
  'spread subiu mais':           {campo:'spread',               label:'Maior Alta do Spread',  fmt:'bps', tipo:'spread_delta',  limiar:null},
  'spread abriu mais':           {campo:'spread',               label:'Maior Abertura Spread', fmt:'bps', tipo:'spread_delta',  limiar:null},
  'maior abertura de spread':    {campo:'spread',               label:'Maior Abertura Spread', fmt:'bps', tipo:'spread_delta',  limiar:null},
  'maior abertura do spread':    {campo:'spread',               label:'Maior Abertura Spread', fmt:'bps', tipo:'spread_delta',  limiar:null},
  'abertura de spread':          {campo:'spread',               label:'Abertura de Spread',    fmt:'bps', tipo:'spread_delta',  limiar:null},
  'queda do spread':             {campo:'spread',               label:'Maior Queda do Spread', fmt:'bps', tipo:'spread_delta',  limiar:null},
  'spread fechou mais':          {campo:'spread',               label:'Maior Fechamento Spread',fmt:'bps',tipo:'spread_delta',  limiar:null},
  'maior alta da divida':        {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'maior alta do dl ebitda':     {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'maior alta dl ebitda':        {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'maior alta da alavancagem':   {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'maior alta de alavancagem':   {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'alavancagem subiu mais':      {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'alavancagem aumentou mais':   {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'piora de alavancagem':        {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'deterioracao da alavancagem': {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'delta dl ebitda':             {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'variacao da alavancagem':     {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'variacao do dl ebitda':       {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'queda da alavancagem':        {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'desalavancagem':              {campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null},
  'maior alta do ebitda':        {campo:'EBITDA_TTM',           label:'Δ EBITDA',              fmt:'mi',  tipo:'fund_delta',    limiar:null},
  'maior queda do ebitda':       {campo:'EBITDA_TTM',           label:'Δ EBITDA',              fmt:'mi',  tipo:'fund_delta',    limiar:null},
  'variacao do ebitda':          {campo:'EBITDA_TTM',           label:'Δ EBITDA',              fmt:'mi',  tipo:'fund_delta',    limiar:null},
  'maior alta da receita':       {campo:'Receita_TTM',          label:'Δ Receita',             fmt:'mi',  tipo:'fund_delta',    limiar:null},
  'variacao da receita':         {campo:'Receita_TTM',          label:'Δ Receita',             fmt:'mi',  tipo:'fund_delta',    limiar:null},
};

function _detectCampo(norm) {
  const keys=Object.keys(_FIN_CAMPOS).sort((a,b)=>b.length-a.length);
  for(const k of keys){if(norm.includes(_norm(k))) return _FIN_CAMPOS[k];}
  return null;
}

function _extractOpVal(norm) {
  const opMap=[
    {pats:['maior que','maior do que','acima de','superior a','mais que','acima dos','maior ou igual'],op:'>'},
    {pats:['menor que','menor do que','abaixo de','inferior a','menos que','abaixo dos','menor ou igual'],op:'<'},
    {pats:['igual a','exatamente'],op:'='},
    {pats:['entre'],op:'between'},
  ];
  let op=null;
  for(const {pats,op:o} of opMap){if(pats.some(p=>norm.includes(_norm(p)))){op=o;break;}}
  const nums=[...norm.matchAll(/[-+]?\\d+[,.]?\\d*/g)].map(m=>parseFloat(m[0].replace(',','.')));
  if(op==='between'&&nums.length>=2) return {op,v1:Math.min(nums[0],nums[1]),v2:Math.max(nums[0],nums[1])};
  const v1=nums.length?nums[0]:null;
  if(!op&&v1!==null) op='>';
  return {op,v1};
}

function _extractMeses(norm) {
  const anoM=norm.match(/(?:ultimos|ultimo|last)\\s+(\\d+)\\s+anos?/);
  if(anoM) return parseInt(anoM[1])*12;
  const mesM=norm.match(/(?:ultimos|ultimo|last)\\s+(\\d+)\\s+meses?/);
  if(mesM) return parseInt(mesM[1]);
  if(/ultimo ano|ultimos 12 meses/.test(norm)) return 12;
  if(/ultimo trimestre|ultimos 3 meses|no trimestre|neste trimestre|no ultimo trimestre/.test(norm)) return 3;
  if(/ultimo semestre|ultimos 6 meses|no semestre|neste semestre|no ultimo semestre|em 6 meses/.test(norm)) return 6;
  if(/ultimos 24 meses/.test(norm)) return 24;
  if(/ultimos 2 anos/.test(norm)) return 24;
  if(/ultimos 3 anos/.test(norm)) return 36;
  if(/ultimos 5 anos/.test(norm)) return 60;
  return null;
}

const _finCache={};
function _matchToFin(emissor) {
  if(_finCache[emissor]!==undefined) return _finCache[emissor];
  const ne=_norm(emissor);
  const keys=Object.keys(FIN_SERIES);
  for(const k of keys){if(_norm(k)===ne){_finCache[emissor]=k;return k;}}
  for(const k of keys){const kn=_norm(k);if(kn.includes(ne)||ne.includes(kn)){_finCache[emissor]=k;return k;}}
  const emToks=ne.split(' ').filter(w=>w.length>3);
  let best=null,bestS=0;
  for(const k of keys){
    const kToks=_norm(k).split(' ').filter(w=>w.length>3);
    const hits=emToks.filter(t=>kToks.some(kt=>kt===t||(kt.length>4&&(kt.includes(t)||t.includes(kt))))).length;
    const score=hits/Math.max(emToks.length,1);
    if(score>bestS&&score>=0.45){bestS=score;best=k;}
  }
  _finCache[emissor]=best;
  return best;
}

function _lastVal(arr) {
  if(!arr) return null;
  for(let i=arr.length-1;i>=0;i--){if(arr[i]!=null&&!isNaN(arr[i]))return parseFloat(arr[i]);}
  return null;
}

function _fmtV(v,fmt) {
  if(v==null) return 'N/D';
  if(fmt==='x') return v.toFixed(2)+'x';
  if(fmt==='%') return (v*100).toFixed(1)+'%';
  if(fmt==='mi') return 'R$ '+(v/1e6).toFixed(0)+' Mi';
  if(fmt==='bps') return v.toFixed(1)+'bps';
  if(fmt==='a') return v.toFixed(1)+'a';
  return v.toFixed(2);
}

// Pre-check rápido: é uma query paramétrica?
function _isParamQuery(norm) {
  const temCampo=_detectCampo(norm)!==null;
  if(!temCampo) return false;
  const {op,v1}=_extractOpVal(norm);
  const temMeses=_extractMeses(norm)!==null;
  const temSort=['mais abriram','mais fecharam','maiores','menores','mais alto','mais baixo','mais alavancados','mais alavancado','piores','melhores','que mais','ranking','top \\d','quais tem','quais estao com','emissores com','ativos com','empresas com','maior alta','maior queda','maior abertura','maior fechamento','mais subiram','mais caiu','mais aumentou','mais deteriorou','variacao de','variacao do','variacao da','piora de','desalavancagem','delta'].some(w=>new RegExp(w).test(norm));
  const temOpVal=op!==null&&v1!==null;
  return temOpVal||temMeses||temSort;
}

// Detecta query de evolução temporal (tem campo + palavra de série temporal)
function _isEvolutionQuery(norm) {
  const evoKWs=['evoluiu','evolucao do','evolucao da','tendencia de','historico de','serie temporal','ao longo do tempo','ao longo dos anos','como foi o','como foi a','como evoluiu','trajetoria de','progressao de'];
  return evoKWs.some(k=>norm.includes(_norm(k)))&&_detectCampo(norm)!==null;
}

// Resolve referência posicional a item de lista anterior ("o 2", "o segundo", etc.)
function _resolveListDrilldown(norm) {
  if(!_ctx.lastList||!_ctx.lastList.length) return null;
  // Desambigua: só ativa se a query for curta/referencial (sem campos, sem setores longos)
  if(norm.length>80) return null;
  const NUMWORDS={'primeiro':1,'segunda':2,'segundo':2,'terceiro':3,'terceira':3,'quarto':4,'quarta':4,'quinto':5,'quinta':5,'sexto':6,'setimo':7,'oitavo':8,'nono':9};
  for(const [w,i] of Object.entries(NUMWORDS)) {
    if(norm.includes(w)&&i<=_ctx.lastList.length) return _ctx.lastList[i-1];
  }
  const m=norm.match(/(?:^|o |a |no |na |do |da |item |numero )([1-9][0-9]?)(?:\s|$)/);
  if(m) {
    const idx=parseInt(m[1])-1;
    if(idx>=0&&idx<_ctx.lastList.length) return _ctx.lastList[idx];
  }
  return null;
}

// ═══════════════════════════════════════════════════════════════════════════════

function _queryAtivos(intent,ent,userTxt) {
  const cartStr   =ent.carteira||'Todas as Carteiras';
  const ativosCart=ent.carteira?ATIVOS.filter(a=>(a.carteira||'').toUpperCase().includes(ent.carteira.toUpperCase())):ATIVOS;
  const totalCart =ativosCart.reduce((s,a)=>s+(a.saldo||0),0);

  // ── QUERY PARAMÉTRICA ─────────────────────────────────────────────────────
  if (intent==='query_param') {
    const norm=_norm(userTxt||'');
    const ci=_detectCampo(norm);
    if(!ci) return 'Qual indicador filtrar? (ex: Dív.Líq./EBITDA, liquidez corrente, ROE, spread, margem EBITDA)';
    const {op,v1,v2}=_extractOpVal(norm);
    const meses=_extractMeses(norm);
    const sortDesc=['mais abriram','mais fecharam','maiores','mais alto','piores','acima','ranking','top','que mais','mais alavancados','mais alavancado','maior alta','maior subida','maior escalada','maior salto','maior disparo','maior explosao','mais subiram','mais aumentaram','mais se deterioraram','maior deterioracao','maior widening','maior abertura','maior crescimento','maior expansao','maior piora'].some(w=>norm.includes(w.replace(' ','_').replace(' ','_'))||norm.includes(w));
    const topN=12;

    // ── SPREAD: variação no período ───────────────────────────────────────
    if(ci.tipo==='spread'||ci.tipo==='spread_delta'||ci.tipo==='spread_hist') {
      let base=ativosCart.filter(a=>(a.saldo||0)>0);
      if(ent.setor) base=base.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase()));
      if(!base.length) return 'Não encontrei ativos'+(ent.setor?' no setor **'+ent.setor+'**':'')+' na carteira **'+cartStr+'**.';
      const periMs=meses||12;
      const hoje=new Date();
      const corte=new Date(hoje.getTime()-periMs*30*86400000);
      const periStr=periMs>=12?(periMs/12)+'ano(s)':periMs+'m';
      const itens=[];
      const vistos=new Set();
      for(const ativo of base) {
        const em=ativo.emissor||ativo.ticker;
        if(vistos.has(em)) continue; vistos.add(em);
        const ts=SPREADS_TS[ativo.ticker];
        if(!ts||!ts.spread||!ts.datas) continue;
        const pairs=ts.datas.map((d,i)=>{return{d:new Date(d),v:ts.spread[i]};} ).filter(p=>p.v!=null);
        if(pairs.length<2) continue;
        const cur=pairs[pairs.length-1].v;
        let past=null;
        for(let i=pairs.length-2;i>=0;i--){if(pairs[i].d<=corte){past=pairs[i].v;break;}}
        if(past==null) past=pairs[0].v;
        const delta=(cur-past)*100;
        if(op&&v1!==null){if(op==='>'&&delta<=v1)continue;if(op==='<'&&delta>=v1)continue;}
        const saldo=base.filter(a=>(a.emissor||a.ticker)===em).reduce((s,a)=>s+(a.saldo||0),0);
        itens.push({em,setor:ativo.setor||'N/D',cur,past,delta,saldo,ticker:ativo.ticker});
      }
      if(!itens.length) return 'Sem dados de spread suficientes'+(ent.setor?' em **'+ent.setor+'**':'')+' para o período.';
      itens.sort((a,b)=>sortDesc?b.delta-a.delta:a.delta-b.delta);
      const top=itens.slice(0,topN);
      const secStr=ent.setor?' · **'+ent.setor+'**':'';
      const threshStr=op&&v1!==null?' (filtro: Δ'+op+v1+'bps)':'';
      const labels=top.map(i=>i.em);
      const data=top.map(i=>parseFloat(i.delta.toFixed(1)));
      const colors=data.map(v=>v>0?'rgba(224,82,82,.75)':'rgba(74,191,203,.75)');
      const linhas=top.map((x,i)=>(i+1)+'. **'+x.em+'** ('+x.setor+'): '+(x.delta>=0?'+':'')+x.delta.toFixed(1)+'bps | atual: '+(x.cur*100).toFixed(0)+'bps → antes: '+(x.past*100).toFixed(0)+'bps').join('\\n');
      const _co={color:'#718096',font:{size:8}};
      _ctx.lastList=top.map(x=>({em:x.em}));
      return {
        text:(sortDesc?'**Spreads que mais abriram**':'**Spreads que mais fecharam**')+' — '+periStr+secStr+threshStr+' · **'+cartStr+'**\\n\\n'+linhas+'\\n\\n*(Diga "análise completa do 1" para detalhar qualquer emissor.)*',
        chartTitulo:'Δ SPREAD '+periStr.toUpperCase()+(ent.setor?' · '+ent.setor.toUpperCase():''),
        chart:{type:'bar',data:{labels,datasets:[{data,backgroundColor:colors,borderRadius:4,borderSkipped:false}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>' '+(ctx.raw>0?'+':'')+ctx.raw+'bps'}}},scales:{x:{ticks:{..._co,callback:v=>v+'bps'},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{..._co},grid:{display:false}}}}}
      };
    }

    // ── DELTA DE FUNDAMENTAIS (variação entre períodos) ──────────────────
    if(ci.tipo==='fund_delta') {
      const periMs=meses||3;
      const periStr=periMs===3?'último trimestre':periMs===6?'último semestre':periMs===12?'último ano':periMs+'m';
      const hoje=new Date();
      const corte=new Date(hoje.getTime()-periMs*30.44*86400000);
      let base=ativosCart.filter(a=>(a.saldo||0)>0);
      if(ent.setor) base=base.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase()));
      const emList=[...new Set(base.map(a=>a.emissor).filter(Boolean))];
      const itens=[];
      for(const em of emList) {
        const fk=_matchToFin(em); if(!fk) continue;
        const fd=FIN_SERIES[fk];   if(!fd) continue;
        const serie=fd[ci.campo];  if(!Array.isArray(serie)||serie.length<2) continue;
        const datas=fd['datas']||fd['Data']||fd['data']||null;
        if(!datas||!Array.isArray(datas)) continue;
        // Pega valor atual (último) e valor no corte
        let valCur=null,valPast=null;
        for(let i=datas.length-1;i>=0;i--) {
          const d=new Date(datas[i]);
          if(valCur==null&&serie[i]!=null){valCur=serie[i];}
          if(d<=corte&&serie[i]!=null){valPast=serie[i];break;}
        }
        if(valCur==null||valPast==null) continue;
        const delta=valCur-valPast;
        const saldo=base.filter(a=>a.emissor===em).reduce((s,a)=>s+(a.saldo||0),0);
        const rating=base.find(a=>a.emissor===em)?.['Rating Douro']||'N/D';
        const setor=base.find(a=>a.emissor===em)?.setor||'N/D';
        itens.push({em,valCur,valPast,delta,saldo,rating,setor});
      }
      if(!itens.length) return 'Sem dados de **'+ci.label+'** com histórico suficiente para calcular variação no '+periStr+(ent.setor?' em **'+ent.setor+'**':'')+'.';
      // Detecta direção: maior alta vs maior queda
      const normQ=_norm(userTxt||'');
      const querQueda=['queda','caiu','cairam','reduziu','reduziram','desalavancou','desalavancaram','desalavancagem','fechou','fecharam','comprimiu','comprimiram','melhorou','melhoraram','menor','mais baixo','caindo','recuou','recuaram','diminuiu','diminuiram','contraiu','contrairam','encolheu','encolheram','declinou','declinaram','tightening','compressao','melhora','reducao','quem mais reduziu','quem mais caiu','quem mais melhorou','que mais caiu','que mais reduziu','que mais melhorou'].some(w=>normQ.includes(w));
      itens.sort((a,b)=>querQueda?a.delta-b.delta:b.delta-a.delta);
      const top=itens.slice(0,12);
      const secStr=ent.setor?' · **'+ent.setor+'**':'';
      const titulo=(querQueda?'**Maior queda**':'**Maior alta**')+' de **'+ci.label+'** — '+periStr+secStr+' — **'+cartStr+'**';
      const linhas=top.map((x,i)=>{
        const sinal=x.delta>=0?'+':'';
        const cur=ci.fmt==='x'?x.valCur.toFixed(2)+'x':ci.fmt==='%'?(x.valCur*100).toFixed(1)+'%':ci.fmt==='mi'?'R$'+(x.valCur/1e6).toFixed(0)+'M':x.valCur.toFixed(2);
        const d=ci.fmt==='x'?sinal+x.delta.toFixed(2)+'x':ci.fmt==='%'?sinal+(x.delta*100).toFixed(1)+'pp':ci.fmt==='mi'?sinal+(x.delta/1e6).toFixed(0)+'M':sinal+x.delta.toFixed(2);
        const warn=ci.limiar!=null&&x.valCur>ci.limiar?' ⚠':'';
        return (i+1)+'. **'+x.em+'** ('+x.setor+' · '+x.rating+'): atual '+cur+warn+' | Δ: **'+d+'** — R$ '+(x.saldo/1e6).toFixed(2)+' Mi';
      }).join('\\n');
      const labels=top.map(x=>x.em);
      const data=top.map(x=>{
        if(ci.fmt==='%') return parseFloat((x.delta*100).toFixed(2));
        if(ci.fmt==='mi') return parseFloat((x.delta/1e6).toFixed(1));
        return parseFloat(x.delta.toFixed(3));
      });
      const colors=data.map(v=>{
        if(querQueda) return v<0?'rgba(74,191,203,.75)':'rgba(224,82,82,.75)';
        return v>0?'rgba(224,82,82,.75)':'rgba(74,191,203,.75)';
      });
      const _co={color:'#718096',font:{size:8}};
      _ctx.lastList=top.map(x=>({em:x.em}));
      return {
        text:titulo+'\\n\\n'+linhas+(itens.length>12?'\\n\\n*('+itens.length+' emissores com dados, top 12)*':'')+'\\n\\n*(Diga "análise completa do 1" para detalhar qualquer emissor.)*',
        chartTitulo:'Δ '+ci.label.toUpperCase()+' · '+periStr.toUpperCase()+(ent.setor?' · '+ent.setor.toUpperCase():''),
        chart:{type:'bar',data:{labels,datasets:[{data,backgroundColor:colors,borderRadius:4,borderSkipped:false}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>{const v=ctx.raw;return ' Δ: '+(v>=0?'+':'')+v+(ci.fmt==='x'?'x':ci.fmt==='%'?'pp':ci.fmt==='mi'?'M':'');}}}},scales:{x:{ticks:{..._co},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{..._co,font:{size:9}},grid:{display:false}}}}}
      };
    }

    // ── INDICADOR FUNDAMENTALISTA (FIN_SERIES) ────────────────────────────
    if(ci.tipo==='fund') {
      let base=ativosCart.filter(a=>(a.saldo||0)>0);
      if(ent.setor) base=base.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase()));
      const emList=[...new Set(base.map(a=>a.emissor).filter(Boolean))];
      const itens=[];
      for(const em of emList) {
        const fk=_matchToFin(em); if(!fk) continue;
        const fd=FIN_SERIES[fk];   if(!fd) continue;
        const val=_lastVal(fd[ci.campo]); if(val==null) continue;
        if(op&&v1!==null) {
          if(op==='>'&&val<=v1) continue;
          if(op==='<'&&val>=v1) continue;
          if(op==='='&&Math.abs(val-v1)>0.05) continue;
          if(op==='between'&&v2!=null&&(val<v1||val>v2)) continue;
        }
        const saldo=base.filter(a=>a.emissor===em).reduce((s,a)=>s+(a.saldo||0),0);
        const rating=base.find(a=>a.emissor===em)?.[' Rating Douro']||base.find(a=>a.emissor===em)?.['Rating Douro']||'N/D';
        const setor=base.find(a=>a.emissor===em)?.setor||fd.setor||'N/D';
        itens.push({em,val,saldo,rating,setor});
      }
      if(!itens.length) {
        const tStr=op&&v1!==null?' com **'+ci.label+'** '+op+' '+_fmtV(v1,ci.fmt):'';
        return 'Nenhum emissor'+(ent.setor?' em **'+ent.setor+'**':'')+tStr+' encontrado com dados fundamentais no sistema. Verifique se a empresa tem demonstrações na CVM.';
      }
      itens.sort((a,b)=>sortDesc?b.val-a.val:a.val-b.val);
      const top=itens.slice(0,topN);
      const threshStr=op&&v1!==null?' (filtro: '+op+' '+_fmtV(v1,ci.fmt)+')':'';
      const secStr=ent.setor?' · Setor **'+ent.setor+'**':'';
      const linhas=top.map((x,i)=>{
        const warn=ci.limiar!=null&&((ci.limiarDir==='>'&&x.val>ci.limiar)||(ci.limiarDir==='<'&&x.val<ci.limiar))?' ⚠':'';
        return (i+1)+'. **'+x.em+'** ('+x.setor+' · '+x.rating+'): **'+_fmtV(x.val,ci.fmt)+'**'+warn+' — R$ '+(x.saldo/1e6).toFixed(2)+' Mi';
      }).join('\\n');
      const labels=top.map(x=>x.em);
      const data=top.map(x=>{
        if(ci.fmt==='%') return parseFloat((x.val*100).toFixed(1));
        if(ci.fmt==='mi') return parseFloat((x.val/1e6).toFixed(1));
        return parseFloat(x.val.toFixed(2));
      });
      const colors=data.map(v=>{
        if(!ci.limiar) return '#4abfcb';
        const over=(ci.limiarDir==='>'&&v>ci.limiar)||(ci.limiarDir==='<'&&v<ci.limiar);
        return over?'rgba(224,82,82,.75)':'rgba(74,191,203,.75)';
      });
      const datasets=[{data,backgroundColor:colors,borderRadius:4,borderSkipped:false}];
      if(ci.limiar!=null){
        const limVal=ci.fmt==='%'?ci.limiar*100:ci.fmt==='mi'?ci.limiar/1e6:ci.limiar;
        datasets.push({type:'line',label:'Limiar ('+_fmtV(ci.limiar,ci.fmt)+')',data:Array(data.length).fill(limVal),borderColor:'#e0b43c',borderDash:[5,3],borderWidth:1.5,pointRadius:0,fill:false});
      }
      const _co={color:'#718096',font:{size:8}};
      const axCb=ci.fmt==='%'?'v=>v+\"%\"':ci.fmt==='x'?'v=>v+\"x\"':ci.fmt==='mi'?'v=>\"R$\"+v+\"M\"':'undefined';
      _ctx.lastList=top.map(x=>({em:x.em}));
      return {
        text:'**'+ci.label+'**'+threshStr+secStr+' — **'+cartStr+'**\\n\\n'+linhas+(itens.length>topN?'\\n\\n*('+itens.length+' emissores encontrados, top '+topN+')*':'')+(itens.filter(x=>ci.limiar!=null&&((ci.limiarDir==='>'&&x.val>ci.limiar)||(ci.limiarDir==='<'&&x.val<ci.limiar))).length?'\\n\\n⚠ **'+itens.filter(x=>ci.limiar!=null&&((ci.limiarDir==='>'&&x.val>ci.limiar)||(ci.limiarDir==='<'&&x.val<ci.limiar))).length+' emissor(es)** no limiar de alerta de covenant.':''),
        chartTitulo:ci.label.toUpperCase()+(ent.setor?' · '+ent.setor.toUpperCase():''),
        chart:{type:'bar',data:{labels,datasets},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:datasets.length>1,position:'bottom',labels:{color:'#8a9ab0',font:{size:9},boxWidth:8,padding:6}},tooltip:{callbacks:{label:ctx=>' '+ctx.raw+(ci.fmt==='x'?'x':ci.fmt==='%'?'%':'')}}},scales:{x:{ticks:{..._co},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{..._co,font:{size:9}},grid:{display:false}}}}}
      };
    }

    return 'Não consegui processar esse indicador. Tente: "Dív.Líq./EBITDA maior que 3.5x", "spread que mais abriu no último ano", "ROE acima de 15%".';
  }

  // ── MULTI-FILTRO ─────────────────────────────────────────────────────────
  if (intent==='multi_filtro') {
    const norm=_norm(userTxt||'');
    // Extrai filtros
    const statusFiltro=(['aprovad','watch','em analise','reprovad','monitoramento'].find(w=>norm.includes(w))||null);
    const statusMap={aprovad:'Aprovado',watch:'Watch','em analise':'Em análise',reprovad:'Reprovado',monitoramento:'Monitoramento'};
    const statusVal=statusFiltro?statusMap[statusFiltro]:null;
    const setorFiltro=ent.setor||null;
    const ratingFiltro=ent.rating||null;
    // Duration
    let durOp=null,durVal=null;
    const durM=norm.match(/duration\s*(?:acima\s*de|maior\s*que|>)\s*(\d+[,.]?\d*)/);
    const durM2=norm.match(/duration\s*(?:abaixo\s*de|menor\s*que|<)\s*(\d+[,.]?\d*)/);
    if(durM){durOp='>';durVal=parseFloat(durM[1].replace(',','.'));}
    else if(durM2){durOp='<';durVal=parseFloat(durM2[1].replace(',','.'));}
    // Spread
    let spOp=null,spVal=null;
    const spM=norm.match(/spread\s*(?:acima\s*de|maior\s*que|>)\s*(\d+[,.]?\d*)/);
    const spM2=norm.match(/spread\s*(?:abaixo\s*de|menor\s*que|<)\s*(\d+[,.]?\d*)/);
    if(spM){spOp='>';spVal=parseFloat(spM[1].replace(',','.'));}
    else if(spM2){spOp='<';spVal=parseFloat(spM2[1].replace(',','.'));}
    // Acima/abaixo genérico (sem campo explícito)
    if(!durOp&&!spOp) {
      const genM=norm.match(/(?:acima\s*de|maior\s*que)\s*(\d+[,.]?\d*)/);
      const genM2=norm.match(/(?:abaixo\s*de|menor\s*que)\s*(\d+[,.]?\d*)/);
      if(genM){durOp='>';durVal=parseFloat(genM[1].replace(',','.'));}
      else if(genM2){durOp='<';durVal=parseFloat(genM2[1].replace(',','.'));}
    }
    // Aplica filtros
    let base=ativosCart.filter(a=>(a.saldo||0)>0);
    const filtrosApl=[];
    if(setorFiltro){base=base.filter(a=>(a.setor||'').toLowerCase().includes(setorFiltro.toLowerCase()));filtrosApl.push('setor: '+setorFiltro);}
    if(statusVal){base=base.filter(a=>(a.Status||'').toLowerCase()===statusVal.toLowerCase());filtrosApl.push('status: '+statusVal);}
    if(ratingFiltro){base=base.filter(a=>(a['Rating Douro']||'').toUpperCase()===ratingFiltro.toUpperCase());filtrosApl.push('rating: '+ratingFiltro);}
    if(durOp&&durVal!=null){
      base=base.filter(a=>{const d=Number(a.duration)||0;return durOp==='>'?d>durVal:d<durVal;});
      filtrosApl.push('duration '+durOp+' '+durVal+'a');
    }
    if(spOp&&spVal!=null){
      base=base.filter(a=>{const s=a.spread!=null?Number(a.spread):null;if(s==null||isNaN(s))return false;return spOp==='>'?s>spVal/100:s<spVal/100;});
      filtrosApl.push('spread '+spOp+' '+spVal+'%');
    }
    if(!filtrosApl.length) return 'Não identifiquei filtros na sua pergunta. Tente: "emissores aprovados com duration acima de 3", "spread abaixo de 1% e rating AA".';
    if(!base.length) return 'Nenhum ativo encontra todos os critérios: **'+filtrosApl.join(' + ')+'** em **'+cartStr+'**.';
    // Agrupa por emissor
    const emMap={};
    for(const a of base){
      const em=a.emissor||a.ticker;
      if(!emMap[em])emMap[em]={em,setor:a.setor||'N/D',status:a.Status||'N/D',rating:a['Rating Douro']||'N/D',saldo:0,durSum:0,durW:0,spread:null};
      emMap[em].saldo+=(a.saldo||0);
      emMap[em].durSum+=(a.duration||0)*(a.saldo||0);
      emMap[em].durW+=(a.saldo||0);
      if(a.spread!=null&&!isNaN(Number(a.spread)))emMap[em].spread=Number(a.spread);
    }
    const lista=Object.values(emMap).sort((a,b)=>b.saldo-a.saldo);
    const totalFilt=lista.reduce((s,x)=>s+x.saldo,0);
    const linhas=lista.slice(0,15).map((x,i)=>{
      const dur=x.durW>0?(x.durSum/x.durW).toFixed(1)+'a':'—';
      const sp=x.spread!=null?(x.spread*100).toFixed(2)+'%':'—';
      return (i+1)+'. **'+x.em+'** ('+x.setor+') — R$ '+(x.saldo/1e6).toFixed(2)+' Mi | Duration: '+dur+' | Spread: '+sp+' | '+x.status;
    }).join('\\n');
    const labels=lista.slice(0,12).map(x=>x.em);
    const data=lista.slice(0,12).map(x=>parseFloat((x.saldo/1e6).toFixed(2)));
    const colors=lista.slice(0,12).map(x=>x.status==='Aprovado'?'rgba(74,191,203,.75)':x.status==='Watch'?'rgba(240,180,50,.75)':'rgba(224,82,82,.75)');
    _ctx.lastList=lista.map(x=>({em:x.em}));
    const _co={color:'#718096',font:{size:8}};
    return {
      text:'**Multi-filtro:** '+filtrosApl.join(' · ')+' — **'+cartStr+'**\\n\\n'+lista.length+' emissor(es) · R$ '+(totalFilt/1e6).toFixed(2)+' Mi\\n\\n'+linhas+(lista.length>15?'\\n\\n*(mostrando top 15 de '+lista.length+')*':'')+'\\n\\n*(Diga "análise completa do 1" para detalhar qualquer emissor.)*',
      chartTitulo:'MULTI-FILTRO: '+filtrosApl.join(' | ').toUpperCase(),
      chart:{type:'bar',data:{labels,datasets:[{data,backgroundColor:colors,borderRadius:4,borderSkipped:false}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>' R$ '+ctx.raw+'M'}}},scales:{x:{ticks:{..._co,callback:v=>'R$'+v+'M'},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{..._co,font:{size:9}},grid:{display:false}}}}}
    };
  }

  if (intent==='exposicao_setor') {
    if(!ent.setor) return 'Qual setor você quer verificar?';
    const matched=ativosCart.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase()));
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    const pct=totalCart>0?((saldo/totalCart)*100).toFixed(1):'0';
    const topEm=[...new Set(matched.map(a=>a.emissor).filter(Boolean))].slice(0,5).join(', ');
    return 'A exposição da carteira **'+cartStr+'** no setor de **'+ent.setor.toUpperCase()+'** é de **R$ '+(saldo/1e6).toFixed(2)+' Mi** ('+pct+'% da carteira).\\n\\n'+(topEm?'Principais emissores: '+topEm+'.\\n\\n':'')+'Quer ver cada emissor detalhado?';
  }

  if (intent==='exposicao_rating') {
    if(!ent.rating) return 'Qual rating você quer verificar?';
    const matched=ativosCart.filter(a=>(a['Rating Douro']||'').toUpperCase()===ent.rating.toUpperCase());
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    const pct=totalCart>0?((saldo/totalCart)*100).toFixed(1):'0';
    return 'A carteira **'+cartStr+'** possui **R$ '+(saldo/1e6).toFixed(2)+' Mi** ('+pct+'%) em ativos com Rating Douro **'+ent.rating+'**.\\n\\nQuer ver o breakdown de quais ativos compõem esse rating?';
  }

  if (intent==='exposicao_emissor') {
    if(!ent.emissor) return 'Qual emissor você quer verificar?';
    const matched=ativosCart.filter(a=>(a.emissor||'').toLowerCase().includes(ent.emissor.toLowerCase())&&(a.saldo||0)>0);
    if(!matched.length) return 'Não encontrei posição em **'+ent.emissor+'** na carteira **'+cartStr+'**.';
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    const pct=totalCart>0?((saldo/totalCart)*100).toFixed(1):'0';
    const dur=saldo>0?(matched.reduce((s,a)=>s+(a.duration||0)*(a.saldo||0),0)/saldo).toFixed(1):'—';
    return 'A posição em **'+ent.emissor+'** na carteira **'+cartStr+'** é de **R$ '+(saldo/1e6).toFixed(2)+' Mi** ('+pct+'% da carteira), duration média de '+dur+'a.\\n\\nQuer ver o spread atual contra a NTN-B?';
  }

  if (intent==='overview_carteira') {
    const validos=ativosCart.filter(a=>a.saldo>0);
    const aprovados=validos.filter(a=>a.Status==='Aprovado').reduce((s,a)=>s+(a.saldo||0),0);
    const emWatch=validos.filter(a=>['Em análise','Watch','Monitoramento'].includes(a.Status)).length;
    const nSet=new Set(validos.map(a=>a.setor).filter(Boolean)).size;
    return 'Overview — **'+cartStr+'**:\\n- **Total Crédito:** R$ '+(totalCart/1e6).toFixed(2)+' Mi\\n- **Ativos com saldo:** '+validos.length+'\\n- **Setores:** '+nSet+'\\n- **% Aprovados:** '+(totalCart>0?(aprovados/totalCart*100).toFixed(1):'0')+'%\\n- **Em watch/análise:** '+emWatch+' ativo(s)\\n\\nQuer o top 5 posições ou breakdown por setor?';
  }

  if (intent==='top_exposicoes') {
    const agrp={};
    ativosCart.forEach(a=>{agrp[a.emissor||'N/D']=(agrp[a.emissor||'N/D']||0)+(a.saldo||0);});
    const top=Object.entries(agrp).sort((a,b)=>b[1]-a[1]).slice(0,5);
    _ctx.lastList=top.map(t=>({em:t[0]}));
    return 'Maiores posições — **'+cartStr+'**:\\n'+top.map((t,i)=>(i+1)+'. **'+t[0]+'**: R$ '+(t[1]/1e6).toFixed(2)+' Mi ('+(totalCart>0?((t[1]/totalCart)*100).toFixed(1):'0')+'%)').join('\\n')+'\\n\\nQuer ver por setor ou rating? (Diga "me conta mais sobre o 1" para análise completa.)';
  }

  if (intent==='status_cobertura') {
    const matched=ativosCart.filter(a=>['Em análise','Watch','Monitoramento','Reprovado'].includes(a.Status)&&(a.saldo||0)>0);
    if(!matched.length) return 'Não há ativos em análise/watch/reprovado na carteira **'+cartStr+'**.';
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    _ctx.lastList=matched.slice(0,8).map(a=>({em:a.emissor||a.ticker}));
    return 'Há **'+matched.length+' ativo(s)** em análise/watch/monitoramento na carteira **'+cartStr+'**, totalizando **R$ '+(saldo/1e6).toFixed(2)+' Mi**.\\n\\n'+matched.slice(0,8).map((a,i)=>(i+1)+'. **'+(a.emissor||a.ticker)+'** ('+(a.ticker||'')+'): '+a.Status).join('\\n')+'\\n\\n*(Diga "análise completa do 1" para detalhes de qualquer emissor.)*';
  }

  if (intent==='divergencia_rating') {
    // Primary: check ATIVOS with active positions (field is 'Rating base S&P')
    const divs=ativosCart.filter(a=>{
      const rd=(a['Rating Douro']||'').trim();
      const rm=(a['Rating base S&P']||'').trim();
      return rd&&rm&&rd!==rm&&(a.saldo||0)>0;
    });
    // Secondary: check RANK_CORP coverage universe (fields: ratingDouro, ratingMkt)
    const rankDivs=(RANK_CORP||[]).filter(r=>{
      const rd=(r.ratingDouro||'').trim();
      const rm=(r.ratingMkt||'').trim();
      return rd&&rm&&rd!==rm;
    });
    const emissoresCart=new Set(ativosCart.map(a=>(a.emissor||'').toLowerCase()));
    // Rank divergences not already covered by cart positions
    const rankExtra=rankDivs.filter(r=>!emissoresCart.has((r.empresa||'').toLowerCase()));
    if(!divs.length&&!rankExtra.length) return 'Não encontrei divergências de rating na carteira **'+cartStr+'**.';
    let resp='';
    if(divs.length){
      resp+='**'+divs.length+' ativo(s) com divergência** na carteira **'+cartStr+'**:\\n';
      resp+=divs.slice(0,8).map(a=>{
        const rd=a['Rating Douro']||'N/D';
        const rm=a['Rating base S&P']||'N/D';
        const dir=rd>rm?'↑ Douro melhor':'↓ Douro mais conservador';
        return '- **'+(a.emissor||a.ticker)+'**: Douro='+rd+' | Mercado='+rm+' ('+dir+')';
      }).join('\\n');
    }
    if(rankExtra.length){
      if(resp) resp+='\\n\\n';
      resp+='**'+rankExtra.length+' emissor(es) cobertos** com divergência (sem posição atual):\\n';
      resp+=rankExtra.slice(0,5).map(r=>{
        const rd=r.ratingDouro||'N/D';
        const rm=r.ratingMkt||'N/D';
        const dir=rd>rm?'↑ Douro melhor':'↓ Douro mais conservador';
        return '- **'+r.empresa+'**: Douro='+rd+' | Mercado='+rm+' ('+dir+')';
      }).join('\\n');
    }
    return resp;
  }

  if (intent==='duration_carteira') {
    const validos=ativosCart.filter(a=>(a.saldo||0)>0&&a.duration!=null);
    const durPond=totalCart>0?(validos.reduce((s,a)=>s+(a.duration||0)*(a.saldo||0),0)/totalCart).toFixed(2):'—';
    const byS={};
    validos.forEach(a=>{const s=a.setor||'N/D';if(!byS[s])byS[s]={saldo:0,ds:0};byS[s].saldo+=(a.saldo||0);byS[s].ds+=(a.duration||0)*(a.saldo||0);});
    const topD=Object.entries(byS).sort((a,b)=>b[1].saldo-a[1].saldo).slice(0,4).map(([s,v])=>s+': '+(v.saldo>0?(v.ds/v.saldo).toFixed(1):'—')+'a').join(' | ');
    return 'Duration médio ponderado — **'+cartStr+'**: **'+durPond+' anos**\\n\\nPor setor (top 4): '+topD;
  }

  if (intent==='comparar_emissores') {
    const normIn=_norm(userTxt||'');
    // Use strict multi-emissor extraction to avoid false fuzzy matches
    const allFound=_extractEmissorMulti(normIn);
    const emList=allFound.length>=2 ? allFound : (()=>{
      // fallback: first found + second pass excluding first
      const em1=_extractEmissor(normIn);
      if(!em1) return [];
      const normEx=normIn.replace(new RegExp(_norm(em1),'g'),' ');
      const em2=_extractEmissor(normEx);
      return em2&&em2!==em1?[em1,em2]:[em1];
    })();
    if(emList.length===0) return 'Qual o primeiro emissor que você quer comparar?';
    if(emList.length===1) return 'Comparar **'+emList[0]+'** com qual outro emissor?';
    // Build comparison table for all emissors found
    const matches=emList.map(em=>ATIVOS.filter(a=>(a.emissor||'').toLowerCase()===em.toLowerCase()&&(a.saldo||0)>0));
    const valid=emList.filter((_,i)=>matches[i].length>0);
    if(valid.length<2) return 'Não encontrei posição em dois ou mais emissores citados na carteira.';
    const tot=ativosCart.reduce((s,a)=>s+(a.saldo||0),0);
    const linhas=valid.map((em,i)=>{
      const ms=matches[emList.indexOf(em)];
      const s=ms.reduce((sum,a)=>sum+(a.saldo||0),0);
      const dur=s>0?(ms.reduce((sum,a)=>sum+(a.duration||0)*(a.saldo||0),0)/s).toFixed(1):'—';
      const sp=ms[0].spread!=null?Number(ms[0].spread).toFixed(3)+'%':'N/D';
      const p=tot>0?((s/tot)*100).toFixed(1):'—';
      return '- **'+em+'**: R$ '+(s/1e6).toFixed(2)+' Mi ('+p+'%) · Duration: '+dur+'a · Spread: '+sp+' · Rating Douro: '+(ms[0]['Rating Douro']||'N/D')+' · Status: '+(ms[0].Status||'N/D');
    }).join('\\n');
    return 'Comparativo: **'+valid.join(' vs ')+'**\\n\\n'+linhas+'\\n\\nQuer aprofundar em algum deles?';
  }

  if (intent==='detalhe_ativo') {
    if(!ent.emissor) return 'Sobre qual emissor você quer ver o spread ou duration?';
    const matched=ativosCart.filter(a=>(a.emissor||'').toLowerCase().includes(ent.emissor.toLowerCase())&&(a.saldo||0)>0);
    if(!matched.length) return 'Não encontrei posição em **'+ent.emissor+'** na carteira **'+cartStr+'**.';
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    const durPond=saldo>0?(matched.reduce((s,a)=>s+(a.duration||0)*(a.saldo||0),0)/saldo).toFixed(2):'—';
    const tickers=matched.map(a=>a.ticker).filter(Boolean);
    let spreadInfo='N/D';
    const dispTs=tickers.filter(t=>SPREADS_TS[t]&&SPREADS_TS[t].spread);
    if(dispTs.length>0) {
      const spVals=dispTs.map(t=>{const arr=SPREADS_TS[t].spread.filter(v=>v!=null);return arr.length?arr[arr.length-1]:null;}).filter(v=>v!=null);
      if(spVals.length) {
        const spMed=spVals.reduce((s,v)=>s+v,0)/spVals.length;
        spreadInfo=spMed.toFixed(3)+'%';
        const allSp=dispTs.flatMap(t=>SPREADS_TS[t].spread.filter(v=>v!=null));
        if(allSp.length>5) {
          const med=allSp.slice().sort((a,b)=>a-b)[Math.floor(allSp.length/2)];
          spreadInfo+=' (mediana hist: '+med.toFixed(3)+'% | '+(spMed-med>=0?'+':'')+(spMed-med).toFixed(3)+'% vs mediana)';
        }
      }
    } else {
      const spRaw=matched.find(a=>a.spread!=null&&!isNaN(Number(a.spread)))?.spread;
      if(spRaw!=null) spreadInfo=Number(spRaw).toFixed(3)+'%';
    }
    const ntnbStr=matched.find(a=>a.ntnb_ref&&a.ntnb_ref!=='None'&&a.ntnb_ref!=='NaT')?.ntnb_ref||'—';
    const taxaStr=matched[0].valor!=null&&!isNaN(Number(matched[0].valor))?Number(matched[0].valor).toFixed(3)+'%':'N/D';
    return 'Detalhe — **'+ent.emissor+'**\\n\\n- **Saldo:** R$ '+(saldo/1e6).toFixed(2)+' Mi ('+matched.length+' ativo(s))\\n- **Taxa atual:** '+taxaStr+'\\n- **Spread vs NTN-B:** '+spreadInfo+'\\n- **NTN-B Ref:** '+ntnbStr+'\\n- **Duration média:** '+durPond+'a\\n- **Rating Douro:** '+(matched[0]['Rating Douro']||'N/D')+'\\n- **Status:** '+(matched[0].Status||'N/D')+'\\n\\nQuer ver a evolução histórica do spread?';
  }

  if (intent==='analise_spreads') {
    const normIn=_norm(userTxt||'');
    const caiu=['caiu','cairam','fechou','fecharam','comprimiu','comprimiram','tightening','baixo','mais baixo','melhores','abaixo'].some(w=>normIn.includes(w));
    let base=ativosCart.filter(a=>(a.saldo||0)>0);
    if(ent.setor) {
      base=base.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase()));
      if(!base.length) return 'Não encontrei ativos no setor **'+ent.setor+'** com saldo.';
    }
    const itens=[];
    for (const ativo of base) {
      const spreadAt=ativo.spread!=null?Number(ativo.spread):null;
      if(spreadAt==null) continue;
      const ts=SPREADS_TS[ativo.ticker];
      let mediana=null,mad1=null,delta7d=null,zscore=null;
      if(ts) {
        mediana=ts.mediana_spread!=null?Number(ts.mediana_spread):null;
        mad1=ts.mediana_mais_1mad_spread!=null?Number(ts.mediana_mais_1mad_spread):null;
        if(ts.spread&&ts.spread.length>8) {const rec=ts.spread.filter(v=>v!=null);if(rec.length>8) delta7d=rec[rec.length-1]-rec[rec.length-8];}
        if(mediana!=null&&mad1!=null){const madV=mad1-mediana,std=madV*1.4826;zscore=std>0?(spreadAt-mediana)/std:null;}
      }
      itens.push({ticker:ativo.ticker,emissor:ativo.emissor||ativo.ticker,setor:ativo.setor||'N/D',spreadAt,mediana,mad1,delta7d,zscore});
    }
    if(!itens.length) return 'Não há dados de spread suficientes na carteira **'+cartStr+'** para esta análise.';
    const ordenados=caiu?itens.sort((a,b)=>a.spreadAt-b.spreadAt):itens.sort((a,b)=>(b.zscore!=null?b.zscore:b.spreadAt)-(a.zscore!=null?a.zscore:a.spreadAt));
    const top=ordenados.slice(0,6);
    const titulo=(caiu?'**Spreads mais comprimidos**':'**Spreads mais elevados** (vs histórico)')+' — '+(ent.setor?'Setor '+ent.setor.toUpperCase():cartStr);
    const linhas=top.map((item,i)=>{
      const zStr=item.zscore!=null?' | z='+item.zscore.toFixed(1):'';
      const d7Str=item.delta7d!=null?' | delta7d: '+(item.delta7d>=0?'+':'')+item.delta7d.toFixed(3)+'%':'';
      const alerta=item.mad1!=null&&item.spreadAt>item.mad1?' ⚠':'';
      return (i+1)+'. **'+item.emissor+'** ('+item.setor+')\\n   Spread: '+item.spreadAt.toFixed(3)+'% | Mediana: '+(item.mediana!=null?item.mediana.toFixed(3)+'%':'N/D')+zStr+d7Str+alerta;
    }).join('\\n');
    const acimaMad=itens.filter(i=>i.mad1!=null&&i.spreadAt>i.mad1).length;
    return titulo+'\\n\\n'+linhas+(acimaMad>0?'\\n\\n⚠ **'+acimaMad+' ativo(s)** acima de +1 MAD — spreads historicamente elevados.':'\\nSpreads dentro da banda histórica normal.')+'\\n\\nQuer aprofundar em algum desses emissores?';
  }

  // ── GRÁFICO DE SPREAD ────────────────────────────────────────────────────
  if (intent==='grafico_spread') {
    if(!ent.emissor) return {text:'Sobre qual emissor você quer ver o gráfico de spread? (ex: "gráfico spread de Klabin")'};
    const mAtivos=ativosCart.filter(a=>(a.emissor||'').toLowerCase().includes(ent.emissor.toLowerCase())&&(a.saldo||0)>0);
    if(!mAtivos.length) return {text:'Não encontrei posição em **'+ent.emissor+'** na carteira **'+cartStr+'**.'};
    const tks=mAtivos.map(a=>a.ticker).filter(t=>SPREADS_TS[t]&&(SPREADS_TS[t].spread||[]).some(v=>v!=null));
    if(!tks.length) return {text:'Não há série histórica de spread para **'+ent.emissor+'**. Verifique se há dados de CP carregados.'};
    const bestTk=tks.reduce((b,t)=>{const len=(SPREADS_TS[t].spread||[]).filter(v=>v!=null).length;return len>(SPREADS_TS[b]?(SPREADS_TS[b].spread||[]).filter(v=>v!=null).length:0)?t:b;},tks[0]);
    const ts=SPREADS_TS[bestTk];
    const pairs=(ts.datas||[]).map((d,i)=>{return{d,v:ts.spread[i]};}).filter(p=>p.v!=null).slice(-120);
    if(!pairs.length) return {text:'Série de spread vazia para **'+bestTk+'**.'};
    const labels=pairs.map(p=>p.d);
    const data=pairs.map(p=>parseFloat(p.v));
    const med=ts.mediana_spread!=null?parseFloat(ts.mediana_spread):null;
    const mad1=ts.mediana_mais_1mad_spread!=null?parseFloat(ts.mediana_mais_1mad_spread):null;
    const cur=data[data.length-1];
    const deltaStr=med!=null?(' | '+(cur-med>=0?'+':'')+(cur-med).toFixed(3)+'% vs mediana'):'';
    const datasets=[{label:bestTk,data,borderColor:'#4abfcb',backgroundColor:'rgba(74,191,203,.07)',tension:.35,pointRadius:0,borderWidth:2,fill:true}];
    if(med!=null) datasets.push({label:'Mediana ('+med.toFixed(3)+'%)',data:Array(data.length).fill(med),borderColor:'#b69d74',borderDash:[6,3],borderWidth:1.5,pointRadius:0,fill:false});
    if(mad1!=null) datasets.push({label:'+1MAD ('+mad1.toFixed(3)+'%)',data:Array(data.length).fill(mad1),borderColor:'#e05252',borderDash:[3,3],borderWidth:1,pointRadius:0,fill:false});
    const _co={color:'#718096',font:{size:8}};
    return {
      text:'Spread de **'+ent.emissor+'** ('+bestTk+') — últimas '+data.length+' observações.\\n\\nAtual: **'+cur.toFixed(3)+'%**'+deltaStr+(mad1!=null&&cur>mad1?'\\n\\n⚠ Spread **acima de +1 MAD** — historicamente elevado.':''),
      chartTitulo:'SPREAD · '+bestTk,
      chart:{type:'line',data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:true,position:'bottom',labels:{color:'#8a9ab0',font:{size:9},boxWidth:8,padding:8}}},scales:{x:{ticks:{..._co,maxTicksLimit:6},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{..._co,callback:v=>v.toFixed(2)+'%'},grid:{color:'rgba(255,255,255,.04)'}}}}}
    };
  }

  // ── GRÁFICO POR SETOR ────────────────────────────────────────────────────
  if (intent==='grafico_setor') {
    const byS={};
    ativosCart.filter(a=>(a.saldo||0)>0).forEach(a=>{const s=a.setor||'N/D';byS[s]=(byS[s]||0)+(a.saldo||0);});
    const sorted=Object.entries(byS).sort((a,b)=>b[1]-a[1]);
    if(!sorted.length) return {text:'Não há dados de setor disponíveis na carteira **'+cartStr+'**.'};
    const labels=sorted.map(s=>s[0]);
    const data=sorted.map(s=>parseFloat((s[1]/1e6).toFixed(2)));
    const tot=sorted.reduce((s,x)=>s+x[1],0);
    const CORES=['#00677b','#b69d74','#4abfcb','#6b8cad','#d4a843','#5a7fa0','#88b3b0','#8b7355','#4a7c6f','#c4956a'];
    const pctLinhas=sorted.slice(0,6).map((s,i)=>(i+1)+'. **'+s[0]+'**: R$ '+(s[1]/1e6).toFixed(1)+' Mi ('+(tot>0?(s[1]/tot*100).toFixed(1):'0')+'%)').join('\\n');
    const _co={color:'#718096',font:{size:9}};
    return {
      text:'Exposição por setor — **'+cartStr+'**:\\n\\n'+pctLinhas,
      chartTitulo:'DISTRIBUIÇÃO SETORIAL (R$ Mi)',
      chart:{type:'bar',data:{labels,datasets:[{data,backgroundColor:labels.map((_,i)=>CORES[i%CORES.length]),borderRadius:4,borderSkipped:false}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>' R$ '+ctx.raw+' Mi'}}},scales:{x:{ticks:{..._co,callback:v=>'R$'+v+'M'},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{..._co},grid:{display:false}}}}}
    };
  }

  // ── CENÁRIO DE ESTRESSE / RISCO DE REFINANCIAMENTO ───────────────────────
  if (intent==='risco_estresse') {
    const emVistos=new Set();
    const itens=[];
    for(const ativo of ativosCart.filter(a=>(a.saldo||0)>0)) {
      const em=ativo.emissor;
      if(!em||emVistos.has(em)) continue;
      emVistos.add(em);
      const ts=SPREADS_TS[ativo.ticker];
      let zscore=null,spreadAt=null,med=null,mad1=null;
      if(ts&&ts.spread) {
        const arr=ts.spread.filter(v=>v!=null);
        if(arr.length>5) {
          spreadAt=arr[arr.length-1];
          med=ts.mediana_spread!=null?parseFloat(ts.mediana_spread):null;
          mad1=ts.mediana_mais_1mad_spread!=null?parseFloat(ts.mediana_mais_1mad_spread):null;
          if(med!=null&&mad1!=null){const madV=mad1-med,std=madV*1.4826;zscore=std>0?(spreadAt-med)/std:null;}
        }
      } else if(ativo.spread!=null) { spreadAt=parseFloat(ativo.spread); }
      const statusRisco=['Em análise','Watch','Monitoramento','Reprovado'].includes(ativo.Status);
      const spStress=zscore!=null?zscore>1.5:(mad1!=null&&spreadAt!=null&&spreadAt>mad1);
      if(statusRisco||spStress) {
        const saldo=ativosCart.filter(a=>(a.emissor||'')===em).reduce((s,a)=>s+(a.saldo||0),0);
        itens.push({em,setor:ativo.setor||'N/D',status:ativo.Status,rating:ativo['Rating Douro']||'N/D',saldo,spreadAt,med,mad1,zscore,statusRisco,spStress});
      }
    }
    if(!itens.length) return 'Nenhum sinal crítico de estresse identificado em **'+cartStr+'**. Spreads dentro da banda histórica e cobertura normalizada.';
    const totalStr=itens.reduce((s,e)=>s+e.saldo,0);
    const pct=totalCart>0?((totalStr/totalCart)*100).toFixed(1):'0';
    itens.sort((a,b)=>(b.zscore||0)-(a.zscore||0));
    const linhas=itens.slice(0,7).map(e=>{
      const flags=[];
      if(e.spStress) flags.push('spread '+(e.zscore?'+'+e.zscore.toFixed(1)+'σ':'> +1MAD'));
      if(e.statusRisco) flags.push(e.status);
      return '- **'+e.em+'** ('+e.setor+' · '+e.rating+'): '+flags.join(' | ')+' — R$ '+(e.saldo/1e6).toFixed(2)+' Mi';
    }).join('\\n');
    const nivel=itens.length>=4?'⚠ **Alerta de refinanciamento**':itens.length>=2?'🔍 **Atenção preventiva**':'📌 **Monitoramento pontual**';
    return nivel+' — **'+cartStr+'**\\n\\nExposição sob stress: **R$ '+(totalStr/1e6).toFixed(2)+' Mi** ('+pct+'% da carteira)\\n\\n'+linhas+'\\n\\n*Critérios: spread > +1.5σ histórico ou status crítico de cobertura. Emissores com maior risco de acesso ao mercado de capitais em cenário de alta de juros.*';
  }

  // ── MAPA DE RISCO POR EMISSOR ────────────────────────────────────────────
  if (intent==='mapa_risco') {
    const _ORD={'CCC':0,'CC':1,'C':2,'D':3,'B-':4,'B':5,'B+':6,'BB-':7,'BB':8,'BB+':9,'BBB-':10,'BBB':11,'BBB+':12,'A-':13,'A':14,'A+':15,'AA-':16,'AA':17,'AA+':18,'AAA':19,'brCCC':0,'brCC':1,'brC':2,'brB-':4,'brB':5,'brB+':6,'brBB-':7,'brBB':8,'brBB+':9,'brBBB-':10,'brBBB':11,'brBBB+':12,'brA-':13,'brA':14,'brA+':15,'brAA-':16,'brAA':17,'brAA+':18,'brAAA':19};
    const agrEm={};
    ativosCart.filter(a=>(a.saldo||0)>0).forEach(a=>{
      const em=a.emissor||'N/D';
      if(!agrEm[em]) agrEm[em]={saldo:0,rating:a['Rating Douro']||'N/D',status:a.Status||'N/D',setor:a.setor||'N/D'};
      agrEm[em].saldo+=(a.saldo||0);
    });
    const lista=Object.entries(agrEm).map(([em,v])=>{return{em,...v,riskScore:_ORD[v.rating]!=null?_ORD[v.rating]:20};});
    lista.sort((a,b)=>a.riskScore-b.riskScore);
    if(!lista.length) return 'Não há ativos com saldo na carteira **'+cartStr+'**.';
    const watchCount=lista.filter(e=>['Em análise','Watch','Monitoramento','Reprovado'].includes(e.status)).length;
    const linhas=lista.slice(0,10).map((e,i)=>{
      const watchFlag=['Em análise','Watch','Monitoramento','Reprovado'].includes(e.status)?' ⚠':'';
      const riskEmoji=e.riskScore<=7?'🔴':e.riskScore<=11?'🟡':'🟢';
      return riskEmoji+' **'+e.em+'** · '+e.rating+' · '+e.setor+' · R$ '+(e.saldo/1e6).toFixed(2)+' Mi'+watchFlag;
    }).join('\\n');
    _ctx.lastList=lista.slice(0,10).map(e=>({em:e.em}));
    return 'Mapa de risco — **'+cartStr+'** (do mais ao menos arriscado):\\n\\n'+linhas+(watchCount?'\\n\\n⚠ **'+watchCount+' emissor(es)** com status crítico de cobertura (Watch/Análise/Reprovado).':'\\n\\nCarteira sem alertas críticos de cobertura.')+'\\n\\n*(Diga "análise completa do 1" para detalhar.)*';
  }

  // ── EVOLUÇÃO TEMPORAL DE FUNDAMENTAIS ──────────────────────────────────────
  if (intent==='evolucao_fundamento') {
    const norm=_norm(userTxt||'');
    const ci=_detectCampo(norm);
    if(!ci) return 'Qual indicador você quer acompanhar? (ex: EBITDA, alavancagem, ROE, margem EBITDA)';
    const meses=_extractMeses(norm)||36;
    const cutDate=new Date(new Date().getTime()-meses*30.44*86400000);
    const _co={color:'#718096',font:{size:8}};
    // ── Por emissor específico ────────────────────────────────────────────
    const fk=ent.emissor?_matchToFin(ent.emissor):null;
    if(fk&&FIN_SERIES[fk]) {
      const fd=FIN_SERIES[fk];
      const arr=fd[ci.campo]||[];
      const datas=fd.datas||[];
      const pairs=datas.map((d,i)=>{return{d:new Date(d),dStr:d,v:arr[i]};}).filter(p=>p.v!=null&&!isNaN(p.v)&&p.d>=cutDate);
      if(!pairs.length) return 'Sem dados de **'+ci.label+'** para **'+ent.emissor+'** no período solicitado.';
      const labels=pairs.map(p=>p.dStr);
      const data=pairs.map(p=>{const v=parseFloat(p.v);return ci.fmt==='%'?parseFloat((v*100).toFixed(2)):ci.fmt==='mi'?parseFloat((v/1e6).toFixed(1)):parseFloat(v.toFixed(2));});
      const lastV=parseFloat(pairs[pairs.length-1].v),firstV=parseFloat(pairs[0].v);
      const delta=lastV-firstV;
      const trendDelta=data.length>1?data[data.length-1]-data[0]:0;
      const trendLine=data.map((_,i)=>parseFloat((data[0]+trendDelta/(data.length-1||1)*i).toFixed(2)));
      const periStr=meses>=12?(meses/12).toFixed(0)+'a':meses+'m';
      const deltaFmt=(delta>=0?'+':'')+(ci.fmt==='%'?(delta*100).toFixed(1)+'%':ci.fmt==='x'?delta.toFixed(2)+'x':ci.fmt==='mi'?'R$ '+(delta/1e6).toFixed(0)+' Mi':delta.toFixed(2));
      return {
        text:'Evolução de **'+ci.label+'** — **'+ent.emissor+'** ('+periStr+')\\n\\nAtual: **'+_fmtV(lastV,ci.fmt)+'** | Var. período: **'+deltaFmt+'** '+(delta>=0?'↑':'↓'),
        chartTitulo:'EVOLUÇÃO '+ci.label.toUpperCase()+' · '+ent.emissor.toUpperCase(),
        chart:{type:'line',data:{labels,datasets:[{label:ci.label,data,borderColor:'#4abfcb',backgroundColor:'rgba(74,191,203,.10)',tension:.4,pointRadius:2,pointBackgroundColor:'#4abfcb',borderWidth:2,fill:true,spanGaps:true},{label:'Tendência',data:trendLine,borderColor:'rgba(182,157,116,.6)',borderDash:[5,4],borderWidth:1.5,pointRadius:0,fill:false}]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:true,position:'bottom',labels:{color:'#8a9ab0',font:{size:9},boxWidth:8,padding:6}}},scales:{x:{ticks:{..._co,maxTicksLimit:8},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{..._co,callback:v=>v+(ci.fmt==='x'?'x':ci.fmt==='%'?'%':'')},grid:{color:'rgba(255,255,255,.04)'}}}}}
      };
    }
    // ── Por setor (média das empresas do portfólio) ───────────────────────
    if(ent.setor) {
      const emSec=ativosCart.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase())&&(a.saldo||0)>0);
      const emList=[...new Set(emSec.map(a=>a.emissor).filter(Boolean))];
      const finKeys=emList.map(e=>_matchToFin(e)).filter(Boolean);
      if(!finKeys.length) return 'Não encontrei dados financeiros para empresas do setor **'+ent.setor+'** na carteira.';
      const allDates=[...new Set(finKeys.flatMap(k=>(FIN_SERIES[k].datas||[])))].filter(d=>new Date(d)>=cutDate).sort();
      if(!allDates.length) return 'Sem dados no período para o setor **'+ent.setor+'**.';
      const avgData=allDates.map(dt=>{
        const vals=finKeys.map(k=>{const idx=(FIN_SERIES[k].datas||[]).indexOf(dt);return idx>=0&&FIN_SERIES[k][ci.campo]&&FIN_SERIES[k][ci.campo][idx]!=null?parseFloat(FIN_SERIES[k][ci.campo][idx]):null;}).filter(v=>v!=null);
        return vals.length?vals.reduce((s,v)=>s+v,0)/vals.length:null;
      });
      const data=avgData.map(v=>v==null?null:ci.fmt==='%'?parseFloat((v*100).toFixed(2)):ci.fmt==='mi'?parseFloat((v/1e6).toFixed(1)):parseFloat(v.toFixed(2)));
      const lastV=avgData.filter(v=>v!=null).slice(-1)[0];
      const periStr=meses>=12?(meses/12).toFixed(0)+'a':meses+'m';
      return {
        text:'Evolução de **'+ci.label+'** — Setor **'+ent.setor+'** (média portfólio, '+periStr+')\\n\\nÚltima média: **'+_fmtV(lastV||0,ci.fmt)+'**',
        chartTitulo:'EVOLUÇÃO '+ci.label.toUpperCase()+' · SETOR '+ent.setor.toUpperCase(),
        chart:{type:'line',data:{labels:allDates,datasets:[{label:ci.label+' (média setor)',data,borderColor:'#b69d74',backgroundColor:'rgba(182,157,116,.10)',tension:.4,pointRadius:2,pointBackgroundColor:'#b69d74',borderWidth:2,fill:true,spanGaps:true}]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:false}},scales:{x:{ticks:{..._co,maxTicksLimit:8},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{..._co,callback:v=>v+(ci.fmt==='x'?'x':ci.fmt==='%'?'%':'')},grid:{color:'rgba(255,255,255,.04)'}}}}}
      };
    }
    return 'Para ver a evolução de **'+ci.label+'**, informe o emissor (ex: "evolução de EBITDA da Klabin") ou o setor.';
  }

  // ── COMPARAÇÃO COM MÉDIA DO SETOR ──────────────────────────────────────────
  if (intent==='comparar_setor') {
    const norm=_norm(userTxt||'');
    const ci=_detectCampo(norm)||{campo:'DivLiquida/EBITDA',label:'Dív.Líq./EBITDA',fmt:'x',tipo:'fund',limiar:3.5,limiarDir:'>'};
    const fk=ent.emissor?_matchToFin(ent.emissor):null;
    const setorRef=ent.setor||(fk?FIN_SERIES[fk]&&FIN_SERIES[fk].setor:null)||(ent.emissor?((ativosCart.find(a=>(a.emissor||'').toLowerCase().includes(ent.emissor.toLowerCase()))||{}).setor||null):null);
    if(!setorRef&&!fk) return 'Para comparar com a média do setor, informe o emissor e/ou setor. Ex: "Klabin vs média de papel e celulose em alavancagem".';
    const peerAtivos=ativosCart.filter(a=>(a.setor||'').toLowerCase().includes((setorRef||'').toLowerCase())&&(a.saldo||0)>0);
    const peerEms=[...new Set(peerAtivos.map(a=>a.emissor).filter(Boolean))];
    const itens=[];
    for(const pe of peerEms) {
      const pfk=_matchToFin(pe); if(!pfk) continue;
      const pv=_lastVal(FIN_SERIES[pfk][ci.campo]); if(pv==null) continue;
      const isTarget=!!(ent.emissor&&pe.toLowerCase().includes(ent.emissor.toLowerCase()));
      itens.push({em:pe,val:pv,isTarget});
    }
    if(fk&&ent.emissor&&!itens.find(x=>x.isTarget)) {
      const tv=_lastVal(FIN_SERIES[fk][ci.campo]);
      if(tv!=null) itens.push({em:ent.emissor,val:tv,isTarget:true});
    }
    if(!itens.length) return 'Não encontrei dados de **'+ci.label+'** para comparação'+(setorRef?' no setor **'+setorRef+'**':'')+'.';;
    const avg=itens.reduce((s,x)=>s+x.val,0)/itens.length;
    const _fmtNum=v=>ci.fmt==='%'?parseFloat((v*100).toFixed(2)):ci.fmt==='mi'?parseFloat((v/1e6).toFixed(1)):parseFloat(v.toFixed(2));
    const labels=[...itens.map(x=>x.em),'⌀ Setor'];
    const data=[...itens.map(x=>_fmtNum(x.val)),_fmtNum(avg)];
    const colors=itens.map(x=>x.isTarget?'rgba(74,191,203,.9)':'rgba(74,191,203,.4)').concat(['rgba(182,157,116,.9)']);
    const sufx=ci.fmt==='x'?'x':ci.fmt==='%'?'%':'';
    const linhas=itens.map((x,i)=>{
      const delta=x.val-avg;
      const ds=(delta>=0?'+':'')+(ci.fmt==='%'?(delta*100).toFixed(1)+'%':ci.fmt==='x'?delta.toFixed(2)+'x':'R$ '+(delta/1e6).toFixed(0)+' Mi');
      return (i+1)+'.'+(x.isTarget?' **':' ')+x.em+(x.isTarget?'**':'')+': **'+(ci.fmt==='%'?(x.val*100).toFixed(1)+'%':_fmtV(x.val,ci.fmt))+'** ('+ds+' vs ⌀)';
    }).join('\\n');
    const _co={color:'#718096',font:{size:8}};
    return {
      text:'**'+ci.label+'** vs média do setor'+(setorRef?' — **'+setorRef+'**':'')+' · **'+cartStr+'**\\n\\n'+linhas+'\\n\\n⌀ Setor: **'+(ci.fmt==='%'?(avg*100).toFixed(1)+'%':_fmtV(avg,ci.fmt))+'**',
      chartTitulo:ci.label.toUpperCase()+' vs ⌀ SETOR'+(setorRef?' · '+setorRef.toUpperCase():''),
      chart:{type:'bar',data:{labels,datasets:[{data,backgroundColor:colors,borderRadius:4,borderSkipped:false}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>' '+ctx.raw+sufx}}},scales:{x:{ticks:{..._co},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{..._co,font:{size:9}},grid:{display:false}}}}}
    };
  }

  // ── SÍNTESE NARRATIVA DE EMISSOR ───────────────────────────────────────────
  if (intent==='sintese_emissor') {
    if(!ent.emissor) return 'Sobre qual emissor você quer a análise completa?';
    const matched=ativosCart.filter(a=>(a.emissor||'').toLowerCase().includes(ent.emissor.toLowerCase())&&(a.saldo||0)>0);
    if(!matched.length) return 'Não encontrei posição em **'+ent.emissor+'** na carteira **'+cartStr+'**.';
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    const pct=totalCart>0?((saldo/totalCart)*100).toFixed(1):'0';
    const durPond=saldo>0?(matched.reduce((s,a)=>s+(a.duration||0)*(a.saldo||0),0)/saldo).toFixed(1):'—';
    const ratingD=matched[0]['Rating Douro']||'N/D';
    const ratingM=matched[0]['Rating S&P']||matched[0]['Rating base S&P']||'N/D';
    const status=matched[0].Status||'N/D';
    const setor=matched[0].setor||'N/D';
    const tickers=matched.map(a=>a.ticker).filter(Boolean);
    const bestTk=tickers.find(t=>SPREADS_TS[t]&&(SPREADS_TS[t].spread||[]).some(v=>v!=null));
    let spreadTxt='N/D',spAlert='';
    if(bestTk) {
      const ts=SPREADS_TS[bestTk];
      const arr=(ts.spread||[]).filter(v=>v!=null);
      if(arr.length) {
        const cur=arr[arr.length-1];
        const med=ts.mediana_spread!=null?parseFloat(ts.mediana_spread):null;
        const mad1=ts.mediana_mais_1mad_spread!=null?parseFloat(ts.mediana_mais_1mad_spread):null;
        spreadTxt=(cur*100).toFixed(2)+'bps'+(med!=null?' (mediana: '+(med*100).toFixed(2)+'bps | '+(cur>=med?'+':'')+(((cur-med)*100).toFixed(2))+'bps vs hist.)':'');
        if(mad1!=null&&cur>mad1) spAlert=' ⚠ acima de +1MAD';
      }
    } else if(matched[0].spread!=null) {
      spreadTxt=(Number(matched[0].spread)*100).toFixed(2)+'bps';
    }
    const fk=_matchToFin(ent.emissor);
    let fundTxt='',FLAGS=[];
    if(fk&&FIN_SERIES[fk]) {
      const fd=FIN_SERIES[fk];
      const dlE=_lastVal(fd['DivLiquida/EBITDA']),liq=_lastVal(fd['Liquidez Corrente']);
      const roe=_lastVal(fd['ROE']),mgE=_lastVal(fd['Mg EBITDA 36M']),fcf=_lastVal(fd['FCF_TTM']);
      const parts=[];
      if(dlE!=null){parts.push('Dív./EBITDA: **'+_fmtV(dlE,'x')+'**'+(dlE>3.5?' ⚠':''));if(dlE>3.5)FLAGS.push('alavancagem elevada');}
      if(liq!=null){parts.push('Liquidez: **'+_fmtV(liq,'x')+'**'+(liq<1?' ⚠':''));if(liq<1)FLAGS.push('liquidez < 1x');}
      if(roe!=null) parts.push('ROE: **'+_fmtV(roe,'%')+'**');
      if(mgE!=null) parts.push('Mg EBITDA: **'+_fmtV(mgE,'%')+'**');
      if(fcf!=null){parts.push('FCF: **'+_fmtV(fcf,'mi')+'**');if(fcf<0)FLAGS.push('FCF negativo');}
      if(parts.length) fundTxt='\\n\\n**Fundamentais:** '+parts.join(' · ');
    }
    const ratingDiv=ratingD!=='N/D'&&ratingM!=='N/D'&&ratingD!==ratingM?' ⚠ *divergência*':'';
    const statusFlag=['Em análise','Watch','Monitoramento'].includes(status)?' ⚠':'';
    const flagStr=FLAGS.length?'\\n\\n⚠ **Alertas:** '+FLAGS.join(', ')+'.':'';
    return '**Análise — '+ent.emissor+'**\\n\\n- **Posição:** R$ '+(saldo/1e6).toFixed(2)+' Mi ('+pct+'% · **'+cartStr+'**)\\n- **Setor:** '+setor+'\\n- **Duration:** '+durPond+'a\\n- **Rating Douro:** '+ratingD+(ratingM!=='N/D'?' · S&P: '+ratingM+ratingDiv:'')+'\\n- **Status:** '+status+statusFlag+'\\n- **Spread:** '+spreadTxt+spAlert+fundTxt+flagStr+'\\n\\nQuer a evolução temporal ou comparar com o setor?';
  }

  // ── MAPA DE VENCIMENTOS (proxy: duration) ──────────────────────────────────
  if (intent==='mapa_vencimentos') {
    const buckets=[{label:'< 1a',min:0,max:1},{label:'1–2a',min:1,max:2},{label:'2–3a',min:2,max:3},{label:'3–5a',min:3,max:5},{label:'5a+',min:5,max:Infinity}];
    const result={},byBucketEm={};
    buckets.forEach(b=>{result[b.label]=0;byBucketEm[b.label]=[];});
    const agrEm={};
    ativosCart.filter(a=>(a.saldo||0)>0&&a.duration!=null).forEach(a=>{
      const em=a.emissor||a.ticker;
      if(!agrEm[em]) agrEm[em]={saldo:0,durSum:0,setor:a.setor||'N/D'};
      agrEm[em].saldo+=(a.saldo||0);
      agrEm[em].durSum+=(a.duration||0)*(a.saldo||0);
    });
    Object.entries(agrEm).forEach(([em,v])=>{
      const dur=v.saldo>0?v.durSum/v.saldo:0;
      for(const b of buckets){if(dur>=b.min&&dur<b.max){result[b.label]+=v.saldo;byBucketEm[b.label].push(em);break;}}
    });
    const total=Object.values(result).reduce((s,v)=>s+v,0);
    if(!total) return 'Não há ativos com duration na carteira **'+cartStr+'**.';
    const labels=buckets.map(b=>b.label);
    const data=labels.map(l=>parseFloat((result[l]/1e6).toFixed(2)));
    const CORES=['#e05252','#e0b43c','#4abfcb','#6b8cad','#00677b'];
    const linhas=labels.map((l,i)=>(i+1)+'. **'+l+'**: R$ '+(result[l]/1e6).toFixed(1)+' Mi ('+(total>0?((result[l]/total)*100).toFixed(1):'0')+'%)'+(byBucketEm[l].length?' — '+byBucketEm[l].slice(0,3).join(', ')+(byBucketEm[l].length>3?' + '+(byBucketEm[l].length-3)+' mais':''):'')).join('\\n');
    const warnPct=total>0?(result['< 1a']||0)/total:0;
    const warn=warnPct>0.15?'\\n\\n⚠ **'+((result['< 1a']||0)/1e6).toFixed(1)+' Mi ('+(warnPct*100).toFixed(0)+'%)** vencem/renovam em < 1 ano — risco de refinanciamento.':'';
    const _co={color:'#718096',font:{size:9}};
    return {
      text:'Perfil de Vencimentos por Duration — **'+cartStr+'**\\n*(duration como proxy de prazo médio de risco de taxa)*\\n\\n'+linhas+warn,
      chartTitulo:'PERFIL DE VENCIMENTOS POR DURATION',
      chart:{type:'bar',data:{labels,datasets:[{data,backgroundColor:CORES,borderRadius:4,borderSkipped:false}]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>' R$ '+ctx.raw+' Mi'}}},scales:{x:{ticks:{..._co},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{..._co,callback:v=>'R$'+v+'M'},grid:{color:'rgba(255,255,255,.04)'}}}}}
    };
  }

  return _FALLBACKS[Math.floor(Math.random()*_FALLBACKS.length)];
}

// ── CHAT CHART RENDERER ───────────────────────────────────────────────────────
function _addChatChartTo(container, titulo, cfg, cidSuffix) {
  const wrap=document.createElement('div');
  wrap.className='dourado-msg';
  const cid='dChart_'+Date.now()+(cidSuffix||'');
  const h=cfg.options&&cfg.options.indexAxis==='y'?Math.max(160,Math.min(260,(cfg.data.labels||[]).length*28+40)):190;
  wrap.innerHTML=`<div class="dourado-avatar" style="width:28px;height:28px;font-size:12px;flex-shrink:0;">D</div><div class="dourado-bubble dourado-chart-bubble"><div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#b69d74;margin-bottom:8px;">${titulo}</div><div style="position:relative;height:${h}px;"><canvas id="${cid}"></canvas></div></div>`;
  container.appendChild(wrap);
  container.scrollTop=container.scrollHeight;
  requestAnimationFrame(()=>{
    const cv=document.getElementById(cid);
    if(cv&&window.Chart) new Chart(cv,cfg);
  });
}
function _addChatChart(titulo, cfg) {
  const msgs=document.getElementById('douradoMsgs');
  _addChatChartTo(msgs, titulo, cfg, '_s');
  if(_dfOpen){
    const fullMsgs=document.getElementById('douradoFullMsgs');
    if(fullMsgs) _addChatChartTo(fullMsgs, titulo, cfg, '_f');
  }
}

function _nlqRespond(userTxt) {
  if(!userTxt||!userTxt.trim()) return _FALLBACKS[0];
  const norm=_norm(userTxt);

  // ── Personalidade ────────────────────────────────────────────────────────
  if(_SAUDACOES_IN.some(s=>norm===_norm(s)||(norm.length<25&&norm.includes(_norm(s))))) {
    let out=_SAUDACOES_OUT[Math.floor(Math.random()*_SAUDACOES_OUT.length)];
    const h=new Date().getHours();
    if(norm.includes('bom dia')||(h>=5&&h<12&&norm.length<15))       out=_SAUDACOES_OUT[5];
    else if(norm.includes('boa tarde')||(h>=12&&h<18&&norm.length<15)) out=_SAUDACOES_OUT[6];
    else if(norm.includes('boa noite')||(h>=18&&h<24&&norm.length<15)) out=_SAUDACOES_OUT[7];
    return out;
  }
  if(_IDENTIDADE_IN.some(s=>norm.includes(_norm(s))))   return _IDENTIDADE_OUT[Math.floor(Math.random()*_IDENTIDADE_OUT.length)];
  if(_AGRADECIMENTOS_IN.some(s=>norm===_norm(s)||(norm.length<20&&norm.includes(_norm(s))))) return _AGRADECIMENTOS_OUT[Math.floor(Math.random()*_AGRADECIMENTOS_OUT.length)];
  if(_DESPEDIDAS_IN.some(s=>norm===_norm(s)||(norm.length<20&&norm.includes(_norm(s))))) return _DESPEDIDAS_OUT[Math.floor(Math.random()*_DESPEDIDAS_OUT.length)];
  // ── Fim personalidade ────────────────────────────────────────────────────

  const normRes=_resolveRef(norm);

  // Extrair entidades
  const ent={};
  const carts=[...new Set(ATIVOS.map(a=>a.carteira).filter(Boolean))];
  for(const c of carts){if(normRes.includes(_norm(c))){ent.carteira=c;break;}}
  const setsAll=[...new Set(ATIVOS.map(a=>a.setor).filter(Boolean))];
  for(const s of setsAll){const sn=_norm(s),words=sn.split(' ').filter(w=>w.length>3);if(words.some(w=>normRes.includes(w))){ent.setor=s;break;}}
  for(const r of ['AAA','AA+','AA','AA-','A+','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B-','CCC']){if(normRes.includes(r.toLowerCase())){ent.rating=r;break;}}
  ent.emissor=_extractEmissor(normRes)||null;

  // Pending param
  if(_ctx.pendingParam) {
    const pp=_ctx.pendingParam;
    const entC=Object.assign({},pp.entities,ent);
    if(pp.missingParam==='emissor'&&ent.emissor){_ctx.pendingParam=null;_ctx.lastIntent=pp.intent;_ctx.lastEntities=entC;return _queryAtivos(pp.intent,entC,userTxt);}
    if(pp.missingParam==='setor'&&ent.setor){_ctx.pendingParam=null;_ctx.lastIntent=pp.intent;_ctx.lastEntities=entC;return _queryAtivos(pp.intent,entC,userTxt);}
    if(pp.missingParam==='rating'&&ent.rating){_ctx.pendingParam=null;_ctx.lastIntent=pp.intent;_ctx.lastEntities=entC;return _queryAtivos(pp.intent,entC,userTxt);}
    _ctx.pendingParam=null;
  }

  // ── Pre-check drill-down contextual: "o 2", "o segundo", etc. ───────────
  const drillItem=_resolveListDrilldown(normRes);
  if(drillItem) {
    const drillEnt=Object.assign({},_ctx.lastEntities,{emissor:drillItem.em||drillItem});
    return _queryAtivos('sintese_emissor',drillEnt,userTxt);
  }

  // ── Pre-check evolução temporal (tem antes do paramétrico pois usa meses) ─
  if(_isEvolutionQuery(normRes)) {
    _ctx.lastIntent='evolucao_fundamento';
    _ctx.lastEntities=ent;
    return _queryAtivos('evolucao_fundamento',ent,userTxt);
  }

  // ── Pre-check paramétrico: detecta antes do intent normal ────────────────
  if(_isParamQuery(normRes)) {
    _ctx.lastIntent='query_param';
    _ctx.lastEntities=ent;
    return _queryAtivos('query_param',ent,userTxt);
  }

  const {intent}=_matchIntent(normRes);

  if(intent==='exposicao_setor'&&!ent.setor)   {_ctx.pendingParam={intent,entities:ent,missingParam:'setor'};   return 'Qual setor você quer verificar? (ex: energia, infraestrutura, financeiro)';}
  if(intent==='exposicao_emissor'&&!ent.emissor){_ctx.pendingParam={intent,entities:ent,missingParam:'emissor'}; return 'Qual emissor você quer verificar?';}
  if(intent==='exposicao_rating'&&!ent.rating)  {_ctx.pendingParam={intent,entities:ent,missingParam:'rating'};  return 'Qual rating você quer verificar? (ex: AAA, AA, BBB, BB)';}

  _ctx.lastIntent=intent;
  _ctx.lastEntities=ent;

  if(intent==='fallback') return _FALLBACKS[Math.floor(Math.random()*_FALLBACKS.length)];
  return _queryAtivos(intent,ent,userTxt);
}

function _chipAndSend(txt) {
  const inp = document.getElementById('douradoInput');
  inp.value = txt;
  douradoSend();
}
function _douradoCmd(txt) {
  const norm = txt.trim().toLowerCase();
  const cmd  = norm.split(/\s+/)[0];
  const args = txt.trim().slice(cmd.length).trim();
  const cmds = {
    '/clear':     () => { document.getElementById('douradoMsgs').innerHTML=''; douradoWelcome(); return true; },
    '/limpar':    () => { document.getElementById('douradoMsgs').innerHTML=''; douradoWelcome(); return true; },
    '/help':      () => { douradoAddMsg('bot',
      '**Comandos disponíveis**\\n\\n' +
      '`/clear` — Limpa o histórico do chat\\n' +
      '`/resumo` — Resumo geral da carteira\\n' +
      '`/top [N]` — Top N maiores posições (padrão: 10)\\n' +
      '`/spread` — Visão de spreads e alertas MAD\\n' +
      '`/rating` — Distribuição de rating da carteira\\n' +
      '`/setor` — Concentração por setor\\n' +
      '`/duration` — Duration média ponderada\\n' +
      '`/watch` — Emissores em watch / análise\\n' +
      '`/stress` — Cenário de estresse: refinanciamento\\n' +
      '`/vencimentos` — Perfil de vencimentos\\n' +
      '`/alavancagem` — Ranking Dív.Liq/EBITDA\\n' +
      '`/cobertura` — Status de cobertura de crédito\\n' +
      '`/carteira [nome]` — Filtra análise por carteira\\n' +
      '`/emissor [nome]` — Síntese completa de um emissor\\n' +
      '`/comparar [A] vs [B]` — Compara dois emissores\\n' +
      '`/grafico setor` — Gráfico de exposição por setor\\n' +
      '`/help` — Esta mensagem'
    ); return true; },
    '/resumo':    () => { _chipAndSend('Resumo geral da carteira'); return true; },
    '/spread':    () => { _chipAndSend('Quais spreads mais subiram? Alertas de MAD'); return true; },
    '/rating':    () => { _chipAndSend('Distribuição de rating da carteira'); return true; },
    '/setor':     () => { _chipAndSend('Concentração por setor'); return true; },
    '/duration':  () => { _chipAndSend('Qual o duration médio da carteira?'); return true; },
    '/watch':     () => { _chipAndSend('Quais emissores estão em watch ou análise?'); return true; },
    '/stress':    () => { _chipAndSend('Cenário de estresse: quais emissores em risco de refinanciamento?'); return true; },
    '/vencimentos':() => { _chipAndSend('Perfil de vencimentos da carteira'); return true; },
    '/alavancagem':() => { _chipAndSend('Ranking de alavancagem — maior para menor'); return true; },
    '/cobertura': () => { _chipAndSend('Status de cobertura dos emissores'); return true; },
    '/grafico':   () => { if(args.includes('setor')) { _chipAndSend('Gráfico de exposição por setor'); return true; } return false; },
    '/top':       () => { const n=parseInt(args)||10; _chipAndSend('Maiores posições por emissor top '+n); return true; },
    '/carteira':  () => { if(args) { _chipAndSend('Resumo da carteira '+args); return true; } return false; },
    '/emissor':   () => { if(args) { _chipAndSend('Análise completa da '+args); return true; } return false; },
    '/comparar':  () => { if(args) { _chipAndSend(args.replace(' vs ',' vs ')); return true; } return false; },
  };
  const fn = cmds[cmd];
  if (fn) return fn();
  douradoAddMsg('bot', `Comando \`${txt}\` não reconhecido. Use \`/help\` para ver os disponíveis.`);
  return true;
}

async function douradoSend() {
  _rebuildDouradoKW();
  _dspHide();
  const input=document.getElementById('douradoInput');
  const txt=input.value.trim();
  if(!txt) return;
  input.value='';
  input.style.height='auto';
  if(txt.startsWith('/')) { if(_douradoCmd(txt)) return; }
  douradoAddMsg('user',txt);
  const thinkingEl=douradoAddMsg('bot','',true);
  await new Promise(r=>setTimeout(r,150+Math.random()*200));
  try {
    const resposta=_nlqRespond(txt);
    thinkingEl.remove();
    if(resposta&&typeof resposta==='object'&&resposta.text!==undefined) {
      douradoAddMsg('bot',resposta.text);
      if(resposta.chart) setTimeout(()=>_addChatChart(resposta.chartTitulo||'',resposta.chart),60);
    } else {
      douradoAddMsg('bot',resposta);
    }
  } catch(e) {
    thinkingEl.remove();
    douradoAddMsg('bot','Erro interno no processamento. Tente novamente.\\n\\n*'+e.message+'*');
  }
}
// ── SIDEBAR RAIL ─────────────────────────────────────────────────────────────
let _sidebarPinned = false;

function _setSidebarRail(shouldRail) {
  const sb = document.querySelector('.sidebar');
  const main = document.querySelector('.main');
  if (!sb || !main) return;
  if (shouldRail && !_sidebarPinned) {
    sb.classList.add('rail');
    main.classList.add('rail-active');
  } else {
    sb.classList.remove('rail');
    main.classList.remove('rail-active');
  }
}

function toggleSidebarPin() {
  _sidebarPinned = !_sidebarPinned;
  const btn = document.getElementById('sidebarPinBtn');
  if (btn) btn.classList.toggle('pinned', _sidebarPinned);
  const activePage = document.querySelector('.page.active');
  const isHome = activePage && activePage.id === 'page-home';
  _setSidebarRail(!isHome);
}

function _updateSidebarBadges() {
  // Dourado pulse quando o chat está fechado
  const dBtn = document.getElementById('douradoBtn');
  if (dBtn) dBtn.classList.toggle('pulsing', !douradoOpen);
}

// ── SEARCHABLE SELECT ─────────────────────────────────────────────────────
function initSearchableSelects() {
  document.querySelectorAll('.filter-pill[data-prefix]').forEach(wrap => {
    const label  = wrap.querySelector('.ss-label');
    const search = wrap.querySelector('.ss-search');
    const list   = wrap.querySelector('.ss-list');
    const sel    = wrap.querySelector('select');
    const prefix = wrap.dataset.prefix || '';
    const allTxt = wrap.dataset.all   || 'Todos';

    // Open / close on pill click
    wrap.addEventListener('click', e => {
      if (e.target.closest('.ss-dropdown')) return;
      const isOpen = wrap.classList.contains('ss-open');
      document.querySelectorAll('.filter-pill.ss-open').forEach(w => {
        w.classList.remove('ss-open');
        w.querySelector('.ss-search').value = '';
        w.querySelectorAll('.ss-opt').forEach(o => o.classList.remove('ss-hidden'));
      });
      if (!isOpen) {
        wrap.classList.add('ss-open');
        setTimeout(() => search.focus(), 40);
      }
    });

    // Live filter
    search.addEventListener('input', () => {
      const q = search.value.toLowerCase();
      list.querySelectorAll('.ss-opt').forEach(o => {
        o.classList.toggle('ss-hidden', !!q && !o.textContent.toLowerCase().includes(q));
      });
    });

    // Pick option
    list.querySelectorAll('.ss-opt').forEach(opt => {
      opt.addEventListener('click', e => {
        e.stopPropagation();
        const val = opt.dataset.value;
        sel.value = val;
        list.querySelectorAll('.ss-opt').forEach(o => o.classList.remove('ss-active'));
        opt.classList.add('ss-active');
        label.textContent = prefix + (val ? val : allTxt);
        wrap.classList.remove('ss-open');
        search.value = '';
        list.querySelectorAll('.ss-opt').forEach(o => o.classList.remove('ss-hidden'));
        applyFilters();
      });
    });
  });

  // Close on outside click
  document.addEventListener('click', e => {
    if (!e.target.closest('.filter-pill[data-prefix]')) {
      document.querySelectorAll('.filter-pill.ss-open').forEach(w => {
        w.classList.remove('ss-open');
        w.querySelector('.ss-search').value = '';
        w.querySelectorAll('.ss-opt').forEach(o => o.classList.remove('ss-hidden'));
      });
    }
  });
}
// ── INIT ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initSearchableSelects();
  showPage('home', null);
  const hBtn = document.getElementById('homeBtnTopbar');
  if (hBtn) hBtn.classList.add('active');
  setTimeout(_updateSidebarBadges, 200);
});

// ── WAR ROOM (Ctrl+Shift+R) ───────────────────────────────────────────────
(function() {
  // Injeta CSS
  const style = document.createElement('style');
  style.textContent = `
    #warRoomOverlay {
      display:none; position:fixed; inset:0; z-index:9999;
      background:#0a0e1a;
      flex-direction:column; align-items:stretch; justify-content:stretch;
      font-family:var(--font,'Montserrat',sans-serif);
      animation: wrFadeIn .25s ease;
    }
    #warRoomOverlay.open { display:flex; }
    @keyframes wrFadeIn { from{opacity:0;transform:scale(.98)} to{opacity:1;transform:scale(1)} }
    .wr-header {
      display:flex; align-items:center; justify-content:space-between;
      padding:18px 36px 14px;
      border-bottom:1px solid rgba(255,255,255,.06);
    }
    .wr-logo { display:flex; align-items:center; gap:12px; }
    .wr-logo-mark {
      width:36px; height:36px; border-radius:8px;
      background:linear-gradient(135deg,#b69d74,#8a7355);
      display:flex; align-items:center; justify-content:center;
      font-size:16px; font-weight:800; color:#fff;
    }
    .wr-logo-text { font-size:15px; font-weight:700; color:#e2e8f0; letter-spacing:.04em; }
    .wr-logo-sub  { font-size:11px; color:#718096; font-weight:500; margin-top:1px; }
    .wr-datetime  { font-size:12px; color:#718096; font-family:var(--mono,'monospace'); text-align:right; }
    .wr-close {
      cursor:pointer; color:#4a5568; font-size:22px; padding:4px 8px;
      border-radius:6px; transition:color .15s, background .15s;
      border:none; background:transparent;
    }
    .wr-close:hover { color:#e2e8f0; background:rgba(255,255,255,.06); }
    .wr-hint { font-size:10px; color:#2d3748; margin-left:8px; }
    .wr-body {
      flex:1; display:grid; padding:28px 36px 24px;
      gap:20px;
      grid-template-rows: auto 1fr auto;
    }
    .wr-kpi-row {
      display:grid;
      grid-template-columns: repeat(5, 1fr);
      gap:16px;
    }
    .wr-kpi {
      background:rgba(255,255,255,.03);
      border:1px solid rgba(255,255,255,.07);
      border-radius:14px; padding:20px 22px;
      display:flex; flex-direction:column; gap:6px;
      position:relative; overflow:hidden;
    }
    .wr-kpi::after {
      content:''; position:absolute; bottom:0; left:0; right:0; height:3px;
    }
    .wr-kpi.green::after  { background:linear-gradient(90deg,#2fa874,#1d7a55); }
    .wr-kpi.red::after    { background:linear-gradient(90deg,#d94141,#a02f2f); }
    .wr-kpi.gold::after   { background:linear-gradient(90deg,#b69d74,#8a7355); }
    .wr-kpi.neutral::after{ background:linear-gradient(90deg,#4a5568,#2d3748); }
    .wr-kpi-label  { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.1em; color:#4a5568; }
    .wr-kpi-value  { font-family:var(--mono,'monospace'); font-size:36px; font-weight:700; color:#e2e8f0; line-height:1; }
    .wr-kpi-sub    { font-size:12px; color:#718096; margin-top:2px; }
    .wr-kpi-badge  {
      display:inline-flex; align-items:center; gap:5px;
      padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700;
      margin-top:4px; width:fit-content;
    }
    .wr-kpi-badge.green  { background:rgba(47,168,116,.15); color:#2fa874; }
    .wr-kpi-badge.red    { background:rgba(217,65,65,.15);  color:#d94141; }
    .wr-kpi-badge.gold   { background:rgba(182,157,116,.15);color:#b69d74; }
    .wr-middle {
      display:grid; grid-template-columns:1fr 1fr; gap:20px;
    }
    .wr-panel {
      background:rgba(255,255,255,.025);
      border:1px solid rgba(255,255,255,.06);
      border-radius:14px; padding:20px 24px; overflow:hidden;
    }
    .wr-panel-title {
      font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.1em;
      color:#4a5568; margin-bottom:16px;
    }
    .wr-emissores-grid {
      display:grid; grid-template-columns:1fr 1fr; gap:8px 24px;
    }
    .wr-em-row {
      display:flex; align-items:center; gap:8px; padding:4px 0;
      border-bottom:1px solid rgba(255,255,255,.04);
    }
    .wr-em-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
    .wr-em-name { flex:1; font-size:13px; color:#a0aec0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .wr-em-val  { font-family:var(--mono,'monospace'); font-size:13px; color:#e2e8f0; font-weight:600; }
    .wr-watch-list { display:flex; flex-direction:column; gap:6px; }
    .wr-watch-item {
      display:flex; align-items:center; justify-content:space-between;
      padding:8px 12px; border-radius:8px;
      background:rgba(182,157,116,.06); border:1px solid rgba(182,157,116,.12);
    }
    .wr-watch-name { font-size:14px; color:#e2e8f0; font-weight:600; }
    .wr-watch-rating { font-family:var(--mono,'monospace'); font-size:13px; color:#b69d74; }
    .wr-watch-status { font-size:11px; color:#b69d74; font-weight:600; }
    .wr-footer {
      display:flex; align-items:center; justify-content:space-between;
      padding-top:12px; border-top:1px solid rgba(255,255,255,.04);
      font-size:11px; color:#2d3748;
    }
    .wr-semaforo-row { display:flex; gap:12px; align-items:center; }
    .wr-semaforo { display:flex; align-items:center; gap:6px; }
    .wr-sem-dot { width:10px; height:10px; border-radius:50%; }
  `;
  document.head.appendChild(style);

  // Injeta HTML
  const overlay = document.createElement('div');
  overlay.id = 'warRoomOverlay';
  overlay.innerHTML = `
    <div class="wr-header">
      <div class="wr-logo">
        <div class="wr-logo-mark">D</div>
        <div>
          <div class="wr-logo-text">DOURO CAPITAL</div>
          <div class="wr-logo-sub">War Room · Comitê de Crédito</div>
        </div>
      </div>
      <div class="wr-datetime" id="wrDatetime"></div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="wr-hint">ESC ou Ctrl+Shift+R para fechar</span>
        <button class="wr-close" onclick="closeWarRoom()" title="Fechar">✕</button>
      </div>
    </div>
    <div class="wr-body">
      <div class="wr-kpi-row" id="wrKpiRow"></div>
      <div class="wr-middle">
        <div class="wr-panel">
          <div class="wr-panel-title">Maiores Exposições</div>
          <div class="wr-emissores-grid" id="wrEmissores"></div>
        </div>
        <div class="wr-panel">
          <div class="wr-panel-title">Watch · Em Análise · Monitoramento</div>
          <div class="wr-watch-list" id="wrWatchList"></div>
        </div>
      </div>
      <div class="wr-footer">
        <div class="wr-semaforo-row" id="wrSemaforo"></div>
        <span>Dados calculados em tempo real · Ctrl+Shift+R para alternar</span>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  // Relógio
  function _wrTick() {
    const el = document.getElementById('wrDatetime');
    if (!el) return;
    const now = new Date();
    el.innerHTML = now.toLocaleDateString('pt-BR',{weekday:'long',day:'2-digit',month:'long',year:'numeric'})
      + '<br>' + now.toLocaleTimeString('pt-BR');
  }

  function buildWarRoom() {
    const ativosBase = typeof ATIVOS !== 'undefined' ? ATIVOS : [];
    const ativos = ativosBase.filter(a => (a.saldo||0) > 0);
    const total  = ativos.reduce((s,a) => s+(a.saldo||0), 0);
    const STATUS_ANALISE = ['Em análise','Watch','Monitoramento'];
    const aprovados  = ativos.filter(a => a.Status==='Aprovado').reduce((s,a)=>s+(a.saldo||0),0);
    const reprovados = ativos.filter(a => a.Status==='Reprovado').reduce((s,a)=>s+(a.saldo||0),0);
    const analise    = ativos.filter(a => STATUS_ANALISE.includes(a.Status)).reduce((s,a)=>s+(a.saldo||0),0);
    const nEmissores = new Set(ativos.map(a=>a.emissor).filter(Boolean)).size;
    const durPond    = total>0 ? (ativos.reduce((s,a)=>s+(a.duration||0)*(a.saldo||0),0)/total).toFixed(1) : '—';
    const pctAprov   = total>0 ? (aprovados/total*100).toFixed(1) : '0.0';
    const pctReprov  = total>0 ? (reprovados/total*100).toFixed(1) : '0.0';
    const pctAnalise = total>0 ? (analise/total*100).toFixed(1) : '0.0';

    // KPIs
    const fM = v => v>=1e9 ? 'R$ '+(v/1e9).toFixed(1)+'B' : v>=1e6 ? 'R$ '+(v/1e6).toFixed(0)+'M' : 'R$ '+(v/1e3).toFixed(0)+'K';
    document.getElementById('wrKpiRow').innerHTML = `
      <div class="wr-kpi neutral">
        <div class="wr-kpi-label">Carteira Total</div>
        <div class="wr-kpi-value">${fM(total)}</div>
        <div class="wr-kpi-sub">${ativos.length} ativos · ${nEmissores} emissores</div>
      </div>
      <div class="wr-kpi green">
        <div class="wr-kpi-label">Aprovados</div>
        <div class="wr-kpi-value">${pctAprov}%</div>
        <div class="wr-kpi-badge green">▲ ${fM(aprovados)}</div>
      </div>
      <div class="wr-kpi ${parseFloat(pctReprov)>10?'red':'neutral'}">
        <div class="wr-kpi-label">Reprovados</div>
        <div class="wr-kpi-value">${pctReprov}%</div>
        <div class="wr-kpi-badge red">${fM(reprovados)}</div>
      </div>
      <div class="wr-kpi gold">
        <div class="wr-kpi-label">Em Análise / Watch</div>
        <div class="wr-kpi-value">${pctAnalise}%</div>
        <div class="wr-kpi-badge gold">${fM(analise)}</div>
      </div>
      <div class="wr-kpi neutral">
        <div class="wr-kpi-label">Duration Média</div>
        <div class="wr-kpi-value">${durPond}<span style="font-size:18px;color:#4a5568"> anos</span></div>
        <div class="wr-kpi-sub">Ponderada por saldo</div>
      </div>
    `;

    // Top emissores
    const byE = {};
    ativos.forEach(a => { byE[a.emissor||'S/N'] = (byE[a.emissor||'S/N']||0)+(a.saldo||0); });
    const topEm = Object.entries(byE).sort((a,b)=>b[1]-a[1]).slice(0,10);
    const corEm = em => {
      const st = (ativos.find(a=>a.emissor===em)?.Status||'').trim();
      if (st==='Aprovado')  return '#2fa874';
      if (st==='Reprovado') return '#d94141';
      return '#b69d74';
    };
    document.getElementById('wrEmissores').innerHTML = topEm.map(([em,v]) =>
      `<div class="wr-em-row">
        <div class="wr-em-dot" style="background:${corEm(em)}"></div>
        <div class="wr-em-name" title="${em}">${em}</div>
        <div class="wr-em-val">${fM(v)}</div>
      </div>`
    ).join('');

    // Watch list
    const watchAtivos = ativos.filter(a => STATUS_ANALISE.includes(a.Status));
    const byEW = {};
    watchAtivos.forEach(a => {
      if (!byEW[a.emissor]) byEW[a.emissor] = {saldo:0,status:a.Status,rating:a.ratingDouro||a.Rating||'—'};
      byEW[a.emissor].saldo += (a.saldo||0);
    });
    const watchItems = Object.entries(byEW).sort((a,b)=>b[1].saldo-a[1].saldo).slice(0,6);
    const wEl = document.getElementById('wrWatchList');
    if (watchItems.length===0) {
      wEl.innerHTML = '<div style="color:#2d3748;font-size:13px;padding:8px 0">Nenhum emissor em watch ou análise.</div>';
    } else {
      wEl.innerHTML = watchItems.map(([em,info]) =>
        `<div class="wr-watch-item">
          <div class="wr-watch-name">${em}</div>
          <div style="display:flex;gap:12px;align-items:center">
            <div class="wr-watch-rating">${info.rating}</div>
            <div class="wr-watch-status">${info.status}</div>
            <div class="wr-em-val" style="font-size:12px;color:#718096">${fM(info.saldo)}</div>
          </div>
        </div>`
      ).join('');
    }

    // Semáforo
    document.getElementById('wrSemaforo').innerHTML = `
      <div class="wr-semaforo"><div class="wr-sem-dot" style="background:#2fa874"></div><span style="color:#4a5568">Aprovado (${pctAprov}%)</span></div>
      <div class="wr-semaforo"><div class="wr-sem-dot" style="background:#b69d74"></div><span style="color:#4a5568">Watch/Análise (${pctAnalise}%)</span></div>
      <div class="wr-semaforo"><div class="wr-sem-dot" style="background:#d94141"></div><span style="color:#4a5568">Reprovado (${pctReprov}%)</span></div>
    `;
  }

  let _wrInterval = null;

  window.openWarRoom = function() {
    overlay.classList.add('open');
    buildWarRoom();
    _wrTick();
    _wrInterval = setInterval(_wrTick, 1000);
    document.body.style.overflow = 'hidden';
  };

  window.closeWarRoom = function() {
    overlay.classList.remove('open');
    clearInterval(_wrInterval);
    document.body.style.overflow = '';
  };

  document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.shiftKey && e.key === 'R') {
      e.preventDefault();
      overlay.classList.contains('open') ? closeWarRoom() : openWarRoom();
    }
    if (e.key === 'Escape' && overlay.classList.contains('open')) {
      closeWarRoom();
    }
  });
})();

// ── HIDDEN FEATURES CSS BASE ──────────────────────────────────────────────
// ── BUSCA GLOBAL (Ctrl+P) ─────────────────────────────────────────────────
(function() {
  const _css = `
    #gspBackdrop {
      display:none; position:fixed; inset:0; z-index:10000;
      background:rgba(5,8,16,.72); backdrop-filter:blur(6px);
      align-items:flex-start; justify-content:center; padding-top:12vh;
    }
    #gspBackdrop.open { display:flex; }
    #gspModal {
      width:min(680px,92vw); background:#0f1623;
      border:1px solid rgba(182,157,116,.25); border-radius:18px;
      box-shadow:0 32px 80px rgba(0,0,0,.7), 0 0 0 1px rgba(255,255,255,.04);
      overflow:hidden; animation:gspIn .18s cubic-bezier(.16,1,.3,1);
    }
    @keyframes gspIn { from{opacity:0;transform:translateY(-16px) scale(.97)} to{opacity:1;transform:none} }
    #gspInputWrap {
      display:flex; align-items:center; gap:12px;
      padding:18px 22px; border-bottom:1px solid rgba(255,255,255,.06);
    }
    #gspIcon { color:#4a5568; font-size:18px; flex-shrink:0; }
    #gspInput {
      flex:1; background:transparent; border:none; outline:none;
      font-size:17px; color:#e2e8f0; font-family:var(--font,'Montserrat',sans-serif);
      font-weight:500;
    }
    #gspInput::placeholder { color:#2d3748; }
    #gspKbd {
      font-size:10px; color:#2d3748; background:rgba(255,255,255,.04);
      border:1px solid rgba(255,255,255,.08); border-radius:5px;
      padding:2px 7px; font-family:var(--mono,'monospace'); white-space:nowrap;
    }
    #gspResults {
      max-height:420px; overflow-y:auto; padding:8px 0;
    }
    #gspResults::-webkit-scrollbar { width:4px; }
    #gspResults::-webkit-scrollbar-track { background:transparent; }
    #gspResults::-webkit-scrollbar-thumb { background:rgba(182,157,116,.2); border-radius:2px; }
    .gsp-section-label {
      font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:.12em;
      color:#2d3748; padding:10px 22px 4px; pointer-events:none;
    }
    .gsp-item {
      display:flex; align-items:center; gap:14px;
      padding:10px 22px; cursor:pointer; transition:background .1s;
      border-radius:0;
    }
    .gsp-item:hover, .gsp-item.active {
      background:rgba(182,157,116,.08);
    }
    .gsp-item-icon {
      width:34px; height:34px; border-radius:9px; flex-shrink:0;
      display:flex; align-items:center; justify-content:center;
      font-size:14px; font-weight:700;
    }
    .gsp-item-main { flex:1; min-width:0; }
    .gsp-item-title {
      font-size:13.5px; font-weight:600; color:#e2e8f0;
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    }
    .gsp-item-sub { font-size:11px; color:#4a5568; margin-top:1px; }
    .gsp-item-right { display:flex; flex-direction:column; align-items:flex-end; gap:4px; }
    .gsp-badge {
      font-size:10px; font-weight:700; padding:2px 8px; border-radius:4px;
      font-family:var(--mono,'monospace');
    }
    .gsp-badge.green  { background:rgba(47,168,116,.15); color:#2fa874; }
    .gsp-badge.red    { background:rgba(217,65,65,.15);  color:#d94141; }
    .gsp-badge.gold   { background:rgba(182,157,116,.15);color:#b69d74; }
    .gsp-badge.blue   { background:rgba(49,116,184,.15); color:#3174b8; }
    .gsp-badge.gray   { background:rgba(74,85,104,.15);  color:#718096; }
    .gsp-item-saldo { font-family:var(--mono,'monospace'); font-size:12px; color:#718096; }
    #gspFooter {
      display:flex; align-items:center; gap:16px;
      padding:10px 22px; border-top:1px solid rgba(255,255,255,.04);
      font-size:10.5px; color:#2d3748;
    }
    .gsp-key {
      display:inline-flex; align-items:center; gap:4px;
    }
    .gsp-key kbd {
      background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.1);
      border-radius:4px; padding:1px 6px; font-size:10px;
      font-family:var(--mono,'monospace'); color:#4a5568;
    }
    #gspEmpty {
      padding:32px 22px; text-align:center;
      color:#2d3748; font-size:13px;
    }
  `;
  const st = document.createElement('style');
  st.textContent = _css;
  document.head.appendChild(st);

  const html = `
    <div id="gspBackdrop" onclick="_gspClose(event)">
      <div id="gspModal">
        <div id="gspInputWrap">
          <span id="gspIcon">⌕</span>
          <input id="gspInput" placeholder="Buscar emissor, banco, aba…" autocomplete="off" spellcheck="false"/>
          <span id="gspKbd">Ctrl+P</span>
        </div>
        <div id="gspResults"></div>
        <div id="gspFooter">
          <span class="gsp-key"><kbd>↑↓</kbd> navegar</span>
          <span class="gsp-key"><kbd>↵</kbd> abrir</span>
          <span class="gsp-key"><kbd>ESC</kbd> fechar</span>
          <span style="margin-left:auto">Ctrl+P para abrir a qualquer momento</span>
        </div>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);

  const PAGES = [
    { id:'home',        label:'Panorama Geral',          icon:'🏠', color:'#1f2839' },
    { id:'composicao',  label:'Composição da Carteira',  icon:'◎',  color:'#00677b' },
    { id:'rating',      label:'Rating & Status',         icon:'★',  color:'#b69d74' },
    { id:'performance', label:'Performance',             icon:'↗',  color:'#2fa874' },
    { id:'spreads',     label:'Spreads',                 icon:'~',  color:'#3174b8' },
    { id:'tunel',       label:'Túnel do Tempo',          icon:'⧖',  color:'#a78bd4' },
    { id:'bonds',       label:'Bonds & Eurobonds',       icon:'$',  color:'#e0c44a' },
    { id:'financeiros', label:'Fundamentos Financeiros', icon:'∑',  color:'#d47aa7' },
    { id:'bancos',      label:'Bancos',                  icon:'⬡',  color:'#5ab8d4' },
    { id:'scorecard',   label:'Scorecard de Crédito',    icon:'✓',  color:'#60b85a' },
    { id:'douro-news',  label:'Douro News',              icon:'◉',  color:'#d94141' },
  ];

  let _idx = 0;
  let _items = [];

  function _badgeCls(status) {
    if (!status) return 'gray';
    const s = status.toLowerCase();
    if (s==='aprovado') return 'green';
    if (s==='reprovado') return 'red';
    if (s.includes('análise')||s==='watch'||s==='monitoramento') return 'gold';
    return 'gray';
  }

  function _fmtSaldo(v) {
    if (!v) return '';
    return v>=1e9 ? 'R$'+(v/1e9).toFixed(1)+'B' : v>=1e6 ? 'R$'+(v/1e6).toFixed(0)+'M' : 'R$'+(v/1e3).toFixed(0)+'K';
  }

  function _buildItems(q) {
    const out = [];
    const qn = q.toLowerCase().trim();

    // Abas
    const pages = qn ? PAGES.filter(p => p.label.toLowerCase().includes(qn) || p.id.includes(qn)) : PAGES;
    pages.forEach(p => out.push({ type:'page', data:p }));

    if (!qn) return out;

    // Emissores corporativos (RANK_CORP)
    const corps = (typeof RANK_CORP!=='undefined'?RANK_CORP:[])
      .filter(r => r.empresa && r.empresa.toLowerCase().includes(qn))
      .slice(0,8);
    corps.forEach(r => {
      const byE = (typeof ATIVOS!=='undefined'?ATIVOS:[]).filter(a=>a.emissor===r.empresa&&(a.saldo||0)>0);
      const saldo = byE.reduce((s,a)=>s+(a.saldo||0),0);
      out.push({ type:'corp', data:r, saldo });
    });

    // Bancos (RANK_BANCOS)
    const banks = (typeof RANK_BANCOS!=='undefined'?RANK_BANCOS:[])
      .filter(r => r.empresa && r.empresa.toLowerCase().includes(qn))
      .slice(0,5);
    banks.forEach(r => out.push({ type:'banco', data:r }));

    return out;
  }

  function _render(q) {
    _items = _buildItems(q);
    _idx = 0;
    const el = document.getElementById('gspResults');
    if (!_items.length) {
      el.innerHTML = '<div id="gspEmpty">Nenhum resultado para <strong style="color:#e2e8f0">"' + q + '"</strong></div>';
      return;
    }
    let html = '';
    let lastType = null;
    _items.forEach((it, i) => {
      if (it.type !== lastType) {
        const labels = { page:'Abas', corp:'Emissores Corporativos', banco:'Bancos' };
        html += `<div class="gsp-section-label">${labels[it.type]||''}</div>`;
        lastType = it.type;
      }
      if (it.type==='page') {
        const p = it.data;
        html += `<div class="gsp-item${i===_idx?' active':''}" data-idx="${i}" onclick="_gspSelect(${i})">
          <div class="gsp-item-icon" style="background:${p.color}22;color:${p.color};font-size:16px">${p.icon}</div>
          <div class="gsp-item-main">
            <div class="gsp-item-title">${p.label}</div>
            <div class="gsp-item-sub">Aba do dashboard</div>
          </div>
          <div class="gsp-item-right"><span class="gsp-badge blue">Página</span></div>
        </div>`;
      } else if (it.type==='corp') {
        const r = it.data;
        html += `<div class="gsp-item${i===_idx?' active':''}" data-idx="${i}" onclick="_gspSelect(${i})">
          <div class="gsp-item-icon" style="background:rgba(182,157,116,.1);color:#b69d74;font-size:12px;font-weight:800">${r.empresa.substring(0,2).toUpperCase()}</div>
          <div class="gsp-item-main">
            <div class="gsp-item-title">${r.empresa}</div>
            <div class="gsp-item-sub">${r.setor||'Corporativo'} · ${r.ratingMkt||'—'}</div>
          </div>
          <div class="gsp-item-right">
            <span class="gsp-badge ${_badgeCls(r.status)}">${r.status||'—'}</span>
            ${it.saldo ? `<span class="gsp-item-saldo">${_fmtSaldo(it.saldo)}</span>` : ''}
          </div>
        </div>`;
      } else {
        const r = it.data;
        html += `<div class="gsp-item${i===_idx?' active':''}" data-idx="${i}" onclick="_gspSelect(${i})">
          <div class="gsp-item-icon" style="background:rgba(91,184,212,.1);color:#5ab8d4;font-size:12px;font-weight:800">${r.empresa.substring(0,2).toUpperCase()}</div>
          <div class="gsp-item-main">
            <div class="gsp-item-title">${r.empresa}</div>
            <div class="gsp-item-sub">Banco · ${r.ratingDouro||'—'}</div>
          </div>
          <div class="gsp-item-right">
            <span class="gsp-badge ${_badgeCls(r.status)}">${r.status||'—'}</span>
          </div>
        </div>`;
      }
    });
    el.innerHTML = html;
  }

  function _setActive(i) {
    _idx = i;
    document.querySelectorAll('.gsp-item').forEach((el,j) => el.classList.toggle('active', j===i));
    const active = document.querySelector('.gsp-item.active');
    if (active) active.scrollIntoView({block:'nearest'});
  }

  window._gspSelect = function(i) {
    if (i===undefined) i = _idx;
    const it = _items[i];
    if (!it) return;
    _forceClose();
    if (it.type==='page') {
      showPage(it.data.id, document.querySelector('.nav-item[onclick*="' + it.data.id + '"]'));
    } else if (it.type==='corp') {
      // Mesma lógica de homeSelectEmp()
      showPage('fundamentos', document.querySelector('.nav-item[onclick*="fundamentos"]'));
      setTimeout(()=>{
        const sel = document.getElementById('fundEmpSel');
        if (sel) { sel.value = it.data.empresa; sel.dispatchEvent(new Event('change')); }
      }, 110);
    } else if (it.type==='banco') {
      // Mesma lógica de homeSelectBanco()
      showPage('bancos', document.querySelector('.nav-item[onclick*="bancos"]'));
      setTimeout(()=>{
        const sel = document.getElementById('bancosEmpSel');
        if (sel) { sel.value = it.data.empresa; sel.dispatchEvent(new Event('change')); }
        if (typeof buildBancos==='function') buildBancos(it.data.empresa);
      }, 110);
    }
  };

  function _gspOpen() {
    document.getElementById('gspBackdrop').classList.add('open');
    const inp = document.getElementById('gspInput');
    inp.value = '';
    _render('');
    setTimeout(()=>inp.focus(), 30);
  }

  window._gspClose = function(e) {
    if (e && e.target !== document.getElementById('gspBackdrop')) return;
    document.getElementById('gspBackdrop').classList.remove('open');
  };
  function _forceClose() { document.getElementById('gspBackdrop').classList.remove('open'); }

  document.getElementById('gspInput').addEventListener('input', e => _render(e.target.value));
  document.getElementById('gspInput').addEventListener('keydown', e => {
    if (e.key==='ArrowDown') { e.preventDefault(); _setActive(Math.min(_idx+1,_items.length-1)); }
    else if (e.key==='ArrowUp') { e.preventDefault(); _setActive(Math.max(_idx-1,0)); }
    else if (e.key==='Enter') { e.preventDefault(); _gspSelect(_idx); }
    else if (e.key==='Escape') { _forceClose(); }
  });

  document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.key==='p') { e.preventDefault(); _gspOpen(); }
    if (e.key==='Escape') _forceClose();
  });
})();

<!--HIDDEN_FEATURES-->