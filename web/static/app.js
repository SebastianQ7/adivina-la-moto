/* ============================================================
   "Adivina la Moto"  -  Cliente web (vanilla JS)
   Habla con el servidor por WebSocket usando los mismos tipos
   de mensaje del protocolo (JOIN, PREGUNTA, ADIVINAR, ...).
   ============================================================ */

// ---- Tipos de mensaje (coinciden con protocolo.py / salas.py) ----
const T = {
  JOIN:"JOIN", PREGUNTA:"PREGUNTA", ADIVINAR:"ADIVINAR", DESCARTAR:"DESCARTAR",
  RENDIRSE:"RENDIRSE", REVANCHA:"REVANCHA", SALIR:"SALIR", EMOJI:"EMOJI", CHAT:"CHAT",
  ESPERANDO:"ESPERANDO", INICIO:"INICIO", RESPUESTA:"RESPUESTA",
  TURNO:"TURNO", FIN:"FIN", ERROR:"ERROR"
};

const AVATARES = ["rojo","azul","verde","morado","dorado","naranja","cyan","rosa"];
const EMOJIS = ["😀","😎","😂","😮","😭","🔥","👏","🤔","⚽","💀"];

// ---- Estado global ----
let MOTOS = {}, ATRIBUTOS = [], VALORES = {}, IMAGENES = {};
let ws = null;
let avatarSel = null, avatares = [];   // avatarSel = URL de la imagen elegida
let modoSel = null;          // 'publica' | 'rapida' | 'bot' | 'privada'
let privAccion = "crear";    // 'crear' | 'unir'
let dificultadSel = "normal"; // 'facil' | 'normal' | 'dificil' (solo modo bot)

let myId = 0, miMoto = null, tablero = [], rivalNombre = "Rival";
let esMiTurno = false, enPartida = false;
let huboInicio = false;   // true una vez empezo la 1a ronda: distingue espera inicial de revancha
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

// Ruido filtrado (para fuego, aplausos...).
function noise(dur, vol, tipoFiltro, freq){
  const c = ac(); if(!c) return;
  const n = Math.max(1, Math.floor(c.sampleRate*dur));
  const buf = c.createBuffer(1, n, c.sampleRate);
  const d = buf.getChannelData(0);
  for(let i=0;i<n;i++) d[i] = Math.random()*2-1;
  const src = c.createBufferSource(); src.buffer = buf;
  const f = c.createBiquadFilter(); f.type = tipoFiltro||"highpass"; f.frequency.value = freq||1000;
  const g = c.createGain();
  src.connect(f); f.connect(g); g.connect(c.destination);
  const now = c.currentTime;
  g.gain.setValueAtTime(vol||0.1, now);
  g.gain.exponentialRampToValueAtTime(0.0001, now+dur);
  src.start(now); src.stop(now+dur);
}
// Tono que se desliza de f1 a f2 (sorpresa, llanto...).
function glide(f1, f2, dur, tipo, vol){
  const c = ac(); if(!c) return;
  const o = c.createOscillator(), g = c.createGain();
  o.type = tipo||"sine";
  const now = c.currentTime;
  o.frequency.setValueAtTime(f1, now);
  o.frequency.exponentialRampToValueAtTime(Math.max(1,f2), now+dur);
  g.gain.setValueAtTime(vol||0.07, now);
  g.gain.exponentialRampToValueAtTime(0.0001, now+dur);
  o.connect(g); g.connect(c.destination);
  o.start(now); o.stop(now+dur);
}
// Rugido de motor para la moto.
function revMoto(){
  const c = ac(); if(!c) return;
  const o = c.createOscillator(), g = c.createGain();
  o.type = "sawtooth";
  const now = c.currentTime;
  o.frequency.setValueAtTime(60, now);
  o.frequency.linearRampToValueAtTime(230, now+0.25);
  o.frequency.linearRampToValueAtTime(85, now+0.6);
  g.gain.setValueAtTime(0.09, now);
  g.gain.exponentialRampToValueAtTime(0.0001, now+0.6);
  o.connect(g); g.connect(c.destination);
  o.start(now); o.stop(now+0.62);
  noise(0.6, 0.04, "lowpass", 420);
}
// Archivos de sonido por emoji. Si el mp3 existe en /sounds/, se reproduce ese;
// si no, cae automaticamente al sonido sintetizado de respaldo. Asi el usuario
// solo tiene que colocar sus mp3 en web/static/sounds/ con estos nombres.
const SOUND_FILES = {
  "😀":"/sounds/happy.mp3", "😎":"/sounds/cool.mp3", "😂":"/sounds/laugh.mp3",
  "😮":"/sounds/wow.mp3", "😭":"/sounds/cry.mp3", "🔥":"/sounds/fire.mp3",
  "👏":"/sounds/applause.mp3", "🤔":"/sounds/hmm.mp3", "⚽":"/sounds/whistle.mp3",
  "💀":"/sounds/death.mp3",
};
const _audioCache = {};
function playEmojiSound(e){
  const url = SOUND_FILES[e];
  if(url){
    try{
      let a = _audioCache[e];
      if(!a){ a = new Audio(url); a.volume = 0.6; _audioCache[e] = a; }
      a.currentTime = 0;
      const pr = a.play();
      if(pr && pr.catch) pr.catch(()=> synthEmoji(e));  // sin archivo -> sintetiza
      return;
    }catch(err){ /* cae al sintetizado */ }
  }
  synthEmoji(e);
}

// Sonido sintetizado de respaldo (sin archivos): cada emoji suena distinto.
function synthEmoji(e){
  switch(e){
    case "😀": beep(660,0.12,"sine",0.07); setTimeout(()=>beep(880,0.14,"sine",0.07),110); break;
    case "😎": beep(330,0.18,"sawtooth",0.05); setTimeout(()=>beep(440,0.24,"sawtooth",0.05),130); break;
    case "😂": [0,95,190,290].forEach((d,i)=>setTimeout(()=>beep(i%2?760:600,0.07,"square",0.05),d)); break;
    case "😮": glide(400,1150,0.3,"sine",0.07); break;
    case "😭": glide(720,190,0.6,"sawtooth",0.07); break;
    case "🔥": noise(0.5,0.12,"lowpass",900); break;
    case "👏": [0,95,200,310].forEach(d=>setTimeout(()=>noise(0.05,0.18,"highpass",1600),d)); break;
    case "🤔": beep(210,0.45,"sine",0.06); break;
    case "⚽": beep(2000,0.07,"square",0.06); setTimeout(()=>beep(2500,0.09,"square",0.06),80); break;
    case "💀": glide(300,85,0.7,"sawtooth",0.07); break;
    default: beep(880,0.08,"sine",0.05);
  }
}

/* ============================================================
   Arranque
   ============================================================ */
window.addEventListener("DOMContentLoaded", async () => {
  aplicarIdioma();
  $("langBtn").onclick = () => { LANG = (LANG==="es")?"en":"es"; localStorage.setItem("lang",LANG); aplicarIdioma(); reconstruirDinamico(); };

  await construirAvatares();
  construirEmojis();

  // Botones del modal de confirmación (con estilo de la página)
  $("modalOk").onclick = ()=>{ const f=_modalOnOk; cerrarModal(); if(f) f(); };
  $("modalCancel").onclick = cerrarModal;
  $("modal").onclick = (e)=>{ if(e.target.id==="modal") cerrarModal(); };

  // Enviar chat con Enter
  $("chatInput").addEventListener("keydown", (e)=>{ if(e.key==="Enter") enviarChat(); });

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
      <div class="meta"><b>${n}</b><span>${tVal(m[ATRIBUTOS[0]])} · ${tVal(m[ATRIBUTOS[1]])}</span></div>`;
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
async function construirAvatares(){
  const cont = $("avatars");
  cont.innerHTML = "";
  // Carga la lista de avatares desde el servidor (cualquier imagen que el
  // usuario ponga en imagenes/avatares/ aparece aqui automaticamente).
  let lista = [];
  try { lista = await (await fetch("/api/avatares")).json(); } catch(e){}
  if(!lista || !lista.length){
    lista = AVATARES.map(c => `/img/avatares/avatar_${c}.png`);  // respaldo
  }
  avatares = lista;
  lista.forEach((url,i)=>{
    const img = document.createElement("img");
    img.src = url;
    img.alt = "avatar";
    if(i===0){ img.classList.add("sel"); avatarSel = url; }
    img.onclick = ()=>{
      document.querySelectorAll("#avatars img").forEach(x=>x.classList.remove("sel"));
      img.classList.add("sel"); avatarSel = url; sfx.click();
    };
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
function salirAlInicio(){ cerrarWS(); enPartida=false; huboInicio=false; mostrar("landing"); }

function elegirModo(modo, el){
  modoSel = modo; sfx.click();
  document.querySelectorAll(".mode").forEach(m=>m.classList.remove("sel"));
  if(el) el.classList.add("sel");
  $("privPanel").classList.toggle("show", modo==="privada");
  $("botPanel").classList.toggle("show", modo==="bot");
}
function setDificultad(d){
  dificultadSel = d; sfx.click();
  $("diffFacil").classList.toggle("sel", d==="facil");
  $("diffNormal").classList.toggle("sel", d==="normal");
  $("diffDificil").classList.toggle("sel", d==="dificil");
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
  conectar({tipo:T.JOIN, nombre, modo, codigo, rapida, dificultad: dificultadSel});
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
  huboInicio = false;   // empieza una nueva busqueda/partida
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
    case T.CHAT:      onChat(msg); break;
    case T.ERROR:     toast(msg.msg||"Error"); break;
  }
}

/* ============================================================
   Handlers de mensajes del servidor
   ============================================================ */
function onEsperando(msg){
  // Si la partida ya empezo alguna vez (estamos en juego o en la pantalla de
  // fin esperando revancha), estos ESPERANDO son avisos: van como toast y NO
  // sacan al jugador de su pantalla (asi no se pierde el boton de Revancha).
  if(enPartida || huboInicio){ toast(msg.msg||""); return; }
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
  huboInicio = true;
  myId = msg.tu_id; miMoto = msg.tu_moto; tablero = msg.tablero;
  rivalNombre = msg.rival; reloj = msg.reloj;
  esMiTurno = msg.tu_turno;
  autoOut = new Set(); manualOut = new Set(); modoAdivinar = false;

  // Cabecera
  $("myName").textContent = $("nombre").value.trim() || "Tú";
  $("rivalName").textContent = rivalNombre;
  $("myAv").src = avatarSel || "";
  pintarMarcador(msg.marcador);

  // Moto secreta
  $("secretImg").src = IMAGENES[miMoto];
  $("secretName").textContent = miMoto;

  construirTablero();
  actualizarTurno();
  $("log").innerHTML = "";
  $("chat").innerHTML = "";
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
  const bR = $("btnRevancha");
  bR.style.display = msg.revancha ? "" : "none";
  bR.disabled = false;
  bR.textContent = t("fin_rematch");
  msg.ganaste ? sfx.win() : sfx.lose();
  mostrar("fin");
}

function onEmoji(msg){
  const f = document.createElement("div");
  f.className = "emoji-float";
  f.textContent = msg.emoji;
  document.body.appendChild(f);
  playEmojiSound(msg.emoji);
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
    confirmar({
      icono: "🎯",
      titulo: (LANG==="es") ? "¿Adivinar este jugador?" : "Guess this player?",
      texto: (LANG==="es") ? "Si fallas, pierdes la ronda al instante." : "If you're wrong, you lose the round instantly.",
      moto: n,
      okText: (LANG==="es") ? "Sí, adivinar" : "Yes, guess",
      onOk: ()=>{ enviar({tipo:T.ADIVINAR, moto:n}); toggleGuess(); }
    });
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
  confirmar({
    icono: "🏳️", danger: true, okClass: "btn-danger",
    titulo: (LANG==="es") ? "¿Rendirte?" : "Give up?",
    texto: (LANG==="es") ? "El rival ganará esta ronda automáticamente." : "Your rival will win this round automatically.",
    okText: (LANG==="es") ? "Rendirme" : "Give up",
    onOk: ()=>enviar({tipo:T.RENDIRSE})
  });
}
function enviarEmoji(e){ enviar({tipo:T.EMOJI, emoji:e}); playEmojiSound(e); }

function enviarChat(){
  const inp = $("chatInput");
  const texto = inp.value.trim();
  if(!texto) return;
  enviar({tipo:T.CHAT, texto});
  agregarChat(texto, true);          // muestro mi propio mensaje al instante
  inp.value = "";
}
function onChat(msg){ agregarChat(msg.texto, false, msg.quien); }
function agregarChat(texto, mio, quien){
  const c = $("chat");
  const el = document.createElement("div");
  el.className = "chat-msg " + (mio ? "mine" : "theirs");
  if(!mio && quien){
    const w = document.createElement("span");
    w.className = "who"; w.textContent = quien;
    el.appendChild(w);
  }
  // createTextNode: nunca interpretar el texto del rival como HTML (seguridad)
  el.appendChild(document.createTextNode(texto));
  c.appendChild(el);
  c.scrollTop = c.scrollHeight;
}
function revancha(){
  enviar({tipo:T.REVANCHA});
  const bR = $("btnRevancha");
  bR.disabled = true;
  bR.textContent = (LANG==="es") ? "Esperando al rival…" : "Waiting for rival…";
}

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
// Modal de confirmación con el estilo de la página (sustituye a window.confirm).
let _modalOnOk = null;
// opts: { titulo, texto, icono, okText, okClass, danger, moto, onOk }
function confirmar(opts){
  $("modalIcon").textContent = opts.icono || "❓";
  $("modalIcon").className = "modal-badge" + (opts.danger ? " danger" : "");
  $("modalBox").classList.toggle("danger", !!opts.danger);
  $("modalTitle").textContent = opts.titulo || ((LANG==="es") ? "¿Confirmar?" : "Confirm?");
  $("modalText").textContent = opts.texto || "";
  // Vista previa de la moto (para adivinar)
  const mm = $("modalMoto");
  if(opts.moto){
    $("modalMotoImg").src = IMAGENES[opts.moto] || "";
    $("modalMotoName").textContent = opts.moto;
    mm.classList.remove("hidden");
  } else {
    mm.classList.add("hidden");
  }
  const ok = $("modalOk");
  ok.textContent = opts.okText || ((LANG==="es") ? "Confirmar" : "Confirm");
  ok.className = "btn " + (opts.okClass || "btn-primary");
  $("modalCancel").textContent = (LANG==="es") ? "Cancelar" : "Cancel";
  _modalOnOk = opts.onOk;
  $("modal").classList.add("show");
}
function cerrarModal(){ $("modal").classList.remove("show"); _modalOnOk = null; }

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
