// Captura de cualquier página como un celular real (Chrome DevTools, sin
// dependencias; Node 22). Abre Chrome headless, captura y lo cierra.
//
// Uso: node captura.mjs '<json>'
//   {"url", "salida": "x.png", "ancho": 390, "alto": 844, "dpr": 3,
//    "espera": 4000, "scroll_texto": "Nuestra carta", "scroll_extra": -40,
//    "js": ["código a ejecutar antes de capturar"], "ocultar_texto": ["Estás en la demo"],
//    "buscar": ["$34.000", "Déjanos tu reseña"], "chrome": "/ruta", "perfil": "/dir"}
// Imprime en stdout: {"rects": {"texto": [x, y, w, h]}} en px css del viewport.
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const cfg = JSON.parse(process.argv[2]);
const W = cfg.ancho || 390, H = cfg.alto || 844, DPR = cfg.dpr || 3;
const port = 9400 + Math.floor(Math.random() * 400);
const perfil = cfg.perfil || mkdtempSync(join(tmpdir(), "estudio-chrome-"));
const chrome = spawn(
  cfg.chrome || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${port}`,
   `--user-data-dir=${perfil}`, `--window-size=${W},${H}`, "about:blank"],
  { stdio: "ignore" }
);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// Vigilante: si la página no responde, cierra Chrome y falla con un mensaje claro.
setTimeout(() => {
  chrome.kill("SIGKILL");
  process.stderr.write(`La página ${cfg.url} no respondió en 75 s\n`);
  process.exit(1);
}, 75000).unref();

try {
  let page;
  for (let i = 0; i < 40 && !page; i++) {
    await sleep(250);
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      page = list.find((t) => t.type === "page");
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
  const evaluar = async (expr) =>
    (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result?.value;

  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: DPR, mobile: true });
  await send("Emulation.setTouchEmulationEnabled", { enabled: true });
  await send("Emulation.setUserAgentOverride", {
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    acceptLanguage: "es-CO,es",
  });
  await send("Emulation.setLocaleOverride", { locale: "es-CO" }).catch(() => {});
  await send("Page.navigate", { url: cfg.url });
  await sleep(cfg.espera || 4000);

  for (const js of cfg.js || []) await evaluar(js);
  if (cfg.ocultar_texto?.length) {
    await evaluar(`(${JSON.stringify(cfg.ocultar_texto)}).forEach(t=>[...document.querySelectorAll('p,div,span')]
      .filter(e=>e.innerText&&e.innerText.trim().startsWith(t)).forEach(e=>e.style.display='none'))`);
  }
  if (cfg.scroll_texto) {
    await evaluar(`(()=>{const t=${JSON.stringify(cfg.scroll_texto)};const e=[...document.querySelectorAll('h1,h2,h3,h4,button,a,p,span')]
      .find(e=>e.innerText&&e.innerText.trim().toLowerCase().startsWith(t.toLowerCase()));
      if(e){e.scrollIntoView({block:'start'});window.scrollBy(0,${cfg.scroll_extra ?? -40});}})()`);
  } else if (cfg.scroll_y) {
    await evaluar(`window.scrollTo(0, ${cfg.scroll_y})`);
  }
  await sleep(900);
  const rects = await evaluar(`(()=>{const out={};for(const t of ${JSON.stringify(cfg.buscar || [])}){
    const els=[...document.querySelectorAll('*')].filter(e=>{const x=(e.innerText||'').trim();return x&&x.toLowerCase().includes(t.toLowerCase())&&x.length<t.length+60});
    els.sort((a,b)=>(a.innerText||'').length-(b.innerText||'').length);
    const e=els.find(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&r.y<innerHeight&&r.y+r.height>0});
    if(e){const r=e.getBoundingClientRect();out[t]=[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)];}}
    return out;})()`);
  const { data } = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(cfg.salida, Buffer.from(data, "base64"));
  process.stdout.write(JSON.stringify({ rects }));
  ws.close();
} finally {
  chrome.kill("SIGTERM");
}
