"""Abre o painel DIRETO DA PASTA (file://), num Chrome real e sem servidor, como a TV faz. Mostra erros e confere
que CSS, JS, dados e carrossel funcionam. Não acessa o portal. Uso: python teste_file.py [pasta]"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
url = (pasta / "index.html").resolve().as_uri()
erros = []
with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True)
    pag = nav.new_page(viewport={"width": 1920, "height": 1080})
    pag.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    pag.on("pageerror", lambda e: erros.append("JS: " + str(e)))
    pag.on("requestfailed", lambda r: erros.append("falhou: " + r.url[:90]))
    pag.goto(url)
    pag.wait_for_timeout(9000)
    r = pag.evaluate("""() => ({
        css: getComputedStyle(document.body).backgroundColor,
        fonte: getComputedStyle(document.querySelector('.panel h2')).fontSize,
        abas: document.querySelectorAll('.slide').length,
        bolinhas: document.querySelectorAll('#dots i').length,
        titulo: document.getElementById('carTitulo').textContent,
        selo: document.getElementById('idade').textContent,
        bi: !!window.DADOS_BI, dados: !!window.DADOS, mercado: !!window.DADOS_MERCADO,
        marquee: document.getElementById('marq').children.length,
        embarcado: document.getElementById('bEmb').textContent,
        rodape: document.getElementById('upd').textContent,
        chuvaCards: document.querySelectorAll('#chuva .farm').length,
        mapa: !!document.querySelector('#mapa .leaflet-pane'),
    })""")
    for k, v in r.items():
        print(f"{k:11s}", v)
    pag.screenshot(path=str(pasta / "coletor" / "dump" / "teste_file.png"))
    nav.close()
print("URL:", url)
print("ERROS:", erros if erros else "nenhum")
