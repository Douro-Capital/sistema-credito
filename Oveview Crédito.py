# =========================================
# PATCH A — imports
# =========================================
import asyncio
import aiohttp
import requests          # mantido para compatibilidade residual
import pandas as pd
import zipfile
import io
import numpy as np
import json
import os
import webbrowser
import ssl
import urllib3
import base64
import re
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ──────────────────────────────────────────────────────────────────────────────
# DOURO NEWS — PIPELINE INTERNO
# ──────────────────────────────────────────────────────────────────────────────
import time, random, unicodedata
from datetime import datetime, timezone
from dataclasses import dataclass, field

try:
    import feedparser as _fp; _HAS_FP = True
except ImportError:
    _HAS_FP = False

try:
    import yfinance as _yf; _HAS_YF = True
except ImportError:
    _HAS_YF = False

_NSRC = {
    "neofeed":        "https://neofeed.com.br/feed/",
    "infomoney":      "https://www.infomoney.com.br/feed/",
    "reuters_br":     "https://feeds.reuters.com/reuters/BRbusinessNews",
    "brazil_journal": "https://braziljournal.com/feed/",
}
_NW = {"brazil_journal":1.5,"neofeed":1.5,"reuters_br":1.2,"infomoney":1.0}
_EMPS = [
    "Rede Dor","Equatorial","Raízen","Klabin","JSL","Energisa","Eletrobras","Minerva",
    "Allos","Petrobras","Rumo","Engie","Eneva","Vamos","M. Dias Branco","JBS",
    "Localiza","Movida","Suzano","Taesa","Hapvida","São Martinho","Vibra","Prio",
    "Braskem","Alupar","Copasa","Dasa","Assaí","Casas Bahia","Vale","Brk Ambiental",
    "Ipiranga","CCR","Auren","Cemig","Omega Energia","CPFL","Copel","Cosan","CSN",
    "Direcional","Simpar","Ecorodovias","Sanepar","Grupo Mateus","Hidrovias","SABESP",
    "Iguatemi","Light","Marfrig","MRV","Oncoclinicas","Neoenergia","Dexco","Camil",
    "V.tal","Multiplan","JHSF","MRS","Aegea","Votorantim","FS Bioenergia",
]
_NKWS = {
    "Macro":    ["inflacao","ipca","igp","juros","selic","copom","pib","fiscal","deficit",
                 "divida publica","arrecadacao","superavit","commodities","banco central"],
    "Política": ["governo","congresso","senado","reforma tributaria","arcabouco fiscal",
                 "ministerio","lula","haddad","tesouro","privatizacao","regulacao"],
    "Mercados": ["bolsa","ibovespa","dolar","cambio","juros futuros","debenture","emissao"],
}
_NINS = [
    {"g":"Howard Marks","i":"You can't predict. You can prepare."},
    {"g":"Warren Buffett","i":"Price is what you pay. Value is what you get."},
    {"g":"Charlie Munger","i":"Invert, always invert."},
    {"g":"Luis Stuhlberger","i":"O mercado é um mestre severo que te obriga a repensar suas convicções todos os dias."},
    {"g":"Ray Dalio","i":"He who lives by the crystal ball will eat shattered glass."},
    {"g":"Peter Lynch","i":"Know what you own, and know why you own it."},
    {"g":"Benjamin Graham","i":"In the short run, the market is a voting machine but in the long run it is a weighing machine."},
    {"g":"Armínio Fraga","i":"Estabilidade macroeconômica é condição necessária para crescimento sustentável."},
    {"g":"Henrique Bredda","i":"Liquidez não resolve problema de fundamento."},
    {"g":"Stanley Druckenmiller","i":"It's not whether you're right or wrong, but how much you make when you're right and how much you lose when you're wrong."},
    {"g":"John Templeton","i":"The four most dangerous words in investing are: this time it's different."},
    {"g":"George Soros","i":"I am only rich because I know when I am wrong."},
    {"g":"Aswath Damodaran","i":"Every valuation is a story combined with numbers."},
]
_NLIV = [
    {"t":"O Investidor Inteligente","a":"Benjamin Graham","d":"A bíblia do value investing e gestão de risco."},
    {"t":"A Lógica do Cisne Negro","a":"Nassim Taleb","d":"Como lidar com o impacto do altamente improvável."},
    {"t":"O Mais Importante para o Investidor","a":"Howard Marks","d":"Insights raros sobre ciclos de mercado e risco."},
    {"t":"A Psicologia Financeira","a":"Morgan Housel","d":"Por que o comportamento importa mais que a matemática."},
    {"t":"Mastering the Market Cycle","a":"Howard Marks","d":"Understanding the patterns that dictate market moves."},
    {"t":"Avaliando Empresas","a":"Aswath Damodaran","d":"O guia definitivo de valuation pelo mestre de NYU."},
    {"t":"Antifrágil","a":"Nassim Taleb","d":"Coisas que se beneficiam do caos e da desordem."},
    {"t":"Princípios","a":"Ray Dalio","d":"As regras de vida e trabalho do fundador da Bridgewater."},
]
_NFIL = [
    {"t":"The Big Short","c":"Crise/Macro","i":"Incentivos desalinhados criam bolhas e colapsos"},
    {"t":"Margin Call","c":"Risco","i":"Gestão de risco sob pressão define sobrevivência"},
    {"t":"Moneyball","c":"Dados","i":"Edge vem de informação mal precificada"},
    {"t":"Inside Job","c":"Crise 2008","i":"Sistema financeiro interligado amplifica riscos"},
    {"t":"The Wizard of Lies","c":"Fraude","i":"Confiança é o ativo mais valioso do mercado"},
    {"t":"Billions","c":"Hedge Fund","i":"Estratégia, poder e regulação"},
    {"t":"Succession","c":"Poder","i":"Governança e conflitos de controle"},
    {"t":"Industry","c":"Carreira","i":"Alta performance no mercado financeiro"},
]

@dataclass
class _N:
    titulo: str; link: str; fonte: str; timestamp: datetime
    categorias: list = field(default_factory=list)
    tickers:    list = field(default_factory=list)
    score:      float = 0.0

def _nn(t):
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in t if unicodedata.category(c)!="Mn")).strip()

def _rss(nome, url):
    if not _HAS_FP: return []
    try:
        out = []
        for e in _fp.parse(url).entries[:20]:
            ti = e.get("title","").strip(); lk = e.get("link","").strip()
            if not (ti and lk): continue
            tp = e.get("published_parsed") or e.get("updated_parsed")
            ts = datetime(*tp[:6], tzinfo=timezone.utc) if tp else datetime.now(timezone.utc)
            out.append(_N(titulo=ti, link=lk, fonte=nome, timestamp=ts))
        return out
    except Exception: return []

def _coletar():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    out = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for f in as_completed([ex.submit(_rss, n, u) for n, u in _NSRC.items()]):
            try: out.extend(f.result())
            except Exception: pass
    return out

def _classif(n):
    t = _nn(n.titulo); cats = []
    for emp in _EMPS:
        if re.search(r'\b'+re.escape(_nn(emp))+r'\b', t):
            cats.append("Empresas")
            if emp.upper() not in n.tickers: n.tickers.append(emp.upper())
            break
    for cat, kws in _NKWS.items():
        if any(k in t for k in kws): cats.append(cat)
    n.categorias = cats or ["Geral"]; return n

def _score(n):
    h = (datetime.now(timezone.utc) - n.timestamp).total_seconds() / 3600
    if h > 24: n.score = -1.0; return n.score
    tl = n.titulo.lower()
    if any(r in tl for r in ["ibovespa hoje","dolar hoje","ao vivo","tempo real"]): n.score = -1.0; return n.score
    s = _NW.get(n.fonte, 1.0)
    if re.search(r"r\$\s*[\d,.]+([ ]*(bi|mi|tri))", tl): s += 2.5
    elif re.search(r"\d+[,.]?\d*\s*%", tl): s += 1.5
    if any(v in tl for v in ["anuncia","aprova","corta","eleva","suspende","emite","lucro",
                               "prejuizo","resultado","guidance","rebaixa","upgrade","downgrade"]): s += 1.5
    if "Empresas" in n.categorias: s += 1.0
    s += 1.0 if h <= 12 else (-0.5 if h > 20 else 0)
    n.score = round(s,2); return n.score

def _dedup(ns, thresh=0.65):
    vs = []; r = []
    for n in sorted(ns, key=lambda x: x.score, reverse=True):
        t = set(_nn(n.titulo).split())
        if not any(len(t&v)/max(len(t|v),1)>=thresh for v in vs):
            vs.append(t); r.append(n)
    return r

def _mkt():
    c = {"ibov":"—","ibov_var":"—","ibov_up":True,"dolar":"—","dolar_var":"—",
         "dolar_up":False,"wti":"—","wti_var":"—","wti_up":False}
    if not _HAS_YF: return c
    try:
        ib = _yf.Ticker("^BVSP").fast_info; iv,ip = ib.last_price,ib.previous_close; ivar=(iv-ip)/ip*100
        dl = _yf.Ticker("BRL=X").fast_info; dv,dp = dl.last_price,dl.previous_close; dvar=(dv-dp)/dp*100
        c.update({"ibov":f"{iv:,.0f}".replace(",","."),"ibov_var":f"{ivar:+.2f}%","ibov_up":ivar>=0,
                  "dolar":f"R$ {dv:.2f}","dolar_var":f"{dvar:+.2f}%","dolar_up":dvar>=0})
        try:
            w=_yf.Ticker("CL=F").fast_info; wv=w.last_price; wvar=(wv-w.previous_close)/w.previous_close*100
            c.update({"wti":f"US$ {wv:.2f}","wti_var":f"{wvar:+.2f}%","wti_up":wvar>=0})
        except Exception: pass
    except Exception as e: print(f"[Douro News] Mercado: {e}")
    return c

def _getrf():
    r = {
        "di_curto":{"n":"DI Jan 27","t":"N/D"},"di_medio":{"n":"DI Jan 29","t":"N/D"},
        "di_longo":{"n":"DI Jan 33","t":"N/D"},"ntnb_curta":{"n":"B5P211 (Curta)","t":"N/D"},
        "ntnb_media":{"n":"IMAB11 (Geral)","t":"N/D"},"ntnb_longa":{"n":"B5MB11 (Longa)","t":"N/D"},
    }
    DM = {"DI1F27":"di_curto","DI1F29":"di_medio","DI1F33":"di_longo"}
    try:
        resp = requests.get("https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/DI1",
                            headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        for item in (resp.json().get("Scty") or []):
            sym = str(item.get("symb","")).upper()
            if sym in DM:
                qtn = item.get("SctyQtn",{}); taxa = qtn.get("curPrc") or qtn.get("curPric")
                if taxa: r[DM[sym]]["t"] = f"{float(str(taxa).replace(',','.')):.2f}%".replace(".",",")
    except Exception: pass
    if _HAS_YF:
        for etf,k in [("B5P211.SA","ntnb_curta"),("IMAB11.SA","ntnb_media"),("B5MB11.SA","ntnb_longa")]:
            try:
                dfe = _yf.Ticker(etf).history(period="5d")
                if len(dfe)>=2:
                    var=(dfe["Close"].iloc[-1]/dfe["Close"].iloc[-2]-1)*100
                    r[k]["t"]=f"{var:+.2f}%".replace(".",",")
            except Exception: pass
    return r

def _make_news_html(nd, logo_tag):
    from collections import defaultdict as _dd
    ctx=nd.get("ctx",{}); rf_=nd.get("rf",{}); ins=nd.get("insight",{})
    liv=nd.get("livro",{}); fil=nd.get("filme"); nots=nd.get("noticias",[])
    ORDEM=["Empresas","Macro","Mercados","Política","Geral"]
    LIMITS={"Empresas":6,"Macro":4,"Mercados":3,"Política":3,"Geral":2}
    by_cat=_dd(list)
    for nit in nots:
        seen=set()
        for cat in (nit.get("categorias") or ["Geral"]):
            if cat not in seen: by_cat[cat].append(nit); seen.add(cat)
    def _cd(n):
        cat=(n.get("tickers") or [""])[0] or (n.get("categorias") or ["Destaque"])[0]
        return (f'<div style="background:#1f2839;border-radius:8px;padding:20px 22px;margin-bottom:10px">'
                f'<div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:700;margin-bottom:8px">{cat}</div>'
                f'<div style="font-size:15px;font-weight:600;color:#fff;line-height:1.55;margin-bottom:12px">{n["titulo"]}</div>'
                f'<div style="display:flex;align-items:center;justify-content:space-between;">'
                f'<span style="font-size:11px;color:#d5d8c9;opacity:.5">{n["fonte"]}</span>'
                f'<a href="{n["link"]}" target="_blank" style="font-size:11px;color:#b69d74;text-decoration:none">ler →</a>'
                f'</div></div>')
    def _cs(n):
        cat=(n.get("tickers") or [""])[0] or ""
        cd=f'<div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:6px">{cat}</div>' if cat else ""
        return (f'<div style="background:#fff;border-radius:8px;padding:16px 18px;margin-bottom:8px;border:0.5px solid #e6e6de">'
                f'{cd}<div style="font-size:13.5px;font-weight:500;color:#1f2839;line-height:1.6;margin-bottom:10px">{n["titulo"]}</div>'
                f'<div style="display:flex;align-items:center;justify-content:space-between;">'
                f'<span style="font-size:11px;color:#4a5051;opacity:.5">{n["fonte"]}</span>'
                f'<a href="{n["link"]}" target="_blank" style="font-size:11px;color:#4a5051;opacity:.55;text-decoration:none">ler →</a>'
                f'</div></div>')
    parts=[]
    for cat in ORDEM:
        items=by_cat.get(cat,[])[:LIMITS.get(cat,3)]
        if not items: continue
        cards="".join([_cd(items[0])]+[_cs(x) for x in items[1:]])
        parts.append(f'<div style="margin-top:32px"><div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">'
                     f'<div style="width:4px;height:4px;border-radius:50%;background:#b69d74;flex-shrink:0"></div>'
                     f'<span style="font-size:10px;font-weight:600;letter-spacing:2.8px;text-transform:uppercase;color:#1f2839;opacity:.7">{cat}</span>'
                     f'<div style="flex:1;height:1px;background:#1f2839;opacity:.08"></div></div>{cards}</div>')
    news_body="".join(parts) or '<p style="color:#718096;font-style:italic;text-align:center;padding:40px">Nenhuma notícia disponível.</p>'
    ic=lambda up:"#2fa874" if up else "#d94141"
    wti_blk=(f'<div style="display:flex;flex-direction:column;gap:4px">'
             f'<span style="font-size:9px;letter-spacing:1.8px;text-transform:uppercase;color:#d5d8c9;opacity:.45">Petróleo WTI</span>'
             f'<span style="font-size:14px;font-weight:500;color:#fff">{ctx.get("wti","—")} '
             f'<span style="color:{ic(ctx.get("wti_up"))};font-size:11px">{ctx.get("wti_var","—")}</span></span></div>'
             ) if ctx.get("wti","—")!="—" else ""
    def rfrow(label,taxa):
        return (f'<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:10px">'
                f'<span style="color:#1f2839;font-weight:500;opacity:.8">{label}</span>'
                f'<span style="font-weight:700">{taxa}</span></div>')
    def rfget(k,fn,ft):
        o=rf_.get(k,{}); return rfrow(o.get("n",fn),o.get("t",ft))
    di_rows ="".join([rfget("di_curto","DI Jan 27","N/D"),rfget("di_medio","DI Jan 29","N/D"),rfget("di_longo","DI Jan 33","N/D")])
    nb_rows ="".join([rfget("ntnb_curta","B5P211 (Curta)","N/D"),rfget("ntnb_media","IMAB11 (Geral)","N/D"),rfget("ntnb_longa","B5MB11 (Longa)","N/D")])
    filme_blk=(f'<div style="background:#fff;padding:22px 24px;border-radius:8px;margin-top:12px;border-left:3px solid #b69d74">'
               f'<div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:14px">Dica de Fim de Semana</div>'
               f'<div style="font-size:16px;font-weight:700;color:#1f2839;margin-bottom:4px">{fil["titulo"]}</div>'
               f'<div style="font-size:12px;color:#4a5051;margin-bottom:10px;opacity:.7">{fil["categoria"]}</div>'
               f'<div style="font-size:13px;line-height:1.6;opacity:.8">{fil["insight"]}</div></div>') if fil else ""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Douro News — {nd.get("data","")}</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Montserrat',sans-serif;background:#f5f5ef;color:#1f2839;-webkit-font-smoothing:antialiased}}
.w{{max-width:680px;margin:0 auto;background:#f5f5ef}}
.rf{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
@media(max-width:520px){{.rf{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="w">
<div style="background:#1f2839;padding:28px 40px 24px">{logo_tag}
  <div style="font-size:11px;color:#d5d8c9;opacity:.4;letter-spacing:.4px;margin-top:14px">{nd.get("dia","")}, {nd.get("data","")} · Edição diária</div>
</div>
<div style="background:#fff;padding:28px 40px;border-bottom:1px solid #ebebE3">
  <p style="font-size:14px;line-height:1.8;font-style:italic;font-weight:500;margin-bottom:6px">"{ins.get("insight","")}"</p>
  <p style="font-size:13px;color:#4a5051">— {ins.get("gestor","")}</p>
</div>
<div style="background:#1f2839;padding:14px 40px;display:flex;gap:36px;flex-wrap:wrap">
  <div style="display:flex;flex-direction:column;gap:4px">
    <span style="font-size:9px;letter-spacing:1.8px;text-transform:uppercase;color:#d5d8c9;opacity:.45">Ibovespa</span>
    <span style="font-size:14px;font-weight:500;color:#fff">{ctx.get("ibov","—")} <span style="color:{ic(ctx.get("ibov_up"))};font-size:11px">{ctx.get("ibov_var","—")}</span></span>
  </div>
  <div style="display:flex;flex-direction:column;gap:4px">
    <span style="font-size:9px;letter-spacing:1.8px;text-transform:uppercase;color:#d5d8c9;opacity:.45">Dólar</span>
    <span style="font-size:14px;font-weight:500;color:#fff">{ctx.get("dolar","—")} <span style="color:{ic(ctx.get("dolar_up"))};font-size:11px">{ctx.get("dolar_var","—")}</span></span>
  </div>
  {wti_blk}
</div>
<div style="padding:8px 40px 44px">
  {news_body}
  <div style="margin-top:32px">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
      <div style="width:4px;height:4px;border-radius:50%;background:#b69d74;flex-shrink:0"></div>
      <span style="font-size:10px;font-weight:600;letter-spacing:2.8px;text-transform:uppercase;color:#1f2839;opacity:.7">Termômetro Renda Fixa</span>
      <div style="flex:1;height:1px;background:#1f2839;opacity:.08"></div>
    </div>
    <div class="rf">
      <div style="background:#fff;padding:18px 20px;border-radius:8px;border:0.5px solid #e6e6de">
        <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:12px">Curva DI Futuro</div>{di_rows}
      </div>
      <div style="background:#fff;padding:18px 20px;border-radius:8px;border:0.5px solid #e6e6de">
        <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:12px">Curva Real (ETFs)</div>{nb_rows}
      </div>
    </div>
  </div>
  <div style="margin-top:20px">
    <div style="background:#fff;padding:22px 24px;border-radius:8px;border-left:3px solid #b69d74">
      <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:14px">Literatura da Semana</div>
      <div style="font-size:16px;font-weight:700;color:#1f2839;margin-bottom:4px">{liv.get("titulo","—")}</div>
      <div style="font-size:12px;color:#4a5051;margin-bottom:10px;opacity:.7">por {liv.get("autor","—")}</div>
      <div style="font-size:13px;line-height:1.6;opacity:.8">{liv.get("desc","")}</div>
    </div>{filme_blk}
  </div>
</div>
<div style="background:#1f2839;padding:18px 40px;display:flex;justify-content:space-between;align-items:center">
  <span style="font-size:14px;color:#b69d74;font-weight:700;letter-spacing:1px">Douro Capital</span>
  <span style="font-size:11px;color:#d5d8c9;opacity:.35">Distribuição privada · {nd.get("hora","")} BRT</span>
</div>
</div></body></html>"""

def _news_pipeline():
    print("[Douro News] Coletando via RSS...")
    raw = _coletar()
    ns = [_classif(n) for n in raw]
    ns = [n for n in ns if _score(n) > 0]
    ns = _dedup(ns)
    print(f"[Douro News] {len(ns)} notícias curadas de {len(raw)} coletadas.")
    agora = datetime.now()
    random.seed(agora.toordinal());    ins = random.choice(_NINS)
    random.seed(agora.isocalendar()[1]); liv = random.choice(_NLIV)
    fil = random.choice(_NFIL) if agora.weekday() == 4 else None
    random.seed(time.time())
    return {
        "noticias": [{"titulo":n.titulo,"link":n.link,"fonte":n.fonte,
                      "timestamp":n.timestamp.isoformat(),
                      "categorias":n.categorias,"tickers":n.tickers,"score":n.score} for n in ns],
        "ctx":  _mkt(), "rf": _getrf(),
        "insight": {"gestor":ins["g"],"insight":ins["i"]},
        "livro":   {"titulo":liv["t"],"autor":liv["a"],"desc":liv["d"]},
        "filme":   ({"titulo":fil["t"],"categoria":fil["c"],"insight":fil["i"]} if fil else None),
        "data": agora.strftime("%d/%m/%Y"),
        "dia":  ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"][agora.weekday()],
        "hora": agora.strftime("%H:%M"),
    }

# =========================================
# SELEÇÃO DE MODO
# =========================================
import sys
print("\n" + "═"*48)
print("  DOURO CAPITAL — Overview de Crédito")
print("═"*48)
print("  [1]  Rodar completo  (dados + HTML)")
print("  [2]  Apenas Douro News  (rápido)")
print("  [3]  Modo offline    (sem ComDinheiro)")
print("═"*48)
_modo = input("  Selecione o modo: ").strip()
while _modo not in ("1", "2", "3"):
    _modo = input("  Opção inválida. Digite 1, 2 ou 3: ").strip()
MODO_COMPLETO = (_modo == "1")
MODO_OFFLINE  = (_modo == "3")
print("═"*48 + "\n")

if MODO_OFFLINE:
    # Modo offline: pula extração do ComDinheiro, lê Excel já salvos
    import glob as _glob
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    BASE_INV  = os.path.abspath(os.path.join(_script_dir, "..", "..", "..", ".."))
    _proc_cands = _glob.glob(os.path.join(os.path.dirname(BASE_INV), "*Processos*"))
    BASE_PROC = _proc_cands[0] if _proc_cands else os.path.join(os.path.dirname(BASE_INV), "Douro - Processos")
    _PLANILHAS_OV = os.path.join(BASE_INV, r"Análise de Crédito\Comitê de acompanhamento\Overview Plataforma\Planilhas Overview")
    print(f"  Usuario: {os.path.basename(os.path.expanduser('~'))}")
    print(f"  Base: {BASE_INV}\n")

    print("=" * 52)
    print("  [OFFLINE] Carregando Excel salvos anteriormente...")
    print(f"            Origem: {_PLANILHAS_OV}")
    print("=" * 52)
    _arquivos_offline = {
        "dados_carteiras_credito": "dados_carteiras_credito1.xlsx",
        "dados_carteiras":         "dados_carteiras1.xlsx",
        "dados_bonds":             "dados_bonds1.xlsx",
        "dados_cp":                "dados_cp1.xlsx",
    }
    _offline_ok = True
    for _nome_off, _arq_off in _arquivos_offline.items():
        _path_off = os.path.join(_PLANILHAS_OV, _arq_off)
        if not os.path.exists(_path_off):
            print(f"  ✗ Arquivo não encontrado: {_arq_off}")
            _offline_ok = False
    if not _offline_ok:
        print("\n  ERRO: um ou mais arquivos offline estao ausentes.")
        print("  Execute o modo [1] ao menos uma vez com a API funcionando.")
        sys.exit(1)

    dados_carteiras_credito = pd.read_excel(os.path.join(_PLANILHAS_OV, "dados_carteiras_credito1.xlsx"))
    dados_carteiras         = pd.read_excel(os.path.join(_PLANILHAS_OV, "dados_carteiras1.xlsx"))
    dados_bonds             = pd.read_excel(os.path.join(_PLANILHAS_OV, "dados_bonds1.xlsx"))
    dados_cp                = pd.read_excel(os.path.join(_PLANILHAS_OV, "dados_cp1.xlsx"))
    dados_carteira          = dados_carteiras

    for _nome_off, _arq_off in _arquivos_offline.items():
        _mtime = os.path.getmtime(os.path.join(_PLANILHAS_OV, _arq_off))
        _data_mod = pd.Timestamp(_mtime, unit="s").strftime("%d/%m/%Y %H:%M")
        print(f"  ✓ {_arq_off}  (salvo em {_data_mod})")

    print("\n  Modo offline ativo — dados do ComDinheiro NAO atualizados.")

if not MODO_COMPLETO and not MODO_OFFLINE:
    _nd = _news_pipeline()
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _base = os.path.abspath(os.path.join(_script_dir, "..", "..", "..", ".."))
    try:
        _lp = os.path.join(_base, r"Análise de Crédito\Comitê de acompanhamento\Overview Plataforma\Douro-Capital-logo-Horizontal-colorida (3).png")
        with open(_lp, "rb") as _lf:
            _lb64 = "data:image/png;base64," + base64.b64encode(_lf.read()).decode()
        _logo_tag = f'<img src="{_lb64}" style="max-height:36px;width:auto">'
    except Exception:
        _logo_tag = '<div style="font-size:20px;font-weight:800;color:#b69d74;letter-spacing:2px">DOURO CAPITAL</div>'
    _html_news = _make_news_html(_nd, _logo_tag)
    _out = os.path.join(_base, r"Análise de Crédito\Comitê de acompanhamento\douro_credito_overview.html")
    with open(_out, "w", encoding="utf-8") as _f:
        _f.write(_html_news)
    print(f"Douro News gerado: {_out}")
    webbrowser.open(f"file:///{_out.replace(os.sep, '/')}")
    sys.exit(0)

# 1. Importações
# ===============================================================================================================================================
# 1.1 Dados Comdinheiro
# ===============================================================================================================================================
# 1.1.1. Parametros
URL_BASE = "https://www.comdinheiro.com.br/Clientes/API/EndPoint001.php"
 
USERNAME = "douro.capital"
PASSWORD = "Douro@2022"
balanco = "31122025"
data_final_carteiras = "31032026"
 
# =========================================
# FUNÇÃO PRINCIPAL (EXTRAÇÃO + TRATAMENTO)
# =========================================
def extrair_e_tratar(payload_url_encoded, tab_name, nome_df=None):

    body = (
        f"username={USERNAME}"
        f"&password={PASSWORD}"
        f"&URL={payload_url_encoded}"
        f"&format=json3"
    )

    import time as _t
    max_tentativas = 5
    for tentativa in range(max_tentativas):
        try:
            session = requests.Session()
            session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            response = session.post(
                URL_BASE,
                params={"code": "import_data"},
                data=body,
                timeout=180,
            )
            session.close()
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if tentativa == max_tentativas - 1:
                raise
            espera = 10 * (tentativa + 1)
            print(f"        ⚠ {nome_df}: erro de conexão (tentativa {tentativa+1}/{max_tentativas}), aguardando {espera}s...")
            _t.sleep(espera)

    print(f"\n--- DEBUG {nome_df} ---")
    print("Status:", response.status_code)
    print("Resposta (preview):", response.text[:300])

    if not response.text.strip():
        raise ValueError(f"{nome_df} retornou resposta vazia")

    try:
        data = response.json()
    except Exception:
        raise ValueError(f"{nome_df} NÃO retornou JSON válido")

    tab = data["tables"][tab_name]

    registros = list(tab.values())
    df = pd.DataFrame(registros)

    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)

    df.columns = [str(col).strip().lower() for col in df.columns]

    if nome_df:
        print(f"{nome_df} carregado: {df.shape[0]} linhas")

    return df
 
# =========================================
# PAYLOADS (MANTENDO ENCODING ORIGINAL)
# =========================================
 
payload_carteira = "RelatorioGerencialCarteiras001.php%3F%26data_analise%3Ddmenos1%26data_ini%3D%26nome_portfolio%3DGrupoGeral%26variaveis%3Dnome_portfolio%2Btipo_ativo%2Bativo%2Bdesc%2Bduration%28a%2Ca%2Cu%29%2Bsaldo_bruto%2Bticker_cmd_puro%2Bmv%28classe_ativos%29%2Bmv%28cv_emissor_gestor%29%26filtro%3Dall%26ativo%3D%26filtro_IF%3Dtodos%26relat_alias%3D%26layout%3D0%26layoutB%3D0%26num_casas%3D%26enviar_email%3D0%26portfolio_editavel%3D%26filtro_id%3D%26orderBy%3D"

 
payload_carteiras_creditos = (
    "HistoricoCotacao002.php%3F%26x%3DExt_Douro_CP_Ticker_Cota%2Bas%2B%2522Cr%25E9ditos%2BIPCA%25BE%2522%2BExt_Douro_CP_Ticker_Aprovados_Cota%2Bas%2B%2522Cr%25E9ditos%2BAprovados%2522%2BANBIMA_IMAB%2Bas%2B%2522IMAB%2522%2BCDI%2BExt_Douro_CP_Ticker_Deb_Cota%2Bas%2B%2522Deb%25EAntures%2522%2BExt_Douro_CP_Ticker_Aprovados_Deb_Cota%2Bas%2B%2522Deb%25EAntures%2BAprovadas%2522%2BCarteiraArx%2Bas%2B%2522ARX%2522%2B54237051000160%2Bas%2B%2522JGP%2BDeb%2BInc%2522%2BANBIMA_IDAIPCAINFRA%2Bas%2B%2522IDA%2BINFRA%2522%26data_ini%3D31122024%26data_fim%3D" 
    + str(data_final_carteiras) +
    "%26pagina%3D1%26d%3DMOEDA_ORIGINAL%26g%3D1%26m%3D0%26info_desejada%3Dretorno%26retorno%3Ddiscreto%26tipo_data%3Ddu_br%26tipo_ajuste%3Dtodosajustes%26num_casas%3D2%26enviar_email%3D0%26ordem_legenda%3D1%26cabecalho_excel%3Dmodo1%26classes_ativos%3Dv57488hd2bqbj%26ordem_data%3D0%26rent_acum%3Drent_acum%26minY%3D%26maxY%3D%26deltaY%3D%26preco_nd_ant%3D0%26base_num_indice%3D100%26flag_num_indice%3D0%26eixo_x%3DData%26startX%3D0%26max_list_size%3D20%26line_width%3D2%26titulo_grafico%3D%26legenda_eixoy%3D%26tipo_grafico%3Dline%26tooltip%3Dunica%26pageviews%3D1&format=json3"
)
payload_bonds = (
            "HistoricoCotacao002.php%3F%26x%3DUS%25B2FWB%25B2USL7909CAE77%2Bas%2B%2522Raizen%2B1~2035%2522%2BUS%25B2FWB%25B2USA35155AE99%2Bas%2B%2522Klabin%2BS~A%2B1~2031%2522%2BUS%25B2FWB%25B2USP2281VAA81%2Bas%2B%2522Axia%2BEnergia%2B1~2035%2522%2BUS%25B2FWB%25B2USL6401PAM51%2Bas%2B%2522Minerva%2B9~2033%2522%2BUS%25B2FWB%25B2US71645WAQ42%2Bas%2B%2522Petrobras%2B1~2040%2522%2BUS%25B2FWB%25B2USL79090AD51%2Bas%2B%2522Rumo%2BS.A.%2B1~2032%2522%2BUS%25B2C_B%25B2USL01343AE91%2Bas%2B%2522Aegea%2BSaneamento%2Be%2BPart%2BS~A%2B1~2036%2522%2BUS%25B2FWB%25B2USF7629AJC20%2Bas%2B%2522Engie%2BBrasil%2B4~2034%2522%2BUS%25B2C_B%25B2USL56900AA86%2Bas%2B%2522JBS%2B4~2035%2522%2BUS%25B2FWB%25B2USL65266AA36%2Bas%2B%2522Movida%2B2~2031%2522%2BUS%25B2FWB%25B2US86964WAK80%2Bas%2B%2522Suzano%2BS.A.%2B1~2032%2522%2BUS%25B2FWB%25B2USU1065PAA94%2Bas%2B%2522Braskem%2B7~2041%2522%2BUS%25B2FWB%25B2USP98088AA83%2Bas%2B%2522Votorantim%2B4~2041%2522%2BUS%25B2FWB%25B2US91911TAH68%2Bas%2B%2522Vale%2B11~2036%2522%2BXS%25B2C_B%25B2XS0556373347%2Bas%2B%2522Cosan%2BPerp.%2522%2BUS%25B2C_B%25B2USL21779AK60%2Bas%2B%2522CSN%2B4~2032%2522%2BUS%25B2FWB%25B2USL8449RAA79%2Bas%2B%2522Simpar%2B1~2031%2522%2BUS%25B2FWB%25B2USL48008AB91%2Bas%2B%2522Hidrovias%2B2~2031%2522%2BUS%25B2C_B%25B2USL07120AB17%2Bas%2B%2522Sabesp%2B8~2030%2522%2BUS%25B2FWB%25B2USG5825AAC65%2Bas%2B%2522Marfrig%2B1~2031%2522%2BUS%25B2C_B%25B2USU6203KAE48%2Bas%2B%2522Multiplan%2B9~2028%2522%26data_ini%3D36m%26data_fim%3Dhoje%26pagina%3D1%26d%3DMOEDA_ORIGINAL%26g%3D1%26m%3D0%26info_desejada%3Dpreco%26retorno%3Ddiscreto%26tipo_data%3Ddu_br%26tipo_ajuste%3Dtodosajustes%26num_casas%3D2%26enviar_email%3D0%26ordem_legenda%3D1%26cabecalho_excel%3Dmodo1%26classes_ativos%3Dv57488hd2bqbj%26ordem_data%3D0%26rent_acum%3Drent_acum%26minY%3D%26maxY%3D%26deltaY%3D%26preco_nd_ant%3D0%26base_num_indice%3D100%26flag_num_indice%3D0%26eixo_x%3DData%26startX%3D0%26max_list_size%3D20%26line_width%3D2%26titulo_grafico%3D%26legenda_eixoy%3D%26tipo_grafico%3Dline%26tooltip%3Dunica%26pageviews%3D1&format=json3"
            )
 

payload_cp = (
    "HistoricoCotacao002.php%3F%26x%3DCETIP_25E0013305.taxa_max%2BCETIP_CRA020002GZ.taxa_indic%2BCETIP_CRA02300MJ9.taxa_indic%2BCETIP_21L0668295.taxa_max%2BCETIP_21K0001812.taxa_indic%2BCETIP_22C1362141.taxa_indic%2BCETIP_23B0587522.taxa_indic%2BCETIP_CRA023007VE.taxa_max%2BCETIP_CRA02400ECU.taxa_indic%2BCETIP_CRA025002S4.taxa_indic%2BCETIP_25C0023404.taxa_max%2BCETIP_CRA024001E4.taxa_max%2BEGIEC1.taxa_indic%2BCETIP_CRA020001P7.taxa_max%2BBTEL23.taxa_indic%2BCETIP_CRA0210012Y.taxa_max%2BCETIP_CRA02300MOQ.taxa_indic%2BEGIE27.taxa_indic%2BCETIP_CRA019000RT.taxa_indic%2BENEV18.taxa_indic%2BCETIP_CRA020003K0.taxa_indic%2BRUMOA5.taxa_indic%2BCETIP_CRA025002S3.taxa_indic%2BRESA15.taxa_max%2BRISP14.taxa_indic%2BCETIP_23I1259644.taxa_max%2BCETIP_23B0540453.taxa_indic%2BCETIP_23H1188857.taxa_indic%2BAMERF2.taxa_max%2BLIGHB6.taxa_max%2BLIGHD3.taxa_max%2BLIGHF2.taxa_max%2BCPLD37.taxa_indic%2BCTGE15.taxa_indic%2BCETIP_CRA019003V2.taxa_max%2BENGIA5.taxa_indic%2BCETIP_22K1520003.taxa_indic%2BSBSPB6.taxa_indic%2BTBLE26.taxa_indic%2BCETIP_22K0934880.taxa_indic%2BCETIP_CRA021000RY.taxa_indic%2BENMTA4.taxa_indic%2BENMTA7.taxa_indic%2BCETIP_CRA019003V3.taxa_max%2BENMTB5.taxa_indic%2BENGIB9.taxa_indic%2BCESE32.taxa_indic%2BSBSPD4.taxa_indic%2BCETIP_22B0004808.taxa_indic%2BCETIP_CRA02300CYR.taxa_indic%2BCETIP_CRA02300HWI.taxa_max%2BCETIP_CRA02300NRM.taxa_indic%2BCETIP_CRA019001E6.taxa_max%2BCETIP_24I01531624.taxa_max%2BENMTA5.taxa_indic%2BEGIE19.taxa_indic%2BEGIE39.taxa_indic%2BFGEN13.taxa_indic%2BCETIP_17K0231156.taxa_max%2BLIGHA5.taxa_max%2BLIGHC5.taxa_max%2BCETIP_CRA023003UX.taxa_indic%2BEQMAA0.taxa_indic%2BCETIP_23I1211962.taxa_max%2BCETIP_23J0019603.taxa_max%2BCETIP_CRA023000GP.taxa_indic%2BPETR27.taxa_indic%2BCETIP_23J1127328.taxa_indic%2BSAELA1.taxa_indic%2BCMGD27.taxa_indic%2BJTEE11.taxa_indic%2BCETIP_23F1519397.taxa_indic%2BCETIP_CRA023000MC.taxa_indic%2BCETIP_CRA025005V5.taxa_indic%2BEGIEB4.taxa_indic%2BENGIA6.taxa_indic%2BCETIP_CRA024001P5.taxa_indic%2BCETIP_CRA024001P6.taxa_indic%2BENGIA1.taxa_indic%2BCETIP_21C0483517.taxa_max%2BEQSP11.taxa_indic%2BCETIP_23C0247388.taxa_indic%2BCETIP_24E1393588.taxa_indic%2BCETIP_CRA02300TSD.taxa_max%2BGSTS14.taxa_indic%2BCETIP_CRA02300209.taxa_indic%2BENTV12.taxa_indic%2BMVLV16.taxa_indic%2BPALF38.taxa_indic%2BMVLV19.taxa_indic%2BAEGP19.taxa_indic%2BBTGH18.taxa_indic%2BELET24.taxa_indic%2BCETIP_23J0019602.taxa_indic%2BCETIP_21H1078699.taxa_indic%2BCETIP_21H1078700.taxa_indic%2BCETIP_CRA02300TSB.taxa_indic%2BENEV15.taxa_indic%2BGASP29.taxa_indic%2BCETIP_CRA02300CYQ.taxa_indic%2BCETIP_CRA023000RT.taxa_indic%2BENEV32.taxa_indic%2BENGI39.taxa_indic%2BCETIP_CRA022008N7.taxa_indic%2BCETIP_23F1514014.taxa_indic%2BCETIP_CRA020001E5.taxa_indic%2BCEEBB6.taxa_indic%2BCEED21.taxa_indic%2BCETIP_23F2455004.taxa_indic%2BCETIP_CRA02200795.taxa_indic%2BEGIEA1.taxa_indic%2BERDVB4.taxa_indic%2BBHIAB1.taxa_max%2BBHIAC1.taxa_max%2BCEPEC1.taxa_indic%2BCETIP_21I0566602.taxa_max%2BCETIP_22J1295549.taxa_max%2BCETIP_23C0247702.taxa_indic%2BCETIP_23K0018801.taxa_indic%2BCETIP_CRA01900749.taxa_max%2BCETIP_CRA022008C5.taxa_max%2BCETIP_CRA02300CCI.taxa_max%2BHRTU23.taxa_max%2BHRTU63.taxa_max%2BOMNG12.taxa_indic%2BWETE11.taxa_max%2BSBSPC6.taxa_indic%2BCMGD28.taxa_indic%2BECER12.taxa_indic%2BOMGE22.taxa_indic%2BCCLS11.taxa_indic%2BCETIP_21J0001207.taxa_max%2BCETIP_CRA022000B5.taxa_max%2BCMIN21.taxa_indic%2BMEZ511.taxa_indic%2BRIS422.taxa_indic%2BTAEE17.taxa_indic%2BUNEG11.taxa_indic%2BVAMO33.taxa_indic%2BCETIP_21K0906902.taxa_max%2BCETIP_22A0695877.taxa_max%2BCSNAA1.taxa_max%2BNTEN11.taxa_indic%2BCETIP_22K1457799.taxa_max%2BCETIP_20L0766583.taxa_indic%2BCETIP_23G0008401.taxa_max%2BCETIP_CRA02300SV0.taxa_max%2BRISP22.taxa_indic%2BTAEEB4.taxa_indic%2BCETIP_23J0138439.taxa_max%2BCEED13.taxa_indic%2BCETIP_CRA024002S1.taxa_indic%2BISAEA8.taxa_indic%2BRUMOB7.taxa_max%2BENGIB6.taxa_indic%2BENMTB3.taxa_indic%2BISAEB8.taxa_indic%2BTAEEA4.taxa_max%2BCETIP_CRA021001K9.taxa_max%2BCETIP_CRA022004H5.taxa_indic%2BCETIP_CRA02200F4H.taxa_max%2BCDAR11.taxa_indic%2BCETIP_20L0653519.taxa_max%2BCETIP_22E1095521.taxa_max%2BCETIP_22F0009410.taxa_indic%2BCETIP_22F0009804.taxa_indic%2BCETIP_22K0767293.taxa_max%2BCETIP_23I1257218.taxa_indic%2BCETIP_23K1775123.taxa_max%2BCETIP_23L0034761.taxa_indic%2BCETIP_24A2721829.taxa_indic%2BCETIP_CRA022006HK.taxa_indic%2BCETIP_CRA022007KI.taxa_indic%2BCETIP_CRA02200C6Z.taxa_indic%2BCETIP_CRA024001P7.taxa_indic%2BCETIP_CRA024004SC.taxa_indic%2BCETIP_CRA0240066C.taxa_max%2BCETIP_CRA0240086L.taxa_indic%2BCETIP_CRA025002S2.taxa_indic%2BCMIN12.taxa_indic%2BENAT33.taxa_indic%2BGSTS24.taxa_indic%2BHARG11.taxa_indic%2BITPO14.taxa_indic%2BLORTA7.taxa_indic%2BMOVI37.taxa_indic%2BMSGT33.taxa_indic%2BORIG11.taxa_indic%2BORIG21.taxa_indic%2BRATL11.taxa_indic%2BRMSA12.taxa_indic%2BSABP12.taxa_indic%2BSIMH16.taxa_indic%2BUHSM12.taxa_indic%2BVAMO34.taxa_indic%2BVERO23.taxa_indic%2BVRDN12.taxa_indic%2BCEPEB3.taxa_indic%2BCETIP_CRA02300EZ2.taxa_indic%2BCETIP_CRA024009Q4.taxa_indic%2BCETIP_CRA02400AYO.taxa_max%2BCETIP_25B3099731.taxa_indic%2BERDVC4.taxa_indic%2BCETIP_CRA022004MS.taxa_indic%2BCEEBB7.taxa_indic%2BNEOE26.taxa_indic%2BCETIP_CRA025002S1.taxa_indic%2BCETIP_CRA02300MJA.taxa_max%2BSBSPE9.taxa_indic%2BCETIP_CRA02300CYT.taxa_max%2BCETIP_CRA02300UEN.taxa_max%2BCETIP_23G1697232.taxa_max%2BCETIP_23J1253082.taxa_max%2BCETIP_CRA0230020A.taxa_max%2BCETIP_24D3313768.taxa_indic%2BCETIP_CRA02300JR5.taxa_max%2BEDVP17.taxa_indic%2BCMGDB0.taxa_indic%2BCPGT27.taxa_indic%2BLIGT12.taxa_max%2BCETIP_25C0023202.taxa_max%2BAURP12.taxa_indic%2BCERT11.taxa_indic%2BCETIP_23H0190135.taxa_max%2BCETIP_25G5313963.taxa_max%2BCETIP_25L0014618.taxa_max%2BCETIP_CRA02300S35.taxa_indic%2BCETIP_CRA024001QA.taxa_indic%2BHVSP11.taxa_indic%2BJALL21.taxa_indic%2BPEJA22.taxa_indic%2BCETIP_25G5313879.taxa_indic%2BCETIP_CRA01400012.taxa_max%2BCETIP_CRA024001Q9.taxa_indic%2BCETIP_CRA0250038P.taxa_max%2BCETIP_CRA0250066A.taxa_max%2BCETIP_CRA025009VN.taxa_max%2BCETIP_22B0006022.taxa_indic%2BHBSA11.taxa_indic%2BJALL11.taxa_indic%2BRESA27.taxa_max%2BCETIP_CRA02300NX8.taxa_max%2BCETIP_CRA024000B7.taxa_indic%2BCETIP_21K0914380.taxa_max%2BVPLT12.taxa_indic%2BAEGPA0.taxa_max%2BAEGPA8.taxa_indic%2BCOMR16.taxa_indic%2BLCAMD1.taxa_indic%2BCETIP_CRA024002MJ.taxa_indic%2BCETIP_25D0012203.taxa_indic%2BCETIP_19L0840477.taxa_max%2BCETIP_23L1737623.taxa_indic%2BRSAN16.taxa_indic%2BUTPS22.taxa_indic%2BCETIP_24D2765586.taxa_indic%2BCETIP_25A1945746.taxa_max%2BCETIP_CRA02300RS5.taxa_indic%2BCETIP_CRA024004MP.taxa_max%2BVALED1.taxa_max%2BBTEL13.taxa_indic%2BCBAN12.taxa_indic%2BELTN17.taxa_indic%2BENMTC4.taxa_indic%2BLGEN11.taxa_indic%2BLIGT11.taxa_max%2BCETIP_25A4146077.taxa_max%2BCETIP_25G0658366.taxa_max%2BCETIP_CRA021001KA.taxa_indic%2BENGIB4.taxa_indic%2BMRFGA1.taxa_max%2BLIGHB0.taxa_max%2BLIGHC6.taxa_max%2BLIGHD4.taxa_max%2BCETIP_24D2765715.taxa_indic%2BCETIP_CRA0240086K.taxa_indic%2BPEJA13.taxa_indic%2BCETIP_CRA02300CT6.taxa_max%2BCETIP_12J0037879.taxa_max%2BCETIP_17H0164854.taxa_max%2BENEV16.taxa_indic%2BCETIP_12E0025287.taxa_max%2BCETIP_16I0000002.taxa_max%26data_ini%3D36m%26data_fim%3Dhoje%26pagina%3D1%26d%3DMOEDA_ORIGINAL%26g%3D1%26m%3D0%26info_desejada%3Dpreco%26retorno%3Ddiscreto%26tipo_data%3Ddu_br%26tipo_ajuste%3Dtodosajustes%26num_casas%3D2%26enviar_email%3D0%26ordem_legenda%3D1%26cabecalho_excel%3Dmodo1%26classes_ativos%3Dv57488hd2bqbj%26ordem_data%3D0%26rent_acum%3Drent_acum%26minY%3D%26maxY%3D%26deltaY%3D%26preco_nd_ant%3D0%26base_num_indice%3D100%26flag_num_indice%3D0%26eixo_x%3DData%26startX%3D0%26max_list_size%3D20%26line_width%3D2%26titulo_grafico%3D%26legenda_eixoy%3D%26tipo_grafico%3Dline%26tooltip%3Dunica%26pageviews%3D1&format=json3"
    )
# (mantive truncado só pra não poluir visual — pode manter o seu completo)
 
 
# =========================================
# CAMINHOS BASE (definido antes das extrações para uso em saves)
# =========================================
if not MODO_OFFLINE:
    import glob as _glob
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    BASE_INV  = os.path.abspath(os.path.join(_script_dir, "..", "..", "..", ".."))
    _proc_cands = _glob.glob(os.path.join(os.path.dirname(BASE_INV), "*Processos*"))
    BASE_PROC = _proc_cands[0] if _proc_cands else os.path.join(os.path.dirname(BASE_INV), "Douro - Processos")

    _PLANILHAS_OV = os.path.join(BASE_INV, r"Análise de Crédito\Comitê de acompanhamento\Overview Plataforma\Planilhas Overview")
    print(f"  Usuario: {os.path.basename(os.path.expanduser('~'))}")
    print(f"  Base: {BASE_INV}\n")

    # =========================================
    # EXTRAÇÕES
    # =========================================
    _extracao_tasks = [
        ("dados_carteira",          payload_carteira,          "tab0"),
        ("dados_carteiras_credito", payload_carteiras_creditos, "tab1"),
        ("dados_bonds",             payload_bonds,             "tab1"),
        ("dados_cp",                payload_cp,                "tab1"),
    ]

    print("=" * 52)
    print("  [1/8] Buscando dados Comdinheiro sequencialmente...")
    print("         (4 chamadas — aguarde)")
    print("=" * 52)

    import time as _time
    _t0_ext = _time.time()

    _resultados_extracao = {}
    for _i, (_nome_task, _payload_task, _tab_task) in enumerate(_extracao_tasks):
        print(f"        → iniciando: {_nome_task}")
        _resultados_extracao[_nome_task] = extrair_e_tratar(_payload_task, _tab_task, _nome_task)
        print(f"        ✓ concluído: {_nome_task}")
        if _i < len(_extracao_tasks) - 1:
            _time.sleep(3)

    dados_carteira          = _resultados_extracao["dados_carteira"]
    dados_carteiras_credito = _resultados_extracao["dados_carteiras_credito"]
    dados_bonds             = _resultados_extracao["dados_bonds"]
    dados_cp                = _resultados_extracao["dados_cp"]

    print(f"\n  Todas as extrações concluídas em {_time.time()-_t0_ext:.1f}s")

print("\nCarteiras:")
print(dados_cp.head())

# =========================================
# AJUSTES DE FORMATO - Ajustar o formato das planilhas extraídas para o formato adequado
# =========================================
print("\n" + "=" * 52)
print("  [5/8] Transformando séries temporais...")
print("=" * 52)
def transformar_series(df, nome_df=None):
   
    # Garante que a primeira coluna é Data
    df = df.rename(columns={df.columns[0]: "Data"})
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
   
    # Unpivot
    df_melt = df.melt(
        id_vars="Data",
        var_name="ativo",
        value_name="valor"
    )
   
    # Remove vazios
    df_melt = df_melt.dropna(subset=["valor"])
      
    if nome_df:
        print(f"{nome_df} transformado: {df_melt.shape[0]} linhas")
   
    return df_melt
 
if not MODO_OFFLINE:
    dados_carteiras_credito = transformar_series(dados_carteiras_credito, "dados_carteiras_credito")
    dados_bonds = transformar_series(dados_bonds, "dados_bonds")
    dados_cp = transformar_series(dados_cp, "dados_cp")
else:
    # Excel já foi salvo no formato long (Data, ativo, valor) — não aplica melt novamente
    for _df_name, _df_ref in [("dados_carteiras_credito", dados_carteiras_credito), ("dados_bonds", dados_bonds), ("dados_cp", dados_cp)]:
        print(f"{_df_name} (offline): {_df_ref.shape[0]} linhas")
 
print(dados_cp["valor"].head(20).tolist())
print("\n" + "=" * 52)
print("  [6/8] Convertendo colunas para numérico...")
print("=" * 52)
def transformar_financeiros(df):
 
    df = df.rename(columns={df.columns[0]: "Data"})
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
    # Unpivot
    df_melt = df.melt(
        id_vars="Data",
        var_name="empresa_indicador",
        value_name="valor"
    )
 
    df_melt = df_melt.dropna(subset=["valor"])
 
    # Split no primeiro espaço
    df_melt[["empresa", "indicador"]] = df_melt["empresa_indicador"].str.split(
        " ", n=1, expand=True
    )
 
    df_melt = df_melt.drop(columns=["empresa_indicador"])
 
    # Tipos
    df_melt["valor"] = pd.to_numeric(df_melt["valor"], errors="coerce")
 
    return df_melt
  
 
# =========================================
# AJUSTES PARA NUMÉRICOS
# =========================================
def converter_numericos(df, colunas):

    for col in colunas:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.replace(".", "", regex=False)   # remove separador milhar
                .str.replace(",", ".", regex=False)  # troca decimal
            )

            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
 
if not MODO_OFFLINE:
    dados_carteiras = converter_numericos(dados_carteira, ["saldo bruto", "duration(a,a,u)"])
else:
    dados_carteiras = dados_carteira.copy()
    dados_carteiras["saldo bruto"]      = pd.to_numeric(dados_carteiras["saldo bruto"],      errors="coerce")
    dados_carteiras["duration(a,a,u)"]  = pd.to_numeric(dados_carteiras.get("duration(a,a,u)", pd.Series(dtype=float)), errors="coerce")
if not MODO_OFFLINE:
    # No modo offline os valores já vêm como float do Excel — converter_numericos
    # removeria o separador decimal e corromperia os dados
    dados_carteiras_credito = converter_numericos(dados_carteiras_credito, ["valor"])
    dados_bonds = converter_numericos(dados_bonds, ["valor"])
    dados_cp = converter_numericos(dados_cp, ["valor"])
else:
    dados_carteiras_credito["valor"] = pd.to_numeric(dados_carteiras_credito["valor"], errors="coerce")
    dados_bonds["valor"]             = pd.to_numeric(dados_bonds["valor"],             errors="coerce")
    dados_cp["valor"]                = pd.to_numeric(dados_cp["valor"],                errors="coerce")

# =========================================
# DEBUG
# =========================================
print("\nCarteiras:")
print(dados_carteira.head())
 
print("\nCarteiras Crédito:")
print(dados_carteiras_credito.head())
 
print("\nBonds:")
print(dados_bonds.head())
 
print("\nCP:")
print(dados_cp.head())
print("\n" + "=" * 52)
print("  [7/8] Salvando arquivos Excel intermediários...")
print("=" * 52)
if MODO_OFFLINE:
    print("  [OFFLINE] Save ignorado — usando dados existentes.")
else:
    print(f"         Destino: {_PLANILHAS_OV}")
    dados_carteiras_credito.to_excel(os.path.join(_PLANILHAS_OV, "dados_carteiras_credito1.xlsx"), index=False)
    print("  ✓ dados_carteiras_credito1.xlsx")
    dados_carteiras.to_excel(os.path.join(_PLANILHAS_OV, "dados_carteiras1.xlsx"), index=False)
    print("  ✓ dados_carteiras1.xlsx")
    dados_bonds.to_excel(os.path.join(_PLANILHAS_OV, "dados_bonds1.xlsx"), index=False)
    print("  ✓ dados_bonds1.xlsx")
    dados_cp.to_excel(os.path.join(_PLANILHAS_OV, "dados_cp1.xlsx"), index=False)
    print("  ✓ dados_cp1.xlsx")

# =========================================
# PATCH B — 1.2 IMPORTAÇÕES ARQUIVOS EXCEL (paralelo via ThreadPoolExecutor)
# =========================================
# BASE_INV e BASE_PROC já definidos acima (antes das extrações)

print("\n" + "=" * 52)
print("  [8/8] Lendo arquivos Excel complementares...")
print("=" * 52)

# Logo — leitura única pequena, mantém síncrono
caminho_logo = os.path.join(BASE_INV, r"Análise de Crédito\Comitê de acompanhamento\Overview Plataforma\Douro-Capital-logo-Horizontal-colorida (3).png")
try:
    with open(caminho_logo, "rb") as img_file:
        logo_b64 = "data:image/png;base64," + base64.b64encode(img_file.read()).decode("utf-8")
    logo_html = f'<img src="{logo_b64}" alt="Douro Capital" style="width: 100%; max-width: 160px; height: auto; display: block;">'
except Exception as e:
    print(f"⚠️ Aviso: Logo não encontrada em {caminho_logo}. Usando logo em texto (Fallback).")
    logo_html = """
    <div class="logo-icon"><svg viewBox="0 0 24 24"><path d="M2 17c3-3 5-5 10-5s7 2 10 5v2H2v-2zm0-5C5 9 7 7 12 7s7 2 10 5H2z"/></svg></div>
    <div class="logo-text">DOURO<br><span>CAPITAL</span></div>
    """

def _read_excel_task(path, sheet_name=0, skiprows=0):
    """Wrapper para leitura de Excel em thread separada."""
    return pd.read_excel(path, sheet_name=sheet_name, skiprows=skiprows)

_excel_tasks = [
    ("ranking_corporativo",     os.path.join(BASE_INV,  r"Análise de Crédito\Rating Crédito\Scorecard de Empresas.xlsm"),                                                                              {"sheet_name": "Ranking",         "skiprows": 4}),
    ("ranking_bancos",          os.path.join(BASE_INV,  r"Análise de Crédito\Rating Crédito\Watch List Bancos.xlsm"),                                                                                  {"sheet_name": "Ranking",         "skiprows": 4}),
    ("fatos_rj",                os.path.join(BASE_INV,  r"Análise de Crédito\Recuperações judiciais\Acompanhamento recuperações judiciais.xlsx"),                                                       {"sheet_name": "Fatos RJ"}),
    ("rating_setor",            os.path.join(BASE_PROC, r"Risco\Documentos base [SEMPRE FAZER CÓPIA]\base_rating_setor.xlsx"),                                                                         {"sheet_name": "Base RatingSetor"}),
    ("cricra_anbima",           os.path.join(BASE_INV,  r"Análise de Crédito\Comitê de acompanhamento\Overview Plataforma\Planilhas Overview\certificados-recebiveis-precos-13-05-2026-15-31-09.xls"),{}),
    ("debenture_anbima",        os.path.join(BASE_INV,  r"Análise de Crédito\Comitê de acompanhamento\Overview Plataforma\Planilhas Overview\debentures-precos-13-05-2026-15-30-48.xlsx"),            {}),
]

print("Lendo arquivos Excel em paralelo...")
_excel_results = {}
with ThreadPoolExecutor(max_workers=6) as _pool:
    _futures = {
        _pool.submit(_read_excel_task, path, **kwargs): nome
        for nome, path, kwargs in _excel_tasks
    }
    for _future in _futures:
        _nome = _futures[_future]
        try:
            _excel_results[_nome] = _future.result()
            print(f"  ✓ {_nome}")
        except Exception as _e:
            print(f"  ✗ {_nome}: {_e}")
            raise

ranking_corporativo     = _excel_results["ranking_corporativo"]
ranking_bancos          = _excel_results["ranking_bancos"]
fatos_rj                = _excel_results["fatos_rj"]
rating_setor            = _excel_results["rating_setor"]
cricra_anbima           = _excel_results["cricra_anbima"]
debenture_anbima        = _excel_results["debenture_anbima"]
exposicao_rating        = ranking_corporativo.iloc[9:20, [14, 15]].copy()

# 1.1.7 Merge de planilhas de crédito privado
cricra_anbima = cricra_anbima.rename(columns={
    "Emissor": "Securitizadora",
    "Devedor": "Emissor",
    "Duration (dias úteis)": "Duration"
})
for col in debenture_anbima.columns:
    if col not in cricra_anbima.columns:
        cricra_anbima[col] = np.nan
for col in cricra_anbima.columns:
    if col not in debenture_anbima.columns:
        debenture_anbima[col] = np.nan
cricra_anbima = cricra_anbima[debenture_anbima.columns]
ntnb_ref = pd.concat([debenture_anbima, cricra_anbima], ignore_index=True)
ntnb_ref["Duration"] = pd.to_numeric(ntnb_ref["Duration"], errors="coerce") / 252
print("Linhas totais:", len(ntnb_ref))

# 1.1.8 Merge de planilhas de ranking
ranking_corporativo = pd.concat([ranking_corporativo, ranking_bancos], ignore_index=True)

# 1.1.7 Limpar nomes das planilhas
dados_cp["ativo"] = (
    dados_cp["ativo"]
    .str.replace("cetip_", "", case=False, regex=False)
    .str.replace(".taxa_indic", "", case=False, regex=False)
    .str.replace(".taxa_max", "", case=False, regex=False)
)
dados_carteira["ticker_cmd_puro"] = (
    dados_carteira["ticker_cmd_puro"]
    .str.replace("cetip_", "", case=False, regex=False)
)
dados_carteira["carteira"] = dados_carteira["carteira"].str.split("_").str[0]
dados_carteira = dados_carteira.rename(
    columns={"minha_variavel(cv_emissor_gestor)": "emissor", "minha_variavel(classe_ativos)": "classe"}
)

# 1.1.8 Criar coluna Officer na Base de Carteiras
conditions = [
    dados_carteira["carteira"].str.contains("DCAB",  na=False),
    dados_carteira["carteira"].str.contains("DCAV",  na=False),
    dados_carteira["carteira"].str.contains("DCLS",  na=False),
    dados_carteira["carteira"].str.contains("DCLM",  na=False),
    dados_carteira["carteira"].str.contains("DCXYZ", na=False),
    dados_carteira["carteira"].str.contains("DCMO",  na=False),
    dados_carteira["carteira"].str.contains("DCCV",  na=False),
    dados_carteira["carteira"].str.contains("DCGD",  na=False),
    dados_carteira["carteira"].str.contains("Braga", na=False),
]
choices = ["AB", "AV", "LS", "LM", "XYZ", "MO", "CV", "GD", "LM"]
dados_carteira["officer"] = np.select(conditions, choices, default=None)

# =========================================
# PATCH C — 1.3 + 1.4 DOWNLOADS PARALELOS (asyncio + aiohttp)
# =========================================
async def _fetch_bytes(session: aiohttp.ClientSession, url: str, label: str, _retry: int = 3) -> bytes:
    """Baixa URL e retorna bytes. Tenta até _retry vezes em caso de timeout/erro."""
    _timeout = aiohttp.ClientTimeout(total=720, connect=30, sock_read=700)
    for attempt in range(1, _retry + 1):
        try:
            async with session.get(url, ssl=False, timeout=_timeout) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status} em {label}")
                data = await resp.read()
                print(f"  ✓ {label}")
                return data
        except Exception as e:
            if attempt < _retry:
                print(f"  ↺ {label} (tentativa {attempt}/{_retry}): {type(e).__name__} — repetindo...")
                await asyncio.sleep(3 * attempt)
            else:
                print(f"  ✗ {label}: falhou após {_retry} tentativas ({type(e).__name__})")
                raise

async def _download_all() -> dict:
    """Executa todos os downloads em paralelo e retorna dict chave→bytes."""
    connector = aiohttp.TCPConnector(limit=10, ssl=False)
    async with aiohttp.ClientSession(
        connector=connector,
        headers={"User-Agent": "Mozilla/5.0"}
    ) as session:

        url_tesouro  = (
            "https://www.tesourotransparente.gov.br/ckan/dataset/"
            "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
            "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
        )
        url_cadastro = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"

        _ANOS = range(2024, 2027)

        # Um ZIP por ano — cada ZIP contém todos os tipos (DRE/BPA/BPP/DFC_MI)
        # Baixar cada ZIP uma única vez, reutilizar para os 4 tipos
        zip_itr_urls = {
            f"zip_itr_{ano}": f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ano}.zip"
            for ano in _ANOS
        }
        zip_dfp_urls = {
            f"zip_dfp_{ano}": f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
            for ano in _ANOS
        }

        tasks = {}
        tasks["tesouro"]  = asyncio.create_task(_fetch_bytes(session, url_tesouro,  "Tesouro Direto"))
        tasks["cadastro"] = asyncio.create_task(_fetch_bytes(session, url_cadastro, "Cadastro CVM"))

        for key, url in {**zip_itr_urls, **zip_dfp_urls}.items():
            ano      = key.split("_")[-1]
            tipo_doc = "ITR" if "itr" in key else "DFP"
            tasks[key] = asyncio.create_task(_fetch_bytes(session, url, f"{tipo_doc}/{ano}"))

        print("Aguardando downloads paralelos...")
        keys        = list(tasks.keys())
        results_raw = await asyncio.gather(*tasks.values(), return_exceptions=True)
        results     = dict(zip(keys, results_raw))

    return results

print("Iniciando downloads paralelos (Tesouro + CVM ITR/DFP + Cadastro)...")
_dl_results = asyncio.run(_download_all())

# ── Helper: valida resultado de download ────────────────────────────────────
def _check_dl(key, label):
    r = _dl_results.get(key)
    if isinstance(r, BaseException):
        raise RuntimeError(f"Download de {label} falhou: {type(r).__name__}: {r}")
    if not isinstance(r, (bytes, bytearray)) or len(r) == 0:
        raise RuntimeError(f"Download de {label} retornou dados inválidos (tipo: {type(r).__name__})")
    return r

# ── Processar Tesouro Direto ──────────────────────────────────────────────
print("Processando Tesouro Direto...")
_tesouro_bytes = _check_dl("tesouro", "Tesouro Direto")
tit_pub = pd.read_csv(io.BytesIO(_tesouro_bytes), sep=';', decimal=',', encoding='utf-8')
tit_pub['Data Base']       = pd.to_datetime(tit_pub['Data Base'], dayfirst=True)
tit_pub                    = tit_pub.rename(columns={"Data Base": "Data"})
tit_pub['Data Vencimento'] = pd.to_datetime(tit_pub['Data Vencimento'], dayfirst=True)
tit_pub                    = tit_pub.sort_values(['Data', 'Data Vencimento'])
tit_pub.columns            = tit_pub.columns.str.strip()
print(f"Tesouro carregado: {len(tit_pub)}")

# ── Processar Cadastro CVM ────────────────────────────────────────────────
print("Processando Cadastro CVM...")
cad_cvm = pd.read_csv(BytesIO(_check_dl("cadastro", "Cadastro CVM")), sep=";", encoding="latin1", low_memory=False)
print(f"Cadastro CVM carregado: {len(cad_cvm)}")

# ── Funções de parse dos ZIPs CVM ────────────────────────────────────────
ANOS = range(2011, 2027)

def _parse_zip_cvm(zip_bytes, nome_arquivo_interno: str):
    """Extrai um CSV específico de um ZIP em memória. Retorna DataFrame ou None."""
    try:
        z = zipfile.ZipFile(io.BytesIO(zip_bytes))
        return pd.read_csv(z.open(nome_arquivo_interno), sep=';', encoding='latin1')
    except Exception as e:
        print(f"    ⚠ {nome_arquivo_interno}: {e}")
        return None

def _filtrar(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['ORDEM_EXERC'] == 'ÚLTIMO'].copy()

def _montar(tipo: str, doc: str) -> pd.DataFrame:
    """
    Monta base ITR ou DFP para um tipo de demonstrativo,
    reutilizando os ZIPs já baixados em _dl_results.
    """
    lista = []
    for ano in ANOS:
        chave_zip = f"zip_{doc.lower()}_{ano}"
        payload   = _dl_results.get(chave_zip)
        if isinstance(payload, Exception) or payload is None:
            print(f"  ✗ {doc}/{tipo}/{ano}: download falhou, pulando")
            continue
        nome_csv = f"{doc.lower()}_cia_aberta_{tipo}_con_{ano}.csv"
        df = _parse_zip_cvm(payload, nome_csv)
        if df is not None:
            lista.append(df)
    if not lista:
        raise Exception(f"Nenhum dado carregado para {doc}/{tipo}")
    return pd.concat(lista, ignore_index=True)

print("Montando bases CVM...")
dre     = _filtrar(_montar("DRE",    "ITR"))
bpa     = _filtrar(_montar("BPA",    "ITR"))
bpp     = _filtrar(_montar("BPP",    "ITR"))
dfc     = _filtrar(_montar("DFC_MI", "ITR"))
dfp_dre = _filtrar(_montar("DRE",    "DFP"))
dfp_bpa = _filtrar(_montar("BPA",    "DFP"))
dfp_bpp = _filtrar(_montar("BPP",    "DFP"))
dfp_dfc = _filtrar(_montar("DFC_MI", "DFP"))
print("Bases CVM montadas.")

# ── Bloco original intacto a partir daqui ────────────────────────────────
for df_temp in [dre, bpa, bpp, dfc, dfp_dre, dfp_bpa, dfp_bpp, dfp_dfc]:
    df_temp['DT_FIM_EXERC'] = pd.to_datetime(df_temp['DT_FIM_EXERC'])

mapa = {
    "3.01":       "Receita",
    "3.02":       "Custo",
    "3.03":       "Lucro Bruto",
    "3.05":       "EBIT",
    "3.11":       "Lucro Liquido",
    "3.07":       "EBT",
    "3.08":       "imposto total",
    "3.06.01":    "Depreciacacao_Amortizacao",
    "3.06.02":    "Despesa Financeira",
    "1":          "Ativo Total",
    "1.01":       "Ativo Circulante",
    "1.01.01":    "Caixa",
    "1.01.02":    "Aplicacoes",
    "1.01.04":    "Estoques",
    "1.02.03":    "Imobilizado",
    "2":          "Passivo Total",
    "2.01":       "Passivo Circulante",
    "2.03":       "Patrimonio Liquido",
    "2.01.04":    "Divida Curto Prazo",
    "2.02.01":    "Divida Longo Prazo",
    "6.01":       "FCO",
    "6.02":       "FCI",
    "6.03":       "FCFin",
}

def tratar(df, tem_dt_ini=False):
    mapa_sem_da = {k: v for k, v in mapa.items() if v != 'Depreciacacao_Amortizacao'}
    mask_codigo = df['CD_CONTA'].isin(mapa_sem_da.keys())

    if 'DS_CONTA' in df.columns and 'DENOM_CIA' in df.columns:
        # Prioridade 1 — texto: DS_CONTA contém DEPRECIA/AMORTIZA/EXAUST
        _ds_upper = df['DS_CONTA'].astype(str).str.upper()
        _text_raw = (
            df['CD_CONTA'].astype(str).str.startswith('3.')
            & _ds_upper.str.contains(r'DEPRECIA|AMORTIZA|EXAUST', regex=True, na=False)
        )
        if _text_raw.any():
            _c = df[_text_raw].copy()
            _c['_dep'] = _c['CD_CONTA'].astype(str).str.count(r'\.')
            grp = ['DENOM_CIA'] + (['DT_FIM_EXERC'] if 'DT_FIM_EXERC' in _c.columns else [])
            _c['_min'] = _c.groupby(grp)['_dep'].transform('min')
            mask_da_texto = pd.Series(False, index=df.index)
            mask_da_texto.loc[_c[_c['_dep'] == _c['_min']].index] = True
        else:
            mask_da_texto = pd.Series(False, index=df.index)
        # Prioridade 2 — código 3.06.01: fallback só para empresas sem match por texto
        _cias_com_texto = set(df.loc[mask_da_texto, 'DENOM_CIA'].unique())
        mask_da_codigo = (
            (df['CD_CONTA'] == '3.06.01')
            & ~df['DENOM_CIA'].isin(_cias_com_texto)
        )
        mask_da = mask_da_texto | mask_da_codigo
    else:
        mask_da = df['CD_CONTA'] == '3.06.01'

    df = df[mask_codigo | mask_da].copy()
    df['Conta'] = df['CD_CONTA'].map(mapa_sem_da)
    df.loc[mask_da.loc[df.index], 'Conta'] = 'Depreciacacao_Amortizacao'
    if tem_dt_ini and 'DT_INI_EXERC' in df.columns:
        df['DT_INI_EXERC'] = pd.to_datetime(df['DT_INI_EXERC'])
    return df

dre     = tratar(dre, tem_dt_ini=True)
bpa     = tratar(bpa)
bpp     = tratar(bpp)
dfc     = tratar(dfc, tem_dt_ini=True)
dfp_dre = tratar(dfp_dre)
dfp_bpa = tratar(dfp_bpa)
dfp_bpp = tratar(dfp_bpp)
dfp_dfc = tratar(dfp_dfc)

def itr_trimestral(itr_df):
    chave  = ['DENOM_CIA', 'CD_CONTA', 'DT_FIM_EXERC']
    itr_df = itr_df.sort_values(chave + ['DT_INI_EXERC'], ascending=True)
    itr_df = itr_df.drop_duplicates(subset=chave, keep='last')
    return itr_df

def montar_base_trimestral(itr_df, dfp_df):
    chave       = ['DENOM_CIA', 'CD_CONTA', 'DT_FIM_EXERC']
    itr_tri     = itr_trimestral(itr_df)[chave + ['VL_CONTA', 'Conta']].copy()
    itr_tri['_ORIGEM'] = 'ITR'
    datas_itr   = itr_tri[chave].drop_duplicates().assign(_TEM_ITR=True)
    dfp_filtrado = dfp_df[chave + ['VL_CONTA', 'Conta']].copy()
    dfp_filtrado = dfp_filtrado.merge(datas_itr, on=chave, how='left')
    dfp_filtrado = dfp_filtrado[dfp_filtrado['_TEM_ITR'].isna()].drop(columns=['_TEM_ITR'])
    dfp_filtrado['_ORIGEM'] = 'DFP'
    combined = pd.concat([itr_tri, dfp_filtrado], ignore_index=True)
    combined = combined.sort_values(['DENOM_CIA', 'CD_CONTA', 'DT_FIM_EXERC']).reset_index(drop=True)
    grp = combined.groupby(['DENOM_CIA', 'CD_CONTA'])['VL_CONTA']
    combined['_t1'] = grp.shift(1)
    combined['_t2'] = grp.shift(2)
    combined['_t3'] = grp.shift(3)
    mask_dfp = combined['_ORIGEM'] == 'DFP'
    combined.loc[mask_dfp, 'VL_CONTA'] = (
        combined.loc[mask_dfp, 'VL_CONTA']
        - combined.loc[mask_dfp, '_t1'].fillna(0)
        - combined.loc[mask_dfp, '_t2'].fillna(0)
        - combined.loc[mask_dfp, '_t3'].fillna(0)
    )
    combined = combined.drop(columns=['_ORIGEM', '_t1', '_t2', '_t3'])
    return combined.sort_values(chave)

base_dre    = montar_base_trimestral(dre, dfp_dre)
base_fluxo  = montar_base_trimestral(dfc, dfp_dfc)
base_balanco = pd.concat([bpa, bpp, dfp_bpa, dfp_bpp], ignore_index=True)
chave = ['DENOM_CIA', 'CD_CONTA', 'DT_FIM_EXERC']
empresas_dfp = set(dfp_bpa['DENOM_CIA'].unique()) | set(dfp_bpp['DENOM_CIA'].unique())
base_balanco['_ORIGEM'] = base_balanco['DENOM_CIA'].apply(
    lambda x: 'DFP' if x in empresas_dfp else 'ITR'
)
base_balanco = base_balanco.sort_values(chave + ['_ORIGEM'])
base_balanco = base_balanco.drop_duplicates(subset=chave, keep='first')
base_balanco = base_balanco.drop(columns=['_ORIGEM'])
base_final   = pd.concat([base_dre, base_balanco, base_fluxo], ignore_index=True)
# Texto sempre tem prioridade: guarda índices que tratar() já marcou como D&A
_da_idx = base_final.index[base_final['Conta'] == 'Depreciacacao_Amortizacao']
base_final['Conta'] = base_final['CD_CONTA'].map(mapa)
# Restaura D&A em todos os índices marcados — texto prevalece sobre código
base_final.loc[_da_idx, 'Conta'] = 'Depreciacacao_Amortizacao'
dados_financeiros = base_final.pivot_table(
    index=['DENOM_CIA', 'DT_FIM_EXERC'],
    columns='Conta',
    values='VL_CONTA',
    aggfunc='sum'
).reset_index()
dados_financeiros = dados_financeiros.sort_values(['DENOM_CIA', 'DT_FIM_EXERC'])

# 2. Cálculos
# ====================================================================================================================================================================================================
# 2.1 Dados Demonstrativos Financeiros
# ====================================================================================================================================================================================================
dados_financeiros['Divida Bruta']   = dados_financeiros.get('Divida Curto Prazo', 0).fillna(0) + dados_financeiros.get('Divida Longo Prazo', 0).fillna(0)
dados_financeiros['Divida Liquida'] = dados_financeiros['Divida Bruta'] - dados_financeiros.get('Caixa', 0).fillna(0) - dados_financeiros.get('Aplicacoes', 0).fillna(0)
# EBITDA corrigido: EBIT + D&A (depreciação e amortização da DRE, conta 3.06.01)
dados_financeiros['EBITDA'] = (
    dados_financeiros['EBIT'].fillna(0)
    + dados_financeiros['Depreciacacao_Amortizacao'].fillna(0).abs()
)
# FCF = FCO (operacional) + FCI (investimento) — FCI é negativo para investimentos
dados_financeiros['FCF'] = dados_financeiros.get('FCO', 0).fillna(0) + dados_financeiros.get('FCI', 0).fillna(0)

for col in ['Receita', 'EBIT', 'EBT', 'imposto total', 'EBITDA', 'Lucro Liquido', 'Lucro Bruto', 'FCO', 'FCF']:
    if col in dados_financeiros.columns:
        dados_financeiros[f'{col}_TTM'] = (
            dados_financeiros.groupby('DENOM_CIA')[col]
            .rolling(4, min_periods=4).sum().reset_index(0, drop=True)
        )
for col in ['Receita', 'EBIT', 'EBT', 'imposto total', 'EBITDA', 'Lucro Liquido', 'Lucro Bruto', 'Despesa Financeira']:
    if col in dados_financeiros.columns:
        dados_financeiros[f'{col}_36M'] = (
            dados_financeiros.groupby('DENOM_CIA')[col]
            .rolling(12, min_periods=12).sum().reset_index(0, drop=True)
        )

dados_financeiros['Mg Bruta 36M']   = dados_financeiros['Lucro Bruto_36M']  / dados_financeiros['Receita_36M']
dados_financeiros['Mg EBITDA 36M']  = dados_financeiros['EBITDA_36M']        / dados_financeiros['Receita_36M']
dados_financeiros['Mg EBIT 36M']    = dados_financeiros['EBIT_36M']           / dados_financeiros['Receita_36M']
dados_financeiros['Mg Liquida 36M'] = dados_financeiros['Lucro Liquido_36M'] / dados_financeiros['Receita_36M']
dados_financeiros['Estrutura de Capital (D/D+E)'] = dados_financeiros['Divida Bruta'] / (
    dados_financeiros['Divida Bruta'] + dados_financeiros.get('Patrimonio Liquido', pd.Series(0, index=dados_financeiros.index)).fillna(0)
)
dados_financeiros['DivLiquida/EBITDA']  = dados_financeiros['Divida Liquida'] / dados_financeiros['EBITDA_TTM']
dados_financeiros['DivLiquida/DespFin'] = dados_financeiros['Divida Liquida'] / dados_financeiros['Despesa Financeira_36M']

for col in ['Patrimonio Liquido', 'Ativo Total', 'Divida Bruta']:
    dados_financeiros[f'{col}_media'] = (
        dados_financeiros.groupby('DENOM_CIA')[col]
        .rolling(5, min_periods=1).mean().reset_index(0, drop=True)
    )
dados_financeiros['Capital_Investido_media'] = dados_financeiros['Divida Bruta_media'] + dados_financeiros['Patrimonio Liquido_media']
dados_financeiros['ROE']        = dados_financeiros['Lucro Liquido_TTM'] / dados_financeiros['Patrimonio Liquido_media']
dados_financeiros['ROA']        = dados_financeiros['Lucro Liquido_TTM'] / dados_financeiros['Ativo Total_media']
dados_financeiros['aliquota_ir']= -dados_financeiros['imposto total']    / dados_financeiros['EBT_TTM']
dados_financeiros['ROIC']       = (dados_financeiros['EBIT_TTM'] * (1 - dados_financeiros['aliquota_ir'])) / dados_financeiros['Capital_Investido_media']
dados_financeiros['Liquidez Corrente'] = dados_financeiros['Ativo Circulante'] / dados_financeiros['Passivo Circulante']

_estoques = dados_financeiros['Estoques'].fillna(0) if 'Estoques' in dados_financeiros.columns else 0
_caixa    = dados_financeiros.get('Caixa', pd.Series(0, index=dados_financeiros.index)).fillna(0)
_aplic    = dados_financeiros.get('Aplicacoes', pd.Series(0, index=dados_financeiros.index)).fillna(0)
_pc       = dados_financeiros['Passivo Circulante'].replace(0, np.nan)
dados_financeiros['Liquidez Seca']     = (dados_financeiros['Ativo Circulante'].fillna(0) - _estoques) / _pc
dados_financeiros['Liquidez Imediata'] = (_caixa + _aplic) / _pc

if 'Despesa Financeira' in dados_financeiros.columns:
    dados_financeiros['Despesa Financeira_TTM'] = (
        dados_financeiros.groupby('DENOM_CIA')['Despesa Financeira']
        .rolling(4, min_periods=4).sum().reset_index(0, drop=True)
    )

if 'Lucro Bruto_TTM' in dados_financeiros.columns:
    dados_financeiros['Mg Bruta TTM']   = dados_financeiros['Lucro Bruto_TTM']   / dados_financeiros['Receita_TTM'].replace(0, np.nan)
    dados_financeiros['Mg EBITDA TTM']  = dados_financeiros['EBITDA_TTM']         / dados_financeiros['Receita_TTM'].replace(0, np.nan)
    dados_financeiros['Mg Liquida TTM'] = dados_financeiros['Lucro Liquido_TTM']  / dados_financeiros['Receita_TTM'].replace(0, np.nan)

dados_financeiros['DivBruta_EBITDA'] = dados_financeiros['Divida Bruta'] / dados_financeiros['EBITDA_TTM'].replace(0, np.nan)

# =========================================
# 2.2 Dados Ativos
# =========================================
dados_cp["ativo"] = dados_cp["ativo"].astype(str).str.upper().str.strip()
ntnb_ref["Código"] = ntnb_ref["Código"].astype(str).str.upper().str.strip()
dados_carteira["ticker_cmd_puro"] = dados_carteira["ticker_cmd_puro"].astype(str).str.upper().str.strip()

ntnb_ref["Referência NTN-B"] = pd.to_datetime(ntnb_ref["Referência NTN-B"], dayfirst=True, errors="coerce")
dados_cp = dados_cp.merge(
    ntnb_ref[["Código", "Referência NTN-B"]].rename(columns={"Código": "ativo", "Referência NTN-B": "ntnb_ref"}),
    on="ativo", how="left"
)

tit_pub_ntnb = tit_pub[tit_pub["Tipo Titulo"].str.strip().isin(["Tesouro IPCA+ com Juros Semestrais", "Tesouro IPCA+"])].copy()
tit_pub_ntnb["Data Vencimento"] = pd.to_datetime(tit_pub_ntnb["Data Vencimento"], errors="coerce").dt.normalize()
tit_pub_ntnb["Data"]            = pd.to_datetime(tit_pub_ntnb["Data"],            errors="coerce").dt.normalize()
dados_cp["ntnb_ref"] = pd.to_datetime(dados_cp["ntnb_ref"], errors="coerce").dt.normalize()
dados_cp["Data"]     = pd.to_datetime(dados_cp["Data"],     errors="coerce").dt.normalize()

tit_pub_ntnb["_prioridade"] = tit_pub_ntnb["Tipo Titulo"].map({
    "Tesouro IPCA+ com Juros Semestrais": 0,
    "Tesouro IPCA+": 1
})
tit_pub_ntnb = (
    tit_pub_ntnb
    .sort_values(["Data", "Data Vencimento", "_prioridade"])
    .drop_duplicates(subset=["Data", "Data Vencimento"], keep="first")
    .drop(columns=["_prioridade"])
)

# ── Merge taxa NTN-B: usa merge exato e preenche gaps com ffill por vencimento ──
_ntnb_taxa = (
    tit_pub_ntnb[["Data", "Data Vencimento", "Taxa Compra Manha"]]
    .rename(columns={"Data Vencimento": "ntnb_ref", "Taxa Compra Manha": "taxa_ntnb"})
    .copy()
)
# Merge exato primeiro
dados_cp = dados_cp.merge(_ntnb_taxa, on=["Data", "ntnb_ref"], how="left")

# Para linhas com ntnb_ref preenchida mas taxa_ntnb ainda NaN (gaps de pregão),
# aplica forward-fill por vencimento: pivota _ntnb_taxa em calendário completo por ntnb_ref
_sem_taxa_mask = dados_cp["ntnb_ref"].notna() & dados_cp["taxa_ntnb"].isna()
if _sem_taxa_mask.any():
    # Cria lookup: para cada (ntnb_ref, Data) → taxa_ntnb preenchida por ffill
    _taxa_pivot = (
        _ntnb_taxa
        .sort_values(["ntnb_ref", "Data"])
        .set_index(["ntnb_ref", "Data"])["taxa_ntnb"]
    )
    def _get_taxa_ffill(row):
        if pd.isna(row["ntnb_ref"]):
            return np.nan
        try:
            idx = _taxa_pivot.loc[row["ntnb_ref"]]
            # Pega a última taxa disponível <= Data
            valid = idx[idx.index <= row["Data"]]
            return valid.iloc[-1] if len(valid) > 0 else np.nan
        except KeyError:
            return np.nan
    dados_cp.loc[_sem_taxa_mask, "taxa_ntnb"] = dados_cp[_sem_taxa_mask].apply(_get_taxa_ffill, axis=1)

_mask_spread = dados_cp["ntnb_ref"].notna() & dados_cp["valor"].notna() & dados_cp["taxa_ntnb"].notna()
dados_cp["spread"] = np.where(_mask_spread, dados_cp["valor"] - dados_cp["taxa_ntnb"], np.nan)
dados_cp["spread"] = pd.to_numeric(dados_cp["spread"], errors="coerce")
dados_cp = dados_cp.sort_values(["ativo", "Data"])

# ── DIAGNÓSTICO SPREAD ────────────────────────────────────────────────────
_n_com_ntnb  = dados_cp["ntnb_ref"].notna().sum()
_n_com_taxa  = dados_cp["taxa_ntnb"].notna().sum()
_n_com_spread= dados_cp["spread"].notna().sum()
print(f"[SPREAD] Linhas com ntnb_ref:  {_n_com_ntnb}")
print(f"[SPREAD] Linhas com taxa_ntnb: {_n_com_taxa}")
print(f"[SPREAD] Linhas com spread:    {_n_com_spread}")
# Mostra datas disponíveis no tit_pub vs datas em dados_cp para debug
_datas_cp   = sorted(dados_cp["Data"].dropna().unique())
_datas_ntnb = sorted(tit_pub_ntnb["Data"].dropna().unique())
if len(_datas_cp) and len(_datas_ntnb):
    print(f"[SPREAD] Última data em dados_cp:       {_datas_cp[-1]}")
    print(f"[SPREAD] Última data em tit_pub_ntnb:   {_datas_ntnb[-1]}")
    _overlap = set(str(d)[:10] for d in _datas_cp) & set(str(d)[:10] for d in _datas_ntnb)
    print(f"[SPREAD] Datas em comum (YYYY-MM-DD):   {len(_overlap)}")
# Mostra exemplo de linha que tem ntnb_ref mas taxa_ntnb NaN
_sem_taxa = dados_cp[dados_cp["ntnb_ref"].notna() & dados_cp["taxa_ntnb"].isna()]
if len(_sem_taxa):
    ex = _sem_taxa.iloc[0]
    print(f"[SPREAD] Exemplo sem taxa: ativo={ex['ativo']} Data={ex['Data']} ntnb_ref={ex['ntnb_ref']}")
# ─────────────────────────────────────────────────────────────────────────
def mad(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    if len(x) == 0:
        return np.nan
    med = np.median(x)
    return np.median(np.abs(x - med))

stats_gerais = (
    dados_cp
    .groupby("ativo")
    .agg(
        mediana_valor=("valor",  "median"),
        std_valor=("valor",      "std"),
        mad_valor=("valor",      mad),
        mediana_spread=("spread","median"),
        std_spread=("spread",    "std"),
        mad_spread=("spread",    mad)
    )
    .assign(
        mediana_mais_1dp_valor=lambda df: df["mediana_valor"] + df["std_valor"],
        mediana_menos_1dp_valor=lambda df: df["mediana_valor"] - df["std_valor"],
        mediana_mais_1mad_valor=lambda df: df["mediana_valor"] + df["mad_valor"],
        mediana_menos_1mad_valor=lambda df: df["mediana_valor"] - df["mad_valor"],
        mediana_mais_1dp_spread=lambda df: df["mediana_spread"] + df["std_spread"],
        mediana_menos_1dp_spread=lambda df: df["mediana_spread"] - df["std_spread"],
        mediana_mais_1mad_spread=lambda df: df["mediana_spread"] + df["mad_spread"],
        mediana_menos_1mad_spread=lambda df: df["mediana_spread"] - df["mad_spread"]
    )
    .reset_index()
)

dados_cp["mm21_valor"]  = dados_cp.groupby("ativo")["valor"].transform(lambda x: x.rolling(21, min_periods=21).mean())
dados_cp["mm21_spread"] = dados_cp.groupby("ativo")["spread"].transform(lambda x: x.rolling(21, min_periods=21).mean())
# Evita merge (cópia full do DataFrame) — usa map por coluna para não estourar RAM
_sg = stats_gerais.set_index("ativo")
for _col in _sg.columns:
    dados_cp[_col] = dados_cp["ativo"].map(_sg[_col])
dados_cp["zscore_valor"] = (dados_cp["valor"] - dados_cp["mediana_valor"]) / dados_cp["std_valor"]

# ===========================================================================================================================================================
# 3. GERAÇÃO DO HTML — OVERVIEW CRÉDITO
# ===========================================================================================================================================================
tipos_credito = ["cri", "cra", "cdca", "debenture"]


print(dados_carteira.head(10))
print(dados_cp.head(10))

pl_total = dados_carteira["saldo bruto"].fillna(0).sum()
pl_total_js = json.dumps(float(pl_total))

pl_por_carteira = (
    dados_carteira
    .groupby("carteira")["saldo bruto"]
    .sum()
    .fillna(0)
    .to_dict()
)
pl_por_carteira = {
    str(k): float(v)
    for k, v in pl_por_carteira.items()
}

pl_por_carteira_js = json.dumps(
    pl_por_carteira,
    ensure_ascii=False
)

dados_carteira_credito = dados_carteira[
    dados_carteira["tipo ativo"].astype(str).str.lower().str.strip().isin(tipos_credito)
].copy()

cols_carteira = ["carteira", "ticker_cmd_puro", "emissor", "duration(a,a,u)", "saldo bruto"]
df_cart = dados_carteira_credito[cols_carteira].copy().rename(columns={
    "ticker_cmd_puro": "ticker",
    "duration(a,a,u)": "duration",
    "saldo bruto":     "saldo"
})

df_cart["duration"] = pd.to_numeric(df_cart["duration"], errors="coerce").fillna(0)

if "classe" in dados_carteira.columns:
    classe_map = (
        dados_carteira[["ticker_cmd_puro", "classe"]]
        .drop_duplicates(subset=["ticker_cmd_puro"])
        .set_index("ticker_cmd_puro")["classe"]
    )
    df_cart["classe"] = df_cart["ticker"].map(classe_map)
elif "minha_variavel(classe_ativos)" in dados_carteira.columns:
    classe_map = (
        dados_carteira[["ticker_cmd_puro", "minha_variavel(classe_ativos)"]]
        .drop_duplicates(subset=["ticker_cmd_puro"])
        .rename(columns={"minha_variavel(classe_ativos)": "classe"})
        .set_index("ticker_cmd_puro")["classe"]
    )
    df_cart["classe"] = df_cart["ticker"].map(classe_map)
else:
    df_cart["classe"] = "Renda Fixa"
df_cart["classe"] = df_cart["classe"].fillna("Renda Fixa")

rating_setor_clean = (
    rating_setor
    .rename(columns={"nome": "emissor"})[["emissor", "Rating base S&P", "setor"]]
    .drop_duplicates(subset=["emissor"])
    .dropna(subset=["emissor"])
)
rank_corp_clean = (
    ranking_corporativo[["Empresa", "Status", "Rating Douro"]]
    .rename(columns={"Empresa": "emissor"})
    .drop_duplicates(subset=["emissor"])
    .dropna(subset=["emissor"])
)

df_cart = df_cart.merge(rating_setor_clean, on="emissor", how="left")
df_cart["Rating base S&P"] = df_cart["Rating base S&P"].fillna("N/D")
df_cart["setor"]            = df_cart["setor"].fillna("Outros")
df_cart = df_cart.merge(rank_corp_clean, on="emissor", how="left")
df_cart["Status"]       = df_cart["Status"].fillna("N/D")
df_cart["Rating Douro"] = df_cart["Rating Douro"].fillna("N/D")

if "spread" in dados_cp.columns and "ativo" in dados_cp.columns:
    _last_valid = lambda s: s.dropna().iloc[-1] if s.dropna().shape[0] > 0 else None
    spread_atual = (
        dados_cp.sort_values("Data")
        .groupby("ativo")
        .agg(spread=("spread", _last_valid), valor=("valor", _last_valid), ntnb_ref=("ntnb_ref", _last_valid))
        .reset_index()
        .rename(columns={"ativo": "ticker"})
    )
    df_cart = df_cart.merge(spread_atual, on="ticker", how="left")
else:
    df_cart["spread"] = None
    df_cart["valor"]  = None

df_cart["spread"] = pd.to_numeric(df_cart["spread"], errors="coerce")
df_cart["valor"]  = pd.to_numeric(df_cart["valor"],  errors="coerce")

n_spread = df_cart["spread"].notna().sum()
n_total  = len(df_cart)
print(f"Ativos exportados:   {n_total}")
print(f"Ativos com spread:   {n_spread} / {n_total} ({100*n_spread/n_total:.1f}%)" if n_total else "")
print(f"Saldo total crédito: R$ {df_cart['saldo'].sum():,.0f}")
print(f"PL total carteira:   R$ {pl_total:,.0f}")

# Mapear officer
officer_map = (
    dados_carteira[["ticker_cmd_puro", "officer"]]
    .drop_duplicates(subset=["ticker_cmd_puro"])
    .set_index("ticker_cmd_puro")["officer"]
).str.replace(".", "", regex=False)

df_cart["officer"] = df_cart["ticker"].map(officer_map).fillna("N/D")

cols_export = [
    "carteira", "ticker", "emissor", "setor", "classe",
    "saldo", "duration", "Rating base S&P", "Rating Douro",
    "Status", "spread", "valor", "ntnb_ref", "officer"
]
df_export = df_cart[[c for c in cols_export if c in df_cart.columns]].copy()
for col in df_export.columns:
    if str(df_export[col].dtype).startswith("datetime"):
        df_export[col] = df_export[col].dt.strftime("%d/%m/%Y").where(df_export[col].notna(), None)
df_export = df_export.where(pd.notnull(df_export), None)

ativos_json = df_export.to_dict(orient="records")
ativos_js   = json.dumps(ativos_json, default=str, ensure_ascii=False)

rank_corp_json = []
for _, row in ranking_corporativo.iterrows():
    emp = row.get("Empresa", "")
    if pd.isna(emp) or emp == "":
        continue
    setor_info = rating_setor_clean[rating_setor_clean["emissor"] == emp]
    setor_val  = setor_info["setor"].values[0]           if len(setor_info) > 0 else "N/D"
    rating_sp  = setor_info["Rating base S&P"].values[0] if len(setor_info) > 0 else "N/D"
    rank_corp_json.append({
        "empresa":     emp,
        "setor":       setor_val,
        "ratingMkt":   str(rating_sp),
        "ratingDouro": str(row.get("Rating Douro", "N/D")),
        "status":      str(row.get("Status",       "N/D")),
    })

rank_bancos_json = []
for _, row in ranking_bancos.iterrows():
    emp = row.get("Empresa", "")
    if pd.isna(emp) or emp == "":
        continue
    rank_bancos_json.append({
        "empresa":     emp,
        "ratingDouro": str(row.get("Rating Douro", "N/D")),
        "status":      str(row.get("Status",       "N/D")),
    })

fin_cols_base = [c for c in [
    "DENOM_CIA", "DT_FIM_EXERC", "CNPJ_CIA",
    "Receita_TTM", "EBITDA_TTM", "Mg EBITDA 36M", "Mg Bruta 36M",
    "DivLiquida/EBITDA", "Estrutura de Capital (D/D+E)",
    "ROE", "ROA", "ROIC", "Liquidez Corrente",
    "Divida Liquida", "FCF_TTM", "Lucro Liquido_TTM",
    # Fundamentos extras
    "Mg Bruta TTM", "Mg EBITDA TTM", "Mg Liquida TTM",
    "Divida Bruta", "DivBruta_EBITDA", "Despesa Financeira_TTM",
    "Liquidez Seca", "Liquidez Imediata",
    "FCO", "FCI", "FCF",
] if c in dados_financeiros.columns]

def limpa_cnpj(x):
    if pd.isna(x):
        return None
    return re.sub(r"\D", "", str(x))

def limpa_nome(x):
    if pd.isna(x):
        return None
    return str(x).strip().upper()

cad_cvm["CNPJ_CIA_LIMPO"]     = cad_cvm["CNPJ_CIA"].apply(limpa_cnpj)
cad_cvm["DENOM_SOCIAL_UPPER"] = cad_cvm["DENOM_SOCIAL"].apply(limpa_nome)
cad_cvm["DENOM_COMERC_UPPER"] = cad_cvm["DENOM_COMERC"].apply(limpa_nome)
cad_cvm = cad_cvm[["CNPJ_CIA_LIMPO", "DENOM_SOCIAL_UPPER", "DENOM_COMERC_UPPER", "SETOR_ATIV"]].drop_duplicates()

df_fin = dados_financeiros[fin_cols_base].copy()
df_fin["DT_FIM_EXERC"] = pd.to_datetime(df_fin["DT_FIM_EXERC"]).dt.strftime("%Y-%m-%d")
df_fin["CNPJ_CIA_LIMPO"]   = df_fin["CNPJ_CIA"].apply(limpa_cnpj) if "CNPJ_CIA" in df_fin.columns else None
df_fin["DENOM_CIA_UPPER"]  = df_fin["DENOM_CIA"].apply(limpa_nome)

df_fin = df_fin.merge(cad_cvm[["CNPJ_CIA_LIMPO", "SETOR_ATIV"]].drop_duplicates(), on="CNPJ_CIA_LIMPO", how="left")

mask_sem_setor = df_fin["SETOR_ATIV"].isna()
merge_social = df_fin.loc[mask_sem_setor].merge(
    cad_cvm[["DENOM_SOCIAL_UPPER", "SETOR_ATIV"]].drop_duplicates(),
    left_on="DENOM_CIA_UPPER", right_on="DENOM_SOCIAL_UPPER", how="left", suffixes=("", "_cad")
)
merge_comerc = df_fin.loc[mask_sem_setor].merge(
    cad_cvm[["DENOM_COMERC_UPPER", "SETOR_ATIV"]].drop_duplicates(),
    left_on="DENOM_CIA_UPPER", right_on="DENOM_COMERC_UPPER", how="left", suffixes=("", "_cad")
)
df_fin.loc[mask_sem_setor, "SETOR_ATIV"] = merge_comerc["SETOR_ATIV_cad"].values
df_fin.loc[mask_sem_setor, "SETOR_ATIV"] = merge_social["SETOR_ATIV_cad"].values

mask_sem_setor = df_fin["SETOR_ATIV"].isna()
merge_comerc2 = df_fin.loc[mask_sem_setor].merge(
    cad_cvm[["DENOM_COMERC_UPPER", "SETOR_ATIV"]].drop_duplicates(),
    left_on="DENOM_CIA_UPPER", right_on="DENOM_COMERC_UPPER", how="left"
)
df_fin.loc[mask_sem_setor, "SETOR_ATIV"] = merge_comerc2["SETOR_ATIV_y"].values
df_fin["SETOR_ATIV"] = df_fin["SETOR_ATIV"].fillna("Não Informado")

fin_series = {}
for emp in df_fin["DENOM_CIA"].unique():
    match = df_fin[df_fin["DENOM_CIA"] == emp].sort_values("DT_FIM_EXERC")
    if len(match) == 0:
        continue
    rec = {}
    for col in fin_cols_base:
        if col in ["DENOM_CIA", "DT_FIM_EXERC"]:
            continue
        rec[col] = match[col].where(pd.notnull(match[col]), None).tolist()
    rec["datas"] = match["DT_FIM_EXERC"].tolist()
    rec["setor"] = match["SETOR_ATIV"].iloc[-1]
    fin_series[emp] = rec
fin_series_js = json.dumps(fin_series, default=str)

setores_unicos = sorted(df_fin["SETOR_ATIV"].dropna().unique().tolist())
setores_js     = json.dumps(setores_unicos, ensure_ascii=False)
print("Quantidade de setores:", len(setores_unicos))

def safe_float(v):
    return float(v) if pd.notna(v) else None

spreads_ts = {}
if "spread" in dados_cp.columns and "ativo" in dados_cp.columns and "Data" in dados_cp.columns:
    dados_cp_sorted = dados_cp.sort_values("Data")
    for ativo_name, subset in dados_cp_sorted.groupby("ativo"):
        subset = subset.sort_values("Data").drop_duplicates("Data")
        subset = subset[subset["spread"].notna() | subset["valor"].notna()]
        if len(subset) == 0:
            continue
        spreads_ts[str(ativo_name)] = {
            "datas":                  subset["Data"].dt.strftime("%Y-%m-%d").tolist(),
            "spread":                 subset["spread"].where(pd.notnull(subset["spread"]), None).tolist(),
            "valor":                  subset["valor"].where(pd.notnull(subset["valor"]), None).tolist() if "valor" in subset.columns else [],
            "mm21_spread":            subset["mm21_spread"].where(pd.notnull(subset["mm21_spread"]), None).tolist() if "mm21_spread" in subset.columns else [],
            "mm21_valor":             subset["mm21_valor"].where(pd.notnull(subset["mm21_valor"]), None).tolist() if "mm21_valor" in subset.columns else [],
            "mediana_valor":          safe_float(subset["mediana_valor"].iloc[-1])          if "mediana_valor" in subset.columns else None,
            "mediana_mais_1mad_valor":safe_float(subset["mediana_mais_1mad_valor"].iloc[-1])if "mediana_mais_1mad_valor" in subset.columns else None,
            "mediana_menos_1mad_valor":safe_float(subset["mediana_menos_1mad_valor"].iloc[-1])if "mediana_menos_1mad_valor" in subset.columns else None,
            "mediana_spread":         safe_float(subset["mediana_spread"].iloc[-1])         if "mediana_spread" in subset.columns else None,
            "mediana_mais_1mad_spread":safe_float(subset["mediana_mais_1mad_spread"].iloc[-1])if "mediana_mais_1mad_spread" in subset.columns else None,
            "mediana_menos_1mad_spread":safe_float(subset["mediana_menos_1mad_spread"].iloc[-1])if "mediana_menos_1mad_spread" in subset.columns else None,
            "std_spread":             safe_float(subset["std_spread"].iloc[-1])             if "std_spread" in subset.columns else None,
        }

dados_carteiras_credito["Data"] = pd.to_datetime(dados_carteiras_credito["Data"])
pivot_perf = dados_carteiras_credito.pivot_table(index="Data", columns="ativo", values="valor").sort_index()
ret_acum   = ((1 + pivot_perf.fillna(0)).cumprod() - 1)
perf_json  = {"datas": ret_acum.index.strftime("%Y-%m-%d").tolist(), "ativos": {}}
for col in pivot_perf.columns:
    serie = pivot_perf[col].dropna()
    if len(serie) == 0:
        continue
    acum     = ((1 + serie).cumprod() - 1)
    vol      = serie.std() * np.sqrt(252)
    curva    = (1 + serie).cumprod()
    drawdown = (curva / curva.cummax() - 1).min()
    perf_json["ativos"][col] = {
        "retornos":    serie.tolist(),
        "retorno_acum":acum.tolist(),
        "datas":       serie.index.strftime("%Y-%m-%d").tolist(),
        "vol":         float(vol),
        "drawdown":    float(drawdown),
        "ret_total":   float(acum.iloc[-1])
    }
corr_matrix = pivot_perf.corr()
perf_json["correlacao"] = {
    "labels": corr_matrix.columns.tolist(),
    "values": corr_matrix.fillna(0).values.tolist()
}
perf_js = json.dumps(perf_json, ensure_ascii=False)

bonds_info = []
status_map = {}
for _, row in ranking_corporativo.iterrows():
    emp = str(row.get("Empresa", "")).strip().upper()
    if emp:
        status_map[emp] = str(row.get("Status", "N/D"))
if "ativo" in dados_bonds.columns:
    ativos_bonds = dados_bonds["ativo"].dropna().unique()
    for ativo in ativos_bonds:
        nome_quebrado  = str(ativo).split(" ")
        emissor_approx = nome_quebrado[0].upper() if len(nome_quebrado) > 0 else "N/D"
        saldo          = dados_carteira.loc[dados_carteira["ticker_cmd_puro"] == ativo, "saldo bruto"].sum()
        status_final   = "N/D"
        emissor_final  = str(ativo).split(" ")[0]
        for emp_key, status_val in status_map.items():
            if emissor_approx in emp_key or emp_key in emissor_approx:
                status_final  = status_val
                emissor_final = emp_key.title()
                break
        bonds_info.append({
            "ativo":    str(ativo),
            "emissor":  emissor_final,
            "status":   status_final,
            "saldo":    float(saldo) if pd.notna(saldo) else 0.0
        })
bonds_ts = {}
if "ativo" in dados_bonds.columns and "Data" in dados_bonds.columns:
    for ativo_name, subset in dados_bonds.sort_values("Data").groupby("ativo"):
        subset_clean = subset.dropna(subset=["valor"])
        if len(subset_clean) > 0:
            bonds_ts[str(ativo_name)] = {
                "datas": subset_clean["Data"].dt.strftime("%Y-%m-%d").tolist(),
                "valor": subset_clean["valor"].tolist()
            }

bonds_info_js  = json.dumps(bonds_info,       default=str, ensure_ascii=False)
bonds_ts_js    = json.dumps(bonds_ts,          default=str, ensure_ascii=False)
ativos_js      = json.dumps(ativos_json,       default=str, ensure_ascii=False)
rank_corp_js   = json.dumps(rank_corp_json,    default=str, ensure_ascii=False)
rank_bancos_js = json.dumps(rank_bancos_json,  default=str, ensure_ascii=False)
spreads_ts_js  = json.dumps(spreads_ts,        default=str, ensure_ascii=False)

# ── BCB IF.DATA — INDICADORES BANCÁRIOS ──────────────────────────────────────
def _fetch_bcb_bancos():
    """Busca indicadores BCB IF.data. Chaves = nomes exatos do Watch List Bancos.xlsm."""

    # Códigos IF.data → nome EXATO da coluna "Empresa" do Watch List Bancos.xlsm
    # A chave é o CodInst do BCB; o valor é o nome que será usado como chave no JS (deve bater com RANK_BANCOS)
    BANCOS_BCB = {
        'C0083694': 'AGIBANK',
        'C0081256': 'ANDBANK',
        'C0080312': 'Banco ABC',
        'C0084480': 'BANCO BRASILEIRO',
        'C0081328': 'BDMG',
        'C0080178': 'Banco BMG',
        'C0084624': 'BOCOM BBM',
        'C0080336': 'BTG Pactual',
        'C0080484': 'Banco BV',
        'C0084844': 'Banco C6',
        'C0080738': 'Caixa',
        'C0081407': 'CNH Capital',
        'C0081744': 'Daycoval',
        'C0081799': 'Banco Digimais',
        'C0080329': 'BANCO DO BRASIL',
        'C0081593': 'Banco do Nordeste',
        'C0083704': 'Facta Financeira',
        'C0081483': 'BANCO FIBRA',
        'C0080848': 'Banco GM',
        'C0084741': 'BANCO HSBC',
        'C0080996': 'BANCO INTER',
        'C0080343': 'John Deere',
        'C0080116': 'JP MORGAN CHASE',
        'C0081706': 'BANCO LUSO BRASILEIRO',
        'C0080123': 'Mercantil do Brasil',
        'C0081768': 'Novo Banco Continental',
        'C0080460': 'OMNI',
        'C0084813': 'PAGBANK',
        'C0088022': 'Picpay',
        'C0080374': 'BANCO PINE',
        'C0080075': 'Bradesco',
        'C0080099': 'Itaú',
        'C0080185': 'SANTANDER',
        'C0080855': 'BANCO RODOBENS',
        'C0081555': 'RABOBANK',
        'C0080745': 'SICREDI',
        'C0080903': 'Banco Original',
        'C0080109': 'BANCO SAFRA',
        'C0087298': 'BANCO STELLANTIS',
        'C0081562': 'BANCO TOYOTA DO BRASIL',
        'C0080202': 'BANCO VOLKSWAGEN',
        'C0082475': 'XP Investimentos',
    }

    # Lookup direto: código BCB → nome exato do Watch List (sem fuzzy)
    # Se o ranking_bancos tiver uma coluna com o código BCB, usa ela; senão usa o dicionário acima diretamente
    bancos_mapeados = dict(BANCOS_BCB)  # cód → nome exato Watch List

    ANOS = ['2021', '2022', '2023', '2024']
    PERIODOS_DEC = ['202112', '202212', '202312', '202412']

    # Constantes das contas (espelha Scorecard Bancos.py)
    CH_BASILEIA = ["Índice de Basileia / (n) = (e) / (j)", "Índice de Basileia (n) = (e) / (j)", "Índice de Basileia"]
    CH_ALAVANC  = ["Razão de Alavancagem / (o) = (c) / (k)", "Razão de Alavancagem (o) = (c) / (k)", "Razão de Alavancagem"]
    CH_IMOB     = ["Índice de Imobilização / (p)", "Índice de Imobilização (p)", "Índice de Imobilização"]
    CH_PL_ATIVO = ["Patrimônio Líquido / (i)", "Patrimônio Líquido (i)", "Patrimônio Líquido"]
    CH_PROV     = ["Resultado de Provisão para Créditos de Difícil Liquidação / (b5)",
                   "Resultado de Provisão para Créditos de Difícil Liquidação (b5)",
                   "Resultado de Provisão para Créditos de Difícil Liquidação"]
    CH_OCRED    = ["Operações de Crédito / (d1)", "Operações de Crédito (d1)", "Operações de Crédito"]
    CH_LUCRO    = ["Lucro Líquido / (j) = (g) + (h) + (i)", "Lucro Líquido (j) = (g) + (h) + (i)",
                   "Lucro Líquido / (j)", "Lucro Líquido (j)", "Lucro Líquido"]
    CH_EXP_O    = ["Despesas de Pessoal / (o)", "Despesas de Pessoal (o)", "Despesas de Pessoal"]
    CH_EXP_P    = ["Despesas Administrativas / (p)", "Despesas Administrativas (p)", "Despesas Administrativas"]
    CH_RES_IF   = ["Resultado de Intermediação Financeira / (k) = (a) + (b) + (c) + (d) + (e) + (f) + (g) + (h) + (i) + (j)",
                   "Resultado de Intermediação Financeira / (c) = (a) + (b)", "Resultado de Intermediação Financeira"]
    CH_REV_RPS  = ["Rendas de Prestação de Serviços / (d1)", "Rendas de Prestação de Serviços (d1)", "Rendas de Prestação de Serviços"]
    CH_REC_INT  = ["Receitas de Intermediação Financeira / (a)", "Receitas de Intermediação Financeira (a)", "Receitas de Intermediação Financeira"]
    # Provisão sobre Op. Crédito (saldo balanço, Rel.2 d2) — proxy de inadimplência esperada
    CH_PROV_BAL = ["Provisão sobre Operações de Crédito / (d2)",
                   "Provisão sobre Operações de Crédito (d2)",
                   "Provisão sobre Operações de Crédito"]

    def _norm_col(s):
        if not s:
            return ""
        s2 = str(s).replace("\r", "").replace("\n", " / ")
        return " ".join(s2.split()).strip()

    def _get_val(ser, chaves):
        if ser is None or len(ser) == 0:
            return None
        mapa = {_norm_col(k): v for k, v in ser.items()}
        for ch in chaves:
            alvo = _norm_col(ch)
            if alvo in mapa:
                return mapa[alvo]
            for k_norm, v in mapa.items():
                if k_norm.startswith(alvo):
                    return v
        return None

    def _baixa(relatorio_id, anomes, session, cods):
        url = (
            "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/"
            f"IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)?"
            f"@AnoMes={anomes}&@TipoInstituicao=1&@Relatorio='{relatorio_id}'"
            "&$top=100000&$format=json&$select=CodInst,NomeColuna,Saldo"
        )
        try:
            r = session.get(url, timeout=45)
            if r.status_code != 200:
                return {}
            dados = r.json().get("value", [])
            if not dados:
                return {}
            df = pd.DataFrame(dados)
            df = df[df["CodInst"].isin(cods)].copy()
            if df.empty:
                return {}
            grp = df.groupby(["CodInst", "NomeColuna"], as_index=False)["Saldo"].sum()
            resultado = {}
            for cod in cods:
                sub = grp[grp["CodInst"] == cod].set_index("NomeColuna")["Saldo"]
                if not sub.empty:
                    resultado[cod] = sub
            return resultado
        except Exception as ex:
            print(f"[BCB] Erro {relatorio_id}/{anomes}: {ex}")
            return {}

    cods = list(BANCOS_BCB.keys())
    bcb_result = {}  # nome_banco -> {anos, basileia, alav, imob, prov_ratio, eficiencia, roe, ml}

    print("[BCB] Baixando indicadores bancários do IF.data...")
    try:
        with requests.Session() as sess:
            # Por ano: baixar estrutura capital (basileia, alav, imob), ativo (PL, op crédito), DRE (lucro, eficiência)
            for ano, per in zip(ANOS, PERIODOS_DEC):
                print(f"[BCB] Período {per}...")
                est = _baixa('5', per, sess, cods)
                ati = _baixa('2', per, sess, cods)
                pas = _baixa('3', per, sess, cods)
                dre = _baixa('4', per, sess, cods)
                for cod in cods:
                    nome = bancos_mapeados[cod]
                    if nome not in bcb_result:
                        bcb_result[nome] = {
                            'anos': [], 'basileia': [], 'alav': [], 'imob': [],
                            'prov_ratio': [], 'npl': [], 'eficiencia': [], 'roe': [], 'ml': []
                        }

                    basileia = _get_val(est.get(cod), CH_BASILEIA)
                    alav     = _get_val(est.get(cod), CH_ALAVANC)
                    imob     = _get_val(est.get(cod), CH_IMOB)

                    pl = _get_val(ati.get(cod), CH_PL_ATIVO)
                    if pl is None:
                        pl = _get_val(pas.get(cod), CH_PL_ATIVO)

                    prov  = _get_val(dre.get(cod), CH_PROV)
                    ocred = _get_val(ati.get(cod), CH_OCRED)
                    prov_ratio = None
                    if prov is not None and ocred not in (None, 0):
                        prov_ratio = round(-prov / ocred * 100, 2)

                    # NPL proxy: Provisão sobre Op. Crédito (saldo balanço Rel.2 d2) / Op. Crédito (d1)
                    prov_bal = _get_val(ati.get(cod), CH_PROV_BAL)
                    npl = None
                    if prov_bal is not None and ocred not in (None, 0):
                        npl = round(abs(prov_bal) / abs(ocred) * 100, 2)

                    desp_p = _get_val(dre.get(cod), CH_EXP_O)
                    desp_a = _get_val(dre.get(cod), CH_EXP_P)
                    res_if = _get_val(dre.get(cod), CH_RES_IF)
                    rec_s  = _get_val(dre.get(cod), CH_REV_RPS)
                    total_d = (desp_p or 0) + (desp_a or 0) if (desp_p is not None or desp_a is not None) else None
                    total_r = (res_if or 0) + (rec_s or 0) if (res_if is not None or rec_s is not None) else None
                    efic = None
                    if total_d is not None and total_r not in (None, 0):
                        efic = round(abs(total_d) / float(total_r) * 100, 2)

                    lucro   = _get_val(dre.get(cod), CH_LUCRO)
                    rec_int = _get_val(dre.get(cod), CH_REC_INT)
                    roe = None
                    if lucro is not None and pl not in (None, 0):
                        roe_v = lucro / abs(pl) * 100
                        # BCB às vezes já retorna em %, às vezes como fração
                        roe = round(roe_v if abs(roe_v) > 0.5 else roe_v * 100, 2)
                    ml = None
                    if lucro is not None and rec_int not in (None, 0):
                        ml_v = lucro / abs(rec_int) * 100
                        ml = round(ml_v if abs(ml_v) > 0.5 else ml_v * 100, 2)

                    has_data = any(v is not None for v in [basileia, alav, efic, roe])
                    if has_data:
                        rec = bcb_result[nome]
                        if ano not in rec['anos']:
                            rec['anos'].append(ano)
                            # BCB retorna frações (0.145 = 14.5%) — converte para percentual
                            bas_v = float(basileia)
                            rec['basileia'].append(round(bas_v * 100 if bas_v < 2 else bas_v, 2) if basileia is not None else None)
                            rec['alav'].append(round(float(alav) * 100, 2) if alav is not None else None)
                            rec['imob'].append(round(float(imob) * 100, 2) if imob is not None else None)
                            rec['prov_ratio'].append(prov_ratio)
                            rec['npl'].append(npl)
                            rec['eficiencia'].append(efic)
                            rec['roe'].append(roe)
                            rec['ml'].append(ml)

        # Remover bancos sem nenhum dado
        bcb_result = {k: v for k, v in bcb_result.items() if v['anos']}
        print(f"[BCB] Dados obtidos para {len(bcb_result)} bancos.")
    except Exception as ex:
        print(f"[BCB] Falha geral: {ex}")
        bcb_result = {}

    # Fallback: se não conseguiu dados reais, retornar dict vazio (JS usa _BCB_DATA estático como fallback)
    return bcb_result

_bcb_bancos_data = _fetch_bcb_bancos()
bcb_bancos_js = json.dumps(_bcb_bancos_data, ensure_ascii=False, default=str)

# ── ALERTAS DE SPREAD/TAXA (janelas 1d, 7d, 21d) ─────────────────────────────
def _compute_alertas(spreads_ts_dict, threshold_bps=0.20):
    from datetime import timedelta as _td
    alertas = []
    for ticker, ts in spreads_ts_dict.items():
        raw_datas  = ts.get("datas", [])
        raw_spread = ts.get("spread", [])
        raw_valor  = ts.get("valor",  [])
        if not raw_datas:
            continue
        rows = []
        for i, d in enumerate(raw_datas):
            try:
                rows.append({
                    "data":   pd.Timestamp(d),
                    "spread": raw_spread[i] if i < len(raw_spread) else None,
                    "valor":  raw_valor[i]  if i < len(raw_valor)  else None,
                })
            except Exception:
                continue
        if not rows:
            continue
        df_ts = pd.DataFrame(rows).sort_values("data")
        for campo, field_key in [("spread", "spread"), ("taxa", "valor")]:
            df_use = df_ts.dropna(subset=[field_key])
            if len(df_use) < 2:
                continue
            last_val  = float(df_use[field_key].iloc[-1])
            last_data = df_use["data"].iloc[-1]
            for janela_label, dias in [("1d", 1), ("7d", 7), ("21d", 21)]:
                ref_dt = last_data - _td(days=dias)
                before = df_use[df_use["data"] <= ref_dt]
                if len(before) == 0:
                    continue
                ref_val = float(before[field_key].iloc[-1])
                var = last_val - ref_val
                if abs(var) < threshold_bps:
                    continue
                alertas.append({
                    "ticker":     ticker,
                    "tipo":       campo,
                    "janela":     janela_label,
                    "atual":      round(last_val, 4),
                    "ref":        round(ref_val,  4),
                    "variacao":   round(var, 4),
                    "data_atual": last_data.strftime("%d/%m/%Y"),
                    "data_ref":   ref_dt.strftime("%d/%m/%Y"),
                })
    alertas.sort(key=lambda x: abs(x["variacao"]), reverse=True)
    return alertas[:150]

try:
    alertas_data = _compute_alertas(spreads_ts)
    print(f"[Notificações] {len(alertas_data)} alertas de spread/taxa gerados.")
except Exception as _ae:
    print(f"[Notificações] Falha nos alertas: {_ae}")
    alertas_data = []
alertas_js = json.dumps(alertas_data, ensure_ascii=False)

# ── CVM FATOS RELEVANTES ──────────────────────────────────────────────────────
def _fetch_fatos_relevantes(df_fin, emissores_carteira, n_max=120):
    """Baixa Fatos Relevantes (dados abertos CVM) para os emissores da carteira."""
    ano_atual = datetime.now().year
    out = []

    def _norm(s):
        s = unicodedata.normalize("NFD", str(s).upper())
        return re.sub(r"[^A-Z0-9 ]", " ", "".join(
            c for c in s if unicodedata.category(c) != "Mn"
        )).strip()

    norms_carteira = {_norm(e): e for e in emissores_carteira if e}

    def _match_nome(nome_cvm_norm):
        words = set(nome_cvm_norm.split())
        for cart_norm, original in norms_carteira.items():
            cart_words = set(cart_norm.split())
            overlap = words & cart_words
            if overlap and len(overlap) >= max(1, len(cart_words) - 1):
                return original
        return None

    for ano in [ano_atual, ano_atual - 1]:
        url = (
            f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FATO_RELEVANTE/"
            f"DADOS/fato_relevante_cia_aberta_{ano}.zip"
        )
        try:
            resp = requests.get(url, timeout=25, verify=False)
            if resp.status_code != 200:
                continue
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                csv_name = next(n for n in z.namelist() if n.endswith(".csv"))
                with z.open(csv_name) as f:
                    df_fr = pd.read_csv(f, sep=";", encoding="latin1", dtype=str)
            if "DENOM_CIA" not in df_fr.columns or "DT_REFER" not in df_fr.columns:
                continue
            df_fr["_NORM"] = df_fr["DENOM_CIA"].apply(_norm)
            df_fr["_MATCH"] = df_fr["_NORM"].apply(_match_nome)
            df_fr = df_fr[df_fr["_MATCH"].notna()].copy()
            if df_fr.empty:
                continue
            df_fr["DT_REFER"] = pd.to_datetime(df_fr["DT_REFER"], errors="coerce")
            df_fr = df_fr.sort_values("DT_REFER", ascending=False)
            for _, row in df_fr.head(n_max).iterrows():
                link = str(row.get("LINK_DOC", "")).strip()
                assunto = str(row.get("ASSUNTO", "Fato Relevante")).strip()[:200]
                out.append({
                    "empresa":    str(row["_MATCH"]),
                    "denom_cvm":  str(row.get("DENOM_CIA", "")),
                    "assunto":    assunto if assunto else "Fato Relevante",
                    "data":       row["DT_REFER"].strftime("%d/%m/%Y") if pd.notna(row["DT_REFER"]) else "—",
                    "link":       link if link.startswith("http") else "",
                })
        except Exception as _e:
            print(f"[CVM] Erro FR {ano}: {_e}")

    # Deduplication
    seen, deduped = set(), []
    for item in out:
        key = (item["empresa"], item["assunto"][:60], item["data"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    deduped.sort(key=lambda x: x["data"], reverse=True)
    return deduped[:n_max]

_emissores_cart = list({a.get("emissor", "") for a in ativos_json if a.get("emissor")})
print(f"[CVM] Buscando Fatos Relevantes para {len(_emissores_cart)} emissores...")
try:
    _fatos_data = _fetch_fatos_relevantes(dados_financeiros, _emissores_cart)
    print(f"[CVM] {len(_fatos_data)} Fatos Relevantes encontrados.")
except Exception as _fre:
    print(f"[CVM] Falha: {_fre}")
    _fatos_data = []
fatos_relevantes_js = json.dumps(_fatos_data, ensure_ascii=False)

# ── DOURO NEWS DATA ──────────────────────────────────────────────────────────
print("[Douro News] Iniciando pipeline de notícias...")
try:
    _news_data = _news_pipeline()
except Exception as _ne:
    print(f"[Douro News] Pipeline falhou: {_ne}")
    _news_data = {"noticias":[],"ctx":{},"rf":{},"insight":{},"livro":{},"filme":None,"data":"","dia":"","hora":""}
news_js = json.dumps(_news_data, ensure_ascii=False, default=str)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Douro Capital — Overview Crédito</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&family=DM+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<style>
:root {{
  --navy: #1f2839;
  --teal: #00677b;
  --gold: #b69d74;
  --gold-light: #d4b47a;
  --bg: #f4f5f0;
  --bg2: #eceee7;
  --surface: #ffffff;
  --surface2: #f8f9f5;
  --text: #1f2839;
  --text2: #4a5568;
  --text3: #718096;
  --border: #dde0d8;
  --green: #2fa874;
  --red: #d94141;
  --blue-hl: #3174b8;
  --font: 'Montserrat', system-ui, sans-serif;
  --mono: 'DM Mono', 'Courier New', monospace;
}}

*, *::before, *::after {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}

body::before,
#canvas,
#progress {{
  pointer-events: none !important;
}}

body {{
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  overflow-x: hidden;
}}

/* ── SCROLL GRÁFICO E TABELA ───────────────────────── */
.chart-scroll-wrap{{
    width:100%;
    max-width:100%;
    overflow-x:auto;
    overflow-y:hidden;
    padding-bottom:8px;
    box-sizing:border-box;
}}
.chart-scroll-inner {{
  position: relative;
  display: inline-flex;
  min-width:100%;
  height: 320px;
}}
.table-wrap{{
    max-height:700px;
    overflow-y:auto;
    overflow-x:auto;
    border-radius:12px;
}}
.table-wrap thead th{{
    position: sticky;
    top: 0;
    z-index: 2;
    background: var(--surface);
}}

/* Scrollbar custom */
.chart-scroll-wrap::-webkit-scrollbar,
.table-wrap::-webkit-scrollbar{{
    height:10px;
    width:10px;
}}
.chart-scroll-wrap::-webkit-scrollbar-thumb,
.table-wrap::-webkit-scrollbar-thumb{{
    background:#b69d74;
    border-radius:999px;
}}
/* SIDEBAR */
.sidebar {{
  position:fixed; left:0; top:0; bottom:0; width:220px;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  box-shadow: 2px 0 12px rgba(31,40,57,0.06);
  display:flex; flex-direction:column; z-index:100;
  transition:width .28s cubic-bezier(.4,0,.2,1), box-shadow .3s;
  overflow:hidden;
}}
.sidebar:hover {{
  box-shadow: 2px 0 18px rgba(31,40,57,0.09);
}}
.sidebar-logo {{
  padding:28px 20px 22px;
  border-bottom: 1px solid var(--border);
  display:flex; align-items:center; gap:10px;
}}
.logo-icon {{ width:38px; height:38px; background:var(--gold); border-radius:4px; display:flex; align-items:center; justify-content:center; flex-shrink:0; box-shadow:0 2px 10px rgba(182,157,116,0.40); }}
.logo-icon svg {{ width:22px; height:22px; fill:var(--surface); }}
.logo-text {{ font-size:17px; font-weight:700; line-height:1.1; color:var(--navy); letter-spacing:-0.5px; }}
.logo-text span {{ color:var(--gold); font-weight:400; }}
.nav-section {{ padding:18px 12px 8px; font-size:10px; text-transform:uppercase; letter-spacing:.12em; color:var(--text3); font-weight:600; }}
.nav-item {{
  display:flex; align-items:center; gap:10px; padding:10px 14px; margin:2px 8px;
  border-radius:8px; cursor:pointer; font-size:12.5px; font-weight:500; color:var(--text3);
  transition:background .18s ease, color .18s ease, padding .28s cubic-bezier(.4,0,.2,1), box-shadow .18s;
  white-space:nowrap; overflow:hidden; position:relative;
}}
.nav-item:hover {{
  background: rgba(255,255,255,0.48);
  color:var(--teal);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.7), 0 1px 6px rgba(31,40,57,0.06);
}}
.nav-item.active {{
  background: linear-gradient(90deg,rgba(0,103,123,0.13),rgba(0,103,123,0.05));
  color:var(--teal); border-left:2px solid var(--teal); margin-left:6px; padding-left:12px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.65), 0 2px 10px rgba(0,103,123,0.10);
}}
.nav-subitem {{ padding-left:28px; font-size:12px; }}
.nav-subitem.active {{ padding-left:26px; }}
.nav-icon {{ width:16px; height:16px; flex-shrink:0; opacity:.7; transition:opacity .18s; }}
.nav-item:hover .nav-icon {{ opacity:1; }}
.nav-item.active .nav-icon {{ opacity:1; }}
/* MAIN */
.main {{ margin-left:220px; min-height:100vh; display:flex; flex-direction:column; transition:margin-left .28s cubic-bezier(.4,0,.2,1), filter .28s cubic-bezier(.4,0,.2,1); }}
/* ── SIDEBAR RAIL MODE ── */
.sidebar.rail {{ width:58px; }}
.sidebar.rail:not(.pinned):hover {{
  width:220px; z-index:200;
  background: var(--bg2);
  box-shadow: 2px 0 18px rgba(31,40,57,0.09);
}}
/* Recuo suave no conteúdo ao expandir sidebar */
.sidebar.rail:not(.pinned):hover ~ .main {{
  opacity: 0.85;
}}
.main.rail-active {{ margin-left:58px; }}
/* Ocultar textos no rail com fade+slide */
.sidebar .nav-item>span,.sidebar .logo-text,.sidebar .nav-section {{
  transition:opacity .2s ease,transform .2s ease,max-width .26s cubic-bezier(.4,0,.2,1);
  max-width:160px; overflow:hidden;
}}
.sidebar.rail .nav-item>span,.sidebar.rail .logo-text,.sidebar.rail .nav-section {{
  opacity:0; max-width:0; transform:translateX(-6px); pointer-events:none;
}}
.sidebar.rail:hover .nav-item>span,.sidebar.rail:hover .logo-text,.sidebar.rail:hover .nav-section {{
  opacity:1; max-width:160px; transform:translateX(0);
}}
/* Centralizar ícone no rail */
.sidebar.rail .nav-item {{ padding:10px 0 10px 21px; }}
.sidebar.rail:hover .nav-item {{ padding:10px 14px; }}
.sidebar.rail .sidebar-logo {{ padding:24px 0; justify-content:center; }}
.sidebar.rail:hover .sidebar-logo {{ padding:24px 20px; justify-content:flex-start; }}
/* ── BADGES DINÂMICOS ── */
.nav-badge {{
  position:absolute; right:10px; top:50%; transform:translateY(-50%);
  background:#e05252; color:#fff; font-size:9px; font-weight:700;
  padding:1px 5px; border-radius:8px; min-width:16px; text-align:center;
  line-height:14px; pointer-events:none;
  transition:right .28s cubic-bezier(.4,0,.2,1),top .28s cubic-bezier(.4,0,.2,1),transform .28s cubic-bezier(.4,0,.2,1),font-size .2s;
}}
.sidebar.rail .nav-badge {{ right:5px; top:5px; transform:none; font-size:8px; padding:1px 3px; min-width:12px; line-height:12px; }}
.sidebar.rail:hover .nav-badge {{ right:10px; top:50%; transform:translateY(-50%); font-size:9px; padding:1px 5px; min-width:16px; line-height:14px; }}
.nav-badge--teal {{ background:#00677b; }}
.nav-badge--gold {{ background:#b69d74; color:#1f2839; }}
/* ── DOURADO PULSE ── */
@keyframes douradoPulse {{ 0%,100% {{ box-shadow:0 0 0 0 rgba(182,157,116,.55),0 4px 18px rgba(0,103,123,.35); }} 60% {{ box-shadow:0 0 0 9px rgba(182,157,116,0),0 4px 18px rgba(0,103,123,.35); }} }}
#douradoBtn.pulsing {{ animation:douradoPulse 2.4s ease infinite; }}
/* ── PIN BUTTON ── */
.sidebar-pin-btn {{ background:none; border:none; cursor:pointer; color:var(--text3); padding:5px 6px; border-radius:6px; display:flex; align-items:center; gap:5px; opacity:.45; transition:opacity .18s,color .18s,background .18s,transform .3s cubic-bezier(.34,1.56,.64,1); flex-shrink:0; }}
.sidebar-pin-btn:hover {{ color:var(--teal); background:rgba(0,103,123,.07); opacity:1; }}
.sidebar-pin-btn.pinned {{ color:var(--teal); opacity:1; transform:rotate(-45deg); }}
.topbar {{ position:sticky; top:0; z-index:50; background:rgba(244,245,240,.95); backdrop-filter:blur(12px); border-bottom:1px solid var(--border); padding:0 32px; height:58px; display:flex; align-items:center; justify-content:space-between; overflow:visible; }}
.topbar-wave {{ position:absolute; inset:0; pointer-events:none; overflow:hidden; opacity:.06; }}
.topbar-wave svg {{ position:absolute; bottom:-2px; left:0; width:200%; animation:waveScroll 18s linear infinite; }}
@keyframes waveScroll {{ from {{ transform:translateX(0); }} to {{ transform:translateX(-50%); }} }}
.topbar-title {{ font-size:20px; font-weight:600; color:var(--navy); letter-spacing:-0.5px; }}
.topbar-title span {{ color:var(--gold); font-weight:400; }}
.topbar-right {{ display:flex; align-items:center; gap:16px; }}
.filter-pill {{ display:flex; align-items:center; gap:8px; background:var(--surface); border:1.2px solid var(--border); border-radius:22px; padding:7px 16px; font-size:12.5px; font-weight:500; color:var(--text2); cursor:pointer; transition:border-color .2s, color .2s, box-shadow .2s; user-select:none; position:relative; min-height:36px; }}
.filter-pill:hover, .filter-pill.ss-open {{ border-color:var(--teal); color:var(--teal); box-shadow:0 4px 16px rgba(0,103,123,.12); }}
.filter-pill select {{ background:none; border:none; color:inherit; font:inherit; font-weight:inherit; cursor:pointer; outline:none; }}
.filter-pill select option {{ background:var(--surface); color:var(--text); }}
.ss-label {{ white-space:nowrap; cursor:default; }}
.ss-caret {{ flex-shrink:0; opacity:.6; transition:transform .18s ease; }}
.filter-pill.ss-open .ss-caret {{ transform:rotate(180deg); opacity:1; }}
.ss-dropdown {{ display:none; position:absolute; top:calc(100% + 8px); left:0; min-width:260px; max-width:420px; background:var(--surface); border:1.5px solid rgba(0,103,123,.4); border-radius:12px; box-shadow:0 12px 40px rgba(0,0,0,.25); z-index:9999; overflow:visible; flex-direction:column; }}
.filter-pill.ss-open .ss-dropdown {{ display:flex; animation:ssDrop .14s ease; }}
@keyframes ssDrop {{ from {{ opacity:0; transform:translateY(-5px); }} to {{ opacity:1; transform:translateY(0); }} }}
.ss-search {{ padding:12px 14px; border:none; border-bottom:1.5px solid var(--border); background:transparent; color:var(--text); font:inherit; font-size:13px; outline:none; width:100%; box-sizing:border-box; transition:border-color .2s; }}
.ss-search::placeholder {{ color:var(--text3); opacity:.7; }}
.ss-search:focus {{ border-bottom-color:rgba(0,103,123,.5); }}
.ss-list {{ max-height:480px; overflow-y:auto; overflow-x:hidden; padding:6px 0; }}
.ss-list:has(> .ss-opt:nth-child(n+8)) {{ border-bottom:2px solid rgba(0,103,123,.15); }}
.ss-list::-webkit-scrollbar {{ width:10px; }}
.ss-list::-webkit-scrollbar-track {{ background:rgba(0,103,123,.05); border-radius:6px; }}
.ss-list::-webkit-scrollbar-thumb {{ background:rgba(0,103,123,.4); border-radius:6px; min-height:40px; }}
.ss-list::-webkit-scrollbar-thumb:hover {{ background:rgba(0,103,123,.6); }}
.ss-opt {{ padding:12px 16px; font-size:13px; cursor:pointer; color:var(--text2); transition:background .08s, color .08s; display:flex; align-items:center; }}
.ss-opt:hover {{ background:rgba(0,103,123,.12); color:var(--teal); }}
.ss-opt.ss-active {{ color:var(--teal); font-weight:600; background:rgba(0,103,123,.08); border-left:4px solid var(--teal); padding-left:12px; }}
.ss-opt.ss-hidden {{ display:none; }}
.content {{ padding:28px 32px 40px; flex:1; }}
.page {{ display:none; }}
.page.active {{ display:block; }}
/* ── SCORECARD PAGE ── */
#page-scorecard.active {{ display:flex !important; flex-direction:column; padding:0; }}
/* ── HOME PAGE ── */
#page-home.active {{ display:block; }}
.home-kpi-row {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:24px; }}
.home-grid-main {{ display:grid; grid-template-columns:2fr 1fr; gap:20px; margin-bottom:20px; }}
.home-grid-bottom {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px; }}
.home-grid-banks {{ display:grid; grid-template-columns:1fr; gap:20px; margin-bottom:20px; }}
.home-btn {{
  display:flex; align-items:center; justify-content:center;
  width:36px; height:36px; border-radius:10px; cursor:pointer; flex-shrink:0;
  position:relative; overflow:hidden;
  background: linear-gradient(145deg, rgba(255,255,255,.13) 0%, rgba(255,255,255,.05) 55%, rgba(255,255,255,.09) 100%);
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border: 1px solid rgba(255,255,255,.18);
  border-top-color: rgba(255,255,255,.38);
  box-shadow:
    inset 0 1px 1px rgba(255,255,255,.22),
    inset 0 -1px 1px rgba(0,0,0,.14),
    0 4px 18px rgba(0,0,0,.22),
    0 1px 4px rgba(0,0,0,.14);
  color: rgba(255,255,255,.72);
  transition: transform .28s cubic-bezier(.34,1.56,.64,1), box-shadow .22s ease, background .22s ease, border-color .22s ease, color .22s ease;
}}
.home-btn::before {{
  content:''; position:absolute; top:0; left:10%; right:10%; height:1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.7), transparent);
  border-radius:50%;
}}
.home-btn::after {{
  content:''; position:absolute; top:0; left:0; right:0; height:45%;
  background: linear-gradient(180deg, rgba(255,255,255,.08) 0%, transparent 100%);
  border-radius:10px 10px 0 0; pointer-events:none;
}}
.home-btn:hover {{
  background: linear-gradient(145deg, rgba(255,255,255,.22) 0%, rgba(255,255,255,.10) 55%, rgba(255,255,255,.17) 100%);
  border-color: rgba(255,255,255,.28);
  border-top-color: rgba(255,255,255,.55);
  box-shadow:
    inset 0 1px 1px rgba(255,255,255,.35),
    inset 0 -1px 1px rgba(0,0,0,.10),
    0 6px 24px rgba(0,0,0,.28),
    0 2px 8px rgba(0,0,0,.16);
  color: rgba(255,255,255,.95);
  transform: scale(1.06) translateY(-1px);
}}
.home-btn.active {{
  background: linear-gradient(145deg, rgba(182,157,116,.28) 0%, rgba(182,157,116,.12) 55%, rgba(182,157,116,.20) 100%);
  border-color: rgba(182,157,116,.30);
  border-top-color: rgba(212,180,122,.40);
  box-shadow:
    inset 0 1px 1px rgba(212,180,122,.18),
    inset 0 -1px 1px rgba(0,0,0,.12),
    0 4px 18px rgba(182,157,116,.20),
    0 0 0 1px rgba(182,157,116,.08);
  color: #d4b47a;
}}
.top5-table {{ width:100%; border-collapse:collapse; font-size:11.5px; }}
.top5-table thead th {{ padding:7px 10px; font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:.08em; color:var(--text3); border-bottom:1px solid var(--border); white-space:nowrap; text-align:left; }}
.top5-table tbody tr {{ border-bottom:1px solid rgba(0,0,0,.04); transition:background .15s; }}
.top5-table tbody tr:hover {{ background:rgba(0,103,123,.04); }}
.top5-table tbody td {{ padding:8px 10px; color:var(--text); font-size:11.5px; font-weight:500; white-space:nowrap; }}
.rank-num {{ display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; border-radius:50%; background:var(--bg2); color:var(--text3); font-size:9px; font-weight:700; margin-right:4px; flex-shrink:0; }}
@media(max-width:1200px) {{ .home-kpi-row {{ grid-template-columns:repeat(2,1fr); }} .home-grid-main {{ grid-template-columns:1fr; }} .home-grid-bottom {{ grid-template-columns:1fr; }} }}
/* KPI */
.kpi-row {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px; }}
.kpi-card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:18px 20px; position:relative; overflow:hidden; transition:box-shadow .2s; box-shadow:0 1px 8px rgba(31,40,57,.03); }}
.kpi-card:hover {{ box-shadow:0 6px 16px rgba(31,40,57,.08); }}
.kpi-card::before {{ content:''; position:absolute; bottom:0; left:0; right:0; height:3px; background:linear-gradient(90deg,var(--teal),var(--gold)); opacity: 0.8; }}
.kpi-label {{ font-size:10.5px; font-weight:600; text-transform:uppercase; letter-spacing:.08em; color:var(--text3); margin-bottom:8px; }}
.kpi-value {{ font-family:var(--mono); font-size:24px; font-weight:600; color:var(--navy); letter-spacing:-0.5px; }}
.kpi-sub {{ font-size:11px; font-weight:500; color:var(--text3); margin-top:4px; }}
.kpi-badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; margin-top:4px; font-family:var(--mono); }}
.kpi-badge.green {{ background:rgba(47,168,116,.15); color:var(--green); }}
.kpi-badge.red   {{ background:rgba(217,65,65,.15); color:var(--red); }}
.kpi-badge.gold  {{ background:rgba(182,157,116,.15); color:var(--gold); }}
/* GRID */
.grid-2   {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px; }}
.grid-3   {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:20px; margin-bottom:20px; }}
.grid-2-1 {{ display:grid; grid-template-columns:2fr 1fr; gap:20px; margin-bottom:20px; }}
.grid-2-1 > * {{ min-width:0; }}
/* CARD */
.card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px 22px; position:relative; margin-bottom:20px; box-shadow:0 1px 8px rgba(31,40,57,.03); }}
.card-title {{ font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:var(--navy); margin-bottom:16px; font-weight:600; display:flex; align-items:center; justify-content:space-between; }}
canvas {{
  max-width: 100%;
}}
/* PATCH 7 — container scroll horizontal para gráfico de emissores */
.chart-scroll-wrap {{
  width:100%;
  max-width:100%;
  overflow-x: auto;
  overflow-y: hidden;
  box-sizing:border-box;
  /* scrollbar discreta */
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}}
.chart-scroll-wrap::-webkit-scrollbar {{ height: 5px; }}
.chart-scroll-wrap::-webkit-scrollbar-track {{ background: transparent; }}
.chart-scroll-wrap::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
.chart-scroll-inner {{
  /* largura mínima calculada via JS — garante barras com espessura adequada */
  display: inline-flex;
  min-width: 100%;
  position: relative;
}}
.chart-scroll-inner > div {{
  min-width: 100%;
}}

/* TABLE */
.table-wrap {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }}
thead th {{ text-align:left; padding:10px 12px; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.08em; color:var(--text3); border-bottom:1px solid var(--border); white-space:nowrap; }}
tbody tr {{ border-bottom:1px solid rgba(0,0,0,.04); transition:background .15s; }}
tbody tr:hover {{ background:rgba(0,103,123,.045); }}
tbody td {{ padding:10px 12px; color:var(--text); font-size:12px; font-weight:500; white-space:nowrap; }}
.td-muted {{ color:var(--text3); }}
/* BADGES */
.badge {{ display:inline-block; padding:3px 9px; border-radius:6px; font-size:10.5px; font-weight:600; letter-spacing:.02em; }}
.badge-green {{ background:rgba(47,168,116,.15); color:var(--green); }}
.badge-red   {{ background:rgba(217,65,65,.15); color:var(--red); }}
.badge-gold  {{ background:rgba(182,157,116,.15); color:var(--gold); }}
.badge-blue  {{ background:rgba(49,116,184,.15); color:var(--blue-hl); }}
.badge-teal  {{ background:rgba(0,103,123,.15); color:var(--teal); }}
.badge-muted {{ background:var(--bg2); color:var(--text3); border: 1px solid var(--border); }}
/* CHART HEIGHTS */
.h320 {{ height:320px; position:relative; }}
.h260 {{ height:260px; position:relative; }}
.h200 {{ height:200px; position:relative; }}
/* SECTION HEADER */
.section-header {{ display:flex; align-items:center; gap:16px; margin-bottom:24px; }}
.section-header h2 {{ font-size:24px; font-weight:600; color:var(--navy); letter-spacing:-0.5px; }}
.accent-line {{ flex:1; height:1px; background:linear-gradient(90deg,var(--border),transparent); }}
/* CONTROLS */
.custom-select {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:8px 28px 8px 12px; color:var(--text); font-family:var(--font); font-size:12px; font-weight:500; cursor:pointer; outline:none; appearance:none; background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23718096' viewBox='0 0 16 16'%3E%3Cpath d='M7.247 11.14L2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z'/%3E%3C/svg%3E"); background-repeat:no-repeat; background-position:right 10px center; }}
.custom-select option {{ background:var(--surface); color:var(--text); }}
.flex-row {{ display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:16px; }}
/* RANGE SLIDER DUPLO — LIQUID GLASS */
.glass-range-wrap {{
  background: rgba(255,255,255,0.40);
  -webkit-backdrop-filter: blur(14px) saturate(170%);
  backdrop-filter: blur(14px) saturate(170%);
  border: 1px solid rgba(255,255,255,0.58);
  border-radius: 12px;
  padding: 13px 16px 11px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.70), 0 2px 14px rgba(31,40,57,0.05);
}}
.glass-range-label {{
  font-size:11px; font-family:var(--mono); font-weight:700; color:var(--teal);
  background: rgba(0,103,123,0.09);
  border: 1px solid rgba(0,103,123,0.20);
  border-radius: 6px; padding: 2px 9px;
  letter-spacing: .02em;
}}
.fin-range-inp {{ position:absolute;left:8px;right:8px;width:calc(100% - 16px);height:32px;top:0;-webkit-appearance:none;appearance:none;background:transparent;pointer-events:none;z-index:2; }}
.fin-range-inp::-webkit-slider-thumb {{ -webkit-appearance:none;appearance:none;width:18px;height:18px;border-radius:50%;background:#fff;border:2.5px solid var(--teal);box-shadow:0 2px 8px rgba(0,103,123,.28),0 1px 3px rgba(31,40,57,.10);cursor:pointer;pointer-events:all;transition:transform .15s,box-shadow .15s; }}
.fin-range-inp::-webkit-slider-thumb:hover {{ transform:scale(1.18);box-shadow:0 3px 14px rgba(0,103,123,.40),0 1px 4px rgba(31,40,57,.12); }}
.fin-range-inp::-moz-range-thumb {{ width:18px;height:18px;border-radius:50%;background:#fff;border:2.5px solid var(--teal);box-shadow:0 2px 8px rgba(0,103,123,.28);cursor:pointer;pointer-events:all; }}
/* COLORS */
.col-good {{ color:var(--green); font-weight:600; }}
.col-warn {{ color:var(--gold); font-weight:600; }}
.col-bad  {{ color:var(--red); font-weight:600; }}
/* ANIMATIONS */
.fade-in {{ animation:fadeIn .4s ease; }}
@keyframes fadeIn {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}
/* ── DOURO NEWS SIDEBAR — magnetic 3D + ticker scramble ── */
.nav-item.nav-news {{
  transform-style: preserve-3d;
  transition: transform .18s cubic-bezier(.16,1,.3,1), box-shadow .28s, border-color .28s, background .28s;
  will-change: transform;
}}
.nav-item.nav-news .news-icon-wrap {{
  position:relative; flex-shrink:0;
  transition: transform .28s cubic-bezier(.16,1,.3,1);
}}
/* linhas do jornal animam como manchetes entrando */
.nav-item.nav-news .news-headline-line {{
  transform-box: fill-box;
  transform-origin: left center;
  transform: scaleX(0);
  transition: transform .22s cubic-bezier(.16,1,.3,1), opacity .22s;
}}
.nav-item.nav-news:hover .news-icon-wrap {{
  transform: scale(1.12);
  filter: drop-shadow(0 0 6px rgba(182,157,116,.55));
}}
.nav-item.nav-news:hover .news-headline-line:nth-child(1) {{ transform:scaleX(1.0); opacity:1; transition-delay:.05s; }}
.nav-item.nav-news:hover .news-headline-line:nth-child(2) {{ transform:scaleX(1.0); opacity:.7; transition-delay:.10s; }}
.nav-item.nav-news:hover .news-headline-line:nth-child(3) {{ transform:scaleX(1.0); opacity:.85; transition-delay:.15s; }}
/* badge pop */
@keyframes newsBadgePop {{
  0%   {{ transform:scale(.75); opacity:.6; }}
  55%  {{ transform:scale(1.08); opacity:1; }}
  80%  {{ transform:scale(.97); }}
  100% {{ transform:scale(1); opacity:1; }}
}}
.nav-item.nav-news:hover .news-badge {{ animation: newsBadgePop .36s cubic-bezier(.34,1.56,.64,1) .05s both; }}
/* ── PAGE MORPH TRANSITION ── */
.page-exit {{
  animation: pageMorphOut .22s cubic-bezier(.4,0,.2,1) forwards;
  pointer-events: none;
}}
.page-enter {{
  animation: pageMorphIn .32s cubic-bezier(.16,1,.3,1) forwards;
}}
@keyframes pageMorphOut {{
  from {{ opacity:1; transform:scale(1)    translateY(0); }}
  to   {{ opacity:0; transform:scale(0.97) translateY(-6px); }}
}}
@keyframes pageMorphIn {{
  from {{ opacity:0; transform:scale(0.97) translateY(10px); }}
  to   {{ opacity:1; transform:scale(1)    translateY(0); }}
}}
/* SCROLLBAR geral */
::-webkit-scrollbar {{ width:6px; height:6px; }}
::-webkit-scrollbar-track {{ background:var(--bg2); }}
::-webkit-scrollbar-thumb {{ background:var(--border); border-radius:3px; }}
@media(max-width:1200px) {{ .kpi-row {{ grid-template-columns:repeat(3,1fr); }} .grid-3 {{ grid-template-columns:1fr 1fr; }} }}
@media(max-width:900px) {{ .sidebar {{ width:60px; }} .main {{ margin-left:60px; }} .logo-text, .nav-item span, .nav-section {{ display:none; }} }}
/* ── DOURO NEWS NAV ── */
.nav-item.nav-news:hover {{ background: linear-gradient(135deg,rgba(182,157,116,.2),rgba(182,157,116,.1)) !important; border-color: rgba(182,157,116,.6) !important; }}
.nav-item.nav-news.active {{ background: linear-gradient(135deg,rgba(182,157,116,.25),rgba(182,157,116,.12)) !important; border-color: #b69d74 !important; border-left: none !important; margin-left: 8px !important; }}
.nav-item.nav-notif:hover {{ background: linear-gradient(135deg,rgba(47,168,116,.22),rgba(0,103,123,.13)) !important; border-color: rgba(60,210,140,.55) !important; }}
.nav-item.nav-notif.active {{ background: linear-gradient(135deg,rgba(47,168,116,.28),rgba(0,103,123,.16)) !important; border-color: #3cd28a !important; border-left: none !important; margin-left: 8px !important; }}
/* ── Notificações filter buttons ── */
.notif-janela-btn {{ background:var(--surface2);border:1px solid var(--border);color:var(--text3);padding:4px 12px;border-radius:20px;cursor:pointer;font-size:10px;font-weight:600;font-family:var(--font);transition:all .18s;letter-spacing:.04em; }}
.notif-janela-btn:hover {{ border-color:#3cd28a;color:#3cd28a; }}
.notif-janela-btn.active {{ background:rgba(47,168,116,.15);border-color:#3cd28a;color:#3cd28a; }}
/* ── Alerta card ── */
.alerta-card {{ background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px;position:relative;overflow:hidden;transition:box-shadow .18s,border-color .18s; }}
.alerta-card:hover {{ box-shadow:0 4px 18px rgba(0,0,0,.22);border-color:rgba(60,210,140,.35); }}
.alerta-card.alerta-up {{ border-left:3px solid #d94141; }}
.alerta-card.alerta-dn {{ border-left:3px solid #2fa874; }}
/* ── Fato Relevante card ── */
.fr-card {{ background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 18px;transition:box-shadow .18s,border-color .18s; }}
.fr-card:hover {{ box-shadow:0 4px 18px rgba(0,0,0,.22);border-color:rgba(60,210,140,.3); }}
/* ── PAGE-FLIP hover animation for Douro News label ── */
@keyframes newsPageFlip {{
  0%   {{ transform: perspective(400px) rotateY(0deg);   opacity:1; }}
  30%  {{ transform: perspective(400px) rotateY(-90deg); opacity:.35; }}
  50%  {{ transform: perspective(400px) rotateY(-90deg); opacity:.35; }}
  70%  {{ transform: perspective(400px) rotateY(0deg);   opacity:1; }}
  100% {{ transform: perspective(400px) rotateY(0deg);   opacity:1; }}
}}
.news-label-flipping {{
  display: inline-block;
  animation: newsPageFlip 1.6s cubic-bezier(.42,0,.58,1) forwards;
  transform-origin: left center;
  transform-style: preserve-3d;
}}
/* ── DOURADO CHATBOT ── */
#douradoBtn {{ position:fixed; bottom:28px; right:28px; z-index:9999; width:50px; height:50px; border-radius:50%; background:linear-gradient(135deg,#b69d74,#d4b47a); border:none; cursor:pointer; box-shadow:0 4px 18px rgba(182,157,116,.45); display:flex; align-items:center; justify-content:center; transition:transform .18s,box-shadow .18s; }}
#douradoBtn::after {{ content:''; position:absolute; inset:-4px; border-radius:50%; border:1.5px solid rgba(182,157,116,.5); animation:dRipple 2.6s ease-out infinite; pointer-events:none; }}
#douradoBtn:hover {{ transform:scale(1.1); box-shadow:0 8px 26px rgba(182,157,116,.65); }}
#douradoBtn:hover::after {{ animation:none; opacity:0; transition:opacity .15s; }}
@keyframes dRipple {{ 0% {{ transform:scale(1); opacity:.75; }} 100% {{ transform:scale(1.65); opacity:0; }} }}
#douradoPanel {{ position:fixed; bottom:90px; right:28px; width:356px; max-height:560px; z-index:9998; background:#111827; border:1px solid rgba(182,157,116,.18); border-radius:18px; box-shadow:0 24px 56px rgba(0,0,0,.45),0 2px 8px rgba(0,0,0,.3),inset 0 1px 0 rgba(255,255,255,.04); display:flex; flex-direction:column; transform-origin:bottom right; transform:scale(0.86) translateY(16px); opacity:0; pointer-events:none; transition:transform .32s cubic-bezier(.34,1.32,.64,1),opacity .2s ease; overflow:hidden; }}
#douradoPanel.open {{ transform:scale(1) translateY(0); opacity:1; pointer-events:all; }}
#douradoPanel::before {{ content:''; position:absolute; top:0; left:10%; right:10%; height:1px; background:linear-gradient(90deg,transparent,rgba(182,157,116,.7),rgba(212,180,122,.9),rgba(182,157,116,.7),transparent); }}
.dourado-header {{ padding:13px 15px; border-bottom:1px solid rgba(182,157,116,.12); background:linear-gradient(160deg,#1a2438 0%,#111827 100%); display:flex; align-items:center; justify-content:space-between; flex-shrink:0; }}
.dourado-avatar {{ width:30px; height:30px; border-radius:50%; background:linear-gradient(135deg,#b69d74,#d4b47a); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:800; color:#1f2839; flex-shrink:0; }}
.dourado-status {{ width:7px; height:7px; border-radius:50%; background:#2fa874; box-shadow:0 0 6px rgba(47,168,116,.7); animation:dStatus 2.5s ease-in-out infinite; }}
@keyframes dStatus {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:.4; }} }}
.dourado-msgs {{ flex:1; min-height:0; overflow-y:auto; padding:12px 13px; display:flex; flex-direction:column; gap:9px; background:#0c1220; scrollbar-width:thin; scrollbar-color:rgba(182,157,116,.2) transparent; }}
.dourado-msgs::-webkit-scrollbar {{ width:3px; }}
.dourado-msgs::-webkit-scrollbar-thumb {{ background:rgba(182,157,116,.25); border-radius:3px; }}
.dourado-msg {{ display:flex; gap:7px; align-items:flex-start; animation:dMsgIn .24s cubic-bezier(.34,1.18,.64,1) both; }}
@keyframes dMsgIn {{ from {{ opacity:0; transform:translateY(10px) scale(.96); }} to {{ opacity:1; transform:none; }} }}
.dourado-msg.user {{ flex-direction:row-reverse; }}
.dourado-bubble {{ max-width:82%; padding:8px 12px; border-radius:10px; font-size:11.5px; line-height:1.65; font-family:var(--font); color:#b8c4d4; background:#182030; border:1px solid rgba(255,255,255,.05); }}
.dourado-msg.user .dourado-bubble {{ background:linear-gradient(135deg,#1b2d48,#1e3356); color:#e0dbd2; border-color:rgba(182,157,116,.22); border-radius:10px 2px 10px 10px; }}
.dourado-msg:not(.user) .dourado-bubble {{ border-radius:2px 10px 10px 10px; }}
.dourado-chips {{ display:flex; flex-wrap:wrap; gap:5px; padding:8px 13px; background:#0c1220; border-top:1px solid rgba(255,255,255,.04); flex-shrink:0; }}
.dourado-chip {{ background:rgba(182,157,116,.07); border:1px solid rgba(182,157,116,.25); color:#b69d74; font-size:10px; font-weight:600; padding:4px 9px; border-radius:14px; cursor:pointer; transition:background .15s,border-color .15s; font-family:var(--font); white-space:nowrap; }}
.dourado-chip:hover {{ background:rgba(182,157,116,.16); border-color:rgba(182,157,116,.6); }}
.dourado-chart-bubble {{ max-width:92% !important; padding:10px 12px !important; }}
.dourado-chart-bubble canvas {{ display:block; }}
.dourado-input-row {{ padding:9px 13px; border-top:1px solid rgba(255,255,255,.05); display:flex; gap:7px; background:#111827; flex-shrink:0; align-items:flex-end; }}
.dourado-input {{ flex:1; background:#0c1220; border:1px solid rgba(182,157,116,.18); border-radius:9px; padding:7px 11px; font-family:var(--font); font-size:11.5px; color:#c8d4e0; outline:none; resize:none; max-height:72px; line-height:1.5; transition:border-color .2s; }}
.dourado-input:focus {{ border-color:rgba(182,157,116,.5); }}
.dourado-input::placeholder {{ color:#3d4f6a; }}
.dourado-send {{ width:34px; height:34px; border-radius:8px; border:none; cursor:pointer; background:linear-gradient(135deg,#b69d74,#d4b47a); display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:opacity .15s,transform .15s; }}
.dourado-send:hover {{ opacity:.85; transform:scale(1.06); }}
/* ── SLASH COMMAND PALETTE ── */
#dSlashPal{{position:fixed;z-index:10005;background:#0d1525;border:1px solid rgba(182,157,116,.32);border-radius:10px;overflow:hidden;box-shadow:0 -8px 32px rgba(0,0,0,.75);display:none;min-width:300px;max-height:280px;overflow-y:auto;transform:translateY(-100%);}}
.dsp-item{{display:flex;align-items:center;gap:12px;padding:9px 15px;cursor:pointer;border-bottom:1px solid rgba(255,255,255,.035);transition:background .08s;}}
.dsp-item:hover,.dsp-item.dsp-active{{background:rgba(182,157,116,.1);}}
.dsp-cmd{{font-family:'DM Mono','Courier New',monospace;font-size:12px;color:#b69d74;font-weight:700;min-width:130px;flex-shrink:0;}}
.dsp-desc{{font-size:11px;color:#3a4f6a;}}
.dourado-thinking {{ display:flex; gap:4px; padding:5px 0; align-items:center; }}
.dourado-dot {{ width:5px; height:5px; border-radius:50%; background:#b69d74; animation:dDot 1.2s ease-in-out infinite; }}
.dourado-dot:nth-child(2) {{ animation-delay:.2s; }}
.dourado-dot:nth-child(3) {{ animation-delay:.4s; }}
@keyframes dDot {{ 0%,80%,100% {{ transform:scale(.55); opacity:.35; }} 40% {{ transform:scale(1); opacity:1; }} }}
</style>
</head>
<body>
<aside class="sidebar">
  <div class="sidebar-logo" style="justify-content: center; padding: 24px 20px;">
    {logo_html}
  </div>
  <div class="nav-section">Carteira</div>
  <div class="nav-item active" onclick="showPage('composicao',this)">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
    <span>Composição</span>
  </div>
  <div class="nav-item" onclick="showPage('rating',this)">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
    <span>Classe e Rating</span>
  </div>
  <div class="nav-item" onclick="showPage('performance',this)">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17l6-6 4 4 7-7"/></svg>
    <span>Performance</span>
  </div>
  <div class="nav-section">Mercado</div>
  <div class="nav-item" onclick="showPage('spreads',this)">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M18 17l-5-5-4 4-3-3"/></svg>
    <span>Spreads</span>
  </div>
  <div class="nav-item" onclick="showPage('tunel',this)">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/></svg>
    <span>Túnel de Preço</span>
  </div>
  <div class="nav-item" onclick="showPage('bonds',this)">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12h4l2-9 5 18 2-9h5"/></svg>
    <span>Bonds</span>
  </div>
  <div class="nav-section">Fundamentos Financeiros</div>
  <div class="nav-item" onclick="showPage('financeiros',this)">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
    <span>Dados</span>
  </div>
  <div class="nav-item" onclick="showPage('fundamentos',this)">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
    <span>Empresas</span>
  </div>
  <div class="nav-item" onclick="showPage('bancos',this)">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><path d="M2 11h20"/></svg>
    <span>Bancos</span>
  </div>
  <div class="nav-section">RANKING</div>
  <div class="nav-item" onclick="showPage('scorecard',this)">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
    <span>Scorecard</span>
  </div>
  <div style="margin-top:auto;margin-left:12px;margin-right:12px;margin-bottom:8px;border-top:1px solid rgba(182,157,116,.25);padding-top:8px;"></div>
  <div class="nav-item nav-notif" id="navNotifItem" onclick="showPage('notificacoes',this)"
    style="margin:4px 8px 6px;border-radius:10px;background:linear-gradient(145deg,rgba(47,168,116,.16) 0%,rgba(0,103,123,.10) 55%,rgba(47,168,116,.12) 100%);border:1px solid rgba(47,168,116,.28);border-top-color:rgba(60,210,140,.35);position:relative;overflow:hidden;box-shadow:0 4px 16px rgba(47,168,116,.12);">
    <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 80% 50%,rgba(47,168,116,.08),transparent 70%);pointer-events:none;"></div>
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="#3cd28a" stroke-width="2" style="flex-shrink:0;z-index:1">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
      <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
    </svg>
    <span style="color:#3cd28a;font-weight:700;letter-spacing:.02em;display:flex;align-items:center;gap:6px;z-index:1;">
      Notificações
      <span id="notifBadgeNav" style="display:none;background:linear-gradient(135deg,#2fa874,#3cd28a);color:#0d1f17;font-size:8px;font-weight:800;padding:2px 6px;border-radius:4px;letter-spacing:.05em;"></span>
    </span>
  </div>
  <div class="nav-item nav-news" onclick="showPage('douro-news',this)"
    style="margin:4px 8px 24px;border-radius:10px;background:linear-gradient(145deg,rgba(182,157,116,.18) 0%,rgba(182,157,116,.08) 55%,rgba(182,157,116,.14) 100%);border:1px solid rgba(182,157,116,.32);border-top-color:rgba(212,180,122,.45);position:relative;overflow:hidden;box-shadow:0 4px 16px rgba(182,157,116,.15);"
    onmouseenter="(function(el){{
      const lbl=el.querySelector('.news-label');
      if(!lbl||lbl._flipping)return;
      lbl._flipping=true;
      lbl.classList.remove('news-label-flipping');
      void lbl.offsetWidth;
      lbl.classList.add('news-label-flipping');
      lbl.addEventListener('animationend',function h(){{
        lbl.classList.remove('news-label-flipping');
        lbl._flipping=false;
        lbl.removeEventListener('animationend',h);
      }});
    }})(this)"
    onmousemove="(function(el,e){{
      const r=el.getBoundingClientRect();
      const x=(e.clientX-r.left)/r.width-.5;
      const y=(e.clientY-r.top)/r.height-.5;
      el.style.transform='perspective(320px) rotateY('+x*10+'deg) rotateX('+(-y*8)+'deg) translateZ(3px)';
    }})(this,event)"
    onmouseleave="(function(el){{
      el.style.transform='perspective(320px) rotateY(0deg) rotateX(0deg) translateZ(0)';
      const lbl=el.querySelector('.news-label');
      if(lbl){{lbl.classList.remove('news-label-flipping');lbl._flipping=false;}}
    }})(this)">
    <div class="news-icon-wrap">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="#d4b47a" stroke-width="2">
        <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/>
        <line class="news-headline-line" x1="10" y1="7" x2="18" y2="7" stroke="#d4b47a" stroke-width="1.5"/>
        <line class="news-headline-line" x1="10" y1="10" x2="16" y2="10" stroke="#d4b47a" stroke-width="1.5" opacity=".6"/>
        <line class="news-headline-line" x1="10" y1="13" x2="17" y2="13" stroke="#d4b47a" stroke-width="1.5" opacity=".7"/>
        <line x1="10" y1="17" x2="15" y2="17" stroke="#d4b47a" stroke-width="1.5" opacity=".4"/>
      </svg>
    </div>
    <span style="color:#d4b47a;font-weight:700;letter-spacing:.02em;display:flex;align-items:center;gap:6px;">
      <span class="news-label">Douro News</span>
      <span class="news-badge" style="background:linear-gradient(135deg,#b69d74,#d4b47a);color:#1f2839;font-size:8px;font-weight:800;padding:2px 6px;border-radius:4px;letter-spacing:.05em;display:inline-block;">NEWS</span>
    </span>
  </div>
</aside>
<main class="main">
  <div class="topbar">
    <div class="topbar-wave" aria-hidden="true">
      <svg viewBox="0 0 1440 40" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
        <path d="M0 28 C240 8 480 38 720 22 C960 6 1200 36 1440 18 L1440 40 L0 40 Z" fill="#1f2839"/>
        <path d="M0 34 C180 18 360 38 540 28 C720 18 900 38 1080 26 C1260 14 1380 32 1440 24 L1440 40 L0 40 Z" fill="#b69d74" opacity=".5"/>
        <path d="M0 28 C240 8 480 38 720 22 C960 6 1200 36 1440 18 L1440 40 L0 40 Z" fill="#1f2839"/>
        <path d="M0 34 C180 18 360 38 540 28 C720 18 900 38 1080 26 C1260 14 1380 32 1440 24 L1440 40 L0 40 Z" fill="#b69d74" opacity=".5"/>
      </svg>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      <button class="home-btn" id="homeBtnTopbar" onclick="showPage('home',null)" title="Página Inicial">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z"/>
          <path d="M9 21V12h6v9"/>
        </svg>
      </button>
      <button id="sidebarPinBtn" class="sidebar-pin-btn" onclick="toggleSidebarPin()" title="Fixar painel lateral">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg>
      </button>
      <div class="topbar-title">Overview <span>Crédito</span></div>
    </div>
    <div class="topbar-right">
      <!-- Carteira -->
      <div class="filter-pill" id="ss-carteira" data-prefix="Carteira: " data-all="Todas">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/></svg>
        <span class="ss-label">Carteira: Todas</span>
        <svg class="ss-caret" width="10" height="6" viewBox="0 0 10 6" fill="none"><polyline points="1,1 5,5 9,1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <div class="ss-dropdown" onclick="event.stopPropagation()">
          <input class="ss-search" type="text" placeholder="Buscar carteira...">
          <div class="ss-list">
            <div class="ss-opt ss-active" data-value="">Todas</div>
            {carteira_options_dd}
          </div>
        </div>
        <select id="carteiraFilter" style="display:none">
          <option value="">Todas</option>
          {carteira_options}
        </select>
      </div>
      <!-- Setor -->
      <div class="filter-pill" id="ss-setor" data-prefix="Setor: " data-all="Todos">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <span class="ss-label">Setor: Todos</span>
        <svg class="ss-caret" width="10" height="6" viewBox="0 0 10 6" fill="none"><polyline points="1,1 5,5 9,1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <div class="ss-dropdown" onclick="event.stopPropagation()">
          <input class="ss-search" type="text" placeholder="Buscar setor...">
          <div class="ss-list">
            <div class="ss-opt ss-active" data-value="">Todos</div>
            {setor_options_dd}
          </div>
        </div>
        <select id="setorFilter" style="display:none">
          <option value="">Todos</option>
          {setor_options}
        </select>
      </div>
      <!-- Officer -->
      <div class="filter-pill" id="ss-officer" data-prefix="Officer: " data-all="Todos">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        <span class="ss-label">Officer: Todos</span>
        <svg class="ss-caret" width="10" height="6" viewBox="0 0 10 6" fill="none"><polyline points="1,1 5,5 9,1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <div class="ss-dropdown" onclick="event.stopPropagation()">
          <input class="ss-search" type="text" placeholder="Buscar officer...">
          <div class="ss-list">
            <div class="ss-opt ss-active" data-value="">Todos</div>
            {officer_options_dd}
          </div>
        </div>
        <select id="officerFilter" style="display:none">
          <option value="">Todos</option>
          {officer_options}
        </select>
      </div>
    </div>
  </div>
  <!-- ══ BOTÃO (i) FLUTUANTE ══ -->
  <button id="sysInfoBtn" onclick="openSysInfo()" title="Como este sistema funciona" style="position:fixed;bottom:12px;left:12px;z-index:9990;width:18px;height:18px;border-radius:4px;background:transparent;border:1px solid rgba(182,157,116,.22);color:rgba(182,157,116,.38);font-size:9px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .2s;font-family:'DM Mono',monospace;letter-spacing:0;opacity:.55;">i</button>

  <!-- ══ MODAL: COMO O SISTEMA FUNCIONA ══ -->
  <div id="sysInfoModal" style="display:none;position:fixed;inset:0;z-index:10000;background:rgba(15,20,35,.6);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);align-items:center;justify-content:center;">
    <div id="sysInfoInner" style="position:relative;width:96vw;max-width:1420px;height:92vh;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid rgba(182,157,116,.18);box-shadow:0 40px 100px rgba(0,0,0,.28),0 0 0 1px rgba(182,157,116,.1);display:flex;flex-direction:column;">

      <!-- ── HEADER ── -->
      <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 22px 12px;border-bottom:1px solid #edeae3;background:#fafaf8;flex-shrink:0;gap:16px;">
        <!-- logo + título -->
        <div style="display:flex;align-items:center;gap:11px;flex-shrink:0;">
          <div style="width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,rgba(182,157,116,.18),rgba(182,157,116,.06));border:1px solid rgba(182,157,116,.32);display:flex;align-items:center;justify-content:center;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#b69d74" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
          </div>
          <div>
            <div style="font-size:13px;font-weight:700;color:#1f2839;letter-spacing:-.3px;">Como este sistema funciona</div>
            <div style="font-size:8.5px;color:rgba(182,157,116,.65);font-family:'DM Mono',monospace;margin-top:1px;letter-spacing:.07em;">ARQUITETURA · OVERVIEW CRÉDITO</div>
          </div>
        </div>

        <!-- ── VIEW TOGGLE (pill on/off) ── -->
        <div id="sysViewToggle" style="display:flex;align-items:center;background:#f0ede6;border-radius:10px;padding:3px;gap:2px;border:1px solid rgba(182,157,116,.2);">
          <button id="sysToggleDiagram" onclick="sysView('diagram')"
            style="display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:7px;border:none;cursor:pointer;font-size:9px;font-weight:700;letter-spacing:.06em;font-family:'Montserrat',sans-serif;transition:all .22s cubic-bezier(.16,1,.3,1);background:linear-gradient(135deg,#b69d74,#d4b47a);color:#fff;box-shadow:0 2px 8px rgba(182,157,116,.4);">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
            DIAGRAMA
          </button>
          <button id="sysToggleTerminal" onclick="sysView('terminal')"
            style="display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:7px;border:none;cursor:pointer;font-size:9px;font-weight:700;letter-spacing:.06em;font-family:'Montserrat',sans-serif;transition:all .22s cubic-bezier(.16,1,.3,1);background:transparent;color:#9a8a76;">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
            TERMINAL
          </button>
          <button id="sysToggleShortcuts" onclick="sysView('shortcuts')"
            style="display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:7px;border:none;cursor:pointer;font-size:9px;font-weight:700;letter-spacing:.06em;font-family:'Montserrat',sans-serif;transition:all .22s cubic-bezier(.16,1,.3,1);background:transparent;color:#9a8a76;">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M6 12h.01M18 12h.01M10 12h4M6 16h12"/></svg>
            ATALHOS
          </button>
        </div>

        <!-- fechar -->
        <button onclick="closeSysInfo()" style="width:30px;height:30px;border-radius:7px;border:1px solid #e4e0d8;background:#f5f3ef;color:#8a8276;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .18s;flex-shrink:0;" onmouseover="this.style.background='#fff0dc';this.style.color='#b69d74';this.style.borderColor='rgba(182,157,116,.5)'" onmouseout="this.style.background='#f5f3ef';this.style.color='#8a8276';this.style.borderColor='#e4e0d8'">×</button>
      </div>

      <!-- ══════════════════════════════════════════════════════════ -->
      <!-- VIEW A: DIAGRAMA — nós distintos + painel didático fixo  -->
      <!-- ══════════════════════════════════════════════════════════ -->
      <div id="sysViewDiagram" style="flex:1;overflow:hidden;display:flex;min-height:0;">

        <!-- ── COLUNA ESQUERDA: diagrama de nós ── -->
        <div style="flex:1;overflow-y:auto;padding:24px 28px;background:#f8f7f4;min-width:0;">

          <!-- linha de fluxo vertical conectando tudo -->
          <div style="position:relative;">

            <!-- trilho central vertical -->
            <div style="position:absolute;left:28px;top:20px;bottom:20px;width:2px;background:linear-gradient(to bottom,rgba(182,157,116,.4),rgba(47,168,116,.3));border-radius:2px;z-index:0;"></div>

            <!-- ── NÓ 01: Inicialização ── -->
            <div class="sdg-row" data-mod="0" onclick="sysSelectMod(0)">
              <div class="sdg-dot sdg-dot--gold">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              </div>
              <div class="sdg-card sdg-card--gold sdg-active">
                <div class="sdg-card-head">
                  <div style="display:flex;align-items:center;gap:10px;flex:1;">
                    <span class="sdg-badge" style="background:linear-gradient(135deg,#b69d74,#d4b47a);color:#fff;">01</span>
                    <div>
                      <div class="sdg-title">Inicialização &amp; Modo</div>
                      <div class="sdg-tech">Python · argparse · pathlib</div>
                    </div>
                  </div>
                  <div style="display:flex;gap:5px;align-items:center;">
                    <span class="sdg-tag" style="background:rgba(182,157,116,.12);color:#9a7e52;border-color:rgba(182,157,116,.3);">ENTRY POINT</span>
                  </div>
                </div>
                <div class="sdg-chips">
                  <span class="sdg-chip" style="border-color:rgba(182,157,116,.25);color:#7a6340;">Modo 1: Completo</span>
                  <span class="sdg-chip" style="border-color:#e0dbd2;color:#b0a898;">Modo 2: News Rápido</span>
                  <span class="sdg-chip" style="border-color:rgba(182,157,116,.25);color:#7a6340;">Valida caminhos</span>
                  <span class="sdg-chip" style="border-color:rgba(182,157,116,.25);color:#7a6340;">Credenciais</span>
                </div>
              </div>
            </div>

            <!-- conector 01→02 com label -->
            <div class="sdg-connector">
              <span class="sdg-conn-label">dispara extração paralela</span>
            </div>

            <!-- ── NÓ 02: Extração — nó MAIOR, destaque especial ── -->
            <div class="sdg-row" data-mod="1" onclick="sysSelectMod(1)">
              <div class="sdg-dot sdg-dot--teal">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
              </div>
              <div class="sdg-card sdg-card--teal sdg-card--wide">
                <div class="sdg-card-head">
                  <div style="display:flex;align-items:center;gap:10px;flex:1;">
                    <span class="sdg-badge" style="background:linear-gradient(135deg,#0082a0,#00b4d8);color:#fff;">02</span>
                    <div>
                      <div class="sdg-title">Extração Paralela de Dados</div>
                      <div class="sdg-tech">ThreadPoolExecutor · asyncio · aiohttp</div>
                    </div>
                  </div>
                  <span class="sdg-tag" style="background:rgba(0,130,155,.1);color:#0082a0;border-color:rgba(0,130,155,.3);">10+ FONTES SIMULTÂNEAS</span>
                </div>
                <!-- duas colunas de fontes -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px;">
                  <div style="background:rgba(0,130,155,.05);border:1px solid rgba(0,130,155,.15);border-radius:8px;padding:10px;">
                    <div style="font-size:7.5px;font-weight:700;letter-spacing:.1em;color:#0082a0;margin-bottom:6px;font-family:'DM Mono',monospace;">THREADS (IO)</div>
                    <div style="display:flex;flex-direction:column;gap:4px;">
                      <div class="sdg-source-row"><span class="sdg-src-dot" style="background:#0082a0;"></span><span class="sdg-src-name">Carteira CP</span><span class="sdg-src-detail">Comdinheiro · saldo · duration</span></div>
                      <div class="sdg-source-row"><span class="sdg-src-dot" style="background:#0082a0;"></span><span class="sdg-src-name">Bonds Offshore</span><span class="sdg-src-detail">preços 36 meses</span></div>
                      <div class="sdg-source-row"><span class="sdg-src-dot" style="background:#0082a0;"></span><span class="sdg-src-name">Rankings Excel</span><span class="sdg-src-detail">Scorecard · Rating</span></div>
                      <div class="sdg-source-row"><span class="sdg-src-dot" style="background:#0082a0;"></span><span class="sdg-src-name">Watch List</span><span class="sdg-src-detail">bancos · status</span></div>
                    </div>
                  </div>
                  <div style="background:rgba(49,116,184,.05);border:1px solid rgba(49,116,184,.15);border-radius:8px;padding:10px;">
                    <div style="font-size:7.5px;font-weight:700;letter-spacing:.1em;color:#3174b8;margin-bottom:6px;font-family:'DM Mono',monospace;">ASYNC (NETWORK)</div>
                    <div style="display:flex;flex-direction:column;gap:4px;">
                      <div class="sdg-source-row"><span class="sdg-src-dot" style="background:#3174b8;"></span><span class="sdg-src-name">Tesouro Direto</span><span class="sdg-src-detail">NTN-B · LFT CSV</span></div>
                      <div class="sdg-source-row"><span class="sdg-src-dot" style="background:#3174b8;"></span><span class="sdg-src-name">Cadastro CVM</span><span class="sdg-src-detail">CNPJ · setor</span></div>
                      <div class="sdg-source-row"><span class="sdg-src-dot" style="background:#3174b8;"></span><span class="sdg-src-name">ZIPs CVM ITR/DFP</span><span class="sdg-src-detail">DRE·BPA·BPP·DFC 2011–2026</span></div>
                      <div class="sdg-source-row"><span class="sdg-src-dot" style="background:#6b5ca5;"></span><span class="sdg-src-name">BCB IF.data</span><span class="sdg-src-detail">Basileia · ROE · eficiência · 27 bancos</span></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- conector com bifurcação 02→03 e 02→04 -->
            <div class="sdg-connector">
              <span class="sdg-conn-label">dados brutos → dois pipelines independentes</span>
            </div>

            <!-- ── NÓ 03 + 03b + 04 em linha ── -->
            <div style="display:flex;gap:12px;margin-bottom:0;position:relative;z-index:1;padding-left:52px;">

              <!-- NÓ 03: Cálculos -->
              <div class="sdg-card sdg-card--blue sdg-card--half" data-mod="2" onclick="sysSelectMod(2)" style="flex:1.4;">
                <div class="sdg-card-head">
                  <span class="sdg-badge" style="background:linear-gradient(135deg,#3174b8,#5b9bd5);color:#fff;">03</span>
                  <div style="flex:1;margin-left:10px;">
                    <div class="sdg-title">Cálculos Financeiros</div>
                    <div class="sdg-tech">pandas · numpy · KPIs TTM</div>
                  </div>
                </div>
                <div style="margin-top:9px;display:flex;flex-direction:column;gap:5px;">
                  <div class="sdg-kpi-row">
                    <span class="sdg-kpi-label">KPIs</span>
                    <span class="sdg-kpi-val" style="color:#3174b8;">EBITDA · DivLíq · FCF · ROE · ROIC</span>
                  </div>
                  <div class="sdg-kpi-row">
                    <span class="sdg-kpi-label">Spread</span>
                    <span class="sdg-kpi-val" style="color:#3174b8;">CP − NTN-B · z-score · MAD · MM21</span>
                  </div>
                  <div class="sdg-kpi-row">
                    <span class="sdg-kpi-label">D&amp;A</span>
                    <span class="sdg-kpi-val" style="color:#3174b8;">nome da conta &gt; código contábil</span>
                  </div>
                  <div class="sdg-kpi-row">
                    <span class="sdg-kpi-label">Export</span>
                    <span class="sdg-kpi-val" style="color:#3174b8;">ativos.json · spreads_ts · fin_series</span>
                  </div>
                </div>
              </div>

              <!-- NÓ 03b: Indicadores Bancários BCB -->
              <div class="sdg-card sdg-card--half" data-mod="3" onclick="sysSelectMod(3)" style="flex:1;background:linear-gradient(135deg,rgba(107,92,165,.07),rgba(107,92,165,.03));border:1px solid rgba(107,92,165,.22);">
                <div class="sdg-card-head">
                  <span class="sdg-badge" style="background:linear-gradient(135deg,#6b5ca5,#9880d0);color:#fff;">03b</span>
                  <div style="flex:1;margin-left:10px;">
                    <div class="sdg-title">Indicadores Bancários</div>
                    <div class="sdg-tech">BCB IF.data · requests · 27 bancos</div>
                  </div>
                </div>
                <div style="margin-top:9px;display:flex;flex-direction:column;gap:5px;">
                  <div class="sdg-kpi-row">
                    <span class="sdg-kpi-label">Solvência</span>
                    <span class="sdg-kpi-val" style="color:#6b5ca5;">Basileia · Tier 1 · Alavancagem</span>
                  </div>
                  <div class="sdg-kpi-row">
                    <span class="sdg-kpi-label">Rentab.</span>
                    <span class="sdg-kpi-val" style="color:#6b5ca5;">ROE · Margem Líquida</span>
                  </div>
                  <div class="sdg-kpi-row">
                    <span class="sdg-kpi-label">Qualidade</span>
                    <span class="sdg-kpi-val" style="color:#6b5ca5;">PDD/Carteira · Inadimplência</span>
                  </div>
                  <div class="sdg-kpi-row">
                    <span class="sdg-kpi-label">Export</span>
                    <span class="sdg-kpi-val" style="color:#6b5ca5;">BCB_LIVE · 2021–2024</span>
                  </div>
                </div>
              </div>

              <!-- NÓ 04: News -->
              <div class="sdg-card sdg-card--amber sdg-card--half" data-mod="4" onclick="sysSelectMod(4)" style="flex:1;">
                <div class="sdg-card-head">
                  <span class="sdg-badge" style="background:linear-gradient(135deg,#c07c2a,#e09940);color:#fff;">04</span>
                  <div style="flex:1;margin-left:10px;">
                    <div class="sdg-title">News Pipeline</div>
                    <div class="sdg-tech">feedparser · Jaccard</div>
                  </div>
                </div>
                <div style="margin-top:9px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:9px;color:#7a5a28;font-family:'DM Mono',monospace;">4 feeds RSS</span>
                    <span style="font-size:10px;font-weight:700;color:#c07c2a;">→ score → dedup</span>
                  </div>
                  <div style="display:flex;flex-direction:column;gap:4px;">
                    <div class="sdg-news-step"><span class="sdg-news-n" style="background:#c07c2a;">1</span><span>_rss() × 4 em paralelo</span></div>
                    <div class="sdg-news-step"><span class="sdg-news-n" style="background:#9a7e52;">2</span><span>_classif() → Macro/Empresas/Mkt</span></div>
                    <div class="sdg-news-step"><span class="sdg-news-n" style="background:#7a6340;">3</span><span>_score() → fonte + recência + R$</span></div>
                    <div class="sdg-news-step"><span class="sdg-news-n" style="background:#5a4830;">4</span><span>_dedup() → Jaccard 65%</span></div>
                  </div>
                </div>
              </div>

            </div>

            <!-- conector 03+04 → 05 -->
            <div class="sdg-connector" style="padding-left:52px;">
              <span class="sdg-conn-label">JSONs + news injetados no template</span>
            </div>

            <!-- ── NÓ 05: HTML ── -->
            <div class="sdg-row" data-mod="5" onclick="sysSelectMod(5)">
              <div class="sdg-dot sdg-dot--green">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
              </div>
              <div class="sdg-card sdg-card--green">
                <div class="sdg-card-head">
                  <span class="sdg-badge" style="background:linear-gradient(135deg,#2fa874,#52c896);color:#fff;">05</span>
                  <div style="flex:1;margin-left:10px;">
                    <div class="sdg-title">Geração do HTML Final</div>
                    <div class="sdg-tech">HTML_TEMPLATE · f-string injection · webbrowser</div>
                  </div>
                  <span class="sdg-tag" style="background:rgba(47,168,116,.1);color:#2fa874;border-color:rgba(47,168,116,.3);">STANDALONE</span>
                </div>
                <div class="sdg-chips" style="margin-top:8px;">
                  <span class="sdg-chip" style="border-color:rgba(47,168,116,.25);color:#1a7a52;">SPA · 10 views</span>
                  <span class="sdg-chip" style="border-color:rgba(47,168,116,.25);color:#1a7a52;">Logo base64</span>
                  <span class="sdg-chip" style="border-color:rgba(47,168,116,.25);color:#1a7a52;">Gráficos embutidos</span>
                  <span class="sdg-chip" style="border-color:rgba(47,168,116,.25);color:#1a7a52;">Zero servidor</span>
                  <span class="sdg-chip" style="border-color:rgba(47,168,116,.25);color:#1a7a52;">Abre no browser</span>
                </div>
              </div>
            </div>

            <!-- conector 05 → 06 -->
            <div class="sdg-connector">
              <span class="sdg-conn-label">chatbot vive dentro do HTML gerado</span>
            </div>

            <!-- ── NÓ 06: NLQ — destaque máximo ── -->
            <div class="sdg-row" data-mod="6" onclick="sysSelectMod(6)">
              <div class="sdg-dot sdg-dot--gold" style="background:linear-gradient(135deg,#b69d74,#d4b47a);">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </div>
              <div class="sdg-card sdg-card--gold sdg-card--wide sdg-card--nlq">
                <div class="sdg-card-head" style="margin-bottom:10px;">
                  <span class="sdg-badge" style="background:linear-gradient(135deg,#b69d74,#d4b47a);color:#fff;font-size:10px;padding:3px 9px;">06</span>
                  <div style="flex:1;margin-left:10px;">
                    <div class="sdg-title" style="font-size:13px;">Motor NLQ — Dourado</div>
                    <div class="sdg-tech">NLQ offline · 20 intents · PT-BR nativo</div>
                  </div>
                  <span class="sdg-tag" style="background:rgba(47,168,116,.12);color:#2fa874;border-color:rgba(47,168,116,.3);font-size:8px;">0 APIs EXTERNAS</span>
                </div>
                <!-- pipeline NLQ visual -->
                <div style="display:flex;align-items:center;gap:0;margin-bottom:12px;background:rgba(182,157,116,.06);border:1px solid rgba(182,157,116,.15);border-radius:8px;padding:8px 12px;overflow-x:auto;">
                  <div class="sdg-pipe-step" style="border-color:rgba(182,157,116,.3);color:#7a6340;"><span style="font-size:8px;font-family:'DM Mono',monospace;font-weight:700;">_norm()</span><span style="font-size:7px;color:#9a9288;display:block;">NFD · acentos</span></div>
                  <div class="sdg-pipe-arr">→</div>
                  <div class="sdg-pipe-step" style="border-color:rgba(182,157,116,.3);color:#7a6340;"><span style="font-size:8px;font-family:'DM Mono',monospace;font-weight:700;">Entidades</span><span style="font-size:7px;color:#9a9288;display:block;">emissor·setor·rating</span></div>
                  <div class="sdg-pipe-arr">→</div>
                  <div class="sdg-pipe-step" style="border-color:rgba(182,157,116,.3);color:#7a6340;"><span style="font-size:8px;font-family:'DM Mono',monospace;font-weight:700;">_matchIntent()</span><span style="font-size:7px;color:#9a9288;display:block;">KW + cosseno</span></div>
                  <div class="sdg-pipe-arr">→</div>
                  <div class="sdg-pipe-step" style="border-color:rgba(182,157,116,.3);color:#7a6340;"><span style="font-size:8px;font-family:'DM Mono',monospace;font-weight:700;">_queryAtivos()</span><span style="font-size:7px;color:#9a9288;display:block;">resposta + chart</span></div>
                </div>
                <!-- grid de intents -->
                <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:4px;">
                  <span class="sdn-tag">exposicao_emissor</span><span class="sdn-tag">exposicao_setor</span><span class="sdn-tag">exposicao_rating</span><span class="sdn-tag">overview_carteira</span><span class="sdn-tag">top_exposicoes</span>
                  <span class="sdn-tag">query_param</span><span class="sdn-tag">multi_filtro</span><span class="sdn-tag">fund_delta</span><span class="sdn-tag">spread_delta</span><span class="sdn-tag">detalhe_ativo</span>
                  <span class="sdn-tag">sintese_emissor</span><span class="sdn-tag">grafico_spread</span><span class="sdn-tag">mapa_risco</span><span class="sdn-tag">risco_estresse</span><span class="sdn-tag">mapa_vencimentos</span>
                  <span class="sdn-tag">analise_spreads</span><span class="sdn-tag">comparar_emissores</span><span class="sdn-tag">duration_carteira</span><span class="sdn-tag">grafico_setor</span><span class="sdn-tag">status_cobertura</span>
                </div>
              </div>
            </div>

          </div><!-- /position:relative -->
        </div><!-- /coluna diagrama -->

        <!-- ── COLUNA DIREITA: painel didático fixo ── -->
        <div style="width:300px;flex-shrink:0;border-left:1px solid #edeae3;background:#ffffff;display:flex;flex-direction:column;overflow:hidden;">

          <!-- header do painel -->
          <div style="padding:16px 18px 12px;border-bottom:1px solid #edeae3;background:#fafaf8;flex-shrink:0;">
            <div style="font-size:7.5px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:rgba(182,157,116,.55);font-family:'DM Mono',monospace;margin-bottom:6px;">EM OUTRAS PALAVRAS</div>
            <div id="sdgPanelTitle" style="font-size:14px;font-weight:700;color:#1f2839;letter-spacing:-.3px;line-height:1.3;">Inicialização &amp; Modo</div>
          </div>

          <!-- conteúdo scrollável -->
          <div id="sdgPanelBody" style="flex:1;overflow-y:auto;padding:18px;"></div>

          <!-- rodapé com métricas -->
          <div style="padding:12px 18px;border-top:1px solid #edeae3;background:#fafaf8;flex-shrink:0;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
              <div style="text-align:center;padding:8px;background:#fff;border-radius:8px;border:1px solid rgba(182,157,116,.15);">
                <div style="font-size:18px;font-weight:800;color:#b69d74;letter-spacing:-.5px;">7</div>
                <div style="font-size:8px;color:#9a9288;font-family:'DM Mono',monospace;">módulos</div>
              </div>
              <div style="text-align:center;padding:8px;background:#fff;border-radius:8px;border:1px solid rgba(107,92,165,.2);">
                <div style="font-size:18px;font-weight:800;color:#6b5ca5;letter-spacing:-.5px;">1</div>
                <div style="font-size:8px;color:#9a9288;font-family:'DM Mono',monospace;">APIs externas</div>
              </div>
              <div style="text-align:center;padding:8px;background:#fff;border-radius:8px;border:1px solid rgba(0,130,155,.12);">
                <div style="font-size:18px;font-weight:800;color:#0082a0;letter-spacing:-.5px;">10+</div>
                <div style="font-size:8px;color:#9a9288;font-family:'DM Mono',monospace;">fontes de dados</div>
              </div>
              <div style="text-align:center;padding:8px;background:#fff;border-radius:8px;border:1px solid rgba(182,157,116,.15);">
                <div style="font-size:18px;font-weight:800;color:#b69d74;letter-spacing:-.5px;">20</div>
                <div style="font-size:8px;color:#9a9288;font-family:'DM Mono',monospace;">intents NLQ</div>
              </div>
            </div>
          </div>

        </div><!-- /painel didático -->

      </div><!-- /sysViewDiagram -->

      <!-- ══════════════════════════════════════════════ -->
      <!-- VIEW B: TERMINAL (opção 3 — dark log + prose) -->
      <!-- ══════════════════════════════════════════════ -->
      <div id="sysViewTerminal" style="flex:1;overflow:hidden;display:none;min-height:0;">
        <div style="display:flex;height:100%;">

          <!-- painel dark — terminal de logs -->
          <div style="flex:1;background:#0d1117;overflow-y:auto;padding:22px 24px;font-family:'DM Mono',monospace;font-size:11px;line-height:1.85;border-right:1px solid #21262d;">
            <div style="color:#8b949e;margin-bottom:18px;font-size:9px;letter-spacing:.12em;text-transform:uppercase;">OVERVIEW CRÉDITO · BUILD LOG</div>
            <div id="sysTermLog"></div>
            <div style="display:flex;align-items:center;gap:6px;margin-top:12px;">
              <span style="color:#3fb950;">$</span>
              <span style="color:#e6edf3;">_</span>
              <span style="width:8px;height:14px;background:#e6edf3;display:inline-block;animation:termCursor .9s step-end infinite;"></span>
            </div>
          </div>

          <!-- painel branco — prose explicativa -->
          <div style="flex:1;overflow-y:auto;padding:22px 26px;background:#fdfdfc;">
            <div style="font-size:8px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:rgba(0,130,155,.5);margin-bottom:18px;font-family:'DM Mono',monospace;">O QUE ESTÁ ACONTECENDO</div>
            <div id="sysTermProse"></div>
          </div>

        </div>
      </div><!-- /sysViewTerminal -->

      <!-- ══════════════════════════════════════════════ -->
      <!-- VIEW C: ATALHOS DE TECLADO                    -->
      <!-- ══════════════════════════════════════════════ -->
      <div id="sysViewShortcuts" style="flex:1;overflow-y:auto;display:none;background:#f8f7f4;padding:28px 36px;min-height:0;">

        <div style="max-width:900px;margin:0 auto;">

          <!-- título da seção -->
          <div style="margin-bottom:28px;">
            <div style="font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:rgba(182,157,116,.6);font-family:'DM Mono',monospace;margin-bottom:6px;">KEYBOARD SHORTCUTS</div>
            <div style="font-size:20px;font-weight:700;color:#1f2839;letter-spacing:-.4px;">Atalhos do Sistema</div>
            <div style="font-size:12px;color:#7a7268;margin-top:4px;">Todos os atalhos disponíveis no Overview de Crédito · Douro Capital</div>
          </div>

          <!-- grupo: painéis principais -->
          <div style="margin-bottom:24px;">
            <div style="font-size:8px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#b69d74;font-family:'DM Mono',monospace;margin-bottom:12px;display:flex;align-items:center;gap:10px;">
              PAINÉIS PRINCIPAIS
              <span style="flex:1;height:1px;background:rgba(182,157,116,.2);display:block;"></span>
            </div>
            <div style="display:flex;flex-direction:column;gap:8px;">

              <!-- War Room -->
              <div style="display:flex;align-items:flex-start;gap:16px;background:#fff;border:1px solid #ede9e0;border-radius:12px;padding:16px 20px;transition:box-shadow .18s;" onmouseover="this.style.boxShadow='0 4px 20px rgba(182,157,116,.12)'" onmouseout="this.style.boxShadow='none'">
                <div style="display:flex;gap:5px;flex-shrink:0;align-items:center;margin-top:1px;">
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f0ede6;border:1px solid rgba(182,157,116,.35);border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#7a6340;letter-spacing:.03em;">Ctrl</span>
                  <span style="font-size:10px;color:#b0a898;font-weight:600;">+</span>
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f0ede6;border:1px solid rgba(182,157,116,.35);border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#7a6340;">Shift</span>
                  <span style="font-size:10px;color:#b0a898;font-weight:600;">+</span>
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#b69d74,#d4b47a);border-radius:6px;padding:3px 10px;font-size:11px;font-weight:800;font-family:'DM Mono',monospace;color:#fff;box-shadow:0 2px 6px rgba(182,157,116,.35);">R</span>
                </div>
                <div style="flex:1;">
                  <div style="font-size:13px;font-weight:700;color:#1f2839;margin-bottom:3px;">War Room · Comitê de Crédito</div>
                  <div style="font-size:11.5px;color:#6a6258;line-height:1.6;">Abre/fecha o painel completo do War Room — visão consolidada da carteira em tempo real com semáforo de risco, exposição por emissor e setor, alertas de rating e análise de stress. Pressionar novamente ou <kbd style="background:#f0ede6;border:1px solid #ddd;border-radius:3px;padding:1px 5px;font-size:9px;font-family:'DM Mono',monospace;">ESC</kbd> fecha o painel.</div>
                </div>
                <div style="flex-shrink:0;">
                  <span style="background:rgba(182,157,116,.1);color:#9a7e52;border:1px solid rgba(182,157,116,.25);border-radius:6px;padding:2px 9px;font-size:9px;font-weight:700;font-family:'DM Mono',monospace;letter-spacing:.06em;">TOGGLE</span>
                </div>
              </div>

              <!-- Global Search -->
              <div style="display:flex;align-items:flex-start;gap:16px;background:#fff;border:1px solid #ede9e0;border-radius:12px;padding:16px 20px;transition:box-shadow .18s;" onmouseover="this.style.boxShadow='0 4px 20px rgba(49,116,184,.08)'" onmouseout="this.style.boxShadow='none'">
                <div style="display:flex;gap:5px;flex-shrink:0;align-items:center;margin-top:1px;">
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f0ede6;border:1px solid rgba(182,157,116,.35);border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#7a6340;">Ctrl</span>
                  <span style="font-size:10px;color:#b0a898;font-weight:600;">+</span>
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#3174b8,#5b9bd5);border-radius:6px;padding:3px 10px;font-size:11px;font-weight:800;font-family:'DM Mono',monospace;color:#fff;box-shadow:0 2px 6px rgba(49,116,184,.3);">P</span>
                </div>
                <div style="flex:1;">
                  <div style="font-size:13px;font-weight:700;color:#1f2839;margin-bottom:3px;">Global Search — Busca Rápida</div>
                  <div style="font-size:11.5px;color:#6a6258;line-height:1.6;">Abre a paleta de busca global do sistema. Digite qualquer trecho do nome de um ativo, emissor, ticker ou setor para localizar instantaneamente. Navegue nos resultados com <kbd style="background:#f0ede6;border:1px solid #ddd;border-radius:3px;padding:1px 5px;font-size:9px;font-family:'DM Mono',monospace;">↑</kbd> <kbd style="background:#f0ede6;border:1px solid #ddd;border-radius:3px;padding:1px 5px;font-size:9px;font-family:'DM Mono',monospace;">↓</kbd> e confirme com <kbd style="background:#f0ede6;border:1px solid #ddd;border-radius:3px;padding:1px 5px;font-size:9px;font-family:'DM Mono',monospace;">Enter</kbd>. Disponível em qualquer tela.</div>
                </div>
                <div style="flex-shrink:0;">
                  <span style="background:rgba(49,116,184,.08);color:#3174b8;border:1px solid rgba(49,116,184,.2);border-radius:6px;padding:2px 9px;font-size:9px;font-weight:700;font-family:'DM Mono',monospace;letter-spacing:.06em;">GLOBAL</span>
                </div>
              </div>

              <!-- Comparador -->
              <div style="display:flex;align-items:flex-start;gap:16px;background:#fff;border:1px solid #ede9e0;border-radius:12px;padding:16px 20px;transition:box-shadow .18s;" onmouseover="this.style.boxShadow='0 4px 20px rgba(107,92,165,.08)'" onmouseout="this.style.boxShadow='none'">
                <div style="display:flex;gap:5px;flex-shrink:0;align-items:center;margin-top:1px;">
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f0ede6;border:1px solid rgba(182,157,116,.35);border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#7a6340;">Ctrl</span>
                  <span style="font-size:10px;color:#b0a898;font-weight:600;">+</span>
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f0ede6;border:1px solid rgba(182,157,116,.35);border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#7a6340;">Shift</span>
                  <span style="font-size:10px;color:#b0a898;font-weight:600;">+</span>
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#6b5ca5,#9880d0);border-radius:6px;padding:3px 10px;font-size:11px;font-weight:800;font-family:'DM Mono',monospace;color:#fff;box-shadow:0 2px 6px rgba(107,92,165,.3);">C</span>
                </div>
                <div style="flex:1;">
                  <div style="font-size:13px;font-weight:700;color:#1f2839;margin-bottom:3px;">Comparador de Emissores</div>
                  <div style="font-size:11.5px;color:#6a6258;line-height:1.6;">Abre o painel de comparação lado a lado entre dois emissores. Digite o nome nos campos A e B — o sistema faz fuzzy match contra todos os emissores da carteira e exibe fundamentos financeiros (EBITDA, Dív.Liq/EBITDA, ROE, ROIC, FCF, liquidez), indicadores BCB para bancos, posições abertas e status do comitê em tempo real.</div>
                </div>
                <div style="flex-shrink:0;">
                  <span style="background:rgba(107,92,165,.08);color:#6b5ca5;border:1px solid rgba(107,92,165,.2);border-radius:6px;padding:2px 9px;font-size:9px;font-weight:700;font-family:'DM Mono',monospace;letter-spacing:.06em;">ANÁLISE</span>
                </div>
              </div>

              <!-- Debug Overlay -->
              <div style="display:flex;align-items:flex-start;gap:16px;background:#fff;border:1px solid #ede9e0;border-radius:12px;padding:16px 20px;transition:box-shadow .18s;" onmouseover="this.style.boxShadow='0 4px 20px rgba(47,168,116,.08)'" onmouseout="this.style.boxShadow='none'">
                <div style="display:flex;gap:5px;flex-shrink:0;align-items:center;margin-top:1px;">
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f0ede6;border:1px solid rgba(182,157,116,.35);border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#7a6340;">Ctrl</span>
                  <span style="font-size:10px;color:#b0a898;font-weight:600;">+</span>
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f0ede6;border:1px solid rgba(182,157,116,.35);border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#7a6340;">Shift</span>
                  <span style="font-size:10px;color:#b0a898;font-weight:600;">+</span>
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0d7050,#2fa874);border-radius:6px;padding:3px 10px;font-size:11px;font-weight:800;font-family:'DM Mono',monospace;color:#fff;box-shadow:0 2px 6px rgba(47,168,116,.3);">D</span>
                </div>
                <div style="flex:1;">
                  <div style="font-size:13px;font-weight:700;color:#1f2839;margin-bottom:3px;">Debug Overlay — Diagnóstico do Sistema</div>
                  <div style="font-size:11.5px;color:#6a6258;line-height:1.6;">Abre o painel técnico de diagnóstico com fundo Matrix animado. Exibe em tempo real: contagem de ativos, emissores únicos, cobertura do FIN_SERIES, bancos BCB, notícias curadas, PL total, todos os dados injetados pelo Python e o log do sistema. Útil para validar se o build gerou dados completos.</div>
                </div>
                <div style="flex-shrink:0;">
                  <span style="background:rgba(47,168,116,.08);color:#2fa874;border:1px solid rgba(47,168,116,.2);border-radius:6px;padding:2px 9px;font-size:9px;font-weight:700;font-family:'DM Mono',monospace;letter-spacing:.06em;">DEV</span>
                </div>
              </div>

            </div>
          </div>

          <!-- grupo: navegação e chat -->
          <div style="margin-bottom:24px;">
            <div style="font-size:8px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#b69d74;font-family:'DM Mono',monospace;margin-bottom:12px;display:flex;align-items:center;gap:10px;">
              NAVEGAÇÃO &amp; CHAT
              <span style="flex:1;height:1px;background:rgba(182,157,116,.2);display:block;"></span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">

              <!-- ESC -->
              <div style="display:flex;align-items:flex-start;gap:14px;background:#fff;border:1px solid #ede9e0;border-radius:12px;padding:14px 18px;">
                <div style="flex-shrink:0;margin-top:1px;">
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f5f3ef;border:1px solid #ddd;border-radius:6px;padding:3px 10px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#5a5248;">ESC</span>
                </div>
                <div>
                  <div style="font-size:12px;font-weight:700;color:#1f2839;margin-bottom:3px;">Fechar Painel Ativo</div>
                  <div style="font-size:11px;color:#6a6258;line-height:1.55;">Fecha qualquer painel aberto — War Room, Busca Global, Comparador, Debug ou este modal. Funciona como saída universal em todo o sistema.</div>
                </div>
              </div>

              <!-- Enter -->
              <div style="display:flex;align-items:flex-start;gap:14px;background:#fff;border:1px solid #ede9e0;border-radius:12px;padding:14px 18px;">
                <div style="flex-shrink:0;margin-top:1px;">
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f5f3ef;border:1px solid #ddd;border-radius:6px;padding:3px 10px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#5a5248;">Enter</span>
                </div>
                <div>
                  <div style="font-size:12px;font-weight:700;color:#1f2839;margin-bottom:3px;">Enviar Mensagem — Dourado IA</div>
                  <div style="font-size:11px;color:#6a6258;line-height:1.55;">Envia a mensagem no chat Dourado. Use <kbd style="background:#f0ede6;border:1px solid #ddd;border-radius:3px;padding:1px 5px;font-size:9px;font-family:'DM Mono',monospace;">Shift+Enter</kbd> para quebra de linha sem enviar. Dourado interpreta perguntas sobre emissores, spreads, alavancagem, rating e vencimentos.</div>
                </div>
              </div>

              <!-- Setas -->
              <div style="display:flex;align-items:flex-start;gap:14px;background:#fff;border:1px solid #ede9e0;border-radius:12px;padding:14px 18px;">
                <div style="display:flex;gap:4px;flex-shrink:0;margin-top:1px;">
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f5f3ef;border:1px solid #ddd;border-radius:6px;padding:3px 8px;font-size:11px;font-weight:700;font-family:'DM Mono',monospace;color:#5a5248;">↑</span>
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f5f3ef;border:1px solid #ddd;border-radius:6px;padding:3px 8px;font-size:11px;font-weight:700;font-family:'DM Mono',monospace;color:#5a5248;">↓</span>
                </div>
                <div>
                  <div style="font-size:12px;font-weight:700;color:#1f2839;margin-bottom:3px;">Navegar Resultados</div>
                  <div style="font-size:11px;color:#6a6258;line-height:1.55;">Navega pelos resultados da Busca Global sem tirar as mãos do teclado. Pressione <kbd style="background:#f0ede6;border:1px solid #ddd;border-radius:3px;padding:1px 5px;font-size:9px;font-family:'DM Mono',monospace;">Enter</kbd> para abrir o item selecionado.</div>
                </div>
              </div>

              <!-- Shift+Enter placeholder -->
              <div style="display:flex;align-items:flex-start;gap:14px;background:#faf9f7;border:1px solid #ede9e0;border-radius:12px;padding:14px 18px;opacity:.65;">
                <div style="flex-shrink:0;margin-top:1px;">
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f5f3ef;border:1px solid #ddd;border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#9a9288;">Shift</span>
                  <span style="font-size:10px;color:#c0bab2;font-weight:600;margin:0 3px;">+</span>
                  <span style="display:inline-flex;align-items:center;justify-content:center;background:#f5f3ef;border:1px solid #ddd;border-radius:6px;padding:3px 8px;font-size:10px;font-weight:700;font-family:'DM Mono',monospace;color:#9a9288;">Enter</span>
                </div>
                <div>
                  <div style="font-size:12px;font-weight:700;color:#4a4540;margin-bottom:3px;">Quebra de Linha no Chat</div>
                  <div style="font-size:11px;color:#8a8278;line-height:1.55;">Insere uma quebra de linha no campo de texto do Dourado sem disparar o envio. Ideal para perguntas mais estruturadas com múltiplas linhas.</div>
                </div>
              </div>

            </div>
          </div>

          <!-- dica de rodapé -->
          <div style="background:linear-gradient(135deg,rgba(182,157,116,.07),rgba(182,157,116,.03));border:1px solid rgba(182,157,116,.2);border-radius:10px;padding:13px 18px;display:flex;align-items:center;gap:12px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#b69d74" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
            <div style="font-size:10.5px;color:#7a6a58;line-height:1.5;">Todos os atalhos usam <b style="color:#5a4a38;">e.preventDefault()</b> para suprimir comportamentos padrão do browser. Se um atalho não responder, verifique se o foco não está em um campo de texto externo ao sistema.</div>
          </div>

        </div>
      </div><!-- /sysViewShortcuts -->

      <!-- ── FOOTER ── -->
      <div style="padding:8px 22px;border-top:1px solid #edeae3;background:#fafaf8;flex-shrink:0;display:flex;align-items:center;justify-content:space-between;">
        <div style="font-size:8px;color:rgba(154,126,82,.45);font-family:'DM Mono',monospace;letter-spacing:.06em;">DOURO CAPITAL · OVERVIEW DE CRÉDITO · DISTRIBUIÇÃO PRIVADA</div>
        <div style="display:flex;align-items:center;gap:5px;"><div style="width:5px;height:5px;border-radius:50%;background:#2fa874;box-shadow:0 0 6px rgba(47,168,116,.6);animation:pulse 2s ease-in-out infinite;"></div><div style="font-size:8px;color:rgba(47,168,116,.65);font-family:'DM Mono',monospace;">SISTEMA OPERACIONAL</div></div>
      </div>
    </div>
  </div>

  <style>
  #sysInfoBtn:hover {{ opacity:1 !important; border-color:rgba(182,157,116,.55) !important; color:rgba(182,157,116,.75) !important; }}
  @keyframes sysModalIn {{ from {{ opacity:0; transform:scale(.97) translateY(10px); }} to {{ opacity:1; transform:scale(1) translateY(0); }} }}
  #sysInfoInner {{ animation:sysModalIn .3s cubic-bezier(.16,1,.3,1); }}
  @keyframes termCursor {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0; }} }}
  @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:.4; }} }}
  @keyframes flowPop {{ from {{ opacity:0; transform:translateY(5px); }} to {{ opacity:1; transform:translateY(0); }} }}
  @keyframes sdgCardIn {{ from {{ opacity:0; transform:translateX(12px); }} to {{ opacity:1; transform:translateX(0); }} }}

  /* ── DIAGRAMA: trilho + rows ── */
  .sdg-row {{ display:flex;align-items:flex-start;gap:12px;margin-bottom:0;position:relative;z-index:1;padding-bottom:0;cursor:pointer; }}
  .sdg-dot {{ width:38px;height:38px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;margin-top:14px;position:relative;z-index:2;box-shadow:0 2px 8px rgba(0,0,0,.15);transition:transform .2s; }}
  .sdg-row:hover .sdg-dot {{ transform:scale(1.12); }}
  .sdg-dot--gold {{ background:linear-gradient(135deg,#b69d74,#d4b47a); }}
  .sdg-dot--teal {{ background:linear-gradient(135deg,#0082a0,#00b4d8); }}
  .sdg-dot--green {{ background:linear-gradient(135deg,#2fa874,#52c896); }}

  /* ── cards ── */
  .sdg-card {{ flex:1;background:#fff;border:1.5px solid #e8e3db;border-radius:12px;padding:14px 16px;transition:all .22s cubic-bezier(.16,1,.3,1);box-shadow:0 1px 4px rgba(0,0,0,.04);margin-bottom:0; }}
  .sdg-card:hover {{ transform:translateY(-2px);box-shadow:0 6px 22px rgba(0,0,0,.09); }}
  .sdg-card--half {{ cursor:pointer; }}
  .sdg-card--wide {{ }}
  .sdg-card--gold {{ border-color:rgba(182,157,116,.28);background:linear-gradient(160deg,#fdfcf8 0%,#fff 60%); }}
  .sdg-card--gold:hover {{ border-color:rgba(182,157,116,.5);box-shadow:0 6px 22px rgba(182,157,116,.14); }}
  .sdg-card--teal {{ border-color:rgba(0,130,155,.2);background:linear-gradient(160deg,#f8fdfe 0%,#fff 60%); }}
  .sdg-card--teal:hover {{ border-color:rgba(0,130,155,.4);box-shadow:0 6px 22px rgba(0,130,155,.1); }}
  .sdg-card--blue {{ border-color:rgba(49,116,184,.2);background:linear-gradient(160deg,#f8fbff 0%,#fff 60%); }}
  .sdg-card--blue:hover {{ border-color:rgba(49,116,184,.4);box-shadow:0 6px 22px rgba(49,116,184,.1); }}
  .sdg-card--amber {{ border-color:rgba(192,124,42,.22);background:linear-gradient(160deg,#fdf9f3 0%,#fff 60%); }}
  .sdg-card--amber:hover {{ border-color:rgba(192,124,42,.42);box-shadow:0 6px 22px rgba(192,124,42,.1); }}
  .sdg-card--green {{ border-color:rgba(47,168,116,.2);background:linear-gradient(160deg,#f7fdf9 0%,#fff 60%); }}
  .sdg-card--green:hover {{ border-color:rgba(47,168,116,.4);box-shadow:0 6px 22px rgba(47,168,116,.1); }}
  .sdg-card--nlq {{ background:linear-gradient(160deg,#fdfcf7 0%,#fffef9 100%); }}
  .sdg-card-active {{ box-shadow:0 0 0 2.5px rgba(182,157,116,.5),0 6px 22px rgba(182,157,116,.16) !important;transform:translateY(-2px) !important; }}

  .sdg-card-head {{ display:flex;align-items:center;gap:0; }}
  .sdg-badge {{ font-size:9px;font-weight:800;font-family:'DM Mono',monospace;padding:3px 8px;border-radius:6px;flex-shrink:0; }}
  .sdg-title {{ font-size:11.5px;font-weight:700;color:#1f2839; }}
  .sdg-tech {{ font-size:8px;color:#9a9288;font-family:'DM Mono',monospace;margin-top:1px; }}
  .sdg-tag {{ font-size:7.5px;font-weight:700;letter-spacing:.06em;padding:2px 7px;border-radius:5px;border:1px solid;font-family:'DM Mono',monospace;white-space:nowrap; }}
  .sdg-chips {{ display:flex;flex-wrap:wrap;gap:4px;margin-top:8px; }}
  .sdg-chip {{ font-size:8.5px;padding:3px 8px;border-radius:5px;border:1px solid;background:transparent;font-family:'DM Mono',monospace; }}

  /* conectores entre nós */
  .sdg-connector {{ display:flex;align-items:center;gap:0;padding:4px 0 4px 18px;position:relative;z-index:1; }}
  .sdg-conn-label {{ font-size:8px;color:rgba(182,157,116,.55);font-family:'DM Mono',monospace;font-style:italic;padding-left:42px; }}

  /* fontes de dados */
  .sdg-source-row {{ display:flex;align-items:center;gap:6px; }}
  .sdg-src-dot {{ width:5px;height:5px;border-radius:50%;flex-shrink:0; }}
  .sdg-src-name {{ font-size:9px;font-weight:600;color:#3a3530;flex-shrink:0; }}
  .sdg-src-detail {{ font-size:8px;color:#9a9288;font-family:'DM Mono',monospace; }}

  /* KPI rows */
  .sdg-kpi-row {{ display:flex;align-items:baseline;gap:6px; }}
  .sdg-kpi-label {{ font-size:8px;font-weight:700;color:#9a9288;font-family:'DM Mono',monospace;width:42px;flex-shrink:0; }}
  .sdg-kpi-val {{ font-size:8.5px;font-weight:600; }}

  /* news steps */
  .sdg-news-step {{ display:flex;align-items:center;gap:7px;font-size:9px;color:#6b5c46; }}
  .sdg-news-n {{ width:16px;height:16px;border-radius:50%;color:#fff;font-size:8px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0; }}

  /* NLQ pipeline */
  .sdg-pipe-step {{ background:#fff;border:1px solid rgba(182,157,116,.25);border-radius:7px;padding:6px 10px;text-align:center;white-space:nowrap; }}
  .sdg-pipe-arr {{ color:rgba(182,157,116,.4);font-size:14px;padding:0 4px;flex-shrink:0; }}

  /* tags intents */
  .sdn-tag {{ font-size:7.5px;padding:2px 6px;border-radius:3px;background:#faf7f2;border:1px solid rgba(182,157,116,.2);color:rgba(154,126,82,.75);font-family:'DM Mono',monospace; }}

  /* painel didático direito */
  .sdg-prose-title {{ font-size:12px;font-weight:700;color:#1f2839;margin:0 0 8px; }}
  .sdg-prose-body {{ font-size:10.5px;color:#6b6256;line-height:1.75; }}
  .sdg-prose-body strong {{ color:#1f2839; }}
  .sdg-prose-highlight {{ background:#faf7f2;border:1px solid rgba(182,157,116,.2);border-left:3px solid #b69d74;border-radius:0 6px 6px 0;padding:9px 12px;margin:10px 0;font-size:10px;color:#5a4a38;line-height:1.65;font-style:italic; }}

  /* terminal */
  .tlog-ok {{ color:#3fb950; }}
  .tlog-info {{ color:#58a6ff; }}
  .tlog-warn {{ color:#d29922; }}
  .tlog-dim {{ color:#8b949e; }}
  .tlog-gold {{ color:#d4b47a; }}
  .tlog-section {{ color:#6e7681;margin-top:10px;margin-bottom:1px;font-size:9px;letter-spacing:.12em;text-transform:uppercase;border-top:1px solid #21262d;padding-top:10px; }}
  .tprose-card {{ margin-bottom:13px;padding:14px;border-radius:10px;border:1px solid;animation:flowPop .25s ease; }}
  .tprose-card h4 {{ font-size:11px;font-weight:700;color:#1f2839;margin:0 0 6px; }}
  .tprose-card p {{ font-size:10.5px;color:#6b6256;line-height:1.72;margin:0; }}
  #sysInfoBody *::-webkit-scrollbar {{ width:3px; }}
  #sysInfoBody *::-webkit-scrollbar-thumb {{ background:rgba(182,157,116,.2);border-radius:3px; }}
  </style>

  <script>
  /* ── CONTEÚDO DIDÁTICO do painel direito ── */
  const _SYS_PROSE = [
    {{
      title: 'Inicialização &amp; Modo',
      html: '<p class="sdg-prose-body">Quando você executa o script, ele começa fazendo uma única pergunta: <strong>modo 1</strong> (relatório completo) ou <strong>modo 2</strong> (só notícias rápidas)?</p><div class="sdg-prose-highlight">No modo 2, tudo termina em segundos — busca os feeds RSS, pontua as notícias e gera um HTML leve. No modo 1, todos os outros módulos são ativados em sequência.</div><p class="sdg-prose-body" style="margin-top:8px;">Antes de prosseguir, valida que os arquivos Excel existem, que as credenciais Comdinheiro estão configuradas e que o usuário é reconhecido — evitando falhas silenciosas mais tarde.</p>'
    }},
    {{
      title: 'Extração Paralela de Dados',
      html: '<p class="sdg-prose-body">Em vez de baixar uma fonte de cada vez, o sistema dispara <strong>10+ conexões ao mesmo tempo</strong> usando duas tecnologias:</p><div class="sdg-prose-highlight"><strong>ThreadPoolExecutor</strong> para tarefas pesadas de I/O (ler Excel, chamar Comdinheiro).<br><strong>asyncio + aiohttp</strong> para downloads de rede (CVM, Tesouro Direto).</div><p class="sdg-prose-body" style="margin-top:8px;">O resultado: o que levaria ~40 segundos sequencial termina em ~4 segundos. Os ZIPs da CVM cobrem demonstrativos financeiros de <strong>2011 até hoje</strong> — DRE, Balanço Ativo, Passivo e Fluxo de Caixa.</p>'
    }},
    {{
      title: 'Cálculos Financeiros',
      html: '<p class="sdg-prose-body">Com os dados brutos em mãos, o sistema monta todos os indicadores que aparecem na plataforma:</p><div class="sdg-prose-highlight">EBITDA · Dívida Líquida · FCF · ROE · ROIC — calculados em janela TTM (últimos 12 meses) e 36 meses.</div><p class="sdg-prose-body" style="margin-top:8px;">Para o spread, compara a taxa de cada ativo de crédito com a NTN-B de referência mais próxima, e calcula o z-score histórico para detectar se o spread está caro ou barato versus o próprio histórico.</p><div class="sdg-prose-highlight">Uma regra importante: D&A é sempre identificado pelo <strong>nome da conta</strong> (ex: "DEPRECIA"), nunca pelo código contábil — que muda de empresa para empresa.</div>'
    }},
    {{
      title: 'Indicadores Bancários — BCB IF.data',
      html: '<p class="sdg-prose-body">Para a aba <strong>Bancos</strong>, o sistema consulta diretamente a <strong>API pública do Banco Central</strong> (olinda.bcb.gov.br/IFDATA) — sem scraping, sem planilha manual:</p><div class="sdg-prose-highlight">Relatório 2 (Ativo) · Relatório 3 (Passivo) · Relatório 4 (DRE) · Relatório 5 (Estrutura de Capital) — para <strong>27 bancos</strong> do portfólio, de 2021 a 2024.</div><p class="sdg-prose-body" style="margin-top:8px;">Os nomes dos bancos são mapeados por similaridade contra o <em>Watch List Bancos.xlsm</em>, garantindo que <strong>BTG Pactual</strong>, <strong>Banco ABC</strong>, <strong>Daycoval</strong> etc. batam com os nomes exatos da planilha de rating. Dados reais têm prioridade; os valores estáticos de referência são usados só como fallback se a API estiver fora do ar.</p>'
    }},
    {{
      title: 'News Pipeline',
      html: '<p class="sdg-prose-body">4 feeds RSS são lidos em paralelo. Cada notícia passa por um <strong>sistema de pontuação</strong> antes de entrar na plataforma:</p><div class="sdg-prose-highlight">+pontos: fonte confiável · notícia recente · menciona R$ · verbos de evento ("anuncia", "corta", "revisa") · emissor está na carteira.</div><p class="sdg-prose-body" style="margin-top:8px;">No final, duplicatas são removidas por <strong>similaridade de Jaccard</strong> — se dois títulos compartilham mais de 65% das palavras, só o de maior score entra. O resultado são as notícias curadas que aparecem na aba Douro News.</p>'
    }},
    {{
      title: 'Geração do HTML Final',
      html: '<p class="sdg-prose-body">Todos os dados calculados são injetados como variáveis JavaScript dentro de um único template HTML gigante:</p><div class="sdg-prose-highlight">window.ATIVOS · window.SPREADS_TS · window.FIN_SERIES · window.NEWS — embutidos diretamente no arquivo, sem servidor.</div><p class="sdg-prose-body" style="margin-top:8px;">O resultado é um arquivo <strong>standalone</strong>: logo em base64, gráficos, SPA com 10 telas, o chatbot Dourado — tudo em um único .html que abre com dois cliques em qualquer PC da equipe, sem instalar nada.</p>'
    }},
    {{
      title: 'Motor NLQ — Dourado',
      html: '<p class="sdg-prose-body">O Dourado é um motor de <strong>linguagem natural 100% offline</strong>, sem GPT nem OpenAI. Funciona em 4 etapas:</p><div class="sdg-prose-highlight"><strong>1. Normaliza</strong> o texto (remove acentos, caixa)<br><strong>2. Extrai entidades</strong> (emissor por fuzzy match, setor, rating)<br><strong>3. Classifica a intenção</strong> por scoring de palavras-chave<br><strong>4. Consulta os dados</strong> e devolve resposta + gráfico</div><p class="sdg-prose-body" style="margin-top:8px;">São <strong>20 intents</strong> diferentes — de "qual o spread da Klabin?" até "quais empresas de energia estão aprovadas com duration acima de 4?". Zero custo por query, zero latência de rede.</p>'
    }},
  ];

  /* ── DADOS dos módulos (para o terminal) ── */
  const _SYS_MODS = [
    {{
      label:'Inicialização', color:'gold',
      logs:[
        {{t:'ok', tx:'[BOOT] overview_credito.py iniciado'}},
        {{t:'info', tx:'[BOOT] Python 3.11 · pandas 2.x · aiohttp 3.x'}},
        {{t:'dim', tx:'[INPUT] Modo de execução? (1=completo / 2=news)'}},
        {{t:'gold', tx:'[INPUT] → modo 1 selecionado'}},
        {{t:'ok', tx:'[BOOT] caminhos validados · usuário confirmado'}},
      ],
      prose:'<h4>Você escolhe o que o sistema faz</h4><p>O script pergunta: <strong style="color:#9a7e52">relatório completo</strong> (modo 1) ou só <strong style="color:#9a7e52">notícias rápidas</strong> (modo 2). No modo 2, encerra em segundos. No modo 1, dispara todos os módulos abaixo em sequência.</p>'
    }},
    {{
      label:'Extração Paralela', color:'teal',
      logs:[
        {{t:'section', tx:'── EXTRAÇÃO DE DADOS ──'}},
        {{t:'info', tx:'[THREAD] ThreadPoolExecutor · workers=12'}},
        {{t:'ok', tx:'[OK] Carteira CP · Comdinheiro API · 847 linhas'}},
        {{t:'ok', tx:'[OK] Bonds offshore · 36M preços'}},
        {{t:'ok', tx:'[OK] Rankings Excel · scorecard · rating'}},
        {{t:'ok', tx:'[OK] Watch list · bancos · status'}},
        {{t:'info', tx:'[ASYNC] asyncio + aiohttp'}},
        {{t:'ok', tx:'[OK] Tesouro CSV · NTN-B · LFT'}},
        {{t:'ok', tx:'[OK] Cadastro CVM · CNPJ · setor'}},
        {{t:'ok', tx:'[OK] ZIPs CVM · DRE·BPA·BPP·DFC 2011-2026'}},
        {{t:'gold', tx:'[DONE] 10 fontes · ~4.2s total (paralelo)'}},
      ],
      prose:'<h4>Ele busca tudo ao mesmo tempo, em paralelo</h4><p>Dispara <strong style="color:#0082a0">10+ conexões simultâneas</strong>: Comdinheiro, Excel local, Tesouro Nacional, CVM (demonstrativos de 2011 até hoje) — sem esperar uma de cada vez. ThreadPool cuida do IO-bound; asyncio cuida do network-bound.</p>'
    }},
    {{
      label:'Cálculos Financeiros', color:'blue',
      logs:[
        {{t:'section', tx:'── TRATAMENTO E CÁLCULOS ──'}},
        {{t:'info', tx:'[PROC] tratar() · D\\u0026A por nome da conta'}},
        {{t:'dim', tx:'[D\\u0026A] "DEPRECIA" no nome → prioridade sobre 3.06.01'}},
        {{t:'ok', tx:'[OK] Trimestralizado ITR+DFP · sem duplicatas'}},
        {{t:'ok', tx:'[OK] KPIs TTM/36M · EBITDA · DivLíq · FCF · ROE · ROIC'}},
        {{t:'ok', tx:'[SPREAD] ntnb_ref merge · .dt.normalize()'}},
        {{t:'ok', tx:'[SPREAD] z-score · MAD · mediana · MM21'}},
        {{t:'ok', tx:'[EXPORT] ativos.json · spreads_ts.json · fin_series.json'}},
      ],
      prose:'<h4>Todos os cálculos financeiros acontecem aqui</h4><p>Dados brutos da CVM viram indicadores: <strong style="color:#3174b8">EBITDA, Dívida Líquida, FCF, ROE, ROIC</strong>. Spreads são comparados com a NTN-B do dia, gerando z-scores para detectar distorções. D&A sempre pelo <em>nome da conta</em> — nunca pelo código contábil, que muda por empresa.</p>'
    }},
    {{
      label:'Indicadores BCB', color:'purple',
      logs:[
        {{t:'section', tx:'── BCB IF.data — BANCOS ──'}},
        {{t:'info', tx:'[BCB] olinda.bcb.gov.br/IFDATA · 27 bancos'}},
        {{t:'info', tx:'[BCB] Relatório 2 → Ativo (operações de crédito, PL)'}},
        {{t:'info', tx:'[BCB] Relatório 3 → Passivo (PL fallback)'}},
        {{t:'info', tx:'[BCB] Relatório 4 → DRE (lucro, eficiência, provisão)'}},
        {{t:'info', tx:'[BCB] Relatório 5 → Estrutura Capital (Basileia, alav., imob.)'}},
        {{t:'ok', tx:'[OK] 2021 · 2022 · 2023 · 2024 coletados'}},
        {{t:'ok', tx:'[OK] Match por similaridade → Watch List Bancos.xlsm'}},
        {{t:'ok', tx:'[INJECT] BCB_LIVE → window.BCB_LIVE · substitui fallback estático'}},
        {{t:'gold', tx:'[DONE] Dados reais p/ aba Bancos: Basileia · ROE · PDD · Eficiência'}},
      ],
      prose:'<h4>Dados bancários direto do Banco Central</h4><p>A API pública do BCB (<strong style="color:#6b5ca5">IF.data</strong>) retorna demonstrativos oficiais de 27 bancos do portfólio. Relatórios 2/3/4/5 cobrem Ativo, Passivo, DRE e Estrutura de Capital. Os nomes são mapeados por similaridade ao Watch List interno — dados reais sempre têm prioridade sobre os valores de referência estáticos.</p>'
    }},
    {{
      label:'News Pipeline', color:'gold',
      logs:[
        {{t:'section', tx:'── NEWS PIPELINE ──'}},
        {{t:'info', tx:'[RSS] _rss() × 4 feeds · ThreadPool'}},
        {{t:'ok', tx:'[RSS] Valor Econômico · 38 itens'}},
        {{t:'ok', tx:'[RSS] Exame · 22 itens'}},
        {{t:'ok', tx:'[RSS] InfoMoney · 29 itens'}},
        {{t:'ok', tx:'[RSS] Reuters BR · 18 itens'}},
        {{t:'info', tx:'[SCORE] _classif() · Macro / Empresas / Mercado'}},
        {{t:'info', tx:'[SCORE] fonte + recência + R$ + verbos evento'}},
        {{t:'ok', tx:'[DEDUP] Jaccard 65% · 31 duplicatas removidas'}},
        {{t:'gold', tx:'[DONE] 76 notícias únicas curadas'}},
      ],
      prose:'<h4>Notícias curadas automaticamente</h4><p>4 feeds RSS lidos em paralelo. Cada notícia ganha um <strong style="color:#9a7e52">score</strong>: peso da fonte, recência, presença de valores em R$, verbos de evento ("anuncia", "corta", "revisa") e se o emissor está na carteira. Duplicatas filtradas por similaridade de Jaccard ≥ 65%.</p>'
    }},
    {{
      label:'Geração HTML', color:'green',
      logs:[
        {{t:'section', tx:'── GERAÇÃO HTML FINAL ──'}},
        {{t:'info', tx:'[HTML] HTML_TEMPLATE · 4.800 linhas'}},
        {{t:'ok', tx:'[INJECT] ATIVOS_JSON → window.ATIVOS'}},
        {{t:'ok', tx:'[INJECT] SPREADS_TS → window.SPREADS_TS'}},
        {{t:'ok', tx:'[INJECT] FIN_SERIES → window.FIN_SERIES'}},
        {{t:'ok', tx:'[INJECT] NEWS_JSON → window.NEWS'}},
        {{t:'ok', tx:'[BUILD] SPA 10 views · logo base64 embutida'}},
        {{t:'ok', tx:'[SAVE] overview_credito_2026-05-22.html'}},
        {{t:'gold', tx:'[OPEN] webbrowser.open() → Chrome'}},
      ],
      prose:'<h4>Um único arquivo HTML — sem servidor</h4><p>Logo em base64, todos os dados embutidos como variáveis JS, gráficos Plotly/Chart.js, SPA com 10 telas — tudo num HTML <strong style="color:#2fa874">standalone</strong>. Qualquer PC da equipe abre com duplo clique, sem instalar nada, sem rede.</p>'
    }},
    {{
      label:'Motor NLQ', color:'gold',
      logs:[
        {{t:'section', tx:'── MOTOR NLQ — DOURADO ──'}},
        {{t:'gold', tx:'[NLQ] 0 APIs externas · 100% offline'}},
        {{t:'info', tx:'[NLQ] _norm() · NFD · remove acentos'}},
        {{t:'info', tx:'[NLQ] _detectEmissor() · fuzzy match 847 ativos'}},
        {{t:'info', tx:'[NLQ] _matchIntent() · KW scoring + sim. cosseno'}},
        {{t:'ok', tx:'[NLQ] 20 intents registrados'}},
        {{t:'dim', tx:'[NLQ] intents: exposicao_emissor exposicao_setor'}},
        {{t:'dim', tx:'[NLQ]   query_param multi_filtro fund_delta'}},
        {{t:'dim', tx:'[NLQ]   spread_delta sintese_emissor grafico_spread'}},
        {{t:'dim', tx:'[NLQ]   mapa_risco risco_estresse + 11 mais'}},
        {{t:'gold', tx:'[READY] Dourado pronto para perguntas em PT-BR'}},
      ],
      prose:'<h4>Dourado entende português — zero API externa</h4><p>Motor NLQ 100% offline: normaliza texto (NFD, acentos, caixa), extrai entidades (emissor por fuzzy match, setor, rating), classifica intenção por scoring de keywords + similaridade, consulta os dados da carteira em tempo real. Sem GPT, sem OpenAI, sem custo por query.</p>'
    }},
  ];
  let _sysCurrentMod = 0;
  let _sysView = 'diagram';
  let _termTyping = null;

  function sysView(v) {{
    _sysView = v;
    const dg=document.getElementById('sysViewDiagram');
    const tm=document.getElementById('sysViewTerminal');
    const sk=document.getElementById('sysViewShortcuts');
    const bD=document.getElementById('sysToggleDiagram');
    const bT=document.getElementById('sysToggleTerminal');
    const bS=document.getElementById('sysToggleShortcuts');
    // reset all
    [bD,bT,bS].forEach(b=>{{ b.style.background='transparent'; b.style.color='#9a8a76'; b.style.boxShadow='none'; }});
    dg.style.display='none'; tm.style.display='none'; sk.style.display='none';
    if(v==='diagram') {{
      dg.style.display='flex';
      bD.style.background='linear-gradient(135deg,#b69d74,#d4b47a)'; bD.style.color='#fff'; bD.style.boxShadow='0 2px 8px rgba(182,157,116,.4)';
    }} else if(v==='terminal') {{
      tm.style.display='flex';
      bT.style.background='#0d1117'; bT.style.color='#e6edf3'; bT.style.boxShadow='0 2px 8px rgba(0,0,0,.4)';
      sysRenderTerminalAll();
    }} else {{
      sk.style.display='block';
      bS.style.background='linear-gradient(135deg,#3174b8,#5b9bd5)'; bS.style.color='#fff'; bS.style.boxShadow='0 2px 8px rgba(49,116,184,.35)';
    }}
  }}

  function sysSelectMod(idx) {{
    _sysCurrentMod = idx;
    // highlight cards do diagrama
    document.querySelectorAll('.sdg-card,.sdg-card--half').forEach(el => {{
      const modVal = el.closest('[data-mod]') ? parseInt(el.closest('[data-mod]').dataset.mod) : parseInt(el.dataset&&el.dataset.mod);
      el.classList.toggle('sdg-card-active', modVal===idx);
    }});
    document.querySelectorAll('[data-mod]').forEach(el => {{
      el.querySelectorAll('.sdg-card').forEach(c => {{
        c.classList.toggle('sdg-card-active', parseInt(el.dataset.mod)===idx);
      }});
    }});
    // painel didático direito
    const prose = _SYS_PROSE[idx];
    if(prose) {{
      document.getElementById('sdgPanelTitle').innerHTML = prose.title;
      const body = document.getElementById('sdgPanelBody');
      body.style.animation='none';
      body.innerHTML = prose.html;
      body.style.animation='sdgCardIn .22s ease';
    }}
    // terminal (se ativo, rola até a seção)
    if(_sysView==='terminal') {{
      const sec = document.getElementById('termSec'+idx);
      if(sec) sec.scrollIntoView({{behavior:'smooth',block:'start'}});
    }}
  }}

  /* Terminal: tipa TODOS os módulos em sequência ao abrir */
  function sysRenderTerminalAll() {{
    if(_termTyping) {{ clearInterval(_termTyping); _termTyping=null; }}
    const logEl = document.getElementById('sysTermLog');
    const proseEl = document.getElementById('sysTermProse');
    logEl.innerHTML = '';
    proseEl.innerHTML = '';
    // achata todas as linhas de todos os módulos com marcadores de seção
    const allLines = [];
    _SYS_MODS.forEach(function(mod, mi) {{
      // separador de seção com ancora
      allLines.push({{t:'_anchor', id:'termSec'+mi}});
      mod.logs.forEach(function(ln) {{ allLines.push(ln); }});
    }});
    // popula prose de todos os módulos de uma vez (scroll serve como contexto)
    _SYS_MODS.forEach(function(mod, mi) {{
      const prose = _SYS_PROSE[mi];
      if(!prose) return;
      const div = document.createElement('div');
      div.className = 'tprose-card';
      div.id = 'termProse'+mi;
      div.style.cssText = 'border-color:rgba(182,157,116,.18);background:#faf7f2;margin-bottom:14px;';
      div.innerHTML = '<h4>'+prose.title+'</h4>'+prose.html.replace(/<p class="sdg-prose-body"[^>]*>/g,'<p>').replace(/<div class="sdg-prose-highlight">/g,'<p style="font-style:italic;font-size:9.5px;color:#5a4a38;background:rgba(182,157,116,.08);border-left:2px solid #b69d74;padding:7px 10px;margin:8px 0;border-radius:0 5px 5px 0;">').replace(/<\/div>/g,'</p>');
      proseEl.appendChild(div);
    }});
    // tipa as linhas de log
    let i=0;
    _termTyping = setInterval(function() {{
      if(i>=allLines.length) {{ clearInterval(_termTyping); _termTyping=null; return; }}
      const ln = allLines[i++];
      if(ln.t==='_anchor') {{
        const anc = document.createElement('div');
        anc.id = ln.id;
        logEl.appendChild(anc);
      }} else {{
        const div = document.createElement('div');
        div.className = 'tlog-'+ln.t;
        div.style.margin='0';
        div.textContent = ln.tx;
        logEl.appendChild(div);
        logEl.scrollTop = logEl.scrollHeight;
      }}
    }}, 55);
  }}

  function openSysInfo() {{
    document.getElementById('sysInfoModal').style.display='flex';
    sysView('diagram');
    sysSelectMod(0);
  }}
  function closeSysInfo() {{
    document.getElementById('sysInfoModal').style.display='none';
    if(_termTyping) {{ clearInterval(_termTyping); _termTyping=null; }}
  }}
  document.getElementById('sysInfoModal').addEventListener('click', e => {{ if(e.target.id==='sysInfoModal') closeSysInfo(); }});
  document.addEventListener('keydown', e => {{ if(e.key==='Escape'&&document.getElementById('sysInfoModal').style.display!=='none') closeSysInfo(); }});
  </script>

  <div class="content">
    <!-- ── PAGE: HOME ── -->
    <div class="page fade-in" id="page-home">
      <div class="section-header">
        <h2>Panorama</h2>
        <div class="accent-line"></div>
        <span id="homeDataRef" style="font-size:11px;color:var(--text3);font-family:var(--mono);white-space:nowrap;"></span>
      </div>
      <div class="home-kpi-row" id="homeKpiRow"></div>
      <div class="home-grid-main">
        <div class="card">
          <div class="card-title">Saldo Bruto por Emissor</div>
          <div class="chart-scroll-wrap">
            <div class="chart-scroll-inner" id="homeChartEmissorWrap">
              <div style="height:300px;position:relative;"><canvas id="homeChartEmissor"></canvas></div>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-title">Por Classe de Ativo</div>
          <div style="height:300px;position:relative;"><canvas id="homeChartClasse"></canvas></div>
        </div>
      </div>
      <div class="home-grid-bottom">
        <div class="card">
          <div class="card-title">Top 5 Corporativos — <span onclick="homeDiveScorecard('corp')" style="font-size:10px;color:var(--teal);text-transform:none;font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:2px;">Clique para Deep Dive →</span></div>
          <div id="homeTop5Corp" style="display:flex;flex-direction:column;gap:4px;margin-top:4px;"></div>
        </div>
        <div class="card">
          <div class="card-title">Top 5 Bancos — <span onclick="homeDiveScorecard('banco')" style="font-size:10px;color:var(--teal);text-transform:none;font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:2px;">Clique para Deep Dive →</span></div>
          <div id="homeTop5Bancos" style="display:flex;flex-direction:column;gap:4px;margin-top:4px;"></div>
        </div>
      </div>
      <div class="home-grid-banks">
        <div class="card">
          <div class="card-title">Retorno Acumulado <span style="font-size:10px;color:var(--text3);text-transform:none;font-weight:400;">por carteira</span></div>
          <div style="height:280px;position:relative;"><canvas id="homeChartPerf"></canvas></div>
        </div>
      </div>
    </div>
    <!-- ── FIM PAGE: HOME ── -->
    <div class="page fade-in" id="page-composicao">
      <div class="section-header"><h2>Composição da Carteira</h2><div class="accent-line"></div></div>
      <div class="kpi-row" id="kpiRow"></div>
      <div class="grid-2-1">
        <div class="card">
          <div class="card-title">Saldo Bruto % da Carteira Total por Emissor</div>
          <div class="chart-scroll-wrap">
            <div class="chart-scroll-inner" id="chartEmissorWrap">
              <div style="height:320px;position:relative;">
                <canvas id="chartEmissor" style="cursor:pointer"></canvas>
              </div>
            </div>
          </div>
          <div id="emissorVerTodosChip" style="display:none;margin-top:8px;font-size:11px;color:var(--teal);text-align:right;cursor:pointer;font-weight:600;letter-spacing:.01em;" onclick="document.getElementById('tbodyAtivos').closest('.card').scrollIntoView({{behavior:'smooth'}})"></div>
        </div>
        <div class="card"><div class="card-title">% por Setor</div><div class="h320"><canvas id="chartSetor"></canvas></div></div>
      </div>
      <div class="card">
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px">
          <div class="card-title" style="margin-bottom:0;flex:1;min-width:0">Detalhamento por Ativo <span id="countAtivos" style="color:var(--text3);font-size:11px;text-transform:none"></span><span id="emFiltroTag"></span></div>
          <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
            <div style="position:relative">
              <svg style="position:absolute;left:8px;top:8px;width:12px;height:12px;stroke:var(--text3);fill:none;pointer-events:none" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" id="ativosSearch" oninput="_renderTbodyAtivos()" placeholder="Pesquisar" style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:6px 10px 6px 26px;color:var(--text);font-family:var(--font);font-size:11px;outline:none;width:160px;transition:border-color .2s" onfocus="this.style.borderColor='var(--teal)'" onblur="this.style.borderColor='var(--border)'">
            </div>
            <button onclick="_ativosSortReset()" title="Resetar ordenacao" style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:5px 10px;cursor:pointer;font-size:10px;font-weight:600;color:var(--text3);transition:all .15s" onmouseover="this.style.borderColor='var(--teal)';this.style.color='var(--teal)'" onmouseout="this.style.borderColor='var(--border)';this.style.color='var(--text3)'">Limpar</button>
          </div>
        </div>
        <div class="table-wrap"><table><thead><tr>
          <th onclick="_ativosSort('carteira')" style="cursor:pointer;user-select:none;white-space:nowrap">Carteira <span id="_sh_carteira" style="opacity:.4">&#8597;</span></th>
          <th onclick="_ativosSort('ticker')" style="cursor:pointer;user-select:none;white-space:nowrap">Ticker <span id="_sh_ticker" style="opacity:.4">&#8597;</span></th>
          <th onclick="_ativosSort('emissor')" style="cursor:pointer;user-select:none;white-space:nowrap">Emissor <span id="_sh_emissor" style="opacity:.4">&#8597;</span></th>
          <th onclick="_ativosSort('setor')" style="cursor:pointer;user-select:none;white-space:nowrap">Setor <span id="_sh_setor" style="opacity:.4">&#8597;</span></th>
          <th onclick="_ativosSort('saldo')" style="cursor:pointer;user-select:none;white-space:nowrap">Saldo Bruto <span id="_sh_saldo" style="color:var(--teal);opacity:1">&#8595;</span></th>
          <th onclick="_ativosSort('pctCred')" style="cursor:pointer;user-select:none;white-space:nowrap">% Credito <span id="_sh_pctCred" style="opacity:.4">&#8597;</span></th>
          <th onclick="_ativosSort('pctPL')" style="cursor:pointer;user-select:none;white-space:nowrap">% PL Total <span id="_sh_pctPL" style="opacity:.4">&#8597;</span></th>
          <th onclick="_ativosSort('duration')" style="cursor:pointer;user-select:none;white-space:nowrap">Duration <span id="_sh_duration" style="opacity:.4">&#8597;</span></th>
          <th onclick="_ativosSort('classe')" style="cursor:pointer;user-select:none;white-space:nowrap">Classe <span id="_sh_classe" style="opacity:.4">&#8597;</span></th>
          <th>Rating Mkt</th>
          <th>Rating Douro</th>
          <th onclick="_ativosSort('status')" style="cursor:pointer;user-select:none;white-space:nowrap">Status <span id="_sh_status" style="opacity:.4">&#8597;</span></th>
        </tr></thead><tbody id="tbodyAtivos"></tbody></table></div>
      </div>
    </div>
    <div class="page fade-in" id="page-rating">
      <div class="section-header"><h2>Classe e Rating</h2><div class="accent-line"></div></div>
      <div class="grid-3">
        <div class="card"><div class="card-title">% por Classe de Ativo</div><div class="h260"><canvas id="chartClasse"></canvas></div></div>
        <div class="card"><div class="card-title">% Rating de Mercado</div><div class="h260"><canvas id="chartRatingMkt"></canvas></div></div>
        <div class="card"><div class="card-title">% Rating Proprietário (Douro)</div><div class="h260"><canvas id="chartRatingDouro"></canvas></div></div>
      </div>
      <div class="card">
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px">
          <div class="card-title" style="margin-bottom:0;flex:1;min-width:0">Detalhamento por Ativo <span id="countAtivosRating" style="color:var(--text3);font-size:11px;text-transform:none"></span><span id="emFiltroTagRating"></span></div>
          <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
            <div style="position:relative">
              <svg style="position:absolute;left:8px;top:8px;width:12px;height:12px;stroke:var(--text3);fill:none;pointer-events:none" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" id="ativosSearchRating" oninput="_renderTbodyAtivosRating()" placeholder="Pesquisar" style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:6px 10px 6px 26px;color:var(--text);font-family:var(--font);font-size:11px;outline:none;width:160px;transition:border-color .2s" onfocus="this.style.borderColor='var(--teal)'" onblur="this.style.borderColor='var(--border)'">
            </div>
            <button onclick="_ativosSortReset()" title="Resetar ordenacao" style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:5px 10px;cursor:pointer;font-size:10px;font-weight:600;color:var(--text3);transition:all .15s" onmouseover="this.style.borderColor='var(--teal)';this.style.color='var(--teal)'" onmouseout="this.style.borderColor='var(--border)';this.style.color='var(--text3)'">Limpar</button>
          </div>
        </div>
        <div class="table-wrap"><table><thead><tr>
          <th onclick="_ativosSort('carteira')" style="cursor:pointer;user-select:none;white-space:nowrap">Carteira <span id="_sh_carteira_rating" style="opacity:.4">↕</span></th>
          <th onclick="_ativosSort('ticker')" style="cursor:pointer;user-select:none;white-space:nowrap">Ticker <span id="_sh_ticker_rating" style="opacity:.4">↕</span></th>
          <th onclick="_ativosSort('emissor')" style="cursor:pointer;user-select:none;white-space:nowrap">Emissor <span id="_sh_emissor_rating" style="opacity:.4">↕</span></th>
          <th onclick="_ativosSort('setor')" style="cursor:pointer;user-select:none;white-space:nowrap">Setor <span id="_sh_setor_rating" style="opacity:.4">↕</span></th>
          <th onclick="_ativosSort('saldo')" style="cursor:pointer;user-select:none;white-space:nowrap">Saldo Bruto <span id="_sh_saldo_rating" style="color:var(--teal);opacity:1">↓</span></th>
          <th onclick="_ativosSort('pctCred')" style="cursor:pointer;user-select:none;white-space:nowrap">% Credito <span id="_sh_pctCred_rating" style="opacity:.4">↕</span></th>
          <th onclick="_ativosSort('pctPL')" style="cursor:pointer;user-select:none;white-space:nowrap">% PL Total <span id="_sh_pctPL_rating" style="opacity:.4">↕</span></th>
          <th onclick="_ativosSort('duration')" style="cursor:pointer;user-select:none;white-space:nowrap">Duration <span id="_sh_duration_rating" style="opacity:.4">↕</span></th>
          <th onclick="_ativosSort('classe')" style="cursor:pointer;user-select:none;white-space:nowrap">Classe <span id="_sh_classe_rating" style="opacity:.4">↕</span></th>
          <th>Rating Mkt</th>
          <th>Rating Douro</th>
          <th onclick="_ativosSort('status')" style="cursor:pointer;user-select:none;white-space:nowrap">Status <span id="_sh_status_rating" style="opacity:.4">↕</span></th>
        </tr></thead><tbody id="tbodyAtivosRating"></tbody></table></div>
      </div>
    </div>
    <!-- PAGE: FINANCEIROS -->
    <div class="page fade-in" id="page-financeiros">
      <div class="section-header"><h2>Dados</h2><div class="accent-line"></div></div>
      <div class="card" style="margin-bottom:16px;padding:16px 20px">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;align-items:start">
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Indicador</div>
            <select class="custom-select" id="indFinSel" onchange="buildFinanceiros()" style="width:100%">
              <option value="DivLiquida/EBITDA">Dívida Líq / EBITDA</option>
              <option value="Mg EBITDA 36M">Mg. EBITDA (%)</option>
              <option value="Mg Bruta 36M">Mg. Bruta (%)</option>
              <option value="Estrutura de Capital (D/D+E)">Estrutura de Capital</option>
              <option value="ROE">ROE</option>
              <option value="ROA">ROA</option>
              <option value="ROIC">ROIC</option>
              <option value="Liquidez Corrente">Liquidez Corrente</option>
              <option value="Receita_TTM">Receita TTM</option>
              <option value="EBITDA_TTM">EBITDA TTM</option>
              <option value="FCF_TTM">FCF TTM</option>
            </select>
          </div>
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Setor (CVM)</div>
            <select class="custom-select" id="setorFinSel" onchange="finOnSetorChange()" style="width:100%">
              <option value="">Todos os Setores</option>
            </select>
          </div>
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Empresas selecionadas</div>
            <div id="finChipsWrap" style="display:flex;flex-wrap:wrap;gap:6px;min-height:34px;align-items:center">
              <span style="color:var(--text3);font-size:11px">Nenhuma selecionada — use os filtros</span>
            </div>
          </div>
        </div>
        <div style="margin-top:12px">
          <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">
            Empresas disponíveis <span id="finEmpCount" style="color:var(--teal)"></span>
            <button onclick="finAddAll()" style="margin-left:12px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.3);color:var(--teal);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">+ Adicionar todas</button>
            <button onclick="finRemoveAll()" style="margin-left:6px;background:rgba(217,65,65,.1);border:1px solid rgba(217,65,65,.3);color:var(--red);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">× Limpar</button>
          </div>
          <div id="finEmpList" style="display:flex;flex-wrap:wrap;gap:6px;max-height:100px;overflow-y:auto"></div>
        </div>
        <div style="margin-top:16px">
          <div class="glass-range-wrap">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
              <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.10em">Período</div>
              <span id="finDateRangeLabel" class="glass-range-label"></span>
            </div>
            <div style="position:relative;height:32px;padding:0 8px">
              <div id="finRangeTrack" style="position:absolute;top:14px;left:8px;right:8px;height:5px;background:rgba(0,103,123,0.10);border-radius:999px">
                <div id="finRangeFill" style="position:absolute;height:100%;background:linear-gradient(90deg,rgba(0,103,123,.45),var(--teal));border-radius:999px;left:0%;width:100%;transition:left .04s,width .04s"></div>
              </div>
              <input type="range" id="finRangeMin" min="0" max="100" value="0" class="fin-range-inp" oninput="finRangeUpdate(event)">
              <input type="range" id="finRangeMax" min="0" max="100" value="100" class="fin-range-inp" oninput="finRangeUpdate(event)">
            </div>
          </div>
        </div>
      </div>
      <div class="card"><div class="card-title" id="finTitle">Indicador</div><div class="h320"><canvas id="chartFinMain"></canvas></div></div>
      <div class="card">
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px">
          <div class="card-title" style="margin-bottom:0;flex:1;min-width:0">Painel de Indicadores — Último Período</div>
          <div style="position:relative;flex-shrink:0">
            <svg style="position:absolute;left:8px;top:8px;width:12px;height:12px;stroke:var(--text3);fill:none;pointer-events:none" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input type="text" id="finPainelSearch" oninput="_finPainelRender()" placeholder="Pesquisar" style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:6px 10px 6px 26px;color:var(--text);font-family:var(--font);font-size:11px;outline:none;width:160px;transition:border-color .2s" onfocus="this.style.borderColor='var(--teal)'" onblur="this.style.borderColor='var(--border)'">
          </div>
        </div>
        <div class="table-wrap"><table><thead><tr>
          <th onclick="_finPainelSort('empresa')" style="cursor:pointer;user-select:none">Empresa <span id="_fpsh_empresa" style="color:var(--teal);opacity:1">&#8595;</span></th>
          <th onclick="_finPainelSort('setor')" style="cursor:pointer;user-select:none">Setor (CVM) <span id="_fpsh_setor" style="opacity:.4">&#8597;</span></th>
          <th onclick="_finPainelSort('rec')" style="cursor:pointer;user-select:none">Receita TTM <span id="_fpsh_rec" style="opacity:.4">&#8597;</span></th>
          <th onclick="_finPainelSort('ebt')" style="cursor:pointer;user-select:none">EBITDA TTM <span id="_fpsh_ebt" style="opacity:.4">&#8597;</span></th>
          <th onclick="_finPainelSort('mg')" style="cursor:pointer;user-select:none">Mg EBITDA <span id="_fpsh_mg" style="opacity:.4">&#8597;</span></th>
          <th onclick="_finPainelSort('dl')" style="cursor:pointer;user-select:none">Div Liq/EBITDA <span id="_fpsh_dl" style="opacity:.4">&#8597;</span></th>
          <th onclick="_finPainelSort('ec')" style="cursor:pointer;user-select:none">Estrutura Cap. <span id="_fpsh_ec" style="opacity:.4">&#8597;</span></th>
          <th onclick="_finPainelSort('roe')" style="cursor:pointer;user-select:none">ROE <span id="_fpsh_roe" style="opacity:.4">&#8597;</span></th>
          <th onclick="_finPainelSort('lc')" style="cursor:pointer;user-select:none">Liq. Corrente <span id="_fpsh_lc" style="opacity:.4">&#8597;</span></th>
        </tr></thead><tbody id="tbodyFin"></tbody></table></div>
      </div>
    </div>
    <!-- PAGE: FUNDAMENTOS -->
    <div class="page fade-in" id="page-fundamentos">
      <div class="section-header"><h2>Empresas</h2><div class="accent-line"></div></div>
      <!-- Seletor de empresa -->
      <div class="card" style="margin-bottom:16px;padding:16px 22px">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;align-items:end">
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Empresa</div>
            <div style="position:relative">
              <svg style="position:absolute;left:10px;top:9px;width:14px;height:14px;stroke:var(--text3);fill:none" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" id="fundSearch" oninput="fundFilterList()" placeholder="Buscar empresa..." style="width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 12px 8px 32px;color:var(--text);font-family:var(--font);font-size:12px;outline:none;transition:border-color .2s">
            </div>
            <select id="fundEmpSel" class="custom-select" onchange="buildFundamentos()" style="width:100%;margin-top:8px"></select>
          </div>
          <div id="fundInfoA" style="display:flex;flex-direction:column;gap:4px">
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:4px">Setor / Último Balanço</div>
            <div id="fundInfoSetor" style="font-size:13px;font-weight:600;color:var(--navy)">—</div>
            <div id="fundInfoData"  style="font-size:11px;color:var(--text3)">—</div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div><div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:4px">Receita TTM</div><div id="fundKpiRec" style="font-family:var(--mono);font-size:15px;font-weight:700;color:var(--navy)">—</div></div>
            <div><div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:4px">EBITDA TTM</div><div id="fundKpiEbt" style="font-family:var(--mono);font-size:15px;font-weight:700;color:var(--teal)">—</div></div>
            <div><div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:4px">Dív. Líq/EBITDA</div><div id="fundKpiDl" style="font-family:var(--mono);font-size:15px;font-weight:700;color:var(--navy)">—</div></div>
            <div style="display:flex;flex-direction:column;gap:4px;position:relative"><div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:4px">Liq. Corrente</div><div style="display:flex;align-items:center;gap:8px"><div id="fundKpiLc" style="font-family:var(--mono);font-size:15px;font-weight:700;color:var(--navy)">—</div><button onclick="exportarPDFFundamentos()" title="Exportar dados da empresa como PDF" style="background:rgba(182,157,116,.15);border:1px solid rgba(182,157,116,.3);color:var(--text3);padding:5px 8px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600;transition:all .15s;display:flex;align-items:center;gap:4px"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>PDF</button></div></div>
          </div>
        </div>
        <div style="margin-top:16px">
          <div class="glass-range-wrap">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
              <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.10em">Período</div>
              <span id="fundDateRangeLabel" class="glass-range-label"></span>
            </div>
            <div style="position:relative;height:32px;padding:0 8px">
              <div id="fundRangeTrack" style="position:absolute;top:14px;left:8px;right:8px;height:5px;background:rgba(0,103,123,0.10);border-radius:999px">
                <div id="fundRangeFill" style="position:absolute;height:100%;background:linear-gradient(90deg,rgba(0,103,123,.45),var(--teal));border-radius:999px;left:0%;width:100%;transition:left .04s,width .04s"></div>
              </div>
              <input type="range" id="fundRangeMin" min="0" max="100" value="0" class="fin-range-inp" oninput="fundRangeUpdate(event)">
              <input type="range" id="fundRangeMax" min="0" max="100" value="100" class="fin-range-inp" oninput="fundRangeUpdate(event)">
            </div>
          </div>
        </div>
      </div>
      <!-- Gráficos -->
      <div class="grid-2">
        <div class="card"><div class="card-title">Resultado — Receita / EBITDA / Lucro Líquido (LTM)</div><div class="h320"><canvas id="fundChartPL"></canvas></div></div>
        <div class="card"><div class="card-title">Margens LTM — Bruta / EBITDA / Líquida</div><div class="h320"><canvas id="fundChartMg"></canvas></div></div>
      </div>
      <div class="grid-2">
        <div class="card"><div class="card-title">Alavancagem — Dív. Líquida/EBITDA · Dív. Bruta/EBITDA</div><div class="h320"><canvas id="fundChartLev"></canvas></div></div>
        <div class="card"><div class="card-title">Liquidez — Corrente / Seca / Imediata</div><div class="h320"><canvas id="fundChartLiq"></canvas></div></div>
      </div>
      <div class="card"><div class="card-title">Fluxo de Caixa por Trimestre — FCO / FCI / FCF</div><div class="h320"><canvas id="fundChartCF"></canvas></div></div>
    </div>
    <!-- PAGE: BANCOS -->
    <div class="page fade-in" id="page-bancos">
      <div class="section-header"><h2>Bancos</h2><div class="accent-line"></div></div>
      <div class="card" style="margin-bottom:16px;padding:16px 22px">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:end">
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Banco</div>
            <select id="bancosEmpSel" class="custom-select" onchange="buildBancos()" style="width:100%"></select>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
            <div><div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:4px">Basileia</div><div id="bancoKpiBasileia" style="font-family:var(--mono);font-size:15px;font-weight:700;color:var(--navy)">—</div></div>
            <div><div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:4px">ROE</div><div id="bancoKpiROE" style="font-family:var(--mono);font-size:15px;font-weight:700;color:var(--teal)">—</div></div>
            <div style="display:flex;flex-direction:column;gap:4px"><div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:4px">Inadimplência</div><div style="display:flex;align-items:center;gap:8px"><div id="bancoKpiNPL" style="font-family:var(--mono);font-size:15px;font-weight:700;color:var(--navy)">—</div><button onclick="exportarPDFBancos()" title="Exportar dados do banco como PDF" style="background:rgba(182,157,116,.15);border:1px solid rgba(182,157,116,.3);color:var(--text3);padding:5px 8px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600;transition:all .15s;display:flex;align-items:center;gap:4px"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>PDF</button></div></div>
          </div>
        </div>
      </div>
      <div class="grid-2">
        <div class="card"><div class="card-title">Solvência — Índice de Basileia · Tier 1 Capital</div><div class="h320"><canvas id="bancoChartBasileia"></canvas></div></div>
        <div class="card"><div class="card-title">Rentabilidade — ROE · NIM</div><div class="h320"><canvas id="bancoChartRent"></canvas></div></div>
      </div>
      <div class="grid-2">
        <div class="card"><div class="card-title">Qualidade de Crédito — Cobertura PDD · Desp. Provisão/Carteira</div><div class="h320"><canvas id="bancoChartCredit"></canvas></div></div>
        <div class="card"><div class="card-title">Eficiência Operacional</div><div class="h320"><canvas id="bancoChartEfic"></canvas></div></div>
      </div>
    </div>
    <!-- PAGE: SPREADS -->
    <div class="page fade-in" id="page-spreads">
      <div class="section-header"><h2>Spreads vs NTN-B</h2><div class="accent-line"></div></div>
      <div class="card" style="margin-bottom:16px;padding:16px 20px">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;align-items:start;margin-bottom:14px">
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Classe</div>
            <select class="custom-select" id="spClasseSel" onchange="spOnClasseChange()" style="width:100%"><option value="">Todas as Classes</option></select>
          </div>
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Setor</div>
            <select class="custom-select" id="spSetorSel" onchange="spOnSetorChange()" style="width:100%"><option value="">Todos os Setores</option></select>
          </div>
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Emissor</div>
            <select class="custom-select" id="spEmsSel" onchange="spOnEmsChange()" style="width:100%"><option value="">Todos os Emissores</option></select>
          </div>
        </div>
        <div style="margin-bottom:10px">
          <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:6px">Ativos selecionados</div>
          <div id="spChipsWrap" style="display:flex;flex-wrap:wrap;gap:6px;min-height:28px;align-items:center"><span style="color:var(--text3);font-size:11px">Nenhum selecionado — use os filtros acima</span></div>
        </div>
        <div style="margin-top:4px">
          <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">
            Ativos disponíveis <span id="spAtivoCount" style="color:var(--teal)"></span>
            <button type="button" onclick="spAddAll()" style="margin-left:12px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.3);color:var(--teal);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">+ Adicionar todos</button>
            <button type="button" onclick="spRemoveAll()" style="margin-left:6px;background:rgba(217,65,65,.1);border:1px solid rgba(217,65,65,.3);color:var(--red);padding:3px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">× Limpar</button>
          </div>
          <div id="spAtivoList" style="display:flex;flex-wrap:wrap;gap:6px;max-height:100px;overflow-y:auto"></div>
        </div>
      </div>
      <div class="card"><div class="card-title">Evolução das Taxas (%)</div><div class="h320"><canvas id="chartSpTaxa"></canvas></div></div>
      <div class="card"><div class="card-title">Evolução dos Spreads vs NTN-B (%)</div><div class="h320"><canvas id="chartSpSpread"></canvas></div></div>
      <div class="card"><div class="card-title">Dispersão — Duration × Spread</div><div class="h320"><canvas id="chartSpScatter"></canvas></div></div>
      <div class="card">
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px">
          <div class="card-title" style="margin-bottom:0;flex:1;min-width:0">Posição Atual — Ativos com Spread</div>
          <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
            <div style="position:relative">
              <svg style="position:absolute;left:8px;top:8px;width:12px;height:12px;stroke:var(--text3);fill:none;pointer-events:none" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" id="spreadsSearch" oninput="_renderTbodySpreads()" placeholder="Pesquisar" style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:6px 10px 6px 26px;color:var(--text);font-family:var(--font);font-size:11px;outline:none;width:160px;transition:border-color .2s" onfocus="this.style.borderColor='var(--teal)'" onblur="this.style.borderColor='var(--border)'">
            </div>
            <label style="display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text3);cursor:pointer;white-space:nowrap">
              <input type="checkbox" id="spSoSelecionados" onchange="_renderTbodySpreads()" style="cursor:pointer"> Só selecionados
            </label>
          </div>
        </div>
        <div class="table-wrap"><table><thead><tr>
          <th onclick="_spSort('ticker')" style="cursor:pointer;user-select:none;white-space:nowrap">Ativo <span id="_spsh_ticker" style="opacity:.4">&#8597;</span></th>
          <th onclick="_spSort('emissor')" style="cursor:pointer;user-select:none;white-space:nowrap">Emissor <span id="_spsh_emissor" style="opacity:.4">&#8597;</span></th>
          <th onclick="_spSort('setor')" style="cursor:pointer;user-select:none;white-space:nowrap">Setor <span id="_spsh_setor" style="opacity:.4">&#8597;</span></th>
          <th onclick="_spSort('taxa')" style="cursor:pointer;user-select:none;white-space:nowrap">Taxa (%) <span id="_spsh_taxa" style="opacity:.4">&#8597;</span></th>
          <th onclick="_spSort('spread')" style="cursor:pointer;user-select:none;white-space:nowrap">Spread (%) <span id="_spsh_spread" style="color:var(--teal);opacity:1">&#8595;</span></th>
          <th onclick="_spSort('mediana')" style="cursor:pointer;user-select:none;white-space:nowrap">Mediana <span id="_spsh_mediana" style="opacity:.4">&#8597;</span></th>
          <th>+1 MAD</th><th>−1 MAD</th>
          <th onclick="_spSort('ntnb')" style="cursor:pointer;user-select:none;white-space:nowrap">NTN-B Ref <span id="_spsh_ntnb" style="opacity:.4">&#8597;</span></th>
          <th onclick="_spSort('duration')" style="cursor:pointer;user-select:none;white-space:nowrap">Duration <span id="_spsh_duration" style="opacity:.4">&#8597;</span></th>
          <th onclick="_spSort('status')" style="cursor:pointer;user-select:none;white-space:nowrap">Status <span id="_spsh_status" style="opacity:.4">&#8597;</span></th>
        </tr></thead><tbody id="tbodySpreads"></tbody></table></div>
      </div>
    </div>
    <!-- PAGE: TÚNEL DE PREÇO -->
    <div class="page fade-in" id="page-tunel">
      <div class="section-header"><h2>Túnel de Preço</h2><div class="accent-line"></div></div>
      <div class="card" style="margin-bottom:16px;padding:16px 20px">
        <div style="display:grid;grid-template-columns:1fr;gap:16px;">
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Ativo</div>
            <select id="ativoTunelSel" class="custom-select" onchange="buildTunel()" style="width:100%"></select>
          </div>
        </div>
      </div>
      <div class="grid-2">
        <div class="card"><div class="card-title">Taxa (%) — Mediana ± 1 MAD + MM21</div><div class="h320"><canvas id="chartTunelTaxa"></canvas></div></div>
        <div class="card"><div class="card-title">Distribuição Histórica — Taxa (%)</div><div class="h320"><canvas id="chartHistTunelTaxa"></canvas></div></div>
      </div>
      <div class="grid-2">
        <div class="card"><div class="card-title">Spread (%) — Mediana ± 1 MAD + MM21</div><div class="h320"><canvas id="chartTunelSpread"></canvas></div></div>
        <div class="card"><div class="card-title">Distribuição Histórica — Spread (%)</div><div class="h320"><canvas id="chartHistTunelSpread"></canvas></div></div>
      </div>
      <div class="card">
        <div class="card-title">Estatísticas do Ativo Selecionado</div>
        <div class="table-wrap"><table><thead><tr><th>Ticker</th><th>Emissor</th><th>Setor</th><th>Duration</th><th>Taxa Atual (%)</th><th>Spread Atual (%)</th><th>Mediana Spread</th><th>+1 MAD</th><th>−1 MAD</th><th>Z-Score</th><th>Vol Spread</th><th>Status</th></tr></thead><tbody id="tbodyTunel"></tbody></table></div>
      </div>
    </div>
    <!-- PAGE: BONDS -->
    <div class="page fade-in" id="page-bonds">
      <div class="section-header"><h2>Evolução — Bonds Offshore</h2><div class="accent-line"></div></div>
      <div class="card" style="margin-bottom:16px;padding:16px 20px">
        <div style="display:grid;grid-template-columns:1fr 2fr;gap:24px;align-items:start">
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Buscar Ticker</div>
            <div style="position:relative;">
              <svg style="position:absolute;left:10px;top:9px;width:14px;height:14px;stroke:var(--text3);fill:none" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" id="bondSearch" oninput="bondFilterList()" placeholder="Ex: RUMO..." style="width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 12px 8px 30px;color:var(--text);font-family:var(--font);font-size:12px;outline:none;transition:border-color .2s;">
            </div>
            <div style="margin-top:12px;display:flex;gap:6px">
              <button onclick="bondAddAll()" style="background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.3);color:var(--teal);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">+ Adicionar Visíveis</button>
              <button onclick="bondRemoveAll()" style="background:rgba(217,65,65,.1);border:1px solid rgba(217,65,65,.3);color:var(--red);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600">× Limpar</button>
            </div>
          </div>
          <div>
            <div style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:8px">Bonds Selecionados <span id="bondCount" style="color:var(--teal)"></span></div>
            <div id="bondChipsWrap" style="display:flex;flex-wrap:wrap;gap:6px;min-height:34px;align-items:center;padding-top:4px;"><span style="color:var(--text3);font-size:11px">Nenhum selecionado — use a busca</span></div>
          </div>
        </div>
        <div style="margin-top:16px;border-top:1px solid var(--border);padding-top:12px">
          <div id="bondList" style="display:flex;flex-wrap:wrap;gap:6px;max-height:120px;overflow-y:auto"></div>
        </div>
      </div>
      <div class="card"><div class="card-title">Curva de Preço dos Ativos (Eixo Y = Valor / Eixo X = Data)</div><div class="h320" style="height: 400px;"><canvas id="chartBondsPreco"></canvas></div></div>
      <div class="card">
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px">
          <div class="card-title" style="margin-bottom:0;flex:1;min-width:0">Posição Atual — Bonds Offshore</div>
          <div style="position:relative;flex-shrink:0">
            <svg style="position:absolute;left:8px;top:8px;width:12px;height:12px;stroke:var(--text3);fill:none;pointer-events:none" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input type="text" id="bondsSearch" oninput="_renderTbodyBonds()" placeholder="Pesquisar" style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:6px 10px 6px 26px;color:var(--text);font-family:var(--font);font-size:11px;outline:none;width:160px;transition:border-color .2s" onfocus="this.style.borderColor='var(--teal)'" onblur="this.style.borderColor='var(--border)'">
          </div>
        </div>
        <div class="table-wrap"><table><thead><tr>
          <th onclick="_bondsSort('ticker')" style="cursor:pointer;user-select:none">Ativo <span id="_bsh_ticker" style="color:var(--teal);opacity:1">&#8595;</span></th>
          <th onclick="_bondsSort('emissor')" style="cursor:pointer;user-select:none">Emissor <span id="_bsh_emissor" style="opacity:.4">&#8597;</span></th>
          <th onclick="_bondsSort('status')" style="cursor:pointer;user-select:none">Status Douro <span id="_bsh_status" style="opacity:.4">&#8597;</span></th>
          <th onclick="_bondsSort('preco')" style="cursor:pointer;user-select:none">Preço Atual <span id="_bsh_preco" style="opacity:.4">&#8597;</span></th>
        </tr></thead><tbody id="tbodyBonds"></tbody></table></div>
      </div>
    </div>
    <div class="page fade-in" id="page-ranking">
      <div class="section-header"><h2>Ranking de Emissores</h2><div class="accent-line"></div></div>
      <div id="subpage-corporativo">
        <div class="card">
          <div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px">
            <div class="card-title" style="margin-bottom:0;flex:1;min-width:0">Corporativos — Scorecard Douro</div>
            <div style="position:relative;flex-shrink:0">
              <svg style="position:absolute;left:8px;top:8px;width:12px;height:12px;stroke:var(--text3);fill:none;pointer-events:none" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" id="rankCorpSearch" oninput="_renderRankCorp()" placeholder="Pesquisar" style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:6px 10px 6px 26px;color:var(--text);font-family:var(--font);font-size:11px;outline:none;width:160px;transition:border-color .2s" onfocus="this.style.borderColor='var(--teal)'" onblur="this.style.borderColor='var(--border)'">
            </div>
          </div>
          <div class="table-wrap"><table><thead><tr>
            <th onclick="_rankCorpSort('empresa')" style="cursor:pointer;user-select:none">Empresa <span id="_rcsh_empresa" style="opacity:.4">&#8597;</span></th>
            <th onclick="_rankCorpSort('setor')" style="cursor:pointer;user-select:none">Setor <span id="_rcsh_setor" style="opacity:.4">&#8597;</span></th>
            <th onclick="_rankCorpSort('ratingMkt')" style="cursor:pointer;user-select:none">Rating <span id="_rcsh_ratingMkt" style="opacity:.4">&#8597;</span></th>
            <th onclick="_rankCorpSort('ratingDouro')" style="cursor:pointer;user-select:none">Rating Douro <span id="_rcsh_ratingDouro" style="opacity:.4">&#8597;</span></th>
            <th onclick="_rankCorpSort('status')" style="cursor:pointer;user-select:none">Status <span id="_rcsh_status" style="color:var(--teal);opacity:1">&#8595;</span></th>
          </tr></thead><tbody id="tbodyRankCorp"></tbody></table></div>
        </div>
        <div class="card"><div class="card-title">Distribuição por Status — Corporativos</div><div class="h260"><canvas id="chartRankingStatus"></canvas></div></div>
      </div>
      <div id="subpage-bancario" style="display:none">
        <div class="card">
          <div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px">
            <div class="card-title" style="margin-bottom:0;flex:1;min-width:0">Bancos — Watch List</div>
            <div style="position:relative;flex-shrink:0">
              <svg style="position:absolute;left:8px;top:8px;width:12px;height:12px;stroke:var(--text3);fill:none;pointer-events:none" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" id="rankBancosSearch" oninput="_renderRankBancos()" placeholder="Pesquisar" style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:6px 10px 6px 26px;color:var(--text);font-family:var(--font);font-size:11px;outline:none;width:160px;transition:border-color .2s" onfocus="this.style.borderColor='var(--teal)'" onblur="this.style.borderColor='var(--border)'">
            </div>
          </div>
          <div class="table-wrap"><table><thead><tr>
            <th onclick="_rankBancosSort('empresa')" style="cursor:pointer;user-select:none">Banco <span id="_rbsh_empresa" style="opacity:.4">&#8597;</span></th>
            <th onclick="_rankBancosSort('ratingDouro')" style="cursor:pointer;user-select:none">Rating Douro <span id="_rbsh_ratingDouro" style="opacity:.4">&#8597;</span></th>
            <th onclick="_rankBancosSort('status')" style="cursor:pointer;user-select:none">Status <span id="_rbsh_status" style="color:var(--teal);opacity:1">&#8595;</span></th>
          </tr></thead><tbody id="tbodyRankBancos"></tbody></table></div>
        </div>
        <div class="card"><div class="card-title">Distribuição por Rating Douro — Bancos</div><div class="h260"><canvas id="chartRankingBancosBar"></canvas></div></div>
      </div>
      <div id="subpage-comparativo" style="display:none">
        <div class="grid-2">
          <div class="card"><div class="card-title">Corporativos × Bancos — Rating Douro</div><div class="h260"><canvas id="chartCompRating"></canvas></div></div>
          <div class="card"><div class="card-title">Corporativos × Bancos — Status</div><div class="h260"><canvas id="chartCompStatus"></canvas></div></div>
        </div>
        <div class="grid-2">
          <div class="card"><div class="card-title">Corporativos — Scorecard Douro</div><div class="table-wrap"><table><thead><tr><th>Empresa</th><th>Setor</th><th>Rating</th><th>Rating Douro</th><th>Status</th></tr></thead><tbody id="tbodyCompCorp"></tbody></table></div></div>
          <div class="card"><div class="card-title">Bancos — Watch List</div><div class="table-wrap"><table><thead><tr><th>Banco</th><th>Rating Douro</th><th>Status</th></tr></thead><tbody id="tbodyCompBancos"></tbody></table></div></div>
        </div>
      </div>
    </div>
    <div class="page fade-in" id="page-performance">
      <div class="section-header"><h2>Performance dos Ativos</h2><div class="accent-line"></div></div>
      <div class="flex-row">
        <select class="custom-select" id="janelaPerf" onchange="buildPerformance()">
          <option value="21">21 dias</option>
          <option value="63">63 dias</option>
          <option value="252">252 dias</option>
        </select>
      </div>
      <div class="grid-2">
        <div class="card"><div class="card-title">Retorno Acumulado</div><div class="h320"><canvas id="chartPerfAcum"></canvas></div></div>
        <div class="card"><div class="card-title">Rolling Return</div><div class="h320"><canvas id="chartRolling"></canvas></div></div>
      </div>
      <div class="card"><div class="card-title">Matriz de Correlação</div><div class="table-wrap"><table id="corrTable"></table></div></div>
      <div class="card"><div class="card-title">Métricas</div><div class="table-wrap">
        <table><thead><tr><th>Ativo</th><th>Volatilidade</th><th>DrawDown Máx.</th><th>Retorno Acum.</th></tr></thead><tbody id="tbodyPerf"></tbody></table>
      </div></div>
    </div>
    <!-- PAGE: DOURO NEWS -->
    <div class="page" id="page-douro-news">
      <div class="section-header">
        <div style="display:flex;align-items:center;gap:14px;">
          <div style="width:36px;height:36px;background:linear-gradient(135deg,#b69d74,#d4b47a);border-radius:8px;display:flex;align-items:center;justify-content:center;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1f2839" stroke-width="2.5"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8M15 18h-5M10 6h8v4h-8z"/></svg>
          </div>
          <h2>Douro <span style="color:#b69d74">News</span></h2>
        </div>
        <div class="accent-line"></div>
      </div>
      <div class="card" style="border-left:3px solid #b69d74;background:linear-gradient(135deg,var(--surface),rgba(182,157,116,.04));padding:20px 24px;">
        <div id="newsInsight"><p style="color:var(--text3);font-style:italic;text-align:center;padding:12px 0;">Carregando insight...</p></div>
      </div>
      <div id="newsMarket" style="background:#1f2839;border-radius:10px;padding:14px 20px;display:flex;gap:32px;flex-wrap:wrap;margin:4px 0;min-height:52px;"></div>
      <div id="newsCards"></div>
      <div id="newsRF" style="margin-top:24px;"></div>
      <div id="newsWeekly" style="margin-top:12px;"></div>
    </div>
    <!-- PAGE: NOTIFICAÇÕES -->
    <div class="page fade-in" id="page-notificacoes">
      <div class="section-header" style="margin-bottom:8px">
        <div style="display:flex;align-items:center;gap:14px;">
          <div style="width:36px;height:36px;background:linear-gradient(135deg,#2fa874,#3cd28a);border-radius:8px;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 14px rgba(47,168,116,.35);">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0d1f17" stroke-width="2.5"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
          </div>
          <div>
            <h2 style="margin:0">Notificações <span style="color:#3cd28a">& Alertas</span></h2>
            <div style="font-size:11px;color:var(--text3);margin-top:2px">Variações de spread/taxa · Fatos Relevantes CVM</div>
          </div>
        </div>
        <div class="accent-line" style="background:linear-gradient(90deg,#2fa874,transparent);"></div>
      </div>

      <!-- Filtro de janela -->
      <div style="display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap;align-items:center;">
        <span style="font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;">Janela:</span>
        <button class="notif-janela-btn active" data-janela="all"  onclick="_notifSetJanela('all',this)">Todas</button>
        <button class="notif-janela-btn"        data-janela="1d"   onclick="_notifSetJanela('1d',this)">1 dia</button>
        <button class="notif-janela-btn"        data-janela="7d"   onclick="_notifSetJanela('7d',this)">7 dias</button>
        <button class="notif-janela-btn"        data-janela="21d"  onclick="_notifSetJanela('21d',this)">21 dias</button>
        <span style="margin-left:12px;font-size:10px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;">Tipo:</span>
        <button class="notif-janela-btn active" data-tipo="all"    onclick="_notifSetTipo('all',this)">Todos</button>
        <button class="notif-janela-btn"        data-tipo="spread" onclick="_notifSetTipo('spread',this)">Spread</button>
        <button class="notif-janela-btn"        data-tipo="taxa"   onclick="_notifSetTipo('taxa',this)">Taxa</button>
      </div>

      <!-- KPI strip -->
      <div id="notifKpiStrip" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px;"></div>

      <!-- Alert cards grid -->
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
        <div style="width:3px;height:3px;border-radius:50%;background:#3cd28a;flex-shrink:0;"></div>
        <span style="font-size:10px;font-weight:600;letter-spacing:2.8px;text-transform:uppercase;color:var(--text3);">Alertas de Spread & Taxa</span>
        <div style="flex:1;height:1px;background:var(--border);"></div>
        <span id="notifAlertasCount" style="font-size:10px;color:#3cd28a;font-weight:600;"></span>
      </div>
      <div id="notifAlertasGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-bottom:32px;"></div>

      <!-- Fatos Relevantes feed -->
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
        <div style="width:3px;height:3px;border-radius:50%;background:#3cd28a;flex-shrink:0;"></div>
        <span style="font-size:10px;font-weight:600;letter-spacing:2.8px;text-transform:uppercase;color:var(--text3);">Fatos Relevantes CVM — Empresas da Carteira</span>
        <div style="flex:1;height:1px;background:var(--border);"></div>
        <span id="notifFRCount" style="font-size:10px;color:#3cd28a;font-weight:600;"></span>
      </div>
      <div style="margin-bottom:12px;position:relative;max-width:320px;">
        <svg style="position:absolute;left:9px;top:8px;width:13px;height:13px;stroke:var(--text3);fill:none;pointer-events:none" viewBox="0 0 24 24" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input type="text" id="notifFRSearch" oninput="_notifRenderFR()" placeholder="Filtrar empresa ou assunto..."
          style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:7px 10px 7px 28px;color:var(--text);font-family:var(--font);font-size:11px;outline:none;width:100%;transition:border-color .2s"
          onfocus="this.style.borderColor='#3cd28a'" onblur="this.style.borderColor='var(--border)'">
      </div>
      <div id="notifFRCards" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px;"></div>
    </div>
    <!-- PAGE: SCORECARD -->
    <div class="page fade-in" id="page-scorecard" style="height:calc(100vh - 58px);margin:-28px -32px -40px;display:none;">
      <iframe
        id="scorecardFrame"
        src=""
        style="width:100%;height:100%;border:none;display:block;"
        allowfullscreen>
      </iframe>
    </div>
  </div>
</main>
<!-- ── DOURADO CHATBOT ── -->
<button id="douradoBtn" onclick="douradoToggle()" title="Dourado — Analista de Crédito">
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1f2839" stroke-width="2.3">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
</button>
<div id="douradoPanel">
  <div class="dourado-header">
    <div style="display:flex;align-items:center;gap:10px;">
      <div style="position:relative;">
        <div class="dourado-avatar">D</div>
        <div class="dourado-status" style="position:absolute;bottom:0;right:0;border:1.5px solid #111827;"></div>
      </div>
      <div>
        <div style="font-size:12.5px;font-weight:700;color:#e8e4dc;letter-spacing:-.2px;line-height:1.2;">Dourado</div>
        <div style="font-size:10px;color:#6b7f9e;font-weight:500;">Analista de Crédito · Douro Capital</div>
      </div>
    </div>
    <div style="display:flex;align-items:center;gap:5px;">
      <!-- botão expand tela cheia -->
      <button onclick="douradoExpand()" title="Tela cheia" style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);cursor:pointer;color:#4a5568;padding:5px;border-radius:7px;display:flex;align-items:center;justify-content:center;transition:all .15s;" onmouseover="this.style.background='rgba(182,157,116,.12)';this.style.color='#b69d74';this.style.borderColor='rgba(182,157,116,.3)'" onmouseout="this.style.background='rgba(255,255,255,.04)';this.style.color='#4a5568';this.style.borderColor='rgba(255,255,255,.07)'">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
      </button>
      <button onclick="douradoToggle()" style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);cursor:pointer;color:#4a5568;padding:5px;border-radius:7px;display:flex;align-items:center;justify-content:center;transition:all .15s;" onmouseover="this.style.background='rgba(255,255,255,.09)';this.style.color='#94a3b8'" onmouseout="this.style.background='rgba(255,255,255,.04)';this.style.color='#4a5568'">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
  </div>
  <div class="dourado-msgs" id="douradoMsgs"></div>
  <div class="dourado-chips" id="douradoChips">
    <button class="dourado-chip" onclick="douradoChip('Resumo geral da carteira')">Resumo</button>
    <button class="dourado-chip" onclick="douradoChip('Quais emissores estão em watch ou análise?')">Em watch</button>
    <button class="dourado-chip" onclick="douradoChip('Maiores posições por emissor')">Top posições</button>
    <button class="dourado-chip" onclick="douradoChip('Divergências de rating Douro vs mercado')">Divergências</button>
    <button class="dourado-chip" onclick="douradoChip('Qual o duration médio da carteira?')">Duration</button>
    <button class="dourado-chip" onclick="douradoChip('Quais spreads mais subiram?')">Spreads altos</button>
    <button class="dourado-chip" onclick="douradoChip('Cenário de estresse: quais emissores em risco de refinanciamento?')">Estresse</button>
    <button class="dourado-chip" onclick="douradoChip('Gráfico de exposição por setor')">Gráfico setor</button>
    <button class="dourado-chip" onclick="douradoChip('Quais emissores com Dív.Líq./EBITDA acima de 3.5x?')">Alavancagem</button>
    <button class="dourado-chip" onclick="douradoChip('Spreads que mais abriram no último ano')">Δ Spread 1a</button>
    <button class="dourado-chip" onclick="douradoChip('Perfil de vencimentos da carteira')">Vencimentos</button>
    <button class="dourado-chip" onclick="douradoChip('Análise completa da Klabin')">Síntese emis.</button>
    <button class="dourado-chip" onclick="douradoChip('Como evoluiu a alavancagem da Suzano?')">Evolução</button>
  </div>
  <div class="dourado-input-row">
    <textarea class="dourado-input" id="douradoInput" placeholder="/ para comandos · texto livre para consultas..." rows="1"
      oninput="_dspShow(this)"
      onkeydown="if(_dspKeyNav(event,this))return;if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();douradoSend();}}"></textarea>
    <button class="dourado-send" onclick="douradoSend()">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#1f2839" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
    </button>
  </div>
</div>
<div id="dSlashPal"></div>
<!-- ══ DOURADO FULLSCREEN ══ -->
<div id="douradoFull" style="display:none;position:fixed;inset:0;z-index:10001;background:rgba(4,8,20,.92);backdrop-filter:blur(24px) saturate(160%);-webkit-backdrop-filter:blur(24px) saturate(160%);align-items:center;justify-content:center;">
  <div style="position:absolute;inset:0;pointer-events:none;overflow:hidden;opacity:.03;">
    <svg width="100%" height="100%"><defs><pattern id="dfGrid" width="36" height="36" patternUnits="userSpaceOnUse"><path d="M 36 0 L 0 0 0 36" fill="none" stroke="#b69d74" stroke-width=".7"/></pattern></defs><rect width="100%" height="100%" fill="url(#dfGrid)"/></svg>
  </div>
  <div style="position:relative;width:94vw;max-width:1100px;height:88vh;background:linear-gradient(160deg,rgba(17,24,39,.99),rgba(11,17,30,.99));border-radius:18px;border:1px solid rgba(182,157,116,.16);box-shadow:0 40px 100px rgba(0,0,0,.75),inset 0 1px 0 rgba(182,157,116,.1);display:flex;flex-direction:column;overflow:hidden;">
    <!-- header fullscreen -->
    <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid rgba(182,157,116,.1);background:linear-gradient(160deg,rgba(26,36,56,.95),rgba(17,24,39,.99));flex-shrink:0;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#b69d74,#d4b47a);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:#1f2839;flex-shrink:0;">D</div>
        <div>
          <div style="font-size:13px;font-weight:700;color:#e8e4dc;letter-spacing:-.2px;line-height:1.2;">Dourado</div>
          <div style="font-size:10px;color:#6b7f9e;">Analista de Crédito · Douro Capital</div>
        </div>
        <div style="width:7px;height:7px;border-radius:50%;background:#2fa874;box-shadow:0 0 6px rgba(47,168,116,.7);margin-left:4px;"></div>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <!-- orb IA -->
        <div id="dfOrbBtn" onclick="toggleDFHints()" title="Inteligência do Dourado" style="position:relative;width:34px;height:34px;cursor:pointer;flex-shrink:0;">
          <canvas id="dfOrbCanvas" width="34" height="34" style="position:absolute;inset:0;border-radius:50%;"></canvas>
          <div id="dfOrbRing" style="position:absolute;inset:-3px;border-radius:50%;border:1.5px solid rgba(182,157,116,.35);animation:orbRingSpin 4s linear infinite;pointer-events:none;"></div>
          <div id="dfOrbRing2" style="position:absolute;inset:-6px;border-radius:50%;border:1px dashed rgba(182,157,116,.15);animation:orbRingSpin 8s linear infinite reverse;pointer-events:none;"></div>
        </div>
        <button onclick="douradoCollapse()" title="Minimizar" style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);cursor:pointer;color:#4a5568;padding:6px;border-radius:7px;display:flex;align-items:center;justify-content:center;transition:all .15s;" onmouseover="this.style.background='rgba(255,255,255,.09)';this.style.color='#94a3b8'" onmouseout="this.style.background='rgba(255,255,255,.04)';this.style.color='#4a5568'">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/></svg>
        </button>
        <button onclick="douradoCollapse();douradoToggle();" style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);cursor:pointer;color:#4a5568;padding:6px;border-radius:7px;display:flex;align-items:center;justify-content:center;transition:all .15s;" onmouseover="this.style.background='rgba(255,255,255,.09)';this.style.color='#94a3b8'" onmouseout="this.style.background='rgba(255,255,255,.04)';this.style.color='#4a5568'">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    </div>
    <!-- painel capacidades liquid glass -->
    <div id="dfHintsPanel" style="display:none;flex-shrink:0;border-bottom:1px solid rgba(182,157,116,.1);background:rgba(6,12,26,.72);backdrop-filter:blur(28px) saturate(180%);-webkit-backdrop-filter:blur(28px) saturate(180%);">
      <div style="position:relative;padding:16px 24px 18px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
          <div style="width:5px;height:5px;border-radius:50%;background:#b69d74;box-shadow:0 0 7px rgba(182,157,116,.9);animation:dfPing 1.6s ease-in-out infinite;flex-shrink:0;"></div>
          <span style="font-size:7px;font-weight:800;letter-spacing:4px;text-transform:uppercase;color:rgba(182,157,116,.5);font-family:'DM Mono',monospace;">O QUE VOCÊ PODE PERGUNTAR</span>
          <div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(182,157,116,.18),transparent);"></div>
        </div>
        <div id="dfHintsList" style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;"></div>
      </div>
    </div>
    <!-- corpo do chat fullscreen -->
    <div id="douradoFullMsgs" style="flex:1;min-height:0;overflow-y:auto;padding:16px 20px;display:flex;flex-direction:column;gap:10px;background:#0a1120;scrollbar-width:thin;scrollbar-color:rgba(182,157,116,.2) transparent;"></div>
    <!-- chips fullscreen -->
    <div style="display:flex;flex-wrap:wrap;gap:5px;padding:8px 20px;background:#0c1220;border-top:1px solid rgba(255,255,255,.04);flex-shrink:0;">
      <button class="dourado-chip" onclick="douradoChipFull('Resumo geral da carteira')">Resumo</button>
      <button class="dourado-chip" onclick="douradoChipFull('Maiores posições por emissor')">Top posições</button>
      <button class="dourado-chip" onclick="douradoChipFull('Quais emissores estão em watch ou análise?')">Em watch</button>
      <button class="dourado-chip" onclick="douradoChipFull('Divergências de rating Douro vs mercado')">Divergências</button>
      <button class="dourado-chip" onclick="douradoChipFull('Qual o duration médio da carteira?')">Duration</button>
      <button class="dourado-chip" onclick="douradoChipFull('Análise completa da Equatorial')">Síntese emis.</button>
      <button class="dourado-chip" onclick="douradoChipFull('Spreads que mais abriram no último ano')">Δ Spread 1a</button>
      <button class="dourado-chip" onclick="douradoChipFull('Cenário de estresse: quais emissores em risco?')">Estresse</button>
    </div>
    <!-- input fullscreen -->
    <div style="padding:12px 20px;border-top:1px solid rgba(255,255,255,.05);display:flex;gap:8px;background:#111827;flex-shrink:0;align-items:flex-end;">
      <textarea id="douradoInputFull" class="dourado-input" placeholder="/ para comandos · pergunte sobre emissores, spreads, alavancagem, rating..." rows="2" style="flex:1;max-height:96px;"
        oninput="_dspShow(this)"
        onkeydown="if(_dspKeyNav(event,this))return;if(event.key==='Enter'&&!event.shiftKey){{event.preventDefault();douradoSendFull();}}"></textarea>
      <button class="dourado-send" onclick="douradoSendFull()" style="width:40px;height:40px;">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#1f2839" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
      </button>
    </div>
  </div>
</div>
<style>
@keyframes dfIn       {{ from {{ opacity:0;transform:scale(.97) translateY(8px); }} to {{ opacity:1;transform:none; }} }}
@keyframes orbRingSpin {{ from {{ transform:rotate(0deg); }} to {{ transform:rotate(360deg); }} }}
@keyframes orbPulse   {{ 0%,100% {{ opacity:.75;transform:scale(1); }} 50% {{ opacity:1;transform:scale(1.07); }} }}
@keyframes dfPanelIn  {{ from {{ opacity:0;transform:translateY(-6px); }} to {{ opacity:1;transform:none; }} }}
@keyframes dfPing     {{ 0%,100% {{ box-shadow:0 0 5px rgba(182,157,116,.7); }} 50% {{ box-shadow:0 0 12px rgba(182,157,116,1); }} }}
@keyframes dfCardIn   {{ from {{ opacity:0;transform:translateY(10px) scale(.96); }} to {{ opacity:1;transform:none; }} }}
#douradoFull > div:nth-child(2) {{ animation:dfIn .28s cubic-bezier(.16,1,.3,1); }}
#dfOrbBtn {{ animation:orbPulse 2.8s ease-in-out infinite; }}
#dfOrbBtn:hover {{ animation:none !important;transform:scale(1.1);filter:brightness(1.25); }}
#dfHintsPanel {{ animation:dfPanelIn .22s cubic-bezier(.16,1,.3,1); }}
/* liquid glass card */
.df-lg-card {{
  position:relative;
  background:linear-gradient(145deg,rgba(255,255,255,.06) 0%,rgba(255,255,255,.02) 100%);
  backdrop-filter:blur(20px) saturate(160%);
  -webkit-backdrop-filter:blur(20px) saturate(160%);
  border:1px solid rgba(255,255,255,.09);
  border-top:1px solid rgba(255,255,255,.14);
  border-radius:14px;
  padding:13px 14px 11px;
  cursor:pointer;
  overflow:hidden;
  transition:transform .22s cubic-bezier(.16,1,.3,1), box-shadow .22s, border-color .22s, background .22s;
  animation:dfCardIn .32s cubic-bezier(.16,1,.3,1) both;
}}
.df-lg-card::before {{
  content:'';
  position:absolute;inset:0;
  border-radius:14px;
  background:radial-gradient(ellipse at 50% 0%,rgba(182,157,116,.13) 0%,transparent 70%);
  opacity:0;
  transition:opacity .22s;
  pointer-events:none;
}}
.df-lg-card:hover {{
  transform:translateY(-3px) scale(1.02);
  border-color:rgba(182,157,116,.38);
  border-top-color:rgba(182,157,116,.55);
  box-shadow:0 8px 32px rgba(0,0,0,.45), 0 0 0 1px rgba(182,157,116,.1), inset 0 1px 0 rgba(182,157,116,.18);
  background:linear-gradient(145deg,rgba(182,157,116,.1) 0%,rgba(182,157,116,.04) 100%);
}}
.df-lg-card:hover::before {{ opacity:1; }}
.df-lg-card:active {{ transform:translateY(-1px) scale(1.005); }}
.df-lg-icon {{
  width:30px;height:30px;border-radius:8px;
  background:rgba(182,157,116,.12);
  border:1px solid rgba(182,157,116,.2);
  display:flex;align-items:center;justify-content:center;
  margin-bottom:9px;
  transition:background .2s,box-shadow .2s;
  flex-shrink:0;
}}
.df-lg-card:hover .df-lg-icon {{
  background:rgba(182,157,116,.22);
  box-shadow:0 0 12px rgba(182,157,116,.3);
}}
.df-lg-title {{
  font-size:9.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;
  color:rgba(228,215,185,.92);margin-bottom:7px;line-height:1.2;
}}
.df-lg-ex {{
  font-size:8.5px;color:rgba(160,155,145,.7);line-height:1.55;
  display:flex;align-items:flex-start;gap:5px;
  padding:3px 0;
  border-top:1px solid rgba(255,255,255,.04);
  transition:color .15s;
  cursor:pointer;
}}
.df-lg-ex:first-of-type {{ border-top:none; }}
.df-lg-ex:hover {{ color:rgba(182,157,116,.95); }}
.df-lg-arr {{ color:rgba(182,157,116,.35);flex-shrink:0;font-size:8px;margin-top:1px;transition:color .15s,transform .15s; }}
.df-lg-ex:hover .df-lg-arr {{ color:rgba(182,157,116,.9);transform:translateX(2px); }}
</style>
<script>
// ── DOURADO FULLSCREEN ────────────────────────────────────────────────────
const DF_HINTS = [
  {{ label:'SÍNTESE',     title:'Síntese de Emissor',
    examples:['Análise completa da Klabin','Me fala tudo sobre a Equatorial','Perfil completo da Rumo: fundamentos e spread'] }},
  {{ label:'FUNDAMENTOS', title:'Filtro por Fundamento',
    examples:['Emissores com DL/EBITDA acima de 3.5x','Quais têm ROE abaixo de 8%?','Margem EBITDA maior que 25%'] }},
  {{ label:'TEMPORAL',    title:'Evolução Temporal de KPI',
    examples:['Como evoluiu a alavancagem da Suzano?','Trajetória do EBITDA da Eneva nos últimos 12 meses','Como progrediu o FCF da Klabin?'] }},
  {{ label:'COMPARATIVO', title:'Comparação de Emissores',
    examples:['Comparar Eneva e Engie em DL/EBITDA','Klabin vs Suzano: spread e alavancagem','Compare Energisa vs Cemig vs Copel'] }},
  {{ label:'ESTRESSE',    title:'Estresse de Liquidez',
    examples:['Quais emissores em risco de refinanciamento?','Quais nomes com pressão de liquidez no setor elétrico?','Quem fica em apuros com juros altos?'] }},
  {{ label:'Z-SCORE',     title:'Análise de Spread',
    examples:['Quais spreads mais subiram na carteira?','Quais spreads estão acima da mediana?','Quais emissores com spread mais alto por setor?'] }},
  {{ label:'BENCHMARK',   title:'Benchmark Setorial',
    examples:['Equatorial vs média do setor elétrico em DL/EBITDA','Como a Raízen se compara ao setor?','Rumo vs peers de logística em alavancagem'] }},
  {{ label:'VENCIMENTOS', title:'Mapa de Vencimentos',
    examples:['Perfil de vencimentos da carteira','Quais ativos vencem nos próximos 12 meses?','Estrutura de vencimentos da carteira'] }},
  {{ label:'RANKING',     title:'Ranking Dinâmico',
    examples:['Quais spreads mais subiram no último ano?','Maiores posições por emissor','Ranking de alavancagem — maior para menor'] }},
  {{ label:'MULTI-FILTRO',title:'Query Multi-Critério',
    examples:['Energia elétrica aprovada com duration acima de 4','Emissores rating AA com spread abaixo de 1.2%','Watch e saneamento com DL/EBITDA acima de 3x'] }},
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
function _initOrb() {{
  const cv = document.getElementById('dfOrbCanvas');
  if (!cv || cv._orbRunning) return;
  cv._orbRunning = true;
  const ctx = cv.getContext('2d');
  const W=34, H=34, cx=W/2, cy=H/2;
  let t=0;
  const pts = Array.from({{length:5}},(_,i)=>{{
    const a=(i/5)*Math.PI*2;
    return {{ a, r:5+Math.random()*5, sp:.01+Math.random()*.015, sz:.7+Math.random()*1, al:.35+Math.random()*.45 }};
  }});
  function draw() {{
    ctx.clearRect(0,0,W,H);
    const g=ctx.createRadialGradient(cx,cy,1,cx,cy,13);
    g.addColorStop(0,'rgba(212,180,122,.85)'); g.addColorStop(.5,'rgba(182,157,116,.45)');
    g.addColorStop(.85,'rgba(140,110,60,.15)'); g.addColorStop(1,'rgba(100,70,30,0)');
    ctx.beginPath(); ctx.arc(cx,cy,13,0,Math.PI*2); ctx.fillStyle=g; ctx.fill();
    const g2=ctx.createRadialGradient(cx-3,cy-3,0,cx,cy,7);
    g2.addColorStop(0,'rgba(255,240,200,.5)'); g2.addColorStop(1,'rgba(255,240,200,0)');
    ctx.beginPath(); ctx.arc(cx,cy,13,0,Math.PI*2); ctx.fillStyle=g2; ctx.fill();
    for(const p of pts) {{
      p.a+=p.sp;
      ctx.beginPath(); ctx.arc(cx+Math.cos(p.a)*p.r, cy+Math.sin(p.a)*p.r, p.sz,0,Math.PI*2);
      ctx.fillStyle=`rgba(255,225,150,${{p.al*(.7+.3*Math.sin(t*.04+p.a))}})`;
      ctx.fill();
    }}
    t++; _orbAnim=requestAnimationFrame(draw);
  }}
  draw();
}}

// ── RENDER LIQUID GLASS CARDS ─────────────────────────────────────────────
function _renderLGCards() {{
  const list=document.getElementById('dfHintsList');
  if(!list||list._lgRendered) return;
  list._lgRendered=true;
  list.innerHTML=DF_HINTS.map((h,i)=>`
    <div class="df-lg-card" style="animation-delay:${{i*.04}}s">
      <div style="display:flex;align-items:center;gap:9px;margin-bottom:8px;">
        <div class="df-lg-icon" style="color:rgba(182,157,116,.85)">${{DF_GLYPHS[i%DF_GLYPHS.length]}}</div>
        <span class="df-lg-title">${{h.label}}</span>
      </div>
      ${{h.examples.map(ex=>`
        <div class="df-lg-ex" onclick="dfUseHint(${{JSON.stringify(ex)}})">
          <span class="df-lg-arr">›</span>
          <span>${{ex}}</span>
        </div>`).join('')}}
    </div>`).join('');
}}

// ── EXPAND / COLLAPSE / TOGGLE ────────────────────────────────────────────
function douradoExpand() {{
  const full=document.getElementById('douradoFull');
  full.style.display='flex'; _dfOpen=true; _initOrb();
  if(!_dfInitialized) {{
    _dfInitialized=true;
    const src=document.getElementById('douradoMsgs'), dst=document.getElementById('douradoFullMsgs');
    if(src&&dst) {{ dst.innerHTML=src.innerHTML; dst.scrollTop=dst.scrollHeight; }}
    _renderLGCards();
  }}
}}
function douradoCollapse() {{
  document.getElementById('douradoFull').style.display='none';
  _dfOpen=false; _dfHintsVisible=false;
  document.getElementById('dfHintsPanel').style.display='none';
  if(_orbAnim){{cancelAnimationFrame(_orbAnim);_orbAnim=null;}}
  const cv=document.getElementById('dfOrbCanvas'); if(cv) cv._orbRunning=false;
}}
function toggleDFHints() {{
  _dfHintsVisible=!_dfHintsVisible;
  const panel=document.getElementById('dfHintsPanel');
  panel.style.display=_dfHintsVisible?'block':'none';
  if(_dfHintsVisible) _renderLGCards();
}}
function dfUseHint(ex) {{
  const inp=document.getElementById('douradoInputFull');
  if(inp){{inp.value=ex;inp.focus();}}
  // Force-collapse the hints panel without toggling the flag through toggleDFHints
  _dfHintsVisible=false;
  const panel=document.getElementById('dfHintsPanel');
  if(panel) panel.style.display='none';
  douradoSendFull();
}}
function _douradoAddMsgBoth(role, text) {{
  douradoAddMsg(role, text);
  const fullMsgs = document.getElementById('douradoFullMsgs');
  if (!fullMsgs || !_dfOpen) return;
  const div = document.createElement('div');
  div.className = `dourado-msg ${{role==='user'?'user':''}}`;
  if (role === 'bot') {{
    div.innerHTML = `<div class="dourado-avatar" style="width:28px;height:28px;font-size:12px;flex-shrink:0;">D</div><div class="dourado-bubble">${{_renderMd(text)}}</div>`;
  }} else {{
    div.innerHTML = `<div class="dourado-bubble">${{text.replace(/</g,'&lt;').replace(/>/g,'&gt;')}}</div>`;
  }}
  fullMsgs.appendChild(div);
  fullMsgs.scrollTop = fullMsgs.scrollHeight;
}}
function douradoSendFull() {{
  _dspHide();
  const inp = document.getElementById('douradoInputFull');
  const txt = (inp.value || '').trim();
  if (!txt) return;
  inp.value = '';
  if(_dfHintsVisible) toggleDFHints();
  if(txt.startsWith('/')) {{ if(_douradoCmd(txt)) return; }}
  _douradoAddMsgBoth('user', txt);
  setTimeout(() => {{
    const resp = _nlqRespond(txt);
    if (resp && resp.text) {{
      _douradoAddMsgBoth('bot', resp.text);
      if (resp.chart) _addChatChart(resp.chartTitulo || '', resp.chart);
    }} else if (typeof resp === 'string') {{
      _douradoAddMsgBoth('bot', resp);
    }}
  }}, 320);
}}
function douradoChipFull(txt) {{
  const inp = document.getElementById('douradoInputFull');
  if (inp) {{ inp.value = txt; inp.focus(); inp.setSelectionRange(txt.length, txt.length); }}
}}
document.getElementById('douradoFull').addEventListener('click', e => {{ if(e.target.id==='douradoFull') douradoCollapse(); }});
</script>
<script>
// ── DADOS INJETADOS PELO PYTHON ─────────────────────────────────────────
const ATIVOS       = {ativos_js};
const FIN_SERIES   = {fin_series_js};
const RANK_CORP    = {rank_corp_js};
const RANK_BANCOS  = {rank_bancos_js};
const SPREADS_TS   = {spreads_ts_js};
const PERF_DATA    = {perf_js};
const BONDS_INFO   = {bonds_info_js};
const BONDS_TS     = {bonds_ts_js};
const setores      = {setores_js};
const PL_TOTAL     = {pl_total_js};
const PL_POR_CARTEIRA = {pl_por_carteira_js};
const NEWS_DATA          = {news_js};
const ALERTAS_NOTIF      = {alertas_js};
const FATOS_RELEVANTES   = {fatos_relevantes_js};
const SCORECARD_SRC = {scorecard_src};
const BCB_LIVE     = {bcb_bancos_js};
const BUILD_INFO   = {build_info_js};

// ── CONSTANTES ────────────────────────────────────────────────────────────
const COLORS = ['#b69d74','#00677b','#1f2839','#2fa874','#d94141','#3174b8','#a78bd4','#e0c44a','#60b85a','#d47aa7','#5ab8d4','#d4a77a'];
/* ── CROSSHAIR PLUGIN (linha vertical que snapa em X para todas as séries) ── */
const _crosshairPlugin = {{
  id: 'crosshair',
  afterDraw(chart) {{
    if (chart.config.type !== 'line') return;
    if (!chart._crosshairX) return;
    const {{ctx, chartArea:{{top,bottom}}}} = chart;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(chart._crosshairX, top);
    ctx.lineTo(chart._crosshairX, bottom);
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(182,157,116,.55)';
    ctx.setLineDash([4,3]);
    ctx.stroke();
    ctx.restore();
  }},
  afterEvent(chart, args) {{
    if (chart.config.type !== 'line') return;
    const e = args.event;
    if (e.type === 'mousemove') {{
      chart._crosshairX = e.x;
    }} else if (e.type === 'mouseout') {{
      chart._crosshairX = null;
    }}
    chart.draw();
  }}
}};
Chart.register(_crosshairPlugin);

/* opções comuns para gráficos com crosshair */
const _CROSSHAIR_OPTS = {{
  interaction: {{ mode:'index', intersect:false, axis:'x' }},
  plugins: {{
    tooltip: {{
      mode: 'index',
      intersect: false,
      backgroundColor: 'rgba(15,20,35,.88)',
      titleColor: '#d4b47a',
      bodyColor: '#c8c0b4',
      borderColor: 'rgba(182,157,116,.3)',
      borderWidth: 1,
      padding: 10,
      titleFont: {{ family:"'DM Mono',monospace", size:10 }},
      bodyFont: {{ family:"'DM Mono',monospace", size:10 }},
      callbacks: {{
        label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(2)}}%`
      }}
    }}
  }}
}};

const CHART_DEFAULTS = {{
  responsive:true,
  maintainAspectRatio:false,
  plugins:{{ legend:{{ labels:{{ color:'#718096', font:{{size:11, family:"'Montserrat', sans-serif"}}, boxWidth:12 }} }} }},
  scales:{{
    x:{{ ticks:{{ color:'#718096', font:{{size:10, family:"'DM Mono', monospace"}}, maxTicksLimit:12 }}, grid:{{ color:'rgba(31,40,57,.05)' }} }},
    y:{{ ticks:{{ color:'#718096', font:{{size:10, family:"'DM Mono', monospace"}} }}, grid:{{ color:'rgba(31,40,57,.05)' }} }}
  }}
}};
const DOUGHNUT_OPTS = {{
  responsive:true, maintainAspectRatio:false, cutout:'65%',
  plugins:{{ legend:{{ position:'bottom', labels:{{ color:'#718096', font:{{size:11, family:"'Montserrat', sans-serif"}}, boxWidth:12, padding:12, filter:(item,data)=>data.datasets[0].data[item.index]>0 }} }} }}
}};
let activeCharts = {{}};
function mk(id, cfg) {{
  const canvas = document.getElementById(id);
  if (!canvas) return null;
  if (activeCharts[id]) {{
    try {{ activeCharts[id].destroy(); }} catch(e) {{}}
    delete activeCharts[id];
  }}
  canvas.width  = canvas.offsetWidth  || canvas.width;
  canvas.height = canvas.offsetHeight || canvas.height;
  try {{
    const c = new Chart(canvas, cfg);
    activeCharts[id] = c;
    return c;
  }} catch(e) {{
    console.warn('Chart.js erro em "' + id + '":', e);
    return null;
  }}
}}
// ── HELPERS ───────────────────────────────────────────────────────────────
const fmtBRL = v => v==null?'—': v>=1e9?`R$ ${{(v/1e9).toFixed(2)}}Bi`: v>=1e6?`R$ ${{(v/1e6).toFixed(1)}}Mi`: v>=1e3?`R$ ${{(v/1e3).toFixed(0)}}Ki`:`R$ ${{Number(v).toFixed(0)}}`;
const fmtPct = v => v==null?'—':`${{(v*100).toFixed(1)}}%`;
const fmtX   = v => v==null?'—':`${{Number(v).toFixed(2)}}x`;
const badgeStatus = s => {{
  const m = {{Aprovado:'badge-green', Reprovado:'badge-red', 'Em análise':'badge-gold', Watch:'badge-gold', Monitoramento:'badge-gold'}};
  return `<span class="badge ${{m[s]||'badge-muted'}}">${{s||'—'}}</span>`;
}};
const badgeRating = r => {{
  if (!r || r === 'N/D') return '<span class="badge badge-muted">—</span>';
  const aaa=['AAA'], aa=['AA+','AA','AA-'], a=['A+','A','A-'], bbb=['BBB+','BBB','BBB-'], bb=['BB+','BB','BB-'];
  const cls = aaa.includes(r)?'badge-blue': aa.includes(r)||a.includes(r)?'badge-teal': bbb.includes(r)||bb.includes(r)?'badge-gold': 'badge-red';
  return `<span class="badge ${{cls}}">${{r}}</span>`;
}};
// ── FILTROS ───────────────────────────────────────────────────────────────
function getFiltered() {{
  const cart    = document.getElementById('carteiraFilter').value;
  const setor   = document.getElementById('setorFilter').value;
  const officer = document.getElementById('officerFilter')?.value || '';
  return ATIVOS.filter(a =>
    (!cart    || a.carteira === cart)   &&
    (!setor   || a.setor   === setor)  &&
    (!officer || a.officer === officer)
  );
}}
function applyFilters() {{
  buildComposicao();
  buildRating();
  spInicializado = false;
  buildSpreads();
  buildTunel();
}}
// ── NAVEGAÇÃO ─────────────────────────────────────────────────────────────
const initializedPages = {{}};
const loadedPages = {{}};
function showPage(id, el) {{
  const current = document.querySelector('.page.active');
  const pg      = document.getElementById('page-' + id);
  if (current && current !== pg) {{
    current.classList.add('page-exit');
    current.addEventListener('animationend', () => {{
      current.classList.remove('active', 'page-exit');
    }}, {{ once: true }});
  }} else if (current) {{
    current.classList.remove('active');
  }}
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  pg.classList.remove('page-enter');
  void pg.offsetWidth;
  pg.classList.add('active', 'page-enter');
  pg.addEventListener('animationend', () => pg.classList.remove('page-enter'), {{ once: true }});
  if(el) el.classList.add('active');
  // Esconde filtros na home (Panorama)
  const tRight = document.querySelector('.topbar-right');
  if (tRight) tRight.style.display = id === 'home' ? 'none' : '';
  const builders = {{
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
    bancos: buildBancos,
    'douro-news': buildDouroNews,
    notificacoes: buildNotificacoes,
    scorecard: buildScorecard
  }};
  const hBtn = document.getElementById('homeBtnTopbar');
  if (hBtn) hBtn.classList.toggle('active', id === 'home');
  _setSidebarRail(id !== 'home');
  if (builders[id]) {{
    requestAnimationFrame(() => {{
      builders[id]();
      setTimeout(() => {{
        Object.values(activeCharts).forEach(c => {{
          try {{ c.resize(); c.update(); }} catch(e){{}}
        }});
      }}, 80);
    }});
  }}
}}
// ── HOME PAGE NAVIGATION ───────────────────────────────────────────────────
function homeSelectEmp(empresa) {{
  showPage('fundamentos', document.querySelector('.nav-item[onclick*="fundamentos"]'));
  setTimeout(() => {{
    const sel = document.getElementById('fundEmpSel');
    if (sel) {{
      sel.value = empresa;
      sel.dispatchEvent(new Event('change'));
    }}
  }}, 100);
}}
function homeSelectBanco(banco) {{
  showPage('bancos', document.querySelector('.nav-item[onclick*="bancos"]'));
  setTimeout(() => {{
    const sel = document.getElementById('bancosEmpSel');
    if (sel) {{
      sel.value = banco;
      sel.dispatchEvent(new Event('change'));
    }}
    buildBancos(banco);
  }}, 100);
}}
function homeDiveScorecard(tipo) {{
  if (tipo === 'corp') {{
    showPage('scorecard', document.querySelector('.nav-item[onclick*="scorecard"]'));
  }} else if (tipo === 'banco') {{
    showPage('scorecard', document.querySelector('.nav-item[onclick*="scorecard"]'));
  }}
}}
// ── COMPOSIÇÃO HELPERS ────────────────────────────────────────────────────
function getCorStatus(nomeEmissor) {{
  const match = ATIVOS.find(a => a.emissor === nomeEmissor);
  const st = (match?.Status||'').trim();
  if (st==='Aprovado')  return '#00677b';
  if (st==='Reprovado') return '#d94141';
  return '#b69d74';
}}

// ── BAR-CLICK EMISSOR FILTER ───────────────────────────────────────────────
let _emFiltroBar = null;
let _cachedAtivos = [], _cachedTotalCred = 0, _cachedPLFilt = 0;
let _setorFiltroDonut = null;
let _ratingFilter = {{ classe: null, ratingMkt: null, ratingDouro: null }};

let _ativosSortCol = 'saldo';
let _ativosSortAsc = false;
function _ativosSort(col) {{
  if (_ativosSortCol === col) {{ _ativosSortAsc = !_ativosSortAsc; }}
  else {{ _ativosSortCol = col; _ativosSortAsc = col === 'carteira' || col === 'ticker' || col === 'emissor' || col === 'setor' || col === 'classe' || col === 'status'; }}
  _renderTbodyAtivos();
  _renderTbodyAtivosRating();
}}
function _ativosSortReset() {{
  _ativosSortCol = 'saldo'; _ativosSortAsc = false;
  const inp = document.getElementById('ativosSearch');
  if (inp) inp.value = '';
  const inpRating = document.getElementById('ativosSearchRating');
  if (inpRating) inpRating.value = '';
  _renderTbodyAtivos();
  _renderTbodyAtivosRating();
}}
function _renderTbodyAtivos() {{
  const q = (document.getElementById('ativosSearch')?.value || '').toLowerCase().trim();
  let source = _cachedAtivos;
  if (_setorFiltroDonut) source = source.filter(a => (a.setor||'N/D') === _setorFiltroDonut);
  if (_emFiltroBar) source = source.filter(a => (a.emissor||'').toLowerCase() === _emFiltroBar.toLowerCase());
  if (q) {{
    source = source.filter(a => {{
      const fields = [a.carteira,a.ticker,a.emissor,a.setor,a.classe,a.Status,a['Rating base S&P'],a['Rating Douro']];
      return fields.some(f => f && String(f).toLowerCase().includes(q));
    }});
  }}
  const cmpStr = (a, b) => (a||'').localeCompare(b||'', 'pt-BR');
  const cmpNum = (a, b) => (a||0) - (b||0);
  const dir = _ativosSortAsc ? 1 : -1;
  source = [...source].sort((a, b) => {{
    switch(_ativosSortCol) {{
      case 'carteira':  return dir * cmpStr(a.carteira, b.carteira);
      case 'ticker':    return dir * cmpStr(a.ticker, b.ticker);
      case 'emissor':   return dir * cmpStr(a.emissor, b.emissor);
      case 'setor':     return dir * cmpStr(a.setor, b.setor);
      case 'saldo':     return dir * cmpNum(a.saldo, b.saldo);
      case 'pctCred':   return dir * cmpNum(a.saldo, b.saldo);
      case 'pctPL':     return dir * cmpNum(a.saldo, b.saldo);
      case 'duration':  return dir * cmpNum(a.duration, b.duration);
      case 'classe':    return dir * cmpStr(a.classe, b.classe);
      case 'status':    return dir * cmpStr(a.Status, b.Status);
      default:          return dir * cmpNum(b.saldo, a.saldo);
    }}
  }});
  ['carteira','ticker','emissor','setor','saldo','pctCred','pctPL','duration','classe','status'].forEach(col => {{
    const el = document.getElementById('_sh_'+col);
    const el2 = document.getElementById('_sh_'+col+'_rating');
    const text = col === _ativosSortCol ? (_ativosSortAsc ? '↑' : '↓') : '↕';
    const style = col === _ativosSortCol ? 'var(--teal)' : '';
    if (el) {{ el.textContent = text; el.style.opacity = col === _ativosSortCol ? '1' : '.4'; el.style.color = style; }}
    if (el2) {{ el2.textContent = text; el2.style.opacity = col === _ativosSortCol ? '1' : '.4'; el2.style.color = style; }}
  }});
  const tag = document.getElementById('emFiltroTag');
  if (tag) {{
    let tagHtml = '';
    if (_setorFiltroDonut) tagHtml += `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(182,157,116,.12);border:1px solid rgba(182,157,116,.4);border-radius:12px;padding:2px 10px 2px 8px;font-size:10px;font-weight:600;color:#b69d74;margin-left:8px;cursor:pointer" onclick="_clearSetorFiltro()">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/></svg>
        Setor: ${{_setorFiltroDonut}}&nbsp;<span style="font-size:13px;line-height:1;opacity:.7">×</span></span>`;
    if (_emFiltroBar) tagHtml += `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.3);border-radius:12px;padding:2px 10px 2px 8px;font-size:10px;font-weight:600;color:var(--teal);margin-left:8px;cursor:pointer" onclick="_clearEmFiltroBar()">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/></svg>
        ${{_emFiltroBar}}&nbsp;<span style="font-size:13px;line-height:1;opacity:.7">×</span></span>`;
    tag.innerHTML = tagHtml;
  }}
  const hasFilter = _setorFiltroDonut || _emFiltroBar;
  document.getElementById('countAtivos').textContent =
    hasFilter ? `— ${{source.length}} posição(ões) · ${{_cachedAtivos.length}} total` : `— ${{source.length}} de ${{_cachedAtivos.length}} posições`;
  document.getElementById('tbodyAtivos').innerHTML = source
    .map(a => `<tr>
      <td class="td-muted">${{a.carteira||'—'}}</td>
      <td style="font-weight:700">${{a.ticker||'—'}}</td>
      <td>${{a.emissor||'—'}}</td>
      <td class="td-muted">${{a.setor||'—'}}</td>
      <td style="font-family:var(--mono)">${{fmtBRL(a.saldo)}}</td>
      <td style="font-family:var(--mono)">${{_cachedTotalCred>0?(a.saldo/_cachedTotalCred*100).toFixed(2):0}}%</td>
      <td style="font-family:var(--mono)">${{_cachedPLFilt>0?(a.saldo/_cachedPLFilt*100).toFixed(2):0}}%</td>
      <td style="font-family:var(--mono)">${{a.duration?Number(a.duration).toFixed(1)+'a':'—'}}</td>
      <td class="td-muted">${{a.classe||'—'}}</td>
      <td>${{badgeRating(a['Rating base S&P'])}}</td>
      <td>${{badgeRating(a['Rating Douro'])}}</td>
      <td>${{badgeStatus(a.Status)}}</td>
    </tr>`).join('');
}}

function _renderTbodyAtivosRating() {{
  const q = (document.getElementById('ativosSearchRating')?.value || '').toLowerCase().trim();
  let source = _cachedAtivos;
  if (_ratingFilter.classe) source = source.filter(a => (a.classe||'') === _ratingFilter.classe);
  if (_ratingFilter.ratingMkt) source = source.filter(a => (a['Rating base S&P']||'') === _ratingFilter.ratingMkt);
  if (_ratingFilter.ratingDouro) source = source.filter(a => (a['Rating Douro']||'') === _ratingFilter.ratingDouro);
  if (q) {{
    source = source.filter(a => {{
      const fields = [a.carteira,a.ticker,a.emissor,a.setor,a.classe,a.Status,a['Rating base S&P'],a['Rating Douro']];
      return fields.some(f => f && String(f).toLowerCase().includes(q));
    }});
  }}
  const cmpStr = (a, b) => (a||'').localeCompare(b||'', 'pt-BR');
  const cmpNum = (a, b) => (a||0) - (b||0);
  const dir = _ativosSortAsc ? 1 : -1;
  source = [...source].sort((a, b) => {{
    switch(_ativosSortCol) {{
      case 'carteira':  return dir * cmpStr(a.carteira, b.carteira);
      case 'ticker':    return dir * cmpStr(a.ticker, b.ticker);
      case 'emissor':   return dir * cmpStr(a.emissor, b.emissor);
      case 'setor':     return dir * cmpStr(a.setor, b.setor);
      case 'saldo':     return dir * cmpNum(a.saldo, b.saldo);
      case 'pctCred':   return dir * cmpNum(a.saldo, b.saldo);
      case 'pctPL':     return dir * cmpNum(a.saldo, b.saldo);
      case 'duration':  return dir * cmpNum(a.duration, b.duration);
      case 'classe':    return dir * cmpStr(a.classe, b.classe);
      case 'status':    return dir * cmpStr(a.Status, b.Status);
      default:          return dir * cmpNum(b.saldo, a.saldo);
    }}
  }});
  const tag = document.getElementById('emFiltroTagRating');
  if (tag) {{
    let tagHtml = '';
    if (_ratingFilter.classe) tagHtml += `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(182,157,116,.12);border:1px solid rgba(182,157,116,.4);border-radius:12px;padding:2px 10px 2px 8px;font-size:10px;font-weight:600;color:#b69d74;margin-left:8px;cursor:pointer" onclick="_clearRatingFiltro()">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/></svg>
        Classe: ${{_ratingFilter.classe}}&nbsp;<span style="font-size:13px;line-height:1;opacity:.7">×</span></span>`;
    if (_ratingFilter.ratingMkt) tagHtml += `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.3);border-radius:12px;padding:2px 10px 2px 8px;font-size:10px;font-weight:600;color:var(--teal);margin-left:8px;cursor:pointer" onclick="_clearRatingFiltro()">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/></svg>
        Rating Mkt: ${{_ratingFilter.ratingMkt}}&nbsp;<span style="font-size:13px;line-height:1;opacity:.7">×</span></span>`;
    if (_ratingFilter.ratingDouro) tagHtml += `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(182,157,116,.12);border:1px solid rgba(182,157,116,.4);border-radius:12px;padding:2px 10px 2px 8px;font-size:10px;font-weight:600;color:#b69d74;margin-left:8px;cursor:pointer" onclick="_clearRatingFiltro()">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/></svg>
        Rating Douro: ${{_ratingFilter.ratingDouro}}&nbsp;<span style="font-size:13px;line-height:1;opacity:.7">×</span></span>`;
    tag.innerHTML = tagHtml;
  }}
  const hasFilter = _ratingFilter.classe || _ratingFilter.ratingMkt || _ratingFilter.ratingDouro;
  document.getElementById('countAtivosRating').textContent =
    hasFilter ? `— ${{source.length}} posição(ões) · ${{_cachedAtivos.length}} total` : `— ${{source.length}} de ${{_cachedAtivos.length}} posições`;
  document.getElementById('tbodyAtivosRating').innerHTML = source
    .map(a => `<tr>
      <td class="td-muted">${{a.carteira||'—'}}</td>
      <td style="font-weight:700">${{a.ticker||'—'}}</td>
      <td>${{a.emissor||'—'}}</td>
      <td class="td-muted">${{a.setor||'—'}}</td>
      <td style="font-family:var(--mono)">${{fmtBRL(a.saldo)}}</td>
      <td style="font-family:var(--mono)">${{_cachedTotalCred>0?(a.saldo/_cachedTotalCred*100).toFixed(2):0}}%</td>
      <td style="font-family:var(--mono)">${{_cachedPLFilt>0?(a.saldo/_cachedPLFilt*100).toFixed(2):0}}%</td>
      <td style="font-family:var(--mono)">${{a.duration?Number(a.duration).toFixed(1)+'a':'—'}}</td>
      <td class="td-muted">${{a.classe||'—'}}</td>
      <td>${{badgeRating(a['Rating base S&P'])}}</td>
      <td>${{badgeRating(a['Rating Douro'])}}</td>
      <td>${{badgeStatus(a.Status)}}</td>
    </tr>`).join('');
}}

function _clearRatingFiltro() {{
  _ratingFilter = {{ classe: null, ratingMkt: null, ratingDouro: null }};
  ['chartClasse', 'chartRatingMkt', 'chartRatingDouro'].forEach(id => {{
    const chart = Chart.getChart(id);
    if (chart) {{
      chart.data.datasets[0].backgroundColor = chart.data.labels.map((_,i) => COLORS[i%COLORS.length] + 'ee');
      chart.update('none');
    }}
  }});
  _renderTbodyAtivosRating();
}}

function _clearEmFiltroBar() {{
  _emFiltroBar = null;
  const chart = Chart.getChart('chartEmissor');
  if (chart) {{
    chart.data.datasets[0].backgroundColor = chart.data.labels.map(l => getCorStatus(l)+'cc');
    chart.data.datasets[0].borderColor     = chart.data.labels.map(l => getCorStatus(l));
    chart.update('none');
  }}
  _renderTbodyAtivos();
  _renderTbodyAtivosRating();
}}

function _clearSetorFiltro() {{
  _setorFiltroDonut = null;
  const donut = Chart.getChart('chartSetor');
  if (donut) {{
    const orig = donut.data.labels.map((_,i) => COLORS[i%COLORS.length]+'ee');
    donut.data.datasets[0].backgroundColor = orig;
    donut.data.datasets[0].borderWidth = 2;
    donut.update('none');
  }}
  _renderBarEmissor();
  _renderTbodyAtivos();
  _renderTbodyAtivosRating();
}}

function _renderBarEmissor() {{
  const src = _setorFiltroDonut
    ? _cachedAtivos.filter(a => (a.setor||'N/D') === _setorFiltroDonut)
    : _cachedAtivos;
  const byE = {{}};
  src.forEach(a => {{ const em = a.emissor||'Sem emissor'; byE[em]=(byE[em]||0)+(a.saldo||0); }});
  const emSort = Object.entries(byE).sort((a,b)=>b[1]-a[1]);
  const chart = Chart.getChart('chartEmissor');
  if (!chart) return;
  chart.data.labels = emSort.map(e=>e[0]);
  chart.data.datasets[0].data = emSort.map(e=>+((e[1]/1e6).toFixed(2)));
  chart.data.datasets[0].backgroundColor = emSort.map(e=>getCorStatus(e[0])+'cc');
  chart.data.datasets[0].borderColor = emSort.map(e=>getCorStatus(e[0]));
  chart.update('none');
  _emFiltroBar = null;
}}

function homeDiveEmp(empresa) {{
  const navEl = document.querySelector('.nav-item[onclick*="fundamentos"]');
  showPage('fundamentos', navEl);
  if (navEl) navEl.classList.add('active');
  requestAnimationFrame(() => {{
    setTimeout(() => {{
      const sel = document.getElementById('fundEmpSel');
      if (!sel) return;
      const normaliza = s => (s||'').toString().normalize('NFD').replace(/[̀-ͯ]/g,'').trim().toUpperCase();
      const opts = [...sel.options];
      const match = opts.find(o => normaliza(o.text) === normaliza(empresa) || normaliza(o.text).includes(normaliza(empresa).split(' ')[0]));
      if (match) {{ sel.value = match.value; buildFundamentos(); }}
    }}, 100);
  }});
}}

// ── HOME — COMMAND CENTER ─────────────────────────────────────────────────
function buildHome() {{
  const cartSel    = document.getElementById('carteiraFilter').value;
  const ativosBase = cartSel ? ATIVOS.filter(a => a.carteira === cartSel) : ATIVOS;
  const ativos     = ativosBase.filter(a => (a.saldo || 0) > 0);
  const totalCred  = ativos.reduce((s, a) => s + (a.saldo || 0), 0);

  const dataRef = document.getElementById('homeDataRef');
  if (dataRef) dataRef.textContent = 'Dados de ' + new Date().toLocaleDateString('pt-BR', {{ day:'2-digit', month:'short', year:'numeric' }});

  const STATUS_ANALISE  = ['Em análise','Watch','Monitoramento'];
  const STATUS_COBERTOS = ['Aprovado','Reprovado',...STATUS_ANALISE];
  const aprovados    = ativos.filter(a => a.Status === 'Aprovado').reduce((s,a) => s+(a.saldo||0), 0);
  const analise      = ativos.filter(a => STATUS_ANALISE.includes(a.Status)).reduce((s,a) => s+(a.saldo||0), 0);
  const durPond      = totalCred > 0
    ? (ativos.reduce((s,a) => s+(a.duration||0)*(a.saldo||0), 0) / totalCred).toFixed(1) : '—';
  const nEmissores   = new Set(ativos.map(a => a.emissor).filter(Boolean)).size;

  document.getElementById('homeKpiRow').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Crédito Privado</div><div class="kpi-value">${{fmtBRL(totalCred)}}</div><div class="kpi-sub">${{ativos.length}} ativos · ${{nEmissores}} emissores</div></div>
    <div class="kpi-card"><div class="kpi-label">Duration Média</div><div class="kpi-value">${{durPond}}a</div><div class="kpi-sub">Ponderada por saldo</div></div>
    <div class="kpi-card"><div class="kpi-label">Aprovados</div><div class="kpi-value">${{totalCred>0?((aprovados/totalCred)*100).toFixed(1):0}}%</div><span class="kpi-badge green">${{fmtBRL(aprovados)}}</span></div>`;

  const byE = {{}};
  ativos.forEach(a => {{ byE[a.emissor||'S/N'] = (byE[a.emissor||'S/N']||0) + (a.saldo||0); }});
  const emSort   = Object.entries(byE).sort((a,b) => b[1]-a[1]).slice(0, 10);
  const saldosMi = emSort.map(e => +((e[1]/1e6).toFixed(2)));
  const pctPL    = emSort.map(e => PL_TOTAL > 0 ? +((e[1]/PL_TOTAL)*100).toFixed(2) : 0);
  const getCorSt = em => {{
    const match = ATIVOS.find(a => a.emissor === em);
    const st    = (match?.Status||'').trim();
    if (st === 'Aprovado')  return '#00677b';
    if (st === 'Reprovado') return '#d94141';
    return '#b69d74';
  }};
  const wrapHome = document.getElementById('homeChartEmissorWrap');
  if (wrapHome) {{ wrapHome.style.width = '100%'; wrapHome.style.removeProperty('overflow-x'); }}
  const canvasHomeEm = document.getElementById('homeChartEmissor');
  if (canvasHomeEm) {{ canvasHomeEm.removeAttribute('width'); canvasHomeEm.removeAttribute('height'); }}
  mk('homeChartEmissor', {{
    type: 'bar',
    data: {{ labels: emSort.map(e => e[0]), datasets: [{{
      label: 'Saldo (R$ Mi)', data: saldosMi,
      backgroundColor: emSort.map(e => getCorSt(e[0])+'cc'),
      borderColor: emSort.map(e => getCorSt(e[0])),
      borderWidth:1.5, borderRadius:4, yAxisID:'y'
    }}] }},
    options: {{
      ...CHART_DEFAULTS,
      responsive: true, maintainAspectRatio: false,
      layout:{{ padding:{{ bottom:4 }} }}, interaction:{{ mode:'index', intersect:false }},
      plugins: {{ ...CHART_DEFAULTS.plugins, legend:{{ display:false }},
        tooltip:{{ callbacks:{{ label: ctx => 'Saldo: R$ '+ctx.raw+' Mi',
          afterBody: items => items?.length ? '% PL: '+pctPL[items[0].dataIndex]+'%' : '' }} }} }},
      scales: {{
        x: {{ ...CHART_DEFAULTS.scales.x, ticks:{{ color:'#718096', font:{{ size:11, family:"'DM Mono',monospace" }}, maxRotation:0, minRotation:0, autoSkip:false }} }},
        y: {{ ...CHART_DEFAULTS.scales.y, type:'linear', position:'left', beginAtZero:true,
          ticks:{{ ...CHART_DEFAULTS.scales.y.ticks, callback: v => 'R$ '+v+' Mi' }} }}
      }}
    }}
  }});

  const byClasse = {{}};
  ativos.forEach(a => {{ byClasse[a.classe||'Outros'] = (byClasse[a.classe||'Outros']||0)+(a.saldo||0); }});
  const clSort = Object.entries(byClasse).sort((a,b) => b[1]-a[1]);
  mk('homeChartClasse', {{
    type:'doughnut',
    data:{{ labels: clSort.map(e=>e[0]), datasets:[{{
      data: clSort.map(e=>+((e[1]/totalCred)*100).toFixed(1)),
      backgroundColor: clSort.map((_,i)=>COLORS[i%COLORS.length]+'ee'),
      borderColor:'#ffffff', borderWidth:2
    }}] }},
    options:{{ ...DOUGHNUT_OPTS,
      plugins:{{ ...DOUGHNUT_OPTS.plugins, tooltip:{{ callbacks:{{ label: c => {{
        const mi = (clSort[c.dataIndex][1]/1e6).toFixed(2);
        return c.label+': '+c.raw+'% — R$ '+mi+' Mi';
      }} }} }} }}
    }}
  }});

  const top5Corp = RANK_CORP.slice(0,5);
  document.getElementById('homeTop5Corp').innerHTML = top5Corp.map((rankInfo, i) => {{
    const em    = rankInfo.empresa || '—';
    const setor = rankInfo.setor || '—';
    const saldo = ativos.filter(a=>a.emissor===em).reduce((s,a)=>s+(a.saldo||0),0);
    return `<div style="display:flex;flex-direction:column;gap:0;margin-bottom:8px;padding:10px 12px;border-radius:8px;border:1px solid transparent;background:transparent;transition:background .15s;border:1px solid transparent;">
      <div style="display:flex;align-items:center;gap:12px;padding:0;cursor:pointer;transition:background .15s;"
        onmouseover="this.style.background='rgba(0,103,123,.05)';this.parentElement.style.borderColor='rgba(0,103,123,.15)'"
        onmouseout="this.style.background='';this.parentElement.style.borderColor='transparent'"
        onclick="homeSelectEmp('${{em}}')">
        <span class="rank-num">${{i+1}}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{em}}</div>
          <div style="font-size:10px;color:var(--text3);margin-top:2px">${{setor}}</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
          ${{badgeRating(rankInfo.ratingDouro||'—')}}
          ${{badgeStatus(rankInfo.status||'—')}}
          <div style="font-family:var(--mono);font-size:11px;color:var(--text2)">${{saldo>0?fmtBRL(saldo):'—'}}</div>
        </div>
        <div style="font-size:10px;color:var(--teal);font-weight:600;white-space:nowrap">→</div>
      </div>
    </div>`;
  }}).join('');

  const top5Bancos = RANK_BANCOS.slice(0,5);
  document.getElementById('homeTop5Bancos').innerHTML = top5Bancos.map((rankInfo, i) => {{
    const em    = rankInfo.empresa || '—';
    const saldo = ativos.filter(a=>a.emissor===em).reduce((s,a)=>s+(a.saldo||0),0);
    return `<div style="display:flex;flex-direction:column;gap:0;margin-bottom:8px;padding:10px 12px;border-radius:8px;border:1px solid transparent;background:transparent;transition:background .15s;border:1px solid transparent;">
      <div style="display:flex;align-items:center;gap:12px;padding:0;cursor:pointer;transition:background .15s;"
        onmouseover="this.style.background='rgba(0,103,123,.05)';this.parentElement.style.borderColor='rgba(0,103,123,.15)'"
        onmouseout="this.style.background='';this.parentElement.style.borderColor='transparent'"
        onclick="homeSelectBanco('${{em}}')">
        <span class="rank-num">${{i+1}}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{em}}</div>
          <div style="font-size:10px;color:var(--text3);margin-top:2px">${{rankInfo.tipo||'Banco'}}</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
          ${{badgeRating(rankInfo.ratingDouro||'—')}}
          ${{badgeStatus(rankInfo.status||'—')}}
          <div style="font-family:var(--mono);font-size:11px;color:var(--text2)">${{saldo>0?fmtBRL(saldo):'—'}}</div>
        </div>
        <div style="font-size:10px;color:var(--teal);font-weight:600;white-space:nowrap">→</div>
      </div>
    </div>`;
  }}).join('');

  const atvsPerf = Object.keys(PERF_DATA.ativos || {{}});
  if (atvsPerf.length) {{
    const dsPerf = atvsPerf.map((a,i) => ({{
      label: a, data: PERF_DATA.ativos[a].retorno_acum.map(v=>+(v*100).toFixed(2)),
      borderColor: COLORS[i%COLORS.length], backgroundColor:'transparent',
      tension:.3, pointRadius:0, borderWidth:1.8
    }}));
    mk('homeChartPerf', {{
      type:'line',
      data:{{ labels: PERF_DATA.datas, datasets: dsPerf }},
      options:{{
        ...CHART_DEFAULTS,
        ..._CROSSHAIR_OPTS,
        plugins:{{ ...CHART_DEFAULTS.plugins, ..._CROSSHAIR_OPTS.plugins,
          legend:{{ display:true, position:'bottom', labels:{{ color:'#718096', font:{{ size:9 }}, boxWidth:8, padding:10 }} }} }},
        scales:{{
          x:{{ ...CHART_DEFAULTS.scales.x, ticks:{{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:6 }} }},
          y:{{ ...CHART_DEFAULTS.scales.y, ticks:{{ ...CHART_DEFAULTS.scales.y.ticks, callback: v=>v.toFixed(1)+'%' }} }}
        }}
      }}
    }});
  }}
}}

// ── COMPOSIÇÃO ─────────────────────────────────────────────────────────────
function buildComposicao() {{
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
    <div class="kpi-card"><div class="kpi-label">Saldo Crédito Privado</div><div class="kpi-value">${{fmtBRL(totalCredito)}}</div><div class="kpi-sub">${{ativos.length}} posições · ${{uniqueTickers}} tickers</div></div>
    <div class="kpi-card"><div class="kpi-label">% do PL Total</div><div class="kpi-value">${{plFiltrado>0?(totalCredito/plFiltrado*100).toFixed(1):0}}%</div><div class="kpi-sub">PL: ${{fmtBRL(plFiltrado)}}</div></div>
    <div class="kpi-card"><div class="kpi-label">Aprovados</div><div class="kpi-value">${{totalCredito>0?(aprovados/totalCredito*100).toFixed(1):0}}%</div><span class="kpi-badge green">${{fmtBRL(aprovados)}}</span></div>
    <div class="kpi-card"><div class="kpi-label">Em Análise / Watch</div><div class="kpi-value">${{totalCredito>0?(analise/totalCredito*100).toFixed(1):0}}%</div><span class="kpi-badge gold">${{fmtBRL(analise)}}</span></div>
    <div class="kpi-card"><div class="kpi-label">Reprovados</div><div class="kpi-value">${{totalCredito>0?(reprovados/totalCredito*100).toFixed(1):0}}%</div><span class="kpi-badge red">${{fmtBRL(reprovados)}}</span></div>
    <div class="kpi-card"><div class="kpi-label">Sem Cobertura</div><div class="kpi-value">${{totalCredito>0?(semCobertura/totalCredito*100).toFixed(1):0}}%</div><span class="kpi-badge" style="background:rgba(113,128,150,.12);color:var(--text3)">${{fmtBRL(semCobertura)}}</span></div>
    <div class="kpi-card"><div class="kpi-label">Duration Média</div><div class="kpi-value">${{(ativos.reduce((s,a)=>s+((a.duration||0)*(a.saldo||0)),0)/Math.max(totalCredito,1)).toFixed(1)}}a</div><div class="kpi-sub">Ponderada por saldo</div></div>`;

  const byE = {{}};
  ativos.forEach(a => {{
    const em = a.emissor || 'Sem emissor';
    byE[em] = (byE[em]||0) + (a.saldo||0);
  }});
  const emSort   = Object.entries(byE).sort((a,b) => b[1]-a[1]);
  const emSort10 = emSort.slice(0, 10);
  const saldosMi = emSort10.map(e => +((e[1]/1e6).toFixed(2)));
  const pctPL    = emSort10.map(e => plFiltrado > 0 ? +((e[1]/plFiltrado)*100).toFixed(2) : 0);

  const chipVer = document.getElementById('emissorVerTodosChip');
  if (chipVer) {{
    if (emSort.length > 10) {{
      chipVer.style.display = 'block';
      chipVer.textContent = `+ ${{emSort.length - 10}} outros emissores — ver todos na tabela ↓`;
    }} else {{ chipVer.style.display = 'none'; }}
  }}

const BAR_MIN_PX = 80;
const CHART_H    = 320;
const larguraGrafico = Math.max(emSort10.length * BAR_MIN_PX, 600);

const inner = document.getElementById('chartEmissorWrap');
if (inner) {{
  inner.style.width    = larguraGrafico + 'px';
  inner.style.maxWidth = 'none';
  const chartDiv = inner.querySelector('div');
  if (chartDiv) {{ chartDiv.style.width = larguraGrafico + 'px'; chartDiv.style.height = CHART_H + 'px'; }}
}}
const canvasEmissor = document.getElementById('chartEmissor');
if (canvasEmissor) {{ canvasEmissor.width = larguraGrafico; canvasEmissor.height = CHART_H; }}

  const legendaStatus = [
    {{ label:'Aprovado',   cor:'#00677b' }},
    {{ label:'Em análise', cor:'#b69d74' }},
    {{ label:'Reprovado',  cor:'#d94141' }},
  ];

  mk('chartEmissor', {{
    type: 'bar',
    data: {{
      labels: emSort10.map(e => e[0]),
      datasets: [
        {{
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
        }},
        ...legendaStatus.map(ls => ({{
          type:            'bar',
          label:           ls.label,
          data:            [],
          backgroundColor: ls.cor + 'cc',
          borderColor:     ls.cor,
          borderWidth:     1.5,
          yAxisID:         'y',
          order:           2
        }}))
      ]
    }},
    options: {{
      ...CHART_DEFAULTS,
      responsive: false,
      maintainAspectRatio: false,
      layout: {{ padding: {{ bottom: 8 }} }},
      interaction: {{ mode:'index', intersect:false }},
      onClick: (evt, elements) => {{
        if (!elements || !elements.length) return;
        const clickedLabel = emSort10[elements[0].index][0];
        _emFiltroBar = _emFiltroBar === clickedLabel ? null : clickedLabel;
        const chart = Chart.getChart('chartEmissor');
        if (chart) {{
          chart.data.datasets[0].backgroundColor = emSort10.map(e =>
            !_emFiltroBar || e[0] === _emFiltroBar ? getCorStatus(e[0])+'cc' : getCorStatus(e[0])+'33'
          );
          chart.data.datasets[0].borderColor = emSort10.map(e =>
            !_emFiltroBar || e[0] === _emFiltroBar ? getCorStatus(e[0]) : getCorStatus(e[0])+'55'
          );
          chart.update('none');
        }}
        _renderTbodyAtivos();
      }},
      plugins: {{
        ...CHART_DEFAULTS.plugins,
        legend: {{
          display:  true,
          position: 'top',
          labels: {{
            color:    '#718096',
            font:     {{ size:11, family:"'Montserrat', sans-serif" }},
            boxWidth: 12,
            padding:  16,
            filter:   (item) => item.text !== 'Saldo (R$ Mi)'
          }}
        }},
        tooltip: {{
          filter: (ctx) => ctx.datasetIndex === 0,
          callbacks: {{
            label:     ctx => `Saldo: R$${{ctx.raw}} Mi`,
            afterBody: items => {{
              if (!items || !items.length) return '';
              const idx = items[0].dataIndex;
              const pct = pctPL[idx];
              return pct != null ? `% PL Total: ${{pct}}%` : '';
            }}
          }}
        }}
      }},
      scales: {{
        x: {{
          ...CHART_DEFAULTS.scales.x,
          ticks: {{
            color:       '#718096',
            font:        {{ size:9, family:"'DM Mono', monospace" }},
            maxRotation: 45,
            minRotation: 30,
            autoSkip:    false
          }}
        }},
        y: {{
          ...CHART_DEFAULTS.scales.y,
          type:        'linear',
          position:    'left',
          beginAtZero: true,
          title: {{ display:true, text:'Saldo (R$ Mi)', color:'#718096', font:{{ size:10 }} }},
          ticks: {{ ...CHART_DEFAULTS.scales.y.ticks, callback: v => `R$ ${{v}} Mi` }}
        }},
        y2: {{
          type:        'linear',
          position:    'right',
          beginAtZero: true,
          grid:        {{ drawOnChartArea: false }},
          title: {{ display:true, text:'% PL Total', color:'#718096', font:{{ size:10 }} }},
          ticks: {{ color:'#718096', font:{{ size:10, family:"'DM Mono', monospace" }}, callback: v => v + '%' }}
        }}
      }}
    }}
  }});

  // Setor doughnut
  const byS = {{}};
  ativos.forEach(a => {{ byS[a.setor||'N/D'] = (byS[a.setor||'N/D']||0) + (a.saldo||0); }});
  const sSort = Object.entries(byS).sort((a,b) => b[1]-a[1]);
  mk('chartSetor', {{
    type: 'doughnut',
    data: {{
      labels: sSort.map(e => e[0]),
      datasets: [{{
        data:            sSort.map(e => +(e[1]/totalCredito*100).toFixed(1)),
        backgroundColor: sSort.map((_,i) => COLORS[i%COLORS.length]+'ee'),
        borderColor:     '#ffffff',
        borderWidth:     2
      }}]
    }},
    options: {{
      ...DOUGHNUT_OPTS,
      onClick: (evt, elements) => {{
        const chart = Chart.getChart('chartSetor');
        if (!chart || !elements || !elements.length) {{
          _setorFiltroDonut = null;
          if (chart) {{ chart.data.datasets[0].backgroundColor = sSort.map((_,i)=>COLORS[i%COLORS.length]+'ee'); chart.data.datasets[0].borderWidth=2; chart.update('none'); }}
          _renderBarEmissor(); _renderTbodyAtivos(); return;
        }}
        const idx = elements[0].index;
        const setor = sSort[idx][0];
        if (_setorFiltroDonut === setor) {{
          _setorFiltroDonut = null;
          chart.data.datasets[0].backgroundColor = sSort.map((_,i)=>COLORS[i%COLORS.length]+'ee');
          chart.data.datasets[0].borderWidth = 2;
        }} else {{
          _setorFiltroDonut = setor;
          chart.data.datasets[0].backgroundColor = sSort.map((e,i)=>
            e[0]===setor ? '#b69d74ee' : COLORS[i%COLORS.length]+'44'
          );
          chart.data.datasets[0].borderWidth = sSort.map(e=>e[0]===setor?3:1);
        }}
        chart.update('none');
        _emFiltroBar = null;
        _renderBarEmissor();
        _renderTbodyAtivos();
      }},
      plugins: {{ ...DOUGHNUT_OPTS.plugins, tooltip: {{ callbacks: {{ label: c => {{
        const mi = (sSort[c.dataIndex][1]/1e6).toFixed(2);
        return `${{c.label}}: ${{c.raw}}% — R$ ${{mi}} Mi`;
      }} }} }} }}
    }}
  }});

  _renderTbodyAtivos();
}}

// ── RATING ─────────────────────────────────────────────────────────────────
function buildRating() {{
  const carteiraSelecionada = document.getElementById('carteiraFilter')?.value || '';
  const plFiltrado = carteiraSelecionada ? (PL_POR_CARTEIRA[carteiraSelecionada] || 0) : PL_TOTAL;
  const ativos       = getFiltered();
  const totalCredito = ativos.reduce((s,a) => s+(a.saldo||0), 0);
  _cachedAtivos    = ativos;
  _cachedTotalCred = totalCredito;
  _cachedPLFilt    = plFiltrado;
  _ratingFilter    = {{ classe: null, ratingMkt: null, ratingDouro: null }};
  const byClasse={{}}, byRMkt={{}}, byRD={{}};
  ativos.forEach(a => {{
    byClasse[a.classe||'Outros']             = (byClasse[a.classe||'Outros']||0)             + (a.saldo||0);
    byRMkt[a['Rating base S&P']||'N/D']      = (byRMkt[a['Rating base S&P']||'N/D']||0)      + (a.saldo||0);
    byRD[a['Rating Douro']||'N/D']           = (byRD[a['Rating Douro']||'N/D']||0)           + (a.saldo||0);
  }});
  const donut = (id, obj) => {{
    const e = Object.entries(obj).sort((a,b) => b[1]-a[1]);
    mk(id, {{
      type:'doughnut',
      data:{{ labels:e.map(x=>x[0]), datasets:[{{ data:e.map(x=>+(x[1]/totalCredito*100).toFixed(1)), backgroundColor:e.map((_,i)=>COLORS[i%COLORS.length]+'ee'), borderColor:'#ffffff', borderWidth:2 }}]}},
      options:{{ ...DOUGHNUT_OPTS,
        onClick: (evt, elements) => {{
          const chart = Chart.getChart(id);
          if (!chart) return;
          if (!elements || !elements.length) {{
            _clearRatingFiltro();
            return;
          }}
          const idx = elements[0].index;
          const label = e[idx][0];
          const selected = id === 'chartClasse' ? _ratingFilter.classe : id === 'chartRatingMkt' ? _ratingFilter.ratingMkt : _ratingFilter.ratingDouro;
          const same = selected === label;
          _ratingFilter = {{ classe:null, ratingMkt:null, ratingDouro:null }};
          if (!same) {{
            if (id === 'chartClasse') _ratingFilter.classe = label;
            if (id === 'chartRatingMkt') _ratingFilter.ratingMkt = label;
            if (id === 'chartRatingDouro') _ratingFilter.ratingDouro = label;
          }}
          chart.data.datasets[0].backgroundColor = e.map((item,i) => {{
            if (same) return COLORS[i%COLORS.length]+'ee';
            return item[0] === label ? COLORS[i%COLORS.length]+'ee' : COLORS[i%COLORS.length]+'44';
          }});
          chart.update('none');
          _renderTbodyAtivosRating();
        }},
        plugins:{{ ...DOUGHNUT_OPTS.plugins, tooltip:{{ callbacks:{{ label: c => {{
          const mi = (e[c.dataIndex][1]/1e6).toFixed(2);
          return `${{c.label}}: ${{c.raw}}% — R$ ${{mi}} Mi`;
        }} }} }} }}
      }}
    }});
  }};
  donut('chartClasse',      byClasse);
  donut('chartRatingMkt',   byRMkt);
  donut('chartRatingDouro', byRD);
  _renderTbodyAtivosRating();

}}
// ── DADOS FINANCEIROS ─────────────────────────────────────────────────────
const finSelecionadas = new Set();
let finInicializado = false;
let _finAllDates = [];
let _finDateMin = 0;
let _finDateMax = Infinity;

function finRangeInit() {{
  const allTs = [];
  Object.values(FIN_SERIES).forEach(d => {{
    (d.datas || []).forEach(dt => {{
      const ts = parseBRDate(dt);
      if (ts) allTs.push(ts);
    }});
  }});
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
}}

function finRangeUpdate(ev) {{
  const rMin = document.getElementById('finRangeMin');
  const rMax = document.getElementById('finRangeMax');
  if (!rMin || !rMax) return;
  let vMin = parseInt(rMin.value), vMax = parseInt(rMax.value);
  if (vMin >= vMax) {{
    if (ev && ev.target === rMin) {{ rMin.value = Math.max(0, vMax - 1); vMin = parseInt(rMin.value); }}
    else {{ rMax.value = Math.min(parseInt(rMax.max), vMin + 1); vMax = parseInt(rMax.value); }}
  }}
  _finDateMin = _finAllDates[vMin] || 0;
  _finDateMax = _finAllDates[vMax] || Infinity;
  _finRangeLabel(); _finRangeFill();
  buildFinanceiros();
}}

function _finRangeLabel() {{
  const label = document.getElementById('finDateRangeLabel');
  if (!label || !_finAllDates.length) return;
  const rMin = document.getElementById('finRangeMin');
  const rMax = document.getElementById('finRangeMax');
  const vMin = parseInt(rMin?.value || 0);
  const vMax = parseInt(rMax?.value || _finAllDates.length - 1);
  const fmt = ts => new Date(ts).getFullYear();
  label.textContent = fmt(_finAllDates[vMin]) + ' – ' + fmt(_finAllDates[vMax]);
}}

function _finRangeFill() {{
  const rMin = document.getElementById('finRangeMin');
  const rMax = document.getElementById('finRangeMax');
  const fill = document.getElementById('finRangeFill');
  if (!fill || !rMin || !rMax) return;
  const total = parseInt(rMin.max) || 1;
  const l = (parseInt(rMin.value) / total) * 100;
  const r = (parseInt(rMax.value) / total) * 100;
  fill.style.left = l + '%';
  fill.style.width = (r - l) + '%';
}}

// ── FUNDAMENTOS DATE RANGE ──────────────────────────────────────────────────
let _fundAllDates = [];
let _fundDateMin = 0;
let _fundDateMax = Infinity;

function fundRangeInit() {{
  const allTs = [];
  Object.values(FIN_SERIES).forEach(d => {{
    (d.datas || []).forEach(dt => {{
      const ts = parseBRDate(dt);
      if (ts) allTs.push(ts);
    }});
  }});
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
}}

function fundRangeUpdate(ev) {{
  const rMin = document.getElementById('fundRangeMin');
  const rMax = document.getElementById('fundRangeMax');
  if (!rMin || !rMax) return;
  let vMin = parseInt(rMin.value), vMax = parseInt(rMax.value);
  if (vMin >= vMax) {{
    if (ev && ev.target === rMin) {{ rMin.value = Math.max(0, vMax - 1); vMin = parseInt(rMin.value); }}
    else {{ rMax.value = Math.min(parseInt(rMax.max), vMin + 1); vMax = parseInt(rMax.value); }}
  }}
  _fundDateMin = _fundAllDates[vMin] || 0;
  _fundDateMax = _fundAllDates[vMax] || Infinity;
  _fundRangeLabel(); _fundRangeFill();
  buildFundamentos();
}}

function _fundRangeLabel() {{
  const label = document.getElementById('fundDateRangeLabel');
  if (!label || !_fundAllDates.length) return;
  const rMin = document.getElementById('fundRangeMin');
  const rMax = document.getElementById('fundRangeMax');
  const vMin = parseInt(rMin?.value || 0);
  const vMax = parseInt(rMax?.value || _fundAllDates.length - 1);
  const fmt = ts => new Date(ts).getFullYear();
  label.textContent = fmt(_fundAllDates[vMin]) + ' – ' + fmt(_fundAllDates[vMax]);
}}

function _fundRangeFill() {{
  const rMin = document.getElementById('fundRangeMin');
  const rMax = document.getElementById('fundRangeMax');
  const fill = document.getElementById('fundRangeFill');
  if (!fill || !rMin || !rMax) return;
  const total = parseInt(rMin.max) || 1;
  const l = (parseInt(rMin.value) / total) * 100;
  const r = (parseInt(rMax.value) / total) * 100;
  fill.style.left = l + '%';
  fill.style.width = (r - l) + '%';
}}

function finInitSels() {{
  if (finInicializado) return;
  finInicializado = true;
  const selSetor = document.getElementById('setorFinSel');
  selSetor.innerHTML = '<option value="">Todos os Setores</option>';
  setores.forEach(s => {{
    const o = document.createElement('option');
    o.value = s; o.textContent = s;
    selSetor.appendChild(o);
  }});
  finRangeInit();
  finRenderEmpList();
}}
function parseBRDate(str) {{
  if (!str || typeof str !== 'string') return null;
  if (str.includes('-')) {{
    const parts = str.split('T')[0].split('-').map(Number);
    if (parts.length !== 3 || !parts[0] || !parts[1] || !parts[2]) return null;
    const ts = new Date(parts[0], parts[1]-1, parts[2]).getTime();
    return isNaN(ts) ? null : ts;
  }}
  const parts = str.split('/');
  if (parts.length !== 3) return null;
  const [d, m, y] = parts.map(Number);
  if (!d || !m || !y) return null;
  const ts = new Date(y, m-1, d).getTime();
  return isNaN(ts) ? null : ts;
}}
function finGetEmpsDisp() {{
  const setor = document.getElementById('setorFinSel')?.value || '';
  return Object.keys(FIN_SERIES).filter(e => {{
    if (setor && (FIN_SERIES[e]?.setor || 'Não Informado') !== setor) return false;
    return true;
  }});
}}
function finRenderEmpList() {{
  const disponiveis = finGetEmpsDisp();
  const countEl = document.getElementById('finEmpCount');
  if (countEl) countEl.textContent = `(${{disponiveis.length}})`;
  const wrap = document.getElementById('finEmpList');
  if (!wrap) return;
  wrap.innerHTML = '';
  disponiveis.sort().forEach(e => {{
    const sel = finSelecionadas.has(e);
    const btn = document.createElement('button');
    btn.textContent = e;
    btn.style.cssText = `padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600;transition:all .15s;border:1px solid ${{sel?'var(--teal)':'var(--border)'}};background:${{sel?'rgba(0,103,123,.12)':'var(--surface2)'}};color:${{sel?'var(--teal)':'var(--text3)'}};`;
    btn.onclick = () => finToggle(e);
    wrap.appendChild(btn);
  }});
  finRenderChips();
}}
function finToggle(e) {{
  if (finSelecionadas.has(e)) finSelecionadas.delete(e); else finSelecionadas.add(e);
  finRenderEmpList(); buildFinanceiros();
}}
function finRenderChips() {{
  const wrap = document.getElementById('finChipsWrap');
  if (!wrap) return;
  if (!finSelecionadas.size) {{ wrap.innerHTML = '<span style="color:var(--text3);font-size:11px">Nenhuma selecionada</span>'; return; }}
  wrap.innerHTML = [...finSelecionadas].map(e => `<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.25);border-radius:4px;padding:3px 8px;font-size:10px;font-weight:600;color:var(--teal)">${{e}}<span onclick="finToggle('${{e}}')" style="cursor:pointer;opacity:.7;font-size:12px;line-height:1">×</span></span>`).join('');
}}
function finAddAll()    {{ finGetEmpsDisp().forEach(e => finSelecionadas.add(e)); finRenderEmpList(); buildFinanceiros(); }}
function finRemoveAll() {{ finSelecionadas.clear(); finRenderEmpList(); buildFinanceiros(); }}
function finOnSetorChange() {{ finRenderEmpList(); }}
function buildFinanceiros() {{
  if (!finInicializado) {{ finInitSels(); finInicializado = true; }}
  finRenderEmpList();
  const ind      = document.getElementById('indFinSel').value;
  const empresas = [...finSelecionadas];
  if (!empresas.length) {{
    if (activeCharts['chartFinMain']) {{ activeCharts['chartFinMain'].destroy(); delete activeCharts['chartFinMain']; }}
    _finPainelRender();
    return;
  }}
  document.getElementById('finTitle').textContent = ind.replace('_',' ').replace('TTM','TTM (R$ Mi)');
  const isPct = ['Mg EBITDA 36M','Mg Bruta 36M','Estrutura de Capital (D/D+E)','ROE','ROA','ROIC'].includes(ind);
  const isVal = ['Receita_TTM','EBITDA_TTM','FCF_TTM'].includes(ind);
  const datasets = empresas.map((emp, i) => {{
    const d = FIN_SERIES[emp];
    if (!d) return null;
    const raw   = d[ind] || [];
    const datas = d.datas || [];
    const dados = datas.map((dt, j) => {{
      const v = raw[j];
      if (v == null || v !== v) return null;
      const dtParsed = parseBRDate(dt);
      if (!dtParsed) return null;
      if (dtParsed < _finDateMin || dtParsed > _finDateMax) return null;
      const yv = isVal ? +(v/1e6).toFixed(1) : v;
      if (yv !== yv) return null;
      return {{ x: dtParsed, y: yv }};
    }}).filter(p => p !== null);
    return {{ label:emp, data:dados, borderColor:COLORS[i%COLORS.length], backgroundColor:'transparent', tension:0.3, fill:false, pointRadius:empresas.length<=2?3:0, pointHoverRadius:5, borderWidth:empresas.length<=5?2:1.3 }};
  }}).filter(Boolean);
  const yUnit   = isPct ? '%' : isVal ? 'R$ Mi' : 'x';
  const yTickCb = isPct ? (v=>(v*100).toFixed(1)+'%') : isVal ? (v=>'R$ '+v.toFixed(0)+' Mi') : (v=>Number(v).toFixed(2)+'x');
  const yTicks  = {{ color:'#718096', font:{{size:10,family:"'DM Mono',monospace"}}, callback: yTickCb }};
  mk('chartFinMain', {{
    type: 'line', data: {{ datasets }},
    options: {{
      ...CHART_DEFAULTS, maintainAspectRatio:false, parsing:false,
      interaction: {{ mode:'nearest', intersect:false }},
      plugins: {{
        ...CHART_DEFAULTS.plugins,
        legend: {{ display:true, position:'bottom', labels:{{ color:'#718096', font:{{size:10}}, boxWidth:10 }} }},
        tooltip: {{ callbacks: {{ label: ctx => {{
          const v = ctx.parsed.y;
          if (v == null) return null;
          if (isPct) return ctx.dataset.label+': '+(v*100).toFixed(1)+'%';
          if (isVal) return ctx.dataset.label+': R$ '+v.toFixed(1)+' Mi';
          return ctx.dataset.label+': '+v.toFixed(2)+'x';
        }} }} }}
      }},
      scales: {{
        x: {{ type:'time', time:{{ unit:'month', displayFormats:{{ month:'MMM/yy' }}, tooltipFormat:'dd/MM/yyyy' }}, ...CHART_DEFAULTS.scales.x, ticks:{{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:12 }} }},
        y: {{ ...CHART_DEFAULTS.scales.y, ticks:yTicks, title:{{ display:true, text:yUnit, color:'#718096', font:{{size:10}} }} }}
      }}
    }}
  }});
  const last = arr => arr?.length ? arr.slice().reverse().find(v => v != null) : null;
  const gc   = (v, g, w) => v == null ? '' : v >= g ? 'col-good' : v >= w ? 'col-warn' : 'col-bad';
  _finPainelRender();
}}

let _fpSortCol='empresa', _fpSortAsc=true;
function _finPainelSort(col){{if(_fpSortCol===col)_fpSortAsc=!_fpSortAsc;else{{_fpSortCol=col;_fpSortAsc=(col==='empresa'||col==='setor');}}_finPainelRender();}}
function _finPainelRender(){{
  const q=(document.getElementById('finPainelSearch')?.value||'').toLowerCase();
  const last=arr=>arr?.length?arr.slice().reverse().find(v=>v!=null):null;
  const getRow=nome=>{{
    const fd=FIN_SERIES[nome]; if(!fd) return null;
    return {{nome, setor:fd.setor||'Não Informado',
      rec:last(fd['Receita_TTM']), ebt:last(fd['EBITDA_TTM']),
      mg:last(fd['Mg EBITDA 36M']), dl:last(fd['DivLiquida/EBITDA']),
      ec:last(fd['Estrutura de Capital (D/D+E)']), roe:last(fd['ROE']),
      lc:last(fd['Liquidez Corrente'])}};
  }};
  let src=Object.keys(FIN_SERIES).map(getRow).filter(Boolean);
  if(q) src=src.filter(r=>[r.nome,r.setor].some(f=>f&&f.toLowerCase().includes(q)));
  const dir=_fpSortAsc?1:-1;
  const cmpStr=(a,b)=>(a||'').localeCompare(b||'','pt-BR');
  const cmpNum=(a,b)=>(a??-Infinity)-(b??-Infinity);
  src=[...src].sort((a,b)=>{{
    switch(_fpSortCol){{
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
    }}
  }});
  ['empresa','setor','rec','ebt','mg','dl','ec','roe','lc'].forEach(col=>{{
    const el=document.getElementById('_fpsh_'+col);if(!el)return;
    if(col===_fpSortCol){{el.textContent=_fpSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}}
    else{{el.textContent='↕';el.style.opacity='.4';el.style.color='';}}
  }});
  document.getElementById('tbodyFin').innerHTML=src.map(r=>`<tr>
    <td style="font-weight:600">${{r.nome}}</td>
    <td class="td-muted">${{r.setor}}</td>
    <td style="font-family:var(--mono)">${{r.rec!=null?fmtBRL(r.rec):'—'}}</td>
    <td style="font-family:var(--mono)">${{r.ebt!=null?fmtBRL(r.ebt):'—'}}</td>
    <td class="${{gc(r.mg,.35,.2)}}" style="font-family:var(--mono)">${{r.mg!=null?fmtPct(r.mg):'—'}}</td>
    <td class="${{r.dl!=null?(r.dl<3?'col-good':r.dl<5?'col-warn':'col-bad'):''}}" style="font-family:var(--mono)">${{r.dl!=null?fmtX(r.dl):'—'}}</td>
    <td class="${{gc(-((r.ec||0)),-.6,-.75)}}" style="font-family:var(--mono)">${{r.ec!=null?fmtPct(r.ec):'—'}}</td>
    <td class="${{gc(r.roe,.1,.05)}}" style="font-family:var(--mono)">${{r.roe!=null?fmtPct(r.roe):'—'}}</td>
    <td class="${{gc(r.lc,1.2,.9)}}" style="font-family:var(--mono)">${{r.lc!=null?fmtX(r.lc):'—'}}</td>
  </tr>`).join('');
}}
// ── FUNDAMENTOS ────────────────────────────────────────────────────────────
let _fundIniciado = false;

function fundFilterList() {{
  const q  = (document.getElementById('fundSearch')?.value || '').toLowerCase();
  const sel = document.getElementById('fundEmpSel');
  if (!sel) return;
  [...sel.options].forEach(o => {{
    o.hidden = q ? !o.text.toLowerCase().includes(q) : false;
  }});
  // Select first visible if current selection is hidden
  const cur = sel.options[sel.selectedIndex];
  if (cur && cur.hidden) {{
    const first = [...sel.options].find(o => !o.hidden);
    if (first) {{ sel.value = first.value; buildFundamentos(); }}
  }}
}}

function _fundInitSel() {{
  const sel = document.getElementById('fundEmpSel');
  if (!sel) return;
  const empresas = Object.keys(FIN_SERIES).sort();
  sel.innerHTML = empresas.map(e => `<option value="${{e}}">${{e}}</option>`).join('');
}}

function buildFundamentos() {{
  if (!_fundIniciado) {{ _fundInitSel(); _fundIniciado = true; fundRangeInit(); }}
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
  const labels = filtDatas.map(dt => {{
    const p = parseBRDate(dt);
    return p ? new Date(p).toLocaleDateString('pt-BR',{{month:'short',year:'2-digit'}}) : dt;
  }});
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

  const LOPT = {{
    type:'line',
    options: {{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction: {{ mode:'index', intersect:false }},
      plugins: {{
        ...CHART_DEFAULTS.plugins,
        legend: {{ display:true, position:'bottom', labels:{{ color:'#718096', font:{{size:10}}, boxWidth:10 }} }}
      }}
    }}
  }};

  // ── Chart 1: P&L (LTM) ──
  const recMi  = safe(filterArr(d['Receita_TTM'])).map(mi);
  const ebtMi  = safe(filterArr(d['EBITDA_TTM'])).map(mi);
  const llMi   = safe(filterArr(d['Lucro Liquido_TTM'])).map(mi);
  mk('fundChartPL', {{
    type:'bar',
    data:{{ labels,
      datasets:[
        {{ label:'Receita TTM',      data:recMi, type:'bar',  backgroundColor:'rgba(182,157,116,.45)', borderColor:'#b69d74', borderWidth:1, order:2 }},
        {{ label:'EBITDA TTM',       data:ebtMi, type:'bar',  backgroundColor:'rgba(0,103,123,.5)',    borderColor:'#00677b', borderWidth:1, order:3 }},
        {{ label:'Lucro Líquido TTM',data:llMi,  type:'line', borderColor:'#2fa874', backgroundColor:'transparent', tension:0.3, pointRadius:3, pointHoverRadius:5, borderWidth:2, order:1 }}
      ]
    }},
    options:{{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        ...CHART_DEFAULTS.plugins,
        legend:{{display:true,position:'bottom',labels:{{color:'#718096',font:{{size:10}},boxWidth:10}}}},
        tooltip:{{callbacks:{{label:ctx => ctx.dataset.label+': R$ '+Number(ctx.parsed.y||0).toFixed(1)+' Mi'}}}}
      }},
      scales:{{
        x:{{ ...CHART_DEFAULTS.scales.x, ticks:{{...CHART_DEFAULTS.scales.x.ticks,maxRotation:45}} }},
        y:{{ ...CHART_DEFAULTS.scales.y, title:{{display:true,text:'R$ Mi',color:'#718096',font:{{size:10}}}},
             ticks:{{...CHART_DEFAULTS.scales.y.ticks,callback:v=>'R$ '+Number(v).toFixed(0)+' Mi'}} }}
      }}
    }}
  }});

  // ── Chart 2: Margens (LTM) ──
  const mgB  = safe(filterArr(d['Mg Bruta TTM']  || d['Mg Bruta 36M'])).map(pct);
  const mgE  = safe(filterArr(d['Mg EBITDA TTM'] || d['Mg EBITDA 36M'])).map(pct);
  const mgL  = safe(filterArr(d['Mg Liquida TTM'])).map(pct);
  mk('fundChartMg', {{
    type:'line',
    data:{{ labels,
      datasets:[
        {{ label:'Margem Bruta',   data:mgB, borderColor:'#b69d74', backgroundColor:'rgba(182,157,116,.1)', tension:0.3, fill:true,  pointRadius:3, pointHoverRadius:5, borderWidth:2 }},
        {{ label:'Margem EBITDA',  data:mgE, borderColor:'#00677b', backgroundColor:'rgba(0,103,123,.08)',  tension:0.3, fill:true,  pointRadius:3, pointHoverRadius:5, borderWidth:2 }},
        {{ label:'Margem Líquida', data:mgL, borderColor:'#2fa874', backgroundColor:'transparent',          tension:0.3, fill:false, pointRadius:3, pointHoverRadius:5, borderWidth:2 }}
      ]
    }},
    options:{{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        ...CHART_DEFAULTS.plugins,
        legend:{{display:true,position:'bottom',labels:{{color:'#718096',font:{{size:10}},boxWidth:10}}}},
        tooltip:{{callbacks:{{label:ctx => ctx.dataset.label+': '+(ctx.parsed.y!=null?Number(ctx.parsed.y).toFixed(1)+'%':'—')}}}}
      }},
      scales:{{
        x:{{ ...CHART_DEFAULTS.scales.x, ticks:{{...CHART_DEFAULTS.scales.x.ticks,maxRotation:45}} }},
        y:{{ ...CHART_DEFAULTS.scales.y, title:{{display:true,text:'%',color:'#718096',font:{{size:10}}}},
             ticks:{{...CHART_DEFAULTS.scales.y.ticks,callback:v=>Number(v).toFixed(1)+'%'}} }}
      }}
    }}
  }});

  // ── Chart 3: Alavancagem ──
  const dlEbt  = safe(filterArr(d['DivLiquida/EBITDA'])).map(v => v!=null?+Number(v).toFixed(2):null);
  const dbEbt  = safe(filterArr(d['DivBruta_EBITDA'])).map(v => v!=null?+Number(v).toFixed(2):null);
  const dlMi   = safe(filterArr(d['Divida Liquida'])).map(mi);
  const dbMi   = safe(filterArr(d['Divida Bruta'])).map(mi);
  mk('fundChartLev', {{
    type:'bar',
    data:{{ labels,
      datasets:[
        {{ label:'Dív. Líquida (R$ Mi)', data:dlMi, type:'bar',  backgroundColor:'rgba(217,65,65,.4)',   borderColor:'#d94141', borderWidth:1, yAxisID:'yMi', order:3 }},
        {{ label:'Dív. Bruta (R$ Mi)',   data:dbMi, type:'bar',  backgroundColor:'rgba(182,157,116,.4)', borderColor:'#b69d74', borderWidth:1, yAxisID:'yMi', order:4 }},
        {{ label:'Dív. Líq/EBITDA (x)',  data:dlEbt,type:'line', borderColor:'#d94141', backgroundColor:'transparent', tension:0.3, pointRadius:3, pointHoverRadius:5, borderWidth:2.5, yAxisID:'yX', order:1 }},
        {{ label:'Dív. Bruta/EBITDA (x)',data:dbEbt,type:'line', borderColor:'#3174b8', backgroundColor:'transparent', tension:0.3, pointRadius:3, pointHoverRadius:5, borderWidth:2,   yAxisID:'yX', order:2 }}
      ]
    }},
    options:{{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        ...CHART_DEFAULTS.plugins,
        legend:{{display:true,position:'bottom',labels:{{color:'#718096',font:{{size:10}},boxWidth:10}}}},
        tooltip:{{callbacks:{{label:ctx => {{
          const v = ctx.parsed.y;
          if(v==null) return null;
          return ctx.dataset.yAxisID==='yX' ? ctx.dataset.label+': '+Number(v).toFixed(2)+'x' : ctx.dataset.label+': R$ '+Number(v).toFixed(1)+' Mi';
        }}}}}}
      }},
      scales:{{
        x:{{ ...CHART_DEFAULTS.scales.x, ticks:{{...CHART_DEFAULTS.scales.x.ticks,maxRotation:45}} }},
        yMi:{{ type:'linear', position:'left',  display:true, title:{{display:true,text:'R$ Mi',color:'#718096',font:{{size:10}}}},
               ticks:{{color:'#718096',font:{{size:9,family:"'DM Mono',monospace"}},callback:v=>'R$'+Number(v).toFixed(0)+'Mi'}},
               grid:{{color:'rgba(31,40,57,.05)'}} }},
        yX:{{  type:'linear', position:'right', display:true, title:{{display:true,text:'Vezes (x)',color:'#718096',font:{{size:10}}}},
               ticks:{{color:'#718096',font:{{size:9,family:"'DM Mono',monospace"}},callback:v=>Number(v).toFixed(1)+'x'}},
               grid:{{drawOnChartArea:false}} }}
      }}
    }}
  }});

  // ── Chart 4: Liquidez ──
  const liq1 = safe(filterArr(d['Liquidez Corrente'])).map(v => v!=null?+Number(v).toFixed(3):null);
  const liq2 = safe(filterArr(d['Liquidez Seca'])).map(v => v!=null?+Number(v).toFixed(3):null);
  const liq3 = safe(filterArr(d['Liquidez Imediata'])).map(v => v!=null?+Number(v).toFixed(3):null);
  mk('fundChartLiq', {{
    type:'line',
    data:{{ labels,
      datasets:[
        {{ label:'Liq. Corrente', data:liq1, borderColor:'#00677b', backgroundColor:'rgba(0,103,123,.08)', tension:0.3, fill:true,  pointRadius:3, pointHoverRadius:5, borderWidth:2 }},
        {{ label:'Liq. Seca',     data:liq2, borderColor:'#b69d74', backgroundColor:'transparent',         tension:0.3, fill:false, pointRadius:3, pointHoverRadius:5, borderWidth:2 }},
        {{ label:'Liq. Imediata', data:liq3, borderColor:'#2fa874', backgroundColor:'transparent',         tension:0.3, fill:false, pointRadius:3, pointHoverRadius:5, borderWidth:2, borderDash:[4,3] }}
      ]
    }},
    options:{{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        ...CHART_DEFAULTS.plugins,
        legend:{{display:true,position:'bottom',labels:{{color:'#718096',font:{{size:10}},boxWidth:10}}}},
        tooltip:{{callbacks:{{label:ctx => ctx.dataset.label+': '+(ctx.parsed.y!=null?Number(ctx.parsed.y).toFixed(2)+'x':'—')}}}}
      }},
      scales:{{
        x:{{ ...CHART_DEFAULTS.scales.x, ticks:{{...CHART_DEFAULTS.scales.x.ticks,maxRotation:45}} }},
        y:{{ ...CHART_DEFAULTS.scales.y, title:{{display:true,text:'Vezes (x)',color:'#718096',font:{{size:10}}}},
             ticks:{{...CHART_DEFAULTS.scales.y.ticks,callback:v=>Number(v).toFixed(2)+'x'}} }}
      }}
    }}
  }});

  // ── Chart 5: Fluxo de Caixa ──
  const fco = safe(filterArr(d['FCO'])).map(mi);
  const fci = safe(filterArr(d['FCI'])).map(mi);
  const fcf = safe(filterArr(d['FCF'])).map(mi);
  mk('fundChartCF', {{
    type:'bar',
    data:{{ labels,
      datasets:[
        {{ label:'FCO — Operacional',       data:fco, backgroundColor:'rgba(0,103,123,.55)',    borderColor:'#00677b', borderWidth:1 }},
        {{ label:'FCI — Investimentos',      data:fci, backgroundColor:'rgba(217,65,65,.45)',    borderColor:'#d94141', borderWidth:1 }},
        {{ label:'FCF — FCO + FCI',          data:fcf, type:'line', borderColor:'#2fa874', backgroundColor:'transparent', tension:0.3, pointRadius:3, pointHoverRadius:5, borderWidth:2.5 }}
      ]
    }},
    options:{{
      ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{
        ...CHART_DEFAULTS.plugins,
        legend:{{display:true,position:'bottom',labels:{{color:'#718096',font:{{size:10}},boxWidth:10}}}},
        tooltip:{{callbacks:{{label:ctx => ctx.dataset.label+': R$ '+(ctx.parsed.y!=null?Number(ctx.parsed.y).toFixed(1):'—')+' Mi'}}}}
      }},
      scales:{{
        x:{{ ...CHART_DEFAULTS.scales.x, ticks:{{...CHART_DEFAULTS.scales.x.ticks,maxRotation:45}} }},
        y:{{ ...CHART_DEFAULTS.scales.y, title:{{display:true,text:'R$ Mi',color:'#718096',font:{{size:10}}}},
             ticks:{{...CHART_DEFAULTS.scales.y.ticks,callback:v=>'R$ '+Number(v).toFixed(0)+' Mi'}} }}
      }}
    }}
  }});
}}

async function exportarPDFFundamentos() {{
  const sel = document.getElementById('fundEmpSel');
  if (!sel || !sel.value) {{ alert('Selecione uma empresa primeiro'); return; }}

  const empName   = sel.options[sel.selectedIndex]?.text || sel.value;
  const container = document.getElementById('page-fundamentos');
  if (!container) {{ alert('Container nao encontrado.'); return; }}

  const btn = document.querySelector('button[onclick="exportarPDFFundamentos()"]');
  const textoOriginal = btn ? btn.innerHTML : '';
  if (btn) {{ btn.innerHTML = 'Gerando...'; btn.disabled = true; btn.style.opacity = '0.5'; }}

  // Monkey-patch createPattern: html2canvas 1.4.1 lanca erro fatal quando
  // encontra qualquer canvas (interno ou do usuario) com width=0 ou height=0.
  // Interceptamos a chamada e substituimos por um canvas 1x1 transparente.
  const _origCP = CanvasRenderingContext2D.prototype.createPattern;
  CanvasRenderingContext2D.prototype.createPattern = function(img, rep) {{
    if (img instanceof HTMLCanvasElement && (img.width === 0 || img.height === 0)) {{
      const dummy = document.createElement('canvas'); dummy.width = 1; dummy.height = 1;
      return _origCP.call(this, dummy, rep);
    }}
    return _origCP.call(this, img, rep);
  }};

  try {{
    // ── Pre-fix: forca dimensoes reais em canvas zerados e resize dos charts ──
    const canvasCorrigidos = [];
    container.querySelectorAll('canvas').forEach(c => {{
      if (c.width === 0 || c.height === 0) {{
        const w = c.offsetWidth  || c.parentElement?.offsetWidth  || 600;
        const h = c.offsetHeight || c.parentElement?.offsetHeight || 320;
        canvasCorrigidos.push({{ el: c, w: c.width, h: c.height }});
        c.width = w > 0 ? w : 600; c.height = h > 0 ? h : 320;
      }}
    }});
    if (window.Chart && Chart.instances) {{
      Object.values(Chart.instances).forEach(chart => {{
        try {{ if (chart.canvas && container.contains(chart.canvas)) chart.resize(); }} catch(e) {{}}
      }});
    }}
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

    const snap = await html2canvas(container, {{
      useCORS:        true,
      scale:          2,
      backgroundColor:'#f4f5f0',
      logging:        false,
      allowTaint:     true,
      imageTimeout:   20000,
      onclone: clonedDoc => {{
        clonedDoc.querySelectorAll('canvas').forEach(c => {{
          if (c.width === 0 || c.height === 0) {{ c.width = 1; c.height = 1; }}
        }});
      }},
      ignoreElements: el => {{
        try {{
          if (el.id === 'douradoBtn' || el.id === 'douradoPanel') return true;
          const oc = el.getAttribute && el.getAttribute('onclick');
          return !!(oc && oc.includes('exportarPDFFundamentos'));
        }} catch(e) {{ return false; }}
      }}
    }});

    canvasCorrigidos.forEach(({{el, w, h}}) => {{ el.width = w; el.height = h; }});

    const {{ jsPDF }} = window.jspdf;
    const pdf   = new jsPDF({{ orientation:'portrait', unit:'mm', format:'a4', compress:true }});
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const mTop  = 14; const mL = 6; const mRod = 8;
    const areaW = pageW - mL * 2;
    const areaH = pageH - mTop - mRod;
    const dataHoje = new Date().toLocaleDateString('pt-BR', {{ day:'2-digit', month:'2-digit', year:'numeric' }});

    const _cabecalho = () => {{
      pdf.setFillColor(31, 40, 57);
      pdf.rect(0, 0, pageW, mTop - 2, 'F');
      pdf.setTextColor(182, 157, 116); pdf.setFontSize(8); pdf.setFont('helvetica', 'bold');
      pdf.text('DOURO CAPITAL', mL + 2, mTop - 5);
      pdf.setTextColor(210, 210, 210); pdf.setFont('helvetica', 'normal');
      pdf.text(empName, pageW / 2, mTop - 5, {{ align:'center' }});
      pdf.text(dataHoje, pageW - mL - 2, mTop - 5, {{ align:'right' }});
    }};
    const _rodape = () => {{
      pdf.setTextColor(150, 150, 150); pdf.setFontSize(6);
      pdf.text('Douro Capital Gestora de Recursos · Uso Interno · Gerado automaticamente', pageW / 2, pageH - 3, {{ align:'center' }});
    }};

    // Fatia a imagem capturada em paginas A4
    const snapW  = snap.width;
    const snapH  = snap.height;
    const pxPerMm = snapW / areaW;
    const sliceH  = Math.round(areaH * pxPerMm);
    let offsetY = 0; let pagina = 0;

    while (offsetY < snapH) {{
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
    }}

    const nomeArq = 'Empresas_' + empName.replace(/[^a-zA-Z0-9\s]/g,'').replace(/\s+/g,'_') + '_' + dataHoje.replace(/\//g,'-') + '.pdf';
    pdf.save(nomeArq);
  }} catch(err) {{
    console.error('Erro ao gerar PDF:', err);
    alert('Erro ao gerar PDF: ' + (err && err.message ? err.message : String(err)));
  }} finally {{
    // Restaura createPattern original e dimensoes dos canvas
    CanvasRenderingContext2D.prototype.createPattern = _origCP;
    if (typeof canvasCorrigidos !== 'undefined') {{
      canvasCorrigidos.forEach(({{el, w, h}}) => {{ el.width = w; el.height = h; }});
    }}
    if (btn) {{ btn.innerHTML = textoOriginal; btn.disabled = false; btn.style.opacity = ''; }}
  }}
}}

async function exportarPDFBancos() {{
  const sel = document.getElementById('bancosEmpSel');
  if (!sel || !sel.value) {{ alert('Selecione um banco primeiro'); return; }}
  const empName   = sel.options[sel.selectedIndex]?.text || sel.value;
  const container = document.getElementById('page-bancos');
  if (!container) {{ alert('Container nao encontrado.'); return; }}
  const btn = document.querySelector('button[onclick="exportarPDFBancos()"]');
  const textoOriginal = btn ? btn.innerHTML : '';
  if (btn) {{ btn.innerHTML = 'Gerando...'; btn.disabled = true; btn.style.opacity = '0.5'; }}
  const _origCP = CanvasRenderingContext2D.prototype.createPattern;
  CanvasRenderingContext2D.prototype.createPattern = function(img, rep) {{
    if (img instanceof HTMLCanvasElement && (img.width === 0 || img.height === 0)) {{
      const dummy = document.createElement('canvas'); dummy.width = 1; dummy.height = 1;
      return _origCP.call(this, dummy, rep);
    }}
    return _origCP.call(this, img, rep);
  }};
  try {{
    const canvasCorrigidos = [];
    container.querySelectorAll('canvas').forEach(c => {{
      if (c.width === 0 || c.height === 0) {{
        const w = c.offsetWidth  || c.parentElement?.offsetWidth  || 600;
        const h = c.offsetHeight || c.parentElement?.offsetHeight || 320;
        canvasCorrigidos.push({{ el: c, w: c.width, h: c.height }});
        c.width = w > 0 ? w : 600; c.height = h > 0 ? h : 320;
      }}
    }});
    if (window.Chart && Chart.instances) {{
      Object.values(Chart.instances).forEach(chart => {{
        try {{ if (chart.canvas && container.contains(chart.canvas)) chart.resize(); }} catch(e) {{}}
      }});
    }}
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const snap = await html2canvas(container, {{
      useCORS: true, scale: 2, backgroundColor: '#f4f5f0',
      logging: false, allowTaint: true, imageTimeout: 20000,
      onclone: clonedDoc => {{
        clonedDoc.querySelectorAll('canvas').forEach(c => {{
          if (c.width === 0 || c.height === 0) {{ c.width = 1; c.height = 1; }}
        }});
      }},
      ignoreElements: el => {{
        try {{
          if (el.id === 'douradoBtn' || el.id === 'douradoPanel') return true;
          const oc = el.getAttribute && el.getAttribute('onclick');
          return !!(oc && oc.includes('exportarPDFBancos'));
        }} catch(e) {{ return false; }}
      }}
    }});
    canvasCorrigidos.forEach(({{el, w, h}}) => {{ el.width = w; el.height = h; }});
    const {{ jsPDF }} = window.jspdf;
    const pdf   = new jsPDF({{ orientation:'portrait', unit:'mm', format:'a4', compress:true }});
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const mTop  = 14; const mL = 6; const mRod = 8;
    const areaW = pageW - mL * 2;
    const areaH = pageH - mTop - mRod;
    const dataHoje = new Date().toLocaleDateString('pt-BR', {{ day:'2-digit', month:'2-digit', year:'numeric' }});
    const _cabecalho = () => {{
      pdf.setFillColor(31, 40, 57);
      pdf.rect(0, 0, pageW, mTop - 2, 'F');
      pdf.setTextColor(182, 157, 116); pdf.setFontSize(8); pdf.setFont('helvetica', 'bold');
      pdf.text('DOURO CAPITAL', mL + 2, mTop - 5);
      pdf.setTextColor(210, 210, 210); pdf.setFont('helvetica', 'normal');
      pdf.text(empName, pageW / 2, mTop - 5, {{ align:'center' }});
      pdf.text(dataHoje, pageW - mL - 2, mTop - 5, {{ align:'right' }});
    }};
    const _rodape = () => {{
      pdf.setTextColor(150, 150, 150); pdf.setFontSize(6);
      pdf.text('Douro Capital Gestora de Recursos · Uso Interno · Gerado automaticamente', pageW / 2, pageH - 3, {{ align:'center' }});
    }};
    const snapW = snap.width, snapH = snap.height;
    const pxPerMm = snapW / areaW;
    const sliceH  = Math.round(areaH * pxPerMm);
    let offsetY = 0, pagina = 0;
    while (offsetY < snapH) {{
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
    }}
    const nomeArq = 'Bancos_' + empName.replace(/[^a-zA-Z0-9\s]/g,'').replace(/\s+/g,'_') + '_' + dataHoje.replace(/\//g,'-') + '.pdf';
    pdf.save(nomeArq);
  }} catch(err) {{
    console.error('Erro ao gerar PDF:', err);
    alert('Erro ao gerar PDF: ' + (err && err.message ? err.message : String(err)));
  }} finally {{
    CanvasRenderingContext2D.prototype.createPattern = _origCP;
    if (typeof canvasCorrigidos !== 'undefined') {{
      canvasCorrigidos.forEach(({{el, w, h}}) => {{ el.width = w; el.height = h; }});
    }}
    if (btn) {{ btn.innerHTML = textoOriginal; btn.disabled = false; btn.style.opacity = ''; }}
  }}
}}

// ── SPREADS ────────────────────────────────────────────────────────────────
const spSelecionados = new Set();
let spInicializado = false;
function spInitSels() {{
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
  classesDisp.forEach(c => {{
    const o = document.createElement('option');
    o.value = c; o.textContent = c;
    selClasse.appendChild(o);
  }});
  // Setores
  const setoresDisp = [...new Set(
    ativosDisp
      .map(a => cart.find(x => x.ticker === a)?.setor)
      .filter(Boolean)
  )].sort();
  const selSetor = document.getElementById('spSetorSel');
  selSetor.innerHTML = '<option value="">Todos os Setores</option>';
  setoresDisp.forEach(s => {{
    const o = document.createElement('option');
    o.value = s; o.textContent = s;
    selSetor.appendChild(o);
  }});
  // Emissores
  const emissoresDisp = [...new Set(
    ativosDisp
      .map(a => cart.find(x => x.ticker === a)?.emissor)
      .filter(Boolean)
  )].sort();
  const selEms = document.getElementById('spEmsSel');
  selEms.innerHTML = '<option value="">Todos os Emissores</option>';
  emissoresDisp.forEach(e => {{
    const o = document.createElement('option');
    o.value = e; o.textContent = e;
    selEms.appendChild(o);
  }});

  spRenderAtivoList();
}}
function spGetAtivosDisp() {{
  const cart    = getFiltered();
  const classe  = document.getElementById('spClasseSel')?.value || '';
  const setor   = document.getElementById('spSetorSel')?.value  || '';
  const emissor = document.getElementById('spEmsSel')?.value    || '';

  return Object.keys(SPREADS_TS).filter(a => {{
    const c = cart.find(x => x.ticker === a);
    if (!c) return false;
    if (classe  && c.classe  !== classe)  return false;
    if (setor   && c.setor   !== setor)   return false;
    if (emissor && c.emissor !== emissor)  return false;
    return true;
  }});
}}
function spRenderAtivoList() {{
  const disponiveis = spGetAtivosDisp();
  document.getElementById('spAtivoCount').textContent = `(${{disponiveis.length}})`;
  const wrap = document.getElementById('spAtivoList');
  wrap.innerHTML = '';
  disponiveis.sort().forEach(a => {{
    const sel = spSelecionados.has(a);
    const btn = document.createElement('button');
    btn.textContent = a;
    btn.style.cssText = `padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600;transition:all .15s;border:1px solid ${{sel?'var(--teal)':'var(--border)'}};background:${{sel?'rgba(0,103,123,.12)':'var(--surface2)'}};color:${{sel?'var(--teal)':'var(--text3)'}};`;
    btn.onclick = () => spToggle(a);
    wrap.appendChild(btn);
  }});
  spRenderChips();
}}
function spToggle(a) {{
  if (spSelecionados.has(a)) spSelecionados.delete(a); else spSelecionados.add(a);
  spRenderAtivoList(); buildSpreads();
}}
function spRenderChips() {{
  const wrap = document.getElementById('spChipsWrap');
  if (!spSelecionados.size) {{ wrap.innerHTML = '<span style="color:var(--text3);font-size:11px">Nenhum selecionado</span>'; return; }}
  wrap.innerHTML = [...spSelecionados].map(a => `<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.25);border-radius:4px;padding:3px 8px;font-size:10px;font-weight:600;color:var(--teal)">${{a}}<span onclick="spToggle('${{a}}')" style="cursor:pointer;opacity:.7;font-size:12px;line-height:1">×</span></span>`).join('');
}}
function spAddAll()    {{ spGetAtivosDisp().forEach(a => spSelecionados.add(a)); spRenderAtivoList(); buildSpreads(); }}
function spRemoveAll() {{ spSelecionados.clear(); spRenderAtivoList(); buildSpreads(); }}
function spOnClasseChange() {{
  const cart   = getFiltered();
  const classe = document.getElementById('spClasseSel').value;
  // Re-popula Setores filtrando pela classe
  const ativosClasse = Object.keys(SPREADS_TS).filter(a => {{
    const c = cart.find(x => x.ticker === a);
    return c && (!classe || c.classe === classe);
  }});
  const setores = [...new Set(ativosClasse.map(a => cart.find(x => x.ticker===a)?.setor).filter(Boolean))].sort();
  const selSetor = document.getElementById('spSetorSel');
  selSetor.innerHTML = '<option value="">Todos os Setores</option>';
  setores.forEach(s => {{ const o = document.createElement('option'); o.value=s; o.textContent=s; selSetor.appendChild(o); }});
  // Re-popula Emissores
  const emissores = [...new Set(ativosClasse.map(a => cart.find(x => x.ticker===a)?.emissor).filter(Boolean))].sort();
  const selEms = document.getElementById('spEmsSel');
  selEms.innerHTML = '<option value="">Todos os Emissores</option>';
  emissores.forEach(e => {{ const o = document.createElement('option'); o.value=e; o.textContent=e; selEms.appendChild(o); }});
  spRenderAtivoList();
}}
function spOnSetorChange() {{
  const cart   = getFiltered();
  const classe = document.getElementById('spClasseSel').value;
  const setor  = document.getElementById('spSetorSel').value;
  const ativosDisp = Object.keys(SPREADS_TS).filter(a => {{
    const c = cart.find(x => x.ticker === a);
    return c && (!classe || c.classe === classe) && (!setor || c.setor === setor);
  }});
  const emissores = [...new Set(ativosDisp.map(a => cart.find(x => x.ticker===a)?.emissor).filter(Boolean))].sort();
  const selEms = document.getElementById('spEmsSel');
  selEms.innerHTML = '<option value="">Todos os Emissores</option>';
  emissores.forEach(e => {{ const o = document.createElement('option'); o.value=e; o.textContent=e; selEms.appendChild(o); }});
  spRenderAtivoList();
}}
function spOnEmsChange() {{ spRenderAtivoList(); }}
// ── BANCOS ─────────────────────────────────────────────────────────────────
// Fallback estático (chaves = nomes exatos do Watch List Bancos.xlsm)
// Sobrescrito pelos dados reais do BCB via BCB_LIVE abaixo
const _BCB_DATA = {{
  'Itaú': {{
    anos:['2021','2022','2023','2024'],
    basileia:[14.5,14.7,15.2,16.1], tier1:[12.8,13.2,13.8,14.5],
    roe:[18.5,19.8,20.4,21.2], nim:[7.2,7.8,8.1,7.9],
    inadimpl:[2.8,3.1,3.4,2.9], eficiencia:[42.1,41.5,40.8,40.2],
    pdd:[4.1,4.5,4.8,4.2]
  }},
  'Bradesco': {{
    anos:['2021','2022','2023','2024'],
    basileia:[15.3,14.8,14.1,14.9], tier1:[13.1,12.6,12.2,13.0],
    roe:[19.2,18.1,12.3,14.8], nim:[7.8,8.2,8.6,8.1],
    inadimpl:[3.4,4.1,5.8,4.9], eficiencia:[44.5,45.2,50.1,47.3],
    pdd:[5.2,6.1,8.2,6.8]
  }},
  'SANTANDER': {{
    anos:['2021','2022','2023','2024'],
    basileia:[14.2,14.0,14.8,15.3], tier1:[12.2,12.0,12.8,13.2],
    roe:[20.1,19.5,14.2,16.8], nim:[8.1,8.9,9.2,8.7],
    inadimpl:[3.2,3.8,5.1,4.3], eficiencia:[43.2,44.1,47.8,45.6],
    pdd:[5.1,5.8,7.4,6.2]
  }},
  'BTG Pactual': {{
    anos:['2021','2022','2023','2024'],
    basileia:[17.8,18.1,18.9,19.4], tier1:[15.2,15.8,16.4,17.1],
    roe:[22.4,23.1,24.8,26.2], nim:[4.2,4.8,5.1,5.4],
    inadimpl:[0.8,0.9,1.1,0.9], eficiencia:[38.2,37.5,36.8,35.9],
    pdd:[1.2,1.4,1.6,1.3]
  }},
  'BANCO SAFRA': {{
    anos:['2021','2022','2023','2024'],
    basileia:[16.2,16.8,17.1,17.5], tier1:[14.1,14.5,14.9,15.3],
    roe:[14.8,15.2,14.9,15.4], nim:[5.8,6.1,6.4,6.2],
    inadimpl:[1.8,2.1,2.4,2.1], eficiencia:[46.1,45.8,45.2,44.9],
    pdd:[2.8,3.1,3.4,3.1]
  }},
  'BANCO INTER': {{
    anos:['2021','2022','2023','2024'],
    basileia:[20.1,16.8,15.2,16.4], tier1:[18.5,14.9,13.5,14.8],
    roe:[-8.2,2.1,8.4,12.1], nim:[8.8,9.2,10.1,10.8],
    inadimpl:[4.2,5.8,6.2,5.4], eficiencia:[72.1,65.8,58.2,52.4],
    pdd:[6.8,8.2,9.1,8.1]
  }},
  'Daycoval': {{
    anos:['2021','2022','2023','2024'],
    basileia:[16.8,17.2,17.8,18.1], tier1:[14.8,15.1,15.6,15.9],
    roe:[18.2,19.1,20.4,21.2], nim:[9.2,9.8,10.2,10.1],
    inadimpl:[2.1,2.4,2.8,2.5], eficiencia:[39.8,39.2,38.5,38.1],
    pdd:[3.4,3.8,4.2,3.9]
  }},
  'Banco ABC': {{
    anos:['2021','2022','2023','2024'],
    basileia:[15.8,15.4,16.1,16.8], tier1:[13.8,13.5,14.2,14.8],
    roe:[16.2,17.8,18.4,19.1], nim:[4.8,5.2,5.6,5.4],
    inadimpl:[1.2,1.4,1.8,1.5], eficiencia:[42.8,41.5,40.2,39.8],
    pdd:[2.1,2.4,2.8,2.5]
  }},
  'Banco BMG': {{
    anos:['2021','2022','2023','2024'],
    basileia:[13.2,13.8,14.1,14.8], tier1:[11.4,12.1,12.4,13.1],
    roe:[10.8,12.1,13.8,14.2], nim:[18.4,19.2,20.1,19.8],
    inadimpl:[6.2,6.8,7.2,6.8], eficiencia:[55.2,53.8,51.4,50.2],
    pdd:[9.8,10.4,11.2,10.8]
  }}
}};

// ── Injeção BCB_LIVE: dados reais substituem o fallback estático ──────────
// BCB_LIVE tem chaves = nomes exatos do Watch List (definidos no BANCOS_BCB do Python)
// O lookup é exato — sem fuzzy — porque Python e Watch List usam a mesma grafia
(function() {{
  const live = (typeof BCB_LIVE !== 'undefined') ? BCB_LIVE : {{}};
  Object.keys(live).forEach(nome => {{
    const lv = live[nome];
    _BCB_DATA[nome] = {{
      anos:       lv.anos       || [],
      basileia:   lv.basileia   || [],
      tier1:      lv.alav       || [],
      roe:        lv.roe        || [],
      nim:        lv.ml         || [],
      inadimpl:   lv.npl        || [],   // NPL: carteira vencida >90d / carteira total (Rel. 6)
      pdd:        lv.prov_ratio || [],   // PDD/Carteira: provisão DRE / operações de crédito (Rel. 2+4)
      eficiencia: lv.eficiencia || []
    }};
  }});
}})();

// Busca em _BCB_DATA: exato primeiro, depois case-insensitive como fallback
// Os nomes já vêm do Watch List via Python, então hit exato deve ser a regra
function _bcbLookup(nome) {{
  if (!nome) return undefined;
  // 1. hit exato (nomes já alinhados Python → Watch List)
  if (_BCB_DATA[nome] !== undefined) return _BCB_DATA[nome];
  // 2. fallback case-insensitive (para variações de caixa residuais)
  const nq = nome.toLowerCase();
  const k = Object.keys(_BCB_DATA).find(k => k.toLowerCase() === nq);
  return k ? _BCB_DATA[k] : undefined;
}}

let _bancosIniciado = false;

function buildBancos(preselect) {{
  const sel = document.getElementById('bancosEmpSel');
  if (!sel) return;
  if (!_bancosIniciado) {{
    _bancosIniciado = true;
    const bancos = RANK_BANCOS.length
      ? RANK_BANCOS.map(b=>b.empresa).filter(b => _bcbLookup(b) !== undefined)
      : Object.keys(_BCB_DATA);
    sel.innerHTML = bancos.map(b=>`<option value="${{b}}">${{b}}</option>`).join('');
  }}
  if (preselect) sel.value = preselect;
  const banco = sel.value || sel.options[0]?.value;
  if (!banco) return;
  const rankInfo = (RANK_BANCOS||[]).find(b=>b.empresa===banco)||{{}};
  const d = _bcbLookup(banco);

  // KPIs (last period)
  const last = arr => arr?.length ? arr[arr.length-1] : null;
  if (d) {{
    const basLast = last(d.basileia);
    const roeLast = last(d.roe);
    const nplLast = last(d.inadimpl);
    document.getElementById('bancoKpiBasileia').textContent = basLast!=null ? Number(basLast).toFixed(1)+'%' : '—';
    document.getElementById('bancoKpiROE').textContent      = roeLast!=null ? Number(roeLast).toFixed(1)+'%' : '—';
    document.getElementById('bancoKpiNPL').textContent      = nplLast!=null ? Number(nplLast).toFixed(1)+'%' : '—';
  }} else {{
    ['bancoKpiBasileia','bancoKpiROE','bancoKpiNPL'].forEach(id=>{{document.getElementById(id).textContent='N/D';}});
    // Sem dados BCB: limpa gráficos e exibe aviso
    ['bancoChartBasileia','bancoChartRent','bancoChartCredit','bancoChartEfic'].forEach(id=>{{
      if(activeCharts[id]){{activeCharts[id].destroy();delete activeCharts[id];}}
      const canvas=document.getElementById(id);
      if(canvas){{
        const ctx=canvas.getContext('2d');
        ctx.clearRect(0,0,canvas.width,canvas.height);
        ctx.fillStyle='#718096';
        ctx.font='12px Montserrat,sans-serif';
        ctx.textAlign='center';
        ctx.fillText('Sem dados BCB IF.data para este banco',canvas.width/2,canvas.height/2-8);
        ctx.font='10px Montserrat,sans-serif';
        ctx.fillStyle='#a0aec0';
        ctx.fillText('Indicadores regulatórios não disponíveis publicamente',canvas.width/2,canvas.height/2+10);
      }}
    }});
    _bancosCurrentBanco = banco;
    _renderTbodyBancosComp();
    return;
  }}

  const anos = d?.anos || [];
  const lineOpts = {{
    ...CHART_DEFAULTS, maintainAspectRatio:false,
    interaction:{{mode:'index',intersect:false}},
    plugins:{{ ...CHART_DEFAULTS.plugins, legend:{{display:true,position:'bottom',labels:{{color:'#718096',font:{{size:10}},boxWidth:10}}}} }}
  }};

  // Chart 1: Basileia + Tier 1
  mk('bancoChartBasileia', {{
    type:'line',
    data:{{ labels:anos, datasets:[
      {{ label:'Índice de Basileia (%)', data:d?.basileia||[], borderColor:'#00677b', backgroundColor:'rgba(0,103,123,.12)', tension:0.3, fill:true, pointRadius:4, pointHoverRadius:6, borderWidth:2.5 }},
      {{ label:'Tier 1 Capital (%)',     data:d?.tier1||[],    borderColor:'#b69d74', backgroundColor:'transparent',          tension:0.3, fill:false,pointRadius:4, pointHoverRadius:6, borderWidth:2 }}
    ]}},
    options:{{ ...lineOpts, scales:{{ x:CHART_DEFAULTS.scales.x, y:{{ ...CHART_DEFAULTS.scales.y, title:{{display:true,text:'%',color:'#718096',font:{{size:10}}}}, ticks:{{...CHART_DEFAULTS.scales.y.ticks,callback:v=>v+'%'}}, beginAtZero:false }} }} }}
  }});

  // Chart 2: ROE + NIM
  mk('bancoChartRent', {{
    type:'line',
    data:{{ labels:anos, datasets:[
      {{ label:'ROE (%)',data:d?.roe||[], borderColor:'#2fa874', backgroundColor:'rgba(47,168,116,.1)', tension:0.3, fill:true, pointRadius:4, pointHoverRadius:6, borderWidth:2.5 }},
      {{ label:'NIM (%)',data:d?.nim||[], borderColor:'#3174b8', backgroundColor:'transparent',          tension:0.3, fill:false,pointRadius:4, pointHoverRadius:6, borderWidth:2 }}
    ]}},
    options:{{ ...lineOpts, scales:{{ x:CHART_DEFAULTS.scales.x, y:{{ ...CHART_DEFAULTS.scales.y, title:{{display:true,text:'%',color:'#718096',font:{{size:10}}}}, ticks:{{...CHART_DEFAULTS.scales.y.ticks,callback:v=>v+'%'}} }} }} }}
  }});

  // Chart 3: Inadimplência + PDD/Carteira (omite série se todos os valores forem null)
  const _hasData = arr => (arr||[]).some(v => v != null);
  const _creditDS = [];
  if (_hasData(d?.inadimpl)) _creditDS.push({{ label:'Cobertura PDD (%)',        data:d.inadimpl, borderColor:'#d94141', backgroundColor:'rgba(217,65,65,.1)', tension:0.3, fill:true, pointRadius:4, pointHoverRadius:6, borderWidth:2.5 }});
  if (_hasData(d?.pdd))      _creditDS.push({{ label:'Desp. Provisão/Carteira (%)', data:d.pdd,  borderColor:'#e0c44a', backgroundColor:'transparent',        tension:0.3, fill:false,pointRadius:4, pointHoverRadius:6, borderWidth:2 }});
  mk('bancoChartCredit', {{
    type:'line',
    data:{{ labels:anos, datasets:_creditDS }},
    options:{{ ...lineOpts, scales:{{ x:CHART_DEFAULTS.scales.x, y:{{ ...CHART_DEFAULTS.scales.y, title:{{display:true,text:'%',color:'#718096',font:{{size:10}}}}, ticks:{{...CHART_DEFAULTS.scales.y.ticks,callback:v=>v+'%'}}, beginAtZero:true }} }} }}
  }});

  // Chart 4: Eficiência (lower = better)
  mk('bancoChartEfic', {{
    type:'bar',
    data:{{ labels:anos, datasets:[
      {{ label:'Índice de Eficiência (%)', data:d?.eficiencia||[], backgroundColor:'rgba(182,157,116,.5)', borderColor:'#b69d74', borderWidth:1.5, borderRadius:4 }}
    ]}},
    options:{{ ...CHART_DEFAULTS, maintainAspectRatio:false,
      interaction:{{mode:'index',intersect:false}},
      plugins:{{ ...CHART_DEFAULTS.plugins, legend:{{display:false}},
        tooltip:{{callbacks:{{label:ctx=>ctx.dataset.label+': '+Number(ctx.parsed.y).toFixed(1)+'%'}}}}
      }},
      scales:{{ x:CHART_DEFAULTS.scales.x, y:{{ ...CHART_DEFAULTS.scales.y, title:{{display:true,text:'% (menor = melhor)',color:'#718096',font:{{size:10}}}}, ticks:{{...CHART_DEFAULTS.scales.y.ticks,callback:v=>v+'%'}}, beginAtZero:true }} }}
    }}
  }});

  _bancosCurrentBanco = banco;
  _renderTbodyBancosComp();
}}

let _bancosCurrentBanco = '', _bcSortCol='inadimpl', _bcSortAsc=false;
function _bancosCompSort(col){{if(_bcSortCol===col)_bcSortAsc=!_bcSortAsc;else{{_bcSortCol=col;_bcSortAsc=(col==='nome'||col==='rating'||col==='status');}}_renderTbodyBancosComp();}}
function _renderTbodyBancosComp(){{
  if(!document.getElementById('tbodyBancos'))return;
  const q=(document.getElementById('bancosSearch')?.value||'').toLowerCase();
  const l=arr=>{{const v=arr?.length?arr[arr.length-1]:null;return v!=null?Number(v).toFixed(1)+'%':'—';}};
  const lv=arr=>arr?.length?arr[arr.length-1]:null;
  const rOrd=['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC','CC','C','D','N/D'];
  const sOrd=['Aprovado','Em análise','Watch','Monitoramento','Reprovado','N/D'];
  const dir=_bcSortAsc?1:-1;
  const allBancos=RANK_BANCOS.length?RANK_BANCOS.map(b=>b.empresa).filter(b=>_bcbLookup(b)!==undefined):Object.keys(_BCB_DATA);
  let src=allBancos.map(b=>{{const bd=_bcbLookup(b);const ri=(RANK_BANCOS||[]).find(x=>x.empresa===b)||{{}};return{{b,bd,ri}};}});
  if(q) src=src.filter(x=>[x.b,x.ri.ratingDouro,x.ri.status].some(f=>f&&String(f).toLowerCase().includes(q)));
  src=[...src].sort((a,b)=>{{
    const aV=col=>{{const bd=a.bd;switch(col){{case 'basileia':return lv(bd?.basileia)??-Infinity;case 'tier1':return lv(bd?.tier1)??-Infinity;case 'roe':return lv(bd?.roe)??-Infinity;case 'nim':return lv(bd?.nim)??-Infinity;case 'inadimpl':return lv(bd?.inadimpl)??-Infinity;case 'eficiencia':return lv(bd?.eficiencia)??-Infinity;default:return 0;}}}};
    const bV=col=>{{const bd=b.bd;switch(col){{case 'basileia':return lv(bd?.basileia)??-Infinity;case 'tier1':return lv(bd?.tier1)??-Infinity;case 'roe':return lv(bd?.roe)??-Infinity;case 'nim':return lv(bd?.nim)??-Infinity;case 'inadimpl':return lv(bd?.inadimpl)??-Infinity;case 'eficiencia':return lv(bd?.eficiencia)??-Infinity;default:return 0;}}}};
    if(_bcSortCol==='nome') return dir*(a.b||'').localeCompare(b.b||'','pt-BR');
    if(_bcSortCol==='rating') return dir*((rOrd.indexOf(a.ri.ratingDouro||'N/D')<0?99:rOrd.indexOf(a.ri.ratingDouro||'N/D'))-(rOrd.indexOf(b.ri.ratingDouro||'N/D')<0?99:rOrd.indexOf(b.ri.ratingDouro||'N/D')));
    if(_bcSortCol==='status') return dir*((sOrd.indexOf(a.ri.status||'N/D')<0?99:sOrd.indexOf(a.ri.status||'N/D'))-(sOrd.indexOf(b.ri.status||'N/D')<0?99:sOrd.indexOf(b.ri.status||'N/D')));
    return dir*(aV(_bcSortCol)-bV(_bcSortCol));
  }});
  ['nome','basileia','tier1','roe','nim','inadimpl','eficiencia','rating','status'].forEach(col=>{{
    const el=document.getElementById('_bcsh_'+col);if(!el)return;
    if(col===_bcSortCol){{el.textContent=_bcSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}}
    else{{el.textContent='↕';el.style.opacity='.4';el.style.color='';}}
  }});
  document.getElementById('tbodyBancos').innerHTML=src.map(x=>{{
    const {{b,bd,ri}}=x;
    const isCurrent=b===_bancosCurrentBanco;
    const roeV=lv(bd?.roe);const nplV=lv(bd?.inadimpl);
    return `<tr style="${{isCurrent?'background:rgba(182,157,116,.08)':''}}">
      <td style="font-weight:600;color:${{isCurrent?'var(--teal)':'inherit'}}">${{b}}</td>
      <td style="font-family:var(--mono)">${{bd?l(bd.basileia):'—'}}</td>
      <td style="font-family:var(--mono)">${{bd?l(bd.tier1):'—'}}</td>
      <td style="font-family:var(--mono);color:${{roeV!=null?(roeV>15?'var(--teal)':roeV<10?'#d94141':'inherit'):'inherit'}}">${{bd?l(bd.roe):'—'}}</td>
      <td style="font-family:var(--mono)">${{bd?l(bd.nim):'—'}}</td>
      <td style="font-family:var(--mono);color:${{nplV!=null?(nplV>5?'#d94141':nplV<3?'var(--teal)':'inherit'):'inherit'}}">${{bd?l(bd.inadimpl):'—'}}</td>
      <td style="font-family:var(--mono)">${{bd?l(bd.eficiencia):'—'}}</td>
      <td>${{badgeRating(ri.ratingDouro)}}</td>
      <td>${{badgeStatus(ri.status)}}</td>
    </tr>`;
  }}).join('');
}}

function buildSpreads() {{
  // NÃO chame spInitSels() aqui — só popula na primeira vez
  if (!spInicializado) {{
    spInitSels();
    spInicializado = true;
  }}
  const cart       = getFiltered();
  const ativosUsar = [...spSelecionados].filter(a => SPREADS_TS[a]);
  if (!ativosUsar.length) {{
    ['chartSpTaxa','chartSpSpread','chartSpScatter'].forEach(id => {{
      if (activeCharts[id]) {{ activeCharts[id].destroy(); delete activeCharts[id]; }}
    }});
    document.getElementById('tbodySpreads').innerHTML = '<tr><td colspan="11" style="text-align:center;color:var(--text3);padding:40px 32px;font-size:13px">Selecione ativos usando os filtros acima</td></tr>';
    return;
  }}
  const dsTaxa = ativosUsar.map((a, i) => {{
    const ts   = SPREADS_TS[a];
    const dados = (ts.datas||[]).map((d,j) => {{
      const dt = parseBRDate(d); if (!dt) return null;
      const yv = ts.valor?.[j]; if (yv==null||yv!==yv) return null;
      return {{ x:dt, y:yv }};
    }}).filter(p => p !== null);
    return {{ label:a, data:dados, borderColor:COLORS[i%COLORS.length], backgroundColor:'transparent', tension:.3, pointRadius:0, borderWidth:2 }};
  }});
  mk('chartSpTaxa', {{
    type:'line', data:{{ datasets:dsTaxa }},
    options:{{ ...CHART_DEFAULTS, parsing:false, interaction:{{ mode:'nearest', intersect:false }},
      plugins:{{ ...CHART_DEFAULTS.plugins, legend:{{ display:true, position:'bottom', labels:{{ color:'#718096', font:{{size:10}}, boxWidth:10 }} }}, tooltip:{{ callbacks:{{ label: ctx => ctx.dataset.label+': '+(ctx.parsed.y!=null?ctx.parsed.y.toFixed(3)+'%':'—') }} }} }},
      scales:{{ x:{{ type:'time', time:{{ unit:'month', displayFormats:{{ month:'MMM/yy' }}, tooltipFormat:'dd/MM/yyyy' }}, ...CHART_DEFAULTS.scales.x, ticks:{{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:12 }} }}, y:{{ ...CHART_DEFAULTS.scales.y, title:{{ display:true, text:'Taxa (%)', color:'#718096', font:{{size:10}} }}, ticks:{{ ...CHART_DEFAULTS.scales.y.ticks, callback: v => v.toFixed(2)+'%' }} }} }}
    }}
  }});
  const dsSpread = ativosUsar.map((a, i) => {{
    const ts   = SPREADS_TS[a];
    const dados = (ts.datas||[]).map((d,j) => {{
      const dt = parseBRDate(d); if (!dt) return null;
      const yv = ts.spread?.[j]; if (yv==null||yv!==yv) return null;
      return {{ x:dt, y:yv }};
    }}).filter(p => p !== null);
    return {{ label:a, data:dados, borderColor:COLORS[i%COLORS.length], backgroundColor:COLORS[i%COLORS.length]+'18', tension:.3, pointRadius:0, borderWidth:2, fill:false }};
  }});
  mk('chartSpSpread', {{
    type:'line', data:{{ datasets:dsSpread }},
    options:{{ ...CHART_DEFAULTS, parsing:false, interaction:{{ mode:'nearest', intersect:false }},
      plugins:{{ ...CHART_DEFAULTS.plugins, legend:{{ display:true, position:'bottom', labels:{{ color:'#718096', font:{{size:10}}, boxWidth:10 }} }}, tooltip:{{ callbacks:{{ label: ctx => ctx.dataset.label+': '+(ctx.parsed.y!=null?ctx.parsed.y.toFixed(3)+'%':'—') }} }} }},
      scales:{{ x:{{ type:'time', time:{{ unit:'month', displayFormats:{{ month:'MMM/yy' }}, tooltipFormat:'dd/MM/yyyy' }}, ...CHART_DEFAULTS.scales.x, ticks:{{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:12 }} }}, y:{{ ...CHART_DEFAULTS.scales.y, title:{{ display:true, text:'Spread s/ NTN-B (%)', color:'#718096', font:{{size:10}} }}, ticks:{{ ...CHART_DEFAULTS.scales.y.ticks, callback: v => v.toFixed(2)+'%' }} }} }}
    }}
  }});
  const scatterPts = ativosUsar.map((a, i) => {{
    const c = cart.find(x => x.ticker === a);
    const ts = SPREADS_TS[a];
    const spread = ts?.spread?.filter(v => v!=null).slice(-1)[0] ?? null;
    const dur    = c?.duration ?? null;
    if (spread == null || dur == null) return null;
    return {{ ticker:a, x:dur, y:spread, color:COLORS[i%COLORS.length] }};
  }}).filter(Boolean);
  const _sxVals = scatterPts.map(p=>p.x), _syVals = scatterPts.map(p=>p.y);
  const _sxMin  = _sxVals.length ? Math.max(0, Math.min(..._sxVals) - 0.3) : 0;
  const _sxMax  = _sxVals.length ? Math.max(..._sxVals) + 0.3 : 5;
  const _syRng  = _syVals.length ? Math.max(..._syVals) - Math.min(..._syVals) : 0;
  const _syPad  = Math.max(_syRng * 0.18, 0.002);
  const _syMin  = _syVals.length ? Math.min(..._syVals) - _syPad : 0;
  const _syMax  = _syVals.length ? Math.max(..._syVals) + _syPad : 1;
  mk('chartSpScatter', {{
    type:'scatter',
    data:{{ datasets:[{{ label:'Ativos', data:scatterPts.map(p=>({{ x:p.x, y:p.y, ticker:p.ticker }})), backgroundColor:scatterPts.map(p=>p.color+'cc'), pointRadius:8, pointHoverRadius:11 }}] }},
    options:{{ ...CHART_DEFAULTS, plugins:{{ ...CHART_DEFAULTS.plugins, legend:{{ display:false }}, tooltip:{{ callbacks:{{ label: c=>`${{c.raw.ticker}}: dur=${{c.raw.x?.toFixed(1)}}a | spread=${{c.raw.y?.toFixed(3)}}%` }} }} }}, scales:{{ x:{{ ...CHART_DEFAULTS.scales.x, title:{{ display:true, text:'Duration (anos)', color:'#718096', font:{{size:10}} }}, min:_sxMin, max:_sxMax }}, y:{{ ...CHART_DEFAULTS.scales.y, title:{{ display:true, text:'Spread (%)', color:'#718096', font:{{size:10}} }}, min:_syMin, max:_syMax, ticks:{{ ...CHART_DEFAULTS.scales.y.ticks, callback: v=>v.toFixed(3)+'%' }} }} }} }}
  }});
  _spCache = [...new Map(cart.filter(a => SPREADS_TS[a.ticker]).map(a => [a.ticker, a])).values()];
  _renderTbodySpreads();
}}

let _spCache = [];
let _spSortCol = 'spread', _spSortAsc = false;

function _spSort(col) {{
  if (_spSortCol===col) _spSortAsc=!_spSortAsc; else {{ _spSortCol=col; _spSortAsc=(col==='ticker'||col==='emissor'||col==='setor'||col==='ntnb'||col==='status'); }}
  _renderTbodySpreads();
}}

function _renderTbodySpreads() {{
  const q=(document.getElementById('spreadsSearch')?.value||'').toLowerCase().trim();
  const soSel=document.getElementById('spSoSelecionados')?.checked;
  let src=_spCache;
  if(soSel) src=src.filter(a=>spSelecionados.has(a.ticker));
  if(q) src=src.filter(a=>[a.ticker,a.emissor,a.setor,a.ntnb_ref,a.Status].some(f=>f&&String(f).toLowerCase().includes(q)));
  const getV=a=>{{
    const ts=SPREADS_TS[a.ticker];
    return {{
      taxa: ts?.valor?.filter(v=>v!=null).slice(-1)[0]??null,
      spread: ts?.spread?.filter(v=>v!=null).slice(-1)[0]??null,
      mediana: ts?.mediana_spread??null,
      p1mad: ts?.mediana_mais_1mad_spread??null,
      m1mad: ts?.mediana_menos_1mad_spread??null,
    }};
  }};
  const cmpStr=(a,b)=>(a||'').localeCompare(b||'','pt-BR');
  const cmpNum=(a,b)=>(a??-Infinity)-(b??-Infinity);
  const dir=_spSortAsc?1:-1;
  src=[...src].sort((a,b)=>{{
    const av=getV(a), bv=getV(b);
    switch(_spSortCol){{
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
    }}
  }});
  ['ticker','emissor','setor','taxa','spread','mediana','ntnb','duration','status'].forEach(col=>{{
    const el=document.getElementById('_spsh_'+col); if(!el) return;
    if(col===_spSortCol){{el.textContent=_spSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}}
    else{{el.textContent='↕';el.style.opacity='.4';el.style.color='';}}
  }});
  const tb=document.getElementById('tbodySpreads');
  if(!src.length){{tb.innerHTML='<tr><td colspan="11" style="text-align:center;color:var(--text3);padding:32px">Sem dados.</td></tr>';return;}}
  tb.innerHTML=src.map(a=>{{
    const v=getV(a);
    const sc=v.spread==null?'':v.spread>(v.p1mad??Infinity)?'col-bad':v.spread<(v.m1mad??-Infinity)?'col-good':'col-warn';
    return `<tr>
      <td style="font-weight:700;font-family:var(--mono);font-size:11px">${{a.ticker||'—'}}</td>
      <td>${{a.emissor||'—'}}</td><td class="td-muted">${{a.setor||'—'}}</td>
      <td style="font-family:var(--mono)">${{v.taxa!=null?Number(v.taxa).toFixed(3):'—'}}</td>
      <td class="${{sc}}" style="font-family:var(--mono)">${{v.spread!=null?Number(v.spread).toFixed(3):'—'}}</td>
      <td style="font-family:var(--mono)">${{v.mediana!=null?Number(v.mediana).toFixed(3):'—'}}</td>
      <td style="font-family:var(--mono);color:var(--green)">${{v.p1mad!=null?Number(v.p1mad).toFixed(3):'—'}}</td>
      <td style="font-family:var(--mono);color:var(--red)">${{v.m1mad!=null?Number(v.m1mad).toFixed(3):'—'}}</td>
      <td class="td-muted">${{a.ntnb_ref||'—'}}</td>
      <td style="font-family:var(--mono)">${{a.duration?Number(a.duration).toFixed(1)+'a':'—'}}</td>
      <td>${{badgeStatus(a.Status)}}</td>
    </tr>`;
  }}).join('');
}}
// ── TÚNEL ─────────────────────────────────────────────────────────────────
function calcDistribuicao(valores, pontos=60) {{
  const vals = (valores||[]).filter(v => v!=null && !isNaN(v));
  if (!vals.length) return {{ xs:[], ys:[] }};
  const min = Math.min(...vals), max = Math.max(...vals);
  const largura = (max-min)||1, bandwidth = largura/8;
  const xs=[], ys=[];
  for (let i=0; i<pontos; i++) {{
    const x = min + (largura*i/(pontos-1));
    let soma = 0;
    vals.forEach(v => {{ const u=(x-v)/bandwidth; soma+=Math.exp(-0.5*u*u); }});
    xs.push(x); ys.push(soma/(vals.length*bandwidth*Math.sqrt(2*Math.PI)));
  }}
  return {{ xs, ys }};
}}
function buildTunel() {{
  const ativosCarteira = getFiltered().map(a => a.ticker);
  const ativos = Object.keys(SPREADS_TS).filter(a => ativosCarteira.includes(a));
  const sel = document.getElementById('ativoTunelSel');
  if (!sel) return;
  const anterior = sel.value;
  sel.innerHTML = '';
  ativos.forEach(a => {{ const o=document.createElement('option'); o.value=a; o.textContent=a; sel.appendChild(o); }});
  if (ativos.includes(anterior)) sel.value = anterior;
  const ativo = sel.value || ativos[0];
  if (!ativo || !SPREADS_TS[ativo]) {{
    if (activeCharts['chartTunelTaxa'])   activeCharts['chartTunelTaxa'].destroy();
    if (activeCharts['chartTunelSpread']) activeCharts['chartTunelSpread'].destroy();
    document.getElementById('tbodyTunel').innerHTML = '<tr><td colspan="12" style="text-align:center;color:var(--text3);padding:32px">Nenhum ativo disponível.</td></tr>';
    return;
  }}
  const ts   = SPREADS_TS[ativo];
  const cart = getFiltered();
  const info = cart.find(a => a.ticker === ativo) || {{}};
  const dadosValidos = (ts.datas||[]).map((d,i) => ({{ data:d, valor:ts.valor?.[i]??null, spread:ts.spread?.[i]??null, mm21v:ts.mm21_valor?.[i]??null, mm21s:ts.mm21_spread?.[i]??null }})).filter(x => x.data!=null && (x.valor!=null || x.spread!=null));
  const datas  = dadosValidos.map(x => {{ const raw=x.data; if (!raw) return null; if (raw.includes('-')) return raw.split('T')[0]; const p=raw.split('/'); return p.length===3?`${{p[2]}}-${{p[1].padStart(2,'0')}}-${{p[0].padStart(2,'0')}}`:null; }});
  const valores = dadosValidos.map(x => x.valor);
  const spreads = dadosValidos.map(x => x.spread);
  const mm21v   = dadosValidos.map(x => x.mm21v);
  const mm21s   = dadosValidos.map(x => x.mm21s);
  const hline   = (val, color, label) => ({{ label, data:datas.map(()=>val), borderColor:color, backgroundColor:'transparent', borderDash:[4,4], borderWidth:1.5, pointRadius:0 }});
  mk('chartTunelTaxa', {{
    type:'line', data:{{ labels:datas, datasets:[
      {{ label:'Taxa', data:valores, borderColor:'#b69d74', backgroundColor:'rgba(182,157,116,.12)', tension:.3, pointRadius:0, borderWidth:2, fill:true }},
      ...(mm21v.some(v=>v!=null)?[{{ label:'MM21 Taxa', data:mm21v, borderColor:'#00677b', backgroundColor:'transparent', tension:.4, pointRadius:0, borderDash:[2,2] }}]:[]),
      ...(ts.mediana_valor!=null?[hline(ts.mediana_valor,'#4a90d9','Mediana')]:[]),
      ...(ts.mediana_mais_1mad_valor!=null?[hline(ts.mediana_mais_1mad_valor,'#3ec98e','+1 MAD')]:[]),
      ...(ts.mediana_menos_1mad_valor!=null?[hline(ts.mediana_menos_1mad_valor,'#e05252','−1 MAD')]:[])
    ]}},
    options:{{ ...CHART_DEFAULTS, scales:{{ x:{{ type:'time', time:{{ unit:'month', displayFormats:{{ month:'MMM/yy' }}, tooltipFormat:'dd/MM/yyyy' }}, ...CHART_DEFAULTS.scales.x, ticks:{{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:10 }} }}, y:{{ ...CHART_DEFAULTS.scales.y, title:{{ display:true, text:'Taxa (%)', color:'#8a9ab5', font:{{size:10}} }} }} }} }}
  }});
  const distTaxa = calcDistribuicao(valores.filter(v=>v!=null));
  mk('chartHistTunelTaxa', {{ type:'line', data:{{ labels:distTaxa.xs.map(v=>v.toFixed(2)), datasets:[{{ label:'Distribuição Taxa', data:distTaxa.ys, borderColor:'#b69d74', backgroundColor:'rgba(182,157,116,.12)', fill:true, tension:.35, pointRadius:0, borderWidth:2 }}] }}, options:{{ ...CHART_DEFAULTS, plugins:{{ ...CHART_DEFAULTS.plugins, legend:{{ display:false }} }} }} }});
  mk('chartTunelSpread', {{
    type:'line', data:{{ labels:datas, datasets:[
      {{ label:'Spread', data:spreads, borderColor:'#4a90d9', backgroundColor:'rgba(74,144,217,.12)', tension:.3, pointRadius:0, borderWidth:2, fill:true }},
      ...(mm21s.some(v=>v!=null)?[{{ label:'MM21 Spread', data:mm21s, borderColor:'#00677b', backgroundColor:'transparent', tension:.4, pointRadius:0, borderDash:[2,2] }}]:[]),
      ...(ts.mediana_spread!=null?[hline(ts.mediana_spread,'#b69d74','Mediana')]:[]),
      ...(ts.mediana_mais_1mad_spread!=null?[hline(ts.mediana_mais_1mad_spread,'#3ec98e','+1 MAD')]:[]),
      ...(ts.mediana_menos_1mad_spread!=null?[hline(ts.mediana_menos_1mad_spread,'#e05252','−1 MAD')]:[])
    ]}},
    options:{{ ...CHART_DEFAULTS, scales:{{ x:{{ type:'time', time:{{ unit:'month', displayFormats:{{ month:'MMM/yy' }}, tooltipFormat:'dd/MM/yyyy' }}, ...CHART_DEFAULTS.scales.x, ticks:{{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:10 }} }}, y:{{ ...CHART_DEFAULTS.scales.y, title:{{ display:true, text:'Spread (%)', color:'#8a9ab5', font:{{size:10}} }} }} }} }}
  }});
  const distSpread = calcDistribuicao(spreads.filter(v=>v!=null));
  mk('chartHistTunelSpread', {{ type:'line', data:{{ labels:distSpread.xs.map(v=>v.toFixed(2)), datasets:[{{ label:'Distribuição Spread', data:distSpread.ys, borderColor:'#4a90d9', backgroundColor:'rgba(74,144,217,.12)', fill:true, tension:.35, pointRadius:0, borderWidth:2 }}] }}, options:{{ ...CHART_DEFAULTS, plugins:{{ ...CHART_DEFAULTS.plugins, legend:{{ display:false }} }} }} }});
  const taxaAtual   = valores.filter(v=>v!=null).slice(-1)[0]  ?? null;
  const spreadAtual = spreads.filter(v=>v!=null).slice(-1)[0]  ?? null;
  const med    = ts.mediana_spread ?? null;
  const p1mad  = ts.mediana_mais_1mad_spread  ?? null;
  const m1mad  = ts.mediana_menos_1mad_spread ?? null;
  const volSpread = ts.std_spread ?? null;
  let zscore = null;
  if (spreadAtual!=null && med!=null && p1mad!=null) {{
    const madVal = p1mad - med, stdAprox = madVal * 1.4826;
    zscore = stdAprox > 0 ? (spreadAtual - med) / stdAprox : null;
  }}
  const zCls  = zscore==null?'': zscore>2?'col-bad': zscore>1?'col-warn': zscore<-1?'col-good':'';
  const scSp  = spreadAtual==null?'': spreadAtual>(p1mad??Infinity)?'col-bad': spreadAtual<(m1mad??-Infinity)?'col-good':'col-warn';
  document.getElementById('tbodyTunel').innerHTML = `<tr>
    <td style="font-weight:600;font-size:11px">${{ativo}}</td>
    <td>${{info.emissor||'—'}}</td><td class="td-muted">${{info.setor||'—'}}</td>
    <td style="font-family:var(--mono)">${{info.duration?Number(info.duration).toFixed(1)+'a':'—'}}</td>
    <td style="font-family:var(--mono)">${{taxaAtual!=null?Number(taxaAtual).toFixed(3):'—'}}</td>
    <td class="${{scSp}}" style="font-family:var(--mono)">${{spreadAtual!=null?Number(spreadAtual).toFixed(3):'—'}}</td>
    <td style="font-family:var(--mono)">${{med!=null?Number(med).toFixed(3):'—'}}</td>
    <td style="font-family:var(--mono);color:var(--green)">${{p1mad!=null?Number(p1mad).toFixed(3):'—'}}</td>
    <td style="font-family:var(--mono);color:var(--red)">${{m1mad!=null?Number(m1mad).toFixed(3):'—'}}</td>
    <td class="${{zCls}}" style="font-family:var(--mono)">${{zscore!=null?Number(zscore).toFixed(2):'—'}}</td>
    <td style="font-family:var(--mono)">${{volSpread!=null?Number(volSpread).toFixed(4):'—'}}</td>
    <td>${{badgeStatus(info.Status)}}</td>
  </tr>`;
}}
// ── BONDS ─────────────────────────────────────────────────────────────────
const bondsSelecionados = new Set();
let bondsFiltrados = [], bondsInicializado = false;
function bondInitSels() {{
  bondsFiltrados = Object.keys(BONDS_TS).sort();
  if (bondsSelecionados.size===0 && bondsFiltrados.length>0) bondsFiltrados.slice(0,3).forEach(b => bondsSelecionados.add(b));
  bondRenderList();
}}
function bondFilterList() {{
  const termo = document.getElementById('bondSearch').value.toLowerCase();
  bondsFiltrados = Object.keys(BONDS_TS).filter(b => b.toLowerCase().includes(termo)).sort();
  bondRenderList();
}}
function bondRenderList() {{
  const wrap = document.getElementById('bondList'); if (!wrap) return;
  wrap.innerHTML = '';
  bondsFiltrados.forEach(b => {{
    const sel = bondsSelecionados.has(b);
    const btn = document.createElement('button');
    btn.textContent = b;
    btn.style.cssText = `padding:4px 10px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600;transition:all .15s;border:1px solid ${{sel?'var(--teal)':'var(--border)'}};background:${{sel?'rgba(0,103,123,.12)':'var(--surface2)'}};color:${{sel?'var(--teal)':'var(--text3)'}};`;
    btn.onclick = () => bondToggle(b);
    wrap.appendChild(btn);
  }});
  bondRenderChips();
}}
function bondToggle(b) {{ if (bondsSelecionados.has(b)) bondsSelecionados.delete(b); else bondsSelecionados.add(b); bondRenderList(); buildBonds(); }}
function bondRenderChips() {{
  const wrap=document.getElementById('bondChipsWrap'), countEl=document.getElementById('bondCount');
  if (!wrap) return;
  if (countEl) countEl.textContent = `(${{bondsSelecionados.size}})`;
  if (!bondsSelecionados.size) {{ wrap.innerHTML='<span style="color:var(--text3);font-size:11px">Nenhum selecionado — use a busca</span>'; return; }}
  wrap.innerHTML = [...bondsSelecionados].map(b=>`<span style="display:inline-flex;align-items:center;gap:4px;background:rgba(0,103,123,.1);border:1px solid rgba(0,103,123,.25);border-radius:4px;padding:3px 8px;font-size:10px;font-weight:600;color:var(--teal)">${{b}}<span onclick="bondToggle('${{b}}')" style="cursor:pointer;opacity:.7;font-size:12px;line-height:1">×</span></span>`).join('');
}}
function bondAddAll()    {{ bondsFiltrados.forEach(b=>bondsSelecionados.add(b)); bondRenderList(); buildBonds(); }}
function bondRemoveAll() {{ bondsSelecionados.clear(); bondRenderList(); buildBonds(); }}
function buildBonds() {{
  if (!bondsInicializado) {{ bondInitSels(); bondsInicializado=true; }} else bondRenderList();
  const bondsPlot = [...bondsSelecionados];
  if (!bondsPlot.length) {{
    if (activeCharts['chartBondsPreco']) {{ activeCharts['chartBondsPreco'].destroy(); delete activeCharts['chartBondsPreco']; }}
    const tb=document.getElementById('tbodyBonds'); if(tb) tb.innerHTML='<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:32px">Selecione bonds para visualizar dados.</td></tr>';
    return;
  }}
  const datasetsPreco = bondsPlot.map((b,i) => {{
    const ts=BONDS_TS[b]; if(!ts) return null;
    const dados=(ts.datas||[]).map((d,j)=>{{ const dt=parseBRDate(d); if(!dt) return null; return {{ x:dt, y:ts.valor?.[j]??null }}; }}).filter(p=>p&&p.y!=null);
    return {{ label:b, data:dados, borderColor:COLORS[i%COLORS.length], backgroundColor:'transparent', tension:0.25, pointRadius:0, borderWidth:2 }};
  }}).filter(Boolean);
  mk('chartBondsPreco', {{
    type:'line', data:{{ datasets:datasetsPreco }},
    options:{{ ...CHART_DEFAULTS, parsing:false, maintainAspectRatio:false, interaction:{{ mode:'nearest', intersect:false }},
      plugins:{{ ...CHART_DEFAULTS.plugins, legend:{{ display:true, position:'bottom', labels:{{ color:'#718096', font:{{size:10}}, boxWidth:10 }} }}, tooltip:{{ callbacks:{{ label: ctx=>ctx.dataset.label+': '+(ctx.parsed.y!=null?ctx.parsed.y.toFixed(2):'—') }} }} }},
      scales:{{ x:{{ type:'time', time:{{ unit:'month', displayFormats:{{ month:'MMM/yy' }}, tooltipFormat:'dd/MM/yyyy' }}, ...CHART_DEFAULTS.scales.x, ticks:{{ ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:12 }} }}, y:{{ ...CHART_DEFAULTS.scales.y, title:{{ display:true, text:'Preço (% PU)', color:'#718096', font:{{size:10}} }}, ticks:{{ ...CHART_DEFAULTS.scales.y.ticks, callback: v=>v.toFixed(2) }} }} }}
    }}
  }});
  _bondsCachePlot = bondsPlot;
  _renderTbodyBonds();
}}

let _bondsCachePlot=[], _bondsSortCol='ticker', _bondsSortAsc=true;
function _bondsSort(col){{if(_bondsSortCol===col)_bondsSortAsc=!_bondsSortAsc;else{{_bondsSortCol=col;_bondsSortAsc=(col==='ticker'||col==='emissor'||col==='status');}}_renderTbodyBonds();}}
function _renderTbodyBonds(){{
  const q=(document.getElementById('bondsSearch')?.value||'').toLowerCase();
  const dir=_bondsSortAsc?1:-1;
  let src=_bondsCachePlot.map(b=>{{
    const info=BONDS_INFO.find(x=>x.ativo===b)||{{}};
    const ts=BONDS_TS[b];
    const preco=ts?.valor?.filter(v=>v!=null).slice(-1)[0]??null;
    return {{b,info,preco}};
  }});
  if(q) src=src.filter(x=>[x.b,x.info.emissor,x.info.status].some(f=>f&&String(f).toLowerCase().includes(q)));
  src=[...src].sort((a,b)=>{{
    if(_bondsSortCol==='ticker') return dir*(a.b||'').localeCompare(b.b||'','pt-BR');
    if(_bondsSortCol==='emissor') return dir*(a.info.emissor||'').localeCompare(b.info.emissor||'','pt-BR');
    if(_bondsSortCol==='status') return dir*(a.info.status||'').localeCompare(b.info.status||'','pt-BR');
    if(_bondsSortCol==='preco') return dir*((a.preco??-Infinity)-(b.preco??-Infinity));
    return 0;
  }});
  ['ticker','emissor','status','preco'].forEach(col=>{{
    const el=document.getElementById('_bsh_'+col);if(!el)return;
    if(col===_bondsSortCol){{el.textContent=_bondsSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}}
    else{{el.textContent='↕';el.style.opacity='.4';el.style.color='';}}
  }});
  const tb=document.getElementById('tbodyBonds');
  if(!tb) return;
  if(!src.length){{tb.innerHTML='<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:32px">Sem dados.</td></tr>';return;}}
  tb.innerHTML=src.map(x=>`<tr><td style="font-weight:700;font-family:var(--mono);font-size:11px">${{x.b}}</td><td>${{x.info.emissor||'—'}}</td><td>${{badgeStatus(x.info.status)}}</td><td style="font-family:var(--mono);color:var(--teal)">${{x.preco!=null?Number(x.preco).toFixed(2):'—'}}</td></tr>`).join('');
}}
// ── RANKING ───────────────────────────────────────────────────────────────
let _rcSortCol='status',_rcSortAsc=false;
function _rankCorpSort(col){{if(_rcSortCol===col)_rcSortAsc=!_rcSortAsc;else{{_rcSortCol=col;_rcSortAsc=col!=='status';}}_renderRankCorp();}}
function _renderRankCorp(){{
  const q=(document.getElementById('rankCorpSearch')?.value||'').toLowerCase();
  const rOrd=['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC','CC','C','D','N/D'];
  const sOrd=['Aprovado','Em análise','Watch','Monitoramento','Reprovado','N/D'];
  const cmpStr=(a,b)=>(a||'').localeCompare(b||'','pt-BR');
  const cmpRat=(a,b)=>(rOrd.indexOf(a||'N/D')<0?99:rOrd.indexOf(a||'N/D'))-(rOrd.indexOf(b||'N/D')<0?99:rOrd.indexOf(b||'N/D'));
  const cmpSt=(a,b)=>(sOrd.indexOf(a||'N/D')<0?99:sOrd.indexOf(a||'N/D'))-(sOrd.indexOf(b||'N/D')<0?99:sOrd.indexOf(b||'N/D'));
  const dir=_rcSortAsc?1:-1;
  let src=RANK_CORP.filter(e=>!q||[e.empresa,e.setor,e.ratingMkt,e.ratingDouro,e.status].some(f=>f&&String(f).toLowerCase().includes(q)));
  src=[...src].sort((a,b)=>{{
    switch(_rcSortCol){{
      case 'empresa': return dir*cmpStr(a.empresa,b.empresa);
      case 'setor': return dir*cmpStr(a.setor,b.setor);
      case 'ratingMkt': return dir*cmpRat(a.ratingMkt,b.ratingMkt);
      case 'ratingDouro': return dir*cmpRat(a.ratingDouro,b.ratingDouro);
      default: return dir*cmpSt(a.status,b.status);
    }}
  }});
  ['empresa','setor','ratingMkt','ratingDouro','status'].forEach(col=>{{
    const el=document.getElementById('_rcsh_'+col);if(!el)return;
    if(col===_rcSortCol){{el.textContent=_rcSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}}
    else{{el.textContent='↕';el.style.opacity='.4';el.style.color='';}}
  }});
  document.getElementById('tbodyRankCorp').innerHTML=src.map(e=>`<tr><td style="font-weight:600">${{e.empresa}}</td><td class="td-muted">${{e.setor}}</td><td>${{badgeRating(e.ratingMkt)}}</td><td>${{badgeRating(e.ratingDouro)}}</td><td>${{badgeStatus(e.status)}}</td></tr>`).join('');
}}
function buildRankingCorp() {{
  _renderRankCorp();
  const byStatus={{}};
  RANK_CORP.forEach(e=>{{ const s=e.status||'N/D'; byStatus[s]=(byStatus[s]||0)+1; }});
  const statusEntries=Object.entries(byStatus);
  const statusColor=s=>s==='Aprovado'?'#00677b':s==='Em análise'?'#b69d74':s==='Reprovado'?'#d94141':'#718096';
  mk('chartRankingStatus', {{
    type:'doughnut',
    data:{{ labels:statusEntries.map(e=>e[0]), datasets:[{{ data:statusEntries.map(e=>e[1]), backgroundColor:statusEntries.map(e=>statusColor(e[0])+'ee'), borderColor:'#ffffff', borderWidth:2 }}] }},
    options:{{ ...DOUGHNUT_OPTS, plugins:{{ ...DOUGHNUT_OPTS.plugins, tooltip:{{ callbacks:{{ label: c=>`${{c.label}}: ${{c.raw}} emissor(es)` }} }} }} }}
  }});
}}

let _rbSortCol='status',_rbSortAsc=false;
function _rankBancosSort(col){{if(_rbSortCol===col)_rbSortAsc=!_rbSortAsc;else{{_rbSortCol=col;_rbSortAsc=col!=='status';}}_renderRankBancos();}}
function _renderRankBancos(){{
  const q=(document.getElementById('rankBancosSearch')?.value||'').toLowerCase();
  const rOrd=['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC','CC','C','D','N/D'];
  const sOrd=['Aprovado','Em análise','Watch','Monitoramento','Reprovado','N/D'];
  const dir=_rbSortAsc?1:-1;
  let src=RANK_BANCOS.filter(b=>!q||[b.empresa,b.ratingDouro,b.status].some(f=>f&&String(f).toLowerCase().includes(q)));
  src=[...src].sort((a,b)=>{{
    if(_rbSortCol==='empresa') return dir*(a.empresa||'').localeCompare(b.empresa||'','pt-BR');
    if(_rbSortCol==='ratingDouro') return dir*((rOrd.indexOf(a.ratingDouro||'N/D')<0?99:rOrd.indexOf(a.ratingDouro||'N/D'))-(rOrd.indexOf(b.ratingDouro||'N/D')<0?99:rOrd.indexOf(b.ratingDouro||'N/D')));
    return dir*((sOrd.indexOf(a.status||'N/D')<0?99:sOrd.indexOf(a.status||'N/D'))-(sOrd.indexOf(b.status||'N/D')<0?99:sOrd.indexOf(b.status||'N/D')));
  }});
  ['empresa','ratingDouro','status'].forEach(col=>{{
    const el=document.getElementById('_rbsh_'+col);if(!el)return;
    if(col===_rbSortCol){{el.textContent=_rbSortAsc?'↑':'↓';el.style.opacity='1';el.style.color='var(--teal)';}}
    else{{el.textContent='↕';el.style.opacity='.4';el.style.color='';}}
  }});
  document.getElementById('tbodyRankBancos').innerHTML=src.map(b=>`<tr><td style="font-weight:600">${{b.empresa}}</td><td>${{badgeRating(b.ratingDouro)}}</td><td>${{badgeStatus(b.status)}}</td></tr>`).join('');
}}
function buildRankingBancos() {{
  _renderRankBancos();
  const byRD={{}};
  RANK_BANCOS.forEach(b=>{{ byRD[b.ratingDouro||'N/D']=(byRD[b.ratingDouro||'N/D']||0)+1; }});
  const ord=['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC','CC','C','D','N/D'];
  const rde=Object.entries(byRD).sort((a,b)=>ord.indexOf(a[0])-ord.indexOf(b[0]));
  mk('chartRankingBancosBar',{{ type:'bar', data:{{ labels:rde.map(e=>e[0]), datasets:[{{ data:rde.map(e=>e[1]), backgroundColor:rde.map((_,i)=>COLORS[i%COLORS.length]+'ee'), borderColor:rde.map((_,i)=>COLORS[i%COLORS.length]), borderWidth:1, borderRadius:4 }}]}}, options:{{...CHART_DEFAULTS, plugins:{{...CHART_DEFAULTS.plugins, legend:{{display:false}}}}, scales:{{ x:{{...CHART_DEFAULTS.scales.x}}, y:{{...CHART_DEFAULTS.scales.y, ticks:{{...CHART_DEFAULTS.scales.y.ticks, stepSize:1}}}}}}}} }});
}}
function buildRankingComparativo() {{
  document.getElementById('tbodyCompCorp').innerHTML   = RANK_CORP.map(e=>`<tr><td style="font-weight:600">${{e.empresa}}</td><td class="td-muted">${{e.setor}}</td><td>${{badgeRating(e.ratingMkt)}}</td><td>${{badgeRating(e.ratingDouro)}}</td><td>${{badgeStatus(e.status)}}</td></tr>`).join('');
  document.getElementById('tbodyCompBancos').innerHTML = RANK_BANCOS.map(b=>`<tr><td style="font-weight:600">${{b.empresa}}</td><td>${{badgeRating(b.ratingDouro)}}</td><td>${{badgeStatus(b.status)}}</td></tr>`).join('');
  const ord=['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC','CC','C','D','N/D'];
  const byRdCorp={{}}, byRdBanc={{}};
  RANK_CORP.forEach(e=>{{ byRdCorp[e.ratingDouro||'N/D']=(byRdCorp[e.ratingDouro||'N/D']||0)+1; }});
  RANK_BANCOS.forEach(b=>{{ byRdBanc[b.ratingDouro||'N/D']=(byRdBanc[b.ratingDouro||'N/D']||0)+1; }});
  const allRatings=[...new Set([...Object.keys(byRdCorp),...Object.keys(byRdBanc)])].sort((a,b)=>ord.indexOf(a)-ord.indexOf(b));
  mk('chartCompRating',{{type:'bar',data:{{labels:allRatings,datasets:[{{label:'Corporativos',data:allRatings.map(r=>byRdCorp[r]||0),backgroundColor:'rgba(0,103,123,.75)',borderColor:'#00677b',borderWidth:1,borderRadius:3}},{{label:'Bancos',data:allRatings.map(r=>byRdBanc[r]||0),backgroundColor:'rgba(182,157,116,.75)',borderColor:'#b69d74',borderWidth:1,borderRadius:3}}]}},options:{{...CHART_DEFAULTS,plugins:{{...CHART_DEFAULTS.plugins,legend:{{display:true,position:'bottom',labels:{{color:'#718096',font:{{size:10}},boxWidth:10}}}}}},scales:{{x:{{...CHART_DEFAULTS.scales.x}},y:{{...CHART_DEFAULTS.scales.y,ticks:{{...CHART_DEFAULTS.scales.y.ticks,stepSize:1}}}}}}}}}});
  const statusOrd=['Aprovado','Em análise','Watch','Monitoramento','Reprovado'];
  const byStCorp={{}}, byStBanc={{}};
  RANK_CORP.forEach(e=>{{ const s=e.status||'N/D'; byStCorp[s]=(byStCorp[s]||0)+1; }});
  RANK_BANCOS.forEach(b=>{{ const s=b.status||'N/D'; byStBanc[s]=(byStBanc[s]||0)+1; }});
  const statusColor=s=>s==='Aprovado'?'#00677b':s==='Reprovado'?'#d94141':'#b69d74';
  const allStatus=[...new Set([...Object.keys(byStCorp),...Object.keys(byStBanc)])].sort((a,b)=>{{const i=statusOrd.indexOf(a),j=statusOrd.indexOf(b);return(i<0?99:i)-(j<0?99:j);}});
  mk('chartCompStatus',{{type:'bar',data:{{labels:allStatus,datasets:[{{label:'Corporativos',data:allStatus.map(s=>byStCorp[s]||0),backgroundColor:allStatus.map(s=>statusColor(s)+'aa'),borderColor:allStatus.map(s=>statusColor(s)),borderWidth:1,borderRadius:3}},{{label:'Bancos',data:allStatus.map(s=>byStBanc[s]||0),backgroundColor:allStatus.map(s=>statusColor(s)+'55'),borderColor:allStatus.map(s=>statusColor(s)),borderWidth:1,borderRadius:3}}]}},options:{{...CHART_DEFAULTS,plugins:{{...CHART_DEFAULTS.plugins,legend:{{display:true,position:'bottom',labels:{{color:'#718096',font:{{size:10}},boxWidth:10}}}}}},scales:{{x:{{...CHART_DEFAULTS.scales.x}},y:{{...CHART_DEFAULTS.scales.y,ticks:{{...CHART_DEFAULTS.scales.y.ticks,stepSize:1}}}}}}}}}});
}}
function buildRanking() {{ buildRankingCorp(); buildRankingBancos(); }}
function showRankingPage(sub, el) {{
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  const pg=document.getElementById('page-ranking');
  pg.classList.add('active'); pg.classList.remove('fade-in'); void pg.offsetWidth; pg.classList.add('fade-in');
  if(el) el.classList.add('active');
  document.getElementById('subpage-corporativo').style.display='none';
  document.getElementById('subpage-bancario').style.display='none';
  document.getElementById('subpage-comparativo').style.display='none';
  if (sub==='corporativo')  {{ document.getElementById('subpage-corporativo').style.display=''; requestAnimationFrame(()=>buildRankingCorp()); }}
  else if (sub==='bancario'){{ document.getElementById('subpage-bancario').style.display='';   requestAnimationFrame(()=>buildRankingBancos()); }}
  else                      {{ document.getElementById('subpage-comparativo').style.display=''; requestAnimationFrame(()=>buildRankingComparativo()); }}
  loadedPages['ranking']=true;
}}
// ── PERFORMANCE ───────────────────────────────────────────────────────────
function buildPerformance() {{
  const ativos = Object.keys(PERF_DATA.ativos);
  const datasets = ativos.map((a,i)=>({{ label:a, data:PERF_DATA.ativos[a].retorno_acum.map(v=>v*100), borderColor:COLORS[i%COLORS.length], backgroundColor:'transparent', tension:.3, pointRadius:0, borderWidth:2 }}));
  mk('chartPerfAcum',{{ type:'line', data:{{ labels:PERF_DATA.datas, datasets }}, options:{{
    ...CHART_DEFAULTS,
    ..._CROSSHAIR_OPTS,
    plugins:{{ ...CHART_DEFAULTS.plugins, ..._CROSSHAIR_OPTS.plugins }},
    scales:{{
      x:{{ ...CHART_DEFAULTS.scales.x }},
      y:{{ ...CHART_DEFAULTS.scales.y, ticks:{{ ...CHART_DEFAULTS.scales.y.ticks, callback: v=>v.toFixed(1)+'%' }} }}
    }}
  }} }});
  const janela=parseInt(document.getElementById('janelaPerf').value);
  const rollingDs = ativos.map((a,i)=>{{
    const rets=PERF_DATA.ativos[a].retornos, rolling=[];
    for(let j=janela;j<rets.length;j++){{ let acc=1; for(let k=j-janela;k<j;k++) acc*=(1+rets[k]); rolling.push((acc-1)*100); }}
    return {{ label:a, data:rolling, borderColor:COLORS[i%COLORS.length], backgroundColor:'transparent', tension:.3, pointRadius:0, borderWidth:2 }};
  }});
  mk('chartRolling',{{ type:'line', data:{{ labels:PERF_DATA.datas.slice(janela), datasets:rollingDs }}, options:{{
    ...CHART_DEFAULTS,
    ..._CROSSHAIR_OPTS,
    plugins:{{ ...CHART_DEFAULTS.plugins, ..._CROSSHAIR_OPTS.plugins }},
    scales:{{
      x:{{ ...CHART_DEFAULTS.scales.x }},
      y:{{ ...CHART_DEFAULTS.scales.y, ticks:{{ ...CHART_DEFAULTS.scales.y.ticks, callback: v=>v.toFixed(1)+'%' }} }}
    }}
  }} }});
  document.getElementById('tbodyPerf').innerHTML = ativos.map(a=>{{
    const d=PERF_DATA.ativos[a];
    return `<tr><td style="font-weight:700">${{a}}</td><td style="font-family:var(--mono)">${{(d.vol*100).toFixed(2)}}%</td><td class="${{d.drawdown<-0.1?'col-bad':'col-good'}}" style="font-family:var(--mono)">${{(d.drawdown*100).toFixed(2)}}%</td><td class="${{d.ret_total>0?'col-good':'col-bad'}}" style="font-family:var(--mono)">${{(d.ret_total*100).toFixed(2)}}%</td></tr>`;
  }}).join('');
  const corr=PERF_DATA.correlacao;
  let html='<thead><tr><th></th>';
  corr.labels.forEach(l=>{{ html+=`<th>${{l}}</th>`; }});
  html+='</tr></thead><tbody>';
  corr.values.forEach((row,i)=>{{ html+=`<tr><td style="font-weight:700">${{corr.labels[i]}}</td>`; row.forEach(v=>{{ html+=`<td style="font-family:var(--mono)">${{v.toFixed(2)}}</td>`; }}); html+='</tr>'; }});
  html+='</tbody>';
  document.getElementById('corrTable').innerHTML=html;
}}
// ── DOURO NEWS ────────────────────────────────────────────────────────────
function buildDouroNews() {{
  const nd   = typeof NEWS_DATA !== 'undefined' ? NEWS_DATA : {{}};
  const news = nd.noticias || [];
  const ctx  = nd.ctx      || {{}};
  const rf   = nd.rf       || {{}};
  const ins  = nd.insight  || {{}};
  const liv  = nd.livro    || {{}};
  const fil  = nd.filme    || null;

  // ── Insight ───────────────────────────────────────────────────────
  const insEl = document.getElementById('newsInsight');
  if (insEl && ins.insight) {{
    insEl.innerHTML = `
      <p style="font-size:14px;line-height:1.8;font-style:italic;color:var(--text);margin-bottom:8px;">"${{ins.insight}}"</p>
      <p style="font-size:12px;color:var(--text3);">— ${{ins.gestor}}</p>`;
  }}

  // ── Market bar ────────────────────────────────────────────────────
  const mktEl = document.getElementById('newsMarket');
  if (mktEl) {{
    const UP='#2fa874', DN='#d94141';
    const wtiPart = ctx.wti && ctx.wti!=='—' ? `
      <div style="display:flex;flex-direction:column;gap:4px;">
        <span style="font-size:9px;letter-spacing:1.8px;text-transform:uppercase;color:#d5d8c9;opacity:.45;">Petróleo WTI</span>
        <span style="font-size:14px;font-weight:500;color:#fff;">${{ctx.wti}} <span style="color:${{ctx.wti_up?UP:DN}};font-size:11px">${{ctx.wti_var}}</span></span>
      </div>` : '';
    mktEl.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:4px;">
        <span style="font-size:9px;letter-spacing:1.8px;text-transform:uppercase;color:#d5d8c9;opacity:.45;">Ibovespa</span>
        <span style="font-size:14px;font-weight:500;color:#fff;">${{ctx.ibov||'—'}} <span style="color:${{ctx.ibov_up?UP:DN}};font-size:11px">${{ctx.ibov_var||''}}</span></span>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;">
        <span style="font-size:9px;letter-spacing:1.8px;text-transform:uppercase;color:#d5d8c9;opacity:.45;">Dólar</span>
        <span style="font-size:14px;font-weight:500;color:#fff;">${{ctx.dolar||'—'}} <span style="color:${{ctx.dolar_up?UP:DN}};font-size:11px">${{ctx.dolar_var||''}}</span></span>
      </div>
      ${{wtiPart}}`;
  }}

  // ── News cards ────────────────────────────────────────────────────
  const ORDEM = ['Empresas','Macro','Mercados','Política','Geral'];
  const LIMITS = {{Empresas:6,Macro:4,Mercados:3,'Política':3,Geral:2}};
  const byCat = {{}};
  news.forEach(n => {{
    (n.categorias||['Geral']).forEach(cat => {{
      if (!byCat[cat]) byCat[cat] = [];
      if (!byCat[cat].find(x=>x.link===n.link)) byCat[cat].push(n);
    }});
  }});
  let newsHtml = '';
  ORDEM.forEach(cat => {{
    const items = (byCat[cat]||[]).slice(0, LIMITS[cat]||3);
    if (!items.length) return;
    newsHtml += `<div style="margin-top:28px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
        <div style="width:3px;height:3px;border-radius:50%;background:#b69d74;flex-shrink:0;"></div>
        <span style="font-size:10px;font-weight:600;letter-spacing:2.8px;text-transform:uppercase;color:var(--text3);white-space:nowrap;">${{cat}}</span>
        <div style="flex:1;height:1px;background:var(--border);"></div>
      </div>`;
    items.forEach((n,i) => {{
      const tag = (n.tickers||[])[0] || '';
      if (i===0) {{
        newsHtml += `<div style="background:#1f2839;border-radius:8px;padding:20px 22px;margin-bottom:10px;">
          ${{tag?`<div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:700;margin-bottom:8px">${{tag}}</div>`:''}}
          <div style="font-size:14.5px;font-weight:600;color:#fff;line-height:1.55;margin-bottom:12px;">${{n.titulo}}</div>
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <span style="font-size:11px;color:#d5d8c9;opacity:.5;">${{n.fonte}}</span>
            <a href="${{n.link}}" target="_blank" style="font-size:11px;color:#b69d74;text-decoration:none;">ler →</a>
          </div></div>`;
      }} else {{
        newsHtml += `<div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px 18px;margin-bottom:8px;">
          ${{tag?`<div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:6px">${{tag}}</div>`:''}}
          <div style="font-size:13px;font-weight:500;color:var(--text);line-height:1.6;margin-bottom:10px;">${{n.titulo}}</div>
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <span style="font-size:11px;color:var(--text3);">${{n.fonte}}</span>
            <a href="${{n.link}}" target="_blank" style="font-size:11px;color:var(--text3);text-decoration:none;opacity:.7;">ler →</a>
          </div></div>`;
      }}
    }});
    newsHtml += '</div>';
  }});
  const cardsEl = document.getElementById('newsCards');
  if (cardsEl) cardsEl.innerHTML = newsHtml || '<p style="color:var(--text3);font-style:italic;text-align:center;padding:40px;">Nenhuma notícia disponível no momento.</p>';

  // ── RF Termômetro ─────────────────────────────────────────────────
  const rfEl = document.getElementById('newsRF');
  if (rfEl) {{
    const rfRow = (o,fn,ft) => {{
      const label=(o||{{}}).n||fn, taxa=(o||{{}}).t||ft;
      return `<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:10px;"><span style="color:var(--text2);font-weight:500;">${{label}}</span><span style="font-weight:700;color:var(--text);">${{taxa}}</span></div>`;
    }};
    rfEl.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
        <div style="width:3px;height:3px;border-radius:50%;background:#b69d74;flex-shrink:0;"></div>
        <span style="font-size:10px;font-weight:600;letter-spacing:2.8px;text-transform:uppercase;color:var(--text3);white-space:nowrap;">Termômetro Renda Fixa</span>
        <div style="flex:1;height:1px;background:var(--border);"></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="card">
          <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:12px;">Curva DI Futuro</div>
          ${{rfRow(rf.di_curto,'DI Jan 27','N/D')}}${{rfRow(rf.di_medio,'DI Jan 29','N/D')}}${{rfRow(rf.di_longo,'DI Jan 33','N/D')}}
        </div>
        <div class="card">
          <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:12px;">Curva Real (ETFs)</div>
          ${{rfRow(rf.ntnb_curta,'B5P211 (Curta)','N/D')}}${{rfRow(rf.ntnb_media,'IMAB11 (Geral)','N/D')}}${{rfRow(rf.ntnb_longa,'B5MB11 (Longa)','N/D')}}
        </div>
      </div>`;
  }}

  // ── Literatura + Filme ────────────────────────────────────────────
  const wkEl = document.getElementById('newsWeekly');
  if (wkEl) {{
    const filmePart = fil ? `
      <div class="card" style="border-left:3px solid #b69d74;margin-top:12px;">
        <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:14px;">Dica de Fim de Semana</div>
        <div style="font-size:16px;font-weight:700;color:var(--text);margin-bottom:4px;">${{fil.titulo}}</div>
        <div style="font-size:12px;color:var(--text3);margin-bottom:10px;">${{fil.categoria}}</div>
        <div style="font-size:13px;color:var(--text2);line-height:1.6;">${{fil.insight}}</div>
      </div>` : '';
    wkEl.innerHTML = `
      <div class="card" style="border-left:3px solid #b69d74;">
        <div style="font-size:10px;letter-spacing:1.8px;text-transform:uppercase;color:#b69d74;font-weight:600;margin-bottom:14px;">Literatura da Semana</div>
        <div style="font-size:16px;font-weight:700;color:var(--text);margin-bottom:4px;">${{liv.titulo||'—'}}</div>
        <div style="font-size:12px;color:var(--text3);margin-bottom:10px;">por ${{liv.autor||'—'}}</div>
        <div style="font-size:13px;color:var(--text2);line-height:1.6;">${{liv.desc||''}}</div>
      </div>${{filmePart}}`;
  }}

  // ── Fatos Relevantes CVM — bloco "Empresas" dentro do Douro News ──
  const wkEl2 = document.getElementById('newsWeekly');
  if (wkEl2) {{
    const fatos = typeof FATOS_RELEVANTES !== 'undefined' ? FATOS_RELEVANTES : [];
    if (fatos.length > 0) {{
      const top = fatos.slice(0, 6);
      let frHtml = `<div style="margin-top:20px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
          <div style="width:3px;height:3px;border-radius:50%;background:#3cd28a;flex-shrink:0;"></div>
          <span style="font-size:10px;font-weight:600;letter-spacing:2.8px;text-transform:uppercase;color:var(--text3);">Fatos Relevantes CVM</span>
          <div style="flex:1;height:1px;background:var(--border);"></div>
          <span onclick="showPage('notificacoes',document.getElementById('navNotifItem'))" style="font-size:10px;color:#3cd28a;cursor:pointer;font-weight:600;">ver todos →</span>
        </div>`;
      top.forEach(f => {{
        const linkPart = f.link
          ? `<a href="${{f.link}}" target="_blank" style="font-size:10px;color:#3cd28a;text-decoration:none;font-weight:600;">doc →</a>`
          : '';
        frHtml += `<div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:13px 16px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
          <div style="flex:1;min-width:0;">
            <div style="font-size:10px;letter-spacing:1.4px;text-transform:uppercase;color:#3cd28a;font-weight:700;margin-bottom:4px">${{f.empresa}}</div>
            <div style="font-size:12.5px;font-weight:500;color:var(--text);line-height:1.55;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${{f.assunto}}</div>
          </div>
          <div style="text-align:right;flex-shrink:0;">
            <div style="font-size:10px;color:var(--text3);font-family:var(--mono);margin-bottom:4px">${{f.data}}</div>
            ${{linkPart}}
          </div>
        </div>`;
      }});
      frHtml += '</div>';
      wkEl2.innerHTML += frHtml;
    }}
  }}
}}
// ── NOTIFICAÇÕES ──────────────────────────────────────────────────────────
let _notifJanelaFiltro = 'all';
let _notifTipoFiltro   = 'all';

function _notifSetJanela(janela, btn) {{
  _notifJanelaFiltro = janela;
  document.querySelectorAll('.notif-janela-btn[data-janela]').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  _notifRenderAlertas();
}}
function _notifSetTipo(tipo, btn) {{
  _notifTipoFiltro = tipo;
  document.querySelectorAll('.notif-janela-btn[data-tipo]').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  _notifRenderAlertas();
}}

function _notifRenderAlertas() {{
  const alertas = typeof ALERTAS_NOTIF !== 'undefined' ? ALERTAS_NOTIF : [];
  let src = alertas;
  if (_notifJanelaFiltro !== 'all') src = src.filter(a => a.janela === _notifJanelaFiltro);
  if (_notifTipoFiltro   !== 'all') src = src.filter(a => a.tipo  === _notifTipoFiltro);

  // KPI strip — top movers per janela
  const kpiEl = document.getElementById('notifKpiStrip');
  if (kpiEl) {{
    const byJanela = {{'1d': [], '7d': [], '21d': []}};
    alertas.forEach(a => {{ if (byJanela[a.janela]) byJanela[a.janela].push(a); }});
    kpiEl.innerHTML = ['1d','7d','21d'].map(j => {{
      const cnt = byJanela[j].length;
      const worst = byJanela[j][0]; // already sorted by abs variacao
      const varStr = worst ? (worst.variacao >= 0 ? `+${{worst.variacao.toFixed(2)}}%` : `${{worst.variacao.toFixed(2)}}%`) : '—';
      const varCol = worst ? (worst.variacao > 0 ? '#d94141' : '#2fa874') : 'var(--text3)';
      return `<div class="card" style="padding:14px 16px;border-left:3px solid #3cd28a20;">
        <div style="font-size:9px;color:var(--text3);text-transform:uppercase;font-weight:600;letter-spacing:.10em;margin-bottom:8px">Janela ${{j}}</div>
        <div style="font-size:22px;font-weight:700;color:#3cd28a;font-family:var(--mono);margin-bottom:4px">${{cnt}}</div>
        <div style="font-size:11px;color:var(--text3);">alertas</div>
        ${{worst ? `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);font-size:11px;display:flex;justify-content:space-between;align-items:center;"><span style="font-weight:600">${{worst.ticker}}</span><span style="color:${{varCol}};font-family:var(--mono);font-weight:700">${{varStr}}</span></div>` : ''}}
      </div>`;
    }}).join('');
  }}

  const countEl = document.getElementById('notifAlertasCount');
  if (countEl) countEl.textContent = `${{src.length}} alerta(s)`;

  const grid = document.getElementById('notifAlertasGrid');
  if (!grid) return;
  if (!src.length) {{
    grid.innerHTML = `<div class="card" style="grid-column:1/-1;text-align:center;color:var(--text3);padding:40px;">Nenhum alerta para os filtros selecionados.</div>`;
    return;
  }}
  // Badge for sidebar
  const badge = document.getElementById('notifBadgeNav');
  if (badge) {{
    const total = alertas.length;
    if (total > 0) {{ badge.style.display='inline-block'; badge.textContent = total > 99 ? '99+' : String(total); }}
    else badge.style.display = 'none';
  }}
  grid.innerHTML = src.slice(0, 60).map(a => {{
    const isUp  = a.variacao > 0;
    const clr   = isUp ? '#d94141' : '#2fa874';
    const arrow = isUp ? '▲' : '▼';
    const varStr = `${{isUp?'+':''}}${{a.variacao.toFixed(2)}}%`;
    const badgeTxt = a.tipo === 'spread' ? 'SPREAD' : 'TAXA';
    const badgeJanela = a.janela.toUpperCase();
    return `<div class="alerta-card ${{isUp?'alerta-up':'alerta-dn'}}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
        <div>
          <div style="font-size:13px;font-weight:700;color:var(--text);font-family:var(--mono)">${{a.ticker}}</div>
          <div style="display:flex;gap:5px;margin-top:4px">
            <span style="font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;background:rgba(47,168,116,.1);color:#3cd28a;letter-spacing:.08em">${{badgeTxt}}</span>
            <span style="font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;background:rgba(113,128,150,.1);color:var(--text3);letter-spacing:.08em">${{badgeJanela}}</span>
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-size:18px;font-weight:800;color:${{clr}};font-family:var(--mono)">${{arrow}} ${{varStr}}</div>
          <div style="font-size:10px;color:var(--text3);margin-top:2px">${{a.data_ref}} → ${{a.data_atual}}</div>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text3);border-top:1px solid var(--border);padding-top:8px;margin-top:4px">
        <span>Atual: <strong style="color:var(--text);font-family:var(--mono)">${{a.atual.toFixed(3)}}%</strong></span>
        <span>Ref: <strong style="color:var(--text);font-family:var(--mono)">${{a.ref.toFixed(3)}}%</strong></span>
      </div>
    </div>`;
  }}).join('');
}}

function _notifRenderFR() {{
  const fatos = typeof FATOS_RELEVANTES !== 'undefined' ? FATOS_RELEVANTES : [];
  const q = (document.getElementById('notifFRSearch')?.value || '').toLowerCase().trim();
  let src = fatos;
  if (q) src = src.filter(f =>
    (f.empresa||'').toLowerCase().includes(q) ||
    (f.assunto||'').toLowerCase().includes(q) ||
    (f.denom_cvm||'').toLowerCase().includes(q)
  );
  const countEl = document.getElementById('notifFRCount');
  if (countEl) countEl.textContent = `${{src.length}} fato(s)`;
  const el = document.getElementById('notifFRCards');
  if (!el) return;
  if (!src.length) {{
    el.innerHTML = `<div class="fr-card" style="grid-column:1/-1;text-align:center;color:var(--text3);padding:40px;">${{fatos.length ? 'Nenhum resultado para a busca.' : 'Nenhum Fato Relevante encontrado para os emissores da carteira.'}}</div>`;
    return;
  }}
  el.innerHTML = src.slice(0, 80).map(f => {{
    const linkBtn = f.link
      ? `<a href="${{f.link}}" target="_blank" style="font-size:11px;color:#3cd28a;text-decoration:none;font-weight:600;">Abrir documento →</a>`
      : `<span style="font-size:11px;color:var(--text3);opacity:.5">Sem link</span>`;
    return `<div class="fr-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
        <div>
          <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#3cd28a;font-weight:700;margin-bottom:4px">${{f.empresa}}</div>
          <div style="font-size:11px;color:var(--text3);font-style:italic">${{f.denom_cvm || ''}}</div>
        </div>
        <span style="font-size:11px;color:var(--text3);white-space:nowrap;margin-left:12px;font-family:var(--mono)">${{f.data}}</span>
      </div>
      <div style="font-size:13px;font-weight:500;color:var(--text);line-height:1.55;margin-bottom:12px">${{f.assunto}}</div>
      <div style="display:flex;justify-content:flex-end;">${{linkBtn}}</div>
    </div>`;
  }}).join('');
}}

function buildNotificacoes() {{
  _notifRenderAlertas();
  _notifRenderFR();
}}

// ── SCORECARD ─────────────────────────────────────────────────────────────
function buildScorecard() {{
  const frame = document.getElementById('scorecardFrame');
  if (!frame) return;
  // Só carrega o src na primeira vez que a página é aberta
  // Nas visitas seguintes o iframe já está carregado — não recarrega
  if (!frame.src || frame.src === window.location.href || frame.src === 'about:blank') {{
    if (SCORECARD_SRC && SCORECARD_SRC !== 'null') {{
      frame.src = SCORECARD_SRC;
    }} else {{
      // Fallback: scorecard não encontrado — exibir mensagem dentro do iframe
      frame.srcdoc = '<html><body style="font-family:Montserrat,sans-serif;display:flex;'
        + 'align-items:center;justify-content:center;height:100vh;margin:0;'
        + 'background:#f4f5f0;color:#718096;flex-direction:column;gap:12px">'
        + '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#dde0d8" stroke-width="1.5">'
        + '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>'
        + '<p style="font-size:13px;font-weight:500">scorecard.html não encontrado.</p>'
        + '<p style="font-size:11px;opacity:.6">Execute gerar_scorecard.py primeiro.</p>'
        + '</body></html>';
    }}
  }}
}}
// ── DOURADO CHATBOT ───────────────────────────────────────────────────────
let douradoOpen = false;
function douradoToggle() {{
  douradoOpen = !douradoOpen;
  document.getElementById('douradoPanel').classList.toggle('open', douradoOpen);
  if (douradoOpen && document.querySelectorAll('.dourado-msg').length === 0) douradoWelcome();
  const dBtn = document.getElementById('douradoBtn');
  if (dBtn) dBtn.classList.toggle('pulsing', !douradoOpen);
}}
function douradoWelcome() {{
  douradoAddMsg('bot', 'Dourado aqui. Tenho acesso à carteira completa — posso comparar emissores, checar concentrações, revisar status de cobertura ou discutir qualquer posição. O que você quer analisar?');
}}
function _renderMd(raw) {{
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
  for (const line of lines) {{
    const bullet = line.match(/^[-•]\s(.+)/);
    const num    = line.match(/^(\d+)\.\s(.+)/);
    if (bullet) {{
      if (!inList) {{ out.push('<ul style="margin:4px 0;padding:0;list-style:none">'); inList=true; }}
      out.push(`<li style="margin:2px 0;padding-left:12px;position:relative"><span style="position:absolute;left:0;color:#b69d74">▸</span>${{bullet[1]}}</li>`);
    }} else if (num) {{
      if (!inList) {{ out.push('<ul style="margin:4px 0;padding:0;list-style:none">'); inList=true; }}
      out.push(`<li style="margin:2px 0;padding-left:16px;position:relative"><span style="position:absolute;left:0;color:#b69d74">${{num[1]}}.</span>${{num[2]}}</li>`);
    }} else {{
      if (inList) {{ out.push('</ul>'); inList=false; }}
      out.push(line === '' ? '<br>' : `<span>${{line}}</span><br>`);
    }}
  }}
  if (inList) out.push('</ul>');
  return out.join('');
}}
function douradoAddMsg(role, text, thinking=false) {{
  const msgs = document.getElementById('douradoMsgs');
  const div = document.createElement('div');
  div.className = `dourado-msg ${{role==='user'?'user':''}}`;
  if (role === 'bot') {{
    div.innerHTML = `<div class="dourado-avatar" style="width:28px;height:28px;font-size:12px;flex-shrink:0;">D</div>
      <div class="dourado-bubble" id="${{thinking?'douradoThinking':''}}">
        ${{thinking
          ? '<div class="dourado-thinking"><div class="dourado-dot"></div><div class="dourado-dot"></div><div class="dourado-dot"></div></div>'
          : _renderMd(text)
        }}</div>`;
  }} else {{
    div.innerHTML = `<div class="dourado-bubble">${{text.replace(/</g,'&lt;').replace(/>/g,'&gt;')}}</div>`;
  }}
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}}
function douradoChip(txt) {{
  const inp = document.getElementById('douradoInput');
  inp.value = txt;
  inp.focus();
  inp.setSelectionRange(txt.length, txt.length);
}}
// ── SLASH COMMAND PALETTE ─────────────────────────────────────────────────
const _SLASH_CMDS = [
  {{cmd:'/resumo',         desc:'Resumo geral da carteira'}},
  {{cmd:'/spread',         desc:'Spreads e alertas MAD'}},
  {{cmd:'/rating',         desc:'Distribuição de rating da carteira'}},
  {{cmd:'/setor',          desc:'Concentração por setor'}},
  {{cmd:'/duration',       desc:'Duration média ponderada'}},
  {{cmd:'/watch',          desc:'Emissores em watch / análise'}},
  {{cmd:'/stress',         desc:'Cenário de estresse: refinanciamento'}},
  {{cmd:'/vencimentos',    desc:'Perfil de vencimentos da carteira'}},
  {{cmd:'/alavancagem',    desc:'Ranking Dív.Liq/EBITDA (maior → menor)'}},
  {{cmd:'/cobertura',      desc:'Status de cobertura dos emissores'}},
  {{cmd:'/top',            desc:'Top N posições — ex: /top 5'}},
  {{cmd:'/carteira',       desc:'Filtra por carteira — ex: /carteira FI'}},
  {{cmd:'/emissor',        desc:'Síntese completa — ex: /emissor Klabin'}},
  {{cmd:'/comparar',       desc:'Compara emissores — ex: /comparar Klabin vs Suzano'}},
  {{cmd:'/grafico setor',  desc:'Gráfico de exposição por setor'}},
  {{cmd:'/clear',          desc:'Limpa o histórico do chat'}},
  {{cmd:'/help',           desc:'Lista todos os comandos disponíveis'}},
];
let _dspIdx=-1, _dspInp=null;
function _dspShow(inp){{
  const val=inp.value;
  if(!val.startsWith('/')){{_dspHide();return;}}
  const q=val.toLowerCase().trim();
  const list=q==='/'?_SLASH_CMDS:_SLASH_CMDS.filter(c=>c.cmd.startsWith(q));
  const pal=document.getElementById('dSlashPal');
  if(!pal||!list.length){{_dspHide();return;}}
  _dspInp=inp; _dspIdx=-1;
  const r=inp.getBoundingClientRect();
  pal.style.left=r.left+'px';
  pal.style.width=Math.max(r.width,320)+'px';
  pal.style.top=r.top+'px';
  pal.style.transform='translateY(-100%) translateY(-6px)';
  pal.innerHTML=list.map((c,i)=>
    `<div class="dsp-item" data-cmd="${{c.cmd}}" onmousedown="event.preventDefault();_dspPick('${{c.cmd}}')">
      <span class="dsp-cmd">${{c.cmd}}</span><span class="dsp-desc">${{c.desc}}</span>
    </div>`).join('');
  pal.style.display='block';
}}
function _dspHide(){{
  const pal=document.getElementById('dSlashPal');
  if(pal)pal.style.display='none';
  _dspIdx=-1; _dspInp=null;
}}
function _dspPick(cmd){{
  if(_dspInp){{_dspInp.value=cmd+' ';_dspInp.focus();_dspShow(_dspInp);}}
  else{{const i=document.getElementById('douradoInput');if(i){{i.value=cmd+' ';i.focus();}}}}
  _dspHide();
}}
function _dspKeyNav(e,inp){{
  const pal=document.getElementById('dSlashPal');
  if(!pal||pal.style.display==='none')return false;
  const items=pal.querySelectorAll('.dsp-item');
  if(!items.length)return false;
  if(e.key==='ArrowDown'){{e.preventDefault();_dspIdx=Math.min(_dspIdx+1,items.length-1);items.forEach((el,i)=>el.classList.toggle('dsp-active',i===_dspIdx));return true;}}
  if(e.key==='ArrowUp'){{e.preventDefault();_dspIdx=Math.max(_dspIdx-1,0);items.forEach((el,i)=>el.classList.toggle('dsp-active',i===_dspIdx));return true;}}
  if(e.key==='Enter'&&_dspIdx>=0){{const item=items[_dspIdx];if(item){{_dspPick(item.dataset.cmd);e.preventDefault();return true;}}}}
  if(e.key==='Escape'){{_dspHide();return true;}}
  return false;
}}
document.addEventListener('click',e=>{{
  if(!e.target.closest('#dSlashPal')&&!e.target.closest('.dourado-input'))_dspHide();
}});
// ── NLQ FRONTEND ENGINE v2 ───────────────────────────────────────────────
function _norm(s) {{ return (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^a-z0-9 ]/g,' '); }}

function _simRatio(a, b) {{
  if (!a||!b) return 0;
  const la=a.split(' ').filter(w=>w.length>1), lb=b.split(' ').filter(w=>w.length>1);
  if (!la.length||!lb.length) return 0;
  let hits=0;
  for (const wa of la) for (const wb of lb) {{
    if (wa===wb) hits+=1;
    else if (wa.length>3&&wb.length>3&&(wa.includes(wb)||wb.includes(wa))) hits+=0.7;
  }}
  return hits/Math.max(la.length,lb.length);
}}

function _ww(tok, norm) {{
  // whole-word check: tok must appear as a standalone word in norm (not as a substring)
  return new RegExp('(?:^|[\\\\s\\\\-\\\\/,])' + tok.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&') + '(?=[\\\\s\\\\-\\\\/,]|$)').test(norm);
}}

function _extractEmissorMulti(norm) {{
  // Returns all emissores mentioned in the input (for comparison queries)
  const emissores=[...new Set(ATIVOS.map(a=>a.emissor).filter(Boolean))];
  const found=[];
  // Pass 1: exact normalized full name as whole-word sequence
  for (const em of emissores) {{
    const emN=_norm(em);
    if(emN.length<3) continue;
    // require the full normalized name to appear as a whole-word phrase
    if(_ww(emN, norm)) {{ found.push(em); continue; }}
    // also check each word of the name independently as whole-word (all must match)
    const words=emN.split(' ').filter(w=>w.length>=4);
    if(words.length>0 && words.every(w=>_ww(w,norm))) found.push(em);
  }}
  if(found.length>=2) return found;
  // Pass 2: single dominant token (≥5 chars) as whole word — only if no ambiguity
  const candidates=[];
  for (const em of emissores) {{
    if(found.includes(em)) continue;
    const toks=_norm(em).split(' ').filter(w=>w.length>=5);
    if(toks.length>0 && toks.some(tok=>_ww(tok,norm))) candidates.push(em);
  }}
  // Filter out candidates whose token is a substring of another candidate's token
  const safe=candidates.filter(em=>{{
    const toks=_norm(em).split(' ').filter(w=>w.length>=5);
    return !candidates.some(other=>{{
      if(other===em) return false;
      const oN=_norm(other);
      return toks.some(tok=>oN.includes(tok)&&oN!==tok);
    }});
  }});
  safe.forEach(em=>{{ if(!found.includes(em)) found.push(em); }});
  return found;
}}

function _extractEmissor(norm) {{
  const emissores=[...new Set(ATIVOS.map(a=>a.emissor).filter(Boolean))];
  // Pass 1: exact normalized full name as whole-word sequence
  for (const em of emissores) {{
    const emN=_norm(em);
    if(emN.length<3) continue;
    if(_ww(emN,norm)) return em;
    const words=emN.split(' ').filter(w=>w.length>=4);
    if(words.length>0 && words.every(w=>_ww(w,norm))) return em;
  }}
  // Pass 2: all significant tokens (≥5 chars) match as whole words
  for (const em of emissores) {{
    const toks=_norm(em).split(' ').filter(w=>w.length>=5);
    if(!toks.length) continue;
    if(toks.every(tok=>_ww(tok,norm))) return em;
  }}
  // Pass 3: fuzzy — only exact whole-word token equality, threshold 0.65
  let best=null,bestScore=0;
  for (const em of emissores) {{
    const emToks=_norm(em).split(' ').filter(w=>w.length>=4);
    if(!emToks.length) continue;
    let hits=0;
    for(const et of emToks){{ if(_ww(et,norm)) hits+=1; }}
    const score=hits/emToks.length;
    if(score>bestScore&&score>=0.65){{bestScore=score;best=em;}}
  }}
  return best;
}}

// ── Geração dinâmica de frases por emissor ────────────────────────────────
// Para cada emissor da carteira, gera automaticamente frases para cada intent.
// Isso garante cobertura total sem precisar hardcodar cada nome.
function _buildEmissorPhrases() {{
  const emissores = [...new Set(ATIVOS.map(a=>a.emissor).filter(Boolean))];
  const n = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').trim();

  const sintese_kw   = [], sintese_ex   = [];
  const detalhe_kw   = [], detalhe_ex   = [];
  const grafico_kw   = [], grafico_ex   = [];
  const exposicao_kw = [], exposicao_ex = [];
  const evolucao_kw  = [], evolucao_ex  = [];
  const comparar_kw  = [];

  for (const em of emissores) {{
    const e = n(em);
    if (!e || e.length < 3) continue;

    // sintese_emissor: frases de análise completa/perfil
    sintese_kw.push(
      `analise completa de ${{e}}`, `analise completa da ${{e}}`, `analise completa do ${{e}}`,
      `perfil completo de ${{e}}`, `me conta tudo sobre ${{e}}`, `tudo sobre ${{e}}`,
      `como anda ${{e}}`, `como esta ${{e}}`, `o que ta acontecendo com ${{e}}`,
      `o que acontece com ${{e}}`, `me fala tudo sobre ${{e}}`, `due diligence de ${{e}}`,
      `deep dive em ${{e}}`, `quero tudo sobre ${{e}}`, `resume tudo de ${{e}}`,
      `briefing de ${{e}}`, `panorama de ${{e}}`, `situacao de ${{e}}`, `o que sei sobre ${{e}}`
    );
    sintese_ex.push(
      `analise completa de ${{e}}`, `me conta tudo sobre ${{e}}`, `como anda ${{e}}`,
      `o que ta acontecendo com ${{e}}`, `briefing de ${{e}}`
    );

    // detalhe_ativo: spread, yield, ntnb, caro/barato
    detalhe_kw.push(
      `spread de ${{e}}`, `spread da ${{e}}`, `spread do ${{e}}`,
      `yield de ${{e}}`, `yield da ${{e}}`, `quanto rende ${{e}}`,
      `ntnb de ${{e}}`, `ntnb da ${{e}}`, `ntnb ref de ${{e}}`,
      `${{e}} ta caro`, `${{e}} ta barato`, `${{e}} esta caro`, `${{e}} esta barato`,
      `${{e}} esta esticado`, `${{e}} esta comprimido`, `${{e}} esta atrativo`,
      `spread de ${{e}} esta caro`, `o papel de ${{e}} esta caro`
    );
    detalhe_ex.push(`spread de ${{e}}`, `ntnb de ${{e}}`, `${{e}} ta caro`);

    // grafico_spread: "plota spread de X", "grafico de spread de X"
    grafico_kw.push(
      `grafico de spread de ${{e}}`, `grafico do spread de ${{e}}`,
      `historico de spread de ${{e}}`, `historico spread de ${{e}}`,
      `plota spread de ${{e}}`, `plote spread de ${{e}}`, `mostra spread de ${{e}}`,
      `ver spread de ${{e}}`, `quero ver spread de ${{e}}`,
      `evolucao do spread de ${{e}}`, `serie de spread de ${{e}}`,
      `curva de spread de ${{e}}`, `timeline de spread de ${{e}}`
    );
    grafico_ex.push(
      `grafico de spread de ${{e}}`, `historico de spread de ${{e}}`
    );

    // exposicao_emissor: "quanto em X", "posicao em X"
    exposicao_kw.push(
      `posicao em ${{e}}`, `exposicao a ${{e}}`, `exposicao em ${{e}}`,
      `quanto em ${{e}}`, `quanto temos de ${{e}}`, `quanto tenho em ${{e}}`,
      `peso de ${{e}}`, `alocacao em ${{e}}`, `nossa posicao em ${{e}}`,
      `minha posicao em ${{e}}`, `saldo de ${{e}}`, `saldo em ${{e}}`
    );
    exposicao_ex.push(`posicao em ${{e}}`, `quanto em ${{e}}`);

    // evolucao_fundamento: "como evoluiu o ebitda de X"
    evolucao_kw.push(
      `evolucao do ebitda de ${{e}}`, `evolucao da margem de ${{e}}`,
      `evolucao do dl ebitda de ${{e}}`, `evolucao da alavancagem de ${{e}}`,
      `historico de ebitda de ${{e}}`, `tendencia de alavancagem de ${{e}}`,
      `como evoluiu o ebitda de ${{e}}`, `como foi a alavancagem de ${{e}}`,
      `vem caindo a margem de ${{e}}`, `vem subindo o ebitda de ${{e}}`,
      `foi melhorando o roe de ${{e}}`, `foi piorando o dl ebitda de ${{e}}`,
      `trajetoria financeira de ${{e}}`, `dl ebitda de ${{e}} historico`
    );
    evolucao_ex.push(
      `evolucao do ebitda de ${{e}}`, `tendencia de alavancagem de ${{e}}`
    );

    // comparar_emissores: "X vs", "X ou Y"
    comparar_kw.push(`${{e}} vs`, `${{e}} ou `);
  }}

  return {{
    sintese_kw, sintese_ex, detalhe_kw, detalhe_ex,
    grafico_kw, grafico_ex, exposicao_kw, exposicao_ex,
    evolucao_kw, evolucao_ex, comparar_kw
  }};
}}
const _EP = _buildEmissorPhrases();

const _INTENT_KW = {{
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
}};

const _EXEMPLOS = {{
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
}};

function _matchIntent(norm) {{
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
  if(_hasDeltaKW&&_hasCampo) return {{intent:'query_param',confidence:10}};
  // Detecta multi-filtro por presença de ≥2 critérios combinados
  const _hasFiltroNum = /acima de|abaixo de|maior que|menor que|acima|abaixo|\d+[,.]?\d*x|\d+[,.]?\d*%/.test(norm);
  const _hasStatus = ['aprovad','watch','em analise','reprovad','monitoramento','sob monitoramento','em acompanhamento','restricao','restricted','descoberto','sem cobertura'].some(w=>norm.includes(w));
  const _hasDuration = ['duration','prazo medio','maturidade','life','dv01'].some(w=>norm.includes(w));
  const _hasSpread = ['spread','yield','taxa de spread','taxa do spread','taxa cdix','taxa ipca','taxa selic','spreads'].some(w=>norm.includes(w));
  const _hasRating = ['rating aaa','rating aa','rating a','rating bbb','rating bb','rating b','rating','grau de investimento','high yield','junk','investment grade','grau especulativo','nota de credito'].some(w=>norm.includes(w));
  const _hasSetor = [...new Set(ATIVOS.map(a=>a.setor).filter(Boolean))].some(s=>norm.includes(_norm(s)));
  const _critCount = [_hasFiltroNum,_hasStatus,_hasDuration,_hasSpread,_hasRating].filter(Boolean).length;
  if(_critCount>=2||(_hasSetor&&(_hasStatus||_hasDuration||_hasSpread||_hasRating||_hasFiltroNum))) {{
    return {{intent:'multi_filtro',confidence:10}};
  }}
  const scores={{}};
  for (const [intent,kws] of Object.entries(_INTENT_KW)) {{
    scores[intent]=(scores[intent]||0);
    for (const kw of kws) {{ if(norm.includes(_norm(kw))) scores[intent]+=kw.includes(' ')?2:1; }}
  }}
  for (const [intent,exs] of Object.entries(_EXEMPLOS)) {{
    for (const ex of exs) {{ const sim=_simRatio(norm,_norm(ex)); if(sim>0.4) scores[intent]=(scores[intent]||0)+sim*2; }}
  }}
  const best=Object.entries(scores).sort((a,b)=>b[1]-a[1])[0];
  if(!best||best[1]<1) return {{intent:'fallback',confidence:0}};
  return {{intent:best[0],confidence:best[1]}};
}}

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

let _ctx={{lastIntent:null,lastEntities:{{}},pendingParam:null,lastList:null}};

function _resolveRef(norm) {{
  const REFS_PRONOMES=['isso','esse','esses','ela','ele','eles','elas','desse','dele','deles','nesse'];
  const REFS_DETALHE =['spread','taxa','duration','quanto rende','yield','retorno','spread dele','spread dela'];
  const REFS_FOLLOWUP=['e quanto','e o','e a','mais detalhes','me conta mais','aprofunda','detalha'];
  const ent=_ctx.lastEntities||{{}};
  const temP=REFS_PRONOMES.some(r=>norm.includes(_norm(r)));
  const temD=REFS_DETALHE.some(r=>norm.includes(_norm(r)));
  const temF=REFS_FOLLOWUP.some(r=>norm.includes(_norm(r)));
  if(!temP&&!temD&&!temF) return norm;
  if(Object.keys(ent).length===0) return norm;
  let aug=norm;
  if(temD&&ent.emissor&&!_extractEmissor(norm)) aug+=' '+_norm(ent.emissor);
  if(temP||temF) {{
    if(ent.setor)    aug+=' '+_norm(ent.setor);
    if(ent.emissor)  aug+=' '+_norm(ent.emissor);
    if(ent.carteira) aug+=' '+_norm(ent.carteira);
  }}
  return aug;
}}

// ═══════════════════════════════════════════════════════════════════════════════
// MOTOR PARAMÉTRICO — extrai indicador + operador + valor + período das queries
// Suporta: "DivLíq/EBITDA > 3.5x no setor elétrico", "spread que mais abriu em 2 anos"
// ═══════════════════════════════════════════════════════════════════════════════

const _FIN_CAMPOS = {{
  'divida liquida ebitda':  {{campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'}},
  'divliquida ebitda':      {{campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'}},
  'dl ebitda':              {{campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'}},
  'dl/ebitda':              {{campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'}},
  'alavancagem':            {{campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'}},
  'leverage':               {{campo:'DivLiquida/EBITDA',   label:'Dív.Líq./EBITDA',  fmt:'x',   tipo:'fund', limiar:3.5, limiarDir:'>'}},
  'liquidez corrente':      {{campo:'Liquidez Corrente',   label:'Liquidez Corrente', fmt:'x',   tipo:'fund', limiar:1.0, limiarDir:'<'}},
  'liquidez':               {{campo:'Liquidez Corrente',   label:'Liquidez Corrente', fmt:'x',   tipo:'fund', limiar:1.0, limiarDir:'<'}},
  'roe':                    {{campo:'ROE',                  label:'ROE',               fmt:'%',   tipo:'fund', limiar:null}},
  'roa':                    {{campo:'ROA',                  label:'ROA',               fmt:'%',   tipo:'fund', limiar:null}},
  'roic':                   {{campo:'ROIC',                 label:'ROIC',              fmt:'%',   tipo:'fund', limiar:null}},
  'margem ebitda':          {{campo:'Mg EBITDA 36M',        label:'Mg EBITDA',         fmt:'%',   tipo:'fund', limiar:null}},
  'mg ebitda':              {{campo:'Mg EBITDA 36M',        label:'Mg EBITDA',         fmt:'%',   tipo:'fund', limiar:null}},
  'margem liquida':         {{campo:'Mg Liquida TTM',       label:'Mg Líquida',        fmt:'%',   tipo:'fund', limiar:null}},
  'margem bruta':           {{campo:'Mg Bruta 36M',         label:'Mg Bruta',          fmt:'%',   tipo:'fund', limiar:null}},
  'fcf':                    {{campo:'FCF_TTM',              label:'FCF TTM',           fmt:'mi',  tipo:'fund', limiar:null}},
  'fluxo de caixa livre':   {{campo:'FCF_TTM',              label:'FCF TTM',           fmt:'mi',  tipo:'fund', limiar:null}},
  'fluxo de caixa':         {{campo:'FCF_TTM',              label:'FCF TTM',           fmt:'mi',  tipo:'fund', limiar:null}},
  'receita':                {{campo:'Receita_TTM',          label:'Receita TTM',       fmt:'mi',  tipo:'fund', limiar:null}},
  'ebitda':                 {{campo:'EBITDA_TTM',           label:'EBITDA TTM',        fmt:'mi',  tipo:'fund', limiar:null}},
  'divida liquida':         {{campo:'Divida Liquida',       label:'Dív. Líquida',      fmt:'mi',  tipo:'fund', limiar:null}},
  'divida bruta':           {{campo:'Divida Bruta',         label:'Dív. Bruta',        fmt:'mi',  tipo:'fund', limiar:null}},
  'divida':                 {{campo:'Divida Liquida',       label:'Dív. Líquida',      fmt:'mi',  tipo:'fund', limiar:null}},
  'lucro':                  {{campo:'Lucro Liquido_TTM',    label:'Lucro Líq. TTM',    fmt:'mi',  tipo:'fund', limiar:null}},
  'lucro liquido':          {{campo:'Lucro Liquido_TTM',    label:'Lucro Líq. TTM',    fmt:'mi',  tipo:'fund', limiar:null}},
  'despesa financeira':     {{campo:'Despesa Financeira_TTM',label:'Desp. Fin. TTM',   fmt:'mi',  tipo:'fund', limiar:null}},
  'spread delta':                {{campo:'spread',               label:'Δ Spread',              fmt:'bps', tipo:'spread_delta',  limiar:null}},
  'spread historico':            {{campo:'spread',               label:'Spread Histórico',      fmt:'bps', tipo:'spread_hist',   limiar:null}},
  'maior alta do spread':        {{campo:'spread',               label:'Maior Alta do Spread',  fmt:'bps', tipo:'spread_delta',  limiar:null}},
  'maior alta de spread':        {{campo:'spread',               label:'Maior Alta do Spread',  fmt:'bps', tipo:'spread_delta',  limiar:null}},
  'spread subiu mais':           {{campo:'spread',               label:'Maior Alta do Spread',  fmt:'bps', tipo:'spread_delta',  limiar:null}},
  'spread abriu mais':           {{campo:'spread',               label:'Maior Abertura Spread', fmt:'bps', tipo:'spread_delta',  limiar:null}},
  'maior abertura de spread':    {{campo:'spread',               label:'Maior Abertura Spread', fmt:'bps', tipo:'spread_delta',  limiar:null}},
  'maior abertura do spread':    {{campo:'spread',               label:'Maior Abertura Spread', fmt:'bps', tipo:'spread_delta',  limiar:null}},
  'abertura de spread':          {{campo:'spread',               label:'Abertura de Spread',    fmt:'bps', tipo:'spread_delta',  limiar:null}},
  'queda do spread':             {{campo:'spread',               label:'Maior Queda do Spread', fmt:'bps', tipo:'spread_delta',  limiar:null}},
  'spread fechou mais':          {{campo:'spread',               label:'Maior Fechamento Spread',fmt:'bps',tipo:'spread_delta',  limiar:null}},
  'maior alta da divida':        {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'maior alta do dl ebitda':     {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'maior alta dl ebitda':        {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'maior alta da alavancagem':   {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'maior alta de alavancagem':   {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'alavancagem subiu mais':      {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'alavancagem aumentou mais':   {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'piora de alavancagem':        {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'deterioracao da alavancagem': {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'delta dl ebitda':             {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'variacao da alavancagem':     {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'variacao do dl ebitda':       {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'queda da alavancagem':        {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'desalavancagem':              {{campo:'DivLiquida/EBITDA',    label:'Δ Dív.Líq./EBITDA',    fmt:'x',   tipo:'fund_delta',    limiar:null}},
  'maior alta do ebitda':        {{campo:'EBITDA_TTM',           label:'Δ EBITDA',              fmt:'mi',  tipo:'fund_delta',    limiar:null}},
  'maior queda do ebitda':       {{campo:'EBITDA_TTM',           label:'Δ EBITDA',              fmt:'mi',  tipo:'fund_delta',    limiar:null}},
  'variacao do ebitda':          {{campo:'EBITDA_TTM',           label:'Δ EBITDA',              fmt:'mi',  tipo:'fund_delta',    limiar:null}},
  'maior alta da receita':       {{campo:'Receita_TTM',          label:'Δ Receita',             fmt:'mi',  tipo:'fund_delta',    limiar:null}},
  'variacao da receita':         {{campo:'Receita_TTM',          label:'Δ Receita',             fmt:'mi',  tipo:'fund_delta',    limiar:null}},
}};

function _detectCampo(norm) {{
  const keys=Object.keys(_FIN_CAMPOS).sort((a,b)=>b.length-a.length);
  for(const k of keys){{if(norm.includes(_norm(k))) return _FIN_CAMPOS[k];}}
  return null;
}}

function _extractOpVal(norm) {{
  const opMap=[
    {{pats:['maior que','maior do que','acima de','superior a','mais que','acima dos','maior ou igual'],op:'>'}},
    {{pats:['menor que','menor do que','abaixo de','inferior a','menos que','abaixo dos','menor ou igual'],op:'<'}},
    {{pats:['igual a','exatamente'],op:'='}},
    {{pats:['entre'],op:'between'}},
  ];
  let op=null;
  for(const {{pats,op:o}} of opMap){{if(pats.some(p=>norm.includes(_norm(p)))){{op=o;break;}}}}
  const nums=[...norm.matchAll(/[-+]?\\d+[,.]?\\d*/g)].map(m=>parseFloat(m[0].replace(',','.')));
  if(op==='between'&&nums.length>=2) return {{op,v1:Math.min(nums[0],nums[1]),v2:Math.max(nums[0],nums[1])}};
  const v1=nums.length?nums[0]:null;
  if(!op&&v1!==null) op='>';
  return {{op,v1}};
}}

function _extractMeses(norm) {{
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
}}

const _finCache={{}};
function _matchToFin(emissor) {{
  if(_finCache[emissor]!==undefined) return _finCache[emissor];
  const ne=_norm(emissor);
  const keys=Object.keys(FIN_SERIES);
  for(const k of keys){{if(_norm(k)===ne){{_finCache[emissor]=k;return k;}}}}
  for(const k of keys){{const kn=_norm(k);if(kn.includes(ne)||ne.includes(kn)){{_finCache[emissor]=k;return k;}}}}
  const emToks=ne.split(' ').filter(w=>w.length>3);
  let best=null,bestS=0;
  for(const k of keys){{
    const kToks=_norm(k).split(' ').filter(w=>w.length>3);
    const hits=emToks.filter(t=>kToks.some(kt=>kt===t||(kt.length>4&&(kt.includes(t)||t.includes(kt))))).length;
    const score=hits/Math.max(emToks.length,1);
    if(score>bestS&&score>=0.45){{bestS=score;best=k;}}
  }}
  _finCache[emissor]=best;
  return best;
}}

function _lastVal(arr) {{
  if(!arr) return null;
  for(let i=arr.length-1;i>=0;i--){{if(arr[i]!=null&&!isNaN(arr[i]))return parseFloat(arr[i]);}}
  return null;
}}

function _fmtV(v,fmt) {{
  if(v==null) return 'N/D';
  if(fmt==='x') return v.toFixed(2)+'x';
  if(fmt==='%') return (v*100).toFixed(1)+'%';
  if(fmt==='mi') return 'R$ '+(v/1e6).toFixed(0)+' Mi';
  if(fmt==='bps') return v.toFixed(1)+'bps';
  if(fmt==='a') return v.toFixed(1)+'a';
  return v.toFixed(2);
}}

// Pre-check rápido: é uma query paramétrica?
function _isParamQuery(norm) {{
  const temCampo=_detectCampo(norm)!==null;
  if(!temCampo) return false;
  const {{op,v1}}=_extractOpVal(norm);
  const temMeses=_extractMeses(norm)!==null;
  const temSort=['mais abriram','mais fecharam','maiores','menores','mais alto','mais baixo','mais alavancados','mais alavancado','piores','melhores','que mais','ranking','top \\d','quais tem','quais estao com','emissores com','ativos com','empresas com','maior alta','maior queda','maior abertura','maior fechamento','mais subiram','mais caiu','mais aumentou','mais deteriorou','variacao de','variacao do','variacao da','piora de','desalavancagem','delta'].some(w=>new RegExp(w).test(norm));
  const temOpVal=op!==null&&v1!==null;
  return temOpVal||temMeses||temSort;
}}

// Detecta query de evolução temporal (tem campo + palavra de série temporal)
function _isEvolutionQuery(norm) {{
  const evoKWs=['evoluiu','evolucao do','evolucao da','tendencia de','historico de','serie temporal','ao longo do tempo','ao longo dos anos','como foi o','como foi a','como evoluiu','trajetoria de','progressao de'];
  return evoKWs.some(k=>norm.includes(_norm(k)))&&_detectCampo(norm)!==null;
}}

// Resolve referência posicional a item de lista anterior ("o 2", "o segundo", etc.)
function _resolveListDrilldown(norm) {{
  if(!_ctx.lastList||!_ctx.lastList.length) return null;
  // Desambigua: só ativa se a query for curta/referencial (sem campos, sem setores longos)
  if(norm.length>80) return null;
  const NUMWORDS={{'primeiro':1,'segunda':2,'segundo':2,'terceiro':3,'terceira':3,'quarto':4,'quarta':4,'quinto':5,'quinta':5,'sexto':6,'setimo':7,'oitavo':8,'nono':9}};
  for(const [w,i] of Object.entries(NUMWORDS)) {{
    if(norm.includes(w)&&i<=_ctx.lastList.length) return _ctx.lastList[i-1];
  }}
  const m=norm.match(/(?:^|o |a |no |na |do |da |item |numero )([1-9][0-9]?)(?:\s|$)/);
  if(m) {{
    const idx=parseInt(m[1])-1;
    if(idx>=0&&idx<_ctx.lastList.length) return _ctx.lastList[idx];
  }}
  return null;
}}

// ═══════════════════════════════════════════════════════════════════════════════

function _queryAtivos(intent,ent,userTxt) {{
  const cartStr   =ent.carteira||'Todas as Carteiras';
  const ativosCart=ent.carteira?ATIVOS.filter(a=>(a.carteira||'').toUpperCase().includes(ent.carteira.toUpperCase())):ATIVOS;
  const totalCart =ativosCart.reduce((s,a)=>s+(a.saldo||0),0);

  // ── QUERY PARAMÉTRICA ─────────────────────────────────────────────────────
  if (intent==='query_param') {{
    const norm=_norm(userTxt||'');
    const ci=_detectCampo(norm);
    if(!ci) return 'Qual indicador filtrar? (ex: Dív.Líq./EBITDA, liquidez corrente, ROE, spread, margem EBITDA)';
    const {{op,v1,v2}}=_extractOpVal(norm);
    const meses=_extractMeses(norm);
    const sortDesc=['mais abriram','mais fecharam','maiores','mais alto','piores','acima','ranking','top','que mais','mais alavancados','mais alavancado','maior alta','maior subida','maior escalada','maior salto','maior disparo','maior explosao','mais subiram','mais aumentaram','mais se deterioraram','maior deterioracao','maior widening','maior abertura','maior crescimento','maior expansao','maior piora'].some(w=>norm.includes(w.replace(' ','_').replace(' ','_'))||norm.includes(w));
    const topN=12;

    // ── SPREAD: variação no período ───────────────────────────────────────
    if(ci.tipo==='spread'||ci.tipo==='spread_delta'||ci.tipo==='spread_hist') {{
      let base=ativosCart.filter(a=>(a.saldo||0)>0);
      if(ent.setor) base=base.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase()));
      if(!base.length) return 'Não encontrei ativos'+(ent.setor?' no setor **'+ent.setor+'**':'')+' na carteira **'+cartStr+'**.';
      const periMs=meses||12;
      const hoje=new Date();
      const corte=new Date(hoje.getTime()-periMs*30*86400000);
      const periStr=periMs>=12?(periMs/12)+'ano(s)':periMs+'m';
      const itens=[];
      const vistos=new Set();
      for(const ativo of base) {{
        const em=ativo.emissor||ativo.ticker;
        if(vistos.has(em)) continue; vistos.add(em);
        const ts=SPREADS_TS[ativo.ticker];
        if(!ts||!ts.spread||!ts.datas) continue;
        const pairs=ts.datas.map((d,i)=>{{return{{d:new Date(d),v:ts.spread[i]}};}} ).filter(p=>p.v!=null);
        if(pairs.length<2) continue;
        const cur=pairs[pairs.length-1].v;
        let past=null;
        for(let i=pairs.length-2;i>=0;i--){{if(pairs[i].d<=corte){{past=pairs[i].v;break;}}}}
        if(past==null) past=pairs[0].v;
        const delta=(cur-past)*100;
        if(op&&v1!==null){{if(op==='>'&&delta<=v1)continue;if(op==='<'&&delta>=v1)continue;}}
        const saldo=base.filter(a=>(a.emissor||a.ticker)===em).reduce((s,a)=>s+(a.saldo||0),0);
        itens.push({{em,setor:ativo.setor||'N/D',cur,past,delta,saldo,ticker:ativo.ticker}});
      }}
      if(!itens.length) return 'Sem dados de spread suficientes'+(ent.setor?' em **'+ent.setor+'**':'')+' para o período.';
      itens.sort((a,b)=>sortDesc?b.delta-a.delta:a.delta-b.delta);
      const top=itens.slice(0,topN);
      const secStr=ent.setor?' · **'+ent.setor+'**':'';
      const threshStr=op&&v1!==null?' (filtro: Δ'+op+v1+'bps)':'';
      const labels=top.map(i=>i.em);
      const data=top.map(i=>parseFloat(i.delta.toFixed(1)));
      const colors=data.map(v=>v>0?'rgba(224,82,82,.75)':'rgba(74,191,203,.75)');
      const linhas=top.map((x,i)=>(i+1)+'. **'+x.em+'** ('+x.setor+'): '+(x.delta>=0?'+':'')+x.delta.toFixed(1)+'bps | atual: '+(x.cur*100).toFixed(0)+'bps → antes: '+(x.past*100).toFixed(0)+'bps').join('\\n');
      const _co={{color:'#718096',font:{{size:8}}}};
      _ctx.lastList=top.map(x=>({{em:x.em}}));
      return {{
        text:(sortDesc?'**Spreads que mais abriram**':'**Spreads que mais fecharam**')+' — '+periStr+secStr+threshStr+' · **'+cartStr+'**\\n\\n'+linhas+'\\n\\n*(Diga "análise completa do 1" para detalhar qualquer emissor.)*',
        chartTitulo:'Δ SPREAD '+periStr.toUpperCase()+(ent.setor?' · '+ent.setor.toUpperCase():''),
        chart:{{type:'bar',data:{{labels,datasets:[{{data,backgroundColor:colors,borderRadius:4,borderSkipped:false}}]}},options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{{duration:500}},plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>' '+(ctx.raw>0?'+':'')+ctx.raw+'bps'}}}}}},scales:{{x:{{ticks:{{..._co,callback:v=>v+'bps'}},grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{ticks:{{..._co}},grid:{{display:false}}}}}}}}}}
      }};
    }}

    // ── DELTA DE FUNDAMENTAIS (variação entre períodos) ──────────────────
    if(ci.tipo==='fund_delta') {{
      const periMs=meses||3;
      const periStr=periMs===3?'último trimestre':periMs===6?'último semestre':periMs===12?'último ano':periMs+'m';
      const hoje=new Date();
      const corte=new Date(hoje.getTime()-periMs*30.44*86400000);
      let base=ativosCart.filter(a=>(a.saldo||0)>0);
      if(ent.setor) base=base.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase()));
      const emList=[...new Set(base.map(a=>a.emissor).filter(Boolean))];
      const itens=[];
      for(const em of emList) {{
        const fk=_matchToFin(em); if(!fk) continue;
        const fd=FIN_SERIES[fk];   if(!fd) continue;
        const serie=fd[ci.campo];  if(!Array.isArray(serie)||serie.length<2) continue;
        const datas=fd['datas']||fd['Data']||fd['data']||null;
        if(!datas||!Array.isArray(datas)) continue;
        // Pega valor atual (último) e valor no corte
        let valCur=null,valPast=null;
        for(let i=datas.length-1;i>=0;i--) {{
          const d=new Date(datas[i]);
          if(valCur==null&&serie[i]!=null){{valCur=serie[i];}}
          if(d<=corte&&serie[i]!=null){{valPast=serie[i];break;}}
        }}
        if(valCur==null||valPast==null) continue;
        const delta=valCur-valPast;
        const saldo=base.filter(a=>a.emissor===em).reduce((s,a)=>s+(a.saldo||0),0);
        const rating=base.find(a=>a.emissor===em)?.['Rating Douro']||'N/D';
        const setor=base.find(a=>a.emissor===em)?.setor||'N/D';
        itens.push({{em,valCur,valPast,delta,saldo,rating,setor}});
      }}
      if(!itens.length) return 'Sem dados de **'+ci.label+'** com histórico suficiente para calcular variação no '+periStr+(ent.setor?' em **'+ent.setor+'**':'')+'.';
      // Detecta direção: maior alta vs maior queda
      const normQ=_norm(userTxt||'');
      const querQueda=['queda','caiu','cairam','reduziu','reduziram','desalavancou','desalavancaram','desalavancagem','fechou','fecharam','comprimiu','comprimiram','melhorou','melhoraram','menor','mais baixo','caindo','recuou','recuaram','diminuiu','diminuiram','contraiu','contrairam','encolheu','encolheram','declinou','declinaram','tightening','compressao','melhora','reducao','quem mais reduziu','quem mais caiu','quem mais melhorou','que mais caiu','que mais reduziu','que mais melhorou'].some(w=>normQ.includes(w));
      itens.sort((a,b)=>querQueda?a.delta-b.delta:b.delta-a.delta);
      const top=itens.slice(0,12);
      const secStr=ent.setor?' · **'+ent.setor+'**':'';
      const titulo=(querQueda?'**Maior queda**':'**Maior alta**')+' de **'+ci.label+'** — '+periStr+secStr+' — **'+cartStr+'**';
      const linhas=top.map((x,i)=>{{
        const sinal=x.delta>=0?'+':'';
        const cur=ci.fmt==='x'?x.valCur.toFixed(2)+'x':ci.fmt==='%'?(x.valCur*100).toFixed(1)+'%':ci.fmt==='mi'?'R$'+(x.valCur/1e6).toFixed(0)+'M':x.valCur.toFixed(2);
        const d=ci.fmt==='x'?sinal+x.delta.toFixed(2)+'x':ci.fmt==='%'?sinal+(x.delta*100).toFixed(1)+'pp':ci.fmt==='mi'?sinal+(x.delta/1e6).toFixed(0)+'M':sinal+x.delta.toFixed(2);
        const warn=ci.limiar!=null&&x.valCur>ci.limiar?' ⚠':'';
        return (i+1)+'. **'+x.em+'** ('+x.setor+' · '+x.rating+'): atual '+cur+warn+' | Δ: **'+d+'** — R$ '+(x.saldo/1e6).toFixed(2)+' Mi';
      }}).join('\\n');
      const labels=top.map(x=>x.em);
      const data=top.map(x=>{{
        if(ci.fmt==='%') return parseFloat((x.delta*100).toFixed(2));
        if(ci.fmt==='mi') return parseFloat((x.delta/1e6).toFixed(1));
        return parseFloat(x.delta.toFixed(3));
      }});
      const colors=data.map(v=>{{
        if(querQueda) return v<0?'rgba(74,191,203,.75)':'rgba(224,82,82,.75)';
        return v>0?'rgba(224,82,82,.75)':'rgba(74,191,203,.75)';
      }});
      const _co={{color:'#718096',font:{{size:8}}}};
      _ctx.lastList=top.map(x=>({{em:x.em}}));
      return {{
        text:titulo+'\\n\\n'+linhas+(itens.length>12?'\\n\\n*('+itens.length+' emissores com dados, top 12)*':'')+'\\n\\n*(Diga "análise completa do 1" para detalhar qualquer emissor.)*',
        chartTitulo:'Δ '+ci.label.toUpperCase()+' · '+periStr.toUpperCase()+(ent.setor?' · '+ent.setor.toUpperCase():''),
        chart:{{type:'bar',data:{{labels,datasets:[{{data,backgroundColor:colors,borderRadius:4,borderSkipped:false}}]}},options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{{duration:500}},plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>{{const v=ctx.raw;return ' Δ: '+(v>=0?'+':'')+v+(ci.fmt==='x'?'x':ci.fmt==='%'?'pp':ci.fmt==='mi'?'M':'');}}}}}}}},scales:{{x:{{ticks:{{..._co}},grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{ticks:{{..._co,font:{{size:9}}}},grid:{{display:false}}}}}}}}}}
      }};
    }}

    // ── INDICADOR FUNDAMENTALISTA (FIN_SERIES) ────────────────────────────
    if(ci.tipo==='fund') {{
      let base=ativosCart.filter(a=>(a.saldo||0)>0);
      if(ent.setor) base=base.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase()));
      const emList=[...new Set(base.map(a=>a.emissor).filter(Boolean))];
      const itens=[];
      for(const em of emList) {{
        const fk=_matchToFin(em); if(!fk) continue;
        const fd=FIN_SERIES[fk];   if(!fd) continue;
        const val=_lastVal(fd[ci.campo]); if(val==null) continue;
        if(op&&v1!==null) {{
          if(op==='>'&&val<=v1) continue;
          if(op==='<'&&val>=v1) continue;
          if(op==='='&&Math.abs(val-v1)>0.05) continue;
          if(op==='between'&&v2!=null&&(val<v1||val>v2)) continue;
        }}
        const saldo=base.filter(a=>a.emissor===em).reduce((s,a)=>s+(a.saldo||0),0);
        const rating=base.find(a=>a.emissor===em)?.[' Rating Douro']||base.find(a=>a.emissor===em)?.['Rating Douro']||'N/D';
        const setor=base.find(a=>a.emissor===em)?.setor||fd.setor||'N/D';
        itens.push({{em,val,saldo,rating,setor}});
      }}
      if(!itens.length) {{
        const tStr=op&&v1!==null?' com **'+ci.label+'** '+op+' '+_fmtV(v1,ci.fmt):'';
        return 'Nenhum emissor'+(ent.setor?' em **'+ent.setor+'**':'')+tStr+' encontrado com dados fundamentais no sistema. Verifique se a empresa tem demonstrações na CVM.';
      }}
      itens.sort((a,b)=>sortDesc?b.val-a.val:a.val-b.val);
      const top=itens.slice(0,topN);
      const threshStr=op&&v1!==null?' (filtro: '+op+' '+_fmtV(v1,ci.fmt)+')':'';
      const secStr=ent.setor?' · Setor **'+ent.setor+'**':'';
      const linhas=top.map((x,i)=>{{
        const warn=ci.limiar!=null&&((ci.limiarDir==='>'&&x.val>ci.limiar)||(ci.limiarDir==='<'&&x.val<ci.limiar))?' ⚠':'';
        return (i+1)+'. **'+x.em+'** ('+x.setor+' · '+x.rating+'): **'+_fmtV(x.val,ci.fmt)+'**'+warn+' — R$ '+(x.saldo/1e6).toFixed(2)+' Mi';
      }}).join('\\n');
      const labels=top.map(x=>x.em);
      const data=top.map(x=>{{
        if(ci.fmt==='%') return parseFloat((x.val*100).toFixed(1));
        if(ci.fmt==='mi') return parseFloat((x.val/1e6).toFixed(1));
        return parseFloat(x.val.toFixed(2));
      }});
      const colors=data.map(v=>{{
        if(!ci.limiar) return '#4abfcb';
        const over=(ci.limiarDir==='>'&&v>ci.limiar)||(ci.limiarDir==='<'&&v<ci.limiar);
        return over?'rgba(224,82,82,.75)':'rgba(74,191,203,.75)';
      }});
      const datasets=[{{data,backgroundColor:colors,borderRadius:4,borderSkipped:false}}];
      if(ci.limiar!=null){{
        const limVal=ci.fmt==='%'?ci.limiar*100:ci.fmt==='mi'?ci.limiar/1e6:ci.limiar;
        datasets.push({{type:'line',label:'Limiar ('+_fmtV(ci.limiar,ci.fmt)+')',data:Array(data.length).fill(limVal),borderColor:'#e0b43c',borderDash:[5,3],borderWidth:1.5,pointRadius:0,fill:false}});
      }}
      const _co={{color:'#718096',font:{{size:8}}}};
      const axCb=ci.fmt==='%'?'v=>v+\"%\"':ci.fmt==='x'?'v=>v+\"x\"':ci.fmt==='mi'?'v=>\"R$\"+v+\"M\"':'undefined';
      _ctx.lastList=top.map(x=>({{em:x.em}}));
      return {{
        text:'**'+ci.label+'**'+threshStr+secStr+' — **'+cartStr+'**\\n\\n'+linhas+(itens.length>topN?'\\n\\n*('+itens.length+' emissores encontrados, top '+topN+')*':'')+(itens.filter(x=>ci.limiar!=null&&((ci.limiarDir==='>'&&x.val>ci.limiar)||(ci.limiarDir==='<'&&x.val<ci.limiar))).length?'\\n\\n⚠ **'+itens.filter(x=>ci.limiar!=null&&((ci.limiarDir==='>'&&x.val>ci.limiar)||(ci.limiarDir==='<'&&x.val<ci.limiar))).length+' emissor(es)** no limiar de alerta de covenant.':''),
        chartTitulo:ci.label.toUpperCase()+(ent.setor?' · '+ent.setor.toUpperCase():''),
        chart:{{type:'bar',data:{{labels,datasets}},options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{{duration:500}},plugins:{{legend:{{display:datasets.length>1,position:'bottom',labels:{{color:'#8a9ab0',font:{{size:9}},boxWidth:8,padding:6}}}},tooltip:{{callbacks:{{label:ctx=>' '+ctx.raw+(ci.fmt==='x'?'x':ci.fmt==='%'?'%':'')}}}}}},scales:{{x:{{ticks:{{..._co}},grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{ticks:{{..._co,font:{{size:9}}}},grid:{{display:false}}}}}}}}}}
      }};
    }}

    return 'Não consegui processar esse indicador. Tente: "Dív.Líq./EBITDA maior que 3.5x", "spread que mais abriu no último ano", "ROE acima de 15%".';
  }}

  // ── MULTI-FILTRO ─────────────────────────────────────────────────────────
  if (intent==='multi_filtro') {{
    const norm=_norm(userTxt||'');
    // Extrai filtros
    const statusFiltro=(['aprovad','watch','em analise','reprovad','monitoramento'].find(w=>norm.includes(w))||null);
    const statusMap={{aprovad:'Aprovado',watch:'Watch','em analise':'Em análise',reprovad:'Reprovado',monitoramento:'Monitoramento'}};
    const statusVal=statusFiltro?statusMap[statusFiltro]:null;
    const setorFiltro=ent.setor||null;
    const ratingFiltro=ent.rating||null;
    // Duration
    let durOp=null,durVal=null;
    const durM=norm.match(/duration\s*(?:acima\s*de|maior\s*que|>)\s*(\d+[,.]?\d*)/);
    const durM2=norm.match(/duration\s*(?:abaixo\s*de|menor\s*que|<)\s*(\d+[,.]?\d*)/);
    if(durM){{durOp='>';durVal=parseFloat(durM[1].replace(',','.'));}}
    else if(durM2){{durOp='<';durVal=parseFloat(durM2[1].replace(',','.'));}}
    // Spread
    let spOp=null,spVal=null;
    const spM=norm.match(/spread\s*(?:acima\s*de|maior\s*que|>)\s*(\d+[,.]?\d*)/);
    const spM2=norm.match(/spread\s*(?:abaixo\s*de|menor\s*que|<)\s*(\d+[,.]?\d*)/);
    if(spM){{spOp='>';spVal=parseFloat(spM[1].replace(',','.'));}}
    else if(spM2){{spOp='<';spVal=parseFloat(spM2[1].replace(',','.'));}}
    // Acima/abaixo genérico (sem campo explícito)
    if(!durOp&&!spOp) {{
      const genM=norm.match(/(?:acima\s*de|maior\s*que)\s*(\d+[,.]?\d*)/);
      const genM2=norm.match(/(?:abaixo\s*de|menor\s*que)\s*(\d+[,.]?\d*)/);
      if(genM){{durOp='>';durVal=parseFloat(genM[1].replace(',','.'));}}
      else if(genM2){{durOp='<';durVal=parseFloat(genM2[1].replace(',','.'));}}
    }}
    // Aplica filtros
    let base=ativosCart.filter(a=>(a.saldo||0)>0);
    const filtrosApl=[];
    if(setorFiltro){{base=base.filter(a=>(a.setor||'').toLowerCase().includes(setorFiltro.toLowerCase()));filtrosApl.push('setor: '+setorFiltro);}}
    if(statusVal){{base=base.filter(a=>(a.Status||'').toLowerCase()===statusVal.toLowerCase());filtrosApl.push('status: '+statusVal);}}
    if(ratingFiltro){{base=base.filter(a=>(a['Rating Douro']||'').toUpperCase()===ratingFiltro.toUpperCase());filtrosApl.push('rating: '+ratingFiltro);}}
    if(durOp&&durVal!=null){{
      base=base.filter(a=>{{const d=Number(a.duration)||0;return durOp==='>'?d>durVal:d<durVal;}});
      filtrosApl.push('duration '+durOp+' '+durVal+'a');
    }}
    if(spOp&&spVal!=null){{
      base=base.filter(a=>{{const s=a.spread!=null?Number(a.spread):null;if(s==null||isNaN(s))return false;return spOp==='>'?s>spVal/100:s<spVal/100;}});
      filtrosApl.push('spread '+spOp+' '+spVal+'%');
    }}
    if(!filtrosApl.length) return 'Não identifiquei filtros na sua pergunta. Tente: "emissores aprovados com duration acima de 3", "spread abaixo de 1% e rating AA".';
    if(!base.length) return 'Nenhum ativo encontra todos os critérios: **'+filtrosApl.join(' + ')+'** em **'+cartStr+'**.';
    // Agrupa por emissor
    const emMap={{}};
    for(const a of base){{
      const em=a.emissor||a.ticker;
      if(!emMap[em])emMap[em]={{em,setor:a.setor||'N/D',status:a.Status||'N/D',rating:a['Rating Douro']||'N/D',saldo:0,durSum:0,durW:0,spread:null}};
      emMap[em].saldo+=(a.saldo||0);
      emMap[em].durSum+=(a.duration||0)*(a.saldo||0);
      emMap[em].durW+=(a.saldo||0);
      if(a.spread!=null&&!isNaN(Number(a.spread)))emMap[em].spread=Number(a.spread);
    }}
    const lista=Object.values(emMap).sort((a,b)=>b.saldo-a.saldo);
    const totalFilt=lista.reduce((s,x)=>s+x.saldo,0);
    const linhas=lista.slice(0,15).map((x,i)=>{{
      const dur=x.durW>0?(x.durSum/x.durW).toFixed(1)+'a':'—';
      const sp=x.spread!=null?(x.spread*100).toFixed(2)+'%':'—';
      return (i+1)+'. **'+x.em+'** ('+x.setor+') — R$ '+(x.saldo/1e6).toFixed(2)+' Mi | Duration: '+dur+' | Spread: '+sp+' | '+x.status;
    }}).join('\\n');
    const labels=lista.slice(0,12).map(x=>x.em);
    const data=lista.slice(0,12).map(x=>parseFloat((x.saldo/1e6).toFixed(2)));
    const colors=lista.slice(0,12).map(x=>x.status==='Aprovado'?'rgba(74,191,203,.75)':x.status==='Watch'?'rgba(240,180,50,.75)':'rgba(224,82,82,.75)');
    _ctx.lastList=lista.map(x=>({{em:x.em}}));
    const _co={{color:'#718096',font:{{size:8}}}};
    return {{
      text:'**Multi-filtro:** '+filtrosApl.join(' · ')+' — **'+cartStr+'**\\n\\n'+lista.length+' emissor(es) · R$ '+(totalFilt/1e6).toFixed(2)+' Mi\\n\\n'+linhas+(lista.length>15?'\\n\\n*(mostrando top 15 de '+lista.length+')*':'')+'\\n\\n*(Diga "análise completa do 1" para detalhar qualquer emissor.)*',
      chartTitulo:'MULTI-FILTRO: '+filtrosApl.join(' | ').toUpperCase(),
      chart:{{type:'bar',data:{{labels,datasets:[{{data,backgroundColor:colors,borderRadius:4,borderSkipped:false}}]}},options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{{duration:500}},plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>' R$ '+ctx.raw+'M'}}}}}},scales:{{x:{{ticks:{{..._co,callback:v=>'R$'+v+'M'}},grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{ticks:{{..._co,font:{{size:9}}}},grid:{{display:false}}}}}}}}}}
    }};
  }}

  if (intent==='exposicao_setor') {{
    if(!ent.setor) return 'Qual setor você quer verificar?';
    const matched=ativosCart.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase()));
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    const pct=totalCart>0?((saldo/totalCart)*100).toFixed(1):'0';
    const topEm=[...new Set(matched.map(a=>a.emissor).filter(Boolean))].slice(0,5).join(', ');
    return 'A exposição da carteira **'+cartStr+'** no setor de **'+ent.setor.toUpperCase()+'** é de **R$ '+(saldo/1e6).toFixed(2)+' Mi** ('+pct+'% da carteira).\\n\\n'+(topEm?'Principais emissores: '+topEm+'.\\n\\n':'')+'Quer ver cada emissor detalhado?';
  }}

  if (intent==='exposicao_rating') {{
    if(!ent.rating) return 'Qual rating você quer verificar?';
    const matched=ativosCart.filter(a=>(a['Rating Douro']||'').toUpperCase()===ent.rating.toUpperCase());
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    const pct=totalCart>0?((saldo/totalCart)*100).toFixed(1):'0';
    return 'A carteira **'+cartStr+'** possui **R$ '+(saldo/1e6).toFixed(2)+' Mi** ('+pct+'%) em ativos com Rating Douro **'+ent.rating+'**.\\n\\nQuer ver o breakdown de quais ativos compõem esse rating?';
  }}

  if (intent==='exposicao_emissor') {{
    if(!ent.emissor) return 'Qual emissor você quer verificar?';
    const matched=ativosCart.filter(a=>(a.emissor||'').toLowerCase().includes(ent.emissor.toLowerCase())&&(a.saldo||0)>0);
    if(!matched.length) return 'Não encontrei posição em **'+ent.emissor+'** na carteira **'+cartStr+'**.';
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    const pct=totalCart>0?((saldo/totalCart)*100).toFixed(1):'0';
    const dur=saldo>0?(matched.reduce((s,a)=>s+(a.duration||0)*(a.saldo||0),0)/saldo).toFixed(1):'—';
    return 'A posição em **'+ent.emissor+'** na carteira **'+cartStr+'** é de **R$ '+(saldo/1e6).toFixed(2)+' Mi** ('+pct+'% da carteira), duration média de '+dur+'a.\\n\\nQuer ver o spread atual contra a NTN-B?';
  }}

  if (intent==='overview_carteira') {{
    const validos=ativosCart.filter(a=>a.saldo>0);
    const aprovados=validos.filter(a=>a.Status==='Aprovado').reduce((s,a)=>s+(a.saldo||0),0);
    const emWatch=validos.filter(a=>['Em análise','Watch','Monitoramento'].includes(a.Status)).length;
    const nSet=new Set(validos.map(a=>a.setor).filter(Boolean)).size;
    return 'Overview — **'+cartStr+'**:\\n- **Total Crédito:** R$ '+(totalCart/1e6).toFixed(2)+' Mi\\n- **Ativos com saldo:** '+validos.length+'\\n- **Setores:** '+nSet+'\\n- **% Aprovados:** '+(totalCart>0?(aprovados/totalCart*100).toFixed(1):'0')+'%\\n- **Em watch/análise:** '+emWatch+' ativo(s)\\n\\nQuer o top 5 posições ou breakdown por setor?';
  }}

  if (intent==='top_exposicoes') {{
    const agrp={{}};
    ativosCart.forEach(a=>{{agrp[a.emissor||'N/D']=(agrp[a.emissor||'N/D']||0)+(a.saldo||0);}});
    const top=Object.entries(agrp).sort((a,b)=>b[1]-a[1]).slice(0,5);
    _ctx.lastList=top.map(t=>({{em:t[0]}}));
    return 'Maiores posições — **'+cartStr+'**:\\n'+top.map((t,i)=>(i+1)+'. **'+t[0]+'**: R$ '+(t[1]/1e6).toFixed(2)+' Mi ('+(totalCart>0?((t[1]/totalCart)*100).toFixed(1):'0')+'%)').join('\\n')+'\\n\\nQuer ver por setor ou rating? (Diga "me conta mais sobre o 1" para análise completa.)';
  }}

  if (intent==='status_cobertura') {{
    const matched=ativosCart.filter(a=>['Em análise','Watch','Monitoramento','Reprovado'].includes(a.Status)&&(a.saldo||0)>0);
    if(!matched.length) return 'Não há ativos em análise/watch/reprovado na carteira **'+cartStr+'**.';
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    _ctx.lastList=matched.slice(0,8).map(a=>({{em:a.emissor||a.ticker}}));
    return 'Há **'+matched.length+' ativo(s)** em análise/watch/monitoramento na carteira **'+cartStr+'**, totalizando **R$ '+(saldo/1e6).toFixed(2)+' Mi**.\\n\\n'+matched.slice(0,8).map((a,i)=>(i+1)+'. **'+(a.emissor||a.ticker)+'** ('+(a.ticker||'')+'): '+a.Status).join('\\n')+'\\n\\n*(Diga "análise completa do 1" para detalhes de qualquer emissor.)*';
  }}

  if (intent==='divergencia_rating') {{
    // Primary: check ATIVOS with active positions (field is 'Rating base S&P')
    const divs=ativosCart.filter(a=>{{
      const rd=(a['Rating Douro']||'').trim();
      const rm=(a['Rating base S&P']||'').trim();
      return rd&&rm&&rd!==rm&&(a.saldo||0)>0;
    }});
    // Secondary: check RANK_CORP coverage universe (fields: ratingDouro, ratingMkt)
    const rankDivs=(RANK_CORP||[]).filter(r=>{{
      const rd=(r.ratingDouro||'').trim();
      const rm=(r.ratingMkt||'').trim();
      return rd&&rm&&rd!==rm;
    }});
    const emissoresCart=new Set(ativosCart.map(a=>(a.emissor||'').toLowerCase()));
    // Rank divergences not already covered by cart positions
    const rankExtra=rankDivs.filter(r=>!emissoresCart.has((r.empresa||'').toLowerCase()));
    if(!divs.length&&!rankExtra.length) return 'Não encontrei divergências de rating na carteira **'+cartStr+'**.';
    let resp='';
    if(divs.length){{
      resp+='**'+divs.length+' ativo(s) com divergência** na carteira **'+cartStr+'**:\\n';
      resp+=divs.slice(0,8).map(a=>{{
        const rd=a['Rating Douro']||'N/D';
        const rm=a['Rating base S&P']||'N/D';
        const dir=rd>rm?'↑ Douro melhor':'↓ Douro mais conservador';
        return '- **'+(a.emissor||a.ticker)+'**: Douro='+rd+' | Mercado='+rm+' ('+dir+')';
      }}).join('\\n');
    }}
    if(rankExtra.length){{
      if(resp) resp+='\\n\\n';
      resp+='**'+rankExtra.length+' emissor(es) cobertos** com divergência (sem posição atual):\\n';
      resp+=rankExtra.slice(0,5).map(r=>{{
        const rd=r.ratingDouro||'N/D';
        const rm=r.ratingMkt||'N/D';
        const dir=rd>rm?'↑ Douro melhor':'↓ Douro mais conservador';
        return '- **'+r.empresa+'**: Douro='+rd+' | Mercado='+rm+' ('+dir+')';
      }}).join('\\n');
    }}
    return resp;
  }}

  if (intent==='duration_carteira') {{
    const validos=ativosCart.filter(a=>(a.saldo||0)>0&&a.duration!=null);
    const durPond=totalCart>0?(validos.reduce((s,a)=>s+(a.duration||0)*(a.saldo||0),0)/totalCart).toFixed(2):'—';
    const byS={{}};
    validos.forEach(a=>{{const s=a.setor||'N/D';if(!byS[s])byS[s]={{saldo:0,ds:0}};byS[s].saldo+=(a.saldo||0);byS[s].ds+=(a.duration||0)*(a.saldo||0);}});
    const topD=Object.entries(byS).sort((a,b)=>b[1].saldo-a[1].saldo).slice(0,4).map(([s,v])=>s+': '+(v.saldo>0?(v.ds/v.saldo).toFixed(1):'—')+'a').join(' | ');
    return 'Duration médio ponderado — **'+cartStr+'**: **'+durPond+' anos**\\n\\nPor setor (top 4): '+topD;
  }}

  if (intent==='comparar_emissores') {{
    const normIn=_norm(userTxt||'');
    // Use strict multi-emissor extraction to avoid false fuzzy matches
    const allFound=_extractEmissorMulti(normIn);
    const emList=allFound.length>=2 ? allFound : (()=>{{
      // fallback: first found + second pass excluding first
      const em1=_extractEmissor(normIn);
      if(!em1) return [];
      const normEx=normIn.replace(new RegExp(_norm(em1),'g'),' ');
      const em2=_extractEmissor(normEx);
      return em2&&em2!==em1?[em1,em2]:[em1];
    }})();
    if(emList.length===0) return 'Qual o primeiro emissor que você quer comparar?';
    if(emList.length===1) return 'Comparar **'+emList[0]+'** com qual outro emissor?';
    // Build comparison table for all emissors found
    const matches=emList.map(em=>ATIVOS.filter(a=>(a.emissor||'').toLowerCase()===em.toLowerCase()&&(a.saldo||0)>0));
    const valid=emList.filter((_,i)=>matches[i].length>0);
    if(valid.length<2) return 'Não encontrei posição em dois ou mais emissores citados na carteira.';
    const tot=ativosCart.reduce((s,a)=>s+(a.saldo||0),0);
    const linhas=valid.map((em,i)=>{{
      const ms=matches[emList.indexOf(em)];
      const s=ms.reduce((sum,a)=>sum+(a.saldo||0),0);
      const dur=s>0?(ms.reduce((sum,a)=>sum+(a.duration||0)*(a.saldo||0),0)/s).toFixed(1):'—';
      const sp=ms[0].spread!=null?Number(ms[0].spread).toFixed(3)+'%':'N/D';
      const p=tot>0?((s/tot)*100).toFixed(1):'—';
      return '- **'+em+'**: R$ '+(s/1e6).toFixed(2)+' Mi ('+p+'%) · Duration: '+dur+'a · Spread: '+sp+' · Rating Douro: '+(ms[0]['Rating Douro']||'N/D')+' · Status: '+(ms[0].Status||'N/D');
    }}).join('\\n');
    return 'Comparativo: **'+valid.join(' vs ')+'**\\n\\n'+linhas+'\\n\\nQuer aprofundar em algum deles?';
  }}

  if (intent==='detalhe_ativo') {{
    if(!ent.emissor) return 'Sobre qual emissor você quer ver o spread ou duration?';
    const matched=ativosCart.filter(a=>(a.emissor||'').toLowerCase().includes(ent.emissor.toLowerCase())&&(a.saldo||0)>0);
    if(!matched.length) return 'Não encontrei posição em **'+ent.emissor+'** na carteira **'+cartStr+'**.';
    const saldo=matched.reduce((s,a)=>s+(a.saldo||0),0);
    const durPond=saldo>0?(matched.reduce((s,a)=>s+(a.duration||0)*(a.saldo||0),0)/saldo).toFixed(2):'—';
    const tickers=matched.map(a=>a.ticker).filter(Boolean);
    let spreadInfo='N/D';
    const dispTs=tickers.filter(t=>SPREADS_TS[t]&&SPREADS_TS[t].spread);
    if(dispTs.length>0) {{
      const spVals=dispTs.map(t=>{{const arr=SPREADS_TS[t].spread.filter(v=>v!=null);return arr.length?arr[arr.length-1]:null;}}).filter(v=>v!=null);
      if(spVals.length) {{
        const spMed=spVals.reduce((s,v)=>s+v,0)/spVals.length;
        spreadInfo=spMed.toFixed(3)+'%';
        const allSp=dispTs.flatMap(t=>SPREADS_TS[t].spread.filter(v=>v!=null));
        if(allSp.length>5) {{
          const med=allSp.slice().sort((a,b)=>a-b)[Math.floor(allSp.length/2)];
          spreadInfo+=' (mediana hist: '+med.toFixed(3)+'% | '+(spMed-med>=0?'+':'')+(spMed-med).toFixed(3)+'% vs mediana)';
        }}
      }}
    }} else {{
      const spRaw=matched.find(a=>a.spread!=null&&!isNaN(Number(a.spread)))?.spread;
      if(spRaw!=null) spreadInfo=Number(spRaw).toFixed(3)+'%';
    }}
    const ntnbStr=matched.find(a=>a.ntnb_ref&&a.ntnb_ref!=='None'&&a.ntnb_ref!=='NaT')?.ntnb_ref||'—';
    const taxaStr=matched[0].valor!=null&&!isNaN(Number(matched[0].valor))?Number(matched[0].valor).toFixed(3)+'%':'N/D';
    return 'Detalhe — **'+ent.emissor+'**\\n\\n- **Saldo:** R$ '+(saldo/1e6).toFixed(2)+' Mi ('+matched.length+' ativo(s))\\n- **Taxa atual:** '+taxaStr+'\\n- **Spread vs NTN-B:** '+spreadInfo+'\\n- **NTN-B Ref:** '+ntnbStr+'\\n- **Duration média:** '+durPond+'a\\n- **Rating Douro:** '+(matched[0]['Rating Douro']||'N/D')+'\\n- **Status:** '+(matched[0].Status||'N/D')+'\\n\\nQuer ver a evolução histórica do spread?';
  }}

  if (intent==='analise_spreads') {{
    const normIn=_norm(userTxt||'');
    const caiu=['caiu','cairam','fechou','fecharam','comprimiu','comprimiram','tightening','baixo','mais baixo','melhores','abaixo'].some(w=>normIn.includes(w));
    let base=ativosCart.filter(a=>(a.saldo||0)>0);
    if(ent.setor) {{
      base=base.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase()));
      if(!base.length) return 'Não encontrei ativos no setor **'+ent.setor+'** com saldo.';
    }}
    const itens=[];
    for (const ativo of base) {{
      const spreadAt=ativo.spread!=null?Number(ativo.spread):null;
      if(spreadAt==null) continue;
      const ts=SPREADS_TS[ativo.ticker];
      let mediana=null,mad1=null,delta7d=null,zscore=null;
      if(ts) {{
        mediana=ts.mediana_spread!=null?Number(ts.mediana_spread):null;
        mad1=ts.mediana_mais_1mad_spread!=null?Number(ts.mediana_mais_1mad_spread):null;
        if(ts.spread&&ts.spread.length>8) {{const rec=ts.spread.filter(v=>v!=null);if(rec.length>8) delta7d=rec[rec.length-1]-rec[rec.length-8];}}
        if(mediana!=null&&mad1!=null){{const madV=mad1-mediana,std=madV*1.4826;zscore=std>0?(spreadAt-mediana)/std:null;}}
      }}
      itens.push({{ticker:ativo.ticker,emissor:ativo.emissor||ativo.ticker,setor:ativo.setor||'N/D',spreadAt,mediana,mad1,delta7d,zscore}});
    }}
    if(!itens.length) return 'Não há dados de spread suficientes na carteira **'+cartStr+'** para esta análise.';
    const ordenados=caiu?itens.sort((a,b)=>a.spreadAt-b.spreadAt):itens.sort((a,b)=>(b.zscore!=null?b.zscore:b.spreadAt)-(a.zscore!=null?a.zscore:a.spreadAt));
    const top=ordenados.slice(0,6);
    const titulo=(caiu?'**Spreads mais comprimidos**':'**Spreads mais elevados** (vs histórico)')+' — '+(ent.setor?'Setor '+ent.setor.toUpperCase():cartStr);
    const linhas=top.map((item,i)=>{{
      const zStr=item.zscore!=null?' | z='+item.zscore.toFixed(1):'';
      const d7Str=item.delta7d!=null?' | delta7d: '+(item.delta7d>=0?'+':'')+item.delta7d.toFixed(3)+'%':'';
      const alerta=item.mad1!=null&&item.spreadAt>item.mad1?' ⚠':'';
      return (i+1)+'. **'+item.emissor+'** ('+item.setor+')\\n   Spread: '+item.spreadAt.toFixed(3)+'% | Mediana: '+(item.mediana!=null?item.mediana.toFixed(3)+'%':'N/D')+zStr+d7Str+alerta;
    }}).join('\\n');
    const acimaMad=itens.filter(i=>i.mad1!=null&&i.spreadAt>i.mad1).length;
    return titulo+'\\n\\n'+linhas+(acimaMad>0?'\\n\\n⚠ **'+acimaMad+' ativo(s)** acima de +1 MAD — spreads historicamente elevados.':'\\nSpreads dentro da banda histórica normal.')+'\\n\\nQuer aprofundar em algum desses emissores?';
  }}

  // ── GRÁFICO DE SPREAD ────────────────────────────────────────────────────
  if (intent==='grafico_spread') {{
    if(!ent.emissor) return {{text:'Sobre qual emissor você quer ver o gráfico de spread? (ex: "gráfico spread de Klabin")'}};
    const mAtivos=ativosCart.filter(a=>(a.emissor||'').toLowerCase().includes(ent.emissor.toLowerCase())&&(a.saldo||0)>0);
    if(!mAtivos.length) return {{text:'Não encontrei posição em **'+ent.emissor+'** na carteira **'+cartStr+'**.'}};
    const tks=mAtivos.map(a=>a.ticker).filter(t=>SPREADS_TS[t]&&(SPREADS_TS[t].spread||[]).some(v=>v!=null));
    if(!tks.length) return {{text:'Não há série histórica de spread para **'+ent.emissor+'**. Verifique se há dados de CP carregados.'}};
    const bestTk=tks.reduce((b,t)=>{{const len=(SPREADS_TS[t].spread||[]).filter(v=>v!=null).length;return len>(SPREADS_TS[b]?(SPREADS_TS[b].spread||[]).filter(v=>v!=null).length:0)?t:b;}},tks[0]);
    const ts=SPREADS_TS[bestTk];
    const pairs=(ts.datas||[]).map((d,i)=>{{return{{d,v:ts.spread[i]}};}}).filter(p=>p.v!=null).slice(-120);
    if(!pairs.length) return {{text:'Série de spread vazia para **'+bestTk+'**.'}};
    const labels=pairs.map(p=>p.d);
    const data=pairs.map(p=>parseFloat(p.v));
    const med=ts.mediana_spread!=null?parseFloat(ts.mediana_spread):null;
    const mad1=ts.mediana_mais_1mad_spread!=null?parseFloat(ts.mediana_mais_1mad_spread):null;
    const cur=data[data.length-1];
    const deltaStr=med!=null?(' | '+(cur-med>=0?'+':'')+(cur-med).toFixed(3)+'% vs mediana'):'';
    const datasets=[{{label:bestTk,data,borderColor:'#4abfcb',backgroundColor:'rgba(74,191,203,.07)',tension:.35,pointRadius:0,borderWidth:2,fill:true}}];
    if(med!=null) datasets.push({{label:'Mediana ('+med.toFixed(3)+'%)',data:Array(data.length).fill(med),borderColor:'#b69d74',borderDash:[6,3],borderWidth:1.5,pointRadius:0,fill:false}});
    if(mad1!=null) datasets.push({{label:'+1MAD ('+mad1.toFixed(3)+'%)',data:Array(data.length).fill(mad1),borderColor:'#e05252',borderDash:[3,3],borderWidth:1,pointRadius:0,fill:false}});
    const _co={{color:'#718096',font:{{size:8}}}};
    return {{
      text:'Spread de **'+ent.emissor+'** ('+bestTk+') — últimas '+data.length+' observações.\\n\\nAtual: **'+cur.toFixed(3)+'%**'+deltaStr+(mad1!=null&&cur>mad1?'\\n\\n⚠ Spread **acima de +1 MAD** — historicamente elevado.':''),
      chartTitulo:'SPREAD · '+bestTk,
      chart:{{type:'line',data:{{labels,datasets}},options:{{responsive:true,maintainAspectRatio:false,animation:{{duration:500}},plugins:{{legend:{{display:true,position:'bottom',labels:{{color:'#8a9ab0',font:{{size:9}},boxWidth:8,padding:8}}}}}},scales:{{x:{{ticks:{{..._co,maxTicksLimit:6}},grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{ticks:{{..._co,callback:v=>v.toFixed(2)+'%'}},grid:{{color:'rgba(255,255,255,.04)'}}}}}}}}}}
    }};
  }}

  // ── GRÁFICO POR SETOR ────────────────────────────────────────────────────
  if (intent==='grafico_setor') {{
    const byS={{}};
    ativosCart.filter(a=>(a.saldo||0)>0).forEach(a=>{{const s=a.setor||'N/D';byS[s]=(byS[s]||0)+(a.saldo||0);}});
    const sorted=Object.entries(byS).sort((a,b)=>b[1]-a[1]);
    if(!sorted.length) return {{text:'Não há dados de setor disponíveis na carteira **'+cartStr+'**.'}};
    const labels=sorted.map(s=>s[0]);
    const data=sorted.map(s=>parseFloat((s[1]/1e6).toFixed(2)));
    const tot=sorted.reduce((s,x)=>s+x[1],0);
    const CORES=['#00677b','#b69d74','#4abfcb','#6b8cad','#d4a843','#5a7fa0','#88b3b0','#8b7355','#4a7c6f','#c4956a'];
    const pctLinhas=sorted.slice(0,6).map((s,i)=>(i+1)+'. **'+s[0]+'**: R$ '+(s[1]/1e6).toFixed(1)+' Mi ('+(tot>0?(s[1]/tot*100).toFixed(1):'0')+'%)').join('\\n');
    const _co={{color:'#718096',font:{{size:9}}}};
    return {{
      text:'Exposição por setor — **'+cartStr+'**:\\n\\n'+pctLinhas,
      chartTitulo:'DISTRIBUIÇÃO SETORIAL (R$ Mi)',
      chart:{{type:'bar',data:{{labels,datasets:[{{data,backgroundColor:labels.map((_,i)=>CORES[i%CORES.length]),borderRadius:4,borderSkipped:false}}]}},options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{{duration:500}},plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>' R$ '+ctx.raw+' Mi'}}}}}},scales:{{x:{{ticks:{{..._co,callback:v=>'R$'+v+'M'}},grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{ticks:{{..._co}},grid:{{display:false}}}}}}}}}}
    }};
  }}

  // ── CENÁRIO DE ESTRESSE / RISCO DE REFINANCIAMENTO ───────────────────────
  if (intent==='risco_estresse') {{
    const emVistos=new Set();
    const itens=[];
    for(const ativo of ativosCart.filter(a=>(a.saldo||0)>0)) {{
      const em=ativo.emissor;
      if(!em||emVistos.has(em)) continue;
      emVistos.add(em);
      const ts=SPREADS_TS[ativo.ticker];
      let zscore=null,spreadAt=null,med=null,mad1=null;
      if(ts&&ts.spread) {{
        const arr=ts.spread.filter(v=>v!=null);
        if(arr.length>5) {{
          spreadAt=arr[arr.length-1];
          med=ts.mediana_spread!=null?parseFloat(ts.mediana_spread):null;
          mad1=ts.mediana_mais_1mad_spread!=null?parseFloat(ts.mediana_mais_1mad_spread):null;
          if(med!=null&&mad1!=null){{const madV=mad1-med,std=madV*1.4826;zscore=std>0?(spreadAt-med)/std:null;}}
        }}
      }} else if(ativo.spread!=null) {{ spreadAt=parseFloat(ativo.spread); }}
      const statusRisco=['Em análise','Watch','Monitoramento','Reprovado'].includes(ativo.Status);
      const spStress=zscore!=null?zscore>1.5:(mad1!=null&&spreadAt!=null&&spreadAt>mad1);
      if(statusRisco||spStress) {{
        const saldo=ativosCart.filter(a=>(a.emissor||'')===em).reduce((s,a)=>s+(a.saldo||0),0);
        itens.push({{em,setor:ativo.setor||'N/D',status:ativo.Status,rating:ativo['Rating Douro']||'N/D',saldo,spreadAt,med,mad1,zscore,statusRisco,spStress}});
      }}
    }}
    if(!itens.length) return 'Nenhum sinal crítico de estresse identificado em **'+cartStr+'**. Spreads dentro da banda histórica e cobertura normalizada.';
    const totalStr=itens.reduce((s,e)=>s+e.saldo,0);
    const pct=totalCart>0?((totalStr/totalCart)*100).toFixed(1):'0';
    itens.sort((a,b)=>(b.zscore||0)-(a.zscore||0));
    const linhas=itens.slice(0,7).map(e=>{{
      const flags=[];
      if(e.spStress) flags.push('spread '+(e.zscore?'+'+e.zscore.toFixed(1)+'σ':'> +1MAD'));
      if(e.statusRisco) flags.push(e.status);
      return '- **'+e.em+'** ('+e.setor+' · '+e.rating+'): '+flags.join(' | ')+' — R$ '+(e.saldo/1e6).toFixed(2)+' Mi';
    }}).join('\\n');
    const nivel=itens.length>=4?'⚠ **Alerta de refinanciamento**':itens.length>=2?'🔍 **Atenção preventiva**':'📌 **Monitoramento pontual**';
    return nivel+' — **'+cartStr+'**\\n\\nExposição sob stress: **R$ '+(totalStr/1e6).toFixed(2)+' Mi** ('+pct+'% da carteira)\\n\\n'+linhas+'\\n\\n*Critérios: spread > +1.5σ histórico ou status crítico de cobertura. Emissores com maior risco de acesso ao mercado de capitais em cenário de alta de juros.*';
  }}

  // ── MAPA DE RISCO POR EMISSOR ────────────────────────────────────────────
  if (intent==='mapa_risco') {{
    const _ORD={{'CCC':0,'CC':1,'C':2,'D':3,'B-':4,'B':5,'B+':6,'BB-':7,'BB':8,'BB+':9,'BBB-':10,'BBB':11,'BBB+':12,'A-':13,'A':14,'A+':15,'AA-':16,'AA':17,'AA+':18,'AAA':19,'brCCC':0,'brCC':1,'brC':2,'brB-':4,'brB':5,'brB+':6,'brBB-':7,'brBB':8,'brBB+':9,'brBBB-':10,'brBBB':11,'brBBB+':12,'brA-':13,'brA':14,'brA+':15,'brAA-':16,'brAA':17,'brAA+':18,'brAAA':19}};
    const agrEm={{}};
    ativosCart.filter(a=>(a.saldo||0)>0).forEach(a=>{{
      const em=a.emissor||'N/D';
      if(!agrEm[em]) agrEm[em]={{saldo:0,rating:a['Rating Douro']||'N/D',status:a.Status||'N/D',setor:a.setor||'N/D'}};
      agrEm[em].saldo+=(a.saldo||0);
    }});
    const lista=Object.entries(agrEm).map(([em,v])=>{{return{{em,...v,riskScore:_ORD[v.rating]!=null?_ORD[v.rating]:20}};}});
    lista.sort((a,b)=>a.riskScore-b.riskScore);
    if(!lista.length) return 'Não há ativos com saldo na carteira **'+cartStr+'**.';
    const watchCount=lista.filter(e=>['Em análise','Watch','Monitoramento','Reprovado'].includes(e.status)).length;
    const linhas=lista.slice(0,10).map((e,i)=>{{
      const watchFlag=['Em análise','Watch','Monitoramento','Reprovado'].includes(e.status)?' ⚠':'';
      const riskEmoji=e.riskScore<=7?'🔴':e.riskScore<=11?'🟡':'🟢';
      return riskEmoji+' **'+e.em+'** · '+e.rating+' · '+e.setor+' · R$ '+(e.saldo/1e6).toFixed(2)+' Mi'+watchFlag;
    }}).join('\\n');
    _ctx.lastList=lista.slice(0,10).map(e=>({{em:e.em}}));
    return 'Mapa de risco — **'+cartStr+'** (do mais ao menos arriscado):\\n\\n'+linhas+(watchCount?'\\n\\n⚠ **'+watchCount+' emissor(es)** com status crítico de cobertura (Watch/Análise/Reprovado).':'\\n\\nCarteira sem alertas críticos de cobertura.')+'\\n\\n*(Diga "análise completa do 1" para detalhar.)*';
  }}

  // ── EVOLUÇÃO TEMPORAL DE FUNDAMENTAIS ──────────────────────────────────────
  if (intent==='evolucao_fundamento') {{
    const norm=_norm(userTxt||'');
    const ci=_detectCampo(norm);
    if(!ci) return 'Qual indicador você quer acompanhar? (ex: EBITDA, alavancagem, ROE, margem EBITDA)';
    const meses=_extractMeses(norm)||36;
    const cutDate=new Date(new Date().getTime()-meses*30.44*86400000);
    const _co={{color:'#718096',font:{{size:8}}}};
    // ── Por emissor específico ────────────────────────────────────────────
    const fk=ent.emissor?_matchToFin(ent.emissor):null;
    if(fk&&FIN_SERIES[fk]) {{
      const fd=FIN_SERIES[fk];
      const arr=fd[ci.campo]||[];
      const datas=fd.datas||[];
      const pairs=datas.map((d,i)=>{{return{{d:new Date(d),dStr:d,v:arr[i]}};}}).filter(p=>p.v!=null&&!isNaN(p.v)&&p.d>=cutDate);
      if(!pairs.length) return 'Sem dados de **'+ci.label+'** para **'+ent.emissor+'** no período solicitado.';
      const labels=pairs.map(p=>p.dStr);
      const data=pairs.map(p=>{{const v=parseFloat(p.v);return ci.fmt==='%'?parseFloat((v*100).toFixed(2)):ci.fmt==='mi'?parseFloat((v/1e6).toFixed(1)):parseFloat(v.toFixed(2));}});
      const lastV=parseFloat(pairs[pairs.length-1].v),firstV=parseFloat(pairs[0].v);
      const delta=lastV-firstV;
      const trendDelta=data.length>1?data[data.length-1]-data[0]:0;
      const trendLine=data.map((_,i)=>parseFloat((data[0]+trendDelta/(data.length-1||1)*i).toFixed(2)));
      const periStr=meses>=12?(meses/12).toFixed(0)+'a':meses+'m';
      const deltaFmt=(delta>=0?'+':'')+(ci.fmt==='%'?(delta*100).toFixed(1)+'%':ci.fmt==='x'?delta.toFixed(2)+'x':ci.fmt==='mi'?'R$ '+(delta/1e6).toFixed(0)+' Mi':delta.toFixed(2));
      return {{
        text:'Evolução de **'+ci.label+'** — **'+ent.emissor+'** ('+periStr+')\\n\\nAtual: **'+_fmtV(lastV,ci.fmt)+'** | Var. período: **'+deltaFmt+'** '+(delta>=0?'↑':'↓'),
        chartTitulo:'EVOLUÇÃO '+ci.label.toUpperCase()+' · '+ent.emissor.toUpperCase(),
        chart:{{type:'line',data:{{labels,datasets:[{{label:ci.label,data,borderColor:'#4abfcb',backgroundColor:'rgba(74,191,203,.10)',tension:.4,pointRadius:2,pointBackgroundColor:'#4abfcb',borderWidth:2,fill:true,spanGaps:true}},{{label:'Tendência',data:trendLine,borderColor:'rgba(182,157,116,.6)',borderDash:[5,4],borderWidth:1.5,pointRadius:0,fill:false}}]}},options:{{responsive:true,maintainAspectRatio:false,animation:{{duration:500}},plugins:{{legend:{{display:true,position:'bottom',labels:{{color:'#8a9ab0',font:{{size:9}},boxWidth:8,padding:6}}}}}},scales:{{x:{{ticks:{{..._co,maxTicksLimit:8}},grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{ticks:{{..._co,callback:v=>v+(ci.fmt==='x'?'x':ci.fmt==='%'?'%':'')}},grid:{{color:'rgba(255,255,255,.04)'}}}}}}}}}}
      }};
    }}
    // ── Por setor (média das empresas do portfólio) ───────────────────────
    if(ent.setor) {{
      const emSec=ativosCart.filter(a=>(a.setor||'').toLowerCase().includes(ent.setor.toLowerCase())&&(a.saldo||0)>0);
      const emList=[...new Set(emSec.map(a=>a.emissor).filter(Boolean))];
      const finKeys=emList.map(e=>_matchToFin(e)).filter(Boolean);
      if(!finKeys.length) return 'Não encontrei dados financeiros para empresas do setor **'+ent.setor+'** na carteira.';
      const allDates=[...new Set(finKeys.flatMap(k=>(FIN_SERIES[k].datas||[])))].filter(d=>new Date(d)>=cutDate).sort();
      if(!allDates.length) return 'Sem dados no período para o setor **'+ent.setor+'**.';
      const avgData=allDates.map(dt=>{{
        const vals=finKeys.map(k=>{{const idx=(FIN_SERIES[k].datas||[]).indexOf(dt);return idx>=0&&FIN_SERIES[k][ci.campo]&&FIN_SERIES[k][ci.campo][idx]!=null?parseFloat(FIN_SERIES[k][ci.campo][idx]):null;}}).filter(v=>v!=null);
        return vals.length?vals.reduce((s,v)=>s+v,0)/vals.length:null;
      }});
      const data=avgData.map(v=>v==null?null:ci.fmt==='%'?parseFloat((v*100).toFixed(2)):ci.fmt==='mi'?parseFloat((v/1e6).toFixed(1)):parseFloat(v.toFixed(2)));
      const lastV=avgData.filter(v=>v!=null).slice(-1)[0];
      const periStr=meses>=12?(meses/12).toFixed(0)+'a':meses+'m';
      return {{
        text:'Evolução de **'+ci.label+'** — Setor **'+ent.setor+'** (média portfólio, '+periStr+')\\n\\nÚltima média: **'+_fmtV(lastV||0,ci.fmt)+'**',
        chartTitulo:'EVOLUÇÃO '+ci.label.toUpperCase()+' · SETOR '+ent.setor.toUpperCase(),
        chart:{{type:'line',data:{{labels:allDates,datasets:[{{label:ci.label+' (média setor)',data,borderColor:'#b69d74',backgroundColor:'rgba(182,157,116,.10)',tension:.4,pointRadius:2,pointBackgroundColor:'#b69d74',borderWidth:2,fill:true,spanGaps:true}}]}},options:{{responsive:true,maintainAspectRatio:false,animation:{{duration:500}},plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{..._co,maxTicksLimit:8}},grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{ticks:{{..._co,callback:v=>v+(ci.fmt==='x'?'x':ci.fmt==='%'?'%':'')}},grid:{{color:'rgba(255,255,255,.04)'}}}}}}}}}}
      }};
    }}
    return 'Para ver a evolução de **'+ci.label+'**, informe o emissor (ex: "evolução de EBITDA da Klabin") ou o setor.';
  }}

  // ── COMPARAÇÃO COM MÉDIA DO SETOR ──────────────────────────────────────────
  if (intent==='comparar_setor') {{
    const norm=_norm(userTxt||'');
    const ci=_detectCampo(norm)||{{campo:'DivLiquida/EBITDA',label:'Dív.Líq./EBITDA',fmt:'x',tipo:'fund',limiar:3.5,limiarDir:'>'}};
    const fk=ent.emissor?_matchToFin(ent.emissor):null;
    const setorRef=ent.setor||(fk?FIN_SERIES[fk]&&FIN_SERIES[fk].setor:null)||(ent.emissor?((ativosCart.find(a=>(a.emissor||'').toLowerCase().includes(ent.emissor.toLowerCase()))||{{}}).setor||null):null);
    if(!setorRef&&!fk) return 'Para comparar com a média do setor, informe o emissor e/ou setor. Ex: "Klabin vs média de papel e celulose em alavancagem".';
    const peerAtivos=ativosCart.filter(a=>(a.setor||'').toLowerCase().includes((setorRef||'').toLowerCase())&&(a.saldo||0)>0);
    const peerEms=[...new Set(peerAtivos.map(a=>a.emissor).filter(Boolean))];
    const itens=[];
    for(const pe of peerEms) {{
      const pfk=_matchToFin(pe); if(!pfk) continue;
      const pv=_lastVal(FIN_SERIES[pfk][ci.campo]); if(pv==null) continue;
      const isTarget=!!(ent.emissor&&pe.toLowerCase().includes(ent.emissor.toLowerCase()));
      itens.push({{em:pe,val:pv,isTarget}});
    }}
    if(fk&&ent.emissor&&!itens.find(x=>x.isTarget)) {{
      const tv=_lastVal(FIN_SERIES[fk][ci.campo]);
      if(tv!=null) itens.push({{em:ent.emissor,val:tv,isTarget:true}});
    }}
    if(!itens.length) return 'Não encontrei dados de **'+ci.label+'** para comparação'+(setorRef?' no setor **'+setorRef+'**':'')+'.';;
    const avg=itens.reduce((s,x)=>s+x.val,0)/itens.length;
    const _fmtNum=v=>ci.fmt==='%'?parseFloat((v*100).toFixed(2)):ci.fmt==='mi'?parseFloat((v/1e6).toFixed(1)):parseFloat(v.toFixed(2));
    const labels=[...itens.map(x=>x.em),'⌀ Setor'];
    const data=[...itens.map(x=>_fmtNum(x.val)),_fmtNum(avg)];
    const colors=itens.map(x=>x.isTarget?'rgba(74,191,203,.9)':'rgba(74,191,203,.4)').concat(['rgba(182,157,116,.9)']);
    const sufx=ci.fmt==='x'?'x':ci.fmt==='%'?'%':'';
    const linhas=itens.map((x,i)=>{{
      const delta=x.val-avg;
      const ds=(delta>=0?'+':'')+(ci.fmt==='%'?(delta*100).toFixed(1)+'%':ci.fmt==='x'?delta.toFixed(2)+'x':'R$ '+(delta/1e6).toFixed(0)+' Mi');
      return (i+1)+'.'+(x.isTarget?' **':' ')+x.em+(x.isTarget?'**':'')+': **'+(ci.fmt==='%'?(x.val*100).toFixed(1)+'%':_fmtV(x.val,ci.fmt))+'** ('+ds+' vs ⌀)';
    }}).join('\\n');
    const _co={{color:'#718096',font:{{size:8}}}};
    return {{
      text:'**'+ci.label+'** vs média do setor'+(setorRef?' — **'+setorRef+'**':'')+' · **'+cartStr+'**\\n\\n'+linhas+'\\n\\n⌀ Setor: **'+(ci.fmt==='%'?(avg*100).toFixed(1)+'%':_fmtV(avg,ci.fmt))+'**',
      chartTitulo:ci.label.toUpperCase()+' vs ⌀ SETOR'+(setorRef?' · '+setorRef.toUpperCase():''),
      chart:{{type:'bar',data:{{labels,datasets:[{{data,backgroundColor:colors,borderRadius:4,borderSkipped:false}}]}},options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{{duration:500}},plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>' '+ctx.raw+sufx}}}}}},scales:{{x:{{ticks:{{..._co}},grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{ticks:{{..._co,font:{{size:9}}}},grid:{{display:false}}}}}}}}}}
    }};
  }}

  // ── SÍNTESE NARRATIVA DE EMISSOR ───────────────────────────────────────────
  if (intent==='sintese_emissor') {{
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
    if(bestTk) {{
      const ts=SPREADS_TS[bestTk];
      const arr=(ts.spread||[]).filter(v=>v!=null);
      if(arr.length) {{
        const cur=arr[arr.length-1];
        const med=ts.mediana_spread!=null?parseFloat(ts.mediana_spread):null;
        const mad1=ts.mediana_mais_1mad_spread!=null?parseFloat(ts.mediana_mais_1mad_spread):null;
        spreadTxt=(cur*100).toFixed(2)+'bps'+(med!=null?' (mediana: '+(med*100).toFixed(2)+'bps | '+(cur>=med?'+':'')+(((cur-med)*100).toFixed(2))+'bps vs hist.)':'');
        if(mad1!=null&&cur>mad1) spAlert=' ⚠ acima de +1MAD';
      }}
    }} else if(matched[0].spread!=null) {{
      spreadTxt=(Number(matched[0].spread)*100).toFixed(2)+'bps';
    }}
    const fk=_matchToFin(ent.emissor);
    let fundTxt='',FLAGS=[];
    if(fk&&FIN_SERIES[fk]) {{
      const fd=FIN_SERIES[fk];
      const dlE=_lastVal(fd['DivLiquida/EBITDA']),liq=_lastVal(fd['Liquidez Corrente']);
      const roe=_lastVal(fd['ROE']),mgE=_lastVal(fd['Mg EBITDA 36M']),fcf=_lastVal(fd['FCF_TTM']);
      const parts=[];
      if(dlE!=null){{parts.push('Dív./EBITDA: **'+_fmtV(dlE,'x')+'**'+(dlE>3.5?' ⚠':''));if(dlE>3.5)FLAGS.push('alavancagem elevada');}}
      if(liq!=null){{parts.push('Liquidez: **'+_fmtV(liq,'x')+'**'+(liq<1?' ⚠':''));if(liq<1)FLAGS.push('liquidez < 1x');}}
      if(roe!=null) parts.push('ROE: **'+_fmtV(roe,'%')+'**');
      if(mgE!=null) parts.push('Mg EBITDA: **'+_fmtV(mgE,'%')+'**');
      if(fcf!=null){{parts.push('FCF: **'+_fmtV(fcf,'mi')+'**');if(fcf<0)FLAGS.push('FCF negativo');}}
      if(parts.length) fundTxt='\\n\\n**Fundamentais:** '+parts.join(' · ');
    }}
    const ratingDiv=ratingD!=='N/D'&&ratingM!=='N/D'&&ratingD!==ratingM?' ⚠ *divergência*':'';
    const statusFlag=['Em análise','Watch','Monitoramento'].includes(status)?' ⚠':'';
    const flagStr=FLAGS.length?'\\n\\n⚠ **Alertas:** '+FLAGS.join(', ')+'.':'';
    return '**Análise — '+ent.emissor+'**\\n\\n- **Posição:** R$ '+(saldo/1e6).toFixed(2)+' Mi ('+pct+'% · **'+cartStr+'**)\\n- **Setor:** '+setor+'\\n- **Duration:** '+durPond+'a\\n- **Rating Douro:** '+ratingD+(ratingM!=='N/D'?' · S&P: '+ratingM+ratingDiv:'')+'\\n- **Status:** '+status+statusFlag+'\\n- **Spread:** '+spreadTxt+spAlert+fundTxt+flagStr+'\\n\\nQuer a evolução temporal ou comparar com o setor?';
  }}

  // ── MAPA DE VENCIMENTOS (proxy: duration) ──────────────────────────────────
  if (intent==='mapa_vencimentos') {{
    const buckets=[{{label:'< 1a',min:0,max:1}},{{label:'1–2a',min:1,max:2}},{{label:'2–3a',min:2,max:3}},{{label:'3–5a',min:3,max:5}},{{label:'5a+',min:5,max:Infinity}}];
    const result={{}},byBucketEm={{}};
    buckets.forEach(b=>{{result[b.label]=0;byBucketEm[b.label]=[];}});
    const agrEm={{}};
    ativosCart.filter(a=>(a.saldo||0)>0&&a.duration!=null).forEach(a=>{{
      const em=a.emissor||a.ticker;
      if(!agrEm[em]) agrEm[em]={{saldo:0,durSum:0,setor:a.setor||'N/D'}};
      agrEm[em].saldo+=(a.saldo||0);
      agrEm[em].durSum+=(a.duration||0)*(a.saldo||0);
    }});
    Object.entries(agrEm).forEach(([em,v])=>{{
      const dur=v.saldo>0?v.durSum/v.saldo:0;
      for(const b of buckets){{if(dur>=b.min&&dur<b.max){{result[b.label]+=v.saldo;byBucketEm[b.label].push(em);break;}}}}
    }});
    const total=Object.values(result).reduce((s,v)=>s+v,0);
    if(!total) return 'Não há ativos com duration na carteira **'+cartStr+'**.';
    const labels=buckets.map(b=>b.label);
    const data=labels.map(l=>parseFloat((result[l]/1e6).toFixed(2)));
    const CORES=['#e05252','#e0b43c','#4abfcb','#6b8cad','#00677b'];
    const linhas=labels.map((l,i)=>(i+1)+'. **'+l+'**: R$ '+(result[l]/1e6).toFixed(1)+' Mi ('+(total>0?((result[l]/total)*100).toFixed(1):'0')+'%)'+(byBucketEm[l].length?' — '+byBucketEm[l].slice(0,3).join(', ')+(byBucketEm[l].length>3?' + '+(byBucketEm[l].length-3)+' mais':''):'')).join('\\n');
    const warnPct=total>0?(result['< 1a']||0)/total:0;
    const warn=warnPct>0.15?'\\n\\n⚠ **'+((result['< 1a']||0)/1e6).toFixed(1)+' Mi ('+(warnPct*100).toFixed(0)+'%)** vencem/renovam em < 1 ano — risco de refinanciamento.':'';
    const _co={{color:'#718096',font:{{size:9}}}};
    return {{
      text:'Perfil de Vencimentos por Duration — **'+cartStr+'**\\n*(duration como proxy de prazo médio de risco de taxa)*\\n\\n'+linhas+warn,
      chartTitulo:'PERFIL DE VENCIMENTOS POR DURATION',
      chart:{{type:'bar',data:{{labels,datasets:[{{data,backgroundColor:CORES,borderRadius:4,borderSkipped:false}}]}},options:{{responsive:true,maintainAspectRatio:false,animation:{{duration:500}},plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>' R$ '+ctx.raw+' Mi'}}}}}},scales:{{x:{{ticks:{{..._co}},grid:{{color:'rgba(255,255,255,.04)'}}}},y:{{ticks:{{..._co,callback:v=>'R$'+v+'M'}},grid:{{color:'rgba(255,255,255,.04)'}}}}}}}}}}
    }};
  }}

  return _FALLBACKS[Math.floor(Math.random()*_FALLBACKS.length)];
}}

// ── CHAT CHART RENDERER ───────────────────────────────────────────────────────
function _addChatChartTo(container, titulo, cfg, cidSuffix) {{
  const wrap=document.createElement('div');
  wrap.className='dourado-msg';
  const cid='dChart_'+Date.now()+(cidSuffix||'');
  const h=cfg.options&&cfg.options.indexAxis==='y'?Math.max(160,Math.min(260,(cfg.data.labels||[]).length*28+40)):190;
  wrap.innerHTML=`<div class="dourado-avatar" style="width:28px;height:28px;font-size:12px;flex-shrink:0;">D</div><div class="dourado-bubble dourado-chart-bubble"><div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#b69d74;margin-bottom:8px;">${{titulo}}</div><div style="position:relative;height:${{h}}px;"><canvas id="${{cid}}"></canvas></div></div>`;
  container.appendChild(wrap);
  container.scrollTop=container.scrollHeight;
  requestAnimationFrame(()=>{{
    const cv=document.getElementById(cid);
    if(cv&&window.Chart) new Chart(cv,cfg);
  }});
}}
function _addChatChart(titulo, cfg) {{
  const msgs=document.getElementById('douradoMsgs');
  _addChatChartTo(msgs, titulo, cfg, '_s');
  if(_dfOpen){{
    const fullMsgs=document.getElementById('douradoFullMsgs');
    if(fullMsgs) _addChatChartTo(fullMsgs, titulo, cfg, '_f');
  }}
}}

function _nlqRespond(userTxt) {{
  if(!userTxt||!userTxt.trim()) return _FALLBACKS[0];
  const norm=_norm(userTxt);

  // ── Personalidade ────────────────────────────────────────────────────────
  if(_SAUDACOES_IN.some(s=>norm===_norm(s)||(norm.length<25&&norm.includes(_norm(s))))) {{
    let out=_SAUDACOES_OUT[Math.floor(Math.random()*_SAUDACOES_OUT.length)];
    const h=new Date().getHours();
    if(norm.includes('bom dia')||(h>=5&&h<12&&norm.length<15))       out=_SAUDACOES_OUT[5];
    else if(norm.includes('boa tarde')||(h>=12&&h<18&&norm.length<15)) out=_SAUDACOES_OUT[6];
    else if(norm.includes('boa noite')||(h>=18&&h<24&&norm.length<15)) out=_SAUDACOES_OUT[7];
    return out;
  }}
  if(_IDENTIDADE_IN.some(s=>norm.includes(_norm(s))))   return _IDENTIDADE_OUT[Math.floor(Math.random()*_IDENTIDADE_OUT.length)];
  if(_AGRADECIMENTOS_IN.some(s=>norm===_norm(s)||(norm.length<20&&norm.includes(_norm(s))))) return _AGRADECIMENTOS_OUT[Math.floor(Math.random()*_AGRADECIMENTOS_OUT.length)];
  if(_DESPEDIDAS_IN.some(s=>norm===_norm(s)||(norm.length<20&&norm.includes(_norm(s))))) return _DESPEDIDAS_OUT[Math.floor(Math.random()*_DESPEDIDAS_OUT.length)];
  // ── Fim personalidade ────────────────────────────────────────────────────

  const normRes=_resolveRef(norm);

  // Extrair entidades
  const ent={{}};
  const carts=[...new Set(ATIVOS.map(a=>a.carteira).filter(Boolean))];
  for(const c of carts){{if(normRes.includes(_norm(c))){{ent.carteira=c;break;}}}}
  const setsAll=[...new Set(ATIVOS.map(a=>a.setor).filter(Boolean))];
  for(const s of setsAll){{const sn=_norm(s),words=sn.split(' ').filter(w=>w.length>3);if(words.some(w=>normRes.includes(w))){{ent.setor=s;break;}}}}
  for(const r of ['AAA','AA+','AA','AA-','A+','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B-','CCC']){{if(normRes.includes(r.toLowerCase())){{ent.rating=r;break;}}}}
  ent.emissor=_extractEmissor(normRes)||null;

  // Pending param
  if(_ctx.pendingParam) {{
    const pp=_ctx.pendingParam;
    const entC=Object.assign({{}},pp.entities,ent);
    if(pp.missingParam==='emissor'&&ent.emissor){{_ctx.pendingParam=null;_ctx.lastIntent=pp.intent;_ctx.lastEntities=entC;return _queryAtivos(pp.intent,entC,userTxt);}}
    if(pp.missingParam==='setor'&&ent.setor){{_ctx.pendingParam=null;_ctx.lastIntent=pp.intent;_ctx.lastEntities=entC;return _queryAtivos(pp.intent,entC,userTxt);}}
    if(pp.missingParam==='rating'&&ent.rating){{_ctx.pendingParam=null;_ctx.lastIntent=pp.intent;_ctx.lastEntities=entC;return _queryAtivos(pp.intent,entC,userTxt);}}
    _ctx.pendingParam=null;
  }}

  // ── Pre-check drill-down contextual: "o 2", "o segundo", etc. ───────────
  const drillItem=_resolveListDrilldown(normRes);
  if(drillItem) {{
    const drillEnt=Object.assign({{}},_ctx.lastEntities,{{emissor:drillItem.em||drillItem}});
    return _queryAtivos('sintese_emissor',drillEnt,userTxt);
  }}

  // ── Pre-check evolução temporal (tem antes do paramétrico pois usa meses) ─
  if(_isEvolutionQuery(normRes)) {{
    _ctx.lastIntent='evolucao_fundamento';
    _ctx.lastEntities=ent;
    return _queryAtivos('evolucao_fundamento',ent,userTxt);
  }}

  // ── Pre-check paramétrico: detecta antes do intent normal ────────────────
  if(_isParamQuery(normRes)) {{
    _ctx.lastIntent='query_param';
    _ctx.lastEntities=ent;
    return _queryAtivos('query_param',ent,userTxt);
  }}

  const {{intent}}=_matchIntent(normRes);

  if(intent==='exposicao_setor'&&!ent.setor)   {{_ctx.pendingParam={{intent,entities:ent,missingParam:'setor'}};   return 'Qual setor você quer verificar? (ex: energia, infraestrutura, financeiro)';}}
  if(intent==='exposicao_emissor'&&!ent.emissor){{_ctx.pendingParam={{intent,entities:ent,missingParam:'emissor'}}; return 'Qual emissor você quer verificar?';}}
  if(intent==='exposicao_rating'&&!ent.rating)  {{_ctx.pendingParam={{intent,entities:ent,missingParam:'rating'}};  return 'Qual rating você quer verificar? (ex: AAA, AA, BBB, BB)';}}

  _ctx.lastIntent=intent;
  _ctx.lastEntities=ent;

  if(intent==='fallback') return _FALLBACKS[Math.floor(Math.random()*_FALLBACKS.length)];
  return _queryAtivos(intent,ent,userTxt);
}}

function _chipAndSend(txt) {{
  const inp = document.getElementById('douradoInput');
  inp.value = txt;
  douradoSend();
}}
function _douradoCmd(txt) {{
  const norm = txt.trim().toLowerCase();
  const cmd  = norm.split(/\s+/)[0];
  const args = txt.trim().slice(cmd.length).trim();
  const cmds = {{
    '/clear':     () => {{ document.getElementById('douradoMsgs').innerHTML=''; douradoWelcome(); return true; }},
    '/limpar':    () => {{ document.getElementById('douradoMsgs').innerHTML=''; douradoWelcome(); return true; }},
    '/help':      () => {{ douradoAddMsg('bot',
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
    ); return true; }},
    '/resumo':    () => {{ _chipAndSend('Resumo geral da carteira'); return true; }},
    '/spread':    () => {{ _chipAndSend('Quais spreads mais subiram? Alertas de MAD'); return true; }},
    '/rating':    () => {{ _chipAndSend('Distribuição de rating da carteira'); return true; }},
    '/setor':     () => {{ _chipAndSend('Concentração por setor'); return true; }},
    '/duration':  () => {{ _chipAndSend('Qual o duration médio da carteira?'); return true; }},
    '/watch':     () => {{ _chipAndSend('Quais emissores estão em watch ou análise?'); return true; }},
    '/stress':    () => {{ _chipAndSend('Cenário de estresse: quais emissores em risco de refinanciamento?'); return true; }},
    '/vencimentos':() => {{ _chipAndSend('Perfil de vencimentos da carteira'); return true; }},
    '/alavancagem':() => {{ _chipAndSend('Ranking de alavancagem — maior para menor'); return true; }},
    '/cobertura': () => {{ _chipAndSend('Status de cobertura dos emissores'); return true; }},
    '/grafico':   () => {{ if(args.includes('setor')) {{ _chipAndSend('Gráfico de exposição por setor'); return true; }} return false; }},
    '/top':       () => {{ const n=parseInt(args)||10; _chipAndSend('Maiores posições por emissor top '+n); return true; }},
    '/carteira':  () => {{ if(args) {{ _chipAndSend('Resumo da carteira '+args); return true; }} return false; }},
    '/emissor':   () => {{ if(args) {{ _chipAndSend('Análise completa da '+args); return true; }} return false; }},
    '/comparar':  () => {{ if(args) {{ _chipAndSend(args.replace(' vs ',' vs ')); return true; }} return false; }},
  }};
  const fn = cmds[cmd];
  if (fn) return fn();
  douradoAddMsg('bot', `Comando \`${{txt}}\` não reconhecido. Use \`/help\` para ver os disponíveis.`);
  return true;
}}

async function douradoSend() {{
  _dspHide();
  const input=document.getElementById('douradoInput');
  const txt=input.value.trim();
  if(!txt) return;
  input.value='';
  input.style.height='auto';
  if(txt.startsWith('/')) {{ if(_douradoCmd(txt)) return; }}
  douradoAddMsg('user',txt);
  const thinkingEl=douradoAddMsg('bot','',true);
  await new Promise(r=>setTimeout(r,150+Math.random()*200));
  try {{
    const resposta=_nlqRespond(txt);
    thinkingEl.remove();
    if(resposta&&typeof resposta==='object'&&resposta.text!==undefined) {{
      douradoAddMsg('bot',resposta.text);
      if(resposta.chart) setTimeout(()=>_addChatChart(resposta.chartTitulo||'',resposta.chart),60);
    }} else {{
      douradoAddMsg('bot',resposta);
    }}
  }} catch(e) {{
    thinkingEl.remove();
    douradoAddMsg('bot','Erro interno no processamento. Tente novamente.\\n\\n*'+e.message+'*');
  }}
}}
// ── SIDEBAR RAIL ─────────────────────────────────────────────────────────────
let _sidebarPinned = false;

function _setSidebarRail(shouldRail) {{
  const sb = document.querySelector('.sidebar');
  const main = document.querySelector('.main');
  if (!sb || !main) return;
  if (shouldRail && !_sidebarPinned) {{
    sb.classList.add('rail');
    main.classList.add('rail-active');
  }} else {{
    sb.classList.remove('rail');
    main.classList.remove('rail-active');
  }}
}}

function toggleSidebarPin() {{
  _sidebarPinned = !_sidebarPinned;
  const btn = document.getElementById('sidebarPinBtn');
  if (btn) btn.classList.toggle('pinned', _sidebarPinned);
  const activePage = document.querySelector('.page.active');
  const isHome = activePage && activePage.id === 'page-home';
  _setSidebarRail(!isHome);
}}

function _updateSidebarBadges() {{
  // Dourado pulse quando o chat está fechado
  const dBtn = document.getElementById('douradoBtn');
  if (dBtn) dBtn.classList.toggle('pulsing', !douradoOpen);
}}

// ── SEARCHABLE SELECT ─────────────────────────────────────────────────────
function initSearchableSelects() {{
  document.querySelectorAll('.filter-pill[data-prefix]').forEach(wrap => {{
    const label  = wrap.querySelector('.ss-label');
    const search = wrap.querySelector('.ss-search');
    const list   = wrap.querySelector('.ss-list');
    const sel    = wrap.querySelector('select');
    const prefix = wrap.dataset.prefix || '';
    const allTxt = wrap.dataset.all   || 'Todos';

    // Open / close on pill click
    wrap.addEventListener('click', e => {{
      if (e.target.closest('.ss-dropdown')) return;
      const isOpen = wrap.classList.contains('ss-open');
      document.querySelectorAll('.filter-pill.ss-open').forEach(w => {{
        w.classList.remove('ss-open');
        w.querySelector('.ss-search').value = '';
        w.querySelectorAll('.ss-opt').forEach(o => o.classList.remove('ss-hidden'));
      }});
      if (!isOpen) {{
        wrap.classList.add('ss-open');
        setTimeout(() => search.focus(), 40);
      }}
    }});

    // Live filter
    search.addEventListener('input', () => {{
      const q = search.value.toLowerCase();
      list.querySelectorAll('.ss-opt').forEach(o => {{
        o.classList.toggle('ss-hidden', !!q && !o.textContent.toLowerCase().includes(q));
      }});
    }});

    // Pick option
    list.querySelectorAll('.ss-opt').forEach(opt => {{
      opt.addEventListener('click', e => {{
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
      }});
    }});
  }});

  // Close on outside click
  document.addEventListener('click', e => {{
    if (!e.target.closest('.filter-pill[data-prefix]')) {{
      document.querySelectorAll('.filter-pill.ss-open').forEach(w => {{
        w.classList.remove('ss-open');
        w.querySelector('.ss-search').value = '';
        w.querySelectorAll('.ss-opt').forEach(o => o.classList.remove('ss-hidden'));
      }});
    }}
  }});
}}
// ── INIT ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {{
  initSearchableSelects();
  showPage('home', null);
  const hBtn = document.getElementById('homeBtnTopbar');
  if (hBtn) hBtn.classList.add('active');
  setTimeout(_updateSidebarBadges, 200);
}});

// ── WAR ROOM (Ctrl+Shift+R) ───────────────────────────────────────────────
(function() {{
  // Injeta CSS
  const style = document.createElement('style');
  style.textContent = `
    #warRoomOverlay {{
      display:none; position:fixed; inset:0; z-index:9999;
      background:#0a0e1a;
      flex-direction:column; align-items:stretch; justify-content:stretch;
      font-family:var(--font,'Montserrat',sans-serif);
      animation: wrFadeIn .25s ease;
    }}
    #warRoomOverlay.open {{ display:flex; }}
    @keyframes wrFadeIn {{ from{{opacity:0;transform:scale(.98)}} to{{opacity:1;transform:scale(1)}} }}
    .wr-header {{
      display:flex; align-items:center; justify-content:space-between;
      padding:18px 36px 14px;
      border-bottom:1px solid rgba(255,255,255,.06);
    }}
    .wr-logo {{ display:flex; align-items:center; gap:12px; }}
    .wr-logo-mark {{
      width:36px; height:36px; border-radius:8px;
      background:linear-gradient(135deg,#b69d74,#8a7355);
      display:flex; align-items:center; justify-content:center;
      font-size:16px; font-weight:800; color:#fff;
    }}
    .wr-logo-text {{ font-size:15px; font-weight:700; color:#e2e8f0; letter-spacing:.04em; }}
    .wr-logo-sub  {{ font-size:11px; color:#718096; font-weight:500; margin-top:1px; }}
    .wr-datetime  {{ font-size:12px; color:#718096; font-family:var(--mono,'monospace'); text-align:right; }}
    .wr-close {{
      cursor:pointer; color:#4a5568; font-size:22px; padding:4px 8px;
      border-radius:6px; transition:color .15s, background .15s;
      border:none; background:transparent;
    }}
    .wr-close:hover {{ color:#e2e8f0; background:rgba(255,255,255,.06); }}
    .wr-hint {{ font-size:10px; color:#2d3748; margin-left:8px; }}
    .wr-body {{
      flex:1; display:grid; padding:28px 36px 24px;
      gap:20px;
      grid-template-rows: auto 1fr auto;
    }}
    .wr-kpi-row {{
      display:grid;
      grid-template-columns: repeat(5, 1fr);
      gap:16px;
    }}
    .wr-kpi {{
      background:rgba(255,255,255,.03);
      border:1px solid rgba(255,255,255,.07);
      border-radius:14px; padding:20px 22px;
      display:flex; flex-direction:column; gap:6px;
      position:relative; overflow:hidden;
    }}
    .wr-kpi::after {{
      content:''; position:absolute; bottom:0; left:0; right:0; height:3px;
    }}
    .wr-kpi.green::after  {{ background:linear-gradient(90deg,#2fa874,#1d7a55); }}
    .wr-kpi.red::after    {{ background:linear-gradient(90deg,#d94141,#a02f2f); }}
    .wr-kpi.gold::after   {{ background:linear-gradient(90deg,#b69d74,#8a7355); }}
    .wr-kpi.neutral::after{{ background:linear-gradient(90deg,#4a5568,#2d3748); }}
    .wr-kpi-label  {{ font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.1em; color:#4a5568; }}
    .wr-kpi-value  {{ font-family:var(--mono,'monospace'); font-size:36px; font-weight:700; color:#e2e8f0; line-height:1; }}
    .wr-kpi-sub    {{ font-size:12px; color:#718096; margin-top:2px; }}
    .wr-kpi-badge  {{
      display:inline-flex; align-items:center; gap:5px;
      padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700;
      margin-top:4px; width:fit-content;
    }}
    .wr-kpi-badge.green  {{ background:rgba(47,168,116,.15); color:#2fa874; }}
    .wr-kpi-badge.red    {{ background:rgba(217,65,65,.15);  color:#d94141; }}
    .wr-kpi-badge.gold   {{ background:rgba(182,157,116,.15);color:#b69d74; }}
    .wr-middle {{
      display:grid; grid-template-columns:1fr 1fr; gap:20px;
    }}
    .wr-panel {{
      background:rgba(255,255,255,.025);
      border:1px solid rgba(255,255,255,.06);
      border-radius:14px; padding:20px 24px; overflow:hidden;
    }}
    .wr-panel-title {{
      font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.1em;
      color:#4a5568; margin-bottom:16px;
    }}
    .wr-emissores-grid {{
      display:grid; grid-template-columns:1fr 1fr; gap:8px 24px;
    }}
    .wr-em-row {{
      display:flex; align-items:center; gap:8px; padding:4px 0;
      border-bottom:1px solid rgba(255,255,255,.04);
    }}
    .wr-em-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
    .wr-em-name {{ flex:1; font-size:13px; color:#a0aec0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .wr-em-val  {{ font-family:var(--mono,'monospace'); font-size:13px; color:#e2e8f0; font-weight:600; }}
    .wr-watch-list {{ display:flex; flex-direction:column; gap:6px; }}
    .wr-watch-item {{
      display:flex; align-items:center; justify-content:space-between;
      padding:8px 12px; border-radius:8px;
      background:rgba(182,157,116,.06); border:1px solid rgba(182,157,116,.12);
    }}
    .wr-watch-name {{ font-size:14px; color:#e2e8f0; font-weight:600; }}
    .wr-watch-rating {{ font-family:var(--mono,'monospace'); font-size:13px; color:#b69d74; }}
    .wr-watch-status {{ font-size:11px; color:#b69d74; font-weight:600; }}
    .wr-footer {{
      display:flex; align-items:center; justify-content:space-between;
      padding-top:12px; border-top:1px solid rgba(255,255,255,.04);
      font-size:11px; color:#2d3748;
    }}
    .wr-semaforo-row {{ display:flex; gap:12px; align-items:center; }}
    .wr-semaforo {{ display:flex; align-items:center; gap:6px; }}
    .wr-sem-dot {{ width:10px; height:10px; border-radius:50%; }}
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
  function _wrTick() {{
    const el = document.getElementById('wrDatetime');
    if (!el) return;
    const now = new Date();
    el.innerHTML = now.toLocaleDateString('pt-BR',{{weekday:'long',day:'2-digit',month:'long',year:'numeric'}})
      + '<br>' + now.toLocaleTimeString('pt-BR');
  }}

  function buildWarRoom() {{
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
        <div class="wr-kpi-value">${{fM(total)}}</div>
        <div class="wr-kpi-sub">${{ativos.length}} ativos · ${{nEmissores}} emissores</div>
      </div>
      <div class="wr-kpi green">
        <div class="wr-kpi-label">Aprovados</div>
        <div class="wr-kpi-value">${{pctAprov}}%</div>
        <div class="wr-kpi-badge green">▲ ${{fM(aprovados)}}</div>
      </div>
      <div class="wr-kpi ${{parseFloat(pctReprov)>10?'red':'neutral'}}">
        <div class="wr-kpi-label">Reprovados</div>
        <div class="wr-kpi-value">${{pctReprov}}%</div>
        <div class="wr-kpi-badge red">${{fM(reprovados)}}</div>
      </div>
      <div class="wr-kpi gold">
        <div class="wr-kpi-label">Em Análise / Watch</div>
        <div class="wr-kpi-value">${{pctAnalise}}%</div>
        <div class="wr-kpi-badge gold">${{fM(analise)}}</div>
      </div>
      <div class="wr-kpi neutral">
        <div class="wr-kpi-label">Duration Média</div>
        <div class="wr-kpi-value">${{durPond}}<span style="font-size:18px;color:#4a5568"> anos</span></div>
        <div class="wr-kpi-sub">Ponderada por saldo</div>
      </div>
    `;

    // Top emissores
    const byE = {{}};
    ativos.forEach(a => {{ byE[a.emissor||'S/N'] = (byE[a.emissor||'S/N']||0)+(a.saldo||0); }});
    const topEm = Object.entries(byE).sort((a,b)=>b[1]-a[1]).slice(0,10);
    const corEm = em => {{
      const st = (ativos.find(a=>a.emissor===em)?.Status||'').trim();
      if (st==='Aprovado')  return '#2fa874';
      if (st==='Reprovado') return '#d94141';
      return '#b69d74';
    }};
    document.getElementById('wrEmissores').innerHTML = topEm.map(([em,v]) =>
      `<div class="wr-em-row">
        <div class="wr-em-dot" style="background:${{corEm(em)}}"></div>
        <div class="wr-em-name" title="${{em}}">${{em}}</div>
        <div class="wr-em-val">${{fM(v)}}</div>
      </div>`
    ).join('');

    // Watch list
    const watchAtivos = ativos.filter(a => STATUS_ANALISE.includes(a.Status));
    const byEW = {{}};
    watchAtivos.forEach(a => {{
      if (!byEW[a.emissor]) byEW[a.emissor] = {{saldo:0,status:a.Status,rating:a.ratingDouro||a.Rating||'—'}};
      byEW[a.emissor].saldo += (a.saldo||0);
    }});
    const watchItems = Object.entries(byEW).sort((a,b)=>b[1].saldo-a[1].saldo).slice(0,6);
    const wEl = document.getElementById('wrWatchList');
    if (watchItems.length===0) {{
      wEl.innerHTML = '<div style="color:#2d3748;font-size:13px;padding:8px 0">Nenhum emissor em watch ou análise.</div>';
    }} else {{
      wEl.innerHTML = watchItems.map(([em,info]) =>
        `<div class="wr-watch-item">
          <div class="wr-watch-name">${{em}}</div>
          <div style="display:flex;gap:12px;align-items:center">
            <div class="wr-watch-rating">${{info.rating}}</div>
            <div class="wr-watch-status">${{info.status}}</div>
            <div class="wr-em-val" style="font-size:12px;color:#718096">${{fM(info.saldo)}}</div>
          </div>
        </div>`
      ).join('');
    }}

    // Semáforo
    document.getElementById('wrSemaforo').innerHTML = `
      <div class="wr-semaforo"><div class="wr-sem-dot" style="background:#2fa874"></div><span style="color:#4a5568">Aprovado (${{pctAprov}}%)</span></div>
      <div class="wr-semaforo"><div class="wr-sem-dot" style="background:#b69d74"></div><span style="color:#4a5568">Watch/Análise (${{pctAnalise}}%)</span></div>
      <div class="wr-semaforo"><div class="wr-sem-dot" style="background:#d94141"></div><span style="color:#4a5568">Reprovado (${{pctReprov}}%)</span></div>
    `;
  }}

  let _wrInterval = null;

  window.openWarRoom = function() {{
    overlay.classList.add('open');
    buildWarRoom();
    _wrTick();
    _wrInterval = setInterval(_wrTick, 1000);
    document.body.style.overflow = 'hidden';
  }};

  window.closeWarRoom = function() {{
    overlay.classList.remove('open');
    clearInterval(_wrInterval);
    document.body.style.overflow = '';
  }};

  document.addEventListener('keydown', e => {{
    if (e.ctrlKey && e.shiftKey && e.key === 'R') {{
      e.preventDefault();
      overlay.classList.contains('open') ? closeWarRoom() : openWarRoom();
    }}
    if (e.key === 'Escape' && overlay.classList.contains('open')) {{
      closeWarRoom();
    }}
  }});
}})();

// ── HIDDEN FEATURES CSS BASE ──────────────────────────────────────────────
// ── BUSCA GLOBAL (Ctrl+P) ─────────────────────────────────────────────────
(function() {{
  const _css = `
    #gspBackdrop {{
      display:none; position:fixed; inset:0; z-index:10000;
      background:rgba(5,8,16,.72); backdrop-filter:blur(6px);
      align-items:flex-start; justify-content:center; padding-top:12vh;
    }}
    #gspBackdrop.open {{ display:flex; }}
    #gspModal {{
      width:min(680px,92vw); background:#0f1623;
      border:1px solid rgba(182,157,116,.25); border-radius:18px;
      box-shadow:0 32px 80px rgba(0,0,0,.7), 0 0 0 1px rgba(255,255,255,.04);
      overflow:hidden; animation:gspIn .18s cubic-bezier(.16,1,.3,1);
    }}
    @keyframes gspIn {{ from{{opacity:0;transform:translateY(-16px) scale(.97)}} to{{opacity:1;transform:none}} }}
    #gspInputWrap {{
      display:flex; align-items:center; gap:12px;
      padding:18px 22px; border-bottom:1px solid rgba(255,255,255,.06);
    }}
    #gspIcon {{ color:#4a5568; font-size:18px; flex-shrink:0; }}
    #gspInput {{
      flex:1; background:transparent; border:none; outline:none;
      font-size:17px; color:#e2e8f0; font-family:var(--font,'Montserrat',sans-serif);
      font-weight:500;
    }}
    #gspInput::placeholder {{ color:#2d3748; }}
    #gspKbd {{
      font-size:10px; color:#2d3748; background:rgba(255,255,255,.04);
      border:1px solid rgba(255,255,255,.08); border-radius:5px;
      padding:2px 7px; font-family:var(--mono,'monospace'); white-space:nowrap;
    }}
    #gspResults {{
      max-height:420px; overflow-y:auto; padding:8px 0;
    }}
    #gspResults::-webkit-scrollbar {{ width:4px; }}
    #gspResults::-webkit-scrollbar-track {{ background:transparent; }}
    #gspResults::-webkit-scrollbar-thumb {{ background:rgba(182,157,116,.2); border-radius:2px; }}
    .gsp-section-label {{
      font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:.12em;
      color:#2d3748; padding:10px 22px 4px; pointer-events:none;
    }}
    .gsp-item {{
      display:flex; align-items:center; gap:14px;
      padding:10px 22px; cursor:pointer; transition:background .1s;
      border-radius:0;
    }}
    .gsp-item:hover, .gsp-item.active {{
      background:rgba(182,157,116,.08);
    }}
    .gsp-item-icon {{
      width:34px; height:34px; border-radius:9px; flex-shrink:0;
      display:flex; align-items:center; justify-content:center;
      font-size:14px; font-weight:700;
    }}
    .gsp-item-main {{ flex:1; min-width:0; }}
    .gsp-item-title {{
      font-size:13.5px; font-weight:600; color:#e2e8f0;
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    }}
    .gsp-item-sub {{ font-size:11px; color:#4a5568; margin-top:1px; }}
    .gsp-item-right {{ display:flex; flex-direction:column; align-items:flex-end; gap:4px; }}
    .gsp-badge {{
      font-size:10px; font-weight:700; padding:2px 8px; border-radius:4px;
      font-family:var(--mono,'monospace');
    }}
    .gsp-badge.green  {{ background:rgba(47,168,116,.15); color:#2fa874; }}
    .gsp-badge.red    {{ background:rgba(217,65,65,.15);  color:#d94141; }}
    .gsp-badge.gold   {{ background:rgba(182,157,116,.15);color:#b69d74; }}
    .gsp-badge.blue   {{ background:rgba(49,116,184,.15); color:#3174b8; }}
    .gsp-badge.gray   {{ background:rgba(74,85,104,.15);  color:#718096; }}
    .gsp-item-saldo {{ font-family:var(--mono,'monospace'); font-size:12px; color:#718096; }}
    #gspFooter {{
      display:flex; align-items:center; gap:16px;
      padding:10px 22px; border-top:1px solid rgba(255,255,255,.04);
      font-size:10.5px; color:#2d3748;
    }}
    .gsp-key {{
      display:inline-flex; align-items:center; gap:4px;
    }}
    .gsp-key kbd {{
      background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.1);
      border-radius:4px; padding:1px 6px; font-size:10px;
      font-family:var(--mono,'monospace'); color:#4a5568;
    }}
    #gspEmpty {{
      padding:32px 22px; text-align:center;
      color:#2d3748; font-size:13px;
    }}
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
    {{ id:'home',        label:'Panorama Geral',          icon:'🏠', color:'#1f2839' }},
    {{ id:'composicao',  label:'Composição da Carteira',  icon:'◎',  color:'#00677b' }},
    {{ id:'rating',      label:'Rating & Status',         icon:'★',  color:'#b69d74' }},
    {{ id:'performance', label:'Performance',             icon:'↗',  color:'#2fa874' }},
    {{ id:'spreads',     label:'Spreads',                 icon:'~',  color:'#3174b8' }},
    {{ id:'tunel',       label:'Túnel do Tempo',          icon:'⧖',  color:'#a78bd4' }},
    {{ id:'bonds',       label:'Bonds & Eurobonds',       icon:'$',  color:'#e0c44a' }},
    {{ id:'financeiros', label:'Fundamentos Financeiros', icon:'∑',  color:'#d47aa7' }},
    {{ id:'bancos',      label:'Bancos',                  icon:'⬡',  color:'#5ab8d4' }},
    {{ id:'scorecard',   label:'Scorecard de Crédito',    icon:'✓',  color:'#60b85a' }},
    {{ id:'douro-news',  label:'Douro News',              icon:'◉',  color:'#d94141' }},
  ];

  let _idx = 0;
  let _items = [];

  function _badgeCls(status) {{
    if (!status) return 'gray';
    const s = status.toLowerCase();
    if (s==='aprovado') return 'green';
    if (s==='reprovado') return 'red';
    if (s.includes('análise')||s==='watch'||s==='monitoramento') return 'gold';
    return 'gray';
  }}

  function _fmtSaldo(v) {{
    if (!v) return '';
    return v>=1e9 ? 'R$'+(v/1e9).toFixed(1)+'B' : v>=1e6 ? 'R$'+(v/1e6).toFixed(0)+'M' : 'R$'+(v/1e3).toFixed(0)+'K';
  }}

  function _buildItems(q) {{
    const out = [];
    const qn = q.toLowerCase().trim();

    // Abas
    const pages = qn ? PAGES.filter(p => p.label.toLowerCase().includes(qn) || p.id.includes(qn)) : PAGES;
    pages.forEach(p => out.push({{ type:'page', data:p }}));

    if (!qn) return out;

    // Emissores corporativos (RANK_CORP)
    const corps = (typeof RANK_CORP!=='undefined'?RANK_CORP:[])
      .filter(r => r.empresa && r.empresa.toLowerCase().includes(qn))
      .slice(0,8);
    corps.forEach(r => {{
      const byE = (typeof ATIVOS!=='undefined'?ATIVOS:[]).filter(a=>a.emissor===r.empresa&&(a.saldo||0)>0);
      const saldo = byE.reduce((s,a)=>s+(a.saldo||0),0);
      out.push({{ type:'corp', data:r, saldo }});
    }});

    // Bancos (RANK_BANCOS)
    const banks = (typeof RANK_BANCOS!=='undefined'?RANK_BANCOS:[])
      .filter(r => r.empresa && r.empresa.toLowerCase().includes(qn))
      .slice(0,5);
    banks.forEach(r => out.push({{ type:'banco', data:r }}));

    return out;
  }}

  function _render(q) {{
    _items = _buildItems(q);
    _idx = 0;
    const el = document.getElementById('gspResults');
    if (!_items.length) {{
      el.innerHTML = '<div id="gspEmpty">Nenhum resultado para <strong style="color:#e2e8f0">"' + q + '"</strong></div>';
      return;
    }}
    let html = '';
    let lastType = null;
    _items.forEach((it, i) => {{
      if (it.type !== lastType) {{
        const labels = {{ page:'Abas', corp:'Emissores Corporativos', banco:'Bancos' }};
        html += `<div class="gsp-section-label">${{labels[it.type]||''}}</div>`;
        lastType = it.type;
      }}
      if (it.type==='page') {{
        const p = it.data;
        html += `<div class="gsp-item${{i===_idx?' active':''}}" data-idx="${{i}}" onclick="_gspSelect(${{i}})">
          <div class="gsp-item-icon" style="background:${{p.color}}22;color:${{p.color}};font-size:16px">${{p.icon}}</div>
          <div class="gsp-item-main">
            <div class="gsp-item-title">${{p.label}}</div>
            <div class="gsp-item-sub">Aba do dashboard</div>
          </div>
          <div class="gsp-item-right"><span class="gsp-badge blue">Página</span></div>
        </div>`;
      }} else if (it.type==='corp') {{
        const r = it.data;
        html += `<div class="gsp-item${{i===_idx?' active':''}}" data-idx="${{i}}" onclick="_gspSelect(${{i}})">
          <div class="gsp-item-icon" style="background:rgba(182,157,116,.1);color:#b69d74;font-size:12px;font-weight:800">${{r.empresa.substring(0,2).toUpperCase()}}</div>
          <div class="gsp-item-main">
            <div class="gsp-item-title">${{r.empresa}}</div>
            <div class="gsp-item-sub">${{r.setor||'Corporativo'}} · ${{r.ratingMkt||'—'}}</div>
          </div>
          <div class="gsp-item-right">
            <span class="gsp-badge ${{_badgeCls(r.status)}}">${{r.status||'—'}}</span>
            ${{it.saldo ? `<span class="gsp-item-saldo">${{_fmtSaldo(it.saldo)}}</span>` : ''}}
          </div>
        </div>`;
      }} else {{
        const r = it.data;
        html += `<div class="gsp-item${{i===_idx?' active':''}}" data-idx="${{i}}" onclick="_gspSelect(${{i}})">
          <div class="gsp-item-icon" style="background:rgba(91,184,212,.1);color:#5ab8d4;font-size:12px;font-weight:800">${{r.empresa.substring(0,2).toUpperCase()}}</div>
          <div class="gsp-item-main">
            <div class="gsp-item-title">${{r.empresa}}</div>
            <div class="gsp-item-sub">Banco · ${{r.ratingDouro||'—'}}</div>
          </div>
          <div class="gsp-item-right">
            <span class="gsp-badge ${{_badgeCls(r.status)}}">${{r.status||'—'}}</span>
          </div>
        </div>`;
      }}
    }});
    el.innerHTML = html;
  }}

  function _setActive(i) {{
    _idx = i;
    document.querySelectorAll('.gsp-item').forEach((el,j) => el.classList.toggle('active', j===i));
    const active = document.querySelector('.gsp-item.active');
    if (active) active.scrollIntoView({{block:'nearest'}});
  }}

  window._gspSelect = function(i) {{
    if (i===undefined) i = _idx;
    const it = _items[i];
    if (!it) return;
    _forceClose();
    if (it.type==='page') {{
      showPage(it.data.id, document.querySelector('.nav-item[onclick*="' + it.data.id + '"]'));
    }} else if (it.type==='corp') {{
      // Mesma lógica de homeSelectEmp()
      showPage('fundamentos', document.querySelector('.nav-item[onclick*="fundamentos"]'));
      setTimeout(()=>{{
        const sel = document.getElementById('fundEmpSel');
        if (sel) {{ sel.value = it.data.empresa; sel.dispatchEvent(new Event('change')); }}
      }}, 110);
    }} else if (it.type==='banco') {{
      // Mesma lógica de homeSelectBanco()
      showPage('bancos', document.querySelector('.nav-item[onclick*="bancos"]'));
      setTimeout(()=>{{
        const sel = document.getElementById('bancosEmpSel');
        if (sel) {{ sel.value = it.data.empresa; sel.dispatchEvent(new Event('change')); }}
        if (typeof buildBancos==='function') buildBancos(it.data.empresa);
      }}, 110);
    }}
  }};

  function _gspOpen() {{
    document.getElementById('gspBackdrop').classList.add('open');
    const inp = document.getElementById('gspInput');
    inp.value = '';
    _render('');
    setTimeout(()=>inp.focus(), 30);
  }}

  window._gspClose = function(e) {{
    if (e && e.target !== document.getElementById('gspBackdrop')) return;
    document.getElementById('gspBackdrop').classList.remove('open');
  }};
  function _forceClose() {{ document.getElementById('gspBackdrop').classList.remove('open'); }}

  document.getElementById('gspInput').addEventListener('input', e => _render(e.target.value));
  document.getElementById('gspInput').addEventListener('keydown', e => {{
    if (e.key==='ArrowDown') {{ e.preventDefault(); _setActive(Math.min(_idx+1,_items.length-1)); }}
    else if (e.key==='ArrowUp') {{ e.preventDefault(); _setActive(Math.max(_idx-1,0)); }}
    else if (e.key==='Enter') {{ e.preventDefault(); _gspSelect(_idx); }}
    else if (e.key==='Escape') {{ _forceClose(); }}
  }});

  document.addEventListener('keydown', e => {{
    if (e.ctrlKey && e.key==='p') {{ e.preventDefault(); _gspOpen(); }}
    if (e.key==='Escape') _forceClose();
  }});
}})();

<!--HIDDEN_FEATURES-->

</script>
</body>
</html>"""

# ── 3.3 PREENCHER OPÇÕES DE FILTRO ──────────────────────────────────────
carteiras_unicas = sorted(df_cart["carteira"].dropna().unique().tolist())
setores_unicos   = sorted(df_cart["setor"].dropna().unique().tolist())
carteira_options    = "\n".join(f'<option value="{c}">{c}</option>' for c in carteiras_unicas)
setor_options       = "\n".join(f'<option value="{s}">{s}</option>' for s in setores_unicos)
carteira_options_dd = "\n".join(f'<div class="ss-opt" data-value="{c}">{c}</div>' for c in carteiras_unicas)
setor_options_dd    = "\n".join(f'<div class="ss-opt" data-value="{s}">{s}</div>' for s in setores_unicos)
officers_unicos  = sorted(
    df_cart["officer"].dropna().replace("N/D", pd.NA).dropna().unique().tolist()
)
officer_options     = "\n".join(f'<option value="{o}">{o}</option>' for o in officers_unicos)
officer_options_dd  = "\n".join(f'<div class="ss-opt" data-value="{o}">{o}</div>' for o in officers_unicos)

# ── 3.4 MONTAR HTML FINAL ─────────────────────────────────────────────────

# ── BUILD INFO: timestamps de geração e das planilhas de base ─────────────
_agora_build = datetime.now()
_bi_modo_label = "Completo (API ao vivo)" if MODO_COMPLETO else ("Offline (planilhas salvas)" if MODO_OFFLINE else "News rápido")
_bi_modo_num   = "1" if MODO_COMPLETO else ("3" if MODO_OFFLINE else "2")

_bi_arquivos = []
_bi_rastrear = [
    ("Scorecard de Empresas",  os.path.join(BASE_INV, r"Análise de Crédito\Rating Crédito\Scorecard de Empresas.xlsm")),
    ("Watch List Bancos",      os.path.join(BASE_INV, r"Análise de Crédito\Rating Crédito\Watch List Bancos.xlsm")),
    ("Base Rating/Setor",      os.path.join(BASE_PROC, r"Risco\Documentos base [SEMPRE FAZER CÓPIA]\base_rating_setor.xlsx")),
]
if MODO_OFFLINE:
    _bi_rastrear += [
        ("Carteira CP (cache)",          os.path.join(_PLANILHAS_OV, "dados_cp1.xlsx")),
        ("Carteiras (cache)",            os.path.join(_PLANILHAS_OV, "dados_carteiras1.xlsx")),
        ("Bonds Offshore (cache)",       os.path.join(_PLANILHAS_OV, "dados_bonds1.xlsx")),
        ("Crédito Detalhado (cache)",    os.path.join(_PLANILHAS_OV, "dados_carteiras_credito1.xlsx")),
    ]
for _bi_nome, _bi_path in _bi_rastrear:
    try:
        _bi_mt  = os.path.getmtime(_bi_path)
        _bi_ts  = datetime.fromtimestamp(_bi_mt).strftime("%d/%m/%Y %H:%M")
        _bi_age = int((_agora_build - datetime.fromtimestamp(_bi_mt)).total_seconds() / 3600)
        _bi_arquivos.append({"nome": _bi_nome, "ts": _bi_ts, "horas": _bi_age, "ok": True})
    except Exception:
        _bi_arquivos.append({"nome": _bi_nome, "ts": "—", "horas": -1, "ok": False})

_build_info = {
    "gerado_em":  _agora_build.strftime("%d/%m/%Y %H:%M:%S"),
    "modo":       _bi_modo_label,
    "modo_num":   _bi_modo_num,
    "dados_vivos": MODO_COMPLETO,
    "arquivos":   _bi_arquivos,
}
build_info_js = json.dumps(_build_info, ensure_ascii=False)

# Caminho absoluto do scorecard.html (gerado por gerar_scorecard.py)
_scorecard_abs = os.path.join(
    BASE_INV,
    r"Análise de Crédito\Rating Crédito\Scorecard\scorecard.html"
)
# Converte para URI file:// compatível com iframe src em arquivo local
# Barra invertida → barra normal, espaços → %20
_scorecard_uri = "file:///" + _scorecard_abs.replace("\\", "/").replace(" ", "%20")
scorecard_src_js = json.dumps(_scorecard_uri)   # string JS com aspas

html_final = HTML_TEMPLATE.format(
    carteira_options    = carteira_options,
    setor_options       = setor_options,
    officer_options     = officer_options,
    carteira_options_dd = carteira_options_dd,
    setor_options_dd    = setor_options_dd,
    officer_options_dd  = officer_options_dd,
    ativos_js        = ativos_js,
    pl_total_js      = pl_total_js,
    pl_por_carteira_js = pl_por_carteira_js,
    fin_series_js    = fin_series_js,
    setores_js       = setores_js,
    rank_corp_js     = rank_corp_js,
    rank_bancos_js   = rank_bancos_js,
    spreads_ts_js    = spreads_ts_js,
    perf_js          = perf_js,
    bonds_info_js    = bonds_info_js,
    bonds_ts_js      = bonds_ts_js,
    news_js          = news_js,
    alertas_js       = alertas_js,
    fatos_relevantes_js = fatos_relevantes_js,
    scorecard_src    = scorecard_src_js,
    bcb_bancos_js    = bcb_bancos_js,
    logo_html        = logo_html,
    build_info_js    = build_info_js,
)
# Injeta blocos JS com chaves simples (fora do .format() para evitar KeyError)
_hidden_js = """
// ── COMPARADOR DE EMISSORES (Ctrl+Shift+C) ────────────────────────────────
(function() {
  const _css = `
    #cmpOverlay {
      display:none; position:fixed; inset:0; z-index:9998;
      background:rgba(4,7,14,.97); flex-direction:column;
      font-family:var(--font,'Montserrat',sans-serif);
    }
    #cmpOverlay.open { display:flex; animation:cmpSlideIn .28s cubic-bezier(.16,1,.3,1); }
    @keyframes cmpSlideIn { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:none} }
    #cmpBar {
      display:grid; grid-template-columns:1fr 60px 1fr 48px;
      align-items:center; flex-shrink:0;
      border-bottom:1px solid rgba(255,255,255,.055);
      background:rgba(10,14,24,.9); backdrop-filter:blur(12px);
    }
    .cmp-slot {
      display:flex; align-items:center; gap:10px; padding:14px 24px;
      position:relative; border-right:1px solid rgba(255,255,255,.05);
    }
    .cmp-slot-letter {
      width:28px; height:28px; border-radius:8px; flex-shrink:0;
      display:flex; align-items:center; justify-content:center;
      font-size:11px; font-weight:800; color:#fff;
    }
    .cmp-slot-inp {
      flex:1; background:transparent; border:none; outline:none;
      font-size:13.5px; font-weight:600; color:#e2e8f0;
      font-family:var(--font,'Montserrat',sans-serif);
    }
    .cmp-slot-inp::placeholder { color:#252d3d; font-weight:400; }
    .cmp-slot-status {
      font-size:10px; font-weight:700; padding:2px 9px; border-radius:10px;
      white-space:nowrap; flex-shrink:0;
    }
    .cmp-slot-status.green { background:rgba(47,168,116,.18); color:#2fa874; }
    .cmp-slot-status.red   { background:rgba(217,65,65,.18);  color:#d94141; }
    .cmp-slot-status.gold  { background:rgba(182,157,116,.18);color:#b69d74; }
    .cmp-slot-status.gray  { background:rgba(74,85,104,.15);  color:#4a5568; }
    .cmp-vs {
      text-align:center; font-size:11px; font-weight:700; color:#1e2535;
      letter-spacing:.12em; text-transform:uppercase;
    }
    #cmpCloseBtn {
      background:transparent; border:none; color:#2d3748; font-size:18px;
      cursor:pointer; height:100%; padding:0 16px; transition:color .15s;
    }
    #cmpCloseBtn:hover { color:#e2e8f0; }
    .cmp-dd {
      position:absolute; top:100%; left:0; right:0; z-index:200;
      background:#0a0e1c; border:1px solid rgba(255,255,255,.08);
      border-top:none; max-height:280px; overflow-y:auto;
      box-shadow:0 20px 50px rgba(0,0,0,.7);
    }
    .cmp-dd::-webkit-scrollbar { width:3px; }
    .cmp-dd::-webkit-scrollbar-thumb { background:rgba(255,255,255,.1); border-radius:2px; }
    .cmp-dd-row {
      display:flex; align-items:center; gap:10px; padding:9px 16px;
      cursor:pointer; transition:background .1s; border-bottom:1px solid rgba(255,255,255,.03);
    }
    .cmp-dd-row:hover { background:rgba(182,157,116,.07); }
    .cmp-dd-name { flex:1; font-size:12.5px; color:#c8d0e0; font-weight:500; }
    .cmp-dd-tag  { font-size:10px; color:#2d3748; }
    #cmpBody {
      flex:1; display:grid; grid-template-columns:1fr 1px 1fr; overflow:hidden;
    }
    .cmp-divider-v {
      background:linear-gradient(to bottom,transparent,rgba(182,157,116,.2) 20%,rgba(182,157,116,.2) 80%,transparent);
    }
    .cmp-panel { overflow-y:auto; padding:24px 28px; }
    .cmp-panel::-webkit-scrollbar { width:3px; }
    .cmp-panel::-webkit-scrollbar-thumb { background:rgba(255,255,255,.07); border-radius:2px; }
    .cmp-empty-state {
      height:100%; display:flex; flex-direction:column;
      align-items:center; justify-content:center; gap:14px; color:#1a2030;
    }
    .cmp-empty-letter {
      font-size:72px; font-weight:800; line-height:1;
      background:linear-gradient(135deg,#1a2030,#0d1520);
      -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    }
    .cmp-entity-head {
      display:flex; align-items:center; gap:14px;
      padding-bottom:18px; margin-bottom:18px;
      border-bottom:1px solid rgba(255,255,255,.055);
    }
    .cmp-avatar {
      width:44px; height:44px; border-radius:11px; flex-shrink:0;
      display:flex; align-items:center; justify-content:center;
      font-size:16px; font-weight:800; color:#fff;
    }
    .cmp-ename { font-size:17px; font-weight:700; color:#e2e8f0; }
    .cmp-emeta { font-size:11.5px; color:#3a4558; margin-top:3px; }
    .cmp-kpis { display:grid; grid-template-columns:1fr 1fr; gap:9px; margin-bottom:18px; }
    .cmp-kpi {
      background:rgba(255,255,255,.022); border:1px solid rgba(255,255,255,.05);
      border-radius:9px; padding:11px 13px; transition:border-color .2s;
    }
    .cmp-kpi:hover { border-color:rgba(255,255,255,.1); }
    .cmp-kpi-lbl { font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:.1em; color:#1e2840; }
    .cmp-kpi-v   { font-family:var(--mono,'monospace'); font-size:19px; font-weight:700; color:#e2e8f0; margin-top:5px; line-height:1; }
    .cmp-kpi-v.g { color:#2fa874; } .cmp-kpi-v.r { color:#d94141; } .cmp-kpi-v.o { color:#b69d74; }
    .cmp-sec-lbl {
      font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:.12em;
      color:#1e2840; margin:14px 0 8px; display:flex; align-items:center; gap:8px;
    }
    .cmp-sec-lbl::after { content:''; flex:1; height:1px; background:rgba(255,255,255,.04); }
    .cmp-pos-list { display:flex; flex-direction:column; gap:5px; }
    .cmp-pos-row {
      display:flex; align-items:center; gap:8px; padding:7px 10px;
      background:rgba(255,255,255,.018); border:1px solid rgba(255,255,255,.04);
      border-radius:7px;
    }
    .cmp-pos-name { flex:1; font-size:11.5px; color:#8899aa; }
    .cmp-pos-cls  { font-size:10px; color:#2d3748; }
    .cmp-pos-val  { font-family:var(--mono,'monospace'); font-size:12px; color:#c8d0e0; font-weight:600; }
    #cmpFoot {
      display:flex; align-items:center; justify-content:space-between;
      padding:9px 24px; border-top:1px solid rgba(255,255,255,.04);
      font-size:10px; color:#1a2030; flex-shrink:0;
    }
    /* ── MODE SWITCHER ── */
    #cmpModeBar {
      display:flex; align-items:center; justify-content:center; gap:12px;
      padding:8px 24px; flex-shrink:0;
      background:rgba(6,9,18,.9); border-bottom:1px solid rgba(255,255,255,.04);
    }
    #cmpModeTrack {
      position:relative; display:flex; align-items:stretch;
      background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.06);
      border-radius:22px; padding:3px; user-select:none; cursor:pointer;
    }
    #cmpModeThumb {
      position:absolute; top:3px; bottom:3px;
      background:rgba(182,157,116,.18); border:1px solid rgba(182,157,116,.45);
      border-radius:18px; transition:left .24s cubic-bezier(.4,0,.2,1),width .24s;
      pointer-events:none; z-index:0;
    }
    .cmp-mode-seg {
      position:relative; z-index:1; padding:5px 13px;
      font-size:9.5px; font-weight:700; letter-spacing:.07em; text-transform:uppercase;
      color:#252d3d; border-radius:16px; transition:color .18s; white-space:nowrap;
      cursor:pointer;
    }
    .cmp-mode-seg.active { color:#b69d74; }
    #cmpModeLbl { font-size:9px; color:#1a2030; letter-spacing:.1em; text-transform:uppercase; }
    /* ── TERMINAL MODE ── */
    #cmpOverlay.mode-terminal { background:rgba(0,3,6,.99); }
    #cmpOverlay.mode-terminal #cmpBar,
    #cmpOverlay.mode-terminal #cmpModeBar { background:#000508; }
    #cmpOverlay.mode-terminal .cmp-panel { background:transparent; }
    #cmpOverlay.mode-terminal #cmpPanel0 .cmp-ename { color:#2fa874 !important; font-family:'Courier New',monospace; }
    #cmpOverlay.mode-terminal #cmpPanel1 .cmp-ename { color:#6ba4d4 !important; font-family:'Courier New',monospace; }
    #cmpOverlay.mode-terminal .cmp-kpi { background:#010a05; border-color:rgba(47,168,116,.12); }
    #cmpOverlay.mode-terminal #cmpPanel1 .cmp-kpi { background:#010510; border-color:rgba(107,164,212,.12); }
    #cmpOverlay.mode-terminal .cmp-kpi-v { font-family:'Courier New',monospace; }
    #cmpOverlay.mode-terminal #cmpPanel0 .cmp-kpi-v { color:#2fa874; }
    #cmpOverlay.mode-terminal #cmpPanel1 .cmp-kpi-v { color:#6ba4d4; }
    #cmpOverlay.mode-terminal .cmp-kpi-lbl { color:rgba(47,168,116,.5); }
    #cmpOverlay.mode-terminal #cmpPanel1 .cmp-kpi-lbl { color:rgba(107,164,212,.5); }
    #cmpOverlay.mode-terminal .cmp-entity-head { border-color:rgba(47,168,116,.1); }
    #cmpOverlay.mode-terminal .cmp-sec-lbl { color:rgba(47,168,116,.4); }
    #cmpOverlay.mode-terminal #cmpPanel1 .cmp-sec-lbl { color:rgba(107,164,212,.4); }
    #cmpOverlay.mode-terminal .cmp-sec-lbl::after { background:rgba(47,168,116,.08); }
    #cmpOverlay.mode-terminal #cmpPanel1 .cmp-sec-lbl::after { background:rgba(107,164,212,.08); }
    #cmpOverlay.mode-terminal .cmp-divider-v { background:linear-gradient(to bottom,transparent,rgba(47,168,116,.15) 20%,rgba(47,168,116,.15) 80%,transparent); }
    /* ── DUELO MODE ── */
    #cmpOverlay.mode-duelo #cmpPanel0 { background:rgba(182,157,116,.02); }
    #cmpOverlay.mode-duelo #cmpPanel1 { background:rgba(49,116,184,.02); }
    #cmpOverlay.mode-duelo #cmpPanel0 .cmp-entity-head { border-color:rgba(182,157,116,.15); }
    #cmpOverlay.mode-duelo #cmpPanel1 .cmp-entity-head { border-color:rgba(49,116,184,.15); }
    .cmp-win-tag { font-size:10px; margin-left:auto; padding:1px 6px; border-radius:8px; font-weight:700; }
    .cmp-win-tag.a { background:rgba(182,157,116,.18); color:#b69d74; }
    .cmp-win-tag.b { background:rgba(49,116,184,.18); color:#6ba4d4; }
    .cmp-win-tag.tie { background:rgba(255,255,255,.06); color:#3a4558; }
    #cmpDueloScore {
      display:none; align-items:center; justify-content:center; gap:18px;
      padding:10px 0 0; font-size:11px; color:#3a4558;
    }
    .cmp-dscore-val { font-size:22px; font-weight:800; line-height:1; }
    /* ── DELTA MODE ── */
    #cmpDeltaWrap {
      flex:1; overflow-y:auto; padding:0;
    }
    #cmpDeltaWrap::-webkit-scrollbar { width:3px; }
    #cmpDeltaWrap::-webkit-scrollbar-thumb { background:rgba(255,255,255,.07); }
    .cmp-delta-score { display:flex; align-items:center; justify-content:space-between; padding:14px 28px 8px; flex-shrink:0; }
    .cmp-delta-score-val { font-size:28px; font-weight:800; line-height:1; }
    .cmp-delta-score-lbl { font-size:9px; text-transform:uppercase; letter-spacing:.1em; color:#1e2840; margin-top:2px; }
    .cmp-delta-hdr { display:grid; grid-template-columns:140px 1fr 1fr 1fr 60px; padding:8px 28px; border-bottom:1px solid rgba(255,255,255,.04); font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:.1em; color:#1e2840; }
    .cmp-delta-row { display:grid; grid-template-columns:140px 1fr 1fr 1fr 60px; align-items:center; padding:9px 28px; border-bottom:1px solid rgba(255,255,255,.025); transition:background .12s; }
    .cmp-delta-row:hover { background:rgba(255,255,255,.02); }
    .cmp-delta-metric { font-size:11px; color:#3a4558; }
    .cmp-delta-val { font-family:'DM Mono',monospace; font-size:12.5px; color:#c8d0e0; font-weight:600; }
    .cmp-delta-diff-col { font-size:10.5px; font-weight:700; font-family:'DM Mono',monospace; }
    .cmp-delta-diff-col.pos { color:#2fa874; } .cmp-delta-diff-col.neg { color:#d94141; } .cmp-delta-diff-col.neu { color:#3a4558; }
    .cmp-delta-win-col { text-align:center; font-size:12px; }
    /* ── PREMIUM MODE ── */
    .cmp-strength-wrap { padding:12px 28px 0; flex-shrink:0; }
    .cmp-strength-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
    .cmp-strength-nm { font-size:10px; font-weight:700; }
    .cmp-strength-nm.a { color:#b69d74; } .cmp-strength-nm.b { color:#6ba4d4; }
    .cmp-strength-sc { font-size:9px; color:#2d3748; }
    .cmp-strength-track { height:5px; background:rgba(255,255,255,.04); border-radius:3px; overflow:hidden; }
    .cmp-strength-fill { height:100%; border-radius:3px; transition:width .6s cubic-bezier(.4,0,.2,1); }
    #cmpOverlay.mode-premium .cmp-kpi { border-radius:12px; transition:transform .15s,border-color .15s; }
    #cmpOverlay.mode-premium .cmp-kpi:hover { transform:translateY(-2px); border-color:rgba(255,255,255,.12); }
    #cmpOverlay.mode-premium #cmpPanel0 .cmp-avatar { box-shadow:0 0 20px rgba(182,157,116,.2); }
    #cmpOverlay.mode-premium #cmpPanel1 .cmp-avatar { box-shadow:0 0 20px rgba(49,116,184,.2); }

    /* ── STREET FIGHTER MODE ─────────────────────────────── */
    #cmpOverlay.mode-sf { background:#0a0008; }
    #cmpOverlay.mode-sf #cmpBar { background:#120010; border-bottom:2px solid #ff003c; }
    #cmpOverlay.mode-sf #cmpModeBar { background:#0f000d; border-bottom:2px solid #ff003c; }
    #cmpSfWrap {
      width:100%; display:flex; flex-direction:column; align-items:center;
      background:radial-gradient(ellipse at 50% 30%,#1a0015 0%,#050008 100%);
      position:relative; overflow:hidden; padding:0 0 24px;
    }
    #cmpSfWrap::before {
      content:''; position:absolute; inset:0; pointer-events:none;
      background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(255,0,60,.03) 3px,rgba(255,0,60,.03) 4px);
    }
    .sf-arena {
      width:100%; display:flex; justify-content:space-between; align-items:flex-end;
      padding:0 32px; gap:0; position:relative;
    }
    .sf-fighter {
      display:flex; flex-direction:column; align-items:center; gap:6px; z-index:2;
    }
    .sf-hb-wrap {
      width:240px; display:flex; flex-direction:column; gap:4px;
    }
    .sf-hb-wrap.right { align-items:flex-end; }
    .sf-hb-label {
      font-family:'Courier New',monospace; font-size:11px; font-weight:700; letter-spacing:.12em;
      text-transform:uppercase;
    }
    .sf-hb-label.a { color:#ffcd00; text-shadow:0 0 8px #ffcd00; text-align:left; }
    .sf-hb-label.b { color:#00cfff; text-shadow:0 0 8px #00cfff; text-align:right; }
    .sf-hb-track {
      height:18px; background:#111; border:2px solid #333;
      border-radius:2px; overflow:hidden; position:relative;
    }
    .sf-hb-fill {
      height:100%; border-radius:1px;
      transition:width .8s cubic-bezier(.4,0,.2,1);
    }
    .sf-hb-fill.a { background:linear-gradient(90deg,#ff0000,#ffcd00 60%,#00ff44); float:left; }
    .sf-hb-fill.b { background:linear-gradient(270deg,#ff0000,#00cfff 60%,#00ff44); float:right; }
    .sf-portrait {
      width:100px; height:100px; border-radius:4px; display:flex; align-items:center;
      justify-content:center; font-size:42px; border:3px solid; position:relative;
      image-rendering:pixelated;
    }
    .sf-portrait.a { border-color:#ffcd00; box-shadow:0 0 18px rgba(255,205,0,.5),inset 0 0 20px rgba(255,205,0,.08); background:#12000e; }
    .sf-portrait.b { border-color:#00cfff; box-shadow:0 0 18px rgba(0,207,255,.5),inset 0 0 20px rgba(0,207,255,.08); background:#00020e; }
    .sf-portrait::after {
      content:''; position:absolute; inset:0;
      background:repeating-linear-gradient(0deg,transparent,transparent 5px,rgba(255,255,255,.025) 5px,rgba(255,255,255,.025) 6px);
      border-radius:2px;
    }
    .sf-vs-wrap {
      position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
      z-index:10;
    }
    .sf-vs {
      font-family:'Courier New',monospace; font-size:36px; font-weight:900;
      color:#fff; letter-spacing:.05em; text-shadow:0 0 20px #ff003c, 2px 2px 0 #ff003c,-2px -2px 0 #990022;
      animation:sfVsPulse 1s ease-in-out infinite;
    }
    @keyframes sfVsPulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.12)} }
    .sf-name {
      font-family:'Courier New',monospace; font-size:10px; font-weight:700;
      letter-spacing:.14em; text-transform:uppercase; text-align:center; margin-top:4px;
    }
    .sf-name.a { color:#ffcd00; text-shadow:0 0 6px #ffcd00; }
    .sf-name.b { color:#00cfff; text-shadow:0 0 6px #00cfff; }
    .sf-fight-word {
      font-family:'Courier New',monospace; font-size:28px; font-weight:900;
      text-transform:uppercase; letter-spacing:.18em; margin:12px 0 0;
      animation:sfFight .6s steps(1) infinite;
    }
    @keyframes sfFight { 0%{color:#ff003c;text-shadow:0 0 12px #ff003c} 33%{color:#ffcd00;text-shadow:0 0 12px #ffcd00} 66%{color:#00cfff;text-shadow:0 0 12px #00cfff} 100%{color:#ff003c;text-shadow:0 0 12px #ff003c} }
    .sf-stats-wrap {
      width:100%; padding:0 32px; display:grid; grid-template-columns:1fr 1fr; gap:6px 32px; margin-top:16px;
    }
    .sf-stat-row {
      display:flex; flex-direction:column; gap:3px; padding:6px 0;
      border-bottom:1px solid rgba(255,255,255,.05);
    }
    .sf-stat-label {
      font-family:'Courier New',monospace; font-size:9px; color:#666;
      letter-spacing:.1em; text-transform:uppercase;
    }
    .sf-stat-bar-wrap { height:8px; background:#1a1a1a; border-radius:1px; overflow:hidden; display:flex; }
    .sf-stat-fill-a { height:100%; background:linear-gradient(90deg,#ffcd0088,#ffcd00); border-radius:1px 0 0 1px; transition:width .6s; }
    .sf-stat-fill-b { height:100%; background:linear-gradient(90deg,#00cfff,#00cfff88); border-radius:0 1px 1px 0; transition:width .6s; }
    .sf-stat-vals { display:flex; justify-content:space-between; font-size:9px; margin-top:2px; }
    .sf-stat-vals .av { color:#ffcd00; font-weight:700; }
    .sf-stat-vals .bv { color:#00cfff; font-weight:700; }
    .sf-stat-vals .lbl { color:#555; font-size:8px; text-transform:uppercase; letter-spacing:.06em; }
    .sf-winner-banner {
      font-family:'Courier New',monospace; font-size:13px; font-weight:900;
      letter-spacing:.18em; text-transform:uppercase; text-align:center;
      padding:8px 32px; margin-top:10px;
      animation:sfWin 1s steps(1) infinite;
    }
    @keyframes sfWin { 0%{color:#ffcd00;text-shadow:0 0 16px #ffcd00} 50%{color:#fff;text-shadow:0 0 4px #fff} 100%{color:#ffcd00;text-shadow:0 0 16px #ffcd00} }
    .sf-ko { font-size:10px; letter-spacing:.2em; color:#ff003c; animation:sfFight .4s steps(1) infinite; font-weight:700; margin-top:2px; display:block; }
  `;
  const st = document.createElement('style'); st.textContent = _css; document.head.appendChild(st);

  document.body.insertAdjacentHTML('beforeend', `
    <div id="cmpOverlay">
      <div id="cmpBar">
        <div class="cmp-slot" id="cmpSlot0">
          <div class="cmp-slot-letter" style="background:#b69d74">A</div>
          <input class="cmp-slot-inp" id="cmpInp0" placeholder="Emissor A…" autocomplete="off" spellcheck="false"/>
          <span class="cmp-slot-status gray" id="cmpSt0">—</span>
          <div class="cmp-dd" id="cmpDd0" style="display:none"></div>
        </div>
        <div class="cmp-vs">vs</div>
        <div class="cmp-slot" id="cmpSlot1">
          <div class="cmp-slot-letter" style="background:#3174b8">B</div>
          <input class="cmp-slot-inp" id="cmpInp1" placeholder="Emissor B…" autocomplete="off" spellcheck="false"/>
          <span class="cmp-slot-status gray" id="cmpSt1">—</span>
          <div class="cmp-dd" id="cmpDd1" style="display:none"></div>
        </div>
        <button id="cmpCloseBtn" onclick="closeCmp()">✕</button>
      </div>
      <div id="cmpModeBar">
        <span id="cmpModeLbl">Modo</span>
        <div id="cmpModeTrack">
          <div class="cmp-mode-seg active" data-mode="1">Duelo</div>
        </div>
      </div>
      <div id="cmpBody">
        <div class="cmp-panel" id="cmpPanel0">
          <div class="cmp-empty-state"><div class="cmp-empty-letter">A</div><div style="font-size:12px">Digite um emissor acima</div></div>
        </div>
        <div class="cmp-divider-v" id="cmpDividerV"></div>
        <div class="cmp-panel" id="cmpPanel1">
          <div class="cmp-empty-state"><div class="cmp-empty-letter">B</div><div style="font-size:12px">Digite um emissor acima</div></div>
        </div>
      </div>
      <div id="cmpFoot">
        <span>Ctrl+Shift+C · ESC para fechar</span>
        <span id="cmpFootMode">Duelo — Confronto direto</span>
      </div>
    </div>
  `);

  const COLOR = ['#b69d74','#3174b8'];

  function _bc(s) {
    if (!s) return 'gray';
    const l = s.toLowerCase();
    return l==='aprovado'?'green':l==='reprovado'?'red':(l.includes('nálise')||l==='watch'||l==='monitoramento')?'gold':'gray';
  }
  function _fmM(v) {
    if (!v||isNaN(v)) return '—';
    return v>=1e9?'R$'+(v/1e9).toFixed(1)+'B':v>=1e6?'R$'+(v/1e6).toFixed(0)+'M':'R$'+(v/1e3).toFixed(0)+'K';
  }
  function _lv(arr) { return Array.isArray(arr)&&arr.length?arr[arr.length-1]:null; }

  function _allNames() {
    const c = (typeof RANK_CORP!=='undefined'?RANK_CORP:[]).map(r=>r.empresa);
    const b = (typeof RANK_BANCOS!=='undefined'?RANK_BANCOS:[]).map(r=>r.empresa);
    return [...new Set([...c,...b])].filter(Boolean).sort();
  }

  function _showDd(idx, q) {
    const dd = document.getElementById('cmpDd'+idx);
    if (!q) { dd.style.display='none'; return; }
    const hits = _allNames().filter(n=>n.toLowerCase().includes(q.toLowerCase())).slice(0,14);
    if (!hits.length) { dd.style.display='none'; return; }
    const corps = typeof RANK_CORP!=='undefined'?RANK_CORP:[];
    const banks = typeof RANK_BANCOS!=='undefined'?RANK_BANCOS:[];
    dd.innerHTML = hits.map(n=>{
      const r = corps.find(x=>x.empresa===n)||banks.find(x=>x.empresa===n)||{};
      const tag = corps.find(x=>x.empresa===n)?'Corp':'Banco';
      return `<div class="cmp-dd-row" onmousedown="_cmpPick(${idx},'${n.replace(/'/g,"\\\\'")}')">
        <div class="cmp-dd-name">${n}</div>
        <div class="cmp-dd-tag">${tag}</div>
        <span class="cmp-slot-status ${_bc(r.status)}" style="font-size:9px;padding:1px 7px">${r.status||'—'}</span>
      </div>`;
    }).join('');
    dd.style.display = 'block';
  }

  function _renderPanel(idx, nome) {
    const corps = typeof RANK_CORP!=='undefined'?RANK_CORP:[];
    const banks = typeof RANK_BANCOS!=='undefined'?RANK_BANCOS:[];
    const fins  = typeof FIN_SERIES!=='undefined'?FIN_SERIES:{};
    const ativos= typeof ATIVOS!=='undefined'?ATIVOS:[];
    const col   = COLOR[idx];
    const ri    = corps.find(r=>r.empresa===nome)||banks.find(r=>r.empresa===nome)||{};
    const isBank= !!banks.find(r=>r.empresa===nome);
    const bcbD  = typeof _bcbLookup==='function'?_bcbLookup(nome):undefined;
    const finKey= typeof _matchToFin==='function'?_matchToFin(nome):nome;
    const fin   = (finKey&&fins[finKey]) ? fins[finKey] : (fins[nome]||null);
    const pos   = ativos.filter(a=>a.emissor===nome&&(a.saldo||0)>0);
    const totPos= pos.reduce((s,a)=>s+(a.saldo||0),0);
    const bc    = _bc(ri.status);

    let h = `
      <div class="cmp-entity-head">
        <div class="cmp-avatar" style="background:${col}18;color:${col}">${nome.substring(0,2).toUpperCase()}</div>
        <div>
          <div class="cmp-ename">${nome}</div>
          <div class="cmp-emeta">${ri.setor||(isBank?'Banco':'Corporativo')}
            &nbsp;·&nbsp;Rating Douro: <b style="color:#c8d0e0">${ri.ratingDouro||'—'}</b>
            &nbsp;·&nbsp;Mkt: ${ri.ratingMkt||'—'}</div>
          <span class="cmp-slot-status ${bc}" style="margin-top:6px;display:inline-block">${ri.status||'—'}</span>
        </div>
      </div>`;

    if (isBank && bcbD) {
      const bas=_lv(bcbD.basileia), roe=_lv(bcbD.roe), pdd=_lv(bcbD.inadimpl), efi=_lv(bcbD.eficiencia), nim=_lv(bcbD.nim);
      h += `<div class="cmp-sec-lbl">Indicadores BCB</div>
      <div class="cmp-kpis">
        <div class="cmp-kpi"><div class="cmp-kpi-lbl">Basileia</div><div class="cmp-kpi-v ${bas!=null&&bas<11?'r':bas!=null&&bas>14?'g':''}">${bas!=null?Number(bas).toFixed(1)+'%':'—'}</div></div>
        <div class="cmp-kpi"><div class="cmp-kpi-lbl">ROE</div><div class="cmp-kpi-v ${roe!=null&&roe>15?'g':roe!=null&&roe<8?'r':''}">${roe!=null?Number(roe).toFixed(1)+'%':'—'}</div></div>
        <div class="cmp-kpi"><div class="cmp-kpi-lbl">Cob. PDD</div><div class="cmp-kpi-v">${pdd!=null?Number(pdd).toFixed(1)+'%':'—'}</div></div>
        <div class="cmp-kpi"><div class="cmp-kpi-lbl">Eficiência</div><div class="cmp-kpi-v ${efi!=null&&efi<45?'g':efi!=null&&efi>65?'r':''}">${efi!=null?Number(efi).toFixed(1)+'%':'—'}</div></div>
        <div class="cmp-kpi"><div class="cmp-kpi-lbl">NIM</div><div class="cmp-kpi-v">${nim!=null?Number(nim).toFixed(1)+'%':'—'}</div></div>
        <div class="cmp-kpi"><div class="cmp-kpi-lbl">Anos</div><div class="cmp-kpi-v" style="font-size:13px">${(bcbD.anos||[]).join(', ')||'—'}</div></div>
      </div>`;
    } else if (fin) {
      const kpis = [
        ['Receita TTM',     _lv(fin['Receita_TTM']),        'M', false],
        ['EBITDA TTM',      _lv(fin['EBITDA_TTM']),         'M', false],
        ['Mg EBITDA',       _lv(fin['Mg EBITDA TTM']),      '%', false],
        ['Dív.Liq/EBITDA',  _lv(fin['DivLiquida/EBITDA']),  'x', true],
        ['ROE',             _lv(fin['ROE']),                 '%', false],
        ['ROIC',            _lv(fin['ROIC']),                '%', false],
        ['FCF TTM',         _lv(fin['FCF_TTM']),             'M', false],
        ['Liq. Corrente',   _lv(fin['Liquidez Corrente']),   'x', false],
        ['Dív.Bruta/EBITDA',_lv(fin['DivBruta_EBITDA']),    'x', true],
        ['Mg Líquida',      _lv(fin['Mg Liquida TTM']),      '%', false],
      ];
      h += `<div class="cmp-sec-lbl">Fundamentos Financeiros</div><div class="cmp-kpis">`;
      kpis.forEach(([lbl,val,unit,inv])=>{
        const n = parseFloat(val);
        let cls = '';
        if (!isNaN(n)) {
          if (unit==='%') cls = n>12?'g':n<0?'r':'';
          if (unit==='x'&&inv) cls = n>4?'r':n<2?'g':'';
        }
        const disp = isNaN(n)||val==null?'—':unit==='M'?_fmM(n*1e6):n.toFixed(1)+unit;
        h += `<div class="cmp-kpi"><div class="cmp-kpi-lbl">${lbl}</div><div class="cmp-kpi-v ${cls}">${disp}</div></div>`;
      });
      h += `</div>`;
      if (fin.datas&&fin.datas.length) {
        h += `<div class="cmp-sec-lbl">Último balanço</div>
        <div style="font-size:11px;color:#2d3748">${fin.datas[fin.datas.length-1]||'—'} · Setor: ${fin.setor||'—'}</div>`;
      }
    } else {
      h += `<div style="color:#1a2030;font-size:12px;padding:8px 0 16px">Sem dados financeiros para este emissor.</div>`;
    }

    if (pos.length) {
      h += `<div class="cmp-sec-lbl">Posições · ${_fmM(totPos)}</div><div class="cmp-pos-list">`;
      pos.sort((a,b)=>(b.saldo||0)-(a.saldo||0)).slice(0,8).forEach(a=>{
        h += `<div class="cmp-pos-row">
          <div class="cmp-pos-name">${a['Ativo']||a['ativo']||'—'}</div>
          <div style="display:flex;flex-direction:column;gap:1px;align-items:flex-end">
            <span class="cmp-pos-cls" style="color:#3a5070">${a.carteira||a['Carteira']||'—'}</span>
            <span class="cmp-pos-cls">${a['Classe']||a['classe']||''}</span>
          </div>
          <div class="cmp-pos-val">${_fmM(a.saldo||0)}</div>
        </div>`;
      });
      h += `</div>`;
    } else {
      h += `<div style="color:#1a2030;font-size:11px;padding:6px 0">Sem posições abertas.</div>`;
    }
    document.getElementById('cmpPanel'+idx).innerHTML = h;
    _cmpCache[idx] = {nome};
    if (_cmpCache[0]&&_cmpCache[1]) _applyDuelo();
  }

  /* ── MODE ENGINE — DUELO ÚNICO ────────────────────────────────────────── */
  let _cmpMode = 1;
  const _cmpCache = {0:null, 1:null};

  function _applyDuelo() {
    if (!_cmpCache[0]||!_cmpCache[1]) return;
    const d0 = document.getElementById('cmpPanel0');
    const d1 = document.getElementById('cmpPanel1');
    if (!d0||!d1) return;
    const fins = typeof FIN_SERIES!=='undefined'?FIN_SERIES:{};
    const _lv2 = arr=>Array.isArray(arr)&&arr.length?arr[arr.length-1]:null;
    const METRICS = [
      {k:'Receita_TTM',    lb:'Receita TTM',    inv:false},
      {k:'EBITDA_TTM',     lb:'EBITDA TTM',     inv:false},
      {k:'Mg EBITDA 36M',  lb:'Mg EBITDA',      inv:false},
      {k:'DivLiquida/EBITDA',lb:'Dív/EBITDA',   inv:true},
      {k:'ROE',            lb:'ROE',             inv:false},
      {k:'Liquidez Corrente',lb:'Liq. Corrente', inv:false},
    ];
    let winsA=0,winsB=0;
    const finA = fins[typeof _matchToFin==='function'?_matchToFin(_cmpCache[0].nome):_cmpCache[0].nome]||fins[_cmpCache[0].nome]||null;
    const finB = fins[typeof _matchToFin==='function'?_matchToFin(_cmpCache[1].nome):_cmpCache[1].nome]||fins[_cmpCache[1].nome]||null;
    if (!finA||!finB) return;
    METRICS.forEach(({k,inv})=>{
      const a=parseFloat(_lv2(finA[k])), b=parseFloat(_lv2(finB[k]));
      if (isNaN(a)||isNaN(b)) return;
      const aBetter=inv?(a<b):(a>b), bBetter=inv?(b<a):(b>a);
      if (aBetter) winsA++; else if (bBetter) winsB++;
    });
    const scoreEl = document.getElementById('cmpDueloScore');
    if (!scoreEl) {
      const sc = document.createElement('div');
      sc.id='cmpDueloScore';
      sc.innerHTML = `<span class="cmp-dscore-val" style="color:#b69d74">${winsA}</span><span style="font-size:10px">métricas ganhas</span><span class="cmp-dscore-val" style="color:#6ba4d4">${winsB}</span>`;
      document.getElementById('cmpBody').before(sc);
    } else {
      scoreEl.style.display='flex';
      scoreEl.innerHTML = `<span class="cmp-dscore-val" style="color:#b69d74">${winsA}</span><span style="font-size:10px;color:#1e2840">métricas ganhas</span><span class="cmp-dscore-val" style="color:#6ba4d4">${winsB}</span>`;
    }
  }

  /* _renderCombined removido — apenas modo DUELO */
  function _renderCombined() { /* noop */ }
  function _renderCombined_REMOVED() {
    const fins = typeof FIN_SERIES!=='undefined'?FIN_SERIES:{};
    const _lv2 = arr=>Array.isArray(arr)&&arr.length?arr[arr.length-1]:null;
    const nA = _cmpCache[0].nome, nB = _cmpCache[1].nome;
    const finA = fins[typeof _matchToFin==='function'?_matchToFin(nA):nA]||fins[nA]||{};
    const finB = fins[typeof _matchToFin==='function'?_matchToFin(nB):nB]||fins[nB]||{};
    const METRICS = [
      {k:'Receita_TTM',    lb:'Receita TTM',     fmt:(v)=>`R$${(v/1e9).toFixed(1)}B`, inv:false, unit:'M'},
      {k:'EBITDA_TTM',     lb:'EBITDA TTM',      fmt:(v)=>`R$${(v/1e9).toFixed(1)}B`, inv:false, unit:'M'},
      {k:'Mg EBITDA 36M',  lb:'Mg EBITDA',       fmt:(v)=>`${(v*100).toFixed(1)}%`,   inv:false, unit:'%'},
      {k:'DivLiquida/EBITDA',lb:'Dív/EBITDA',    fmt:(v)=>`${v.toFixed(1)}x`,         inv:true,  unit:'x'},
      {k:'Estrutura de Capital (D/D+E)',lb:'Estr. Capital',fmt:(v)=>`${(v*100).toFixed(0)}%`,inv:true,unit:'%'},
      {k:'ROE',            lb:'ROE',              fmt:(v)=>`${(v*100).toFixed(1)}%`,   inv:false, unit:'%'},
      {k:'ROIC',           lb:'ROIC',             fmt:(v)=>`${(v*100).toFixed(1)}%`,   inv:false, unit:'%'},
      {k:'Liquidez Corrente',lb:'Liq. Corrente',  fmt:(v)=>`${v.toFixed(1)}x`,         inv:false, unit:'x'},
    ];
    if (_cmpMode===2) {
      // RADAR MODE
      const body = document.getElementById('cmpBody');
      body.innerHTML = `<div style="width:100%;display:flex;flex-direction:column;align-items:center;padding:20px">
        <canvas id="cmpRadarChart" style="max-width:380px;max-height:380px"></canvas>
        <div style="display:flex;gap:32px;margin-top:16px;font-size:11px">
          <span style="color:#b69d74">● ${nA}</span><span style="color:#6ba4d4">● ${nB}</span>
        </div>
      </div>`;
      const labels=[],dA=[],dB=[];
      METRICS.forEach(({k,lb,inv})=>{
        const a=parseFloat(_lv2(finA[k])),b=parseFloat(_lv2(finB[k]));
        if(isNaN(a)||isNaN(b)) return;
        labels.push(lb);
        const mn=Math.min(a,b),mx=Math.max(a,b),rng=mx-mn||1;
        const na=inv?(1-(a-mn)/rng):(a-mn)/rng;
        const nb=inv?(1-(b-mn)/rng):(b-mn)/rng;
        dA.push(+(na*100).toFixed(0)); dB.push(+(nb*100).toFixed(0));
      });
      if (typeof Chart!=='undefined'&&labels.length) {
        new Chart(document.getElementById('cmpRadarChart'),{
          type:'radar',
          data:{labels,datasets:[
            {label:nA,data:dA,borderColor:'#b69d74',backgroundColor:'rgba(182,157,116,.12)',borderWidth:2,pointBackgroundColor:'#b69d74'},
            {label:nB,data:dB,borderColor:'#3174b8',backgroundColor:'rgba(49,116,184,.1)',borderWidth:2,pointBackgroundColor:'#3174b8'}
          ]},
          options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{display:false}},
            scales:{r:{ticks:{display:false,stepSize:25},grid:{color:'rgba(255,255,255,.06)'},pointLabels:{color:'#3a4558',font:{size:10}},angleLines:{color:'rgba(255,255,255,.05)'}}}}
        });
      }
    } else if (_cmpMode===4) {
      // DELTA MODE
      const corps = typeof RANK_CORP!=='undefined'?RANK_CORP:[];
      const banks = typeof RANK_BANCOS!=='undefined'?RANK_BANCOS:[];
      const riA = corps.find(r=>r.empresa===nA)||banks.find(r=>r.empresa===nA)||{};
      const riB = corps.find(r=>r.empresa===nB)||banks.find(r=>r.empresa===nB)||{};
      let winsA=0,winsB=0,rows='';
      METRICS.forEach(({k,lb,fmt,inv})=>{
        const a=parseFloat(_lv2(finA[k])),b=parseFloat(_lv2(finB[k]));
        if(isNaN(a)||isNaN(b)){rows+=`<div class="cmp-delta-row"><div class="cmp-delta-metric">${lb}</div><div class="cmp-delta-val" style="color:#1e2840">—</div><div class="cmp-delta-val" style="color:#1e2840">—</div><div class="cmp-delta-diff-col neu">—</div><div></div></div>`;return;}
        const diff=b-a, pct=a!==0?((b-a)/Math.abs(a)*100):0;
        const aBetter=inv?(a<b):(a>b), bBetter=inv?(b<a):(b>a);
        if(aBetter)winsA++; else if(bBetter)winsB++;
        const dCls=bBetter?'pos':aBetter?'neg':'neu';
        const dStr=(diff>0?'+':'')+pct.toFixed(1)+'%';
        const win=aBetter?`<span style="color:#b69d74">A</span>`:bBetter?`<span style="color:#6ba4d4">B</span>`:`<span style="color:#2d3748">—</span>`;
        rows+=`<div class="cmp-delta-row"><div class="cmp-delta-metric">${lb}</div><div class="cmp-delta-val">${fmt(a)}</div><div class="cmp-delta-val">${fmt(b)}</div><div class="cmp-delta-diff-col ${dCls}">${dStr}</div><div class="cmp-delta-win-col">${win}</div></div>`;
      });
      document.getElementById('cmpBody').innerHTML = `
        <div id="cmpDeltaWrap">
          <div class="cmp-delta-score">
            <div><div class="cmp-delta-score-val" style="color:#b69d74">${winsA}</div><div class="cmp-delta-score-lbl">${nA}</div></div>
            <div style="font-size:11px;color:#1e2840;text-align:center">métricas<br>ganhas</div>
            <div><div class="cmp-delta-score-val" style="color:#6ba4d4">${winsB}</div><div class="cmp-delta-score-lbl">${nB}</div></div>
          </div>
          <div class="cmp-delta-hdr"><div>Indicador</div><div>${nA.split(' ')[0]}</div><div>${nB.split(' ')[0]}</div><div>Δ %</div><div style="text-align:center">Vence</div></div>
          ${rows}
        </div>`;
    } else if (_cmpMode===5) {
      // PREMIUM: re-render both panels then add strength bar
      [0,1].forEach(idx=>{ if (_cmpCache[idx]) _renderPanel(idx,_cmpCache[idx].nome); });
      const corps = typeof RANK_CORP!=='undefined'?RANK_CORP:[];
      const banks = typeof RANK_BANCOS!=='undefined'?RANK_BANCOS:[];
      const riA = corps.find(r=>r.empresa===nA)||banks.find(r=>r.empresa===nA)||{};
      const riB = corps.find(r=>r.empresa===nB)||banks.find(r=>r.empresa===nB)||{};
      let winsA=0,winsB=0;
      METRICS.forEach(({k,inv})=>{
        const a=parseFloat(_lv2(finA[k])),b=parseFloat(_lv2(finB[k]));
        if(isNaN(a)||isNaN(b)) return;
        if(inv?(a<b):(a>b)) winsA++; else if(inv?(b<a):(b>a)) winsB++;
      });
      const total=winsA+winsB||1, pctA=Math.round(winsA/total*100);
      const wrap = document.createElement('div');
      wrap.className='cmp-strength-wrap';
      wrap.innerHTML=`<div class="cmp-strength-top"><span class="cmp-strength-nm a">${nA.split(' ')[0]} · ${winsA} pts</span><span class="cmp-strength-sc">Força relativa</span><span class="cmp-strength-nm b">${nB.split(' ')[0]} · ${winsB} pts</span></div><div class="cmp-strength-track"><div class="cmp-strength-fill" style="width:${pctA}%;background:linear-gradient(90deg,#b69d74,#3174b8)"></div></div>`;
      document.getElementById('cmpBody').before(wrap);
    } else if (_cmpMode===6) {
      // STREET FIGHTER MODE
      const corps = typeof RANK_CORP!=='undefined'?RANK_CORP:[];
      const banks = typeof RANK_BANCOS!=='undefined'?RANK_BANCOS:[];
      const riA = corps.find(r=>r.empresa===nA)||banks.find(r=>r.empresa===nA)||{};
      const riB = corps.find(r=>r.empresa===nB)||banks.find(r=>r.empresa===nB)||{};
      let winsA=0,winsB=0;
      const sfMetrics=[];
      METRICS.forEach(({k,lb,fmt,inv})=>{
        const a=parseFloat(_lv2(finA[k])),b=parseFloat(_lv2(finB[k]));
        if(isNaN(a)||isNaN(b)){sfMetrics.push({lb,aVal:'—',bVal:'—',pctA:50,pctB:50,aBetter:false,bBetter:false});return;}
        const aBetter=inv?(a<b):(a>b), bBetter=inv?(b<a):(b>a);
        if(aBetter)winsA++; else if(bBetter)winsB++;
        const mn=Math.min(a,b),mx=Math.max(a,b),rng=mx-mn||1;
        const na=inv?(1-(a-mn)/rng):(a-mn)/rng;
        const nb=inv?(1-(b-mn)/rng):(b-mn)/rng;
        const sum=na+nb||1;
        sfMetrics.push({lb,aVal:fmt(a),bVal:fmt(b),pctA:Math.round(na/sum*100),pctB:Math.round(nb/sum*100),aBetter,bBetter});
      });
      const total=winsA+winsB||1;
      const hpA=Math.round(winsA/total*100), hpB=Math.round(winsB/total*100);
      const winner=winsA>winsB?nA:winsB>winsA?nB:null;
      const emojiA=['🏦','🏢','💰','📈','⚡'][Math.abs(nA.charCodeAt(0))%5];
      const emojiB=['🏦','🏢','💰','📈','⚡'][Math.abs(nB.charCodeAt(0))%5];
      const ratingA=riA.ratingDouro||riA.ratingMkt||'—';
      const ratingB=riB.ratingDouro||riB.ratingMkt||'—';
      const statusA=riA.status||'—', statusB=riB.status||'—';
      let statsHtml='';
      sfMetrics.forEach(({lb,aVal,bVal,pctA,pctB,aBetter,bBetter})=>{
        statsHtml+=`<div class="sf-stat-row">
          <div class="sf-stat-label">${lb}</div>
          <div class="sf-stat-bar-wrap">
            <div class="sf-stat-fill-a" style="width:${pctA}%"></div>
            <div class="sf-stat-fill-b" style="width:${pctB}%"></div>
          </div>
          <div class="sf-stat-vals">
            <span class="av"${aBetter?' style="text-shadow:0 0 6px #ffcd00"':''}>${aVal}</span>
            <span class="lbl">${lb}</span>
            <span class="bv"${bBetter?' style="text-shadow:0 0 6px #00cfff"':''}>${bVal}</span>
          </div>
        </div>`;
      });
      const winBanner=winner
        ?`<div class="sf-winner-banner">${winner===nA?'<span style="color:#ffcd00">'+nA.split(' ')[0]+'</span>':'<span style="color:#00cfff">'+nB.split(' ')[0]+'</span>'} WINS!<br><span class="sf-ko">K.O.</span></div>`
        :`<div class="sf-winner-banner" style="animation:none;color:#aaa">DRAW</div>`;
      document.getElementById('cmpBody').innerHTML=`<div id="cmpSfWrap">
        <div class="sf-fight-word">⚔ FIGHT!</div>
        <div class="sf-arena" style="margin-top:12px">
          <div class="sf-fighter">
            <div class="sf-hb-wrap left">
              <div class="sf-hb-label a">${nA.split(' ')[0]}</div>
              <div class="sf-hb-track"><div class="sf-hb-fill a" style="width:${hpA}%"></div></div>
              <div style="font-size:8px;color:#555;font-family:'Courier New',monospace;letter-spacing:.08em">HP ${hpA}% · ${winsA} wins · ${ratingA}</div>
            </div>
            <div class="sf-portrait a">${emojiA}</div>
            <div class="sf-name a">${nA.split(' ')[0]}</div>
            <div style="font-size:8px;color:#ffcd0066;font-family:'Courier New',monospace">${statusA.toUpperCase()}</div>
          </div>
          <div class="sf-vs-wrap"><div class="sf-vs">VS</div></div>
          <div class="sf-fighter" style="align-items:flex-end">
            <div class="sf-hb-wrap right">
              <div class="sf-hb-label b">${nB.split(' ')[0]}</div>
              <div class="sf-hb-track"><div class="sf-hb-fill b" style="width:${hpB}%;float:right"></div></div>
              <div style="font-size:8px;color:#555;font-family:'Courier New',monospace;letter-spacing:.08em;text-align:right">HP ${hpB}% · ${winsB} wins · ${ratingB}</div>
            </div>
            <div class="sf-portrait b">${emojiB}</div>
            <div class="sf-name b">${nB.split(' ')[0]}</div>
            <div style="font-size:8px;color:#00cfff66;font-family:'Courier New',monospace">${statusB.toUpperCase()}</div>
          </div>
        </div>
        ${winBanner}
        <div class="sf-stats-wrap">${statsHtml}</div>
      </div>`;
    }
  }

  /* ── MODE SWITCHER INTERACTIONS ── */
  (function() {
    const track = document.getElementById('cmpModeTrack');
    if (!track) return;
    let dragging=false, startX=0, startMode=0;
    const segs = ()=>document.querySelectorAll('.cmp-mode-seg');
    const modeFromX = (x) => {
      let best=0, bd=Infinity;
      segs().forEach((el,i)=>{const r=el.getBoundingClientRect(),cx=r.left+r.width/2,d=Math.abs(x-cx);if(d<bd){bd=d;best=i;}});
      return best;
    };
    track.addEventListener('mousedown', e=>{
      dragging=true; startX=e.clientX; startMode=_cmpMode;
      e.preventDefault();
    });
    document.addEventListener('mousemove', e=>{
      if (!dragging) return;
      const m=modeFromX(e.clientX);
      _updateModeThumb(m);
      document.querySelectorAll('.cmp-mode-seg').forEach((el,i)=>el.classList.toggle('active',i===m));
    });
    document.addEventListener('mouseup', e=>{
      if (!dragging) return;
      dragging=false;
      _setMode(modeFromX(e.clientX));
    });
    track.addEventListener('click', e=>{
      const seg=e.target.closest('.cmp-mode-seg');
      if (seg) _setMode(parseInt(seg.dataset.mode));
    });
    // Touch support
    track.addEventListener('touchstart', e=>{dragging=true;startX=e.touches[0].clientX;},{passive:true});
    track.addEventListener('touchmove', e=>{
      if (!dragging) return;
      const m=modeFromX(e.touches[0].clientX);
      _updateModeThumb(m);
      document.querySelectorAll('.cmp-mode-seg').forEach((el,i)=>el.classList.toggle('active',i===m));
    },{passive:true});
    track.addEventListener('touchend', e=>{
      if (!dragging) return;
      dragging=false;
      _setMode(modeFromX(e.changedTouches[0].clientX));
    });
    // Init thumb position
    requestAnimationFrame(()=>_updateModeThumb(0));
  })();

  window._cmpPick = function(idx, nome) {
    document.getElementById('cmpInp'+idx).value = nome;
    document.getElementById('cmpDd'+idx).style.display = 'none';
    const corps = typeof RANK_CORP!=='undefined'?RANK_CORP:[];
    const banks = typeof RANK_BANCOS!=='undefined'?RANK_BANCOS:[];
    const ri = corps.find(r=>r.empresa===nome)||banks.find(r=>r.empresa===nome)||{};
    const st = document.getElementById('cmpSt'+idx);
    st.textContent = ri.status||'—';
    st.className = 'cmp-slot-status '+_bc(ri.status);
    _renderPanel(idx, nome);
  };

  [0,1].forEach(idx=>{
    document.getElementById('cmpInp'+idx).addEventListener('input', e=>_showDd(idx, e.target.value));
    document.getElementById('cmpInp'+idx).addEventListener('keydown', e=>{
      if (e.key==='Escape') document.getElementById('cmpDd'+idx).style.display='none';
    });
    document.getElementById('cmpInp'+idx).addEventListener('blur', ()=>{
      setTimeout(()=>{ const dd=document.getElementById('cmpDd'+idx); if(dd) dd.style.display='none'; }, 200);
    });
  });

  window.closeCmp = function() { document.getElementById('cmpOverlay').classList.remove('open'); };

  document.addEventListener('keydown', e=>{
    if (e.ctrlKey&&e.shiftKey&&e.key==='C') {
      e.preventDefault();
      const ov = document.getElementById('cmpOverlay');
      if (ov.classList.contains('open')) closeCmp();
      else { ov.classList.add('open'); setTimeout(()=>document.getElementById('cmpInp0').focus(), 60); }
    }
    if (e.key==='Escape') document.getElementById('cmpOverlay')?.classList.remove('open');
  });
})();

// ── PAINEL DE DEBUG (Ctrl+Shift+D) ────────────────────────────────────────
(function() {
  const _css = `
    #dbgOverlay {
      display:none; position:fixed; inset:0; z-index:10001;
      background:rgba(0,4,8,.92); backdrop-filter:blur(10px);
      align-items:center; justify-content:center;
      font-family:var(--font,'Montserrat',sans-serif);
    }
    #dbgOverlay.open { display:flex; animation:dbgPop .22s cubic-bezier(.16,1,.3,1); }
    @keyframes dbgPop { from{opacity:0;transform:scale(.95)} to{opacity:1;transform:none} }
    #dbgMatrixCanvas {
      position:absolute; inset:0; width:100%; height:100%;
      opacity:.18; filter:blur(1.2px); pointer-events:none; z-index:0;
    }
    #dbgBox { position:relative; z-index:1; }
    #dbgBox {
      width:min(860px,96vw); max-height:87vh; overflow:hidden;
      background:#030810;
      border:1px solid rgba(47,168,116,.22);
      border-radius:14px; display:flex; flex-direction:column;
      box-shadow:0 0 60px rgba(47,168,116,.06), 0 0 0 1px rgba(47,168,116,.04), 0 40px 100px rgba(0,0,0,.9);
    }
    #dbgHead {
      display:flex; align-items:center; justify-content:space-between;
      padding:14px 22px; border-bottom:1px solid rgba(47,168,116,.1); flex-shrink:0;
      background:rgba(47,168,116,.02);
    }
    #dbgTitle {
      display:flex; align-items:center; gap:9px;
      font-size:11px; font-weight:700; color:#1d7a55; letter-spacing:.14em; text-transform:uppercase;
    }
    .dbg-dot {
      width:7px; height:7px; border-radius:50%; background:#2fa874;
      box-shadow:0 0 8px #2fa874;
      animation:dbgBlink 1.6s ease-in-out infinite;
    }
    @keyframes dbgBlink {
      0%,100%{opacity:1;box-shadow:0 0 8px #2fa874} 50%{opacity:.3;box-shadow:none}
    }
    #dbgCloseBtn {
      background:transparent; border:none; color:#0d4a28; font-size:18px;
      cursor:pointer; padding:4px 8px; border-radius:5px; transition:color .15s;
    }
    #dbgCloseBtn:hover { color:#2fa874; }
    #dbgScroll {
      flex:1; overflow-y:auto; padding:18px 22px; display:flex; flex-direction:column; gap:14px;
    }
    #dbgScroll::-webkit-scrollbar { width:3px; }
    #dbgScroll::-webkit-scrollbar-thumb { background:rgba(47,168,116,.2); border-radius:2px; }
    .dbg-row4 { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
    .dbg-tile {
      background:rgba(47,168,116,.03); border:1px solid rgba(47,168,116,.1);
      border-radius:9px; padding:11px 13px;
    }
    .dbg-tile-lbl { font-size:8.5px; font-weight:700; text-transform:uppercase; letter-spacing:.12em; color:#0d4a28; }
    .dbg-tile-val { font-family:var(--mono,'monospace'); font-size:21px; font-weight:700; color:#2fa874; margin-top:5px; line-height:1; }
    .dbg-tile-sub { font-size:9.5px; color:#0a2e1a; margin-top:2px; }
    .dbg-card { border:1px solid rgba(47,168,116,.08); border-radius:9px; overflow:hidden; }
    .dbg-card-hdr {
      background:rgba(47,168,116,.03); padding:8px 15px;
      font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:.12em; color:#0d4a28;
      border-bottom:1px solid rgba(47,168,116,.07);
    }
    .dbg-tbl { width:100%; border-collapse:collapse; }
    .dbg-tbl td { padding:6px 15px; font-size:11.5px; border-bottom:1px solid rgba(47,168,116,.04); vertical-align:middle; }
    .dbg-tbl td:first-child { color:#1d5c3a; font-weight:600; width:38%; white-space:nowrap; display:table-cell; }
    .dbg-tbl td:nth-child(2) { font-family:var(--mono,'monospace'); color:#2fa874; }
    .dbg-tbl td:nth-child(3) { font-family:var(--mono,'monospace'); color:#2fa874; text-align:right; white-space:nowrap; }
    .dbg-tbl td:last-child  { font-family:var(--mono,'monospace'); color:#2fa874; }
    .dbg-tbl tr:last-child td { border-bottom:none; }
    .dbg-log-wrap { padding:10px 15px; max-height:160px; overflow-y:auto; }
    .dbg-log-wrap::-webkit-scrollbar { width:2px; }
    .dbg-log-wrap::-webkit-scrollbar-thumb { background:rgba(47,168,116,.15); }
    .dbg-log-line { display:flex; gap:10px; font-size:10.5px; line-height:1.8; }
    .dbg-log-ts  { color:#052a14; flex-shrink:0; font-family:var(--mono,'monospace'); }
    .dbg-log-msg { color:#1d7a55; font-family:var(--mono,'monospace'); }
    .dbg-log-msg.w { color:#b69d74; }
    #dbgFoot {
      padding:8px 22px; border-top:1px solid rgba(47,168,116,.07); flex-shrink:0;
      display:flex; justify-content:space-between;
      font-size:9.5px; color:#052a14; font-family:var(--mono,'monospace');
    }
  `;
  const st = document.createElement('style'); st.textContent = _css; document.head.appendChild(st);

  document.body.insertAdjacentHTML('beforeend', `
    <div id="dbgOverlay">
      <canvas id="dbgMatrixCanvas"></canvas>
      <div id="dbgBox">
        <div id="dbgHead">
          <div id="dbgTitle"><div class="dbg-dot"></div>SYSTEM DIAGNOSTICS</div>
          <button id="dbgCloseBtn" onclick="closeDbg()">&#x2715;</button>
        </div>
        <div id="dbgScroll"></div>
        <div id="dbgFoot"><span id="dbgTs"></span><span>Ctrl+Shift+D para fechar</span></div>
      </div>
    </div>
  `);

  const _logs = [];
  const _origLog = console.log.bind(console);
  console.log = function(...a) {
    _origLog(...a);
    const msg = a.map(x=>typeof x==='object'?JSON.stringify(x):String(x)).join(' ');
    _logs.push({ts: new Date().toLocaleTimeString('pt-BR'), msg, w: msg.toLowerCase().includes('erro')||msg.toLowerCase().includes('falha')});
    if (_logs.length > 60) _logs.shift();
  };

  function _fmM(v) {
    if (!v||isNaN(v)) return '—';
    return v>=1e9?'R$'+(v/1e9).toFixed(1)+'B':v>=1e6?'R$'+(v/1e6).toFixed(0)+'M':'R$'+(v/1e3).toFixed(0)+'K';
  }

  function _fmAge(h) {
    if (h < 0)   return {txt:'—', cls:''};
    if (h < 1)   return {txt:'há menos de 1h', cls:'g'};
    if (h < 6)   return {txt:`há ${h}h`, cls:'g'};
    if (h < 24)  return {txt:`há ${h}h`, cls:''};
    if (h < 48)  return {txt:`há ${Math.floor(h/24)}d`, cls:'o'};
    return       {txt:`há ${Math.floor(h/24)}d`, cls:'r'};
  }

  function _build() {
    const at  = typeof ATIVOS!=='undefined'?ATIVOS:[];
    const rc  = typeof RANK_CORP!=='undefined'?RANK_CORP:[];
    const rb  = typeof RANK_BANCOS!=='undefined'?RANK_BANCOS:[];
    const fs  = typeof FIN_SERIES!=='undefined'?FIN_SERIES:{};
    const bk  = typeof _BCB_DATA!=='undefined'?_BCB_DATA:{};
    const bl  = typeof BCB_LIVE!=='undefined'?BCB_LIVE:{};
    const nd  = typeof NEWS_DATA!=='undefined'?(NEWS_DATA.noticias||[]).length:0;
    const pl  = typeof PL_TOTAL!=='undefined'?PL_TOTAL:0;
    const bi  = typeof BUILD_INFO!=='undefined'?BUILD_INFO:{};
    const tc  = at.filter(a=>(a.saldo||0)>0).reduce((s,a)=>s+(a.saldo||0),0);
    const fsK = Object.keys(fs).length;
    const bkK = Object.keys(bk).length;
    const blK = Object.keys(bl).length;

    document.getElementById('dbgTs').textContent = 'Snapshot ' + new Date().toLocaleTimeString('pt-BR');

    // ── Card de timestamps ──────────────────────────────────────────────────
    const isDadosVivos = bi.dados_vivos;
    const modoNum = bi.modo_num || '?';
    const modoCor = modoNum==='1' ? '#2fa874' : modoNum==='3' ? '#b69d74' : '#3174b8';
    const modoIcon = modoNum==='1'
      ? '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>'
      : modoNum==='3'
      ? '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'
      : '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>';

    // bloco principal: geração do HTML
    const geradoAge = _fmAge(
      bi.arquivos&&bi.arquivos.length
        ? Math.min(...(bi.arquivos.filter(a=>a.ok).map(a=>a.horas).filter(h=>h>=0)))
        : -1
    );

    const mainLabel = isDadosVivos
      ? 'Geração do HTML (dados ao vivo — Modo 1)'
      : 'Geração do HTML (dados locais — Modo 3)';
    const mainSub = isDadosVivos
      ? 'Comdinheiro + CVM buscados ao rodar o script'
      : 'Comdinheiro NÃO consultado · dados das planilhas locais';

    // arquivos rastreados
    const arqRows = (bi.arquivos||[]).map(a => {
      const age = _fmAge(a.horas);
      const dotCls = !a.ok ? 'r' : a.horas < 0 ? '' : a.horas < 6 ? 'g' : a.horas < 48 ? 'o' : 'r';
      const dotColor = dotCls==='g'?'#2fa874':dotCls==='o'?'#b69d74':dotCls==='r'?'#d94141':'#2d3748';
      return `<tr>
        <td style="display:flex;align-items:center;gap:7px;">
          <span style="width:6px;height:6px;border-radius:50%;background:${dotColor};flex-shrink:0;display:inline-block;${dotCls==='g'?'box-shadow:0 0 5px '+dotColor+';':''}"></span>
          ${a.nome}
        </td>
        <td>${a.ok?a.ts:'<span style="color:#d94141">não encontrado</span>'}</td>
        <td style="color:${dotColor};font-size:10px;white-space:nowrap;">${a.ok?age.txt:'—'}</td>
      </tr>`;
    }).join('');

    const isOld = (bi.arquivos||[]).some(a=>a.ok&&a.horas>72);
    const alertHtml = isOld
      ? `<div style="display:flex;align-items:center;gap:8px;background:rgba(217,65,65,.06);border:1px solid rgba(217,65,65,.2);border-radius:7px;padding:8px 12px;margin-top:2px;">
           <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#d94141" stroke-width="2.2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
           <span style="font-size:10px;color:#d94141;">Uma ou mais planilhas de base estão desatualizadas (mais de 72h). Considere reabrir e salvar.</span>
         </div>`
      : '';

    const logHtml = _logs.length
      ? [..._logs].reverse().map(l=>`<div class="dbg-log-line"><span class="dbg-log-ts">${l.ts}</span><span class="dbg-log-msg${l.w?' w':''}">${l.msg}</span></div>`).join('')
      : '<span style="color:#052a14;font-size:10px">Nenhum log capturado ainda.</span>';

    document.getElementById('dbgScroll').innerHTML = `
      <div class="dbg-row4">
        <div class="dbg-tile"><div class="dbg-tile-lbl">Ativos</div><div class="dbg-tile-val">${at.length}</div><div class="dbg-tile-sub">Carteira: ${_fmM(tc)}</div></div>
        <div class="dbg-tile"><div class="dbg-tile-lbl">Corp. Rank</div><div class="dbg-tile-val">${rc.length}</div><div class="dbg-tile-sub">FIN_SERIES: ${fsK} emp.</div></div>
        <div class="dbg-tile"><div class="dbg-tile-lbl">Bancos BCB</div><div class="dbg-tile-val">${blK}</div><div class="dbg-tile-sub">_BCB_DATA: ${bkK} total</div></div>
        <div class="dbg-tile"><div class="dbg-tile-lbl">Notícias</div><div class="dbg-tile-val">${nd}</div><div class="dbg-tile-sub">PL: ${_fmM(pl)}</div></div>
      </div>

      <div class="dbg-card">
        <div class="dbg-card-hdr" style="display:flex;align-items:center;justify-content:space-between;">
          <span>Última Atualização dos Dados</span>
          <span style="display:inline-flex;align-items:center;gap:5px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:5px;padding:2px 9px;font-size:9px;color:${modoCor};">
            ${modoIcon}&nbsp;Modo ${modoNum} · ${bi.modo||'—'}
          </span>
        </div>
        <div style="padding:12px 15px;display:flex;flex-direction:column;gap:10px;">

          <!-- Geração do HTML -->
          <div style="display:flex;align-items:flex-start;gap:12px;padding:10px 12px;background:rgba(47,168,116,.04);border:1px solid rgba(47,168,116,.12);border-radius:8px;">
            <div style="width:8px;height:8px;border-radius:50%;background:#2fa874;box-shadow:0 0 7px #2fa874;flex-shrink:0;margin-top:3px;"></div>
            <div style="flex:1;">
              <div style="font-size:9.5px;font-weight:700;color:#1d7a55;letter-spacing:.06em;text-transform:uppercase;margin-bottom:3px;">${mainLabel}</div>
              <div style="font-family:var(--mono,'monospace');font-size:15px;font-weight:700;color:#2fa874;">${bi.gerado_em||'—'}</div>
              <div style="font-size:9.5px;color:#0a2e1a;margin-top:3px;">${mainSub}</div>
            </div>
          </div>

          <!-- Planilhas de base -->
          <div>
            <div style="font-size:8.5px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#0d4a28;margin-bottom:7px;">
              ${isDadosVivos ? 'Planilhas de Referência (Scorecard · Watch List)' : 'Planilhas de Base (fonte dos dados neste build)'}
            </div>
            <table class="dbg-tbl" style="width:100%">
              <colgroup><col style="width:44%"><col style="width:34%"><col style="width:22%"></colgroup>
              ${arqRows||'<tr><td colspan="3" style="color:#052a14">Nenhum arquivo rastreado.</td></tr>'}
            </table>
            ${alertHtml}
          </div>

        </div>
      </div>

      <div class="dbg-card">
        <div class="dbg-card-hdr">Variáveis Injetadas pelo Python</div>
        <table class="dbg-tbl">
          <tr><td>ATIVOS</td><td>${at.length} registros · ${new Set(at.map(a=>a.emissor).filter(Boolean)).size} emissores únicos</td></tr>
          <tr><td>FIN_SERIES</td><td>${fsK} empresas com séries financeiras</td></tr>
          <tr><td>RANK_CORP</td><td>${rc.length} emissores corporativos</td></tr>
          <tr><td>RANK_BANCOS</td><td>${rb.length} bancos no ranking</td></tr>
          <tr><td>BCB_LIVE</td><td>${blK} bancos com dados ao vivo</td></tr>
          <tr><td>NEWS_DATA</td><td>${nd} notícias curadas</td></tr>
          <tr><td>PL_TOTAL</td><td>${_fmM(pl)}</td></tr>
          <tr><td>SPREADS_TS</td><td>${typeof SPREADS_TS!=='undefined'?SPREADS_TS.length+' pontos':'—'}</td></tr>
          <tr><td>PERF_DATA</td><td>${typeof PERF_DATA!=='undefined'?JSON.stringify(PERF_DATA).length+' bytes':'—'}</td></tr>
        </table>
      </div>
      <div class="dbg-card">
        <div class="dbg-card-hdr">Log do Sistema (${_logs.length} entradas)</div>
        <div class="dbg-log-wrap">${logHtml}</div>
      </div>
    `;
  }

  window.openDbg  = function() { _build(); document.getElementById('dbgOverlay').classList.add('open'); };
  window.closeDbg = function() { document.getElementById('dbgOverlay').classList.remove('open'); };

  // Matrix rain animation
  (function() {
    const cvs = document.getElementById('dbgMatrixCanvas');
    const ctx = cvs.getContext('2d');
    const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&アイウエオカキクケコサシスセソタチツテトナニヌネノ';
    const FS = 13;
    let cols, drops, raf;
    function _resize() {
      cvs.width  = cvs.offsetWidth  || window.innerWidth;
      cvs.height = cvs.offsetHeight || window.innerHeight;
      cols  = Math.floor(cvs.width / FS);
      drops = Array.from({length: cols}, () => Math.random() * -50 | 0);
    }
    function _tick() {
      ctx.fillStyle = 'rgba(0,4,8,.18)';
      ctx.fillRect(0, 0, cvs.width, cvs.height);
      ctx.font = FS + 'px monospace';
      for (let i = 0; i < cols; i++) {
        const ch = CHARS[Math.random() * CHARS.length | 0];
        const bright = Math.random() > 0.92;
        ctx.fillStyle = bright ? '#afffdd' : '#2fa874';
        ctx.fillText(ch, i * FS, drops[i] * FS);
        if (drops[i] * FS > cvs.height && Math.random() > 0.975) drops[i] = 0;
        drops[i] += 0.45;
      }
      raf = requestAnimationFrame(_tick);
    }
    function _start() {
      _resize();
      if (!raf) _tick();
    }
    function _stop() {
      if (raf) { cancelAnimationFrame(raf); raf = null; }
    }
    const _origOpen  = window.openDbg  || function(){};
    const _origClose = window.closeDbg || function(){};
    window.openDbg  = function() { _origOpen();  _start(); };
    window.closeDbg = function() { _origClose(); _stop();  };
    window.addEventListener('resize', () => { if (raf) _resize(); });
  })();

  document.getElementById('dbgOverlay').addEventListener('click', e=>{
    if (e.target === document.getElementById('dbgOverlay')) closeDbg();
  });

  document.addEventListener('keydown', e=>{
    if (e.ctrlKey&&e.shiftKey&&e.key==='D') {
      e.preventDefault();
      document.getElementById('dbgOverlay').classList.contains('open') ? closeDbg() : openDbg();
    }
    if (e.key==='Escape') closeDbg();
  });
})();
"""
html_final = html_final.replace('<!--HIDDEN_FEATURES-->', _hidden_js)

out_path = os.path.join(BASE_INV,
    r"Análise de Crédito\Comitê de acompanhamento\Overview Plataforma\Overview Crédito.html")
# Escreve em chunks de 8 MB: substitui NaN→null por pedaço para não duplicar a string inteira na RAM
_CHUNK = 8 * 1024 * 1024
with open(out_path, "w", encoding="utf-8") as fout:
    for _i in range(0, len(html_final), _CHUNK):
        fout.write(re.sub(r'\bNaN\b', 'null', html_final[_i:_i+_CHUNK]))

print(f"[OK] HTML gerado: {out_path}")
webbrowser.open(f"file:///{out_path.replace(os.sep, '/')}")