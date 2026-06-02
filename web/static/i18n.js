// Diccionario de traducciones es/en para "Adivina la Moto".
// Las claves coinciden con los atributos data-i18n del HTML y con textos
// dinamicos que usa app.js (prefijo no necesario: se buscan por clave).

const I18N = {
  es: {
    nav_how: "Cómo se juega", nav_rules: "Reglas", nav_gallery: "Galería", nav_play: "Jugar",
    hero_kicker: "Duelo de deducción · 24 motos",
    hero_t1: "Haz preguntas.", hero_t2: "Descarta.", hero_t3: "Adivina.",
    hero_lead: "El clásico \"¿Quién es quién?\" pero con 24 motos icónicas. Descubre la moto secreta de tu rival antes de que descubra la tuya.",
    hero_cta1: "Jugar ahora", hero_cta2: "Cómo se juega",
    tag1: "👥 2 jugadores", tag2: "🤖 vs Bot", tag3: "⚡ Partida rápida", tag4: "🔒 Salas privadas + QR",
    how_kicker: "El juego en 4 pasos", how_title: "Cómo se juega",
    how_sub: "Ambos reciben el mismo tablero de 24 motos y una moto secreta distinta. Por turnos, preguntan y descartan hasta adivinar.",
    s1t: "Te toca una moto", s1p: "El servidor te asigna en secreto una moto. Tu rival debe adivinarla… y tú la suya.",
    s2t: "Pregunta sí/no", s2p: "En tu turno preguntas por un atributo: \"¿es japonesa?\", \"¿es deportiva?\". Responde SÍ o NO.",
    s3t: "Descarta motos", s3p: "Según la respuesta, el tablero tacha solo las motos imposibles. Tú también puedes tachar a mano.",
    s4t: "¡Adivina!", s4p: "Cuando creas saberla, adivina. Si aciertas ganas; si fallas, pierdes al instante.",
    rules_kicker: "Lo que debes saber", rules_title: "Reglas",
    r1t: "Turnos alternados", r1p: "Solo puedes preguntar o adivinar cuando es tu turno. El servidor lo valida.",
    r2t: "Una acción por turno", r2p: "Haces una pregunta (y pasas el turno) o intentas adivinar.",
    r3t: "Fallar = perder", r3p: "Si adivinas mal, pierdes la ronda de inmediato. Adivina con cuidado.",
    r4t: "Modo rápido", r4p: "Con reloj: 30s por turno. Si se acaba, pierdes el turno (no la partida).",
    r5t: "Rendirse", r5p: "Puedes rendirte cuando quieras; el rival gana la ronda.",
    r6t: "Marcador", r6p: "Se llevan las rondas ganadas durante la sesión. Hay revancha al terminar.",
    gal_kicker: "El tablero completo", gal_title: "Las 24 motos",
    gal_sub: "Cada una con su origen, estilo, cilindrada, era, cilindros, refrigeración y si salió en el cine.",
    lobby_kicker: "Prepárate", lobby_title: "Crea tu jugador", lobby_sub: "Elige un nombre, un avatar y cómo quieres jugar.",
    lobby_name: "Tu nombre", lobby_avatar: "Tu avatar", lobby_mode: "Modo de juego",
    m_pub_t: "Partida pública", m_pub_s: "Te emparejamos con quien busque rival.",
    m_fast_t: "Partida rápida", m_fast_s: "Pública pero con reloj de 30s por turno.",
    m_bot_t: "Contra el Bot", m_bot_s: "Juega solo contra la máquina.",
    m_priv_t: "Partida privada", m_priv_s: "Con código y QR para tu amigo.",
    priv_create: "Crear sala", priv_join: "Unirme", priv_code: "Código de la sala",
    priv_fast_t: "Modo rápido", priv_fast_s: "Reloj de 30s por turno",
    lobby_start: "Empezar", lobby_back: "← Volver al inicio",
    wait_title: "Buscando rival…", wait_sub: "Te emparejaremos en cuanto otro jugador entre.",
    wait_code: "Código de la sala", wait_cancel: "Cancelar",
    wait_priv_title: "Sala lista", wait_priv_sub: "Comparte el código o el QR con tu amigo.",
    g_secret: "Tu moto secreta", g_ask: "Preguntar", g_ask_btn: "Preguntar",
    g_guess_btn: "🎯 Adivinar una moto", g_guess_cancel: "✕ Cancelar adivinar",
    g_giveup: "🏳️ Rendirme", g_left: "motos posibles", g_react: "Reaccionar", g_history: "Historial",
    fin_reveal: "La moto del rival era", fin_rematch: "Revancha", fin_exit: "Salir",
    turn_mine: "Tu turno", turn_theirs: "Turno del rival",
    guess_confirm: "¿Adivinar que la moto del rival es {m}?",
    toast_pick_guess: "Toca una moto del tablero para adivinarla",
    toast_not_turn: "No es tu turno",
    win: "¡Ganaste!", lose: "Perdiste",
    score_you: "Tú", score_label: "Marcador",
  },
  en: {
    nav_how: "How to play", nav_rules: "Rules", nav_gallery: "Gallery", nav_play: "Play",
    hero_kicker: "Deduction duel · 24 bikes",
    hero_t1: "Ask questions.", hero_t2: "Rule out.", hero_t3: "Guess.",
    hero_lead: "The classic \"Guess Who?\" but with 24 iconic motorcycles. Find your rival's secret bike before they find yours.",
    hero_cta1: "Play now", hero_cta2: "How to play",
    tag1: "👥 2 players", tag2: "🤖 vs Bot", tag3: "⚡ Quick match", tag4: "🔒 Private rooms + QR",
    how_kicker: "The game in 4 steps", how_title: "How to play",
    how_sub: "Both get the same 24-bike board and a different secret bike. Take turns asking and ruling out until you guess.",
    s1t: "You get a bike", s1p: "The server secretly assigns you a bike. Your rival must guess it… and you guess theirs.",
    s2t: "Ask yes/no", s2p: "On your turn ask about an attribute: \"is it Japanese?\", \"is it a sportbike?\". Answer is YES or NO.",
    s3t: "Rule out bikes", s3p: "Based on the answer, the board crosses out impossible bikes. You can also cross them out yourself.",
    s4t: "Guess!", s4p: "When you think you know it, guess. Right = you win; wrong = you lose instantly.",
    rules_kicker: "What you should know", rules_title: "Rules",
    r1t: "Alternating turns", r1p: "You can only ask or guess on your turn. The server validates it.",
    r2t: "One action per turn", r2p: "You ask a question (and pass the turn) or try to guess.",
    r3t: "Miss = lose", r3p: "If you guess wrong, you lose the round immediately. Guess carefully.",
    r4t: "Quick mode", r4p: "With a clock: 30s per turn. If it runs out, you lose the turn (not the game).",
    r5t: "Give up", r5p: "You can surrender anytime; the rival wins the round.",
    r6t: "Score", r6p: "Rounds won are kept during the session. There's a rematch at the end.",
    gal_kicker: "The full board", gal_title: "The 24 bikes",
    gal_sub: "Each with its origin, style, displacement, era, cylinders, cooling and movie fame.",
    lobby_kicker: "Get ready", lobby_title: "Create your player", lobby_sub: "Pick a name, an avatar and how you want to play.",
    lobby_name: "Your name", lobby_avatar: "Your avatar", lobby_mode: "Game mode",
    m_pub_t: "Public match", m_pub_s: "We pair you with anyone looking for a rival.",
    m_fast_t: "Quick match", m_fast_s: "Public but with a 30s-per-turn clock.",
    m_bot_t: "Against the Bot", m_bot_s: "Play solo against the machine.",
    m_priv_t: "Private match", m_priv_s: "With a code and QR for your friend.",
    priv_create: "Create room", priv_join: "Join", priv_code: "Room code",
    priv_fast_t: "Quick mode", priv_fast_s: "30s-per-turn clock",
    lobby_start: "Start", lobby_back: "← Back to home",
    wait_title: "Looking for a rival…", wait_sub: "We'll pair you as soon as another player joins.",
    wait_code: "Room code", wait_cancel: "Cancel",
    wait_priv_title: "Room ready", wait_priv_sub: "Share the code or QR with your friend.",
    g_secret: "Your secret bike", g_ask: "Ask", g_ask_btn: "Ask",
    g_guess_btn: "🎯 Guess a bike", g_guess_cancel: "✕ Cancel guessing",
    g_giveup: "🏳️ Give up", g_left: "possible bikes", g_react: "React", g_history: "History",
    fin_reveal: "The rival's bike was", fin_rematch: "Rematch", fin_exit: "Exit",
    turn_mine: "Your turn", turn_theirs: "Rival's turn",
    guess_confirm: "Guess that the rival's bike is {m}?",
    toast_pick_guess: "Tap a bike on the board to guess it",
    toast_not_turn: "It's not your turn",
    win: "You won!", lose: "You lost",
    score_you: "You", score_label: "Score",
  }
};

// Traduccion de los VALORES de atributos de las motos (para la UI).
const I18N_VAL = {
  es: {}, // en español se muestran tal cual (origen, estilo, etc.)
  en: {
    // origen
    japonesa: "Japanese", americana: "American", italiana: "Italian",
    inglesa: "British", alemana: "German", austriaca: "Austrian",
    // estilo
    deportiva: "sport", naked: "naked", cruiser: "cruiser", touring: "touring",
    trail: "adventure", enduro: "enduro",
    // cilindrada
    baja: "low", media: "medium", alta: "high",
    // era
    clasica_pre1990: "classic (pre-1990)", noventas: "nineties", moderna_post2000: "modern (post-2000)",
    // cilindros / refrigeracion / cine
    "1": "1", "2": "2", "3": "3", "4_o_mas": "4+",
    aire: "air", liquida: "liquid", si: "yes", no: "no",
  }
};

// Traduccion de los NOMBRES de atributo (encabezados de los selects).
const I18N_ATTR = {
  es: { origen:"origen", estilo:"estilo", cilindrada:"cilindrada", era:"era",
        cilindros:"cilindros", refrigeracion:"refrigeración", famosa_en_cine:"famosa en cine" },
  en: { origen:"origin", estilo:"style", cilindrada:"displacement", era:"era",
        cilindros:"cylinders", refrigeracion:"cooling", famosa_en_cine:"movie fame" }
};

let LANG = localStorage.getItem("lang") || "es";

function t(clave) {
  return (I18N[LANG] && I18N[LANG][clave]) || (I18N.es[clave]) || clave;
}
function tVal(v) {
  if (LANG === "es") return String(v);
  return (I18N_VAL.en[v] !== undefined) ? I18N_VAL.en[v] : String(v);
}
function tAttr(a) {
  return (I18N_ATTR[LANG] && I18N_ATTR[LANG][a]) || a;
}

function aplicarIdioma() {
  document.documentElement.lang = LANG;
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const k = el.getAttribute("data-i18n");
    if (I18N[LANG] && I18N[LANG][k] !== undefined) el.textContent = I18N[LANG][k];
  });
  const btn = document.getElementById("langBtn");
  if (btn) btn.textContent = (LANG === "es") ? "EN" : "ES";
}
