/* Painel de Operações: lógica. Script comum (NÃO módulo) carregado no fim de index.html, para funcionar
   aberto direto da pasta (file://). Dados: data.js, bi.js (coletor) e mercado.js, lidos a cada CFG.dadosMin. */
/* ============================================================
   CONFIGURAÇÃO: intervalo de atualização de cada bloco (minutos)
   Ajuste aqui conforme o ritmo real de cada fonte.
   ============================================================ */
const CFG = {
  dadosMin: 10,        // relê data.js e bi.js (arquivos LOCAIS: custa quase nada). Quem pesa é o coletor.
  radarZoomLargo: 6,   // zoom do radar enquanto uma aba larga (compras) deixa o mapa estreito: assim todas as fazendas continuam à vista
  radarMin: 10,        // recarrega o mapa de radar
  previsaoMin: 60,     // previsão de chuva 5 dias (Open-Meteo)
  climaAtrasoDias: 1,  // chuva medida mais velha que isso fica em laranja ("há N d")
  relogioSeg: 1,
  carrosselSeg: 20,        // tempo de cada assunto no bloco da direita (bovinos, grãos, estoques, mercado)
  embarquesNaTela: 12,    // máximo de DIAS de embarque do mês listados no assunto Bovinos; o que passar disso entra na linha "+ N dias"
  contratosNaTela: 9,      // máximo de contratos com saldo listados no assunto Grãos (vencimento mais próximo primeiro); passou disso, o título avisa quantos faltam
  janelaColeta: ["08:30", "19:00"],  // fora dessa janela o painel NÃO acusa atraso (à noite não há coleta)
  marqueePxSeg: 80,        // velocidade da faixa de cotações, em px/s numa tela de 1080 de altura (escala com a tela)
  atrasoMercadoMin: 360,   // cotações são lidas 3x ao dia (8h30, 12h30, 17h30): atraso acima de 6 h
  alertaAtrasoMin: 270, // coletor roda a cada 2 h, das 8h30 às 18h30; passou de 4,5 h sem BI novo, fica vermelho (à noite fica, é esperado)
  radarZoom: 7,            // zoom do mapa (inteiro). 7 = todas as fazendas; 8 aproxima mais
  ordemFazendas: ["Tucano", "Java", "Ponte de Pedra", "Promissão", "Galheiro", "Panamá", "Mato Grosso"],   // ordem dos cartões de chuva
  dolarMin: 15,       // cotação do dólar (AwesomeAPI, pública); se falhar, mantém o último valor e fica laranja
  compraResiduoPct: 5,   // pedido com saldo <= X% do total é 'resíduo': candidato a ser zerado manualmente (aba Compras)
  fonteChuva: "openmeteo"  // "openmeteo" = estimativa por modelo (sempre atual) | "dlavro" = medida do BI (atrasada)
};

const $ = id => document.getElementById(id);
const fmt = n => n.toLocaleString("pt-BR");

/* ---- helpers de transição ---- */
const reduzir = matchMedia("(prefers-reduced-motion: reduce)").matches;
// Troca o HTML só se mudou; o que estava na tela sai em fade e o novo entra em cascata (classe .entra no contêiner).
function setHtmlSuave(el, html){
  if(el._h === html) return;                                    // nada mudou (ex.: recarga de dados): não pisca
  if(reduzir || el._h === undefined){ el._h = html; el.innerHTML = html; return; }
  el.classList.add("sai");
  setTimeout(() => { el._h = html; el.innerHTML = html; el.classList.remove("sai"); }, 280);
}
// Texto simples com o mesmo fade.
function setTextoSuave(el, txt){
  if(el.textContent === txt) return;
  el.classList.add("suave");
  if(reduzir){ el.textContent = txt; return; }
  el.classList.add("sai");
  setTimeout(() => { el.textContent = txt; el.classList.remove("sai"); }, 280);
}
// Número que "conta" até o novo valor (na primeira vez, de 0). Valor nulo vira traço.
function setNum(id, v, formato = fmt){
  const el = $(id);
  if(v == null || isNaN(v)){ el.textContent = "–"; el._n = undefined; return; }
  const de = el._n ?? 0; el._n = v;
  cancelAnimationFrame(el._raf);
  if(reduzir || de === v){ el.textContent = formato(v); return; }
  const t0 = performance.now(), dur = 900;
  const passo = t => {
    const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
    el.textContent = formato(Math.round(de + (v - de) * e));
    if(k < 1) el._raf = requestAnimationFrame(passo);
  };
  el._raf = requestAnimationFrame(passo);
}

/* ---------- MAPA: radar do Windy (iframe) + contornos das fazendas desenhados por cima ---------- */
const COR = { "Tucano":"#ffd24a","Galheiro":"#35d07f","Promissão":"#ff9f43","Nova Maringá":"#59c3ff",
              "Java":"#c792ea","Mato Grosso":"#ff6b9a","Panamá":"#7fe0d0","Ponte de Pedra":"#f4f4a0" };
let mapa, rotulos = {}, centroMapa = null;

function centroDasFazendas(){
  const s = (window.FAZENDAS && window.FAZENDAS.sedes) || [];
  if(!s.length) return { lat: -14.4, lon: -56.9 };
  const lats = s.map(x => x.lat), lons = s.map(x => x.lon);
  return { lat: (Math.min(...lats) + Math.max(...lats)) / 2, lon: (Math.min(...lons) + Math.max(...lons)) / 2 };
}

function iniciarMapa(){
  if(mapa || typeof L === "undefined") return;
  centroMapa = centroDasFazendas();
  // Este Leaflet é transparente e fica sobre o Windy: só desenha as fazendas, com o MESMO
  // centro e zoom do Windy para os dois ficarem alinhados.
  mapa = L.map("mapa", { zoomControl:false, attributionControl:false, dragging:false, scrollWheelZoom:false,
    doubleClickZoom:false, boxZoom:false, keyboard:false, touchZoom:false, zoomSnap:1, preferCanvas:true })
    .setView([centroMapa.lat, centroMapa.lon], CFG.radarZoom, { animate:false });
  const F = window.FAZENDAS; if(!F) return;
  L.geoJSON(F.talhoes, {
    style: f => { const c = COR[f.properties.fazenda] || "#fff"; return { color:c, fillColor:c, weight:1.6, opacity:1, fillOpacity:.5 }; }
  }).addTo(mapa);
  // Um ponto por sede + nome em texto simples. O lado do nome é escolhido para as fazendas
  // vizinhas (Java, Tucano, Ponte de Pedra) não se sobreporem.
  const LADO = { "Java":["bottom",[0,6]], "Tucano":["top",[0,-6]], "Ponte de Pedra":["right",[6,0]],
                 "Promissão":["bottom",[0,6]], "Panamá":["left",[-6,0]], "Mato Grosso":["bottom",[0,6]],
                 "Galheiro":["right",[6,0]] };
  F.sedes.forEach(s => {
    const [direction, offset] = LADO[s.fazenda] || ["top", [0, -6]];
    const cor = COR[s.fazenda] || "#fff";
    // halo translúcido + ponto grande com borda branca: a sede fica visível mesmo sobre o eco do radar
    L.circleMarker([s.lat, s.lon], { radius:14, weight:0, fillColor:cor, fillOpacity:.28, interactive:false }).addTo(mapa);
    rotulos[s.fazenda] = L.circleMarker([s.lat, s.lon], { radius:7, weight:2.5, color:"#fff", fillColor:cor, fillOpacity:1 })
      .bindTooltip(s.fazenda, { permanent:true, direction, offset:[offset[0] * 2.4, offset[1] * 2.4], className:"rotulo" }).addTo(mapa);
    rotulos[s.fazenda]._cor = cor;
  });
}

function atualizarRotulos(){
  Object.entries(rotulos).forEach(([nome, m]) => {
    let txt = nome;
    if(CFG.fonteChuva === "openmeteo" && modelo[nome]) txt = `${nome} <em>${modelo[nome].ontem} mm</em>`;
    else { const c = climaMedido.find(x => x.fazenda === nome); if(c) txt = `${nome} <em>${c.chuvaDia} mm</em>`; }
    m.setTooltipContent(txt);
    const el = m.getTooltip() && m.getTooltip().getElement();
    if(el) el.style.setProperty("--c", m._cor);      // faixa colorida da etiqueta = cor da fazenda
  });
}

// O radar mudou de tamanho: depois da transição do layout, recentra o contorno das fazendas e recarrega o Windy
// (que não se recentra sozinho ao ser redimensionado), para os dois continuarem alinhados.
let timerRadar = null, ultimoTamanhoMapa = "";
const zoomRadar = () => document.querySelector(".app").classList.contains("largo") ? CFG.radarZoomLargo : CFG.radarZoom;
function realinharRadar(){
  clearTimeout(timerRadar);
  timerRadar = setTimeout(() => {
    if(mapa && centroMapa){ mapa.invalidateSize({ animate:false }); mapa.setView([centroMapa.lat, centroMapa.lon], zoomRadar(), { animate:false }); }
    renderRadar();
  }, 500);
}
// Reage ao tamanho REAL do quadro do radar (e não a um tempo fixo): quando a transição do layout termina e o tamanho
// muda, o contorno das fazendas e o Windy são refeitos com o mesmo centro e zoom.
(function(){
  const quadro = document.querySelector(".map");
  if(!quadro || typeof ResizeObserver === "undefined") return;
  new ResizeObserver(() => {
    const t = Math.round(quadro.clientWidth) + "x" + Math.round(quadro.clientHeight);
    if(!quadro.clientWidth){ ultimoTamanhoMapa = "0"; return; }   // radar escondido (aba cheia): refaz quando voltar
    if(ultimoTamanhoMapa && t !== ultimoTamanhoMapa) realinharRadar();
    ultimoTamanhoMapa = t;
  }).observe(quadro);
})();

function renderRadar(){
  iniciarMapa();
  const c = centroMapa || centroDasFazendas();
  $("radar").src = `https://embed.windy.com/embed2.html?lat=${c.lat.toFixed(4)}&lon=${c.lon.toFixed(4)}&zoom=${zoomRadar()}`
    + `&level=surface&overlay=radar&menu=&message=&marker=&calendar=now&type=map&location=coordinates&detail=`
    + `&metricWind=km%2Fh&metricTemp=%C2%B0C&radarRange=-1&t=${Date.now()}`;
  $("radarAtual").textContent = "Windy · recarregado " + new Date().toLocaleTimeString("pt-BR",{hour:"2-digit",minute:"2-digit"});
}

/* ---------- CHUVA: estimativa por modelo (Open-Meteo) ou medida do D-Lavro (via data.js) ---------- */
let climaMedido = [], modelo = {};
const fmtDia = iso => iso.slice(8, 10) + "/" + iso.slice(5, 7);
const soma = a => Math.round(a.reduce((s, v) => s + (v || 0), 0));

async function buscarDolar(){
  try{
    const r = await fetch("https://economia.awesomeapi.com.br/json/last/USD-BRL", {cache:"no-store"});
    const q = (await r.json()).USDBRL;
    const v = parseFloat(q.bid), p = parseFloat(q.pctChange);
    $("dolarV").textContent = "R$ " + v.toLocaleString("pt-BR", {minimumFractionDigits:2, maximumFractionDigits:2});
    $("dolarVar").className = p > 0 ? "up" : p < 0 ? "down" : "flat";
    $("dolarVar").textContent = (p > 0 ? "▲ " : p < 0 ? "▼ " : "") + Math.abs(p).toLocaleString("pt-BR", {minimumFractionDigits:2, maximumFractionDigits:2}) + "%";
    window.__dolar = { v, p };
    desenharMarquee();
    $("dolar").classList.remove("velho");
    $("dolar").title = "Dólar comercial, atualizado em " + q.create_date + " (AwesomeAPI)";
  }catch(e){ $("dolar").classList.add("velho"); }   // sem internet: mantém o último valor, em laranja
}

async function buscarModelo(){
  const sedes = (window.FAZENDAS && window.FAZENDAS.sedes) || [];
  if(!sedes.length) return;
  try{
    const url = "https://api.open-meteo.com/v1/forecast?daily=precipitation_sum&past_days=30&forecast_days=5&timezone=America%2FCuiaba"
      + "&latitude=" + sedes.map(s => s.lat).join(",") + "&longitude=" + sedes.map(s => s.lon).join(",");
    let j = await (await fetch(url)).json();
    if(!Array.isArray(j)) j = [j];
    j.forEach((r, i) => {
      const v = r.daily.precipitation_sum, t = r.daily.time, h = v.length - 5;   // h = índice de hoje
      modelo[sedes[i].fazenda] = { ontem: Math.round(v[h - 1]), d7: soma(v.slice(h - 7, h)), d30: soma(v.slice(h - 30, h)),
                                   prev: v.slice(h).map(x => Math.round(x)), datas: t.slice(h) };
    });
    desenharClima(); atualizarRotulos();
  }catch(e){ /* mantém o último resultado; se nunca houve, o cartão mostra "sem dados" */ }
}

function desenharClima(){
  const hoje = new Date(); hoje.setHours(0,0,0,0);
  const usaModelo = CFG.fonteChuva === "openmeteo";
  const ordem = nome => { const i = CFG.ordemFazendas.indexOf(nome); return i < 0 ? 99 : i; };   // fora da lista vai para o fim
  const fazendas = (usaModelo ? Object.keys(modelo) : climaMedido.map(c => c.fazenda)).sort((a, b) => ordem(a) - ordem(b));
  setHtmlSuave($("chuva"), fazendas.map((nome, k) => {
    const m = modelo[nome];
    const prev = m && m.prev, max = prev ? Math.max(10, ...prev) : 10;
    const barras = prev ? prev.map((mm, i) => {
      const dia = i === 0 ? "hoje" : new Date(m.datas[i] + "T12:00:00").toLocaleDateString("pt-BR", { weekday:"short" }).replace(".", "");
      return `<div><em>${mm}</em><i style="--i:${i};height:${Math.max(2, mm / max * 80)}%"></i><span>${dia}</span></div>`;
    }).join("") : `<div style="color:var(--muted);font-size:calc(1.4*var(--u));justify-content:center">sem previsão</div>`;

    // Cartão enxuto: nome, o valor principal em destaque (ontem) e os acumulados em coluna, mais as barras da previsão.
    let cab = "", principal = null, acum = [];
    if(usaModelo){
      if(m){ principal = ["ontem", m.ontem]; acum = [["7 d", m.d7], ["30 d", m.d30]]; }
    } else {
      const f = climaMedido.find(c => c.fazenda === nome);
      const idade = Math.round((hoje - new Date(f.dado + "T00:00:00")) / 86400000), velho = idade > CFG.climaAtrasoDias;
      cab = `<span class="dado ${velho ? "velho" : ""}">${fmtDia(f.dado)}${idade > 0 ? ` · há ${idade} d` : " · hoje"}</span>`;
      principal = ["no dia", f.chuvaDia]; acum = [["7 d", f.chuva7d], ["mês", f.chuvaMes], ["ano", f.chuvaAno]];
    }
    // Cartão baixo: nome + chuva de ontem na mesma linha, acumulados numa linha, previsão em barrinhas.
    const ont = principal ? `<span class="ont" title="${principal[0]}"><em>${principal[1]}</em>mm</span>` : `<span class="ont">sem dados</span>`;
    const ac = acum.map(([r, v]) => `${r} <b>${v}</b>`).join(" · ");
    return `<div class="farm" style="--i:${k}"><div class="cab"><b>${nome}</b>${ont}</div><div class="ac">${ac}${cab ? " · " + cab : ""}</div><div class="bars">${barras}</div></div>`;
  }).join(""));
  $("chuvaNota").textContent = usaModelo ? "nº = ontem · barras = 5 dias · Open-Meteo" : "nº = último dia (D-Lavro)";
}

function render(d){
  $("exemploTag").innerHTML = d.semLeitura && d.semLeitura.length
    ? '<span class="tag">SEM LEITURA: ' + d.semLeitura.join(" · ") + '</span>' : "";

  const b = d.bovinos;
  // setNum: o número conta até o valor novo; dado que o coletor não trouxe aparece como traço.
  setNum("bEmb", b.mes.embarcado);
  setNum("bPend", b.mes.aEmbarcar ?? b.mes.pendenteEmbarque);
  setNum("bAbat", b.mes.abatidos);
  setNum("bEmbAno", b.mes.anoEmbarcado);
  setNum("bPendAno", b.mes.anoAEmbarcar);
  setNum("bAbatAno", b.mes.anoAbatidos);
  desenharEmbarques(b.cronograma || [], b.mes && b.mes.ref);

  desenharGraos(Array.isArray(d.graos) ? d.graos : [d.graos]);

  desenharMarquee();

  climaMedido = d.clima;
  desenharClima();

  atualizarRotulos();
}

// Próximos embarques: os N mais próximos; o resumo conta todos os programados.
function desenharEmbarques(embarques, refMes){
  const total = embarques.reduce((s, c) => s + c.cabecas, 0);
  $("embResumo").textContent = embarques.length ? `${embarques.length} programados · ${fmt(total)} cab.` : "nenhum programado";
  // Embarques do mês agrupados por dia (a soma bate com o cartão "A embarcar no mês"); o que é dos meses seguintes
  // entra numa linha só, para o total geral também fechar. refMes = "11/2026" (mês do cartão).
  const mm = refMes ? refMes.slice(0, 2) : null;
  const doMes = mm ? embarques.filter(c => c.data.slice(3, 5) === mm) : embarques;
  const depois = mm ? embarques.filter(c => c.data.slice(3, 5) !== mm) : [];
  const soma = a => a.reduce((s, c) => s + c.cabecas, 0);
  const nomeMes = n => ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"][+n - 1];
  const meses = [...new Set(depois.map(c => nomeMes(c.data.slice(3, 5))))].join("/");
  const dias = [];
  doMes.forEach(c => { const u = dias[dias.length - 1]; if(u && u.data === c.data) u.itens.push(c); else dias.push({ data: c.data, itens: [c] }); });
  const curto = c => c.frigorifico.split(" ")[0];           // "Agra Agroindustrial" -> "Agra"; a cidade só aparece se o mesmo frigorífico tem 2 cidades
  const cidades = {}; doMes.forEach(c => (cidades[curto(c)] ??= new Set()).add(c.cidade));
  let html = dias.slice(0, CFG.embarquesNaTela).map(d => `<div class="dia"><b class="d">${d.data}</b>
      <div class="its">${d.itens.map(c => `<span><em>${curto(c)}${cidades[curto(c)].size > 1 ? ` <i>${c.cidade}</i>` : ""}</em> ${c.fazenda} <b>${fmt(c.cabecas)}</b></span>`).join("")}</div>
      <b class="tt">${fmt(soma(d.itens))}</b></div>`).join("");
  if(dias.length > CFG.embarquesNaTela)
    html += `<div class="dia sum"><span class="d">+ ${dias.length - CFG.embarquesNaTela} dias</span><span></span><b class="tt">${fmt(soma(dias.slice(CFG.embarquesNaTela).flatMap(d => d.itens)))}</b></div>`;
  if(doMes.length)
    html += `<div class="dia tot"><b class="d">Total</b><span class="its">do mês · ${doMes.length} embarques em ${dias.length} dias</span><b class="tt">${fmt(soma(doMes))}</b></div>`;
  if(depois.length)
    html += `<div class="dia sum"><span class="d">Depois</span><span class="its">${meses} · ${depois.length} embarques</span><b class="tt">${fmt(soma(depois))}</b></div>`;
  setHtmlSuave($("bCrono"), html);
}

// Grãos: soja e milho lado a lado (safra mais recente de cada) + os contratos com saldo que vencem primeiro.
function desenharGraos(lista){
  if(!lista.length){ setHtmlSuave($("gCols"), `<div class="nota">Sem leitura dos contratos de grãos.</div>`); setHtmlSuave($("gContratos"), ""); $("gPag").textContent = ""; return; }
  const dm = iso => iso.split("-").reverse().slice(0, 2).join("/");
  setHtmlSuave($("gCols"), lista.map(g => {
    const saldo = g.contratadoSacas - g.entregueSacas;
    const pct = Math.min(100, Math.round(g.entregueSacas / g.contratadoSacas * 100));
    // Saída = aumento do total entregue entre coletas (coletor/estado.json).
    const sd = g.saida;
    const saida = !sd ? "–" : sd.hojeSacas ? `<b>${fmt(sd.hojeSacas)} sc</b> hoje` : sd.ultima ? `última <b>${dm(sd.ultima)}</b>` : "sem saída registrada";
    return `<div class="gcol">
      <div class="p"><b>${g.produto}</b><span>${g.safra} · contratado ${fmt(g.contratadoSacas)} sc</span></div>
      <div class="l">Saldo a entregar</div>
      <div class="v">${fmt(saldo)}<small>sc</small></div>
      <div class="bar"><i style="width:${pct}%"></i></div>
      <div class="m"><span><b>${fmt(g.entregueSacas)}</b> sc entregues</span><span>${saida}</span></div>
    </div>`;
  }).join(""));
  const venc = s => s.split("/").reverse().join("");   // "dd/mm/aaaa" -> "aaaammdd"
  const abertos = lista.flatMap(g => g.contratos.map(c => ({ ...c, produto: g.produto })))
    .filter(c => c.contratadoSacas - c.entregueSacas > 0)
    .sort((a, b) => ((b.entregueSacas > 0) - (a.entregueSacas > 0))                                  // 1º: quem já teve saída fica no topo
      || (a.contratadoSacas - a.entregueSacas) - (b.contratadoSacas - b.entregueSacas)              // 2º: menor saldo (mais perto de concluir)
      || venc(a.vence).localeCompare(venc(b.vence)) || a.ctr.localeCompare(b.ctr));                 // empate: vencimento, depois código
  $("gContratos").classList.toggle("denso", abertos.length > 8);   // muitos contratos: tira a barrinha para caberem   // muitos contratos: tira a barrinha para caberem
  $("gPag").textContent = !abertos.length ? "" : abertos.length > CFG.contratosNaTela ? `mostrando ${CFG.contratosNaTela} de ${abertos.length} em aberto` : `${abertos.length} em aberto`;
  setHtmlSuave($("gContratos"), abertos.length ? abertos.slice(0, CFG.contratosNaTela).map(c => {
    const saldo = c.contratadoSacas - c.entregueSacas;
    const pct = Math.min(100, Math.round(c.entregueSacas / c.contratadoSacas * 100));
    return `<div class="ctr">
      <div class="t"><b>${c.ctr} · ${c.produto} · ${c.cliente}</b><span>${c.fazenda} · vence ${c.vence}</span></div>
      <div class="bar"><i style="width:${pct}%"></i></div>
      <div class="m"><span>${fmt(c.entregueSacas)} de ${fmt(c.contratadoSacas)} sc</span><span>saldo <em>${fmt(saldo)}</em> sc</span></div>
    </div>`;
  }).join("") : `<div class="nota">Nenhum contrato com saldo.</div>`);
}

/* ---------- ÍCONES: SVG embutidos (traço de 24x24, estilo Lucide), sem depender de internet ---------- */
const ICONES = {
  radar: '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
  boi: '<path d="M5 6.5 2 4.5M19 6.5l3-2"/><path d="M6 7.5C6 5.6 8.7 4 12 4s6 1.6 6 3.5V13c0 3.6-2.7 7-6 7s-6-3.4-6-7Z"/><circle cx="9.5" cy="10.5" r=".9"/><circle cx="14.5" cy="10.5" r=".9"/><path d="M9.5 16c1.6.8 3.4.8 5 0"/>',
  alerta: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  trigo: '<path d="M2 22 16 8"/><path d="M3.47 12.53 5 11l1.53 1.53a3.5 3.5 0 0 1 0 4.94L5 19l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z"/><path d="M7.47 8.53 9 7l1.53 1.53a3.5 3.5 0 0 1 0 4.94L9 15l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z"/><path d="M11.47 4.53 13 3l1.53 1.53a3.5 3.5 0 0 1 0 4.94L13 11l-1.53-1.53a3.5 3.5 0 0 1 0-4.94Z"/><path d="M20 2h2v2a4 4 0 0 1-4 4h-2V6a4 4 0 0 1 4-4Z"/><path d="M11.47 17.47 13 19l-1.53 1.53a3.5 3.5 0 0 1-4.94 0L5 19l1.53-1.53a3.5 3.5 0 0 1 4.94 0Z"/><path d="M15.47 13.47 17 15l-1.53 1.53a3.5 3.5 0 0 1-4.94 0L9 15l1.53-1.53a3.5 3.5 0 0 1 4.94 0Z"/><path d="M19.47 9.47 21 11l-1.53 1.53a3.5 3.5 0 0 1-4.94 0L13 11l1.53-1.53a3.5 3.5 0 0 1 4.94 0Z"/>',
  broto: '<path d="M7 20h10"/><path d="M10 20c5.5-2.5.8-6.4 3-10"/><path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z"/><path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/>',
  armazem: '<path d="M22 8.35V20a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8.35A2 2 0 0 1 3.26 6.5l8-3.2a2 2 0 0 1 1.48 0l8 3.2A2 2 0 0 1 22 8.35Z"/><path d="M6 18h12"/><path d="M6 14h12"/><rect width="12" height="12" x="6" y="10"/>',
  pessoas: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  pessoaOk: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/>',
  pessoaX: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="17" x2="22" y1="8" y2="13"/><line x1="22" x2="17" y1="8" y2="13"/>',
  ferias: '<path d="M13 8c0-2.76-2.46-5-5.5-5S2 5.24 2 8h2l1-1 1 1h4"/><path d="M13 7.14A5.82 5.82 0 0 1 16.5 6c3.04 0 5.5 2.24 5.5 5h-3l-1-1-1 1h-3"/><path d="M5.89 9.71c-2.15 2.15-2.3 5.47-.35 7.43l4.24-4.25.7-.7.71-.71 2.12-2.12c-1.95-1.96-5.27-1.8-7.42.35"/><path d="M11 15.5c.5 2.5-.17 4.5-1 6.5h4c2-5.5-.5-12-1-14"/>',
  alta: '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
  caminhao: '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>',
  agenda: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>',
  fabrica: '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M17 18h1"/><path d="M12 18h1"/><path d="M7 18h1"/>',
  lista: '<path d="M3 12h.01M3 18h.01M3 6h.01M8 12h13M8 18h13M8 6h13"/>',
  pino: '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
  contrato: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8M16 13H8M16 17H8"/>',
  bomba: '<line x1="3" x2="15" y1="22" y2="22"/><line x1="4" x2="14" y1="9" y2="9"/><path d="M14 22V4a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v18"/><path d="M14 13h2a2 2 0 0 1 2 2v2a2 2 0 0 0 2 2a2 2 0 0 0 2-2V9.83a2 2 0 0 0-.59-1.42L18 5"/>',
  chuva: '<path d="M4 14.9A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.24"/><path d="M16 14v6"/><path d="M8 14v6"/><path d="M12 16v6"/>',
  cantina: '<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"/>',
};
const svgIcone = n => ICONES[n] ? `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONES[n]}</svg>` : "";
document.querySelectorAll(".ico[data-i]").forEach(el => el.innerHTML = svgIcone(el.dataset.i));

/* ---------- CARROSSEL: troca o assunto do bloco da direita a cada CFG.carrosselSeg ---------- */
const slides = [...document.querySelectorAll(".slide")];
let slideAtual = -1;
// Bolinhas clicáveis: vão direto ao assunto e o tempo de troca recomeça a contar dali.
$("dots").innerHTML = slides.map(s => `<i role="button" tabindex="0" title="${s.dataset.titulo}" aria-label="Mostrar ${s.dataset.titulo}"></i>`).join("");
let relogioCarrossel = null;
function irPara(n){
  clearInterval(relogioCarrossel);
  slideAtual = (n - 1 + slides.length) % slides.length;   // proximoSlide avança 1
  proximoSlide();
  relogioCarrossel = setInterval(proximoSlide, CFG.carrosselSeg * 1000);
}
[...$("dots").children].forEach((d, i) => {
  d.addEventListener("click", () => irPara(i));
  d.addEventListener("keydown", e => { if(e.key === "Enter" || e.key === " "){ e.preventDefault(); irPara(i); } });
});
function proximoSlide(){
  const ant = slides[slideAtual];
  slideAtual = (slideAtual + 1) % slides.length;
  const s = slides[slideAtual];
  slides.forEach(x => { if(x !== s && x !== ant) x.classList.remove("on", "sai"); });
  if(ant && ant !== s){ ant.classList.remove("on"); ant.classList.add("sai"); setTimeout(() => ant.classList.remove("sai"), 650); }
  s.classList.add("on");
  const app = document.querySelector(".app"), largo = !!s.dataset.largo;          // abas largas (compras) espremem o radar
  app.classList.toggle("cheio", !!s.dataset.cheio);                               // aba cheia (vendas): o radar sai da tela
  if(app.classList.contains("largo") !== largo){
    app.classList.toggle("largo", largo);
  }
  setTextoSuave($("carTitulo"), s.dataset.titulo);
  atualizarIdade();
  $("carIco").innerHTML = svgIcone(s.dataset.ico);
  [...$("dots").children].forEach((d, i) => d.classList.toggle("on", i === slideAtual));
  const p = $("prog");                       // barrinha que enche até a próxima troca
  p.style.transition = "none"; p.style.width = "0";
  if(!reduzir) requestAnimationFrame(() => requestAnimationFrame(() => {
    p.style.transition = `width ${CFG.carrosselSeg}s linear`; p.style.width = "100%";
  }));
}

// Janela em que o coletor deve estar rodando (CFG.janelaColeta): fora dela, dado "velho" é esperado e não vira alarme.
function emJanelaDeColeta(){
  const [h1, m1] = CFG.janelaColeta[0].split(":").map(Number), [h2, m2] = CFG.janelaColeta[1].split(":").map(Number);
  const a = new Date(); const min = a.getHours() * 60 + a.getMinutes();
  return min >= h1 * 60 + m1 && min <= h2 * 60 + m2;
}
// "08:39 · há 2 h" (com "ontem"/dd/mm quando não é de hoje)
function textoIdade(iso){
  const d = new Date(iso), agora = new Date(), min = (agora - d) / 60000;
  const hm = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const dia0 = x => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const dias = Math.round((dia0(agora) - dia0(d)) / 86400000);
  const quando = dias === 0 ? hm : dias === 1 ? "ontem " + hm : d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) + " " + hm;
  const resto = Math.round(min % 60);
  const dur = min < 1 ? "agora" : min < 60 ? `há ${Math.round(min)} min` : min < 1440 ? `há ${Math.floor(min / 60)} h${resto ? " " + String(resto).padStart(2, "0") : ""}` : `há ${Math.floor(min / 1440)} d`;
  return { quando, dur, min };
}
// De que fonte vem cada assunto do carrossel (a idade mostrada é a da fonte MAIS ANTIGA do assunto)
const FONTE_ABA = { sVendas: ["graos", "bovinos"], sMortes: ["mortes"], sPlant: ["plantio", "colheita"],
                    sEst: ["estoque", "graos"], sCompras: ["compras"], sFrota: ["ativos"], sInvest: ["investimentos"], sRH: ["rh"] };
const ROTULO_FONTE = { bovinos: "bovinos", graos: "grãos", estoque: "estoques", rh: "funcionários", plantio: "plantio",
                       colheita: "colheita", mortes: "mortes", compras: "compras", ativos: "máquinas e ativos", investimentos: "investimentos", mercado: "cotações" };
function atualizarIdade(){
  const el = $("idade"), aba = slides[slideAtual], d = window.DADOS;
  if(!el || !aba || !d) return;
  const chaves = FONTE_ABA[aba.id] || [];
  const datas = chaves.map(k => d.fontes && d.fontes[k]).filter(Boolean);
  const falhou = chaves.some(k => (d.falhas || []).includes(k));
  if(!datas.length){ el.textContent = "sem leitura"; el.className = "idade ruim"; return; }
  const mais = datas.reduce((a, b) => new Date(a) < new Date(b) ? a : b);
  const { quando, dur, min } = textoIdade(mais);
  const limite = CFG.alertaAtrasoMin;
  const velho = emJanelaDeColeta() && min > limite;
  el.className = "idade" + (falhou ? " ruim" : velho ? " velho" : "");
  el.textContent = (falhou ? "leitura falhou · " : "") + "dado de " + quando + " · " + dur;
  el.title = (falhou ? "A última leitura desta fonte falhou: o painel mostra o último valor bom. " : "") + "Fonte: " + chaves.map(k => ROTULO_FONTE[k]).join(" + ");
}

function atualizarStatus(){
  const d = window.DADOS; if(!d) return;
  atualizarIdade();
  if(!d.atualizadoEm){
    $("dot").className = "dot stale"; $("upd").className = "stale"; $("upd").textContent = "sem dados do BI"; return;
  }
  const idade = (Date.now() - new Date(d.atualizadoEm).getTime()) / 60000;
  const stale = emJanelaDeColeta() && idade > CFG.alertaAtrasoMin;
  const falhas = (d.falhas || []).map(k => ROTULO_FONTE[k]);
  $("dot").className = "dot" + (stale || falhas.length ? " stale" : "");
  $("upd").className = stale || falhas.length ? "stale" : "ok";
  $("upd").textContent = "BI de " + new Date(d.atualizadoEm).toLocaleTimeString("pt-BR",{hour:"2-digit",minute:"2-digit"})
    + (stale ? " · DESATUALIZADO" : "") + (falhas.length ? " · leitura falhou: " + falhas.join(", ") : "");
}

function carregarScript(src){
  return new Promise(ok => {
    const s = document.createElement("script");
    s.src = src + "?t=" + Date.now();
    s.onload = () => { s.remove(); ok(true); };
    s.onerror = () => { s.remove(); ok(false); };
    document.head.appendChild(s);
  });
}

/* data.js = base (só o que não vem de BI). bi.js = coletor (bovinos, grãos, estoques, RH, plantio, colheita, mortes).
   mercado.js = cotações. Se um deles faltar, o bloco fica "sem leitura"; nunca entra valor de exemplo. */
async function carregarDados(){
  window.DADOS_BI = undefined;
  if(!await carregarScript("data.js")){ atualizarStatus(); return; }   // mantém o último valor na tela
  const bi = (await carregarScript("bi.js")) ? window.DADOS_BI : null;
  const d = window.DADOS;
  d.semLeitura = [];
  // mercado.js: gerado por coletor/cotacoes.py (fontes públicas, sem login)
  window.DADOS_MERCADO = undefined;
  if(await carregarScript("mercado.js") && window.DADOS_MERCADO) d.mercado = window.DADOS_MERCADO; else d.semLeitura.push("cotações");
  const bb = (bi && bi.bovinos) || {};
  d.bovinos = { mes: bb.mes || {}, cronograma: bb.cronograma || [] };
  if(!bb.mes) d.semLeitura.push("bovinos");
  d.graos = (bi && bi.graos) || [];
  if(!d.graos.length) d.semLeitura.push("grãos");
  d.atualizadoEm = bi ? bi.atualizadoEm : null;
  d.deBi = !!bi;
  // Hora em que cada fonte foi lida pela última vez (coletor grava bi.fontes; coletas antigas: usa a hora geral)
  const f = (bi && bi.fontes) || {};
  d.fontes = {};
  ["bovinos", "graos", "estoque", "rh", "plantio", "colheita", "mortes", "compras", "ativos", "investimentos"].forEach(k => d.fontes[k] = f[k] || (bi && bi.atualizadoEm) || null);
  d.fontes.mercado = (d.mercado && d.mercado.atualizadoEm) || null;
  d.falhas = (bi && bi.falhas) || [];
  render(d); desenharFaixa(bi && bi.visao); atualizarStatus();
}

/* ---------- FAIXA de indicadores gerais (bi.visao, gerado pelo coletor) ----------
   Cada cartão: valor grande + uma linha de detalhe. Sem dado, fica traço (nunca exemplo). */
/* ---------- ESTOQUES: três blocos, cada um com UM número principal ----------
   Rebanho (faixa larga) · Soja e Milho (lado a lado) · Combustíveis (faixa larga). Detalhe só no que ajuda a decidir. */
const rotSafra = s => /^\d\d\/\d\d$/.test(s) ? "Safra " + s : s.charAt(0) + s.slice(1).toLowerCase();
function desenharEstoques(v){
  const el = $("estGrid"); if(!el) return;
  const ico = n => `<i class="ico">${svgIcone(n)}</i>`;
  const vazio = (titulo, icone, cor, cls = "") => `<section class="ec ${cls}" style="--c:${cor}"><h4>${ico(icone)}${titulo}</h4><span class="n sem">–</span><div class="nota">sem leitura</div></section>`;
  const pc = (a, b) => b ? Math.round(a / b * 100) : 0;

  // REBANHO: número + uma barra confinamento/pasto
  const r = v.rebanho;
  let reb = vazio("Rebanho", "boi", "#e6c84a", "full");
  if(r && r.total){
    const conf = r.confinamento || 0, pasto = r.total - conf, p1 = pc(conf, r.total);
    reb = `<section class="ec full" style="--c:#e6c84a"><h4>${ico("boi")}Rebanho</h4>
      <div class="linha"><span class="n">${fmt(r.total)}<small>cab.</small></span>
        <div class="comp"><div class="eb"><i style="width:${p1}%;background:#e6c84a"></i><i style="width:${100 - p1}%;background:#8a7a3a"></i></div>
          <div class="el"><div><small><i class="lg" style="--c:#e6c84a"></i>Confinamento</small><b>${fmt(conf)} <em>${p1}%</em></b></div>
            <div><small><i class="lg" style="--c:#8a7a3a"></i>Pasto</small><b>${fmt(pasto)} <em>${100 - p1}%</em></b></div></div></div></div></section>`;
  }

  // GRÃOS: número + barra negociado/livre + safras (discretas)
  const g = v.estoqueGraos || {};
  const grao = (nome, chave, cor) => {
    const e = g[chave];
    if(!e) return vazio(nome + " em estoque", "armazem", cor);
    const temNeg = e.negociado != null;
    const neg = temNeg ? Math.min(e.negociado, e.sacas) : 0, livre = e.sacas - neg, pn = pc(neg, e.sacas);
    const acima = temNeg && e.negociado > e.sacas;
    const negocio = temNeg ? `<div class="eb"><i style="width:${pn}%;background:#e8f5ec"></i><i style="width:${100 - pn}%;background:${cor}"></i></div>
      <div class="el"><div><small><i class="lg" style="--c:#e8f5ec"></i>Negociado</small><b>${fmt(e.negociado)} ${acima ? '<em class="alerta">acima do estoque</em>' : `<em>${pn}%</em>`}</b></div>
        <div><small><i class="lg" style="--c:${cor}"></i>Livre</small><b>${fmt(livre)} <em>${100 - pn}%</em></b></div></div>` : "";
    const safras = (e.porSafra || []).map(s => `<div><span>${rotSafra(s.safra)}</span><b>${fmt(s.sacas)}</b></div>`).join("");
    return `<section class="ec" style="--c:${cor}"><h4>${ico("armazem")}${nome} em estoque</h4>
      <span class="n">${fmt(e.sacas)}<small>sc</small></span>${negocio}<div class="safras">${safras}</div></section>`;
  };

  // COMBUSTÍVEIS: três números lado a lado (diesel em destaque)
  const c = v.combustivel || {};
  let comb = vazio("Combustíveis", "bomba", "#59c3ff", "full");
  if(c.diesel != null){
    const tile = (nome, val, grande) => `<div class="${grande ? "t1" : "t2"}"><small>${nome}</small><span class="n">${val == null ? "–" : fmt(val)}<small>L</small></span></div>`;
    comb = `<section class="ec full" style="--c:#59c3ff"><h4>${ico("bomba")}Combustíveis</h4>
      <div class="tiles">${tile("Diesel", c.diesel, true)}${tile("Gasolina", c.gasolina)}${tile("Etanol", c.etanol)}</div></section>`;
  }
  setHtmlSuave(el, reb + grao("Soja", "soja", "#35d07f") + grao("Milho", "milho", "#f2b33d") + comb);
}

function desenharFaixa(v){
  v = v || {};
  const r = v.rebanho;
  $("bReb").innerHTML = r ? `Rebanho atual <b>${fmt(r.total)}</b> cabeças · confinamento <b>${fmt(r.confinamento)}</b> · pasto <b>${fmt(r.total - r.confinamento)}</b>` : "";
  desenharEstoques(v);
  desenharPlantio(v.plantio, v.colheita || {});
  desenharRH(v.rh);
  desenharMortes(v.mortes);
  desenharCompras(v.compras);
  desenharFrota(v.ativos);
  desenharInvest(v.investimentos);
}

const fmt1 = n => n.toLocaleString("pt-BR", { minimumFractionDigits:1, maximumFractionDigits:1 });
const safraCurta = s => (s || "").toLowerCase().replace("safra", "").replace(/\s+/g, " ").trim();   // "SOJA SAFRA 26/27" -> "soja 26/27"
const ordemFaz = nome => { const i = CFG.ordemFazendas.indexOf(nome); return i < 0 ? 99 : i; };
// Barras horizontais: [{nome, partes:[{v, cor}], rotulo}] escaladas pelo maior total.
function barras(el, itens){
  const max = Math.max(1, ...itens.map(x => x.partes.reduce((s, p) => s + p.v, 0)));
  setHtmlSuave(el, itens.map(x => `<div class="r"><span>${x.nome}</span><div class="t">${
    x.partes.map(p => `<i style="width:${p.v / max * 100}%;--c:${p.cor || "var(--accent)"}"></i>`).join("")}</div><b>${x.rotulo}</b></div>`).join(""));
}

/* ---------- PLANTIO E COLHEITA: safra em plantio + última colheita de soja e milho, por fazenda ---------- */
function desenharPlantio(p, col){
  const el = $("plGrid"); if(!el) return;
  col = col || {};
  // plantio por cultura {soja, milho}; bi.js antigo trazia um plantio só (soja)
  p = p || {};
  const plt = (p.soja || p.milho) ? p : (p.planejadoHa ? { soja: p } : {});
  const ico = n => `<i class="ico">${svgIcone(n)}</i>`;
  const vazio = (titulo, icone, cor) => `<section class="ec" style="--c:${cor}"><h4>${ico(icone)}${titulo}</h4><span class="n sem">–</span><div class="nota">sem leitura</div></section>`;
  // "SOJA SAFRA 26/27" -> "safra 26/27"; "MILHO SAFRINHA 26/26" -> "safrinha 26"
  const tag = r => { const t = safraCurta(r || "").replace(/^(soja|milho)\s+/i, "").replace(/(\d\d)\/\1$/, "$1"); return /^\d/.test(t) ? "safra " + t : t; };

  // PLANTIO da safra mais recente da cultura: um número (% concluído) + barra; só nomeia fazenda se ainda faltar plantar
  const cardPlantio = (d, cor) => {
    if(!d || !d.planejadoHa) return vazio("Plantio", "broto", cor);
    const pct = Math.min(100, Math.round(d.plantadoHa / d.planejadoHa * 100));
    const faltam = (d.fazendas || []).filter(f => f.plantadoHa < f.planejadoHa - 0.5)
      .sort((a, b) => (b.planejadoHa - b.plantadoHa) - (a.planejadoHa - a.plantadoHa));
    const estado = faltam.length
      ? "Faltam: " + faltam.slice(0, 2).map(f => `${f.fazenda} <b>${fmt(Math.round(f.planejadoHa - f.plantadoHa))}</b>`).join(" · ") + (faltam.length > 2 ? ` · +${faltam.length - 2}` : "") + " ha"
      : `Todas as ${(d.fazendas || []).length} fazendas concluídas`;
    return `<section class="ec" style="--c:${cor}"><h4>${ico("broto")}Plantio · ${tag(d.safra)}</h4>
      <div class="linha1"><span class="n">${pct}<small>%</small></span><span class="sub">${fmt(Math.round(d.plantadoHa))} de ${fmt(Math.round(d.planejadoHa))} ha</span></div>
      <div class="eb"><i style="width:${pct}%;background:${cor}"></i></div>
      <div class="pst ${faltam.length ? "pend" : "ok"}">${estado}</div></section>`;
  };

  // COLHEITA da safra mais recente que já tem área colhida: sc/ha em destaque + ranking das fazendas
  // (linha branca = média da cultura; barra clara = abaixo da média)
  const cardColheita = (d, cor) => {
    if(!d) return vazio("Colheita", "trigo", cor);
    const fz = [...(d.fazendas || [])].sort((a, b) => b.scHa - a.scHa);
    const max = Math.max(...fz.map(f => f.scHa), d.scHa);
    const linhas = fz.map(f => `<div class="pr"><span>${f.fazenda}</span>
      <div class="pt"><i class="${f.scHa >= d.scHa ? "" : "baixo"}" style="width:${f.scHa / max * 100}%"></i><u style="left:${d.scHa / max * 100}%"></u></div>
      <b>${fmt1(f.scHa)}</b></div>`).join("");
    return `<section class="ec" style="--c:${cor}"><h4>${ico("trigo")}Colheita · ${tag(d.safra)}</h4>
      <div class="linha1"><span class="n">${fmt1(d.scHa)}<small>sc/ha</small></span><span class="sub">${fmt(d.sacas)} sc em ${fmt(Math.round(d.areaHa))} ha</span></div>
      <div class="prs">${linhas}</div>
      <div class="leg"><u></u>média · barra clara = abaixo</div></section>`;
  };

  // grade de 2 colunas e 3 linhas (título | plantio | colheita): soja e milho alinhados linha a linha
  const cab = (nome, cor) => `<div class="chd" style="--c:${cor}">${nome}</div>`;
  const S = "#35d07f", M = "#f2b33d";
  setHtmlSuave(el, cab("Soja", S) + cab("Milho", M) + cardPlantio(plt.soja, S) + cardPlantio(plt.milho, M) + cardColheita(col.soja, S) + cardColheita(col.milho, M));
}

/* ---------- FUNCIONÁRIOS: só contagens ---------- */
function desenharRH(h){
  if(!h){ ["rAt", "rFe", "rAf"].forEach(id => setNum(id, null)); return; }
  setNum("rAt", h.ativos); setNum("rFe", h.ferias); setNum("rAf", h.afastados);
  $("rTot").innerHTML = `quadro total <b>${fmt(h.total)}</b>`;
  // férias do escritório de Campo Grande (coletor: visao.rh.retornosCG / entramCG; só nome curto e data)
  const dm = iso => iso === new Date().toISOString().slice(0, 10) ? "hoje" : iso.slice(8, 10) + "/" + iso.slice(5, 7);
  const linhasF = (lista, campo, vazio) => lista.length
    ? lista.slice(0, 4).map(r => `<div class="ret"><span>${r.nome}</span><b>${dm(r[campo])}</b></div>`).join("")
    : `<div class="ret vazio">${vazio}</div>`;
  const temF = h.retornosCG || h.entramCG;
  $("rRetT").style.display = temF ? "" : "none"; $("rRets").style.display = temF ? "" : "none";
  setHtmlSuave($("rRet"), linhasF(h.retornosCG || [], "retorno", "ninguém em férias"));
  setHtmlSuave($("rEnt"), linhasF(h.entramCG || [], "inicio", "ninguém nos próximos 60 dias"));
  $("rAso").innerHTML = h.exames && h.exames.vencidos != null ? `exames (ASO) vencidos <b>${h.exames.vencidos}</b>` : "";
  if(h.fazendas) barras($("rFaz"), h.fazendas.map(f => ({
    nome: f.fazenda, rotulo: fmt(f.ativos + f.ferias + f.afastados),
    partes: [{ v: f.ativos }, { v: f.ferias, cor: "var(--accent2)" }, { v: f.afastados, cor: "var(--warn)" }] })));
}

/* ---------- MORTES de bovinos: coluna do mês corrente | coluna do ano (BI Mortes) ----------
   Cada coluna: mortes, abate p/ cantina (à parte, nunca somado), principais causas e mortes por fazenda. */
const NOME_MES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
function colunaMortes(s, d, titulo){
  $("mT" + s).textContent = titulo;
  if(!d){ setNum("mTot" + s, null); setNum("mCan" + s, null); $("mMot" + s).innerHTML = ""; $("mFaz" + s).innerHTML = ""; return; }
  setNum("mTot" + s, d.total); setNum("mCan" + s, d.cantina);
  const causaCurta = s => s.split(" - ")[0].replace(" / ", "/").replace(/parasitaria/i, "parasitária").replace(/ bovina$/i, "");
  barras($("mMot" + s), (d.motivos || []).map(x => ({ nome: causaCurta(x.motivo), rotulo: fmt(x.qtd), partes: [{ v: x.qtd, cor: "var(--bad)" }] })));
  // todas as fazendas, na ordem do painel; quem não teve morte no período aparece com 0
  const por = Object.fromEntries((d.fazendas || []).map(f => [f.fazenda, f.mortes]));
  barras($("mFaz" + s), CFG.ordemFazendas.map(n => ({ nome: n, rotulo: fmt(por[n] || 0), partes: [{ v: por[n] || 0, cor: "#ff7a7a" }] })));
}
function desenharMortes(m){
  const mes = m && m.mes;
  colunaMortes("Mes", mes, mes ? NOME_MES[+mes.mes.slice(0, 2) - 1] + " " + mes.mes.slice(3) : "mês");
  colunaMortes("Ano", m, m ? "ano " + (m.ano || "") : "ano");
  const naoSeparou = (m && m.cantinaSeparada === false) || (mes && mes.cantinaSeparada === false);
  $("mNota").textContent = naoSeparou ? "atenção: parte da cantina não deu para separar por fazenda"
                                      : "cantina = abate para consumo, fora das mortes";
}

/* ---------- FAIXA DE COTAÇÕES (rodapé): dólar + boi, soja e milho por praça, rolando para a esquerda ---------- */
function desenharMarquee(){
  const el = $("marq"), box = $("marqBox"); if(!el || !box) return;
  const d = window.DADOS || {}, mk = d.mercado || { pracas: [], linhas: [] };
  const cls = v => v > 0 ? "up" : v < 0 ? "down" : "flat", seta = v => v > 0 ? "▲" : v < 0 ? "▼" : "■";
  const pct = v => Math.abs(v).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
  const praca = n => /^MT/i.test(n) ? "MT" : n;
  const itens = [];
  const dol = window.__dolar;
  if(dol) itens.push(`<span class="mi"><b>DÓLAR</b> <strong>R$ ${dol.v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong> <i class="${cls(dol.p)}">${seta(dol.p)} ${pct(dol.p)}</i></span>`);
  mk.linhas.forEach(l => itens.push(`<span class="mi"><b>${l.produto.toUpperCase()}</b> <small>R$/${l.unidade}</small>`
    + l.valores.map((v, i) => `<em>${praca(mk.pracas[i] || "")}</em> <strong>${v.valor}</strong> <i class="${cls(v.var)}">${seta(v.var)} ${pct(v.var)}</i>`).join("") + `</span>`));
  if(!mk.linhas.length) itens.push(`<span class="mi stale">Cotações indisponíveis no momento</span>`);
  else {
    // de quando são as cotações; laranja se a mais antiga tiver mais de 3 dias, ou se a leitura estiver atrasada
    const datas = mk.linhas.flatMap(l => l.valores.map(v => v.data)).filter(Boolean).sort();
    const velha = datas.length && (Date.now() - new Date(datas[0] + "T12:00:00")) / 86400000 > 3;
    const lida = mk.atualizadoEm ? textoIdade(mk.atualizadoEm) : null;
    const atrasada = lida && emJanelaDeColeta() && lida.min > CFG.atrasoMercadoMin;
    itens.push(`<span class="mi fonte${velha || atrasada ? " stale" : ""}">cotações${datas.length ? " de " + datas[0].split("-").reverse().slice(0, 2).join("/") : ""}${lida ? " · lidas às " + lida.quando.split(" ").pop() : ""} · Agrolink e Imea</span>`);
  }
  const grupo = itens.join('<span class="ms">◆</span>') + '<span class="ms">◆</span>';
  const u = Math.min(innerHeight / 100, innerWidth * 0.005625);
  const chave = grupo + "|" + box.clientWidth + "|" + Math.round(u);
  if(el._h === chave) return;                       // nada mudou: não reinicia a rolagem
  el._h = chave;
  el.style.animation = "none";
  el.innerHTML = `<span class="mg">${grupo}</span>`;  // um grupo só, para medir
  const k = Math.max(1, Math.ceil(box.clientWidth / Math.max(el.firstChild.getBoundingClientRect().width, 1)));
  const um = `<span class="mg">${grupo}</span>`.repeat(k);
  el.innerHTML = um + um;                            // duas metades iguais: o laço (-50%) emenda sem salto
  if(reduzir) return;
  const px = CFG.marqueePxSeg * (u / 10.8);
  el.style.animation = `marq ${(el.scrollWidth / 2 / px).toFixed(1)}s linear infinite`;
}
addEventListener("resize", () => { const el = $("marq"); if(el) el._h = null; desenharMarquee(); });

setInterval(() => {
  $("clock").textContent = new Date().toLocaleTimeString("pt-BR");
  atualizarStatus();
}, CFG.relogioSeg * 1000);
setInterval(carregarDados, CFG.dadosMin * 60000);
setInterval(renderRadar, CFG.radarMin * 60000);
setInterval(buscarModelo, CFG.previsaoMin * 60000);
setInterval(buscarDolar, CFG.dolarMin * 60000);
irPara(0);   // começa no primeiro assunto e liga a troca automática
renderRadar();
buscarModelo();
buscarDolar();
carregarDados();


/* ---------- COMPRAS: pedidos com saldo a receber, dos produtos acompanhados ---------- */
// Cada produto vira um cartão; dentro dele, os pedidos que ainda têm saldo, do mais perto de acabar para o mais cheio.
// Cor da barra = quanto do pedido ainda falta chegar: até 20% vermelho, até 50% amarelo, acima verde.
const CATEGORIAS_COMPRAS = ["Calcário dolomítico", "Gesso agrícola", "Gesso p/ nutrição animal", "Caroço de algodão", "Casquinha de algodão",
  "Farelo de algodão", "Farelo de soja", "DDG ouro", "DDG úmido", "DDG ALD", "Núcleo mineral", "Sementes", "Fertilizantes", "Óleo vegetal (adjuvante)"];
const UNID_COMPRAS = { "Óleo vegetal (adjuvante)": "L" };       // o resto vem em kg
const MAX_PEDIDOS_CARTAO = 4;
function qtdCompras(n, cat){      // quantidade em kg inteiros (ou L), sem converter para toneladas
  return fmt(Math.round(n)) + " " + (UNID_COMPRAS[cat] || "kg");
}
const nomeProduto = n => n.toLowerCase().split(" ").map(w => /\d/.test(w) || (w.length <= 3 && !["de", "do", "da", "e", "c", "p", "com"].includes(w)) ? w.toUpperCase() : w.length > 2 ? w[0].toUpperCase() + w.slice(1) : w).join(" ");
const reais = n => "R$ " + fmt(Math.round(n));
function desenharCompras(lista){
  const el = $("cpGrid"); if(!el) return;
  if(!Array.isArray(lista)){ setHtmlSuave(el, '<div class="nota">sem leitura</div>'); return; }
  const curto = f => f.replace(/(ltda|s\/a|sa|ind|industria|comercio|de|do|da|e)\.?/gi, " ").replace(/\s+/g, " ").trim().split(" ").slice(0, 3).join(" ");
  const porCat = {};
  lista.forEach(p => { p.pct = p.quantidade ? p.saldo / p.quantidade * 100 : 100; (porCat[p.categoria] = porCat[p.categoria] || []).push(p); });
  const nRes = c => porCat[c].filter(p => p.pct <= CFG.compraResiduoPct).length;
  const cats = Object.keys(porCat).sort((a, b) => (nRes(b) > 0) - (nRes(a) > 0) || Math.min(...porCat[a].map(p => p.pct)) - Math.min(...porCat[b].map(p => p.pct)));
  const cartao = cat => {
    const ps = porCat[cat].sort((a, b) => a.pct - b.pct), extra = ps.length - MAX_PEDIDOS_CARTAO;
    const linhas = ps.slice(0, MAX_PEDIDOS_CARTAO).map(p => {
      const res = p.pct <= CFG.compraResiduoPct;                 // resíduo: sobrou pouco, dá para zerar o pedido
      const cor = res ? "#59c3ff" : p.pct <= 20 ? "var(--bad)" : p.pct <= 50 ? "var(--warn)" : "var(--accent)";
      return `<div class="cpl${res ? " res" : ""}" title="${p.produto} · ${p.fornecedor} · pedido ${p.pedido}">
        <div class="cp1"><span class="cpf">${p.fazenda}</span><span class="cpn"><b>${nomeProduto(p.produto)}</b><small> · ${curto(p.fornecedor)} · </small><small class="cpp">${p.pedido}</small><small> · ${p.emissao.slice(0, 5)}</small></span></div>
        <div class="cp2"><div class="pt"><i style="width:${Math.max(2, Math.min(100, p.pct))}%;background:${cor}"></i></div>
        <b style="color:${cor}">${qtdCompras(p.saldo, cat)}<small> / ${fmt(Math.round(p.quantidade))}</small></b>
        <span class="cpv">${p.valorSaldo != null ? reais(p.valorSaldo) : "–"}</span></div></div>`;
    }).join("");
    const r = nRes(cat);
    return `<section class="cpc"><h4>${cat}${r ? `<span class="cpz">${r} p/ zerar</span>` : ""}</h4>${linhas}${extra > 0 ? `<div class="cpx">+${extra} pedido${extra > 1 ? "s" : ""} com saldo</div>` : ""}</section>`;
  };
  setHtmlSuave(el, cats.map(cartao).join("") || '<div class="nota">nenhum pedido com saldo</div>');
}


/* ---------- MÁQUINAS E ATIVOS (BI Ativo Fixo, 1 leitura por dia) ---------- */
const MAQUINAS = ["Tratores", "Colheitadeiras", "Pulverizadores", "Plantadeiras", "Plataformas", "Misturadores", "Distribuidores", "Implementos",
  "Maquinas Pesadas", "Caminhões", "Caminhonetes/Utilitários", "Onibus", "Motocicletas", "Aviões", "Geradores"];
const ROT_MAQ = { "Maquinas Pesadas": "Máquinas pesadas", "Caminhonetes/Utilitários": "Caminhonetes", "Onibus": "Ônibus" };
const TIPOS_TAB = ["Tratores", "Colheitadeiras", "Pulverizadores", "Plantadeiras", "Plataformas"];
const titulo = t => t.toLowerCase().replace(/(^|\s)(?!de|da|do|e)\S/g, c => c.toUpperCase());
function desenharFrota(a){
  const g = $("frGrid"); if(!g) return;
  if(!a || !a.tipos){ setHtmlSuave(g, '<div class="nota">sem leitura</div>'); setHtmlSuave($("frTab"), ""); return; }
  const q = Object.fromEntries(a.tipos.map(t => [t.nome, t.qtd]));
  const total = MAQUINAS.reduce((s, n) => s + (q[n] || 0), 0);
  const destaque = new Set(["Tratores", "Colheitadeiras", "Pulverizadores", "Plantadeiras"]);
  setHtmlSuave(g, `<div class="frT"><small>Máquinas, veículos e implementos</small><b>${fmt(total)}</b></div>` +
    MAQUINAS.filter(n => q[n] != null).map(n => `<div class="frC${destaque.has(n) ? " d" : ""}"><b>${fmt(q[n])}</b><span>${ROT_MAQ[n] || n}</span></div>`).join(""));
  const outros = Object.keys(q).filter(n => !MAQUINAS.includes(n)).sort((x, y) => q[y] - q[x]);
  $("frNota").textContent = outros.length ? "também no cadastro: " + outros.map(n => `${n.replace("Reservatorios/Poços", "Reservatórios/poços").replace(/Informática.*/, "Informática")} ${fmt(q[n])}`).join(" · ") : "";
  const fz = (a.porFilial || []).filter(f => !/escrit/i.test(f.filial));
  const cab = n => (ROT_MAQ[n] || n).replace("Colheitadeiras", "Colheit.").replace("Pulverizadores", "Pulveriz.").replace("Plantadeiras", "Plantad.");
  setHtmlSuave($("frTab"), fz.length ? `<div class="frL cab"><span></span>${TIPOS_TAB.map(n => `<b>${cab(n)}</b>`).join("")}</div>` +
    fz.map(f => `<div class="frL"><span>${titulo(f.filial.replace(/^FAZENDA /i, ""))}</span>${TIPOS_TAB.map(n => `<b>${f.tipos[n] != null ? fmt(f.tipos[n]) : "–"}</b>`).join("")}</div>`).join("") : '<div class="nota">sem leitura por fazenda</div>');
}

/* ---------- INVESTIMENTOS EM MELHORIAS DA FAZENDA (BI Investimentos, 1 leitura por dia; sem máquinas) ---------- */
const NOME_GRUPO = { "6001": "Armazéns, silos e galpões", "6003": "Cercas e currais", "6021": "Alojamentos", "6022": "Balanças", "6023": "Barracões",
  "6024": "Cantinas", "6025": "Casas de funcionários", "6028": "Edificações", "6036": "Posto de abastecimento", "6037": "Rede de comunicação", "6099": "Áreas de reg. ambiental" };
const reaisMi = n => n >= 1e6 ? "R$ " + (n / 1e6).toLocaleString("pt-BR", { maximumFractionDigits:2 }) + " mi" : n >= 1e3 ? "R$ " + fmt(Math.round(n / 1e3)) + " mil" : "R$ " + fmt(Math.round(n));
function desenharInvest(i){
  const k = $("ivK"); if(!k) return;
  if(!i || !i.grupos){ setHtmlSuave(k, '<div class="nota">sem leitura</div>'); return; }
  const pct = i.total ? Math.round(i.melhoriasValor / i.total * 100) : null;
  setHtmlSuave(k, `<div class="ivk"><small>Investido em melhorias · ${i.ano}</small><b>${reaisMi(i.melhoriasValor)}</b></div>
    <div class="ivk"><small>Obras e benfeitorias</small><b>${fmt(i.melhoriasObras)}</b></div>
    <div class="ivk"><small>Do investimento total do ano</small><b>${pct != null ? pct + "%" : "–"}</b></div>`);
  const max = Math.max(...i.grupos.map(g => g.valor), 1);
  const mostrar = i.grupos.slice(0, 8), resto = i.grupos.length - mostrar.length;
  setHtmlSuave($("ivGrupos"), mostrar.map(g => `<div class="ivg"><div class="t"><b>${NOME_GRUPO[g.codigo] || titulo(g.grupo)}</b><span>${fmt(g.obras)} ${g.obras === 1 ? "obra" : "obras"}</span></div>
    <div class="pt"><i style="width:${Math.max(3, g.valor / max * 100)}%;background:var(--accent)"></i></div><em>${reaisMi(g.valor)}</em></div>`).join("") +
    (resto > 0 ? `<div class="cpx">+${resto} grupo${resto > 1 ? "s" : ""} menores</div>` : ""));
  const maxF = Math.max(...(i.porFilial || []).map(f => f.valor), 1);
  setHtmlSuave($("ivFaz"), (i.porFilial || []).slice(0, 6).map(f => `<div class="r"><span>${f.filial}</span><div class="b"><i style="width:${f.valor / maxF * 100}%"></i></div><b>${reaisMi(f.valor)}</b></div>`).join(""));
  setHtmlSuave($("ivRec"), (i.maiores || []).slice(0, 5).map((r, n) => `<div class="ivr"><span>${n + 1}º</span><b>${titulo(r.patrimonio.replace(/^\d+\s*-\s*/, ""))}</b><small>${r.filial}</small><em>${reaisMi(r.valor)}</em></div>`).join(""));
}
