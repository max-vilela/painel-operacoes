"""Salva o texto das páginas dos BIs novos da faixa (estoque, RH, plantio) em dump/ para escrever as extrações."""
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import abrir_pagina, frame_relatorio

ALVOS = [("estoque", ["Estoque de Bovinos", "Estoque de Graos", "Estoque Combustivel"]),
         ("rh", [None]), ("plantio", ["Plantio por Fazenda", None])]

c.DUMP.mkdir(exist_ok=True)
with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    for rel, paginas in ALVOS:
        page.goto(c.url_relatorio(rel), wait_until="domcontentloaded")
        if not c.esta_logado(page):
            raise SystemExit("Sem login")
        c.esperar_relatorio(page)
        for pg in paginas:
            if pg:
                abrir_pagina(page, pg, c.esperar_relatorio)
            fr = frame_relatorio(page)
            nome = f"novo_{rel}_{(pg or 'inicial').replace(' ', '_')}"
            (c.DUMP / (nome + ".txt")).write_text(fr.inner_text("body"), encoding="utf-8")
            page.screenshot(path=str(c.DUMP / (nome + ".png")))
            print("ok", nome)
    ctx.close()
