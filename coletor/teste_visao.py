"""Roda só a faixa de indicadores (estoques, RH, plantio) e atualiza a chave 'visao' do ../bi.js existente."""
import json
from playwright.sync_api import sync_playwright
import coletor as c
from destino import publicar
from extracoes import visao_geral

with sync_playwright() as p:
    ctx = c.abrir(p, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    v = visao_geral(page, c.url_relatorio, c.esperar_relatorio, c.esta_logado)
    ctx.close()
print(json.dumps(v, ensure_ascii=False, indent=1))
txt = c.SAIDA.read_text(encoding="utf-8")
cab, corpo = txt.split("window.DADOS_BI = ", 1)
dados = json.loads(corpo.rstrip().rstrip(";"))
dados["visao"] = v
c.SAIDA.write_text(cab + "window.DADOS_BI = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
publicar(c.SAIDA)
