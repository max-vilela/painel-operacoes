"""Roda só a leitura de compras e grava o resultado em dump/compras_teste.json (não escreve no bi.js)."""
import json, time
from playwright.sync_api import sync_playwright
import coletor as c
c.RELATORIOS["compras"] = "dbe070ab-7322-4ded-ae7e-1c647798e5a9"
from compras import compras, _linhas_matriz
with sync_playwright() as p:
    ctx = c.abrir(p, headless=True); page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    t0 = time.time()
    page.goto(c.url_relatorio("compras"), wait_until="domcontentloaded"); c.esperar_relatorio(page)
    r = compras(page, c.esperar_relatorio)
    print(f"{len(r)} pedidos com saldo em {time.time()-t0:.0f}s")
    (c.Path(__file__).parent / "dump" / "compras_teste.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(Counter(x["categoria"] for x in r))
    ctx.close()
