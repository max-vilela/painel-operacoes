"""Cópia dos arquivos gerados (bi.js, mercado.js) para uma segunda pasta, se houver.

Útil quando o painel é aberto de outra pasta (ex.: uma pasta sincronizada do SharePoint).
O caminho fica em coletor/destino.txt (uma linha; não é versionado). Sem o arquivo, não faz nada.
"""
import shutil
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent / "destino.txt"


def publicar(arquivo):
    arquivo = Path(arquivo)
    try:
        pasta = Path(ARQUIVO.read_text(encoding="utf-8").strip())
    except FileNotFoundError:
        return
    if not pasta.is_dir():
        print("destino.txt aponta para uma pasta que não existe:", pasta)
        return
    shutil.copyfile(arquivo, pasta / arquivo.name)
    print("copiado para", pasta / arquivo.name)
