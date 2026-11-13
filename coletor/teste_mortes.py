"""Roda só a leitura de mortes e atualiza visao.mortes no ../bi.js."""
import json
from playwright.sync_api import sync_playwright
import coletor as c
from destino import publicar
from extracoes import abrir_pagina, mortes

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(c.url_relatorio("mortes"), wait_until="domcontentloaded")
    c.esperar_relatorio(page)
    abrir_pagina(page, "Mortes", c.esperar_relatorio)
    m = mortes(page, c.esperar_relatorio)
    ctx.close()
print(json.dumps(m, ensure_ascii=True))
cab, corpo = c.SAIDA.read_text(encoding="utf-8").split("window.DADOS_BI = ", 1)
d = json.loads(corpo.rstrip().rstrip(";"))
d["visao"]["mortes"] = m
c.SAIDA.write_text(cab + "window.DADOS_BI = " + json.dumps(d, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
publicar(c.SAIDA)
