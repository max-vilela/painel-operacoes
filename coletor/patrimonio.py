"""BIs de patrimônio: 'Ativo Fixo' (quantidade de máquinas e ativos) e 'Investimentos' (melhorias da fazenda). Lidos 1 vez por dia.

ATIVOS  (BI 7def702b…, página 'Painel Ativos'): 21 cartões com a quantidade de cada tipo de ativo (tratores, colheitadeiras…).
        O filtro Filial é percorrido para ter também a quantidade por fazenda.
INVESTIMENTOS (BI 05b9baf3…, página 'Investimentos', filtro Data = ano corrente): o painel quer só MELHORIAS DA FAZENDA, não
        máquinas. No cadastro de grupos do Protheus os 5xxx são máquinas/veículos/implementos e os 6xxx são benfeitorias
        (armazéns, alojamentos, cercas e currais, barracões, cantina, edificações...). Percorre os grupos 6xxx no filtro Grupo,
        lê a tabela 'Detalhe dos Investimentos' (filial, patrimônio, data, valor) de cada um e consolida: obras e valor por
        grupo, valor por fazenda e as obras mais recentes.
"""
import re
import time

from extracoes import abrir_pagina, frame_relatorio, ler_tabela, num

GRUPOS_FORA = {"6038", "6039"}          # móveis e informática não entram em 'melhorias da fazenda'
PREFIXO_MELHORIAS = "6"                 # grupos 6xxx = benfeitorias


# ------------------------------------------------------------------ filtros (lista suspensa) por posição

def _abrir_slicer(page, idx):
    fr = frame_relatorio(page)
    fr.locator(".slicer-container").nth(idx).locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click(timeout=10000)
    page.wait_for_timeout(1300)
    return fr


def _fechar_slicer(page):
    page.keyboard.press("Escape")
    page.mouse.click(60, 900)            # área vazia da lista de páginas (à esquerda): nestes BIs, clicar no corpo vira filtro cruzado
    page.wait_for_timeout(1500)


def texto_do_slicer(page, idx):
    return frame_relatorio(page).locator(".slicer-container").nth(idx).inner_text().strip().replace("\n", " ")


def listar_slicer(page, idx):
    """Todos os itens da lista (rola, a lista é virtualizada), sem 'Selecionar tudo'."""
    fr = _abrir_slicer(page, idx)
    itens = []
    for _ in range(40):
        for t in fr.locator(".slicerItemContainer:visible").all_inner_texts():
            t = t.strip()
            if t and t != "Selecionar tudo" and t not in itens:
                itens.append(t)
        r = fr.locator(".slicerItemContainer:visible").first.evaluate("""el => { for (let p = el.parentElement; p; p = p.parentElement)
            if (p.scrollHeight > p.clientHeight + 4) { const a = p.scrollTop; p.scrollTop += 150; return p.scrollTop !== a; } return false; }""")
        page.wait_for_timeout(300)
        if not r:
            break
    _fechar_slicer(page)
    return itens


def _clicar_item(fr, page, rotulo):
    """Com a lista aberta, acha `rotulo` (busca se houver; senão rola do topo, a lista é virtualizada) e clica. False se não achou."""
    busca = fr.locator("input.searchInput:visible, .searchHeader input:visible").first
    if busca.count():
        busca.click(); page.keyboard.press("Control+A"); page.keyboard.press("Backspace")
        page.keyboard.type(rotulo[:12], delay=40); page.wait_for_timeout(1800)
    topo = False
    for _ in range(80):
        item = fr.locator(".slicerItemContainer:visible").filter(has_text=re.compile(r"^\s*" + re.escape(rotulo) + r"\s*$"))
        if item.count():
            item.first.click(); page.wait_for_timeout(1000)
            return True
        if busca.count():
            return False
        passo = "p.scrollTop = 0; return true;" if not topo else "const a = p.scrollTop; p.scrollTop += 330; return p.scrollTop !== a;"
        r = fr.locator(".slicerItemContainer:visible").first.evaluate("""el => { for (let p = el.parentElement; p; p = p.parentElement)
            if (p.scrollHeight > p.clientHeight + 4) { %s } return false; }""" % passo)
        topo = True
        page.wait_for_timeout(180)
        if not r:
            return False
    return False


def trocar(page, idx, desmarcar, marcar):
    """Numa só abertura do filtro (seleção múltipla): desmarca `desmarcar` e marca `marcar` (qualquer um pode ser None).
    Devolve False se `marcar` não foi achado."""
    fr = _abrir_slicer(page, idx)
    ok = True
    if desmarcar:
        _clicar_item(fr, page, desmarcar)
    if marcar:
        ok = _clicar_item(fr, page, marcar)
    _fechar_slicer(page)
    return ok


def alternar(page, idx, rotulo):
    """Marca/desmarca o item `rotulo` (chame de novo para desfazer)."""
    return trocar(page, idx, None, rotulo)


# ------------------------------------------------------------------ ATIVOS

def _contagens(page):
    """Lê os cartões: depois de 'Tipo de Contrato' + valor do filtro vêm pares (número, nome) até a linha '-' do zoom."""
    linhas = [l.strip().replace("\xa0", " ") for l in frame_relatorio(page).inner_text("body").split("\n")]
    try:
        i = linhas.index("Tipo de Contrato") + 2
    except ValueError:
        return {}
    out = {}
    while i + 1 < len(linhas):
        if linhas[i] == "-":
            break
        if re.fullmatch(r"[\d.]+", linhas[i]) and linhas[i + 1] and not re.fullmatch(r"[\d.]+", linhas[i + 1]):
            out[linhas[i + 1]] = int(linhas[i].replace(".", ""))
            i += 2
        else:
            i += 1
    return out


GRUPOS_POR_FAZENDA = {"Tratores": "TRATORES", "Colheitadeiras": "COLHEITADEIRA DE GRAOS", "Pulverizadores": "PULVERIZADORES",
                      "Plantadeiras": "PLANTADEIRAS", "Plataformas": "PLATAFORMAS"}


def _qtd_por_filial(page):
    """Tabela 'Totais por Unidade' da Visão Geral: filial -> Qtde Ativos (filiais sem ativos não aparecem)."""
    linhas = [l.strip().replace(chr(160), " ") for l in frame_relatorio(page).inner_text("body").split(chr(10))]
    out = {}
    for k, l in enumerate(linhas):
        if re.match(r"^(FAZENDA|ESCRITORIO)", l):
            for q in linhas[k + 1:k + 3]:
                if re.fullmatch(r"[\d.]+", q):
                    out[re.sub(r"^FAZENDA ", "", l)] = int(q.replace(".", "")); break
    return out


def ativos(page, esperar):
    """{'tipos': [{nome, qtd}], 'porFilial': [{filial, tipos: {nome: qtd}}]}.
    Totais: cartões do 'Painel Ativos'. Por fazenda: o filtro Filial desse painel não é confiável (mostra só alguns itens),
    então vem da 'Visão Geral' filtrada por grupo (Tratores, Colheitadeiras, Pulverizadores, Plantadeiras, Plataformas)."""
    abrir_pagina(page, "Painel Ativos", esperar)
    total = _contagens(page)
    if not total:
        return None
    out = {"tipos": [{"nome": n, "qtd": q} for n, q in total.items()], "porFilial": []}
    abrir_pagina(page, "Visão Geral", esperar)
    por = {}
    t0 = time.time()
    anterior = None
    for tipo, grupo in GRUPOS_POR_FAZENDA.items():
        try:
            if not trocar(page, 3, anterior, grupo):
                raise RuntimeError(f"ativos: grupo {grupo} não achado no filtro (aba sem foco?)")
            anterior = grupo
            esperar(page)
            q = {}
            for _ in range(4):                        # a tabela às vezes demora a refazer depois do filtro
                page.wait_for_timeout(1500)
                q = _qtd_por_filial(page)
                if q:
                    break
            print(f"    ativos {tipo}: {time.time() - t0:.0f}s acumulados", flush=True)
        except Exception as e:
            raise RuntimeError(f"ativos {grupo}: {str(e)[:100]}")
        if not q:
            print(f"  AVISO ativos: {tipo} sem linhas por fazenda")
        for f, n in q.items():
            por.setdefault(f, {})[tipo] = n
    if anterior:
        trocar(page, 3, anterior, None)
    for f in sorted(por):
        if not f.startswith("ESCRITORIO"):
            out["porFilial"].append({"filial": f, "tipos": por[f]})
    return out


# ------------------------------------------------------------------ INVESTIMENTOS

def _total_reais(page):
    """Valor da linha 'Total' (R$) da tabela de detalhe."""
    t = frame_relatorio(page).inner_text("body").replace(chr(160), " ")
    m = re.findall(r"Total\s+R\$\s*([\d.]+,\d+)", t)          # \s+ já cobre as quebras de linha
    return num(m[-1]) if m else None


def _valor(txt):
    return num(txt.replace("R$", "").strip())


def _linhas_detalhe(page):
    """Linhas de 'Investimentos - Exel' (uma por patrimônio/obra): (filial, patrimônio, valor)."""
    out = []
    for fil, pat, val in ler_tabela(page, 3):
        try:
            out.append({"filial": fil, "patrimonio": pat, "valor": _valor(val)})
        except ValueError:
            pass
    return out


def _dmy(d):
    return d.split("/")[::-1]          # 'dd/mm/aaaa' -> [aaaa, mm, dd] (ordena por data)


def investimentos(page, esperar):
    abrir_pagina(page, "Investimentos - Exel", esperar)
    ano = texto_do_slicer(page, 0)
    total = _total_reais(page)
    grupos = [g for g in listar_slicer(page, 3)
              if g.startswith(PREFIXO_MELHORIAS) and re.match(r"\d{4}", g) and g[:4] not in GRUPOS_FORA]
    print(f"  investimentos: ano {ano} | total {total} | {len(grupos)} grupos de melhorias", flush=True)
    por_grupo, todas = [], []
    t0 = time.time()
    anterior = None
    for g in grupos:
        try:
            if not trocar(page, 3, anterior, g):
                raise RuntimeError(f"investimentos: grupo {g[:4]} não achado no filtro (aba sem foco?)")
            anterior = g
            esperar(page)
            linhas = _linhas_detalhe(page)
        except Exception as e:
            raise RuntimeError(f"investimentos {g[:4]}: {str(e)[:100]}")
        print(f"    invest {g[:4]}: {len(linhas)} obras ({time.time() - t0:.0f}s acumulados)", flush=True)
        if not linhas:
            continue
        nome = re.sub(r"^\d+\s*-\s*(AF\s*-\s*)?", "", g)
        por_grupo.append({"codigo": g[:4], "grupo": nome, "obras": len(linhas), "valor": round(sum(l["valor"] for l in linhas), 2)})
        for l in linhas:
            todas.append(dict(l, grupo=nome))
    if anterior:
        trocar(page, 3, anterior, None)               # volta a 'Todos'
    soma = sum(g["valor"] for g in por_grupo)
    if total and soma > total * 1.001:
        raise RuntimeError(f"investimentos: melhorias somam {soma:,.0f}, mais que o total do BI ({total:,.0f}): filtro acumulou grupos")
    por_filial = {}
    for l in todas:
        d = por_filial.setdefault(l["filial"], {"filial": l["filial"], "obras": 0, "valor": 0.0})
        d["obras"] += 1; d["valor"] += l["valor"]
    maiores = sorted(todas, key=lambda l: -l["valor"])[:8]
    return {
        "ano": ano, "total": total, "melhoriasValor": round(sum(g["valor"] for g in por_grupo), 2),
        "melhoriasObras": sum(g["obras"] for g in por_grupo),
        "grupos": sorted(por_grupo, key=lambda g: -g["valor"]),
        "porFilial": sorted(({"filial": d["filial"], "obras": d["obras"], "valor": round(d["valor"], 2)} for d in por_filial.values()),
                            key=lambda d: -d["valor"]),
        "maiores": maiores,
    }
