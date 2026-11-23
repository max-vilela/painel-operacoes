"""Publica o CÓDIGO do painel na pasta do SharePoint (a que está em coletor/destino.txt).

Copia index.html, estilo.css, painel.js, data.js e fazendas.js de uma vez, para nunca faltar um arquivo.
Na cópia de destino, os links de estilo.css e painel.js ganham ?v=<hora>, para a TV não usar arquivo antigo do cache.
Os dados (bi.js, mercado.js) NÃO são copiados aqui: quem copia é o coletor, a cada coleta.

Uso:  python publicar_painel.py
"""
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVOS = ["fazendas.js", "data.js", "estilo.css", "painel.js", "index.html"]   # index.html por último: só passa a apontar para o CSS/JS depois de eles já estarem lá


def main():
    try:
        destino = Path((Path(__file__).resolve().parent / "destino.txt").read_text(encoding="utf-8").strip())
    except FileNotFoundError:
        sys.exit("coletor/destino.txt não existe: não sei para onde publicar.")
    if not destino.is_dir():
        sys.exit(f"A pasta de destino não existe: {destino}")
    faltam = [a for a in ARQUIVOS if not (RAIZ / a).exists()]
    if faltam:
        sys.exit("Faltam arquivos na pasta do painel: " + ", ".join(faltam))
    versao = datetime.now().strftime("%Y%m%d%H%M%S")
    for nome in ARQUIVOS:
        origem, alvo = RAIZ / nome, destino / nome
        if nome == "index.html":
            html = origem.read_text(encoding="utf-8")
            html = re.sub(r'(href="estilo\.css|src="painel\.js)(\?v=\w+)?"', rf'\1?v={versao}"', html)
            alvo.write_text(html, encoding="utf-8", newline="")
        else:
            shutil.copyfile(origem, alvo)
        print("copiado:", alvo)
    print("pronto. Versão", versao, "- recarregue a página na TV (F5) para pegar o código novo.")


if __name__ == "__main__":
    main()
    try:                                   # o mesmo código vai também para o painel no Vercel (link interno)
        import publicar_vercel
        print("vercel:", "publicado" if publicar_vercel.publicar() else "FALHOU")
    except Exception as e:
        print("AVISO vercel:", str(e)[:150])
