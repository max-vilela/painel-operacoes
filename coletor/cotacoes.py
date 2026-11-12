"""Cotações de mercado do painel: boi gordo, soja e milho (Diamantino, Sapezal, MT).

Fontes públicas, lidas por HTTP (não usa o portal nem login):
  - Agrolink (regional/mt/<cidade>/cotacoes): praça Diamantino e Sapezal, com data de cada preço.
  - Notícias Agrícolas, tabelas do Imea: boi à vista, soja e milho disponível por praça de MT.
    O Imea não publica um número único do estado nessas páginas; "MT" = média simples das praças.

Grava ../mercado.js (window.DADOS_MERCADO). Se uma fonte falhar, mantém o valor anterior daquela célula
e deixa a data antiga aparecer (o painel avisa quando o dado está velho).

Uso: python cotacoes.py
"""
import html
import json
import re
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

SAIDA = Path(__file__).resolve().parent.parent / "mercado.js"
UA = {"User-Agent": "Mozilla/5.0 (painel-operacoes; uso interno)"}
AGROLINK = "https://www.agrolink.com.br/regional/mt/{}/cotacoes"
NA = "https://www.noticiasagricolas.com.br/cotacoes/"
PRODUTOS = [  # chave interna, rótulo, unidade, favKey do Agrolink, página Imea
    ("boi", "Boi gordo", "@", "boi-gordo-15kg", "boi-gordo/boi-a-vista-imea"),
    ("soja", "Soja", "sc", "soja-em-grao-sc-60kg", "soja/soja-disponivel-imea"),
    ("milho", "Milho", "sc", "milho-seco-sc-60kg", "milho/milho-disponivel-imea"),
]
PRACAS = [("diamantino", "Diamantino"), ("sapezal", "Sapezal")]


def baixar(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")


def agrolink(cidade):
    """{favKey: (preco, var%, data)} com o registro mais recente de cada produto."""
    h = baixar(AGROLINK.format(cidade))
    padrao = re.compile(
        r'\\"preco\\":([\d.]+),\\"variacaoPct\\":(-?[\d.eE-]+),\\"freq\\":\\"diario\\",\\"dia\\":(\d+),\\"favKey\\":\\"([a-z0-9-]+)\|mt\|' + cidade)
    melhores = {}
    for preco, var, dia, chave in padrao.findall(h):
        dia = int(dia)
        if chave not in melhores or dia > melhores[chave][2]:
            melhores[chave] = (float(preco), float(var), dia)
    return {k: (p, v, date(1970, 1, 1) + timedelta(days=d)) for k, (p, v, d) in melhores.items()}


def num_br(s):
    return float(s.replace(".", "").replace(",", ".").replace("+", ""))


def imea(pagina):
    """Média simples das praças do Imea na primeira tabela da página (valor do dia mais recente)."""
    h = baixar(NA + pagina)
    tabela = re.search(r"<table.*?</table>", h, flags=re.S).group(0)
    precos, vars_ = [], []
    for linha in re.findall(r"<tr.*?</tr>", tabela, flags=re.S)[1:]:
        c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td.*?</td>", linha, flags=re.S)]
        if len(c) >= 3:
            precos.append(num_br(c[1])); vars_.append(num_br(c[2]))
    if not precos:
        raise RuntimeError("tabela Imea vazia: " + pagina)
    d = re.search(r"(\d\d/\d\d/\d{4})", h[h.find(tabela) - 1500: h.find(tabela) + len(tabela) + 300])
    data = datetime.strptime(d.group(1), "%d/%m/%Y").date() if d else None
    return sum(precos) / len(precos), sum(vars_) / len(vars_), data, len(precos)


def fmt(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    anterior = {}
    if SAIDA.exists():
        try:
            anterior = json.loads(SAIDA.read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";"))
        except Exception:
            anterior = {}
    antigas = {(l["produto"], i): c for l in anterior.get("linhas", []) for i, c in enumerate(l["valores"])}

    dados, erros = {}, []
    for slug, _ in PRACAS:
        try:
            dados[slug] = agrolink(slug)
        except Exception as e:
            erros.append(f"agrolink {slug}: {e}"); dados[slug] = {}
    linhas = []
    for chave, rotulo, unidade, favkey, pagina in PRODUTOS:
        valores = []
        for i, (slug, _) in enumerate(PRACAS):
            reg = dados[slug].get(favkey)
            if reg:
                valores.append({"valor": fmt(reg[0]), "var": round(reg[1], 2), "data": reg[2].isoformat()})
            else:
                valores.append(antigas.get((rotulo, i), {"valor": "–", "var": 0}))
        try:
            p, v, dt, n = imea(pagina)
            valores.append({"valor": fmt(p), "var": round(v, 2), "data": dt.isoformat() if dt else None, "praças": n})
        except Exception as e:
            erros.append(f"imea {pagina}: {e}")
            valores.append(antigas.get((rotulo, 2), {"valor": "–", "var": 0}))
        linhas.append({"produto": rotulo, "unidade": unidade, "valores": valores})
    out = {"atualizadoEm": datetime.now().astimezone().isoformat(timespec="seconds"),
           "pracas": ["Diamantino", "Sapezal", "MT (méd. Imea)"], "linhas": linhas, "erros": erros}
    SAIDA.write_text("// GERADO por coletor/cotacoes.py. Não editar à mão.\nwindow.DADOS_MERCADO = "
                     + json.dumps(out, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    for l in linhas:
        print(l["produto"], [(v["valor"], v["var"], v.get("data")) for v in l["valores"]])
    if erros:
        print("ERROS:", erros)


if __name__ == "__main__":
    main()
