"""Pedidos de compras com saldo a entregar, dos produtos que o painel acompanha.

Fonte: BI 'Compras' (dbe070ab…), página 'Pedido de Compras x Documento de Entrada'. A matriz SALDO tem 3 níveis:
    Filial  ->  'PEDIDO - FORNECEDOR - cód. fornecedor - emissão - R$'  ->  'cód. produto - PRODUTO'
com QUANTIDADE | TOTAL (R$) | QTDE ENTREGUE | TRANSITORIO | QTDE SALDO | VALOR SALDO. Só as quantidades vão para o painel.
O coletor filtra os GRUPOS DE PRODUTO que contêm os itens, abre a matriz inteira (Expandir > Todos), rola e lê as
linhas (virtualizadas), e guarda os pedidos que ainda têm saldo.
"""
import re
from pathlib import Path

from extracoes import abrir_pagina, frame_relatorio, num, _marcado

PAGINA = "Pedido de Compras x Documento de Entrada"
SLICER_GRUPO = 9            # ordem dos filtros na página: ... PRODUTO(7) FORNECEDOR(8) GRUPO DE PRODUTO(9) ...
GRUPOS = ["0101 - FERTILIZANTES", "0201 - ADJUVANTES", "0301 - SEMENTE DE SOJA", "0302 - SEMENTE DE MILHO",
          "0303 - SEMENTE DE PASTAGEM", "0305 - SEMENTE DE FEIJAO", "0306 - SEMENTE DE SORGO",
          "0401 - CORRETIVOS DE SOLO", "0602 - COMPONENTES NUTRICAO ANIMAL", "0606 - FORMULADOS NUTRICAO ANIMAL"]

# categoria -> (função que reconhece o produto). A ordem importa: a primeira que casar vale.
CATEGORIAS = [
    ("Gesso p/ nutrição animal", lambda p, g: "GESSO AGRICOLA CONF" in p),
    ("Gesso agrícola",           lambda p, g: "GESSO AGRICOLA" in p),
    ("Calcário dolomítico",      lambda p, g: "CALCARIO" in p and "DOLOMIT" in p),
    ("Caroço de algodão",        lambda p, g: "CAROCO DE ALGODAO" in p),
    ("Casquinha de algodão",     lambda p, g: "CASQUINHA DE ALGODAO" in p),
    ("DDG ouro",                 lambda p, g: p.startswith("DDG") and "OURO" in p),
    ("DDG úmido",                lambda p, g: p.startswith("DDG") and "UMIDO" in p),
    ("DDG ALD",                  lambda p, g: p.startswith("DDG") and "ALD" in p),
    ("Farelo de algodão",        lambda p, g: "FARELO DE ALGODAO" in p),
    ("Farelo de soja",           lambda p, g: "FARELO DE SOJA" in p),
    ("Núcleo mineral",           lambda p, g: "NUCLEO" in p and "MINERAL" in p),
    ("Óleo vegetal (adjuvante)", lambda p, g: g.startswith("0201") and ("OLEO VEGETAL" in p or "ADJUVANTE" in p)),
    ("Sementes",                 lambda p, g: p.startswith("SEMENTE") and g[:2] == "03"),
    ("Fertilizantes",            lambda p, g: g.startswith("0101")),
]


def categoria_do(produto, grupo=""):
    p = produto.upper()
    for nome, casa in CATEGORIAS:
        if casa(p, grupo):
            return nome
    return None


# ------------------------------------------------------------------ filtro de grupos

def _abrir_slicer(page, idx):
    fr = frame_relatorio(page)
    fr.locator(".slicer-container").nth(idx).locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click(timeout=10000)
    page.wait_for_timeout(1500)
    return fr


def selecionar_grupos(page, rotulos):
    """Marca SÓ estes grupos no filtro GRUPO DE PRODUTO (seleção múltipla). Devolve os que não foram achados."""
    fr = _abrir_slicer(page, SLICER_GRUPO)
    faltou = []
    for rot in rotulos:
        busca = fr.locator("input.searchInput:visible, .searchHeader input:visible").first
        busca.click(); page.keyboard.press("Control+A"); page.keyboard.press("Backspace")
        page.keyboard.type(rot[:4], delay=40); page.wait_for_timeout(1800)
        item = fr.locator(".slicerItemContainer:visible").filter(has_text=re.compile(r"^\s*" + re.escape(rot) + r"\s*$")).first
        if not item.count():
            faltou.append(rot); continue
        if not _marcado(item):
            item.click(); page.wait_for_timeout(1500)
    page.keyboard.press("Escape"); page.mouse.click(1590, 170); page.wait_for_timeout(3500)
    return faltou


# ------------------------------------------------------------------ leitura da matriz

def _expandir_tudo(page):
    fr = frame_relatorio(page)
    fr.locator(".pivotTable").first.locator("[role=row]").nth(1).locator("[role=rowheader], .pivotTableCellNoWrap").first.click(button="right")
    page.wait_for_timeout(1200)
    fr.get_by_text("Expandir", exact=True).first.hover(); page.wait_for_timeout(1200)
    fr.get_by_text("Todos", exact=True).last.click(); page.wait_for_timeout(4000)


def _linhas_matriz(page, max_passos=400):
    """Rola a matriz do topo ao fim e devolve [(rótulo, [6 números em texto])] na ordem."""
    fr = frame_relatorio(page)
    pv = fr.locator(".pivotTable").first
    cx = pv.bounding_box()
    page.mouse.move(cx["x"] + cx["width"] / 2, cx["y"] + cx["height"] / 2)
    for _ in range(8):
        page.mouse.wheel(0, -20000); page.wait_for_timeout(250)
    vistas = {}
    parados = 0
    for _ in range(max_passos):
        novos = 0
        for r in pv.locator("[role=row]").all():
            idx = r.get_attribute("aria-rowindex")
            if idx is None or idx in vistas:
                continue
            cel = [t.strip().replace("\xa0", " ").strip() for t in r.inner_text().split("\n")]
            vistas[idx] = cel
            novos += 1
        parados = 0 if novos else parados + 1
        if parados >= 3:
            break
        page.mouse.wheel(0, 330); page.wait_for_timeout(350)
    return [vistas[k] for k in sorted(vistas, key=int)]


PED = re.compile(r"^(?P<ped>.+?) - (?P<forn>.+) - (?P<cod>\d{4,6}) - (?P<emi>\d\d/\d\d/\d{4}) - R?\$?$")
PROD = re.compile(r"^(?P<cod>\d{9}) - (?P<nome>.+)$")
FILIAL = re.compile(r"^\d\d - (FAZENDA|ESCRITORIO)")


def _numeros(cel):
    """Células depois do rótulo: QUANT, TOTAL(R$), ENTREGUE, TRANSITORIO (pode vir vazio), SALDO, VALOR SALDO(R$)."""
    v = [c for c in cel[1:] if c != ""]
    if len(v) == 6:
        qtd, _, ent, _, saldo, vsaldo = v
    elif len(v) == 5:
        qtd, _, ent, saldo, vsaldo = v
    else:
        return None
    try:
        return num(qtd), num(ent), num(saldo), num(vsaldo.replace("R$", "").strip())
    except ValueError:
        return None


IGNORAR = Path(__file__).with_name("compras_ignorar.txt")


def pedidos_ignorados():
    """Códigos de pedido listados em compras_ignorar.txt (eliminados por resíduo no Protheus; o BI não traz esse status)."""
    if not IGNORAR.exists():
        return set()
    return {l.split("#")[0].strip().upper() for l in IGNORAR.read_text(encoding="utf-8").splitlines() if l.split("#")[0].strip()}


def pedidos_com_saldo(linhas):
    out, fazenda, ped = [], None, None
    ignorar = pedidos_ignorados()
    for cel in linhas:
        rot = cel[0]
        if FILIAL.match(rot):
            fazenda, ped = rot, None
        elif PROD.match(rot) and ped:
            n = _numeros(cel)
            if not n or n[2] <= 0:
                continue
            m = PROD.match(rot)
            cat = categoria_do(m["nome"], m["cod"][:4])
            if not cat or ped["ped"].upper() in ignorar:
                continue
            out.append({"categoria": cat, "produto": m["nome"], "fazenda": re.sub(r"^\d\d - (FAZENDA |ESCRITORIO )?", "", fazenda).title(),
                        "pedido": ped["ped"], "fornecedor": ped["forn"].title(), "emissao": ped["emi"],
                        "quantidade": n[0], "entregue": n[1], "saldo": n[2], "valorSaldo": round(n[3], 2)})
        else:
            m = PED.match(rot)
            if m:
                ped = m.groupdict()
    return out


def compras(page, esperar):
    """Pedidos com saldo > 0 dos grupos acompanhados, já classificados por categoria."""
    abrir_pagina(page, PAGINA, esperar)
    faltou = selecionar_grupos(page, GRUPOS)
    if faltou:
        raise RuntimeError("compras: grupos de produto não achados no filtro: " + ", ".join(g[:4] for g in faltou))   # sessão/filtro instável: repete
    esperar(page)
    _expandir_tudo(page)
    linhas = _linhas_matriz(page)
    print(f"  compras: {len(linhas)} linhas lidas da matriz")
    ped = pedidos_com_saldo(linhas)
    return ped
