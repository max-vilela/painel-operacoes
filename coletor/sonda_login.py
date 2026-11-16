"""Abre o portal SEM janela e acompanha por 60 s para onde a tela de login leva (só leitura, imprime URLs e botões)."""
import re
from playwright.sync_api import sync_playwright
import coletor as c

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(c.PORTAL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    if not c.esta_logado(page):
        page.get_by_text("Autenticação Microsoft").first.click()
        print("cliquei em Autenticação Microsoft")
    ultimo = None
    for s in range(30):
        if page.url != ultimo:
            ultimo = page.url
            print(f"{s*2:>3}s", re.sub(r"\?.*", "?…", page.url)[:110])
        page.wait_for_timeout(2000)
    print("logado" if c.esta_logado(page) else "SEM LOGIN")
    botoes = page.eval_on_selector_all("a, button, input[type=submit], [role=button]",
                                       "els => els.map(e => (e.innerText || e.value || e.getAttribute('aria-label') || '').trim()).filter(Boolean)")
    print("botões:", botoes[:25])
    page.screenshot(path=str(c.DUMP / "sonda_login.png"))
    ctx.close()
