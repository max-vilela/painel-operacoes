"""Roda só a leitura das férias do escritório de Campo Grande e grava visao.rh.retornosCG no ../bi.js."""
import json
from datetime import date
from playwright.sync_api import sync_playwright
import coletor as c
from destino import publicar
from extracoes import ferias_cg

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True); page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    page.goto(c.url_relatorio("rh"), wait_until="domcontentloaded"); c.esperar_relatorio(page)
    r = ferias_cg(page, c.esperar_relatorio, date.today())
    ctx.close()
print(json.dumps(r, ensure_ascii=False))
cab, corpo = c.SAIDA.read_text(encoding="utf-8").split("window.DADOS_BI = ", 1)
d = json.loads(corpo.rstrip().rstrip(";"))
d["visao"]["rh"]["retornosCG"], d["visao"]["rh"]["entramCG"] = r["retornos"], r["entram"]
c.SAIDA.write_text(cab + "window.DADOS_BI = " + json.dumps(d, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
publicar(c.SAIDA)
