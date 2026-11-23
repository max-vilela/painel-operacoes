"""Publica o painel no Vercel (acesso interno por link difícil de adivinhar, fora dos buscadores).

- Monta a pasta `vercel-site/` com os arquivos do painel (index.html, estilo.css, painel.js, fazendas.js, data.js, bi.js, mercado.js).
- Sem tela de login: a proteção é o endereço (nome do projeto aleatório em coletor/vercel_projeto.txt) + nada de indexação:
  robots.txt com Disallow, cabeçalho X-Robots-Tag em todas as respostas e <meta name="robots"> no index.html.
- Roda `npx vercel deploy --prod` (a CLI precisa estar logada: `npx vercel login`, uma vez).
- Chamado no fim de cada coleta (coletor.py) e à mão: `python coletor\\publicar_vercel.py`.
"""
import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = RAIZ / "vercel-site"
NOME = Path(__file__).resolve().parent / "vercel_projeto.txt"
ARQUIVOS = ["index.html", "estilo.css", "painel.js", "fazendas.js", "data.js", "bi.js", "mercado.js"]

VERCEL_JSON = {
    "cleanUrls": True,
    "headers": [
        {"source": "/(.*)", "headers": [
            {"key": "X-Robots-Tag", "value": "noindex, nofollow, noarchive, nosnippet, noimageindex"},
            {"key": "Referrer-Policy", "value": "no-referrer"},
            {"key": "Cache-Control", "value": "public, max-age=0, must-revalidate"},
        ]},
    ],
}
ROBOTS = "User-agent: *\nDisallow: /\n"
META = '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet"><meta name="referrer" content="no-referrer">'


def nome_do_projeto():
    """Nome aleatório e fixo: o endereço é <nome>.vercel.app. Fica em vercel_projeto.txt (não versionado)."""
    if NOME.exists() and NOME.read_text(encoding="utf-8").strip():
        return NOME.read_text(encoding="utf-8").strip()
    n = "painel-ops-" + secrets.token_hex(10)
    NOME.write_text(n, encoding="utf-8")
    return n


def montar():
    SITE.mkdir(exist_ok=True)
    for a in ARQUIVOS:
        src = RAIZ / a
        if not src.exists():
            print("AVISO: falta", a)
            continue
        if a == "index.html":
            html = src.read_text(encoding="utf-8")
            if 'name="robots"' not in html:
                html = html.replace("<head>", "<head>\n" + META, 1)
            (SITE / a).write_text(html, encoding="utf-8")
        else:
            shutil.copyfile(src, SITE / a)
    (SITE / "robots.txt").write_text(ROBOTS, encoding="utf-8")
    (SITE / "vercel.json").write_text(json.dumps(VERCEL_JSON, indent=2), encoding="utf-8")


def mostrar(txt):
    print(txt.encode("ascii", "replace").decode())


def token_da_cli():
    r"""Login da CLI (npx vercel login) guardado em %APPDATA%\com.vercel.cli\Data\auth.json. Lido aqui porque a tarefa
    agendada roda sem as variáveis de ambiente do usuário e a CLI não achava o login sozinha. Nunca é impresso."""
    for base in (os.environ.get("APPDATA"), str(Path.home() / "AppData" / "Roaming")):
        if not base:
            continue
        arq = Path(base) / "com.vercel.cli" / "Data" / "auth.json"
        if arq.exists():
            try:
                return json.loads(arq.read_text(encoding="utf-8")).get("token")
            except (ValueError, OSError):
                return None
    return None


def vercel(*args, check=True):
    npx = shutil.which("npx") or "npx"
    env = os.environ.copy()
    tok = token_da_cli()
    if tok:
        env["VERCEL_TOKEN"] = tok
    return subprocess.run([npx, "--yes", "vercel@latest", *args], cwd=SITE, capture_output=True, text=True, env=env,
                          encoding="utf-8", errors="replace", check=check, timeout=600)


def publicar():
    montar()
    if not (SITE / ".vercel" / "project.json").exists():
        r = vercel("link", "--yes", "--project", nome_do_projeto(), check=False)
        mostrar((r.stdout + r.stderr).strip()[-400:])
    r = vercel("deploy", "--prod", "--yes", check=False)
    saida = (r.stdout + "\n" + r.stderr).strip()
    mostrar(saida[-600:])
    return r.returncode == 0


if __name__ == "__main__":
    sys.exit(0 if publicar() else 1)
