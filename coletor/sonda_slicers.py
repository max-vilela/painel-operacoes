import sys
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import abrir_pagina, frame_relatorio
with sync_playwright() as p:
    ctx = c.abrir(p, headless=True); page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    page.goto(c.url_relatorio(sys.argv[1]), wait_until="domcontentloaded"); c.esperar_relatorio(page)
    if len(sys.argv) > 2: abrir_pagina(page, sys.argv[2], c.esperar_relatorio)
    fr = frame_relatorio(page); cx = fr.locator(".slicer-container")
    for k in range(cx.count()):
        e = cx.nth(k)
        print(k, repr(e.inner_text()[:30]), "|", repr(e.evaluate("e => e.textContent")[:70]))
    ctx.close()
