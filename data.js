// DADOS DE EXEMPLO. O coletor (a fazer) vai sobrescrever este arquivo a cada 10 minutos.
// Só quantidades: sem valores monetários.
window.DADOS = {
  exemplo: true,
  atualizadoEm: new Date().toISOString(),

  bovinos: {
    aguardandoAbate: { cabecas: 2041, lotes: 14, porFilial: [
      { filial: "Fazenda Tucano", cabecas: 1560 },
      { filial: "Fazenda Galheiro", cabecas: 481 }
    ]},
    mes: { negociado: 1668, embarcado: 1665, aEmbarcar: 14, abatidos: 1665 },
    cronograma: [
      { data: "12/11", frigorifico: "JBS S/A", cidade: "Diamantino", fazenda: "Tucano", cabecas: 450 },
      { data: "13/11", frigorifico: "Agra Agroindustrial", cidade: "Rondonópolis", fazenda: "Galheiro", cabecas: 500 },
      { data: "16/11", frigorifico: "JBS S/A", cidade: "Diamantino", fazenda: "Tucano", cabecas: 325 },
      { data: "18/11", frigorifico: "Falcão Indústria", cidade: "Juruena", fazenda: "Tucano", cabecas: 40 },
      { data: "20/11", frigorifico: "Agra Agroindustrial", cidade: "Rondonópolis", fazenda: "Galheiro", cabecas: 500 }
    ]
  },

  // Lista de produtos: o painel alterna entre eles (CFG.trocaProdutoSeg).
  // Para ter só um, use um único objeto em vez da lista.
  graos: [{
    safra: "2025/2026",
    produto: "Soja",
    contratadoSacas: 1250000,
    entregueSacas: 905000,
    // Um item por contrato de venda. entregueSacas vem da página "Saídas" do BI.
    contratos: [
      { ctr: "000309", fazenda: "Promissão", cliente: "Cargill", contratadoSacas: 165654, entregueSacas: 104654, vence: "30/11/2026" },
      { ctr: "000013", fazenda: "Nova Maringá", cliente: "Cofco", contratadoSacas: 54000, entregueSacas: 12000, vence: "05/12/2026" },
      { ctr: "000008", fazenda: "Galheiro", cliente: "Amaggi", contratadoSacas: 170000, entregueSacas: 50000, vence: "20/12/2026" },
      { ctr: "000004", fazenda: "Promissão", cliente: "Bunge", contratadoSacas: 100000, entregueSacas: 100000, vence: "15/09/2026" },
      { ctr: "000002", fazenda: "Promissão", cliente: "Bunge", contratadoSacas: 30000, entregueSacas: 21000, vence: "15/12/2026" },
      { ctr: "000012", fazenda: "Galheiro", cliente: "Cofco", contratadoSacas: 120000, entregueSacas: 66000, vence: "22/12/2026" },
      { ctr: "000005", fazenda: "Nova Maringá", cliente: "Cargill", contratadoSacas: 9480, entregueSacas: 4000, vence: "20/12/2026" }
    ],
    romaneiosHoje: { caminhoes: 38, toneladas: 1842 },
    romaneiosMes: [
      { dia: "05", ton: 1500 }, { dia: "06", ton: 1720 }, { dia: "07", ton: 1310 },
      { dia: "08", ton: 1900 }, { dia: "09", ton: 2050 }, { dia: "10", ton: 1780 }, { dia: "11", ton: 1842 }
    ]
  },
  {
    safra: "2025/2026 (2ª safra)",
    produto: "Milho",
    contratadoSacas: 480000,
    entregueSacas: 120000,
    contratos: [
      { ctr: "000021", fazenda: "Galheiro", cliente: "Cargill", contratadoSacas: 150000, entregueSacas: 60000, vence: "30/12/2026" },
      { ctr: "000022", fazenda: "Promissão", cliente: "Bunge", contratadoSacas: 90000, entregueSacas: 30000, vence: "15/01/2027" },
      { ctr: "000023", fazenda: "Nova Maringá", cliente: "Cofco", contratadoSacas: 60000, entregueSacas: 0, vence: "28/02/2027" }
    ],
    romaneiosHoje: { caminhoes: 12, toneladas: 540 }
  }],

  // Chuva MEDIDA, vinda do BI D-Lavro (média das estações com leitura de cada fazenda).
  // dado = último dia com leitura (aaaa-mm-dd). A previsão de 5 dias NÃO vem daqui: o painel
  // busca no Open-Meteo pelas coordenadas das sedes (fazendas.js).
  // chuvaAno = valores reais do BI em 11/11/2026 (Visão Geral, Ano 2026). chuvaDia/7d/Mês = EXEMPLO.
  clima: [
    { fazenda: "Galheiro",       dado: "2026-11-04", chuvaDia: 6,  chuva7d: 40, chuvaMes: 55, chuvaAno: 1590 },
    { fazenda: "Java",           dado: "2026-11-04", chuvaDia: 1,  chuva7d: 12, chuvaMes: 20, chuvaAno: 698 },
    { fazenda: "Mato Grosso",    dado: "2026-11-04", chuvaDia: 22, chuva7d: 60, chuvaMes: 80, chuvaAno: 1264 },
    { fazenda: "Panamá",         dado: "2026-11-04", chuvaDia: 3,  chuva7d: 18, chuvaMes: 30, chuvaAno: 1455 },
    { fazenda: "Ponte de Pedra", dado: "2026-11-04", chuvaDia: 1,  chuva7d: 10, chuvaMes: 18, chuvaAno: 938 },
    { fazenda: "Promissão",      dado: "2026-11-04", chuvaDia: 2,  chuva7d: 14, chuvaMes: 25, chuvaAno: 1008 },
    { fazenda: "Tucano",         dado: "2026-11-04", chuvaDia: 1,  chuva7d: 11, chuvaMes: 19, chuvaAno: 873 }
  ],

  // Cotações de mercado (preço público, não é valor de contrato). VALORES DE EXEMPLO.
  // Uma linha por produto; "valores" na mesma ordem de "pracas". var = variação do dia em %.
  mercado: {
    pracas: ["Diamantino", "Sapezal", "MT (Imea)"],
    linhas: [
      { produto: "Boi gordo", unidade: "@",  valores: [{ valor: "000,00", var: 0.4 },  { valor: "000,00", var: 0.2 },  { valor: "000,00", var: 0.3 }] },
      { produto: "Soja",      unidade: "sc", valores: [{ valor: "000,00", var: -0.3 }, { valor: "000,00", var: -0.1 }, { valor: "000,00", var: 0.0 }] },
      { produto: "Milho",     unidade: "sc", valores: [{ valor: "00,00",  var: 0.5 },  { valor: "00,00",  var: 0.5 },  { valor: "00,00",  var: -0.2 }] }
    ]
  },

  avisos: [
    "Bovinos e grãos: lidos dos BIs às 7h e 13h (quantidades, sem valores).",
    "Cotações: Agrolink (Diamantino, Sapezal) e Imea (média das praças de MT). Chuva: estimativa por modelo."
  ]
};
