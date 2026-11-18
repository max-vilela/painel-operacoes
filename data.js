// Base do painel. Os NÚMEROS não ficam aqui: vêm dos arquivos gerados pelo coletor
//   bi.js       (bovinos, grãos, estoques, plantio, colheita, funcionários, mortes; coletor/coletor.py)
//   mercado.js  (cotações; coletor/cotacoes.py)
// Se um desses arquivos faltar, o painel mostra "sem leitura" no bloco, nunca um valor inventado.
// Aqui ficam só os dados que não vêm de BI.
window.DADOS = {
  atualizadoEm: null,          // preenchido pelo painel com a hora do bi.js

  bovinos: { mes: {}, cronograma: [] },
  graos: [],

  // Chuva MEDIDA do BI D-Lavro (hoje DESLIGADA: CFG.fonteChuva = "openmeteo" no index.html, porque o BI
  // vem com os valores ~7x maiores). Formato, se for religada, uma linha por fazenda:
  //   { fazenda: "Galheiro", dado: "2026-11-04", chuvaDia: 6, chuva7d: 40, chuvaMes: 55, chuvaAno: 1590 }
  clima: [],

  mercado: { pracas: ["Diamantino", "Sapezal", "MT (Imea)"], linhas: [] }
};
