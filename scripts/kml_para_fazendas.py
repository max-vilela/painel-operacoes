"""Converte o KML dos talhões físicos em fazendas.js (GeoJSON) para o mapa do painel.

Só LÊ o KML (regra do projeto talhoes-distancias: nunca editar entrada.kml).
Respeita dados/talhoes_ignorados.json (polígonos fantasma que o projeto já excluiu).

Uso:
  python kml_para_fazendas.py [caminho_entrada.kml] [caminho_saida/fazendas.js]
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

KML_PADRAO = Path(r"C:\laragon\www\talhoes-distancias\dados\entrada.kml")
SAIDA_PADRAO = Path(__file__).resolve().parent.parent / "fazendas.js"
NS = {"k": "http://www.opengis.net/kml/2.2"}


def ler_coords(texto):
    pontos = []
    for tripla in texto.split():
        lon, lat, *_ = tripla.split(",")
        pontos.append([round(float(lon), 5), round(float(lat), 5)])
    return pontos


def area_ha(descricao):
    m = re.search(r"Área:\s*([\d.,]+)\s*ha", descricao or "")
    return float(m.group(1).replace(",", ".")) if m else None


def main():
    kml = Path(sys.argv[1]) if len(sys.argv) > 1 else KML_PADRAO
    saida = Path(sys.argv[2]) if len(sys.argv) > 2 else SAIDA_PADRAO

    pasta_dados = kml.parent
    nomes = json.loads((pasta_dados / "nomes.json").read_text(encoding="utf-8"))
    ignorados = json.loads((pasta_dados / "talhoes_ignorados.json").read_text(encoding="utf-8"))

    raiz = ET.parse(kml).getroot()
    talhoes, sedes = [], []
    ignorados_vistos = 0

    for pasta in raiz.iter("{%s}Folder" % NS["k"]):
        chave = (pasta.findtext("k:name", default="", namespaces=NS) or "").strip()
        fazenda = nomes.get(chave)
        if not fazenda:
            continue
        for pm in pasta.findall("k:Placemark", NS):
            nome = (pm.findtext("k:name", default="", namespaces=NS) or "").strip()
            desc = pm.findtext("k:description", default="", namespaces=NS)
            ponto = pm.find("k:Point/k:coordinates", NS)
            poligono = pm.find(".//k:Polygon/k:outerBoundaryIs/k:LinearRing/k:coordinates", NS)
            if ponto is not None:
                lon, lat = ler_coords(ponto.text)[0]
                sedes.append({"fazenda": fazenda, "nome": nome, "lon": lon, "lat": lat})
            elif poligono is not None:
                codigo = nome.split(" - ")[0].strip()
                if codigo in ignorados.get(chave, []):
                    ignorados_vistos += 1
                    continue
                talhoes.append({
                    "type": "Feature",
                    "properties": {"fazenda": fazenda, "codigo": codigo, "nome": nome, "area_ha": area_ha(desc)},
                    "geometry": {"type": "Polygon", "coordinates": [ler_coords(poligono.text)]},
                })

    dados = {"talhoes": {"type": "FeatureCollection", "features": talhoes}, "sedes": sedes}
    saida.write_text(
        "// GERADO por scripts/kml_para_fazendas.py a partir do KML. Não editar à mão.\n"
        "window.FAZENDAS = " + json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    por_fazenda = {}
    for f in talhoes:
        por_fazenda[f["properties"]["fazenda"]] = por_fazenda.get(f["properties"]["fazenda"], 0) + 1
    print(f"{len(talhoes)} talhões, {len(sedes)} sedes, {ignorados_vistos} ignorados -> {saida}")
    for nome, qtd in sorted(por_fazenda.items()):
        print(f"  {nome}: {qtd}")


if __name__ == "__main__":
    main()
