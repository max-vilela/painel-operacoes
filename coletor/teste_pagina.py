import sys
from playwright.sync_api import sync_playwright
import coletor as c
nome = sys.argv[2]
with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(c.url_relatorio(sys.argv[1]), wait_until="domcontentloaded")
    c.esperar_relatorio(page)
    for fr in page.frames:
        loc = fr.get_by_text(nome, exact=True)
        if loc.count():
            print("frame", fr.url[:60], loc.count()); loc.first.click(); break
    page.wait_for_timeout(4000)
    c.esperar_relatorio(page)
    (c.DUMP / f"{sys.argv[1]}_{nome.replace(' ','_')}.txt").write_text(c.texto_da_tela(page), encoding="utf-8")
    page.screenshot(path=str(c.DUMP / f"{sys.argv[1]}_{nome.replace(' ','_')}.png"))
    ctx.close()
