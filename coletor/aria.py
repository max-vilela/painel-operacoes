"""Lista os aria-label dos gráficos de uma página (categoria + valor completos). Uso: python aria.py ID [PAGINA] [FILTRO]"""
import sys
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import abrir_pagina, frame_relatorio

rid = sys.argv[1]
pg = sys.argv[2] if len(sys.argv) > 2 else None
filtro = sys.argv[3] if len(sys.argv) > 3 else ""
with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(f"{c.PORTAL}/Report/{rid}", wait_until="domcontentloaded")
    c.esperar_relatorio(page)
    if pg:
        abrir_pagina(page, pg, c.esperar_relatorio)
    fr = frame_relatorio(page)
    for a in fr.eval_on_selector_all("[aria-label]", "els => els.map(e => e.getAttribute('aria-label'))"):
        if filtro.lower() in a.lower() and len(a) < 200:
            print(a)
    ctx.close()
