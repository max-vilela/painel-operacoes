"""Só leitura: mostra, nos BIs de plantio e colheita, qual período/safra está selecionado e quais existem na lista do filtro."""
import re
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import abrir_pagina, frame_relatorio, _marcado


def lista(page, campo):
    fr = frame_relatorio(page)
    cx = fr.locator(".slicer-container").filter(has_text=campo).first
    atual = cx.inner_text().strip().replace("\n", " ")
    cx.locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click(); page.wait_for_timeout(1500)
    itens, vistos = [], set()
    for _ in range(20):
        for it in fr.locator(".slicerItemContainer:visible").all():
            t = it.inner_text().strip()
            if t and t not in vistos:
                vistos.add(t); itens.append((t, _marcado(it)))
        rolou = fr.locator(".slicerItemContainer:visible").first.evaluate("""el => { for (let p = el.parentElement; p; p = p.parentElement)
            if (p.scrollHeight > p.clientHeight + 4) { const a = p.scrollTop; p.scrollTop += 150; return p.scrollTop !== a; } return false; }""")
        page.wait_for_timeout(400)
        if not rolou:
            break
    page.keyboard.press("Escape"); page.mouse.click(1590, 170); page.wait_for_timeout(1200)
    return atual, itens


with sync_playwright() as p:
    ctx = c.abrir(p, headless=True); page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    for rel, pagina, campo in (("plantio", "Plantio por Fazenda", "SOJA SAFRA"),
                               ("colheita_soja", "Produção por Fazenda - Sintetico", "DE_PER_SAFRA"),
                               ("colheita_milho", "Produção por Fazenda - Sintetico", "DE_PER_SAFRA")):
        page.goto(c.url_relatorio(rel), wait_until="domcontentloaded"); c.esperar_relatorio(page)
        abrir_pagina(page, pagina, c.esperar_relatorio)
        try:
            atual, itens = lista(page, campo)
            marc = [t for t, m in itens if m]
            print(f"\n== {rel} / {campo}\n  selecionado agora: {atual!r}\n  marcados: {marc}\n  todos ({len(itens)}): {[t for t, _ in itens]}")
        except Exception as e:
            print(f"\n== {rel}: erro {str(e)[:120]}")
    ctx.close()
