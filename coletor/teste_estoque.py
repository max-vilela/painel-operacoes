"""Roda só a leitura do Gerenciamento do Estoque e atualiza rebanho/estoqueGraos/combustivel no ../bi.js
(mantém o 'negociado' calculado na última coleta completa)."""
import json
from playwright.sync_api import sync_playwright
import coletor as c
from destino import publicar
from extracoes import ger_estoque

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(c.url_relatorio("ger_estoque"), wait_until="domcontentloaded")
    c.esperar_relatorio(page)
    e = ger_estoque(page, c.esperar_relatorio)
    ctx.close()
print(json.dumps(e, ensure_ascii=True))
cab, corpo = c.SAIDA.read_text(encoding="utf-8").split("window.DADOS_BI = ", 1)
d = json.loads(corpo.rstrip().rstrip(";"))
antigo = d["visao"].get("estoqueGraos", {})
for k, g in e["estoqueGraos"].items():
    if "negociado" in antigo.get(k, {}):
        g["negociado"] = antigo[k]["negociado"]
d["visao"].update(e)
c.SAIDA.write_text(cab + "window.DADOS_BI = " + json.dumps(d, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
publicar(c.SAIDA)
