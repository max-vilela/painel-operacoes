"""Roda só as leituras de ativos e investimentos e grava em dump/patrimonio_teste.json (não escreve no bi.js)."""
import json, sys, time
from playwright.sync_api import sync_playwright
import coletor as c
from patrimonio import ativos, investimentos
quais = sys.argv[1:] or ["ativos", "investimentos"]
with sync_playwright() as p:
    ctx = c.abrir(p, headless=True); page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    out = {}
    for q, rel, f in (("ativos", "ativos", ativos), ("investimentos", "invest", investimentos)):
        if q not in quais: continue
        t0 = time.time()
        page.goto(c.url_relatorio(rel), wait_until="domcontentloaded"); c.esperar_relatorio(page)
        out[q] = f(page, c.esperar_relatorio)
        print(f"{q}: {time.time()-t0:.0f}s")
    (c.Path(__file__).parent / "dump" / "patrimonio_teste.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    ctx.close()
