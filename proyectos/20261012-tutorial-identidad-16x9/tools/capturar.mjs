// Recorre el editor REAL de la identidad digital (Aurela local, sesión demo)
// llenando el perfil de Barbería Central paso a paso, y guarda una captura por
// estado + manifest.json con el punto tocado y el campo activo de cada una.
//
// Uso: node capturar.mjs <escritorio|movil> <carpeta_fotos> <carpeta_salida>
//   carpeta_fotos: logo.png, portada.jpg, galeria-1.jpg, galeria-2.jpg
// Requiere Aurela corriendo en http://localhost:3000 con el demo encendido.
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const [modo, fotosDir, salidaDir] = process.argv.slice(2);
if (!["escritorio", "movil"].includes(modo) || !fotosDir || !salidaDir) {
  console.error("Uso: node capturar.mjs <escritorio|movil> <fotos> <salida>");
  process.exit(1);
}
const MOVIL = modo === "movil";
const W = MOVIL ? 390 : 1600;
const H = MOVIL ? 844 : 900;
const DPR = MOVIL ? 3 : 2;
const BASE = "http://localhost:3000";
const FOTOS = resolve(fotosDir);
const SALIDA = resolve(salidaDir);
mkdirSync(SALIDA, { recursive: true });

const port = 9400 + Math.floor(Math.random() * 400);
const chrome = spawn(
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${port}`,
   `--user-data-dir=${mkdtempSync(join(tmpdir(), "tutorial-chrome-"))}`, `--window-size=${W},${H}`,
   "--lang=es-CO", "about:blank"],
  { stdio: "ignore" }
);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let page;
for (let i = 0; i < 40 && !page; i++) {
  await sleep(250);
  try {
    page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page");
  } catch {}
}
if (!page) throw new Error("Chrome no respondió");
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let seq = 0;
const pend = new Map();
ws.addEventListener("message", (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
});
const send = (method, params = {}) => {
  const id = ++seq;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((ok, ko) => pend.set(id, (m) => (m.error ? ko(new Error(`${method}: ${m.error.message}`)) : ok(m.result))));
};
async function js(expr) {
  const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(`JS: ${r.exceptionDetails.exception?.description || r.exceptionDetails.text}\n${expr.slice(0, 300)}`);
  return r.result?.value;
}

await send("Page.enable");
await send("DOM.enable");
await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: DPR, mobile: MOVIL });
if (MOVIL) {
  await send("Emulation.setTouchEmulationEnabled", { enabled: true });
  await send("Emulation.setUserAgentOverride", {
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    acceptLanguage: "es-CO,es",
  });
}
await send("Emulation.setLocaleOverride", { locale: "es-CO" }).catch(() => {});

async function ir(url, espera = 3500) {
  await send("Page.navigate", { url });
  await sleep(espera);
}

// Funciones de ayuda dentro de la página (se reinyectan tras cada navegación).
const AYUDA = `
window.__t = {
  // Elemento visible cuyo texto (sin espacios de más) coincide.
  porTexto(sel, txt, exacto = true) {
    const ok = (e) => e.offsetParent !== null || getComputedStyle(e).position === 'fixed';
    const o = [...document.querySelectorAll(sel)].filter((e) => {
      const t = e.innerText.replace(/\\s+/g, ' ').trim();
      return ok(e) && (exacto ? t === txt : t.startsWith(txt));
    });
    return o[0] || null;
  },
  campo(label) {
    const l = [...document.querySelectorAll('label')].find((e) => e.textContent.replace(/\\s+/g, ' ').trim().toLowerCase().startsWith(label.toLowerCase()) && e.offsetParent !== null);
    if (!l) return null;
    if (l.htmlFor) return document.getElementById(l.htmlFor);
    return l.parentElement.querySelector('input,textarea,select');
  },
  rect(e) {
    const r = e.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  },
  poner(e, v) {
    const proto = e.tagName === 'TEXTAREA' ? HTMLTextAreaElement : e.tagName === 'SELECT' ? HTMLSelectElement : HTMLInputElement;
    Object.getOwnPropertyDescriptor(proto.prototype, 'value').set.call(e, v);
    e.dispatchEvent(new Event(e.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }));
  },
  // El editor de escritorio se desplaza dentro de .shell-content, no en window.
  sc() {
    const s = document.querySelector('.shell-content');
    return s && s.scrollHeight > s.clientHeight + 5 ? s : document.scrollingElement;
  },
  arriba() { this.sc().scrollTop = 0; },
  centrar(e, dy = 0) {
    const r = e.getBoundingClientRect();
    this.sc().scrollBy(0, r.top + r.height / 2 - innerHeight / 2 + dy);
  },
  limpiar() {
    // Aviso de la demo y la guía: no salen en el video.
    document.querySelectorAll('p,div').forEach((e) => {
      if (/^(Estás en la demo|You're in the demo)/.test(e.innerText.trim())) {
        (e.closest('[class*=note],[class*=Note],[class*=notice],[class*=alert]') || e).style.display = 'none';
      }
    });
    // Que no se vea localhost ni el slug de la copia demo: el enlace real de un cliente.
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let t; (t = w.nextNode()); ) {
      if (/En la demo el enlace/.test(t.nodeValue)) t.parentElement.style.visibility = 'hidden';
      if (/localhost:3000|demo-[0-9a-f]{8}/.test(t.nodeValue)) {
        t.nodeValue = t.nodeValue.replace(/https?:..localhost:3000/g, 'aurelasoluciones.com').replace(/demo-[0-9a-f]{8}/g, 'barberia-central');
      }
    }
    document.querySelectorAll('input').forEach((i) => {
      if (/localhost:3000|^demo-[0-9a-f]{8}$/.test(i.value)) {
        i.value = i.value.replace(/https?:..localhost:3000/g, 'aurelasoluciones.com').replace(/demo-[0-9a-f]{8}/g, 'barberia-central');
      }
    });
  },
};
'ok'`;

const manifest = [];
let n = 0;
// Captura el estado actual. foco: rect del campo activo; toque: punto tocado.
async function foto(nombre, extra = {}) {
  await js("window.__t.limpiar(); 'ok'");
  await sleep(250);
  const { data } = await send("Page.captureScreenshot", { format: "png" });
  const archivo = `${String(n++).padStart(3, "0")}-${nombre}.png`;
  writeFileSync(join(SALIDA, archivo), Buffer.from(data, "base64"));
  manifest.push({ img: archivo, nombre, ...extra });
  console.log("shot:", archivo);
}

// Selector JS que devuelve un elemento; guarda su rect como foco/toque.
async function rectDe(exprElemento) {
  return js(`(()=>{const e=${exprElemento};return e?window.__t.rect(e):null})()`);
}
const centro = (r) => (r ? { x: r.x + r.w / 2, y: r.y + r.h / 2 } : null);

// antes: nombre de una captura justo antes del clic (ya desplazada), para que el
// toque del video caiga sobre el botón y no sobre la pantalla anterior.
async function tocar(exprElemento, nombre, espera = 900, antes = null) {
  await js(`(()=>{const e=${exprElemento};if(!e)throw new Error('no está: ${nombre}');window.__t.centrar(e, ${MOVIL ? 0 : -120});return 'ok'})()`);
  await sleep(300);
  const r = await rectDe(exprElemento);
  if (antes) await foto(antes, { toque: centro(r), foco: r });
  await js(`(()=>{${exprElemento}.click();return 'ok'})()`);
  await sleep(espera);
  await js(AYUDA);
  return r;
}

// Escribe en un campo y captura cada `paso` letras.
async function escribir(exprCampo, texto, nombre, paso = 2, dy = 0) {
  await js(`(()=>{const e=${exprCampo};if(!e)throw new Error('no está: ${nombre}');window.__t.centrar(e, ${dy});e.focus();window.__t.poner(e,'');return 'ok'})()`);
  await sleep(300);
  const r = await rectDe(exprCampo);
  await foto(`${nombre}-00`, { foco: r, toque: centro(r) });
  const cortes = [];
  for (let i = paso; i < texto.length; i += paso) cortes.push(i);
  cortes.push(texto.length);
  for (const [k, i] of cortes.entries()) {
    await js(`(()=>{window.__t.poner(${exprCampo}, ${JSON.stringify(texto.slice(0, i))});return 'ok'})()`);
    await sleep(120);
    await foto(`${nombre}-${String(k + 1).padStart(2, "0")}`, { foco: r, tipeo: true });
  }
  return r;
}

async function subir(selector, indice, archivos) {
  const { root } = await send("DOM.getDocument", { depth: -1 });
  const { nodeIds } = await send("DOM.querySelectorAll", { nodeId: root.nodeId, selector });
  if (!nodeIds[indice]) throw new Error(`no hay input ${selector}[${indice}]`);
  await send("DOM.setFileInputFiles", { nodeId: nodeIds[indice], files: archivos.map((a) => join(FOTOS, a)) });
}

const nav = (txt) =>
  MOVIL
    ? `window.__t.porTexto('.mobile-tabs button', ${JSON.stringify(txt)}, false)`
    : `window.__t.porTexto('nav button, nav a, aside button, aside a', ${JSON.stringify(txt)})`;
const boton = (txt, exacto = true) => `window.__t.porTexto('button', ${JSON.stringify(txt)}, ${exacto})`;
const campo = (label) => `window.__t.campo(${JSON.stringify(label)})`;

try {
  // 0. Sesión demo, idioma español y perfil vacío (el nombre no puede quedar vacío en el servidor:
  //    se borra solo en pantalla antes de escribirlo).
  await ir(`${BASE}/nfc`, 2000);
  await js(`localStorage.setItem('aurela_lang','es'); localStorage.removeItem('aurela_nfc_tour'); 'ok'`);
  const login = await js(`fetch('/api/nfc/demo/login',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({username:'demo',password:'demo'})}).then(r=>r.status)`);
  if (login !== 200) throw new Error(`login demo: ${login}`);
  const reset = await js(`(async()=>{
    const h={'content-type':'application/json'};
    const st=await (await fetch('/api/nfc/profile')).json();
    const p=st.profile;
    await fetch('/api/nfc/profile',{method:'PATCH',headers:h,body:JSON.stringify({displayName:'Barbería Central',headline:'',bio:'',whatsappPhone:'',whatsappText:'',links:{},services:[],testimonials:[],faq:[],hours:{},hoursNote:'',address:'',catalogKind:'general',catalogLabel:'Servicios'})});
    await fetch('/api/nfc/profile/avatar',{method:'DELETE'});
    for (const f of p.covers||[]) await fetch('/api/nfc/profile/cover/'+encodeURIComponent(f.split('/').pop()),{method:'DELETE'});
    for (const f of p.gallery||[]) await fetch('/api/nfc/profile/gallery/'+encodeURIComponent(f.split('/').pop()),{method:'DELETE'});
    await fetch('/api/nfc/profile/publish',{method:'POST',headers:h,body:JSON.stringify({published:false})});
    return p.slug;
  })()`);
  const slug = reset;
  console.log("perfil:", slug);

  await ir(`${BASE}/nfc`, 4500);
  await js(AYUDA);
  await js(`(()=>{const b=window.__t.porTexto('button','Saltar guía');b&&b.click();return 'ok'})()`);
  await sleep(700);
  await js("window.__t.arriba();'ok'");

  // 1. Entrar: checklist "Completa tu tarjeta"
  const lista = await rectDe(`document.querySelector('[data-tour="checklist"]')`);
  await foto("inicio", { foco: lista });

  // 2. Identidad
  let r = await tocar(nav("Identidad"), "nav identidad");
  await js("window.__t.arriba();'ok'");
  await sleep(300);
  await foto("identidad", { toque: centro(r) });

  await js(`(()=>{const e=document.querySelector('.nfc-avatar-uploader');window.__t.centrar(e, ${MOVIL ? 0 : -150});return 'ok'})()`);
  r = await rectDe(`document.querySelector('.nfc-avatar-uploader')`);
  await foto("logo-antes", { foco: r, toque: centro(r) });
  await subir('.nfc-avatar-uploader input[type=file]', 0, ["logo.png"]);
  await sleep(2500);
  await foto("logo-despues", { foco: r });

  await escribir(campo("Nombre"), "Barbería Central", "nombre", 2);
  await escribir(campo("A qué te dedicas"), "Cortes clásicos y modernos · Medellín", "frase", 4);
  await escribir(campo("Presentación"), "Más de 10 años cuidando tu estilo. Agenda tu cita por WhatsApp y llega sin filas.", "bio", 12);

  // 3. Contacto
  await escribir(campo("WhatsApp"), "573001234567", "whatsapp", 2);
  await escribir(campo("Mensaje que llega escrito"), "Hola, quiero agendar una cita", "mensaje", 6);
  await escribir(campo("Instagram"), "@barberiacentral", "instagram", 4);

  r = await tocar(`document.querySelector('.nfc-save-bar button')`, "guardar", 1500, "guardar-identidad-antes");
  await foto("guardado-identidad", { toque: centro(r) });

  // 4. Servicios
  r = await tocar(nav("Servicios"), "nav servicios");
  await js("window.__t.arriba();'ok'");
  await sleep(300);
  await foto("servicios", { toque: centro(r) });

  // "¿Qué tipo de negocio es?" es un Select propio: botón + menú de opciones.
  const tipo = `document.querySelector('.nfc-services-head .field button')`;
  r = await tocar(tipo, "tipo", 700, "tipo-antes");
  await foto("tipo-menu", { foco: r, toque: centro(r) });
  const opcion = `window.__t.porTexto('[role=option],li,button', 'Belleza / barbería / spa')`;
  const ro = await rectDe(opcion);
  await js(`(()=>{${opcion}.click();return 'ok'})()`);
  await sleep(700);
  await foto("tipo-despues", { foco: r, toque: centro(ro) });

  // Con la página completa el catálogo va por categorías: se crea "Cortes" con su chip.
  r = await tocar(`window.__t.porTexto('button', 'Cortes')`, "categoria", 900, "categoria-antes");
  await foto("categoria", { toque: centro(r) });
  const qNombre = `document.querySelectorAll('.nfc-quick-add input')[0]`;
  const qPrecio = `document.querySelectorAll('.nfc-quick-add input')[1]`;
  const qBoton = `document.querySelector('.nfc-quick-add button')`;
  await escribir(qNombre, "Corte clásico", "servicio1-nombre", 3, MOVIL ? 0 : 120);
  await escribir(qPrecio, "$25.000", "servicio1-precio", 2, MOVIL ? 0 : 120);
  r = await tocar(qBoton, "agregar", 900, "agregar-antes");
  await foto("servicio1-agregado", { toque: centro(r) });
  for (const [nom, pre] of [["Corte + barba", "$35.000"], ["Corte niño", "$20.000"]]) {
    await js(`(()=>{window.__t.poner(${qNombre},${JSON.stringify(nom)});window.__t.poner(${qPrecio},${JSON.stringify(pre)});return 'ok'})()`);
    await sleep(150);
    await js(`(()=>{${qBoton}.click();return 'ok'})()`);
    await sleep(500);
  }
  await js(`(()=>{const e=document.querySelector('.nfc-services-head');window.__t.centrar(e, ${MOVIL ? 200 : 260});return 'ok'})()`);
  await sleep(400);
  await foto("servicios-lista");

  r = await tocar(`document.querySelector('.nfc-save-bar button')`, "guardar", 1500, "guardar-servicios-antes");
  await foto("guardado-servicios", { toque: centro(r) });

  // 5. Fotos
  r = await tocar(nav("Fotos"), "nav fotos");
  await js("window.__t.arriba();'ok'");
  await sleep(300);
  await foto("fotos", { toque: centro(r) });
  await subir('input[type=file]', 0, ["portada.jpg"]);
  await sleep(3000);
  await foto("fotos-portada");
  await subir('input[type=file]', 1, ["galeria-1.jpg", "galeria-2.jpg"]);
  await sleep(3500);
  await js(`(()=>{const e=document.querySelectorAll('input[type=file]')[1].closest('section,div');window.__t.centrar(e);return 'ok'})()`);
  await sleep(400);
  await foto("fotos-galeria");

  // Los extras opcionales: horarios y lugar (solo se muestran).
  r = await tocar(nav("Horarios y lugar"), "nav horarios");
  await js("window.__t.arriba();'ok'");
  await sleep(300);
  await foto("horarios", { toque: centro(r) });

  // 6. Publicar
  await js("window.__t.arriba();'ok'");
  r = await tocar(boton("Publicar"), "publicar", 1800, "publicar-antes");
  await js("window.__t.arriba();'ok'");
  await foto("publicado", { toque: centro(r) });
  r = await tocar(nav("Compartir y estadísticas"), "nav compartir", 1200);
  await js("window.__t.arriba();'ok'");
  await sleep(300);
  await foto("lista-completa", { toque: centro(r) });

  // 7. Ayuda (sobre Compartir, con la lista ya completa)
  await js("window.__t.arriba();'ok'");
  r = await rectDe(`document.querySelector('[data-tour="header-actions"]')`);
  await foto("ayuda", { foco: r, toque: centro(r) });

  // 8. Perfil público final (siempre como celular)
  if (MOVIL) {
    await ir(`${BASE}/p/${slug}`, 5000);
    await js(AYUDA);
    await foto("publico-arriba");
    await js("window.__t.sc().scrollBy(0, 640);'ok'");
    await sleep(600);
    await foto("publico-servicios");
  }

  writeFileSync(join(SALIDA, "manifest.json"), JSON.stringify({ modo, W, H, DPR, slug, capturas: manifest }, null, 1));
  console.log("listo:", manifest.length, "capturas");
} finally {
  ws.close();
  chrome.kill("SIGKILL");
}
