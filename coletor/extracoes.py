"""Extrações dos BIs. Cada função lê números da tela (só quantidades) e devolve a estrutura do painel."""
import json
import re
from pathlib import Path
from datetime import date, datetime, timedelta


def frame_relatorio(page):
    for fr in page.frames:
        if "app.powerbi.com" in fr.url:
            return fr
    raise RuntimeError("iframe do relatório não encontrado")


def abrir_pagina(page, nome, esperar):
    fr = frame_relatorio(page)
    fr.get_by_text(nome, exact=True).first.click()
    page.wait_for_timeout(3000)
    esperar(page)


def num(txt):
    """'2.041,00' -> 2041.0 ; '20.000' -> 20000"""
    return float(txt.replace(".", "").replace(",", "."))


def linhas_visiveis(fr, ncols):
    """Linhas da tabela no texto atual: cada linha começa em 'Selecionar Linha' e tem ncols campos."""
    partes = [p.strip() for p in fr.inner_text("body").split("\n")]
    out, i = [], 0
    while i < len(partes):
        if partes[i] == "Selecionar Linha" and i + ncols < len(partes) + 1:
            out.append(tuple(partes[i + 1:i + 1 + ncols]))
            i += ncols
        i += 1
    return out


def ler_tabela(page, ncols, max_voltas=150, passo=300):
    """Tabela virtualizada: rola com o mouse e junta as linhas novas até parar de aparecer."""
    fr = frame_relatorio(page)
    caixa = fr.locator('[role="grid"], [role="table"], .tableEx').first.bounding_box()
    x, y = caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2
    page.mouse.move(x, y)
    for _ in range(6):                      # volta ao topo (a tabela guarda a posição da rolagem)
        page.mouse.wheel(0, -5000)
        page.wait_for_timeout(300)
    vistas, ordem = set(), []
    parados = 0
    for _ in range(max_voltas):
        novas = 0
        for l in linhas_visiveis(fr, ncols):
            if l not in vistas:
                vistas.add(l); ordem.append(l); novas += 1
        parados = parados + 1 if novas == 0 else 0
        if parados >= 2:
            break
        page.mouse.move(x, y)
        page.mouse.wheel(0, passo)
        page.wait_for_timeout(700)
    return ordem


def bovinos_aguardando_abate(page, esperar):
    abrir_pagina(page, "Aguardando Abate", esperar)
    fr = frame_relatorio(page)
    cartao = re.search(r"Cabeças Abatidas\s*\n\s*([\d.]+)", fr.inner_text("body"))
    total = int(cartao.group(1).replace(".", "")) if cartao else None
    # A tabela é virtualizada e a rolagem pode pular linhas: repete com passos menores até a soma bater com o cartão.
    for passo in (300, 200, 120, 80):
        linhas = ler_tabela(page, 7, passo=passo)  # FILIAL, DATA, NF, LOTE, QTDCB, PESO CB, MOTORISTA
        por_filial, lotes = {}, set()
        for filial, _d, _nf, lote, qtd, *_ in linhas:
            por_filial[filial] = por_filial.get(filial, 0) + num(qtd)
            lotes.add(lote)
        if total is None or int(sum(por_filial.values())) == total:
            break
    soma = sum(por_filial.values())
    return {
        "cabecas": total if total is not None else int(soma),
        "lotes": len(lotes),
        "porFilial": [{"filial": f.title(), "cabecas": int(v)} for f, v in sorted(por_filial.items(), key=lambda kv: -kv[1])],
        "_conferencia": {"somaLinhas": int(soma), "cartao": total, "linhas": len(linhas)},
    }


JS_MATRIZ = r"""() => {
  const g=(q)=>[...document.querySelectorAll(q)].map(e=>{const b=e.getBoundingClientRect();return {t:e.innerText.replace(/\u00a0/g,' ').trim(),x:Math.round(b.x),y:Math.round(b.y),w:Math.round(b.width)}});
  return {cols:g('[role=columnheader]'), rows:g('[role=rowheader]'), body:g('[role=gridcell]')};
}"""


def resetar_periodo(page, ano):
    """Período do Cronograma vem preso (ex.: só jun-jul). Seleciona o ANO inteiro (todos os meses).
    Todos os anos deixariam a matriz larga demais: o Power BI só renderiza parte das colunas."""
    fr = frame_relatorio(page)
    caixa = fr.locator(".slicer-container").nth(1)
    caixa.locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click()
    page.wait_for_timeout(1200)

    def item(txt):
        return fr.locator(".slicerItemContainer").filter(has_text=re.compile(r"^\s*" + re.escape(txt) + r"\s*$")).first

    def marcado(loc):
        return "selected" in (loc.locator(".slicerCheckbox").first.get_attribute("class") or "")

    tudo = item("Selecionar tudo")
    if not marcado(tudo):
        tudo.click(); page.wait_for_timeout(2000)
    for a in fr.locator(".slicerItemContainer").all_inner_texts():
        a = a.strip()
        if re.fullmatch(r"\d{4}", a) and int(a) != ano and marcado(item(a)):
            item(a).click(); page.wait_for_timeout(1500)
    if not marcado(item(str(ano))):
        item(str(ano)).click(); page.wait_for_timeout(1500)
    page.keyboard.press("Escape")
    page.mouse.click(1590, 170)  # fecha o dropdown clicando no título do relatório
    page.wait_for_timeout(2500)


def titulo(s):
    ligacoes = {"de", "da", "do", "e", "das", "dos"}
    return " ".join(w if w in ligacoes else (w.upper() if len(w) <= 3 else w.capitalize()) for w in s.lower().split())


def bovinos_cronograma(page, esperar, hoje):
    abrir_pagina(page, "Conograma de Embarque", esperar)
    resetar_periodo(page, hoje.year)
    esperar(page)
    page.wait_for_timeout(3000)
    fr = frame_relatorio(page)
    caixa = fr.locator('[role="grid"], [role="table"], .tableEx, .pivotTable').first.bounding_box()
    cx, cy = caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2
    valores, colunas, totais = {}, {}, {}
    sem_novas = 0
    for _ in range(120):
        m = fr.evaluate(JS_MATRIZ)
        ys = sorted({c["y"] for c in m["cols"]})
        if len(ys) < 3:
            page.screenshot(path="dump/cron_erro.png")
            raise RuntimeError("cabeçalhos da matriz não encontrados: %s" % [(c["t"], c["y"]) for c in m["cols"]][:8])
        y_fil, y_cli, y_cid = ys[0], ys[1], ys[2]
        filiais = [c for c in m["cols"] if c["y"] == y_fil and c["w"] > 1 and c["t"] != "Filial" and c["t"] != "Total"]
        clientes = {c["x"]: c["t"] for c in m["cols"] if c["y"] == y_cli}
        for c in m["cols"]:
            if c["y"] == y_cid and c["t"] and c["x"] in clientes:
                fil = next((f["t"] for f in filiais if f["x"] <= c["x"] < f["x"] + f["w"]), "?")
                colunas[c["x"]] = (fil, clientes[c["x"]], c["t"])
        datas = {r["y"]: r["t"] for r in m["rows"] if re.fullmatch(r"\d\d/\d\d/\d{4}", r["t"])}
        novas = 0
        tx = next((c["x"] for c in m["cols"] if c["y"] == y_fil and c["t"] == "Total"), None)
        for cel in m["body"]:
            if tx is not None and cel["x"] == tx and cel["y"] in datas and re.fullmatch(r"[\d.]+", cel["t"]):
                totais[datas[cel["y"]]] = int(cel["t"].replace(".", ""))
            if cel["y"] in datas and cel["x"] in colunas and re.fullmatch(r"[\d.]+", cel["t"]):
                k = (datas[cel["y"]], cel["x"])
                if k not in valores:
                    valores[k] = int(cel["t"].replace(".", "")); novas += 1
        sem_novas = sem_novas + 1 if novas == 0 else 0
        if sem_novas >= 2:
            break
        page.mouse.move(cx, cy)
        page.mouse.wheel(0, 400)
        page.wait_for_timeout(700)
    # Conferência: soma das colunas de cada data x coluna 'Total' do próprio BI.
    soma_dia = {}
    for (d, _x), cab in valores.items():
        soma_dia[d] = soma_dia.get(d, 0) + cab
    divergentes = {d: (soma_dia.get(d, 0), t) for d, t in totais.items() if soma_dia.get(d, 0) != t}
    print("cronograma: datas conferidas", len(totais), "divergentes", divergentes)
    # Resumo do mês pela DATA DE EMBARQUE (a Visão Geral filtra por data do contrato e vem presa em setembro).
    mes = {"embarcado": 0, "aEmbarcar": 0, "ref": hoje.strftime("%m/%Y"),
           "anoEmbarcado": 0, "anoAEmbarcar": 0, "anoRef": hoje.year}
    for (d, _x), cab in valores.items():
        dt = datetime.strptime(d, "%d/%m/%Y").date()
        if dt.year == hoje.year:
            mes["anoEmbarcado" if dt < hoje else "anoAEmbarcar"] += cab
        if (dt.year, dt.month) == (hoje.year, hoje.month):
            mes["embarcado" if dt < hoje else "aEmbarcar"] += cab
    cron = []
    for (d, x), cab in valores.items():
        dt = datetime.strptime(d, "%d/%m/%Y").date()
        if dt >= hoje:
            fil, cli, cid = colunas[x]
            cron.append((dt, {"data": dt.strftime("%d/%m"), "frigorifico": " ".join(titulo(cli).split()[:2]), "cidade": titulo(cid),
                              "fazenda": titulo(fil), "cabecas": cab}))
    cron.sort(key=lambda t: t[0])
    return [c for _, c in cron][:40], mes


def grupo_produto(prod):
    p = prod.upper()
    if p.startswith("SOJA"):
        return "Soja"
    if p.startswith("MILHO"):
        return "Milho"
    return None


def graos_contratos(page, esperar):
    """Página 'Contrato de Venda - Grãos': por contrato, quantidade e saída (kg) -> sacas de 60 kg.
    Colunas: ST CTR DESCRICAO ENT CLIENTE VALOR QUANTIDADE SAIDA SALDO PROD SAFRA VENCIMENTO FILIAL."""
    abrir_pagina(page, "Contrato de Venda - Grãos", esperar)
    linhas = ler_tabela(page, 13)
    if not linhas:
        raise RuntimeError("tabela de contratos de grãos vazia (sessão expirada?)")
    por_grupo = {}
    for st, ctr, _desc, _ent, cliente, _valor, qtd, saida, _saldo, prod, safra, venc, filial in linhas:
        g = grupo_produto(prod)
        if not g or st.strip().upper() == "E":   # E = eliminado (quantidade 0)
            continue
        por_grupo.setdefault(g, []).append(dict(
            ctr=ctr, cliente=titulo(cliente), safra=safra, vence=venc,
            fazenda=titulo(re.sub(r"^\d+\s*-\s*", "", filial).replace("(MATRIZ)", "").strip()),
            contratadoSacas=round(num(qtd) / 60), entregueSacas=round(num(saida) / 60)))
    out = []
    # Saldo a entregar (contratado - entregue) de TODAS as safras: é a parte do estoque que já está vendida.
    # Safra do contrato "2025/2026" vira "25/26", o mesmo formato do BI Estoque.
    saldo = {}
    for g, itens in por_grupo.items():
        for i in itens:
            m = re.fullmatch(r"\s*\d{2}(\d{2})\s*/\s*\d{2}(\d{2})\s*", i["safra"])
            s = f"{m.group(1)}/{m.group(2)}" if m else i["safra"]
            d = saldo.setdefault(g.lower(), {}).setdefault(s, 0)
            saldo[g.lower()][s] = d + max(0, i["contratadoSacas"] - i["entregueSacas"])
    graos_contratos.saldo_por_safra = saldo
    for g in ("Soja", "Milho"):
        itens = por_grupo.get(g)
        if not itens:
            continue
        safra = max((i["safra"] for i in itens), key=lambda s: s.split("/")[0])
        atuais = [i for i in itens if i["safra"] == safra]
        for i in atuais:
            i.pop("safra")
        out.append({
            "safra": safra, "produto": g,
            "contratadoSacas": sum(i["contratadoSacas"] for i in atuais),
            "entregueSacas": sum(i["entregueSacas"] for i in atuais),
            "contratos": atuais,
            "_conferencia": {"linhasLidas": len(linhas)},
        })
    return out


ESTADO = Path(__file__).resolve().parent / "estado.json"


def acompanhar_saidas(graos, hoje):
    """Saída = aumento do total entregue entre uma coleta e a seguinte (sem ler romaneio por romaneio).
    Guarda o último total por produto/safra em estado.json e preenche g["saida"] = {hoje, ultima, desde}."""
    try:
        est = json.loads(ESTADO.read_text(encoding="utf-8"))
    except Exception:
        est = {}
    for g in graos:
        chave = f'{g["produto"]}|{g["safra"]}'
        e = est.get(chave) or {"total": g["entregueSacas"], "dia": hoje.isoformat(), "saidaDia": 0,
                               "ultima": None, "desde": hoje.isoformat()}
        delta = g["entregueSacas"] - e["total"]
        if e["dia"] != hoje.isoformat():
            e["dia"], e["saidaDia"] = hoje.isoformat(), 0
        if delta > 0:
            e["saidaDia"] += delta
            e["ultima"] = hoje.isoformat()
        e["total"] = g["entregueSacas"]   # delta negativo (correção no BI) é ignorado
        est[chave] = e
        g["saida"] = {"hojeSacas": e["saidaDia"], "ultima": e["ultima"], "desde": e["desde"]}
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


def definir_periodo(page, ini, fim):
    """Slicer de período como intervalo de datas (dois campos de texto dd/mm/aaaa)."""
    fr = frame_relatorio(page)
    campos = fr.locator(".slicer-container").nth(1).locator("input")
    # O fim vem antes do início: o campo de início só aceita datas até o fim atual (que pode estar em setembro).
    for campo, valor in ((campos.nth(1), fim), (campos.nth(0), ini)):
        campo.fill(valor.strftime("%d/%m/%Y"), force=True)
        campo.press("Enter")
        page.wait_for_timeout(3000)
    for campo, valor in ((campos.nth(0), ini), (campos.nth(1), fim)):
        if campo.input_value() != valor.strftime("%d/%m/%Y"):
            raise RuntimeError("período não aceito pelo BI: %s" % [c.input_value() for c in campos.all()])


def bovinos_abatidos_mes(page, esperar, hoje):
    """Página 'Abate': animais abatidos por frigorífico e data. Só a quantidade (as colunas de R$ são ignoradas).
    O Período vem preso (ex.: só setembro): ajusta para o mês corrente e confere a soma com o cartão do BI."""
    abrir_pagina(page, "Abate", esperar)
    primeiro = hoje.replace(day=1)
    ultimo = (primeiro.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    resultado = {}
    # O ano vem depois do mês: o fim é definido antes do início, então ampliar o período também funciona.
    for nome, ini, fim in (("mes", primeiro, ultimo), ("ano", date(hoje.year, 1, 1), date(hoje.year, 12, 31))):
        definir_periodo(page, ini, fim)
        esperar(page)
        page.wait_for_timeout(3000)
        fr = frame_relatorio(page)
        cartao = re.search(r"Cabeças Abatidas\s*\n\s*([\d.]+)", fr.inner_text("body"))
        total = int(cartao.group(1).replace(".", "")) if cartao else None
        soma, linhas = 0, []
        # FRIGORIFICO, DATA DO ABATE, QTDE, @ PESO, PELO LIQ, R$ @, VALOR BRUTO, VL RECEBER
        for passo in (300, 200, 120):
            linhas = ler_tabela(page, 8, passo=passo)
            soma = sum(int(num(l[2])) for l in linhas)
            if total is None or soma == total:
                break
        resultado[nome] = (total if total is not None else soma,
                           {"somaLinhas": soma, "cartao": total, "linhas": len(linhas)})
    return resultado


# ------------------------------------------------------------------ faixa de indicadores gerais

def total_da_tela(fr, decimal=False):
    """Número da linha 'Total' da tabela (o BI mostra 'Total', às vezes um espaço, e o valor).
    decimal=True exige vírgula decimal ('137.224.434,68'): evita pegar o 'Total' do cabeçalho seguido de
    códigos como '04' da primeira linha."""
    padrao = r"[\d.]+,\d+" if decimal else r"[\d.]+(,\d+)?"
    partes = [p.strip() for p in fr.inner_text("body").split("\n")]
    for i, p in enumerate(partes):
        if p == "Total":
            for q in partes[i + 1:i + 4]:
                if q == "Selecionar Linha":
                    break
                if re.fullmatch(padrao, q):
                    return num(q)
    return None


def ler_tabela_conferida(page, ncols, col_valor):
    """Lê a tabela e confere a soma com a linha Total do BI (avisa se não bater)."""
    linhas = ler_tabela(page, ncols)
    soma = sum(num(l[col_valor]) for l in linhas)
    total = total_da_tela(frame_relatorio(page))
    if total is not None and abs(soma - total) > 1:
        print(f"  AVISO: soma das linhas {soma} != Total do BI {total}")
    return linhas, total


def estoques(page, esperar):
    """BI 'Estoque' (PowerBI Celulares). Filtros vêm em 'Todos'; quantidades atuais, sem R$."""
    out = {}
    abrir_pagina(page, "Estoque de Bovinos", esperar)
    linhas, total = ler_tabela_conferida(page, 3, 2)           # produto, armazém, qtd
    conf = sum(num(q) for _, arm, q in linhas if "CONFINAMENTO" in arm.upper())
    out["rebanho"] = {"total": round(total or sum(num(l[2]) for l in linhas)), "confinamento": round(conf)}

    abrir_pagina(page, "Estoque de Graos", esperar)
    linhas, _ = ler_tabela_conferida(page, 3, 2)               # produto, safra (armazém), sacas
    graos = {}
    for prod, safra, sc in linhas:
        chave = "soja" if "SOJA" in prod.upper() else "milho" if "MILHO" in prod.upper() else None
        if not chave:
            continue
        g = graos.setdefault(chave, {"sacas": 0, "porSafra": {}})
        g["sacas"] += num(sc)
        s = safra.upper().replace("SAFRA", "").strip()
        g["porSafra"][s] = g["porSafra"].get(s, 0) + num(sc)
    for g in graos.values():
        g["sacas"] = round(g["sacas"])
        g["porSafra"] = [{"safra": s, "sacas": round(v)} for s, v in
                         sorted(g["porSafra"].items(), key=lambda kv: -kv[1])]
    out["estoqueGraos"] = graos

    abrir_pagina(page, "Estoque Combustivel", esperar)
    linhas, _ = ler_tabela_conferida(page, 3, 2)               # produto, grupo, litros
    soma = lambda f: round(sum(num(q) for p, g, q in linhas if f(p.upper(), g.upper())))
    out["combustivel"] = {
        "diesel": soma(lambda p, g: g == "OLEO DIESEL"),
        "gasolina": soma(lambda p, g: p.startswith("GASOLINA")),
        "etanol": soma(lambda p, g: g == "ETANOL"),
    }
    return out


def filtrar_dropdown(page, campo, valor, tentativas=3):
    """Slicer de lista suspensa com busca (seleção única): escolhe só `valor`.
    `campo` = nome do campo do slicer (aparece no textContent dele, ex.: 'Grupo de Produto').
    A lista às vezes demora a refazer a busca: tenta de novo, esperando mais a cada vez.
    Devolve False se o valor não aparecer em nenhuma tentativa."""
    for n in range(tentativas):
        fr = frame_relatorio(page)
        caixa = fr.locator(".slicer-container").filter(has_text=campo).first
        caixa.locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click()
        page.wait_for_timeout(1200 + 800 * n)
        busca = fr.locator("input.searchInput:visible, .searchHeader input:visible").first
        if busca.count():
            busca.click(); page.keyboard.press("Control+A"); page.keyboard.press("Backspace")
            page.keyboard.type(valor, delay=40); page.wait_for_timeout(1500 + 1500 * n)
        item = fr.locator(".slicerItemContainer:visible").filter(has_text=re.compile(r"^\s*" + re.escape(valor) + r"\s*$")).first
        achou = item.count() > 0
        if achou and not _marcado(item):
            item.click(); page.wait_for_timeout(1500)
        page.keyboard.press("Escape")
        page.mouse.click(1590, 170)
        page.wait_for_timeout(2500)
        if achou:
            return True
    return False


def ger_estoque(page, esperar):
    """BI 'Gerenciamento do Estoque' (saldo atual do Protheus). Fonte certa do estoque — o BI 'Estoque' do
    PowerBI Celulares está desatualizado (13/11/2026: soja 606 mil sc lá x 2,7 mil sc aqui).
    - Saldo Bovinos: tabela Filial | Armazém | Grupo | Fêmea | Macho | Total.
    - Saldo Atual de Produtos filtrado por grupo: soja e milho (kg -> sacas de 60 kg, por armazém/safra),
      óleo diesel, gasolina e etanol (litros)."""
    out = {}
    abrir_pagina(page, "Saldo Bovinos", esperar)
    linhas = ler_tabela(page, 6)
    tot = sum(num(l[5]) for l in linhas if l[5].strip())
    conf = sum(num(l[5]) for l in linhas if "CONFINAMENTO" in l[1].upper() and l[5].strip())
    partes = [p.strip() for p in frame_relatorio(page).inner_text("body").split("\n")]
    bi_tot = None
    for i, p in enumerate(partes):
        if p == "Total":
            ns = [num(q) for q in partes[i + 1:i + 6] if re.fullmatch(r"[\d.]+,\d+", q)]
            if ns:
                bi_tot = ns[-1]
    if bi_tot and abs(bi_tot - tot) > 1:
        print(f"  AVISO rebanho: soma das linhas {tot} != Total do BI {bi_tot} (usando o do BI)")
    out["rebanho"] = {"total": round(bi_tot or tot), "confinamento": round(conf)}

    abrir_pagina(page, "Saldo Atual de Produtos", esperar)
    graos = {}
    for chave, grupo in (("soja", "SOJA EM GRAOS"), ("milho", "MILHO EM GRAOS")):
        if not filtrar_dropdown(page, "Grupo de Produto", grupo):
            print("  AVISO estoque: grupo não encontrado:", grupo); continue
        esperar(page)
        linhas = ler_tabela(page, 11)                             # ..., saldo (kg) na 5ª coluna, armazém na 8ª
        total = total_da_tela(frame_relatorio(page), decimal=True)
        soma_kg = sum(num(l[4]) for l in linhas)
        if total is not None and abs(soma_kg - total) > 1:
            print(f"  AVISO estoque {grupo}: soma das linhas {soma_kg} != Total do BI {total}")
        por = {}
        for l in linhas:
            s = re.sub(r"(?i)safra", "", l[7]).strip() or l[7]
            por[s] = por.get(s, 0) + num(l[4]) / 60
        kg = total if total is not None else sum(num(l[4]) for l in linhas)
        graos[chave] = {"sacas": round(kg / 60), "kg": round(kg),
                        "porSafra": [{"safra": s, "sacas": round(v)} for s, v in sorted(por.items(), key=lambda kv: -kv[1]) if round(v)]}
    out["estoqueGraos"] = graos

    comb = {}
    for chave, grupo in (("diesel", "OLEO DIESEL"), ("gasolina", "GASOLINA"), ("etanol", "ETANOL")):
        if not filtrar_dropdown(page, "Grupo de Produto", grupo):
            print("  AVISO estoque: grupo não encontrado:", grupo); continue
        esperar(page)
        comb[chave] = round(sum(num(l[4]) for l in ler_tabela(page, 11)))   # saldo (L) na 5ª coluna
    out["combustivel"] = comb
    return out


def rh_quadro(page):
    """Cartões da página inicial do Painel de RH (filtros em 'Todos'). Só contagens."""
    partes = [p.strip() for p in frame_relatorio(page).inner_text("body").split("\n")]
    def depois(rotulo):
        for i, p in enumerate(partes):
            if p == rotulo and i + 1 < len(partes) and re.fullmatch(r"[\d.]+", partes[i + 1]):
                return int(num(partes[i + 1]))
        return None
    return {"total": depois("Total Funcionários"), "ativos": depois("Total ativo"),
            "afastados": depois("Afastados"), "ferias": depois("Férias")}


NOMES = [("PONTE DE PEDRA", "Ponte de Pedra"), ("P.PEDRA", "Ponte de Pedra"), ("P. PEDRA", "Ponte de Pedra"),
         ("PROMISS", "Promissão"), ("PANAMA", "Panamá"), ("MATO GROSSO", "Mato Grosso"), ("MATOGROSSO", "Mato Grosso"),
         ("GALHEIRO", "Galheiro"), ("TUCANO", "Tucano"), ("JAVA", "Java"),
         ("CAMPO GRANDE", "Escritório C. Grande"), ("C. GRANDE", "Escritório C. Grande"),
         ("CAMPO NOVO", "Escritório C. Novo"), ("C. NOVO", "Escritório C. Novo")]


def nome_fazenda(txt):
    """'FAZENDA P.PEDRA' / '03 - P. PEDRA' / 'FAZENDAPROMISS…' -> nome usado no painel."""
    t = txt.upper().replace("…", "").replace(" ", "")      # gráfico do BI cola as palavras: "FAZENDAPONTE DEPEDRA"
    for chave, nome in NOMES:
        if chave.replace(" ", "") in t:
            return nome
    return titulo(txt)


def linhas_de_tabela(fr, ncols):
    """Linhas visíveis ('Selecionar Linha' + ncols campos) e os números da linha Total (tabelas pequenas, sem rolar)."""
    partes = [p.strip() for p in fr.inner_text("body").split("\n")]
    linhas = linhas_visiveis(fr, ncols)
    total = []
    for i, p in enumerate(partes):
        if p == "Total":
            total = [num(q) for q in partes[i + 1:i + 1 + ncols + 2] if re.fullmatch(r"[\d.]+(,\d+)?", q)]
            if total:
                break
    return linhas, total, partes


def valor_do_filtro(partes, rotulo):
    for i, p in enumerate(partes):
        if p == rotulo and i + 1 < len(partes):
            return partes[i + 1]
    return None


def plantio(page, esperar):
    """'Plantio por Fazenda' do Indicadores de Plantio: planejado x plantado por fazenda do período selecionado.
    O filtro PERIODO SAFRA vem preso no período em andamento do BI (hoje SOJA SAFRA 26/27)."""
    abrir_pagina(page, "Plantio por Fazenda", esperar)
    linhas, total, partes = linhas_de_tabela(frame_relatorio(page), 7)   # fazenda, período, data, planej., plantado, a plantar, %
    linhas = [l for l in linhas if "SAFRA" in l[1].upper()]              # a página tem outra tabela menor embaixo
    if len(total) < 2:
        return None
    return {"safra": valor_do_filtro(partes, "PERIODO SAFRA"), "planejadoHa": total[0], "plantadoHa": total[1],
            "fazendas": [{"fazenda": nome_fazenda(l[0]), "planejadoHa": num(l[3]), "plantadoHa": num(l[4]),
                          "ultimoPlantio": l[2]} for l in linhas]}


def colheita(page, esperar):
    """'Produção por Fazenda - Sintetico' (Indicadores Colheita Soja/Milho): área colhida, sacas e sc/ha por fazenda
    do PERIODO PRODUCAO selecionado no BI (vem na safra mais recente: soja 25/26, milho safrinha 26)."""
    abrir_pagina(page, "Produção por Fazenda - Sintetico", esperar)
    linhas, total, partes = linhas_de_tabela(frame_relatorio(page), 4)   # fazenda, área, sacas, sc/ha
    if len(total) < 3:
        return None
    return {"safra": valor_do_filtro(partes, "PERIODO PRODUCAO"), "areaHa": total[0], "sacas": round(total[1]),
            "scHa": total[2], "fazendas": [{"fazenda": nome_fazenda(l[0]), "areaHa": num(l[1]), "sacas": round(num(l[2])),
                                            "scHa": num(l[3])} for l in linhas]}


def rh_por_fazenda(page, esperar):
    """Página 'Funcionarios Ativos': conta as linhas da tabela por filial e situação.
    Só as contagens saem daqui; nomes e documentos da tabela não são gravados."""
    abrir_pagina(page, "Funcionarios Ativos", esperar)
    esperado = valor_do_filtro([p.strip() for p in frame_relatorio(page).inner_text("body").split("\n")], "Total Funcionários")
    esperado = int(num(esperado)) if esperado else None
    # filial, contrato, matrícula, admissão, nome, situação, centro de custo, função. Tabela virtualizada:
    # se a rolagem pular linhas, tenta de novo com passo menor até bater com o cartão "Total Funcionários".
    for passo in (250, 150, 90):
        linhas = ler_tabela(page, 8, max_voltas=300, passo=passo)
        if esperado is None or len(linhas) >= esperado:
            break
    if esperado and len(linhas) != esperado:
        print(f"  AVISO RH: li {len(linhas)} linhas, o cartão diz {esperado}")
    por, areas = {}, {}
    for l in linhas:
        f = por.setdefault(nome_fazenda(l[0]), {"ativos": 0, "ferias": 0, "afastados": 0})
        s = l[5].upper()
        f["ferias" if "FÉRIAS" in s or "FERIAS" in s else "afastados" if "AFAST" in s else "ativos"] += 1
        areas[titulo(l[6])] = areas.get(titulo(l[6]), 0) + 1
    return {"linhasLidas": len(linhas), "linhasEsperadas": esperado,
            "fazendas": sorted([{"fazenda": k, **v} for k, v in por.items()], key=lambda x: -sum(x[k] for k in ("ativos", "ferias", "afastados"))),
            "areas": [{"area": k, "qtd": v} for k, v in sorted(areas.items(), key=lambda kv: -kv[1])[:6]]}


def rh_exames(page):
    """Cartões de exame (ASO) da página inicial do Painel de RH."""
    partes = [p.strip() for p in frame_relatorio(page).inner_text("body").split("\n")]
    def depois(r):
        v = valor_do_filtro(partes, r)
        return int(num(v)) if v and re.fullmatch(r"[\d.]+", v) else None
    return {"vencidos": depois("Vencidos"), "aVencer": depois("Prox Venc.")}


CANTINA = "ABATE PARA CANTINA"


def mortes_por_fazenda(fr):
    """Matriz 'Total de Morte' (FILIAL | ano | Total): {fazenda: total}. Nomes completos, ao contrário do gráfico."""
    partes = [p.strip() for p in fr.inner_text("body").split("\n") if p.strip()]
    if "Total de Morte" not in partes:
        return {}
    i, out = partes.index("Total de Morte") + 1, {}
    while i < len(partes) and not partes[i].upper().startswith("FAZENDA"):   # pula o cabeçalho (FILIAL | ano | Total)
        i += 1
    while i < len(partes) and partes[i] != "Total":
        p = partes[i]
        if p.upper().startswith("FAZENDA") and i + 2 < len(partes) and re.fullmatch(r"[\d.]+", partes[i + 2]):
            out[nome_fazenda(p)] = int(num(partes[i + 2])); i += 3
        else:
            i += 1
    return out


def filtrar_motivo(page, motivo):
    """Filtro MOTIVO da página Mortes. motivo=None volta para 'Todos' (desmarca o que estiver marcado)."""
    fr = frame_relatorio(page)
    caixa = fr.locator(".slicer-container").filter(has_text="MOTIVO").first
    caixa.locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click()
    page.wait_for_timeout(1500)
    for it in fr.locator(".slicerItemContainer:visible").all():
        txt = it.inner_text().strip().upper()
        marcado = "selected" in (it.locator(".slicerCheckbox").first.get_attribute("class") or "")
        if (motivo and txt == motivo and not marcado) or (not motivo and marcado and txt != "SELECIONAR TUDO"):
            it.click(); page.wait_for_timeout(1500)
            if motivo:
                break
    page.keyboard.press("Escape")
    page.mouse.click(1590, 170)
    page.wait_for_timeout(3000)


MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]


_IDX_PERIODO = None   # posição do slicer PERIODO na página (achada pela 1ª vez pelo valor = ano)


def _periodo_abrir(page):
    """Abre o dropdown PERIODO e devolve (frame, função item(texto)).
    Acha o slicer pelo valor exibido (um ano) e guarda a posição: depois de mexer ele pode mostrar 'Todos'."""
    global _IDX_PERIODO
    fr = frame_relatorio(page)
    caixas = fr.locator(".slicer-container")
    if _IDX_PERIODO is None:
        for k in range(caixas.count()):
            if re.fullmatch(r"\d{4}", caixas.nth(k).inner_text().strip()):
                _IDX_PERIODO = k; break
    if _IDX_PERIODO is None:
        raise RuntimeError("filtro PERIODO não encontrado")
    caixas.nth(_IDX_PERIODO).locator(".slicer-dropdown-menu, .slicer-restatement, .dropdown-chevron").first.click()
    page.wait_for_timeout(1500)

    def item(txt):
        """Item do dropdown; rola a lista (virtualizada) até ele aparecer."""
        for _ in range(15):
            loc = fr.locator(".slicerItemContainer").filter(has_text=re.compile(r"^\s*" + re.escape(txt) + r"\s*$"))
            if loc.count() and loc.first.bounding_box():
                return loc.first
            # rola o contêiner rolável da lista (ancestral com scrollHeight > clientHeight)
            rolou = fr.locator(".slicerItemContainer").first.evaluate("""el => {
                for (let p = el.parentElement; p; p = p.parentElement)
                    if (p.scrollHeight > p.clientHeight + 4) { const a = p.scrollTop; p.scrollTop += 120; return p.scrollTop !== a; }
                return false; }""")
            page.wait_for_timeout(600)
            if not rolou:
                break
        raise RuntimeError("item não encontrado no PERIODO: " + txt)
    return fr, item


def _periodo_fechar(page):
    page.keyboard.press("Escape")
    page.mouse.click(1590, 170)
    page.wait_for_timeout(3000)


def _marcado(loc):
    return "selected" in (loc.locator(".slicerCheckbox").first.get_attribute("class") or "")


def mortes_do_mes(page, esperar, hoje):
    """Mortes e abate p/ cantina do mês corrente: PERIODO = só o mês; lê; volta PERIODO = ano inteiro.
    Devolve {"mes": "11/2026", total, cantina, fazendas, motivos} (mesmo formato do ano) ou None (e avisa)."""
    ano, mes = str(hoje.year), MESES[hoje.month - 1]
    out = None
    # total do ano antes de filtrar: o do mês tem que ser menor (senão o filtro não pegou)
    total_ano_visto = [int(num(valor_do_filtro([p.strip() for p in frame_relatorio(page).inner_text("body").split("\n") if p.strip()],
                                               "Total de Mortes") or "0")) or 10**9]
    try:
        fr, item = _periodo_abrir(page)
        a = item(ano)
        if a.get_attribute("aria-expanded") == "false":
            a.locator(".expandButton, [class*=expand]").first.click(); page.wait_for_timeout(1200)
        if _marcado(a):
            a.click(); page.wait_for_timeout(1500)          # desmarca o ano inteiro
        m = item(mes)
        if not _marcado(m):
            m.click(); page.wait_for_timeout(1500)          # marca só o mês
        _periodo_fechar(page); esperar(page)
        fr = frame_relatorio(page)
        partes = [p.strip() for p in fr.inner_text("body").split("\n") if p.strip()]
        # com hierarquia o BI escreve o filtro como "2026 (Ano) + novembro (Mês)"
        rotulo = fr.locator(".slicer-container").nth(_IDX_PERIODO).inner_text().strip()
        tot = int(num(valor_do_filtro(partes, "Total de Mortes")))
        if mes in rotulo.lower() and tot < total_ano_visto[0]:
            out = {"mes": f"{hoje.month:02d}/{hoje.year}", **ler_mortes(page, esperar)}
        else:
            print("  AVISO mortes do mês: o filtro não ficou só no mês; ignorado. Slicers:",
                  [fr.locator(".slicer-container").nth(k).inner_text().strip() for k in range(fr.locator(".slicer-container").count())])
            page.screenshot(path=str(Path(__file__).parent / "dump" / "mortes_mes_falha.png"))
    except Exception as e:
        print("  AVISO mortes do mês:", e)
    finally:
        # devolve PERIODO = ano inteiro (como o BI estava)
        try:
            fr, item = _periodo_abrir(page)
            a = item(ano)
            if a.get_attribute("aria-expanded") == "false":
                a.locator(".expandButton, [class*=expand]").first.click(); page.wait_for_timeout(1200)
            m = item(mes)
            if _marcado(m) and not _marcado(a):
                m.click(); page.wait_for_timeout(1500)
            a = item(ano)
            if not _marcado(a):
                a.click(); page.wait_for_timeout(1500)
            _periodo_fechar(page); esperar(page)
            volta = valor_do_filtro([p.strip() for p in frame_relatorio(page).inner_text("body").split("\n") if p.strip()], "PERIODO")
            if volta != ano:
                print("  AVISO: PERIODO do BI Mortes ficou em", volta)
        except Exception as e:
            print("  AVISO: não consegui devolver o PERIODO do BI Mortes:", e)
    return out


def ler_mortes(page, esperar):
    """Lê a página 'Mortes' com o PERIODO que estiver aplicado: total, causas e mortes por fazenda.
    Abate para cantina NÃO é morte para o painel: sai do total, das causas e das barras por fazenda e vira
    um número à parte. Para separar por fazenda, filtra MOTIVO = cantina, lê, e devolve o filtro para 'Todos'."""
    fr = frame_relatorio(page)
    partes = [p.strip() for p in fr.inner_text("body").split("\n") if p.strip()]
    total = int(num(valor_do_filtro(partes, "Total de Mortes")))
    motivos_todos = [(m.strip().upper(), int(num(q))) for m, q, _ in linhas_visiveis(fr, 3)]
    cantina = sum(q for m, q in motivos_todos if m == CANTINA)
    geral = mortes_por_fazenda(fr)
    cant_faz = {}
    if cantina:
        try:
            filtrar_motivo(page, CANTINA)
            fr = frame_relatorio(page)
            if valor_do_filtro([p.strip() for p in fr.inner_text("body").split("\n") if p.strip()], "MOTIVO").upper() == CANTINA:
                cant_faz = mortes_por_fazenda(fr)
        finally:
            filtrar_motivo(page, None)
            esperar(page)
            volta = valor_do_filtro([p.strip() for p in frame_relatorio(page).inner_text("body").split("\n") if p.strip()], "MOTIVO")
            if volta != "Todos":
                print("  AVISO mortes: filtro MOTIVO ficou em", volta)
    if cantina and sum(cant_faz.values()) != cantina:
        print(f"  AVISO mortes: cantina por fazenda {sum(cant_faz.values())} != {cantina}; barras ficam com cantina")
        cant_faz = {}
    fazendas = sorted([{"fazenda": f, "mortes": v - cant_faz.get(f, 0), "cantina": cant_faz.get(f, 0)} for f, v in geral.items()],
                      key=lambda x: -x["mortes"])
    motivos = [{"motivo": m.capitalize(), "qtd": q} for m, q in motivos_todos if m != CANTINA][:5]
    return {"total": total - cantina, "cantina": cantina, "cantinaSeparada": bool(cant_faz) or not cantina,
            "fazendas": fazendas, "motivos": motivos}


def mortes(page, esperar):
    """Ano (PERIODO como o BI abre = ano corrente) e mês corrente (mortes_do_mes), cada um com a leitura completa."""
    ano = valor_do_filtro([p.strip() for p in frame_relatorio(page).inner_text("body").split("\n") if p.strip()], "PERIODO")
    out = {"ano": ano, **ler_mortes(page, esperar)}
    out["mes"] = mortes_do_mes(page, esperar, date.today())
    return out


def visao_geral(page, url_relatorio, esperar, esta_logado):
    """Indicadores das abas Estoques, Plantio/colheita, Funcionários e Mortes.
    Uma falha num BI não derruba os outros (fica traço no painel)."""
    v = {}
    def rh():
        v["rh"] = rh_quadro(page)
        v["rh"]["exames"] = rh_exames(page)
        v["rh"].update(rh_por_fazenda(page, esperar))
    def plantio_colheita():
        v["plantio"] = plantio(page, esperar)
    for nome, func in [("ger_estoque", lambda: v.update(ger_estoque(page, esperar))),
                       ("rh", rh),
                       ("plantio", plantio_colheita),
                       ("colheita_soja", lambda: v.setdefault("colheita", {}).__setitem__("soja", colheita(page, esperar))),
                       ("colheita_milho", lambda: v.setdefault("colheita", {}).__setitem__("milho", colheita(page, esperar))),
                       ("mortes", lambda: (abrir_pagina(page, "Mortes", esperar), v.__setitem__("mortes", mortes(page, esperar))))]:
        try:
            page.goto(url_relatorio(nome), wait_until="domcontentloaded")
            if not esta_logado(page):
                raise SystemExit("Sem login: rode python coletor.py login")
            esperar(page)
            func()
        except SystemExit:
            raise
        except Exception as e:
            print(f"  ERRO {nome}: {e}")
    return v


def negociado_no_estoque(visao, saldo):
    """Negociado de cada produto = saldo a entregar de TODOS os contratos abertos (qualquer safra).
    Decisão do usuário (13/11/2026): total do produto, sem casar safra do contrato com safra do estoque."""
    for prod, e in (visao.get("estoqueGraos") or {}).items():
        e["negociado"] = sum(saldo.get(prod, {}).values())


def coletar_tudo(page, url_relatorio, esperar_relatorio, esta_logado):
    page.goto(url_relatorio("venda_bovinos"), wait_until="domcontentloaded")
    if not esta_logado(page):
        raise SystemExit("Sem login: rode python coletor.py login")
    esperar_relatorio(page)
    cron, mes = bovinos_cronograma(page, esperar_relatorio, date.today())
    print("cronograma:", cron)
    abat = bovinos_abatidos_mes(page, esperar_relatorio, date.today())
    mes["abatidos"], mes["anoAbatidos"] = abat["mes"][0], abat["ano"][0]
    print("abatidos mês:", abat["mes"], "| ano:", abat["ano"])
    print("mes:", mes)
    page.goto(url_relatorio("contrato_graos"), wait_until="domcontentloaded")
    if not esta_logado(page):
        raise SystemExit("Sem login: rode python coletor.py login")
    esperar_relatorio(page)
    graos = graos_contratos(page, esperar_relatorio)
    acompanhar_saidas(graos, date.today())
    print("graos:", [(g["produto"], g["safra"], g["contratadoSacas"], g["entregueSacas"], len(g["contratos"])) for g in graos])
    visao = visao_geral(page, url_relatorio, esperar_relatorio, esta_logado)
    negociado_no_estoque(visao, getattr(graos_contratos, "saldo_por_safra", {}))
    print("visao:", visao)
    return {"bovinos": {"cronograma": cron, "mes": mes}, "graos": graos, "visao": visao}
