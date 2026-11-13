"""Salva texto + print de páginas de um relatório (para escrever extrações).
Uso: python dump_rel.py ID_DO_RELATORIO [PAGINA ...]   (sem página = a inicial; '?' lista só as páginas)"""
import sys
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import abrir_pagina, frame_relatorio

rid, paginas = sys.argv[1], sys.argv[2:] or [None]
c.DUMP.mkdir(exist_ok=True)
with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(f"{c.PORTAL}/Report/{rid}", wait_until="domcontentloaded")
    if not c.esta_logado(page):
        raise SystemExit("Sem login")
    c.esperar_relatorio(page)
    for pg in paginas:
        if pg and pg != "?":
            abrir_pagina(page, pg, c.esperar_relatorio)
        nome = f"rel_{rid[:8]}_{(pg or 'inicial').replace(' ', '_').replace('?', 'lista')}"
        (c.DUMP / (nome + ".txt")).write_text(frame_relatorio(page).inner_text("body"), encoding="utf-8")
        page.screenshot(path=str(c.DUMP / (nome + ".png")))
        print("ok", nome)
    ctx.close()
