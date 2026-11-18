"""Lê romaneios + contratos de grãos, atualiza graos e o negociado no ../bi.js sem rodar a coleta inteira."""
import json
from datetime import date
from playwright.sync_api import sync_playwright
import coletor as c
from destino import publicar
from extracoes import (saidas_romaneios, graos_contratos, acompanhar_saidas, negociado_no_estoque, abrir_pagina,
                       atualizar_relatorio)

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True); page = ctx.pages[0] if ctx.pages else ctx.new_page()
    c.garantir_login(page)
    rom = saidas_romaneios(page, c.url_relatorio, c.esperar_relatorio, c.esta_logado)
    page.goto(c.url_relatorio("contrato_graos"), wait_until="domcontentloaded"); c.esperar_relatorio(page)
    atualizar_relatorio(page, c.esperar_relatorio)
    graos = graos_contratos(page, c.esperar_relatorio, rom)
    acompanhar_saidas(graos, date.today())
    ctx.close()
for g in graos:
    print(g["produto"], g["safra"], "contratado", g["contratadoSacas"], "entregue", g["entregueSacas"], "saldo", g["contratadoSacas"] - g["entregueSacas"], g["saida"])
    for k in g["contratos"]:
        print("   ", k["ctr"], k["cliente"][:20], k["fazenda"], k["contratadoSacas"], k["entregueSacas"])
cab, corpo = c.SAIDA.read_text(encoding="utf-8").split("window.DADOS_BI = ", 1)
d = json.loads(corpo.rstrip().rstrip(";"))
d["graos"] = graos
negociado_no_estoque(d["visao"], getattr(graos_contratos, "saldo_por_safra", {}))
c.SAIDA.write_text(cab + "window.DADOS_BI = " + json.dumps(d, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
publicar(c.SAIDA)
