# Painel de Operações

Painel de TV (HTML estático, 16:9) para o setor: bovinos, grãos, radar de chuva sobre as fazendas, cotações e dólar.
Só quantidades (cabeças, sacas); nenhum valor monetário de contrato.

## Como abrir
Abra `index.html` (ou sirva a pasta: `python -m http.server 8765`). Os dados vêm de arquivos locais lidos a cada 10 min:

| Arquivo | Origem | Gerado por |
|---|---|---|
| `data.js` | base e exemplos (chuva medida, avisos) | à mão |
| `bi.js` | bovinos e grãos dos BIs do portal | `coletor/coletor.py coletar` |
| `mercado.js` | cotações boi/soja/milho | `coletor/cotacoes.py` |
| `fazendas.js` | contornos e sedes das fazendas | `scripts/kml_para_fazendas.py` |

`bi.js`, `mercado.js` e `coletor/estado.json` são gerados e não são versionados. Sem eles o painel mostra o bloco como EXEMPLO.

## Coletor dos BIs (`coletor/`)
Playwright + Chrome instalado, com perfil próprio em `coletor/perfil/` (login Microsoft feito uma vez, nunca versionar).

```
python coletor.py login      # entra no portal (fechar a janela ao terminar)
python coletor.py coletar    # lê os BIs e grava ../bi.js
python cotacoes.py           # lê as cotações e grava ../mercado.js
```

- O portal só aceita **uma sessão por conta**: cada coleta derruba quem estiver logado com o mesmo usuário.
- Feche qualquer Chrome do perfil antes de rodar (senão o Chrome sai com código 21).
- Agendamento no Windows: coletor às 7h e 13h; cotações às 8h30, 12h30 e 17h30.

## Fontes
Radar: Windy (embed). Chuva estimada: Open-Meteo. Dólar: AwesomeAPI. Cotações: Agrolink (Diamantino, Sapezal) e Imea via Notícias Agrícolas (MT = média das praças).
