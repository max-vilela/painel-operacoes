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
import re
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


def garantir_login(page, timeout_s=90):
    """Se o portal estiver na tela de login, entra sozinho pela conta Microsoft que o perfil já conhece:
    'Autenticação Microsoft' -> escolhe a conta marcada como 'Entrou' -> 'Manter conectado? Sim'.
    Não digita senha: se a Microsoft pedir senha/MFA, desiste e devolve False (aí: python coletor.py login).
    O portal só aceita 1 sessão por conta: relogar aqui derruba a sessão de quem estiver usando a mesma conta."""
    page.goto(PORTAL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    if esta_logado(page) and "login.microsoftonline" not in page.url:
        return True
    print("sessão caiu; entrando de novo pela conta Microsoft...")
    try:
        page.get_by_text("Autenticação Microsoft").first.click()
    except Exception:
        return False
    fim = time.time() + timeout_s
    while time.time() < fim:
        page.wait_for_timeout(2000)
        url = page.url.lower()
        if "bi.livioeoutro.com.br" in url and "/identity/login" not in url:
            print("login refeito")
            return True
        if "login.microsoftonline" in url or "login.live" in url:
            if page.locator("input[type=password]:visible").count():
                print("a Microsoft pediu senha: rode python coletor.py login")
                return False
            for alvo in (page.get_by_text("Entrou").first,                       # conta já conectada
                         page.locator("#idSIButton9:visible").first,              # 'Sim' em 'Manter conectado?'
                         page.get_by_role("button", name=re.compile(r"^(Sim|Yes)$")).first):
                try:
                    if alvo.count() and alvo.is_visible():
                        alvo.click(); break
                except Exception:
                    pass
    return False


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


def _ok(dados, fonte):
    """A parte `fonte` foi lida de verdade nesta coleta? (critério mínimo: o número principal veio)"""
    v = dados.get("visao") or {}
    if fonte == "bovinos":
        b = dados.get("bovinos") or {}
        return bool(b.get("mes")) and b.get("cronograma") is not None
    if fonte == "graos":
        return bool(dados.get("graos"))
    if fonte == "estoque":
        g = v.get("estoqueGraos") or {}
        return bool(v.get("rebanho")) and bool(g.get("soja")) and bool(g.get("milho")) and bool((v.get("combustivel") or {}).get("diesel"))
    if fonte == "rh":
        return (v.get("rh") or {}).get("ativos") is not None
    if fonte == "plantio":
        return bool(v.get("plantio"))
    if fonte == "colheita":
        c = v.get("colheita") or {}
        return bool(c.get("soja")) and bool(c.get("milho"))
    if fonte == "mortes":
        return (v.get("mortes") or {}).get("total") is not None
    return True


FONTES = ["bovinos", "graos", "estoque", "rh", "plantio", "colheita", "mortes"]
CHAVES_VISAO = {"estoque": ["rebanho", "estoqueGraos", "combustivel"], "rh": ["rh"], "plantio": ["plantio"],
                "colheita": ["colheita"], "mortes": ["mortes"]}


def mesclar_com_anterior(dados, agora):
    """Grava em dados['fontes'] a hora em que CADA parte foi lida e, se uma parte falhou, mantém o último valor bom dela
    (com a hora antiga) e a lista em dados['falhas']. Assim uma leitura que falha não apaga o número do painel,
    e o painel mostra de quando o dado é e que a leitura falhou."""
    try:
        txt = SAIDA.read_text(encoding="utf-8")
        ant = json.loads(txt.split("window.DADOS_BI = ", 1)[1].rstrip().rstrip(";"))
    except Exception:
        ant = {}
    fontes_ant = ant.get("fontes") or {}
    base = ant.get("atualizadoEm")
    fontes, falhas = {}, []
    dados.setdefault("visao", {})
    for f in FONTES:
        if _ok(dados, f):
            fontes[f] = agora
            continue
        falhas.append(f)
        fontes[f] = fontes_ant.get(f) or base or None
        if f == "bovinos" and ant.get("bovinos"):
            dados["bovinos"] = ant["bovinos"]
        elif f == "graos" and ant.get("graos"):
            dados["graos"] = ant["graos"]
        elif f == "estoque":
            v, pv = dados["visao"], ant.get("visao") or {}
            if not v.get("rebanho") and pv.get("rebanho"):
                v["rebanho"] = pv["rebanho"]
            for prod in ("soja", "milho"):                       # só o produto que faltou volta do anterior
                if not (v.get("estoqueGraos") or {}).get(prod) and (pv.get("estoqueGraos") or {}).get(prod):
                    v.setdefault("estoqueGraos", {})[prod] = pv["estoqueGraos"][prod]
            comb = v.setdefault("combustivel", {})
            for k in ("diesel", "gasolina", "etanol"):
                if not comb.get(k) and (pv.get("combustivel") or {}).get(k):
                    comb[k] = pv["combustivel"][k]
        elif f == "colheita":
            c, pc = dados["visao"].setdefault("colheita", {}), (ant.get("visao") or {}).get("colheita") or {}
            for prod in ("soja", "milho"):                       # só a cultura que faltou volta do anterior
                if not c.get(prod) and pc.get(prod):
                    c[prod] = pc[prod]
        else:
            for k in CHAVES_VISAO.get(f, []):                    # rh, plantio, mortes: a parte inteira volta do anterior
                if k in (ant.get("visao") or {}):
                    dados["visao"][k] = ant["visao"][k]
    dados["fontes"], dados["falhas"] = fontes, falhas
    if falhas:
        print("  AVISO: leitura falhou, mantido o último valor de:", ", ".join(falhas))


def cmd_coletar(_):
    from extracoes import coletar_tudo  # escrito depois do dump de cada página

    with sync_playwright() as p:
        ctx = abrir(p, headless=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        if not garantir_login(page):
            sys.exit("Sem login e não deu para entrar sozinho. Rode: python coletor.py login")
        dados = coletar_tudo(page, url_relatorio, esperar_relatorio, esta_logado)
        ctx.close()
    dados["atualizadoEm"] = datetime.now().astimezone().isoformat(timespec="seconds")
    mesclar_com_anterior(dados, dados["atualizadoEm"])
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
    if args.cmd == "coletar":
        registrar_em_arquivo()
    args.f(args)


class _Tee:
    """Escreve no console (se houver) e no arquivo de log ao mesmo tempo."""
    def __init__(self, *saidas):
        self.saidas = [s for s in saidas if s]
    def write(self, txt):
        for s in self.saidas:
            try:
                s.write(txt); s.flush()
            except Exception:
                pass
    def flush(self):
        for s in self.saidas:
            try:
                s.flush()
            except Exception:
                pass


def registrar_em_arquivo():
    """A tarefa agendada roda sem ninguém olhando: guarda a saída (e erros) em coletor/ultima_coleta.log."""
    log = open(AQUI / "ultima_coleta.log", "w", encoding="utf-8")
    log.write(f"início {datetime.now():%d/%m/%Y %H:%M:%S}\n")
    sys.stdout = _Tee(sys.__stdout__, log)
    sys.stderr = _Tee(sys.__stderr__, log)


if __name__ == "__main__":
    main()
