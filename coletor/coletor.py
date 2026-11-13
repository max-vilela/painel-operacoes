"""Coletor do painel de operações.

Abre os BIs no portal (bi.livioeoutro.com.br) com um perfil PRÓPRIO do Chrome e lê os números
que o relatório mostra na tela. Não usa token do Power BI nem API: é o mesmo que uma pessoa faria.

Comandos:
  python coletor.py login                 abre uma janela para você entrar no portal (1 vez)
  python coletor.py dump RELATORIO [PAGINA]   salva o texto/print da tela (para desenvolver extrações)
  python coletor.py coletar               lê os BIs e grava ../bi.js (o painel lê esse arquivo)

O perfil fica em coletor/perfil (cookies de login): não copie, não versione, não compartilhe.
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from destino import publicar

AQUI = Path(__file__).resolve().parent
PERFIL = AQUI / "perfil"
DUMP = AQUI / "dump"
SAIDA = AQUI.parent / "bi.js"

PORTAL = "https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2"
RELATORIOS = {
    "venda_bovinos": "41557c22-bead-4848-82f6-67fdf78d333a",
    "contrato_graos": "8c2c1c01-310b-4c25-a4cb-32ce4fb42934",
    "romaneios": "141523b6-a1d2-4c0d-8127-9b7716fd629e",
    "dlavro": "26c2786b-90cb-4061-a866-01bb36aa12f1",
    "estoque": "99cf7121-5663-4482-805c-43c80972867a",      # PowerBI Celulares (DESATUALIZADO, não usar)
    "ger_estoque": "fccc6dc1-8135-4f09-9d06-6fa8ee1264c2",  # Gerenciamento do Estoque: saldo atual (fonte certa)
    "rh": "af53f0dc-1a29-4452-9366-9907927b9be9",           # Painel de Recursos Humanos - Fazendas
    "plantio": "55cf318b-874c-4c2c-8ed8-a4b901ccd4f9",      # Indicadores de Plantio
    "colheita_soja": "e54486e0-b7ff-4bba-a0a8-c96f3ef61f94",  # Indicadores Colheita Soja
    "colheita_milho": "a48e797b-fd6b-434f-9fa8-c96bd6e3efcc", # Indicadores Colheita Milho
    "mortes": "d61b96ea-a906-4141-9b72-ceccdae57dfa",       # Mortes (página inicial, PERIODO = ano)
}


def abrir(p, headless):
    """Chrome instalado na máquina, com perfil persistente (mantém o login entre execuções)."""
    PERFIL.mkdir(parents=True, exist_ok=True)
    return p.chromium.launch_persistent_context(
        str(PERFIL), channel="chrome", headless=headless,
        viewport={"width": 1920, "height": 1080}, locale="pt-BR",
    )


def url_relatorio(nome, pagina=None):
    url = f"{PORTAL}/Report/{RELATORIOS[nome]}"
    return url + (f"?page={pagina}" if pagina else "")


def esta_logado(page):
    return "/identity/login" not in page.url.lower()


def esperar_relatorio(page, timeout_s=120):
    """Espera o Power BI terminar de carregar: texto da tela estável e sem 'Carregando'."""
    fim = time.time() + timeout_s
    ultimo, estavel = "", 0
    while time.time() < fim:
        texto = texto_da_tela(page)
        if "Carregando" not in texto and len(texto) > 200 and texto == ultimo:
            estavel += 1
            if estavel >= 3:
                return True
        else:
            estavel = 0
        ultimo = texto
        page.wait_for_timeout(1500)
    return False


def texto_da_tela(page):
    """Texto de todos os frames (o relatório do Power BI vive num iframe)."""
    partes = []
    for fr in page.frames:
        try:
            partes.append(fr.inner_text("body", timeout=2000))
        except Exception:
            pass
    return "\n".join(partes)


# ---------------------------------------------------------------- comandos

def cmd_login(_):
    with sync_playwright() as p:
        ctx = abrir(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(PORTAL)
        print("Entre no portal na janela que abriu. Quando terminar, FECHE a janela.")
        try:
            while ctx.pages:
                time.sleep(1)
        except Exception:
            pass
    print("Perfil salvo em", PERFIL)


def cmd_dump(args):
    DUMP.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = abrir(p, headless=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url_relatorio(args.relatorio, args.pagina), wait_until="domcontentloaded")
        if not esta_logado(page):
            sys.exit("Sem login. Rode: python coletor.py login")
        ok = esperar_relatorio(page)
        base = DUMP / f"{args.relatorio}_{args.pagina or 'inicial'}"
        base.with_suffix(".txt").write_text(texto_da_tela(page), encoding="utf-8")
        page.screenshot(path=str(base.with_suffix(".png")))
        print("carregou" if ok else "TIMEOUT (salvei o que havia)", "->", base)
        ctx.close()


def cmd_coletar(_):
    from extracoes import coletar_tudo  # escrito depois do dump de cada página

    with sync_playwright() as p:
        ctx = abrir(p, headless=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        dados = coletar_tudo(page, url_relatorio, esperar_relatorio, esta_logado)
        ctx.close()
    dados["atualizadoEm"] = datetime.now().astimezone().isoformat(timespec="seconds")
    SAIDA.write_text(
        "// GERADO por coletor/coletor.py. Não editar à mão.\n"
        "window.DADOS_BI = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8",
    )
    print("gravado", SAIDA)
    publicar(SAIDA)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login").set_defaults(f=cmd_login)
    d = sub.add_parser("dump")
    d.add_argument("relatorio", choices=RELATORIOS)
    d.add_argument("pagina", nargs="?")
    d.set_defaults(f=cmd_dump)
    sub.add_parser("coletar").set_defaults(f=cmd_coletar)
    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
