# Painel de Operações — de onde vem cada informação

Atualizado em 17/11/2026. Os números do painel **só são tão novos quanto o BI de origem**: o coletor lê o que o Power BI já tem.

Links dos BIs: `https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2/Report/<id>`

## 1. BIs do portal usados

| BI (nome no portal) | Pasta no portal | Link |
|---|---|---|
| Venda Bovinos | Bovinos | [abrir](https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2/Report/41557c22-bead-4848-82f6-67fdf78d333a) |
| Contrato de Venda - Grãos | Produção | [abrir](https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2/Report/8c2c1c01-310b-4c25-a4cb-32ce4fb42934) |
| Gerenciamento do Estoque | Estoque | [abrir](https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2/Report/fccc6dc1-8135-4f09-9d06-6fa8ee1264c2) |
| Mortes | Bovinos | [abrir](https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2/Report/d61b96ea-a906-4141-9b72-ceccdae57dfa) |
| Indicadores de Plantio | Indicadores PIMS | [abrir](https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2/Report/55cf318b-874c-4c2c-8ed8-a4b901ccd4f9) |
| Indicadores Colheita Soja | Indicadores PIMS | [abrir](https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2/Report/e54486e0-b7ff-4bba-a0a8-c96f3ef61f94) |
| Indicadores Colheita Milho | Indicadores PIMS | [abrir](https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2/Report/a48e797b-fd6b-434f-9fa8-c96bd6e3efcc) |
| Contratos vs Romaneios | Produção | [abrir](https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2/Report/141523b6-a1d2-4c0d-8127-9b7716fd629e) |
| Painel de Recursos Humanos - Fazendas | Relatórios | [abrir](https://bi.livioeoutro.com.br/Organization/2958af72-9c7b-4653-93e6-e43754b94aa2/Report/af53f0dc-1a29-4452-9366-9907927b9be9) |

## 2. Indicador × fonte

### Bovinos
| Indicador no painel | BI | Página | Como é obtido |
|---|---|---|---|
| Embarcado no mês / no ano | Venda Bovinos | Conograma de Embarque (grafia do portal) | Matriz por data de **embarque**, período = ano corrente; soma conferida com a coluna Total do BI |
| A embarcar no mês / no ano | Venda Bovinos | Conograma de Embarque (grafia do portal) | Mesma matriz, animais ainda não embarcados |
| Próximos embarques (lista) | Venda Bovinos | Conograma de Embarque (grafia do portal) | Data, frigorífico, cidade, fazenda e cabeças dos próximos programados |
| Abatidos no mês / no ano | Venda Bovinos | Abate | Cartão de total com o período ajustado para o mês e para o ano (só quantidade, sem R$) |

### Mortes
| Indicador | BI | Página | Como é obtido |
|---|---|---|---|
| Mortes (mês e ano) | Mortes | Mortes | Total de Mortes **menos** abate para cantina; filtro PERIODO = ano e depois só o mês |
| Cantina (mês e ano) | Mortes | Mortes | Motivo "ABATE PARA CANTINA" (fora do total de mortes) |
| Principais causas | Mortes | Mortes | Tabela MOTIVO MORTE × QTDE, 5 maiores, sem cantina |
| Mortes por fazenda | Mortes | Mortes | Matriz "Total de Morte" por filial; cantina por fazenda lida filtrando o motivo |

### Grãos (contratos)
| Indicador | BI | Página | Como é obtido |
|---|---|---|---|
| Contratado / saldo a entregar / % entregue | Contrato de Venda - Grãos | Contrato de Venda - Grãos | Quantidade e saída por contrato em kg ÷ 60 = sacas, da safra mais recente de cada produto |
| Entregue / saída (kg) por contrato | **Contratos vs Romaneios** e Contrato de Venda - Grãos | Todos os Contratos vs Romaneios; Contrato de Venda - Grãos | Vale a **maior** das duas saídas: o BI de Romaneios atualiza antes (18/11: 480 t faturadas no contrato 000316 lá, zero no outro). A saída só aparece depois da nota fiscal |
| Saída hoje / última saída | (derivado) | — | Aumento do "entregue" entre uma coleta e a seguinte |
| Contratos com saldo | Contrato de Venda - Grãos | Contrato de Venda - Grãos | Contratos abertos, vencimento mais próximo primeiro |

### Plantio e colheita
| Indicador | BI | Página | Como é obtido |
|---|---|---|---|
| Planejado / plantado / % por fazenda (soja e milho) | Indicadores de Plantio | Plantio por Fazenda | Automático: o coletor (safras.py) escolhe a safra mais recente de cada cultura com área plantada > 0 (hoje SOJA SAFRA 26/27 e MILHO SAFRINHA 26/26) |
| Produtividade da soja (sc/ha, sacas, área) | Indicadores Colheita Soja | Produção por Fazenda - Sintetico | Automático: safra mais recente com área colhida > 0 (hoje SOJA SAFRA 25/26) |
| Produtividade do milho (sc/ha, sacas, área) | Indicadores Colheita Milho | Produção por Fazenda - Sintetico | Automático: safra mais recente com área colhida > 0 (hoje MILHO SAFRINHA 26/26) |

### Estoques
| Indicador | BI | Página | Como é obtido |
|---|---|---|---|
| Rebanho (total, confinamento, pasto) | Gerenciamento do Estoque | Saldo Bovinos | Soma da coluna Total (conferida com o Total do BI); confinamento = armazém 06 |
| Soja e milho em estoque (por safra) | Gerenciamento do Estoque | Saldo Atual de Produtos | Filtro Grupo = SOJA/MILHO EM GRAOS; kg ÷ 60 = sacas |
| Diesel, gasolina, etanol | Gerenciamento do Estoque | Saldo Atual de Produtos | Filtro Grupo = OLEO DIESEL / GASOLINA / ETANOL, em litros |
| Negociado (soja e milho) | Contrato de Venda - Grãos | Contrato de Venda - Grãos | Saldo a entregar de todos os contratos abertos do produto |

### Funcionários
| Indicador | BI | Página | Como é obtido |
|---|---|---|---|
| Ativos, em férias, afastados, quadro total | Painel de Recursos Humanos - Fazendas | Página inicial (a que abre sozinha) | Cartões da página |
| Exames (ASO) vencidos | Painel de Recursos Humanos - Fazendas | Página inicial (a que abre sozinha) | Cartão "Vencidos" |
| Funcionários por local | Painel de Recursos Humanos - Fazendas | Funcionarios Ativos | Contagem das linhas da tabela por filial e situação (só contagens, sem nomes) |
| Voltam de férias — escritório de Campo Grande | Painel de Recursos Humanos - Fazendas | Gestão de Ferias | Filtro Filial = 11 - ESC. C. GRANDE; quem já começou as férias e volta hoje ou depois. Só nome curto (ex.: "Ivan M.") e a data de retorno |

## 3. Fontes fora do portal

> As cotações e o dólar aparecem na **faixa rolante do rodapé** (não são mais uma aba do carrossel). A faixa mostra de quando são as cotações e a hora da leitura.

| Informação | Fonte | Link | Frequência |
|---|---|---|---|
| Cotação boi, soja e milho — Diamantino e Sapezal | Agrolink | https://www.agrolink.com.br/regional/mt/diamantino/cotacoes | 3x ao dia (8h30, 12h30, 17h30) |
| Cotação — MT (média das praças do Imea) | Notícias Agrícolas / Imea | https://www.noticiasagricolas.com.br/cotacoes/ | 3x ao dia |
| Dólar | AwesomeAPI | https://economia.awesomeapi.com.br/json/last/USD-BRL | a cada 15 min |
| Chuva de ontem, 7 e 30 dias, previsão 5 dias | Open-Meteo (estimativa por modelo) | https://open-meteo.com | a cada 60 min |
| Radar de chuva | Windy | https://www.windy.com | a cada 10 min |
| Contorno e sede das fazendas | Arquivo KML do projeto talhões | `talhoes-distancias\dados\entrada.kml` | fixo |

## 4. Atualização

- **BIs:** coletor automático (tarefa do Windows) a cada 2 h, das 8h30 às 18h30. Ele clica em "Atualizar" no portal antes de ler cada BI e grava `bi.js` na pasta do SharePoint.
- **Painel:** relê os arquivos a cada 10 min. O rodapé fica vermelho ("DESATUALIZADO") se passar de 4h30 sem dado novo.
- **Idade do dado por aba:** cada assunto do carrossel mostra, ao lado do título, "dado de HH:MM · há N h". O coletor grava em `bi.js` a hora em que **cada fonte** foi lida (`fontes`). Laranja = passou de 4h30 (6 h nas cotações) dentro da janela de coleta (8h30 às 19h; fora dela não alerta); vermelho = a última leitura daquela fonte **falhou** (`falhas`) e o painel está mostrando o último valor bom.
- Se uma leitura falha, o coletor **mantém o último valor bom** daquela parte (com a hora antiga) em vez de apagar o número.
- A atualização do **Protheus → Power BI** é agendada no próprio serviço e não depende do coletor.

## 5. Fontes que existem, mas **não** são usadas

| BI | Motivo |
|---|---|
| Estoque (pasta PowerBI Celulares) | Versão de avaliação, desatualizada (soja 606 mil sc contra 2,7 mil sc reais). Substituído pelo Gerenciamento do Estoque |
| D-Lavro | Chuva medida com fator de conversão errado (valores ~7x maiores). Painel usa Open-Meteo até corrigirem |
