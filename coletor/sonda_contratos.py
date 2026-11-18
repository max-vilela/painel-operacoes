"""Mostra o que o BI 'Contrato de Venda - Grãos' diz agora de cada contrato (kg) e o horário da leitura."""
from datetime import datetime
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import abrir_pagina, ler_tabela, num, atualizar_relatorio

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True); page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    page.goto(c.url_relatorio("contrato_graos"), wait_until="domcontentloaded"); c.esperar_relatorio(page)
    for passo in ("sem Atualizar", "com Atualizar"):
        if passo == "com Atualizar":
            atualizar_relatorio(page, c.esperar_relatorio)
        abrir_pagina(page, "Contrato de Venda - Grãos", c.esperar_relatorio)
        linhas = ler_tabela(page, 13)
        print(datetime.now().strftime("%H:%M:%S"), passo, "-", len(linhas), "linhas")
        for st, ctr, _d, _e, cli, _v, qtd, saida, saldo, prod, safra, venc, fil in linhas:
            if ctr in ("000316", "000317", "000318", "000319", "000014", "000015", "000306"):
                print("  ", st, ctr, prod[:12], "qtd", qtd, "saida", saida, "saldo", saldo, "| safra", safra)
    ctx.close()
