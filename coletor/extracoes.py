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
    return {"bovinos": {"cronograma": cron, "mes": mes}, "graos": graos}
