/* Estudio de video: panel local (vanilla JS, sin compilación). */
const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];
const app = $("#app");
const datos = { marcas: [], plantillas: [], escenas: {}, voces: [], musica: [], ia: null };

// ------------------------------------------------------------------ utilidades
async function api(ruta, opciones = {}) {
  const r = await fetch(ruta, {
    headers: opciones.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...opciones,
    body: opciones.body instanceof FormData ? opciones.body : opciones.body ? JSON.stringify(opciones.body) : undefined,
  });
  const json = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(json.detail || `Error ${r.status}`);
  return json;
}

function aviso(texto) {
  const a = $("#aviso");
  a.textContent = texto;
  a.hidden = false;
  clearTimeout(aviso.t);
  aviso.t = setTimeout(() => (a.hidden = true), 2600);
}

function dialogo(texto, { conInput = false, valor = "" } = {}) {
  return new Promise((ok) => {
    const d = $("#dialogo"), inp = $("#dialogo-input");
    $("#dialogo-txt").textContent = texto;
    inp.hidden = !conInput;
    inp.value = valor;
    d.hidden = false;
    if (conInput) setTimeout(() => inp.focus(), 50);
    const cerrar = (res) => { d.hidden = true; $("#dialogo-si").onclick = $("#dialogo-no").onclick = null; ok(res); };
    $("#dialogo-si").onclick = () => cerrar(conInput ? inp.value.trim() : true);
    $("#dialogo-no").onclick = () => cerrar(null);
  });
}

async function copiar(texto) {
  try { await navigator.clipboard.writeText(texto); }
  catch {
    const t = el("textarea", {}, texto);
    document.body.append(t); t.select(); document.execCommand("copy"); t.remove();
  }
  aviso("Copiado");
}

const creditos = (n) => `${Number(n || 0).toLocaleString("es-CO", { maximumFractionDigits: 2 })} créditos`;

function el(tag, attrs = {}, ...hijos) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v === true ? "" : v);
  }
  for (const h of hijos.flat()) if (h !== null && h !== undefined) n.append(h.nodeType ? h : document.createTextNode(h));
  return n;
}

function plantilla(id) {
  return document.importNode($(`#${id}`).content, true);
}

const marcaPor = (slug) => datos.marcas.find((m) => m.slug === slug);

/** URL para ver un archivo referenciado en un proyecto o marca. */
function urlArchivo(ruta, { marca, pid } = {}) {
  if (!ruta) return null;
  if (ruta.startsWith("marca:")) return `/archivos/marcas/${marca}/${ruta.slice(6)}`;
  if (ruta.startsWith("/")) return null;
  return pid ? `/archivos/proyectos/${pid}/${ruta}` : null;
}

const esVideo = (r) => /\.(mp4|mov|m4v)$/i.test(r || "");

function leer(obj, ruta) {
  return ruta.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);
}

function escribir(obj, ruta, valor) {
  const partes = ruta.split(".");
  let o = obj;
  partes.slice(0, -1).forEach((k) => { if (typeof o[k] !== "object" || o[k] === null) o[k] = {}; o = o[k]; });
  const ultima = partes.at(-1);
  if (valor === "" || valor === null || valor === undefined) delete o[ultima];
  else o[ultima] = valor;
  // limpia objetos vacíos (ej. rotulo sin campos)
  if (partes.length > 1 && Object.keys(o).length === 0) delete obj[partes[0]];
}

// ------------------------------------------------------------------ campos de formulario reutilizables
/** Selector de foto/video: miniaturas de la marca y del proyecto + subir. */
function selectorArchivo({ valor, marca, pid, video = false, multi = false, onCambio }) {
  const caja = el("div", { class: "selector-foto" });
  const m = marcaPor(marca);
  const opciones = [];
  const elegidos = multi ? (valor || []) : valor ? [valor] : [];
  if (!video && m) {
    m.fotos_disponibles.forEach((f) => opciones.push(`marca:${f}`));
    if (multi) ["logo", "tarjeta"].forEach((k) => m[k] && opciones.push(`marca:${m[k]}`));
  }
  (selectorArchivo.archivosProyecto || []).forEach((f) => { if (video ? esVideo(f) : !esVideo(f)) opciones.push(f); });
  elegidos.forEach((v) => { if (!opciones.includes(v)) opciones.unshift(v); });
  for (const op of opciones) {
    const url = urlArchivo(op, { marca, pid });
    const activo = elegidos.includes(op);
    const boton = el("button", { type: "button", class: `op${activo ? " activo" : ""}`, title: op,
      onclick: () => {
        if (multi) onCambio(activo ? elegidos.filter((x) => x !== op) : [...elegidos, op]);
        else onCambio(activo ? "" : op);
      } },
      url ? (esVideo(op) ? el("video", { src: url, muted: true }) : el("img", { src: url })) : "…");
    caja.append(boton);
  }
  const subir = el("input", { type: "file", accept: video ? "video/*" : "image/*", hidden: true,
    onchange: async (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const fd = new FormData();
      fd.append("archivo", f);
      try {
        if (pid) {
          const r = await api(`/api/proyectos/${pid}/archivo`, { method: "POST", body: fd });
          selectorArchivo.archivosProyecto = [...(selectorArchivo.archivosProyecto || []), r.ruta];
          onCambio(multi ? [...elegidos, r.ruta] : r.ruta);
        } else {
          fd.append("tipo", "foto");
          const r = await api(`/api/marcas/${marca}/archivo`, { method: "POST", body: fd });
          Object.assign(marcaPor(marca), r);
          const nueva = `marca:${r.fotos_disponibles.at(-1)}`;
          onCambio(multi ? [...elegidos, nueva] : nueva);
        }
      } catch (err) { aviso(err.message); }
    } });
  caja.append(el("button", { type: "button", class: "op subir", title: "Subir", onclick: () => subir.click() }, "+"), subir);
  return caja;
}

function campo(def, valor, onCambio, ctx = {}) {
  const etiqueta = def.etiqueta || def.id;
  switch (def.tipo) {
    case "area":
    case "lineas": {
      const ta = el("textarea", { rows: def.tipo === "lineas" ? 3 : 5 });
      ta.value = def.tipo === "lineas" ? (valor || []).join("\n") : valor ?? "";
      ta.oninput = () => onCambio(def.tipo === "lineas" ? ta.value.split("\n").filter(Boolean) : ta.value);
      return el("label", {}, etiqueta, ta);
    }
    case "modo_tour": {
      const modos = [["plano", "Plano · gratis (acercamiento suave)"], ["profundidad", "Profundidad real · gratis"],
        ["ia", "✦ IA · clip animado de la foto (Kling)"], ["ia_paso", "✦ IA · paso de esta foto a la siguiente"]];
      const s = el("select", {}, ...modos.map(([v, t]) => el("option", { value: v }, t)));
      s.value = valor || "plano";
      s.onchange = () => onCambio(s.value);
      return el("label", {}, etiqueta, s);
    }
    case "modelo_video":
    case "modelo_imagen": {
      const lista = datos.ia?.[def.tipo === "modelo_video" ? "video" : "imagen"] || [];
      const costo = (m) => (def.tipo === "modelo_video" ? `${m.costo_5s} cr / 5 s` : `${m.costo} cr`);
      const opciones = lista.map((m) => el("option", { value: m.id, title: m.nota || "" }, `${m.nombre} · ${costo(m)}${m.recomendado ? " ★" : ""}`));
      if (def.automatico) opciones.unshift(el("option", { value: "" }, "Automático (según el modo)"));
      const s = el("select", {}, ...opciones);
      s.value = valor || (def.automatico ? "" : lista.find((m) => m.recomendado)?.id || "");
      if (!valor && s.value) setTimeout(() => onCambio(s.value));
      const nota = el("span", { class: "sutil" }, lista.find((m) => m.id === s.value)?.nota || "");
      s.onchange = () => { onCambio(s.value); nota.textContent = lista.find((m) => m.id === s.value)?.nota || ""; };
      return el("label", {}, etiqueta, s, nota);
    }
    case "fotos":
    case "foto":
    case "video": {
      const contenedor = el("label", {}, etiqueta);
      const pintar = (v) => {
        contenedor.querySelector(".selector-foto")?.remove();
        contenedor.append(selectorArchivo({ valor: v, marca: ctx.marca, pid: ctx.pid, video: def.tipo === "video", multi: def.tipo === "fotos",
          onCambio: (nv) => { onCambio(nv); pintar(nv); } }));
      };
      pintar(valor);
      return contenedor;
    }
    case "bool": {
      const cb = el("input", { type: "checkbox" });
      cb.checked = !!valor;
      cb.onchange = () => onCambio(cb.checked || "");
      return el("label", { class: "check" }, cb, etiqueta);
    }
    case "opciones": {
      const s = el("select", {}, el("option", { value: "" }, "—"), ...def.opciones.map((o) => el("option", { value: o }, o)));
      s.value = valor ?? "";
      s.onchange = () => onCambio(typeof def.opciones[0] === "number" && s.value !== "" ? Number(s.value) : s.value);
      return el("label", {}, etiqueta, s);
    }
    case "par": {
      const v = valor || def.defecto || ["", ""];
      const a = el("input", { type: "number", step: "0.01", value: v[0] }), b = el("input", { type: "number", step: "0.01", value: v[1] });
      const cambio = () => onCambio(a.value === "" && b.value === "" ? "" : [parseFloat(a.value || 0), parseFloat(b.value || 0)]);
      a.oninput = b.oninput = cambio;
      return el("label", {}, etiqueta, el("div", { class: "dos" }, a, b));
    }
    case "numero": {
      const i = el("input", { type: "number", step: "any", value: valor ?? def.defecto ?? "" });
      i.oninput = () => onCambio(i.value === "" ? "" : parseFloat(i.value));
      return el("label", {}, etiqueta, i);
    }
    case "lista_texto": {
      const i = el("input", { value: (valor || []).join(", ") });
      i.oninput = () => onCambio(i.value.split(",").map((x) => x.trim()).filter(Boolean));
      return el("label", {}, etiqueta, i);
    }
    case "lista": {
      const caja = el("div", {}, el("h4", {}, etiqueta));
      const items = Array.isArray(valor) ? valor : [];
      const pintar = () => {
        $$(".item-lista, .agregar", caja).forEach((n) => n.remove());
        items.forEach((item, i) => {
          const tarjeta = el("div", { class: "item-lista" },
            el("button", { type: "button", class: "peligro", onclick: () => { items.splice(i, 1); onCambio(items); pintar(); } }, "Quitar"));
          def.campos.forEach((sub) => tarjeta.append(campo(sub, item[sub.id], (v) => { item[sub.id] = v; onCambio(items); }, ctx)));
          caja.append(tarjeta);
        });
        caja.append(el("button", { type: "button", class: "secundario agregar",
          onclick: () => { items.push(Object.fromEntries(def.campos.filter((c) => c.defecto !== undefined).map((c) => [c.id, c.defecto]))); onCambio(items); pintar(); } },
          "+ Agregar"));
      };
      pintar();
      return caja;
    }
    default: {
      const i = el("input", { type: def.tipo === "url" ? "url" : "text", value: valor ?? "" ,
        placeholder: def.tipo === "precio" ? "$26.000" : "" });
      i.oninput = () => onCambio(i.value);
      return el("label", {}, etiqueta, i);
    }
  }
}

// ------------------------------------------------------------------ vista: videos
async function vistaVideos() {
  app.replaceChildren(plantilla("t-videos"));
  $("#btn-nuevo").onclick = () => (location.hash = "#nuevo");
  const lista = $("#lista-videos");
  const proyectos = await api("/api/proyectos");
  if (!proyectos.length) {
    lista.append(el("div", { class: "vacio" }, "Todavía no hay videos. Crea el primero con «Nuevo video»."));
    return;
  }
  for (const p of proyectos) {
    const m = marcaPor(p.marca);
    const etapa = p.estado?.etapa;
    const estado = etapa === "listo" ? "Listo" : etapa === "error" ? "Error" : etapa === "nuevo" ? "Sin generar" : `${p.estado.pct}% · ${etapa}`;
    lista.append(el("div", { class: "tarjeta-video", onclick: () => (location.hash = `#editor/${p.id}`) },
      el("div", { class: "poster" }, p.video ? el("video", { src: `${p.video}#t=1`, muted: true, preload: "metadata" }) : "Sin video"),
      el("div", { class: "info" },
        el("strong", {}, p.nombre),
        el("span", { class: "sutil" }, `${m?.nombre || p.marca} · ${p.formato}`), el("br"),
        el("span", { class: `etiqueta${etapa === "error" ? " error" : ""}` }, p.estado?.borrador ? "Borrador" : estado),
        p.motor === "higgsfield" ? el("span", { class: "etiqueta ia" }, "IA") : null)));
  }
}

// ------------------------------------------------------------------ vista: nuevo
async function vistaNuevo() {
  app.replaceChildren(plantilla("t-nuevo"));
  const estado = { marca: datos.marcas[0]?.slug, plantilla: datos.plantillas[0]?.id, formato: "9:16", motor: "gratis", datos: {} };
  selectorArchivo.archivosProyecto = [];

  const pintarMarcas = () => {
    const c = $("#elegir-marca");
    c.replaceChildren(...datos.marcas.map((m) => el("button", { class: `chip${m.slug === estado.marca ? " activo" : ""}`,
      onclick: () => { estado.marca = m.slug; pintarMarcas(); pintarFormulario(); } },
      m.logo ? el("img", { src: `/archivos/marcas/${m.slug}/${m.logo}` }) : null, m.nombre)));
  };
  const pintarPlantillas = () => {
    const c = $("#elegir-plantilla");
    c.replaceChildren(...datos.plantillas.map((p) => el("button", { class: `tarjeta-plantilla${p.id === estado.plantilla ? " activo" : ""}`,
      onclick: () => { estado.plantilla = p.id; estado.datos = {}; $("#guion-nuevo").value = ""; pintarPlantillas(); pintarFormulario(); } },
      el("strong", {}, p.nombre), el("span", {}, p.descripcion))));
  };
  const pintarFormulario = () => {
    const p = datos.plantillas.find((x) => x.id === estado.plantilla);
    const f = $("#form-plantilla");
    f.replaceChildren();
    for (const c of p.campos) {
      if (c.id === "guion") continue; // el guion va en su propia caja
      if (estado.datos[c.id] === undefined && c.defecto !== undefined) estado.datos[c.id] = c.defecto;
      if (c.tipo === "lista" && !estado.datos[c.id]) estado.datos[c.id] = [{}, {}];
      f.append(campo(c, estado.datos[c.id], (v) => (estado.datos[c.id] = v), { marca: estado.marca }));
    }
    if (p.id === "libre" && !$("#guion-nuevo").value) $("#guion-nuevo").value = p.campos[0].defecto;
  };
  $$("#elegir-formato .chip").forEach((b) => (b.onclick = () => {
    estado.formato = b.dataset.f;
    $$("#elegir-formato .chip").forEach((x) => x.classList.toggle("activo", x === b));
  }));
  $$("#elegir-motor-nuevo .chip").forEach((b) => (b.onclick = () => {
    estado.motor = b.dataset.m;
    $$("#elegir-motor-nuevo .chip").forEach((x) => x.classList.toggle("activo", x === b));
  }));
  $("#btn-sugerir").onclick = async () => {
    try {
      const r = await api(`/api/plantillas/${estado.plantilla}/guion`, { method: "POST", body: { marca: estado.marca, datos: estado.datos } });
      $("#guion-nuevo").value = r.guion;
    } catch (e) { aviso(e.message); }
  };
  $("#btn-crear").onclick = async (ev) => {
    const guion = $("#guion-nuevo").value.trim();
    if (!guion) { aviso("Escribe el guion o pulsa «Sugerir guion»"); return; }
    ev.target.disabled = true;
    try {
      const r = await api("/api/proyectos", { method: "POST",
        body: { plantilla: estado.plantilla, marca: estado.marca, datos: { ...estado.datos, guion, formato: estado.formato, motor: estado.motor } } });
      location.hash = `#editor/${r.id}`;
    } catch (e) { aviso(e.message); ev.target.disabled = false; }
  };
  pintarMarcas();
  pintarPlantillas();
  pintarFormulario();
}

// ------------------------------------------------------------------ vista: editor
let sondeo = null;

async function vistaEditor(pid) {
  app.replaceChildren(plantilla("t-editor"));
  clearInterval(sondeo);
  const r = await api(`/api/proyectos/${pid}`);
  const p = r.proyecto;
  selectorArchivo.archivosProyecto = r.archivos;
  const ctx = { marca: p.marca, pid };

  $("#nombre-proyecto").value = p.nombre || pid;
  $("#guion").value = p.guion?.texto || "";
  const marca = marcaPor(p.marca);
  const vozMarca = { voz: "es-CO-GonzaloNeural", velocidad: "+12%", ...(marca?.voz || {}) };
  const voz = { ...vozMarca, ...(p.voz || {}) };
  $("#voz").replaceChildren(...datos.voces.map((v) => el("option", { value: v.id }, `${v.id.replace("Neural", "")} · ${v.genero === "Male" ? "hombre" : "mujer"}`)));
  $("#voz").value = voz.voz;
  $("#velocidad").value = voz.velocidad;
  $("#formato").value = p.formato || "9:16";
  $("#musica").replaceChildren(...datos.musica.map((m) => el("option", { value: m }, m === "sintetica" ? "Base sintética (gratis)" : m === "ninguna" ? "Sin música" : m)));
  $("#musica").value = p.audio?.musica || "sintetica";
  $("#cap-subtitulos").checked = p.capas?.subtitulos !== false;
  $("#cap-logo").checked = p.capas?.logo !== false;
  const et = p.capas?.etiqueta || {};
  $("#et-desde").value = (et.desde || "").replace(/^@/, "");
  $("#et-grande").value = et.grande || "";
  $("#et-pequeno").value = et.pequeno || "";

  const usaIA = (e) => !!datos.escenas[e.tipo]?.ia || (e.tipo === "tour" && (e.params?.paradas || []).some((x) => /^ia/.test(x.modo || e.params?.modo || "")));
  // ---- motor (gratis / Higgsfield)
  const iaCfg = { motor: "gratis", via: "claude", ...(p.ia || {}) };
  iaCfg.voz = { activa: true, voice_id: "75e72cd5-011b-4130-a474-e8b1ab341f04", nombre: "Marisol", tempo: 1.1, ...(iaCfg.voz || {}) };
  const voces = datos.ia?.voces || [];
  $("#ia-voz-id").replaceChildren(...voces.map((v) => el("option", { value: v.id }, `${v.nombre} · ${v.genero}${v.recomendada ? " ★" : ""}`)));
  $("#ia-voz-id").value = iaCfg.voz.voice_id;
  $("#ia-tempo").value = String(iaCfg.voz.tempo);
  $("#ia-voz").checked = iaCfg.voz.activa !== false;
  $("#ia-via").value = iaCfg.via;
  if (!datos.ia?.api_disponible) $('#ia-via option[value="api"]').textContent = "API directa (falta HF_KEY en .env)";
  const esIA = () => iaCfg.motor === "higgsfield";
  const pintarMotor = () => {
    $$("#elegir-motor .chip").forEach((b) => b.classList.toggle("activo", b.dataset.m === iaCfg.motor));
    $("#motor-ia").hidden = !esIA();
    $("#ia-voz-opts").hidden = !$("#ia-voz").checked;
    $("#motor-nota").textContent = esIA()
      ? "Eliges qué partes hace la IA. Mientras el pedido no llegue, el video sale como borrador gratis."
      : "Todo gratis en tu Mac: voz neuronal, fotos con movimiento, texto, 3D y capturas.";
    $("#etq-voz").textContent = esIA() && $("#ia-voz").checked ? "Voz del borrador (gratis)" : "Voz";
  };
  $$("#elegir-motor .chip").forEach((b) => (b.onclick = async () => {
    iaCfg.motor = b.dataset.m;
    pintarMotor(); pintarEscenas();
    if (esIA()) await refrescarIA(true);
  }));
  $("#ia-voz").onchange = () => { pintarMotor(); refrescarIA(true); };
  $("#ia-voz-id").onchange = () => refrescarIA(true);
  $("#ia-tempo").onchange = () => refrescarIA(true);
  $("#btn-muestra-ia").onclick = () => {
    const v = voces.find((x) => x.id === $("#ia-voz-id").value);
    if (!v?.preview) return;
    const a = $("#audio-ia");
    a.src = v.preview; a.hidden = false; a.play();
  };
  $("#ia-via").onchange = () => { $("#ia-chatgpt").hidden = true; refrescarIA(true); };

  const etiquetaTarea = { voz: "Voz", imagen: "Imagen", video: "Clip" };
  const pintarResumenIA = (info) => {
    const c = $("#ia-resumen");
    if (!info.tareas.length) { c.replaceChildren(el("p", { class: "sutil" }, "Activa la voz premium o agrega escenas «Clip de video IA» / «Imagen IA».")); return; }
    const ped = info.pedido;
    const estadoPedido = ped ? { pendiente: "Pedido enviado, esperando", en_proceso: "Generando", listo: "Piezas listas", error: "Con errores" }[ped.estado] || ped.estado : "Sin pedido";
    c.replaceChildren(
      el("div", { class: "costo" }, el("strong", {}, info.costo ? `Falta: ${creditos(info.costo)}` : "Todo listo"), el("span", { class: "sutil" }, ` · ${estadoPedido}`)),
      el("ul", { class: "tareas" }, ...info.tareas.map((t) => {
        const est = ped?.tareas?.find((x) => x.id === t.id)?.estado || (t.listo ? "listo" : "pendiente");
        const subir = el("input", { type: "file", hidden: true, accept: t.tipo === "voz" ? "audio/*" : t.tipo === "video" ? "video/*" : "image/*",
          onchange: async (ev) => {
            const f = ev.target.files[0]; if (!f) return;
            const fd = new FormData(); fd.append("tarea", t.id); fd.append("archivo", f);
            try { await api(`/api/proyectos/${pid}/ia/resultado`, { method: "POST", body: fd }); aviso("Resultado guardado"); refrescarIA(); }
            catch (e) { aviso(e.message); }
          } });
        return el("li", { class: `tarea ${t.listo ? "listo" : est}` },
          el("span", { class: "punto-estado" }),
          el("span", {}, `${etiquetaTarea[t.tipo]}${t.escena !== null && t.escena !== undefined ? ` · escena ${t.escena + 1}` : ""} · ${t.nombre}`),
          el("span", { class: "sutil" }, t.listo ? "listo" : creditos(t.costo)),
          t.listo ? null : el("button", { class: "icono", type: "button", title: "Subir el resultado descargado", onclick: () => subir.click() }, "Subir resultado"), subir);
      })),
      ...(info.revision || []).map((r) => el("p", { class: "aviso-ia" }, `${r.escena !== null ? `Escena ${r.escena + 1}: ` : ""}${r.avisos.join(" ")}`)),
    );
    $("#btn-pedido").disabled = !info.costo;
    $("#btn-pedido").textContent = ped && ped.estado !== "listo" ? "Actualizar pedido IA" : "Enviar pedido IA";
  };
  let sondeoIA = null;
  const refrescarIA = async (guardarAntes = false) => {
    if (!esIA()) return;
    try {
      if (guardarAntes) await guardar();
      const info = await api(`/api/proyectos/${pid}/ia`);
      pintarResumenIA(info);
      clearInterval(sondeoIA);
      if (info.pedido && !["listo", "vacio"].includes(info.pedido.estado)) {
        sondeoIA = setInterval(async () => {
          if (!location.hash.includes(pid)) return clearInterval(sondeoIA);
          const nuevo = await api(`/api/proyectos/${pid}/ia`);
          pintarResumenIA(nuevo);
          if (!nuevo.costo) { clearInterval(sondeoIA); aviso("Piezas IA listas: pulsa «Generar video»"); pintarEscenas(); }
        }, 5000);
      }
    } catch (e) { aviso(e.message); }
  };
  $("#btn-ia-refrescar").onclick = () => refrescarIA(true);
  $("#btn-pedido").onclick = async () => {
    try {
      await guardar();
      const via = $("#ia-via").value;
      const ped = await api(`/api/proyectos/${pid}/ia/pedido`, { method: "POST", body: { via } });
      if (via === "chatgpt") {
        const t = await api(`/api/proyectos/${pid}/ia/chatgpt`);
        $("#ia-chatgpt").hidden = false;
        $("#ia-chatgpt-texto").value = t.texto;
        $("#ia-chatgpt-fotos").replaceChildren(...t.archivos.map((a) => el("a", { class: "min", href: `/api/ia/archivo?ruta=${encodeURIComponent(a)}`, download: a.split("/").at(-1), title: "Descargar para adjuntar" },
          el("img", { src: `/api/ia/archivo?ruta=${encodeURIComponent(a)}` }), a.split("/").at(-1))));
        copiar(t.texto);
      } else if (via === "claude") {
        aviso(`Pedido listo (${creditos(ped.costo)}). Dile a Claude: «procesa los pedidos IA»`);
      } else aviso("Pedido enviado a la API");
      refrescarIA();
      contarPedidos();
    } catch (e) { aviso(e.message); }
  };
  $("#btn-copiar-chatgpt").onclick = () => copiar($("#ia-chatgpt-texto").value);
  if (p.notas_asistente) { $("#notas-asistente").hidden = false; $("#notas-asistente").textContent = `Notas del asistente: ${p.notas_asistente}`; }

  const frases = () => ($("#guion").value.match(/[^.!?]+[.!?]?/g) || []).map((s) => s.trim()).filter(Boolean)
    .flatMap((s) => [s.split(/\s+/).slice(0, 2).join(" ").replace(/[¿¡,:]/g, ""), s.split(/\s+/).slice(0, 3).join(" ").replace(/[¿¡,:]/g, "")]);

  const pintarEscenas = () => {
    const c = $("#escenas");
    c.replaceChildren();
    const dl = el("datalist", { id: "frases" }, ...[...new Set(frases())].map((f) => el("option", { value: f })));
    c.append(dl);
    p.escenas.forEach((e, i) => {
      e.params = e.params || {};
      const def = datos.escenas[e.tipo] || { nombre: e.tipo, campos: [] };
      const tipo = el("select", {}, ...Object.entries(datos.escenas).filter(([k, v]) => !v.ia || esIA() || k === e.tipo)
        .map(([k, v]) => el("option", { value: k }, v.ia ? `✦ ${v.nombre}` : v.nombre)));
      tipo.value = e.tipo;
      tipo.onchange = () => { e.tipo = tipo.value; e.params = {}; pintarEscenas(); };
      const mover = (d) => { const j = i + d; if (j < 0 || j >= p.escenas.length) return; [p.escenas[i], p.escenas[j]] = [p.escenas[j], p.escenas[i]]; pintarEscenas(); };
      const modo = el("select", {}, el("option", { value: "frase" }, "Hasta que la voz diga"), el("option", { value: "seg" }, "Segundos fijos"), el("option", { value: "fin" }, "Hasta el final de la voz"));
      modo.value = e.duracion !== undefined ? "seg" : e.hasta === "fin_voz" ? "fin" : "frase";
      const valorDur = el("input", { list: "frases" });
      const sincronizar = () => {
        valorDur.hidden = modo.value === "fin";
        valorDur.value = modo.value === "seg" ? (e.duracion ?? 3) : modo.value === "frase" ? (e.hasta || "").replace(/^@/, "") : "";
        valorDur.type = modo.value === "seg" ? "number" : "text";
      };
      modo.onchange = () => {
        delete e.duracion; delete e.hasta;
        if (modo.value === "seg") e.duracion = 3;
        else if (modo.value === "fin") { e.hasta = "fin_voz"; e.extra = e.extra ?? 1; }
        sincronizar();
      };
      valorDur.oninput = () => {
        if (modo.value === "seg") e.duracion = parseFloat(valorDur.value || 0);
        else e.hasta = `@${valorDur.value.trim()}`;
      };
      sincronizar();
      const json = el("textarea", { class: "json", rows: 6 });
      json.value = JSON.stringify(e.params, null, 2);
      json.onchange = () => { try { e.params = JSON.parse(json.value); pintarEscenas(); } catch { aviso("JSON inválido"); } };
      const tarjeta = el("div", { class: "escena" },
        el("div", { class: "escena-cab" }, el("span", { class: "num" }, i + 1), tipo,
          el("button", { class: "icono", title: "Subir", onclick: () => mover(-1) }, "↑"),
          el("button", { class: "icono", title: "Bajar", onclick: () => mover(1) }, "↓"),
          el("button", { class: "icono", title: "Quitar", onclick: async () => { if (await dialogo(`¿Quitar la escena ${i + 1}?`)) { p.escenas.splice(i, 1); pintarEscenas(); } } }, "✕")),
        el("div", { class: "dur" }, modo, valorDur));
      if (def.ia) tarjeta.classList.add("escena-ia");
      if (esIA() && e.tipo === "imagen") {
        tarjeta.append(el("button", { class: "secundario convertir", type: "button", onclick: () => {
          const { archivo, rotulo, foco } = e.params;
          e.tipo = "clip_ia";
          e.params = { imagen: archivo, prompt: "", duracion_clip: 5, ...(rotulo ? { rotulo } : {}), ...(foco ? { foco } : {}) };
          pintarEscenas();
          aviso("Escribe qué pasa en el clip (en inglés): sujeto, acción, cámara y luz");
        } }, "✦ Convertir en clip IA"));
      }
      const infoIA = def.ia || e.tipo === "tour" ? el("div", { class: "info-ia" }) : null;
      const revisarIA = async () => {
        if (!infoIA) return;
        try {
          const r = await api(`/api/proyectos/${pid}/ia/revisar`, { method: "POST", body: { escena: e, formato: $("#formato").value } });
          if (e.tipo === "tour" && !r.tareas.length && !r.avisos.length) { infoIA.replaceChildren(); return; }
          infoIA.replaceChildren(
            el("strong", {}, r.listo ? "✓ Piezas IA listas" : `Costo IA de este tour: ${creditos(r.costo)}`),
            ...r.avisos.map((a) => el("p", { class: "aviso-ia" }, a)));
        } catch { /* sin conexión: no se revisa */ }
      };
      let tRevisar;
      def.campos.forEach((cdef) => tarjeta.append(campo(cdef, leer(e.params, cdef.id), (v) => {
        escribir(e.params, cdef.id, v);
        json.value = JSON.stringify(e.params, null, 2);
        if (!esIA() && usaIA(e)) { iaCfg.motor = "higgsfield"; pintarMotor(); aviso("Usas IA en este tour: se activó el motor Higgsfield"); refrescarIA(true); }
        clearTimeout(tRevisar); tRevisar = setTimeout(revisarIA, 600);
      }, ctx)));
      if (infoIA) { tarjeta.append(infoIA); revisarIA(); }
      tarjeta.append(el("details", {}, el("summary", {}, "JSON avanzado"), json));
      c.append(tarjeta);
    });
  };
  pintarEscenas();
  $("#guion").addEventListener("change", pintarEscenas);
  $("#btn-agregar").onclick = () => {
    const pos = p.escenas.findIndex((e) => e.tipo === "cierre");
    p.escenas.splice(pos < 0 ? p.escenas.length : pos, 0, { tipo: "imagen", duracion: 3, params: {} });
    pintarEscenas();
  };

  const recoger = () => {
    p.nombre = $("#nombre-proyecto").value.trim() || pid;
    p.guion = { ...(p.guion || {}), texto: $("#guion").value };
    p.formato = $("#formato").value;
    const v = { voz: $("#voz").value, velocidad: $("#velocidad").value };
    if (v.voz !== vozMarca.voz || v.velocidad !== vozMarca.velocidad) p.voz = v; else delete p.voz;
    p.audio = { ...(p.audio || {}), musica: $("#musica").value };
    const vozIA = voces.find((x) => x.id === $("#ia-voz-id").value);
    p.ia = { ...iaCfg, via: $("#ia-via").value,
      voz: { activa: $("#ia-voz").checked, voice_id: $("#ia-voz-id").value, nombre: vozIA?.nombre || "", tempo: parseFloat($("#ia-tempo").value) } };
    if (!esIA() && !p.escenas.some(usaIA)) p.ia.motor = "gratis";
    p.capas = { ...(p.capas || {}), subtitulos: $("#cap-subtitulos").checked, logo: $("#cap-logo").checked };
    const desde = $("#et-desde").value.trim();
    if (desde && $("#et-grande").value.trim()) {
      p.capas.etiqueta = { desde: `@${desde}`, dur: 1.6, grande: $("#et-grande").value.trim(), pequeno: $("#et-pequeno").value.trim() };
    } else delete p.capas.etiqueta;
    return p;
  };
  const guardar = async () => { await api(`/api/proyectos/${pid}`, { method: "PUT", body: recoger() }); };

  $("#btn-guardar").onclick = async () => { try { await guardar(); aviso("Guardado"); refrescarIA(); } catch (e) { aviso(e.message); } };
  $("#btn-duplicar").onclick = async () => {
    await guardar();
    const n = await api(`/api/proyectos/${pid}/duplicar`, { method: "POST" });
    location.hash = `#editor/${n.id}`;
  };
  $("#btn-probar-voz").onclick = async () => {
    const texto = ($("#guion").value.match(/[^.!?]+[.!?]/) || [$("#guion").value])[0].slice(0, 200);
    try {
      const rr = await api("/api/voz/prueba", { method: "POST", body: { voz: $("#voz").value, velocidad: $("#velocidad").value, texto } });
      const a = $("#audio-prueba");
      a.src = rr.url; a.hidden = false; a.play();
    } catch (e) { aviso(e.message); }
  };

  const mostrarEstado = (est, video) => {
    const prog = $("#progreso"), err = $("#error"), btn = $("#btn-generar");
    const enCurso = !["listo", "error", "nuevo"].includes(est.etapa);
    prog.hidden = !enCurso;
    btn.disabled = enCurso;
    btn.textContent = enCurso ? "Generando…" : "Generar video";
    $(".barra-p span", prog).style.width = `${est.pct || 0}%`;
    $("#progreso-txt").textContent = est.mensaje || "";
    err.hidden = est.etapa !== "error";
    $("#progreso-txt").classList.toggle("borrador", !!est.borrador);
    if (!enCurso && est.borrador) { prog.hidden = false; $(".barra-p", prog).hidden = true; } else $(".barra-p", prog).hidden = false;
    err.textContent = est.etapa === "error" ? `No se pudo generar: ${est.mensaje}` : "";
    if (video) {
      const v = $("#video");
      if (v.getAttribute("src") !== video) v.src = video;
      v.hidden = false;
      const d = $("#descargar");
      d.href = video; d.hidden = false; d.setAttribute("download", `${pid}.mp4`);
    }
    return enCurso;
  };
  const seguir = () => {
    clearInterval(sondeo);
    sondeo = setInterval(async () => {
      if (!location.hash.includes(pid)) return clearInterval(sondeo);
      const est = await api(`/api/proyectos/${pid}/estado`);
      if (!mostrarEstado(est)) {
        clearInterval(sondeo);
        const nuevo = await api(`/api/proyectos/${pid}`);
        mostrarEstado(nuevo.estado, nuevo.video);
        if (est.etapa === "listo") aviso(est.borrador ? "Borrador listo: faltan piezas IA" : "¡Video listo!");
      }
    }, 1500);
  };
  $("#btn-generar").onclick = async () => {
    try {
      await guardar();
      await api(`/api/proyectos/${pid}/generar`, { method: "POST" });
      mostrarEstado({ etapa: "en_cola", pct: 0, mensaje: "En cola" });
      seguir();
    } catch (e) { aviso(e.message); }
  };
  if (mostrarEstado(r.estado, r.video)) seguir();
  pintarMotor();
  refrescarIA();

  // archivos del proyecto
  const pintarArchivos = () => $("#lista-archivos").replaceChildren(...selectorArchivo.archivosProyecto.map((f) => {
    const url = urlArchivo(f, ctx);
    return el("div", { class: "min", title: f }, esVideo(f) ? el("video", { src: url, muted: true }) : el("img", { src: url }), f.split("/").at(-1));
  }));
  pintarArchivos();
  $("#subir-proyecto").onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("archivo", f);
    try {
      const rr = await api(`/api/proyectos/${pid}/archivo`, { method: "POST", body: fd });
      selectorArchivo.archivosProyecto.push(rr.ruta);
      pintarArchivos();
      pintarEscenas();
      aviso("Archivo subido: elígelo en una escena");
    } catch (err) { aviso(err.message); }
  };
}

// ------------------------------------------------------------------ vista: asistente (idea -> proyecto)
async function vistaAsistente() {
  app.replaceChildren(plantilla("t-asistente"));
  const est = { marca: datos.marcas[0]?.slug };
  const pintarMarcas = () => $("#as-marca").replaceChildren(...datos.marcas.map((m) => el("button", { class: `chip${m.slug === est.marca ? " activo" : ""}`,
    onclick: () => { est.marca = m.slug; pintarMarcas(); } }, m.logo ? el("img", { src: `/archivos/marcas/${m.slug}/${m.logo}` }) : null, m.nombre)));
  pintarMarcas();
  $("#as-motor").onchange = () => ($("#as-presupuesto-l").hidden = $("#as-motor").value !== "higgsfield");
  const pedido = () => ({
    idea: $("#as-idea").value.trim(), marca: est.marca, formato: $("#as-formato").value,
    duracion: parseFloat($("#as-duracion").value || 20), motor: $("#as-motor").value,
    presupuesto: $("#as-motor").value === "higgsfield" ? parseFloat($("#as-presupuesto").value || 0) : 0,
  });
  $("#as-chatgpt").onclick = async () => {
    const d = pedido();
    if (!d.idea) return aviso("Escribe la idea");
    try {
      const r = await api("/api/asistente/brief", { method: "POST", body: d });
      await copiar(r.brief);
      $("#as-paso2").hidden = false;
      $("#as-respuesta").focus();
      aviso("Brief copiado: pégalo en ChatGPT");
    } catch (e) { aviso(e.message); }
  };
  $("#as-crear").onclick = async (ev) => {
    const d = pedido();
    ev.target.disabled = true;
    try {
      const r = await api("/api/asistente/crear", { method: "POST", body: { ...d, respuesta: $("#as-respuesta").value } });
      const caja = $("#as-resultado");
      caja.replaceChildren(
        ...(r.errores || []).map((x) => el("p", { class: "error" }, x)),
        ...(r.avisos || []).map((x) => el("p", { class: "aviso-ia" }, x)));
      if (r.ok) {
        caja.append(el("p", {}, `Proyecto creado${r.costo ? ` · IA: ${creditos(r.costo)}` : ""}. `,
          el("a", { href: `#editor/${r.id}` }, "Abrir el editor →")));
        if (!(r.avisos || []).length) location.hash = `#editor/${r.id}`;
      } else if (r.errores?.length) caja.prepend(el("p", { class: "sutil" }, "Corrige esto en ChatGPT (pídele que arregle estos errores) y vuelve a pegar:"));
    } catch (e) { aviso(e.message); }
    ev.target.disabled = false;
  };
  $("#as-claude").onclick = async () => {
    const d = pedido();
    if (!d.idea) return aviso("Escribe la idea");
    try { await api("/api/asistente/ideas", { method: "POST", body: d }); aviso("Idea guardada. Dile a Claude: «procesa las ideas»"); pintarIdeas(); }
    catch (e) { aviso(e.message); }
  };
  const pintarIdeas = async () => {
    const ideas = await api("/api/asistente/ideas");
    $("#as-ideas").replaceChildren(...(ideas.length ? ideas.slice(0, 12).map((i) => el("div", { class: "fila-idea" },
      el("span", { class: `etiqueta${i.estado === "hecha" ? "" : " pendiente"}` }, i.estado === "hecha" ? "Hecha" : "Pendiente"),
      el("span", {}, `${i.idea.slice(0, 90)}${i.idea.length > 90 ? "…" : ""} · ${marcaPor(i.marca)?.nombre || i.marca}`),
      i.proyecto ? el("a", { href: `#editor/${i.proyecto}` }, "Abrir") : null)) : [el("p", { class: "sutil" }, "Ninguna todavía.")]));
  };
  pintarIdeas();
  api("/api/ia/guia").then((g) => ($("#as-guia").textContent = g.texto));
}

// ------------------------------------------------------------------ vista: pedidos IA
async function vistaPedidos() {
  app.replaceChildren(plantilla("t-pedidos"));
  const lista = await api("/api/ia/pedidos");
  const nombres = { claude: "Claude", chatgpt: "ChatGPT", api: "API" };
  const estados = { pendiente: "Pendiente", en_proceso: "Generando", listo: "Listo", error: "Con errores", vacio: "Vacío" };
  $("#lista-pedidos").replaceChildren(...(lista.length ? lista.map((p) => el("div", { class: "panel pedido" },
    el("div", { class: "encabezado-mini" },
      el("strong", {}, p.nombre),
      el("span", { class: `etiqueta${p.estado === "error" ? " error" : p.estado === "listo" ? "" : " pendiente"}` }, estados[p.estado] || p.estado)),
    el("p", { class: "sutil" }, `${marcaPor(p.marca)?.nombre || p.marca} · vía ${nombres[p.via] || p.via} · ${p.conteo.listo}/${p.total} piezas · ${p.estado === "listo" ? "pagado" : `falta ${creditos(p.costo)}`} · ${p.creado}`),
    el("ul", { class: "tareas" }, ...p.tareas.map((t) => el("li", { class: `tarea ${t.estado}` }, el("span", { class: "punto-estado" }),
      el("span", {}, `${{ voz: "Voz", imagen: "Imagen", video: "Clip" }[t.tipo]} · ${t.nombre}`),
      el("span", { class: "sutil" }, t.error ? `Error: ${t.error}` : t.estado)))),
    el("a", { href: `#editor/${p.pid}` }, "Abrir el video →"))) : [el("div", { class: "vacio" }, "No hay pedidos IA. Se crean desde el editor con el motor Higgsfield.")]));
}

async function contarPedidos() {
  try {
    const n = (await api("/api/ia/pedidos")).filter((p) => !["listo", "vacio"].includes(p.estado)).length;
    $("#cuenta-pedidos").hidden = !n;
    $("#cuenta-pedidos").textContent = n;
  } catch { /* sin servidor */ }
}

// ------------------------------------------------------------------ vista: marcas
async function vistaMarcas(slugSel) {
  app.replaceChildren(plantilla("t-marcas"));
  const seleccion = slugSel || datos.marcas[0]?.slug;
  $("#lista-marcas").replaceChildren(...datos.marcas.map((m) => el("div", { class: `item${m.slug === seleccion ? " activo" : ""}`,
    onclick: () => vistaMarcas(m.slug) }, m.logo ? el("img", { src: `/archivos/marcas/${m.slug}/${m.logo}?${Date.now()}` }) : el("span", { class: "punto" }), m.nombre)));
  $("#btn-nueva-marca").onclick = async () => {
    const nombre = await dialogo("Nombre del negocio", { conInput: true });
    if (!nombre) return;
    try {
      const m = await api("/api/marcas", { method: "POST", body: { nombre } });
      datos.marcas.push(m);
      vistaMarcas(m.slug);
    } catch (e) { aviso(e.message); }
  };
  const m = marcaPor(seleccion);
  if (!m) return;
  const f = $("#form-marca");
  const edit = JSON.parse(JSON.stringify(m));
  edit.colores = { primario: "#0F8F72", oscuro: "#0B3D33", tinta: "#10231F", acento: "#6FD3A8", texto: "#FFFFFF", ...(edit.colores || {}) };
  edit.voz = { voz: "es-CO-GonzaloNeural", velocidad: "+12%", ...(edit.voz || {}) };
  edit.cierre = edit.cierre || {};
  const subirArchivo = (tipo) => el("input", { type: "file", accept: "image/*", multiple: tipo === "foto", onchange: async (e) => {
    for (const archivo of e.target.files) {
      const fd = new FormData();
      fd.append("tipo", tipo);
      fd.append("archivo", archivo);
      try { Object.assign(m, await api(`/api/marcas/${m.slug}/archivo`, { method: "POST", body: fd })); } catch (err) { aviso(err.message); }
    }
    vistaMarcas(m.slug);
  } });
  const texto = (etq, obj, k, ph = "") => { const i = el("input", { value: obj[k] || "", placeholder: ph }); i.oninput = () => (obj[k] = i.value); return el("label", {}, etq, i); };
  const color = (k, etq) => { const i = el("input", { type: "color", value: edit.colores[k] }); i.oninput = () => (edit.colores[k] = i.value.toUpperCase()); return el("label", {}, etq, i); };
  const fuenteSel = el("select", {}, ...["avenir", "avenir-heavy", "didot", "optima", "din"].map((x) => el("option", { value: x }, x)));
  fuenteSel.value = edit.fuente_titulos || "avenir";
  fuenteSel.onchange = () => (edit.fuente_titulos = fuenteSel.value);
  const vozSel = el("select", {}, ...datos.voces.map((v) => el("option", { value: v.id }, `${v.id.replace("Neural", "")} · ${v.genero === "Male" ? "hombre" : "mujer"}`)));
  vozSel.value = edit.voz.voz;
  vozSel.onchange = () => (edit.voz.voz = vozSel.value);
  const conNombre = el("input", { type: "checkbox" });
  conNombre.checked = edit.logo_con_nombre !== false;
  conNombre.onchange = () => (edit.logo_con_nombre = conNombre.checked);

  f.replaceChildren(
    el("h3", {}, m.nombre),
    texto("Nombre", edit, "nombre"),
    el("div", { class: "dos" },
      el("label", {}, "Logo (PNG con fondo transparente)", m.logo ? el("img", { class: "previa-img", src: `/archivos/marcas/${m.slug}/${m.logo}?${Date.now()}` }) : null, subirArchivo("logo")),
      el("label", {}, "Diseño de la tarjeta (para el 3D)", m.tarjeta ? el("img", { class: "previa-img", src: `/archivos/marcas/${m.slug}/${m.tarjeta}?${Date.now()}` }) : null, subirArchivo("tarjeta"))),
    el("label", { class: "check" }, conNombre, "Mostrar el nombre junto al logo arriba del video"),
    el("h4", {}, "Colores"),
    el("div", { class: "colores" }, color("primario", "Principal"), color("oscuro", "Oscuro"), color("tinta", "Fondo"), color("acento", "Acento"), color("texto", "Texto")),
    el("div", { class: "dos" }, el("label", {}, "Fuente de títulos", fuenteSel), el("label", {}, "Voz", vozSel)),
    el("h4", {}, "Cierre del video"),
    el("div", { class: "dos" }, texto("Subtítulo", edit.cierre, "subtitulo", "COCINA DE AUTOR"), texto("WhatsApp", edit.cierre, "whatsapp", "WhatsApp 300 000 0000")),
    texto("Web o dirección", edit.cierre, "url", "minegocio.com"),
    el("h4", {}, "Fotos"),
    el("div", { class: "miniaturas" }, ...m.fotos_disponibles.map((x) => el("div", { class: "min", title: x }, el("img", { src: `/archivos/marcas/${m.slug}/${x}` })))),
    el("label", {}, "Agregar fotos", subirArchivo("foto")),
    el("div", { class: "acciones" }, el("button", { class: "primario", onclick: async () => {
      try {
        edit.fotos = m.fotos_disponibles;
        Object.assign(m, await api(`/api/marcas/${m.slug}`, { method: "PUT", body: edit }));
        aviso("Marca guardada");
        vistaMarcas(m.slug);
      } catch (e) { aviso(e.message); }
    } }, "Guardar marca")),
  );
}

// ------------------------------------------------------------------ router
async function ruta() {
  const [vista, arg] = location.hash.replace(/^#/, "").split("/");
  const pestana = ["marcas", "asistente", "pedidos"].includes(vista) ? vista : "videos";
  $$(".barra nav button").forEach((b) => b.classList.toggle("activo", b.dataset.vista === pestana));
  contarPedidos();
  try {
    if (vista === "nuevo") await vistaNuevo();
    else if (vista === "asistente") await vistaAsistente();
    else if (vista === "pedidos") await vistaPedidos();
    else if (vista === "editor" && arg) await vistaEditor(arg);
    else if (vista === "marcas") await vistaMarcas();
    else await vistaVideos();
  } catch (e) {
    app.replaceChildren(el("div", { class: "vista" }, el("div", { class: "error" }, e.message)));
  }
}

document.addEventListener("click", (e) => {
  const ir = e.target.closest("[data-ir]");
  if (ir) { e.preventDefault(); location.hash = `#${ir.dataset.ir}`; }
  const cp = e.target.closest("[data-copiar]");
  if (cp) copiar(cp.dataset.copiar);
  const nav = e.target.closest("[data-vista]");
  if (nav) location.hash = `#${nav.dataset.vista}`;
});
window.addEventListener("hashchange", ruta);

(async () => {
  [datos.marcas, datos.plantillas, datos.escenas, datos.musica, datos.ia] = await Promise.all([
    api("/api/marcas"), api("/api/plantillas"), api("/api/escenas"), api("/api/musica"), api("/api/ia/catalogo"),
  ]);
  // Las voces vienen de internet: no se espera por ellas para mostrar el panel
  datos.voces = [{ id: "es-CO-GonzaloNeural", genero: "Male" }, { id: "es-CO-SalomeNeural", genero: "Female" }];
  ruta();
  api("/api/voces").then((v) => { if (v.length) datos.voces = v; }).catch(() => {});
})();
