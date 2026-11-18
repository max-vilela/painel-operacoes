"""Roda só a escolha automática de safra (plantio e colheita de soja e milho) e imprime o resumo. Não grava nada."""
import time
from playwright.sync_api import sync_playwright
import coletor as c
from safras import colheita_da_cultura, plantio_por_cultura

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True); page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    t0 = time.time()
    page.goto(c.url_relatorio("plantio"), wait_until="domcontentloaded"); c.esperar_relatorio(page)
    pl = plantio_por_cultura(page, c.esperar_relatorio)
    print("PLANTIO:", {k: (v["safra"], v["plantadoHa"], v["planejadoHa"], len(v["fazendas"])) for k, v in pl.items()})
    col = {}
    for cult, rel in (("SOJA", "colheita_soja"), ("MILHO", "colheita_milho")):
        page.goto(c.url_relatorio(rel), wait_until="domcontentloaded"); c.esperar_relatorio(page)
        col[cult.lower()] = colheita_da_cultura(page, c.esperar_relatorio, cult)
    print("COLHEITA:", {k: (v["safra"], v["scHa"], v["areaHa"], len(v["fazendas"])) if v else None for k, v in col.items()})
    print(f"tempo: {time.time() - t0:.0f}s")
    ctx.close()
