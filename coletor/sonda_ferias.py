"""Filtra Gestão de Ferias por Filial = ESC. C. GRANDE e despeja os tokens de cada linha (sem nomes completos no stdout)."""
import re
from playwright.sync_api import sync_playwright
import coletor as c
from extracoes import abrir_pagina, frame_relatorio, filtrar_dropdown, ler_tabela

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True); page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    page.goto(c.url_relatorio("rh"), wait_until="domcontentloaded"); c.esperar_relatorio(page)
    abrir_pagina(page, "Gestão de Ferias", c.esperar_relatorio)
    print("filtrou:", filtrar_dropdown(page, "FILIAL(", "11 - ESC. C. GRANDE")); c.esperar_relatorio(page)
    fr = frame_relatorio(page)
    partes = [x.strip() for x in fr.inner_text("body").split("\n")]
    blocos, cur = [], None
    for x in partes:
        if x == "Selecionar Linha":
            cur = []; blocos.append(cur)
        elif cur is not None and x != "Formatação Condicional Adicional":
            cur.append(x)
    print(len(blocos), "linhas visíveis")
    for b in blocos[:40]:
        nome = next((t for t in b[1:] if re.fullmatch(r"[A-ZÀ-Ü ]{6,}", t) and not t.startswith(("PROGRAM", "EM F"))), "?")
        ab = nome.split()[0] + " " + (nome.split()[-1][0] + "." if len(nome.split()) > 1 else "")
        print(ab, "|", [t if not t == nome else "<nome>" for t in b][1:])
    page.screenshot(path=str(c.DUMP / "sonda_ferias.png"))
    ctx.close()
