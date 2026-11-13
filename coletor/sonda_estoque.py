"""Lista os slicers da página 'Saldo Atual de Produtos' (Gerenciamento do Estoque): texto e aria-label. Só leitura."""
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import abrir_pagina, frame_relatorio

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(c.url_relatorio("ger_estoque"), wait_until="domcontentloaded")
    c.esperar_relatorio(page)
    abrir_pagina(page, "Saldo Atual de Produtos", c.esperar_relatorio)
    fr = frame_relatorio(page)
    cx = fr.locator(".slicer-container")
    for k in range(cx.count()):
        el = cx.nth(k)
        print(k, repr(el.inner_text()[:40]), "|", repr(el.evaluate("e => e.textContent")[:60]), "|",
              el.evaluate("e => (e.closest('[aria-label]')||{}).getAttribute ? e.closest('[aria-label]').getAttribute('aria-label') : ''")[:80])
    ctx.close()
