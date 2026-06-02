/* ============================================================
   "Adivina la Moto"  -  Cliente web (vanilla JS)
   Habla con el servidor por WebSocket usando los mismos tipos
   de mensaje del protocolo (JOIN, PREGUNTA, ADIVINAR, ...).
   ============================================================ */

// ---- Tipos de mensaje (coinciden con protocolo.py / salas.py) ----
const T = {
  JOIN:"JOIN", PREGUNTA:"PREGUNTA", ADIVINAR:"ADIVINAR", DESCARTAR:"DESCARTAR",
  RENDIRSE:"RENDIRSE", REVANCHA:"REVANCHA", SALIR:"SALIR", EMOJI:"EMOJI",
  ESPERANDO:"ESPERANDO", INICIO:"INICIO", RESPUESTA:"RESPUESTA",
  TURNO:"TURNO", FIN:"FIN", ERROR:"ERROR"
};

const AVATARES = ["rojo","azul","verde","morado","dorado","naranja","cyan","rosa"];
const EMOJIS = ["😀","😎","😂","😮","😭","🔥","👏","🤔","🏍️","💀"];

// ---- Estado global ----
let MOTOS = {}, ATRIBUTOS = [], VALORES = {}, IMAGENES = {};
let ws = null;
let avatarSel = "rojo";
let modoSel = null;          // 'publica' | 'rapida' | 'bot' | 'privada'
let privAccion = "crear";    // 'crear' | 'unir'

let myId = 0, miMoto = null, tablero = [], rivalNombre = "Rival";
let esMiTurno = false, enPartida = false;
let reloj = null, relojRestante = 0, relojTimer = null;
let modoAdivinar = false;
let autoOut = new Set();      // descartes por deducción (mis preguntas)
let manualOut = new Set();    // descartes manuales del jugador

const $ = id => document.getElementById(id);

/* ============================================================
   Sonidos (Web Audio, sin archivos)
   ============================================================ */
let AC = null;
function ac(){ if(!AC){ try{ AC = new (window.AudioContext||window.webkitAudioContext)(); }catch(e){} } return AC; }
function beep(freq, dur, tipo="sine", vol=0.08){
  const c = ac(); if(!c) return;
  const o = c.createOscillator(), g = c.createGain();
  o.type = tipo; o.frequency.value = freq;
  g.gain.value = vol;
  o.connect(g); g.connect(c.destination);
  const now = c.currentTime;
  g.gain.setValueAtTime(vol, now);
  g.gain.exponentialRampToValueAtTime(0.0001, now+dur);
  o.start(now); o.stop(now+dur);
}
const sfx = {
  click: ()=>beep(420,0.06,"triangle",0.05),
  yes:   ()=>{ beep(560,0.1,"sine"); setTimeout(()=>beep(780,0.14,"sine"),90); },
  no:    ()=>{ beep(300,0.18,"sawtooth",0.06); },
  turn:  ()=>beep(660,0.08,"sine",0.05),
  win:   ()=>{ [523,659,784,1046].forEach((f,i)=>setTimeout(()=>beep(f,0.18,"triangle",0.08),i*120)); },
  lose:  ()=>{ [392,330,262].forEach((f,i)=>setTimeout(()=>beep(f,0.22,"sawtooth",0.07),i*140)); },
  emoji: ()=>beep(880,0.08,"sine",0.05),
};

/* ============================================================
   Arranque
   ============================================================ */
window.addEventListener("DOMContentLoaded", async () => {
  aplicarIdioma();
  $("langBtn").onclick = () => { LANG = (LANG==="es")?"en":"es"; localStorage.setItem("lang",LANG); aplicarIdioma(); reconstruirDinamico(); };

  construirAvatares();
  construirEmojis();

  try {
    const r = await fetch("/api/motos");
    const data = await r.json();
    MOTOS = data.motos; ATRIBUTOS = data.atributos; VALORES = data.valores; IMAGENES = data.imagenes;
    construirGaleria();
    construirHeroArt();
    construirSelectAtributos();
  } catch(e){ console.error("No se pudo cargar /api/motos", e); }

  // Si llegaron por QR/enlace con ?sala=CODIGO -> ir directo a unirse a privada.
  const params = new URLSearchParams(location.search);
  if (params.get("sala")) {
    irLobby();
    elegirModo("privada", document.querySelector('[data-modo="privada"]'));
    setPriv("unir");
    $("codigo").value = params.get("sala").toUpperCase();
    setTimeout(()=>$("nombre").focus(), 100);
  }
});

function reconstruirDinamico(){
  if (Object.keys(MOTOS).length){ construirGaleria(); construirSelectAtributos(); }
}

/* ============================================================
   Landing dinámica
   ============================================================ */
function construirGaleria(){
  const g = $("gallery"); if(!g) return; g.innerHTML = "";
  Object.keys(MOTOS).forEach(n => {
    const m = MOTOS[n];
    const el = document.createElement("div");
    el.className = "moto-card";
    el.innerHTML = `<div class="ph"><img src="${IMAGENES[n]}" alt="${n}" loading="lazy"></div>
      <div class="meta"><b>${n}</b><span>${tVal(m.origen)} · ${tVal(m.estilo)}</span></div>`;
    g.appendChild(el);
  });
}
function construirHeroArt(){
  const art = $("heroArt"); if(!art) return;
  const nombres = Object.keys(MOTOS);
  const elegidas = nombres.sort(()=>Math.random()-0.5).slice(0,4);
  ["c1","c2","c3","c4"].forEach((c,i)=>{
    const d = document.createElement("div");
    d.className = `chip ${c}`;
    d.innerHTML = `<img src="${IMAGENES[elegidas[i]]}" alt="">`;
    art.appendChild(d);
  });
}

/* ============================================================
   Lobby
   ============================================================ */
function construirAvatares(){
  const cont = $("avatars");
  AVATARES.forEach((c,i)=>{
    const img = document.createElement("img");
    img.src = `/img/avatares/avatar_${c}.png`;
    img.alt = c;
    if(i===0) img.classList.add("sel");
    img.onclick = ()=>{ document.querySelectorAll("#avatars img").forEach(x=>x.classList.remove("sel")); img.classList.add("sel"); avatarSel=c; sfx.click(); };
    cont.appendChild(img);
  });
}
function construirEmojis(){
  const bar = $("emojiBar");
  EMOJIS.forEach(e=>{
    const b = document.createElement("button");
    b.textContent = e;
    b.onclick = ()=>enviarEmoji(e);
    bar.appendChild(b);
  });
}

function irLobby(){ mostrar("lobby"); }
function volverLanding(){ mostrar("landing"); }
function salirAlInicio(){ cerrarWS(); enPartida=false; mostrar("landing"); }

function elegirModo(modo, el){
  modoSel = modo; sfx.click();
  document.querySelectorAll(".mode").forEach(m=>m.classList.remove("sel"));
  if(el) el.classList.add("sel");
  $("privPanel").classList.toggle("show", modo==="privada");
}
function setPriv(accion){
  privAccion = accion; sfx.click();
  $("segCrear").classList.toggle("sel", accion==="crear");
  $("segUnir").classList.toggle("sel", accion==="unir");
  // El switch "modo rápido" solo aplica al CREAR la sala.
  $("rapidaRow").style.display = (accion==="crear") ? "flex" : "none";
}

function comenzar(){
  const nombre = $("nombre").value.trim();
  $("lobbyErr").textContent = "";
  if(!nombre){ $("lobbyErr").textContent = LANG==="es"?"Escribe tu nombre.":"Enter your name."; return; }
  if(!modoSel){ $("lobbyErr").textContent = LANG==="es"?"Elige un modo de juego.":"Pick a game mode."; return; }

  let modo = modoSel, codigo = "", rapida = false;
  if(modoSel==="privada"){
    codigo = $("codigo").value.trim().toUpperCase();
    if(!codigo){ $("lobbyErr").textContent = LANG==="es"?"Escribe el código de la sala.":"Enter the room code."; return; }
    modo = (privAccion==="crear") ? "privada_crear" : "privada_unir";
    rapida = (privAccion==="crear") && $("rapidaChk").checked;
  }
  ac(); // "desbloquea" el audio con el gesto del usuario
  conectar({tipo:T.JOIN, nombre, modo, codigo, rapida});
}

/* ============================================================
   WebSocket
   ============================================================ */
function conectar(joinMsg){
  const proto = (location.protocol==="https:") ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = ()=> ws.send(JSON.stringify(joinMsg));
  ws.onmessage = (ev)=>{ try{ manejar(JSON.parse(ev.data)); }catch(e){ console.error(e); } };
  ws.onclose = ()=>{ if(enPartida){ /* la partida maneja el FIN */ } };
  ws.onerror = ()=> toast(LANG==="es"?"Error de conexión":"Connection error");
  mostrar("esperando");
  $("waitTitle").textContent = t("wait_title");
  $("waitSub").textContent = t("wait_sub");
  $("privateInfo").classList.add("hidden");
}
function enviar(obj){ if(ws && ws.readyState===1) ws.send(JSON.stringify(obj)); }
function cerrarWS(){ if(ws){ try{ enviar({tipo:T.SALIR}); ws.close(); }catch(e){} ws=null; } }
function cancelarEspera(){ cerrarWS(); mostrar("lobby"); }

function manejar(msg){
  switch(msg.tipo){
    case T.ESPERANDO: onEsperando(msg); break;
    case T.INICIO:    onInicio(msg); break;
    case T.RESPUESTA: onRespuesta(msg); break;
    case T.TURNO:     onTurno(msg); break;
    case T.FIN:       onFin(msg); break;
    case T.EMOJI:     onEmoji(msg); break;
    case T.ERROR:     toast(msg.msg||"Error"); break;
  }
}

/* ============================================================
   Handlers de mensajes del servidor
   ============================================================ */
function onEsperando(msg){
  if(enPartida){ toast(msg.msg||""); return; }    // mensajes de revancha, etc.
  mostrar("esperando");
  if(msg.codigo){
    // Sala privada creada: mostrar código + QR.
    $("waitTitle").textContent = t("wait_priv_title");
    $("waitSub").textContent = t("wait_priv_sub");
    $("privateInfo").classList.remove("hidden");
    $("waitCode").textContent = msg.codigo;
    const url = `${location.origin}/?sala=${encodeURIComponent(msg.codigo)}`;
    $("qrImg").src = `https://api.qrserver.com/v1/create-qr-code/?size=188x188&margin=0&data=${encodeURIComponent(url)}`;
    $("shareLink").textContent = url;
  } else {
    $("waitTitle").textContent = t("wait_title");
    $("waitSub").textContent = msg.msg || t("wait_sub");
    $("privateInfo").classList.add("hidden");
  }
}

function onInicio(msg){
  enPartida = true;
  myId = msg.tu_id; miMoto = msg.tu_moto; tablero = msg.tablero;
  rivalNombre = msg.rival; reloj = msg.reloj;
  esMiTurno = msg.tu_turno;
  autoOut = new Set(); manualOut = new Set(); modoAdivinar = false;

  // Cabecera
  $("myName").textContent = $("nombre").value.trim() || "Tú";
  $("rivalName").textContent = rivalNombre;
  $("myAv").src = `/img/avatares/avatar_${avatarSel}.png`;
  pintarMarcador(msg.marcador);

  // Moto secreta
  $("secretImg").src = IMAGENES[miMoto];
  $("secretName").textContent = miMoto;

  construirTablero();
  actualizarTurno();
  $("log").innerHTML = "";
  $("btnAdivinar").textContent = t("g_guess_btn");
  $("board").classList.remove("guessing");
  mostrar("juego");
}

function onRespuesta(msg){
  const mia = (msg.quien_id === myId);
  if(mia){
    // Deducción automática: tacho las motos imposibles según la respuesta.
    aplicarDeduccion(msg.atributo, msg.valor, msg.respuesta);
    actualizarTablero();
  }
  (msg.respuesta==="SI") ? sfx.yes() : sfx.no();
  agregarLog(msg, mia);
}

function onTurno(msg){
  esMiTurno = msg.tu_turno;
  reloj = msg.reloj;
  if(esMiTurno) sfx.turn();
  actualizarTurno();
}

function onFin(msg){
  enPartida = false;
  pararReloj();
  $("finEmoji").textContent = msg.ganaste ? "🏆" : "😵";
  $("finTitle").textContent = msg.ganaste ? t("win") : t("lose");
  $("finTitle").className = msg.ganaste ? "win" : "lose";
  $("finMsg").textContent = msg.msg || "";
  $("finImg").src = IMAGENES[msg.moto_rival] || "";
  $("finMoto").textContent = msg.moto_rival || "";
  $("finScore").textContent = `${t("score_label")}: ${marcadorTexto(msg.marcador)}`;
  $("btnRevancha").style.display = msg.revancha ? "" : "none";
  msg.ganaste ? sfx.win() : sfx.lose();
  mostrar("fin");
}

function onEmoji(msg){
  const f = document.createElement("div");
  f.className = "emoji-float";
  f.textContent = msg.emoji;
  document.body.appendChild(f);
  sfx.emoji();
  setTimeout(()=>f.remove(), 1700);
}

/* ============================================================
   Tablero
   ============================================================ */
function construirTablero(){
  const b = $("board"); b.innerHTML = "";
  tablero.forEach((n,i)=>{
    const c = document.createElement("div");
    c.className = "card";
    c.dataset.moto = n;
    c.style.animationDelay = (i*18)+"ms";
    c.innerHTML = `<div class="pic"><img src="${IMAGENES[n]}" alt="${n}"></div><div class="nm">${n}</div>`;
    c.onclick = ()=>clicCarta(n, c);
    b.appendChild(c);
  });
  actualizarPosibles();
}

function clicCarta(n, c){
  if(modoAdivinar){
    if(!esMiTurno){ toast(t("toast_not_turn")); return; }
    const txt = t("guess_confirm").replace("{m}", n);
    if(confirm(txt)){ enviar({tipo:T.ADIVINAR, moto:n}); toggleGuess(); }
    return;
  }
  // Descarte manual (tachar/destachar)
  if(autoOut.has(n)) return; // ya descartada por deducción
  if(manualOut.has(n)) manualOut.delete(n); else manualOut.add(n);
  enviar({tipo:T.DESCARTAR, moto:n});
  sfx.click();
  actualizarTablero();
}

function aplicarDeduccion(attr, val, resp){
  tablero.forEach(n=>{
    const coincide = String(MOTOS[n][attr]) === String(val);
    if((resp==="SI" && !coincide) || (resp==="NO" && coincide)) autoOut.add(n);
  });
}

function actualizarTablero(){
  document.querySelectorAll("#board .card").forEach(c=>{
    const n = c.dataset.moto;
    c.classList.toggle("out", autoOut.has(n) || manualOut.has(n));
  });
  actualizarPosibles();
}
function actualizarPosibles(){
  const quedan = tablero.filter(n => !autoOut.has(n) && !manualOut.has(n)).length;
  $("posibles").textContent = quedan;
}

function toggleGuess(){
  modoAdivinar = !modoAdivinar;
  $("board").classList.toggle("guessing", modoAdivinar);
  $("btnAdivinar").textContent = modoAdivinar ? t("g_guess_cancel") : t("g_guess_btn");
  if(modoAdivinar) toast(t("toast_pick_guess"));
}

/* ============================================================
   Preguntar / rendirse / emojis / revancha
   ============================================================ */
function construirSelectAtributos(){
  const sel = $("selAtributo"); if(!sel) return;
  sel.innerHTML = "";
  ATRIBUTOS.forEach(a=>{
    const o = document.createElement("option");
    o.value = a; o.textContent = tAttr(a);
    sel.appendChild(o);
  });
  sel.onchange = construirSelectValores;
  construirSelectValores();
}
function construirSelectValores(){
  const attr = $("selAtributo").value;
  const sel = $("selValor"); sel.innerHTML = "";
  (VALORES[attr]||[]).forEach(v=>{
    const o = document.createElement("option");
    o.value = v; o.textContent = tVal(v);
    sel.appendChild(o);
  });
}
function preguntar(){
  if(!esMiTurno){ toast(t("toast_not_turn")); return; }
  enviar({tipo:T.PREGUNTA, atributo:$("selAtributo").value, valor:$("selValor").value});
}
function rendirse(){
  if(confirm(LANG==="es"?"¿Seguro que quieres rendirte?":"Are you sure you want to give up?"))
    enviar({tipo:T.RENDIRSE});
}
function enviarEmoji(e){ enviar({tipo:T.EMOJI, emoji:e}); sfx.emoji(); }
function revancha(){ enviar({tipo:T.REVANCHA}); toast(LANG==="es"?"Esperando al rival…":"Waiting for rival…"); }

/* ============================================================
   Turno, reloj, marcador, log
   ============================================================ */
function actualizarTurno(){
  const pill = $("turnPill");
  pill.textContent = esMiTurno ? t("turn_mine") : t("turn_theirs");
  pill.className = "pill " + (esMiTurno ? "mine" : "theirs");

  const dis = !esMiTurno;
  $("btnPreguntar").disabled = dis;
  $("selAtributo").disabled = dis;
  $("selValor").disabled = dis;
  $("btnAdivinar").disabled = dis;
  if(dis && modoAdivinar) toggleGuess();

  if(reloj){ iniciarReloj(); } else { $("clock").classList.add("hidden"); }
}
function iniciarReloj(){
  pararReloj();
  relojRestante = reloj;
  const cl = $("clock");
  cl.classList.remove("hidden");
  pintarReloj();
  relojTimer = setInterval(()=>{
    relojRestante--;
    pintarReloj();
    if(relojRestante<=0) pararReloj();
  }, 1000);
}
function pintarReloj(){
  const cl = $("clock");
  cl.textContent = Math.max(0,relojRestante);
  cl.classList.toggle("low", relojRestante<=10 && esMiTurno);
}
function pararReloj(){ if(relojTimer){ clearInterval(relojTimer); relojTimer=null; } }

function pintarMarcador(marc){
  if(!marc) return;
  const miNombre = $("myName").textContent;
  let mio=0, suyo=0;
  Object.keys(marc).forEach(k=>{ if(k===rivalNombre) suyo=marc[k]; else mio=marc[k]; });
  // fallback por si los nombres no calzan exactamente
  const vals = Object.values(marc);
  $("myScore").textContent = mio;
  $("rivalScore").textContent = suyo;
}
function marcadorTexto(marc){
  if(!marc) return "";
  let mio=0, suyo=0;
  Object.keys(marc).forEach(k=>{ if(k===rivalNombre) suyo=marc[k]; else mio=marc[k]; });
  return `${t("score_you")} ${mio} — ${suyo} ${rivalNombre}`;
}

function agregarLog(msg, mia){
  const log = $("log");
  const item = document.createElement("div");
  item.className = "log-item" + (mia ? " mine" : "");
  const quien = mia ? (LANG==="es"?"Tú":"You") : msg.quien;
  const pregunta = `${quien}: ¿${tAttr(msg.atributo)} = ${tVal(msg.valor)}?`;
  const resp = (msg.respuesta==="SI") ? (LANG==="es"?"SÍ":"YES") : "NO";
  item.innerHTML = `<span class="a ${msg.respuesta==="SI"?"si":"no"}">${resp}</span><span class="q">${pregunta}</span>`;
  log.insertBefore(item, log.firstChild);
}

/* ============================================================
   Utilidades de UI
   ============================================================ */
function mostrar(idScreen){
  document.querySelectorAll(".screen").forEach(s=>s.classList.remove("active"));
  $(idScreen).classList.add("active");
  window.scrollTo(0,0);
}
let toastTimer = null;
function toast(txt){
  const el = $("toast");
  el.textContent = txt;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>el.classList.remove("show"), 2600);
}
