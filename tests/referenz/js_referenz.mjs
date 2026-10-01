// Führt den Rechenkern der HTML-Version v6.9.1 in Node aus (mit Attrappen-DOM)
// und schreibt die Ergebnisse für den Abgleich mit der Python-Version.
//
// Aufruf: node js_referenz.mjs <html-datei> <faelle.json> <erwartet.json>
import fs from "node:fs";
import vm from "node:vm";

const [htmlPfad, faellePfad, ausgabePfad] = process.argv.slice(2);
const html = fs.readFileSync(htmlPfad, "utf8");
const js = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));

function element(id) {
  return {
    id, value: "", checked: false, options: [], selectedIndex: -1, innerHTML: "", textContent: "", disabled: false, style: {},
    classList: { toggle() {}, add() {}, remove() {} },
    setAttribute() {}, getAttribute() { return null; }, removeAttribute() {},
    addEventListener() {}, appendChild() {}, click() {}, focus() {},
  };
}
const els = {};
const getEl = (id) => (els[id] ??= element(id));
for (const m of html.matchAll(/id="([^"]+)"/g)) getEl(m[1]);
const START = {
  systemKind: "auto", operationMode: "both", building: "mid", glass: "double", shade: "1",
  heatOut: "-12", summer: "33", coolHours: "12", simFactor: "1", wbClass: "standard",
  reheatClass: "none", coolSet: "24", heatSet: "20", validationCase: "", placeInput: "",
};
for (const [k, v] of Object.entries(START)) getEl(k).value = v;

const ctx = {
  console, Math, JSON, Date, Object, Array, String, Number, Set, Map, isFinite, alert() {},
  navigator: {}, URL: { createObjectURL() {}, revokeObjectURL() {} }, Blob: class {},
  setTimeout() {}, window: {},
  document: {
    getElementById: getEl, querySelectorAll: () => [], createElement: () => element(""),
    documentElement: element("html"), body: element("body"),
  },
};
for (const id of Object.keys(els)) ctx[id] = els[id];
vm.createContext(ctx);
vm.runInContext(js, ctx);

const faelle = JSON.parse(fs.readFileSync(faellePfad, "utf8"));
ctx.__faelle = faelle;
const harness = `
(() => {
  const out = [];
  for (const f of __faelle) {
    const s = f.settings;
    for (const [k, v] of Object.entries(s)) document.getElementById(k).value = String(v);
    selectedSystemAlt = null;
    if (f.applyCase) {
      document.getElementById('validationCase').value = f.applyCase;
      applyValidationCase();
    } else {
      rooms = JSON.parse(JSON.stringify(f.rooms));
      document.getElementById('validationCase').value = f.validationCase || '';
    }
    let load = totals();
    if (operationMode.value === 'cool') load.heat = 0;
    if (operationMode.value === 'heat') load.cool = 0;
    const combos = comboCandidates(load), chosen = combos[0] || null;
    const cats = accessoryCategories(chosen);
    const val = validationCompare(load, chosen);
    out.push({
      name: f.name,
      settings: Object.fromEntries(Object.keys(s).map(k => [k, document.getElementById(k).value])),
      rooms: rooms.map(r => {
        const c = calcRoom(r), u = selectedIndoor(r), st = indoorStatus(r, u);
        return { name: r.name, cool: c.cool, coolGross: c.coolGross, storageEffect: c.storageEffect,
                 heat: c.heat, heatTrans: c.heatTrans, heatVent: c.heatVent, heatReheat: c.heatReheat,
                 damp: c.damp, wallGross: c.wallGross, win: c.win,
                 indoorId: u ? u.id : null, indoorStatus: st.txt };
      }),
      load: { cool: load.cool, heat: load.heat, rooms: load.rooms },
      productMode: productMode(load),
      combos: combos.map(c => ({ id: c.id, label: comboLabel(c.items), score: c.score })),
      assignment: roomAssignment(chosen).map(a => [a.system, a.outdoor.id, a.rooms.map(r => r.name)]),
      overall: overallTechnicalStatus(load, chosen).txt,
      heatClass: heatingApplicationClass(load, chosen).label,
      dataQuality: (({ individual, total }) => [individual, total])(dataQualityIndicator()),
      accessories: Object.fromEntries(Object.entries(cats).map(([k, v]) => [k, v.map(a => [a.id, a.qty])])),
      sound: chosen ? chosen.items.map(d => soundOutdoorRating(d).txt) : [],
      quieter: chosen ? chosen.items.map(d => (quieterAlternative(d, load) || {}).id || null) : [],
      validation: val ? { status: val.status, issues: val.issues, warns: val.warns } : null,
    });
  }
  return JSON.stringify(out, null, 1);
})()`;
fs.writeFileSync(ausgabePfad, vm.runInContext(harness, ctx) + "\n");
console.log(`${faelle.length} Fälle → ${ausgabePfad}`);
