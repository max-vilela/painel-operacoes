"""Escolha automática da safra MAIS RECENTE de soja e de milho nos BIs de plantio e de colheita.

Os BIs vêm com um filtro de safra salvo (um valor só, ex.: 'SOJA SAFRA 25/26') e o painel antes lia o que estivesse
selecionado. Aqui o coletor lista os períodos do filtro, ordena do mais novo para o mais antigo e fica com o primeiro
que já tem dado de verdade (plantio: área plantada > 0; colheita: área colhida > 0). Assim, quando a soja 26/27 começar
a ser colhida, ou o milho safra 26/27 a ser plantado, o painel passa para ela sozinho.
"""
import re

from extracoes import _marcado, abrir_pagina, frame_relatorio, linhas_de_tabela, nome_fazenda, num

ROTULO = re.compile(r"[A-ZÇÃÕÉÍÓ ]+ \d\d/\d\d")     # o filtro de safra mostra, por ex.: "SOJA SAFRA 26/27"


def chave_safra(rotulo):
    """Ordem cronológica de plantio: (ano de início, tipo). Safrinha 26/26 (plantada no início de 2026) vem ANTES
    da safra 26/27 (plantada no fim de 2026), e depois da safra 25/26."""
    m = re.search(r"(\d\d)/(\d\d)$", rotulo)
    return (int(m.group(1)) if m else 0, 0 if "SAFRINHA" in rotulo.upper() else 1)


def _slicer_safra(fr):
    cx = fr.locator(".slicer-container")
    for k in range(cx.count()):
        if ROTULO.fullmatch(cx.nth(k).inner_text().strip()):
            return cx.nth(k)
    raise RuntimeError("filtro de safra não encontrado")


def _aberto(fr):
    return fr.locator(".slicerItemContainer:visible").count() > 0


def _abrir(page):
    """Abre a lista do filtro de safra, sem fechar sem querer uma lista que já esteja aberta."""
    fr = frame_relatorio(page)
    for _ in range(3):
        if _aberto(fr):
            return fr
        _slicer_safra(fr).locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click()
        page.wait_for_timeout(1500)
    if not _aberto(fr):
        raise RuntimeError("a lista do filtro de safra não abriu")
    return fr


def _fechar(page):
    fr = frame_relatorio(page)
    page.keyboard.press("Escape")
    page.mouse.click(1590, 170)
    page.wait_for_timeout(1500)
    for _ in range(2):
        if not _aberto(fr):
            break
        _slicer_safra(fr).locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click()   # alterna: fecha
        page.wait_for_timeout(1500)
    page.wait_for_timeout(1000)


def _rolar(fr, page):
    """Rola a lista (virtualizada) um passo. False se não deu para rolar mais."""
    r = fr.locator(".slicerItemContainer:visible").first.evaluate("""el => { for (let p = el.parentElement; p; p = p.parentElement)
        if (p.scrollHeight > p.clientHeight + 4) { const a = p.scrollTop; p.scrollTop += 150; return p.scrollTop !== a; } return false; }""")
    page.wait_for_timeout(450)
    return r


def _topo(fr, page):
    """Volta a lista (virtualizada) ao topo: depois de uma seleção ela abre rolada no meio."""
    fr.locator(".slicerItemContainer:visible").first.evaluate("""el => { for (let p = el.parentElement; p; p = p.parentElement)
        if (p.scrollHeight > p.clientHeight + 4) { p.scrollTop = 0; return true; } return false; }""")
    page.wait_for_timeout(600)


def listar_periodos(page):
    fr = _abrir(page)
    _topo(fr, page)
    itens = []
    for _ in range(30):
        for t in fr.locator(".slicerItemContainer:visible").all_inner_texts():
            t = t.strip()
            if t and t not in itens:
                itens.append(t)
        if not _rolar(fr, page):
            break
    _fechar(page)
    return itens


def selecionar(page, rotulo):
    """Deixa SÓ `rotulo` selecionado no filtro de safra. Devolve True se o filtro ficou assim."""
    for tentativa in range(2):
        fr = _abrir(page)
        _topo(fr, page)
        achou = False
        for _ in range(30):
            loc = fr.locator(".slicerItemContainer:visible").filter(has_text=re.compile(r"^\s*" + re.escape(rotulo) + r"\s*$"))
            if loc.count():
                if not _marcado(loc.first):
                    loc.first.click(); page.wait_for_timeout(1500)
                achou = True
                break
            if not _rolar(fr, page):
                break
        if achou and tentativa == 1:                      # seleção múltipla: desmarca os outros que estiverem marcados
            for it in fr.locator(".slicerItemContainer:visible").all():
                if _marcado(it) and it.inner_text().strip() != rotulo:
                    it.click(); page.wait_for_timeout(1200)
        _fechar(page)
        if not achou:
            return False
        if _slicer_safra(frame_relatorio(page)).inner_text().strip() == rotulo:
            return True
    return False


# ------------------------------------------------------------------ leitura do que está selecionado

def ler_plantio(page, rotulo):
    """'Plantio por Fazenda': planejado x plantado por fazenda do período selecionado."""
    linhas, total, _ = linhas_de_tabela(frame_relatorio(page), 7)   # fazenda, período, data, planej., plantado, a plantar, %
    linhas = [l for l in linhas if re.search(r"SAFR", l[1].upper())]  # (a página tem outra tabela menor embaixo)
    if len(total) < 2:
        return None
    return {"safra": rotulo, "planejadoHa": total[0], "plantadoHa": total[1],
            "fazendas": [{"fazenda": nome_fazenda(l[0]), "planejadoHa": num(l[3]), "plantadoHa": num(l[4]),
                          "ultimoPlantio": l[2]} for l in linhas]}


def ler_colheita(page, rotulo):
    """'Produção por Fazenda - Sintetico': área colhida, sacas e sc/ha por fazenda do período selecionado."""
    linhas, total, _ = linhas_de_tabela(frame_relatorio(page), 4)   # fazenda, área, sacas, sc/ha
    if len(total) < 3:
        return None
    return {"safra": rotulo, "areaHa": total[0], "sacas": round(total[1]), "scHa": total[2],
            "fazendas": [{"fazenda": nome_fazenda(l[0]), "areaHa": num(l[1]), "sacas": round(num(l[2])),
                          "scHa": num(l[3])} for l in linhas]}


def _tem_plantio(d):
    return bool(d) and d["plantadoHa"] > 0


def _tem_colheita(d):
    return bool(d) and d["areaHa"] > 0


def melhor_periodo(page, esperar, cultura, ler, ativo, max_tentativas=5):
    """Do período mais novo ao mais antigo da cultura ('SOJA' ou 'MILHO'), o primeiro com dado de verdade."""
    todos = listar_periodos(page)
    cand = sorted((p for p in todos if p.upper().startswith(cultura + " ") and re.search(r"SAFR", p.upper())),
                  key=chave_safra, reverse=True)
    print(f"  {cultura}: períodos {cand[:max_tentativas]}")
    for rot in cand[:max_tentativas]:
        if not selecionar(page, rot):
            print("  AVISO safra: não consegui selecionar", rot)
            continue
        esperar(page)
        page.wait_for_timeout(1500)
        d = ler(page, rot)
        if ativo(d):
            print(f"  {cultura}: usando {rot}")
            return d
    return None


def _selecionado(page):
    return _slicer_safra(frame_relatorio(page)).inner_text().strip()


def plantio_por_cultura(page, esperar):
    """{'soja': {...}, 'milho': {...}} com a safra mais recente de cada cultura que já tem plantio.
    Se a escolha automática falhar, cai para o que o BI deixou selecionado (como era antes)."""
    abrir_pagina(page, "Plantio por Fazenda", esperar)
    out = {}
    for cult in ("SOJA", "MILHO"):
        try:
            d = melhor_periodo(page, esperar, cult, ler_plantio, _tem_plantio)
        except Exception as e:
            print(f"  AVISO plantio {cult}:", str(e)[:100]); d = None
        if d:
            out[cult.lower()] = d
    if not out:
        rot = _selecionado(page)
        d = ler_plantio(page, rot)
        if d:
            out["milho" if rot.upper().startswith("MILHO") else "soja"] = d
    return out


def colheita_da_cultura(page, esperar, cultura):
    """Colheita da safra mais recente que já tem área colhida; sem isso, o que o BI deixou selecionado."""
    abrir_pagina(page, "Produção por Fazenda - Sintetico", esperar)
    try:
        d = melhor_periodo(page, esperar, cultura, ler_colheita, _tem_colheita)
    except Exception as e:
        print(f"  AVISO colheita {cultura}:", str(e)[:100]); d = None
    return d or ler_colheita(page, _selecionado(page))
