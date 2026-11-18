"""Solta os filtros FILIAL e CONTRATO de 'Todos os Contratos vs Romaneios', ordena por DT HORA PESO 2 (desc) e lista as últimas pesagens."""
import re
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import abrir_pagina, frame_relatorio, linhas_visiveis, _marcado

def selecionar_tudo(page, campo):
    fr = frame_relatorio(page)
    cx = fr.locator(".slicer-container").filter(has_text=campo).first
    cx.locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click()
    page.wait_for_timeout(1500)
    tudo = fr.locator(".slicerItemContainer:visible").filter(has_text=re.compile(r"^\s*Selecionar tudo\s*$")).first
    if tudo.count() and not _marcado(tudo):
        tudo.click(); page.wait_for_timeout(2500)
    page.keyboard.press("Escape"); page.mouse.click(1590, 170); page.wait_for_timeout(3000)

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    page.goto(c.url_relatorio("romaneios"), wait_until="domcontentloaded")
    c.esperar_relatorio(page)
    abrir_pagina(page, "Todos os Contratos vs Romaneios", c.esperar_relatorio)
    for campo in ("FILIAL(", "NJJ_CODCTR"):
        selecionar_tudo(page, campo); c.esperar_relatorio(page)
    fr = frame_relatorio(page)
    cab = fr.get_by_text("DT HORA PESO 2", exact=True).first
    cab.click(); page.wait_for_timeout(3500); cab.click(); page.wait_for_timeout(3500); cab.click(); page.wait_for_timeout(3500)
    c.esperar_relatorio(page)
    partes = [x.strip() for x in fr.inner_text("body").split("\n")]
    print("filtros:", [(k, partes[partes.index(k)+1]) for k in ("FILIAL","CONTRATO","DATA") if k in partes])
    linhas = linhas_visiveis(fr, 14)
    for l in linhas[:25]:
        print(l[0][:14], l[1], l[2], l[3], "|", l[7], l[8], l[9], l[10], l[11], "|", l[13])
    print(len(linhas), "linhas visíveis")
    page.screenshot(path=str(c.DUMP / "sonda_romaneios.png"))
    ctx.close()
