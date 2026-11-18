# Painel de Operações

Painel de TV (HTML estático, 16:9) para o setor: bovinos, grãos, radar de chuva sobre as fazendas, cotações e dólar.
Só quantidades (cabeças, sacas); nenhum valor monetário de contrato.

## Como abrir
Abra `index.html` direto da pasta (duplo clique, `file://`: é assim que a TV abre) ou sirva a pasta com `python -m http.server 8765`.

## Arquivos
| Arquivo | O que é |
|---|---|
| `index.html` | só a estrutura (marcação) das telas |
| `estilo.css` | todo o visual |
| `painel.js` | toda a lógica: carrossel, faixa de cotações, desenho de cada aba, leitura dos dados |
| `fazendas.js` | contornos e sedes das fazendas (`scripts/kml_para_fazendas.py`) |
| `data.js` | esqueleto de dados (sem números de exemplo) |
| `bi.js` | bovinos, grãos, estoques, plantio, colheita, funcionários e mortes dos BIs (`coletor/coletor.py coletar`) |
| `mercado.js` | cotações boi/soja/milho (`coletor/cotacoes.py`) |
| `index-classico.html` | layout antigo, guardado de backup (arquivo único) |

`painel.js` é um script **comum**, não módulo (`type="module"` é bloqueado em `file://`). Os dados são lidos a cada 10 min por injeção de script, que também funciona em `file://`.
`bi.js`, `mercado.js` e `coletor/estado.json` são gerados e não são versionados. Sem eles o bloco mostra "sem leitura".

## Publicar no SharePoint (o que a TV abre)
```
python coletor\publicar_painel.py
```
Copia `fazendas.js`, `data.js`, `estilo.css`, `painel.js` e, por último, `index.html` para a pasta de `coletor/destino.txt`, com um número de versão nos links do CSS e do JS (evita arquivo antigo no cache). Depois, recarregue a página na TV (F5). Os dados (`bi.js`, `mercado.js`) quem copia é o coletor, a cada coleta.
`python coletor\teste_file.py [pasta]` abre o painel direto da pasta num Chrome real e confere se tudo carrega.

## Coletor dos BIs (`coletor/`)
Playwright + Chrome instalado, com perfil próprio em `coletor/perfil/` (login Microsoft feito uma vez, nunca versionar).

```
python coletor.py login      # entra no portal (fechar a janela ao terminar)
python coletor.py coletar    # lê os BIs e grava ../bi.js
python cotacoes.py           # lê as cotações e grava ../mercado.js
```

- O portal só aceita **uma sessão por conta**: cada coleta derruba quem estiver logado com o mesmo usuário.
- Feche qualquer Chrome do perfil antes de rodar (senão o Chrome sai com código 21).
- Agendamento no Windows: coletor a cada 2 h, das 8h30 às 18h30; cotações às 8h30, 12h30 e 17h30.

## Fontes
Radar: Windy (embed). Chuva estimada: Open-Meteo. Dólar: AwesomeAPI. Cotações: Agrolink (Diamantino, Sapezal) e Imea via Notícias Agrícolas (MT = média das praças).
- Cotações e dólar: faixa rolante no rodapé (para a esquerda, em laço); pausa quando o mouse passa por cima.
