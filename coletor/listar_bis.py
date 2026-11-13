"""Lista os relatórios do portal (nome + id) e salva em dump/lista_bis.json. Uso: python listar_bis.py"""
import json
import re
from playwright.sync_api import sync_playwright
import coletor as c

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(c.PORTAL, wait_until="domcontentloaded")
    page.wait_for_timeout(8000)
    if not c.esta_logado(page):
        raise SystemExit("Sem login. Rode: python coletor.py login")
    c.DUMP.mkdir(exist_ok=True)
    (c.DUMP / "portal_inicio.txt").write_text(c.texto_da_tela(page), encoding="utf-8")
    page.screenshot(path=str(c.DUMP / "portal_inicio.png"), full_page=True)
    links = page.eval_on_selector_all("a[href]", "els => els.map(e => [e.innerText.trim(), e.getAttribute('href')])")
    rel = {}
    for txt, href in links:
        m = re.search(r"/(Report|Dashboard)/([0-9a-f-]{36})", href or "", re.I)
        if m:
            rel.setdefault(m.group(2), {"tipo": m.group(1), "nome": txt, "href": href})
    (c.DUMP / "lista_bis.json").write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(rel), "relatórios")
    for k, v in rel.items():
        print(v["tipo"], k, "|", v["nome"].replace("\n", " ")[:80])
    ctx.close()
