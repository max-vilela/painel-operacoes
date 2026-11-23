"""Orquestra a coleta: uma TAREFA por fonte, com tempo medido, nova tentativa, frequência própria e leitura em paralelo.

- Cada tarefa abre o próprio relatório (goto + login + espera + Atualizar), lê e devolve um pedaço do bi.js.
- Tempos: o log mostra quanto cada fonte levou e quantas tentativas; `tempos` também vai no bi.js.
- Nova tentativa: se a leitura falha ou vem incompleta (critério `_ok`), tenta mais uma vez antes de desistir.
- Frequência: cada fonte tem um intervalo mínimo (INTERVALO_H). Fonte que não venceu é pulada e mantém o valor e a hora
  da última leitura (sem marcar falha). `--tudo` força todas.
- Paralelo: 1 navegador (mesma sessão do portal), várias ABAS. A 1ª aba roda na thread principal; as outras threads se
  conectam ao mesmo Chrome pela porta de depuração (CDP). `--paralelo 1` volta ao modo sequencial.
"""
import queue
import threading
import time
from datetime import date, datetime

PORTA_CDP = 9333
# Horas mínimas entre leituras de cada fonte (0 = toda coleta). A coleta roda de 2 em 2 h.
INTERVALO_H = {"bovinos": 0, "graos": 0, "estoque": 0, "mortes": 4, "compras": 4, "plantio": 8, "colheita": 8, "rh": 8}
TOLERANCIA_MIN = 20          # a coleta "atrasa" alguns minutos: 3h50 de idade já conta como 4 h
ORDEM = ["compras", "rh", "graos", "bovinos", "plantio", "colheita", "estoque", "mortes"]   # as mais demoradas primeiro
TENTATIVAS = 2


class SemLogin(Exception):
    pass


def _abrir(page, ctx, nome):
    """Abre o relatório `nome`, confere o login, espera carregar e clica em Atualizar."""
    from extracoes import atualizar_relatorio
    page.goto(ctx["url"](nome), wait_until="domcontentloaded")
    if not ctx["logado"](page):
        raise SemLogin("Sem login: rode python coletor.py login")
    ctx["esperar"](page)
    atualizar_relatorio(page, ctx["esperar"])


# ------------------------------------------------------------------ tarefas (cada uma devolve um pedaço do resultado)

def t_bovinos(page, ctx):
    import extracoes as x
    _abrir(page, ctx, "venda_bovinos")
    cron, mes = x.bovinos_cronograma(page, ctx["esperar"], date.today())
    abat = x.bovinos_abatidos_mes(page, ctx["esperar"], date.today())
    mes["abatidos"], mes["anoAbatidos"] = abat["mes"][0], abat["ano"][0]
    print("  bovinos:", len(cron), "embarques | mes:", mes)
    return {"bovinos": {"cronograma": cron, "mes": mes}}


def t_graos(page, ctx):
    import extracoes as x
    rom = x.saidas_romaneios(page, ctx["url"], ctx["esperar"], ctx["logado"])
    _abrir(page, ctx, "contrato_graos")
    graos = x.graos_contratos(page, ctx["esperar"], rom)
    x.acompanhar_saidas(graos, date.today())
    print("  graos:", [(g["produto"], g["safra"], g["contratadoSacas"], g["entregueSacas"], len(g["contratos"])) for g in graos])
    return {"graos": graos, "_saldo_por_safra": dict(getattr(x.graos_contratos, "saldo_por_safra", {}))}


def t_estoque(page, ctx):
    import extracoes as x
    _abrir(page, ctx, "ger_estoque")
    return {"visao": x.ger_estoque(page, ctx["esperar"])}


def t_rh(page, ctx):
    import extracoes as x
    from datetime import date as _d
    _abrir(page, ctx, "rh")
    rh = x.rh_quadro(page)
    rh["exames"] = x.rh_exames(page)
    rh.update(x.rh_por_fazenda(page, ctx["esperar"]))
    try:
        f = x.ferias_cg(page, ctx["esperar"], _d.today())
        if f:
            rh["retornosCG"], rh["entramCG"] = f["retornos"], f["entram"]
    except Exception as e:
        print("  AVISO férias CG:", e)
    return {"visao": {"rh": rh}}


def t_plantio(page, ctx):
    from safras import plantio_por_cultura
    _abrir(page, ctx, "plantio")
    return {"visao": {"plantio": plantio_por_cultura(page, ctx["esperar"])}}


def t_colheita(page, ctx):
    from safras import colheita_da_cultura
    out = {}
    for cult, rel in (("soja", "colheita_soja"), ("milho", "colheita_milho")):
        try:
            _abrir(page, ctx, rel)
            out[cult] = colheita_da_cultura(page, ctx["esperar"], cult.upper())
        except SemLogin:
            raise
        except Exception as e:
            print(f"  ERRO colheita {cult}: {str(e)[:120]}")
    return {"visao": {"colheita": out}}


def t_mortes(page, ctx):
    import extracoes as x
    _abrir(page, ctx, "mortes")
    x.abrir_pagina(page, "Mortes", ctx["esperar"])
    return {"visao": {"mortes": x.mortes(page, ctx["esperar"])}}


def t_compras(page, ctx):
    from compras import compras
    _abrir(page, ctx, "compras")
    return {"visao": {"compras": compras(page, ctx["esperar"])}}


TAREFAS = {"bovinos": t_bovinos, "graos": t_graos, "estoque": t_estoque, "rh": t_rh, "plantio": t_plantio,
           "colheita": t_colheita, "mortes": t_mortes, "compras": t_compras}


# ------------------------------------------------------------------ execução

def _juntar(destino, parte):
    for k, v in parte.items():
        if isinstance(v, dict) and isinstance(destino.get(k), dict):
            _juntar(destino[k], v)
        else:
            destino[k] = v


def vencidas(anterior, forcar, agora=None):
    """Fontes que devem ser lidas nesta coleta, pelo intervalo de cada uma e a hora da última leitura boa."""
    agora = agora or datetime.now().astimezone()
    fontes_ant = (anterior or {}).get("fontes") or {}
    out = []
    for nome in ORDEM:
        h = INTERVALO_H.get(nome, 0)
        ult = fontes_ant.get(nome)
        if forcar or h == 0 or not ult:
            out.append(nome); continue
        try:
            idade_min = (agora - datetime.fromisoformat(ult)).total_seconds() / 60
        except ValueError:
            out.append(nome); continue
        if idade_min >= h * 60 - TOLERANCIA_MIN:
            out.append(nome)
    return out


def _rodar(nome, page, ctx, resultado, tempos, trava):
    _ok = ctx["ok"]
    t0 = time.time()
    tent = 0
    for tent in range(1, TENTATIVAS + 1):
        try:
            parte = TAREFAS[nome](page, ctx)
            teste = {}
            _juntar(teste, parte)
            if _ok(teste, nome):
                with trava:
                    _juntar(resultado, parte)
                break
            print(f"  AVISO {nome}: leitura incompleta (tentativa {tent}/{TENTATIVAS})")
        except SemLogin:
            raise
        except Exception as e:
            print(f"  ERRO {nome} (tentativa {tent}/{TENTATIVAS}): {str(e)[:160]}")
        time.sleep(5)
    else:
        print(f"  {nome}: desisti depois de {TENTATIVAS} tentativas (fica o último valor bom)")
    tempos[nome] = {"s": round(time.time() - t0), "tentativas": tent}
    print(f"  [tempo] {nome}: {tempos[nome]['s']} s ({tent} tentativa{'s' if tent > 1 else ''})")


def _worker(fila, ctx, resultado, tempos, trava, erros, principal_page=None):
    """Tira tarefas da fila e roda cada uma numa aba. A 1ª aba usa a página já aberta; as demais conectam por CDP."""
    pw = None
    page = principal_page
    try:
        if page is None:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{PORTA_CDP}")
            page = browser.contexts[0].new_page()
        while True:
            try:
                nome = fila.get_nowait()
            except queue.Empty:
                return
            _rodar(nome, page, ctx, resultado, tempos, trava)
    except SemLogin as e:
        erros.append(str(e))
    except Exception as e:
        erros.append(f"worker: {str(e)[:160]}")
    finally:
        if page is not None and principal_page is None:
            try:
                page.close()
            except Exception:
                pass
        if pw is not None:
            try:
                pw.stop()
            except Exception:
                pass


def coletar(page, ctx, nomes, paralelo=3):
    """Roda as tarefas `nomes`. Devolve (resultado, tempos, erros)."""
    resultado, tempos, erros, trava = {}, {}, [], threading.Lock()
    fila = queue.Queue()
    for n in nomes:
        fila.put(n)
    t0 = time.time()
    threads = []
    for _ in range(max(0, min(paralelo, len(nomes)) - 1)):
        t = threading.Thread(target=_worker, args=(fila, ctx, resultado, tempos, trava, erros), daemon=True)
        t.start(); threads.append(t)
        time.sleep(1.5)
    _worker(fila, ctx, resultado, tempos, trava, erros, principal_page=page)
    for t in threads:
        t.join(timeout=1500)
    tempos["_total_s"] = round(time.time() - t0)
    print(f"  [tempo] coleta toda: {tempos['_total_s']} s com {max(1, min(paralelo, len(nomes)))} aba(s)")
    return resultado, tempos, erros
