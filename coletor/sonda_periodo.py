"""Abre o filtro PERIODO da página Mortes e mostra como ele é (itens, se expande para meses). Só leitura."""
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import abrir_pagina, frame_relatorio

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(c.url_relatorio("mortes"), wait_until="domcontentloaded")
    c.esperar_relatorio(page)
    abrir_pagina(page, "Mortes", c.esperar_relatorio)
    fr = frame_relatorio(page)
    caixas = fr.locator(".slicer-container")
    for k in range(caixas.count()):
        print("slicer", k, repr(caixas.nth(k).inner_text()[:60]))
    caixa = caixas.filter(has_text="2026").first
    caixa.locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click()
    page.wait_for_timeout(1500)
    for it in fr.locator(".slicerItemContainer").all():
        cls = it.locator(".slicerCheckbox").first.get_attribute("class") or ""
        print(repr(it.inner_text().strip()), "marcado" if "selected" in cls else "", it.get_attribute("aria-expanded"))
    exp = fr.locator(".slicerItemContainer .expandButton, .slicerItemContainer [class*=expand]")
    print("botões de expandir:", exp.count())
    ano = fr.locator(".slicerItemContainer").filter(has_text="2026").first
    ano.locator(".expandButton, [class*=expand]").first.click()
    page.wait_for_timeout(1500)
    print("--- depois de expandir 2026")
    for it in fr.locator(".slicerItemContainer").all():
        cls = it.locator(".slicerCheckbox").first.get_attribute("class") or ""
        print(repr(it.inner_text().strip()), "marcado" if "selected" in cls else "", it.get_attribute("aria-level"), it.get_attribute("aria-expanded"))
    page.screenshot(path=str(c.DUMP / "sonda_periodo.png"))
    page.keyboard.press("Escape")
    ctx.close()
