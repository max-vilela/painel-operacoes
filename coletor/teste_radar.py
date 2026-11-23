"""Abre o painel por file:// num Chrome headless, vai à aba Compras e volta, e confere se o contorno das fazendas (Leaflet) e o Windy acompanham o tamanho do quadro do radar. Tira prints em dump/."""
from pathlib import Path
from playwright.sync_api import sync_playwright
RAIZ = Path(__file__).resolve().parent.parent
OUT = Path(__file__).parent / "dump"
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.goto((RAIZ / "index.html").as_uri()); pg.wait_for_timeout(6000)
    def medir(rot):
        r = pg.evaluate("""() => { const m = document.querySelector('.map').getBoundingClientRect(), s = mapa.getSize();
            return {app: document.querySelector('.app').className, map: Math.round(m.width)+'x'+Math.round(m.height), leaflet: s.x+'x'+s.y, zoom: mapa.getZoom(), windy: ($('radar').src.match(/zoom=\d+/)||[''])[0]} }""")
        print(rot, r)
    pg.evaluate("clearInterval(relogioCarrossel); irPara(slides.findIndex(s=>s.id==='sBov')); clearInterval(relogioCarrossel)"); pg.wait_for_timeout(3000)
    medir("bovinos "); pg.screenshot(path=str(OUT / "radar_normal.png"))
    pg.evaluate("irPara(slides.findIndex(s=>s.id==='sCompras')); clearInterval(relogioCarrossel)"); pg.wait_for_timeout(4500)
    medir("compras "); pg.screenshot(path=str(OUT / "radar_largo.png"))
    pg.evaluate("irPara(slides.findIndex(s=>s.id==='sBov')); clearInterval(relogioCarrossel)"); pg.wait_for_timeout(4500)
    medir("voltou  "); pg.screenshot(path=str(OUT / "radar_volta.png"))
    b.close()
