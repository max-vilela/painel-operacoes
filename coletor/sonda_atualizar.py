"""Testa o botão 'Atualizar' do portal: abre um relatório, clica, e compara texto/filtros antes e depois."""
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import frame_relatorio

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    page.goto(c.url_relatorio("mortes"), wait_until="domcontentloaded")
    c.esperar_relatorio(page)
    antes = frame_relatorio(page).inner_text("body")
    for rot in ("Atualizar", "Refresh"):
        loc = page.get_by_text(rot, exact=True)
        print(rot, loc.count(), [l.is_visible() for l in loc.all()][:3])
    btn = page.get_by_text("Atualizar", exact=True).first
    btn.click()
    print("clicou; url:", page.url[-30:])
    page.wait_for_timeout(3000)
    c.esperar_relatorio(page)
    depois = frame_relatorio(page).inner_text("body")
    pa = [l for l in antes.split("\n") if l.strip()]
    pd = [l for l in depois.split("\n") if l.strip()]
    print("linhas antes/depois:", len(pa), len(pd), "| iguais:", pa == pd)
    for chave in ("PERIODO", "Total de Mortes"):
        for nome, t in (("antes", pa), ("depois", pd)):
            i = t.index(chave) if chave in t else -1
            print(nome, chave, t[i + 1] if i >= 0 else None)
    ctx.close()
