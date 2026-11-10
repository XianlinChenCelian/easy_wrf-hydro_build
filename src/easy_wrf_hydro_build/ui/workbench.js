"use strict";

const $ = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="ewhb-session"]').content;
const formatter = new Intl.NumberFormat("zh-CN", { maximumSignificantDigits: 7 });
const scientific = new Intl.NumberFormat("zh-CN", { notation: "scientific", maximumSignificantDigits: 7 });
const format = (value) => formatter.format(value);
const labels = {
  refkdt: "入渗系数", dksat: "垂向饱和导水率", lksat: "侧向饱和导水率",
  ov_rough2d: "陆面坡面糙率", retdeprtfac: "坡面滞蓄乘数", ovroughrtfac: "细网格坡面糙率乘数",
  lksatfac: "细网格侧向导水率乘数", channel_manning_n: "河段主槽糙率",
  channel_manning_n_compound: "复合河道糙率", gw_coefficient: "地下水出流系数",
  gw_exponent: "地下水出流指数", gw_max_depth: "地下水最大储水深度",
};
const stages = {
  "": "正在检查输入与运行环境",
  geogrid: "已读取 WPS 网格，正在生成河网和路由输入",
  routing: "已生成水文路由，正在计算土壤参数",
  soil: "已生成土壤参数，正在生成离线初始场",
  initialization: "已生成离线初始场，正在整理结果",
};

function element(tag, text, className) {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (className) result.className = className;
  return result;
}

function button(text, action) {
  const result = element("button", text);
  result.type = "button";
  result.addEventListener("click", action);
  return result;
}

async function api(route, data = {}) {
  const response = await fetch("/api/" + route, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-EWHB-Session": token },
    body: JSON.stringify(data),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "操作失败，请检查启动终端。");
  return payload;
}

for (const control of document.querySelectorAll("[data-view]")) {
  control.addEventListener("click", () => {
    for (const item of document.querySelectorAll("[data-view]")) {
      $(item.dataset.view + "-view").hidden = item !== control;
      if (item === control) item.setAttribute("aria-current", "page");
      else item.removeAttribute("aria-current");
    }
    window.scrollTo(0, 0);
  });
}

const domain = $("domain-form");
const calibration = $("calibration-form");
let grid;
let gridRead = 0;
let templateRead = 0;
let loadedTemplate = "";
let busy = false;

function syncControls() {
  const lakes = $("lakes").checked;
  $("lake-field").hidden = !lakes;
  $("lake-polygons").disabled = !lakes;
  $("lake-polygons").required = lakes;
  const hasStations = Boolean($("stations").value.trim());
  $("mask").disabled = !hasStations;
  if (!hasStations) $("mask").checked = false;
  const customForcing = $("forcing-source").value === "custom";
  $("forcing-field").hidden = !customForcing;
  $("forcing-dir").disabled = !customForcing;
  $("forcing-dir").required = customForcing;
  domain.querySelector('[type="submit"]').disabled = busy || !$("version").value;
  $("create-trial").disabled = busy || !loadedTemplate;
}

async function loadOptions() {
  try {
    const { defaults, versions } = await api("options");
    for (const version of versions) $("version").append(new Option(version, version));
    $("ratio").value = defaults.ratio;
    $("threshold").value = defaults.threshold_cells;
    domain.elements.reach.checked = defaults.reach;
    $("lakes").checked = defaults.lakes;
  } catch (error) {
    showStatus("domain", { state: "error", error: error.message });
  }
  syncControls();
}

function gridMetrics() {
  const ratio = $("ratio").valueAsNumber;
  const threshold = $("threshold").valueAsNumber;
  const spacing = grid && ratio > 0 ? grid.cell_m / ratio : 0;
  $("spacing").textContent = spacing
    ? "水文间距 " + format(spacing) + " m"
    : "读取 WPS 网格后显示水文间距。";
  $("area").textContent = spacing && threshold > 0
    ? "名义起河面积 " + format(spacing * spacing * threshold / 1e6) + " km²"
    : "阈值越大，提取的河网通常越稀。";
}

$("geogrid").addEventListener("input", () => {
  gridRead += 1;
  grid = undefined;
  $("grid-status").textContent = "支持等间距 Lambert 网格。";
  gridMetrics();
});
$("geogrid").addEventListener("change", async () => {
  const path = $("geogrid").value.trim();
  if (!path) return;
  const request = ++gridRead;
  $("grid-status").textContent = "正在读取陆面网格…";
  try {
    const result = await api("geogrid", { path });
    if (request !== gridRead) return;
    grid = result;
    $("grid-status").textContent = "陆面间距 " + format(grid.cell_m) + " m · " +
      (grid.e_we - 1) + " × " + (grid.e_sn - 1) + " 格";
  } catch (error) {
    if (request === gridRead) $("grid-status").textContent = error.message;
  }
  gridMetrics();
});
for (const id of ["ratio", "threshold"]) $(id).addEventListener("input", gridMetrics);
for (const id of ["lakes", "stations"]) $(id).addEventListener("input", syncControls);
$("forcing-source").addEventListener("change", syncControls);

function rangeText([minimum, maximum]) {
  const label = (value) => value !== 0 && Math.abs(value) < 0.001 ? scientific.format(value) : format(value);
  return minimum === maximum ? label(minimum) : label(minimum) + " – " + label(maximum);
}

function parameterRow(name, info) {
  const row = element("tr");
  const title = row.insertCell();
  title.append(element("strong", labels[name] || name), element("small", name));
  const original = row.insertCell();
  if (!info.available) {
    row.className = "unavailable";
    original.colSpan = 3;
    original.append(element("small", "当前模板不可调 · " + (info.reason || info.file)));
    return row;
  }
  original.append(element("code", rangeText(info.template_range)),
    element("small", info.units + " · " + info.file));
  const operation = element("select");
  operation.setAttribute("aria-label", (labels[name] || name) + "调整方式");
  operation.append(new Option("乘系数", "scale"), new Option("统一设值", "set"));
  const input = element("input");
  input.type = "number";
  input.step = "any";
  input.min = "0";
  input.placeholder = "留空";
  input.setAttribute("aria-label", (labels[name] || name) + "新值");
  row.dataset.parameter = name;
  row.insertCell().append(operation);
  row.insertCell().append(input);
  return row;
}

function resetParameters() {
  loadedTemplate = "";
  $("parameter-rows").replaceChildren();
  $("parameters-empty").hidden = false;
  $("parameter-table").hidden = true;
  syncControls();
}

$("template").addEventListener("input", () => {
  templateRead += 1;
  $("template-status").textContent = "";
  resetParameters();
});

$("read-template").addEventListener("click", async () => {
  const field = $("template");
  if (!field.reportValidity()) return;
  const path = field.value.trim();
  if (!path) return;
  const request = ++templateRead;
  resetParameters();
  $("read-template").disabled = true;
  $("template-status").textContent = "正在读取 NetCDF…";
  try {
    const { parameters } = await api("parameters", { template: path });
    if (request !== templateRead) return;
    $("parameter-rows").append(...Object.entries(parameters).map(([name, info]) => parameterRow(name, info)));
    const count = Object.values(parameters).filter((info) => info.available).length;
    $("template-status").textContent = "已读取 · " + count + " 项可调";
    $("parameters-empty").hidden = true;
    $("parameter-table").hidden = false;
    loadedTemplate = path;
  } catch (error) {
    if (request === templateRead) $("template-status").textContent = error.message;
  } finally {
    $("read-template").disabled = false;
    syncControls();
  }
});

function showStatus(kind, status) {
  const result = $(kind + "-result");
  if (!status.state) return;
  result.hidden = false;
  result.dataset.state = status.state;
  const title = { running: "正在处理", done: "已完成", error: "操作未完成" }[status.state];
  result.replaceChildren(element("strong", title));
  if (status.output) result.append(element("p", status.output));
  if (status.state === "error") result.append(element("p", status.error));
  if (status.state === "running") {
    result.append(element("p", kind === "domain" ? stages[status.stage] : "正在复制模板并应用参数。"));
  }
  if (status.state !== "done") return;
  if (kind === "domain") {
    const details = status.summary;
    result.append(element("p", "水文间距 " + format(details.spacing_m) + " m · " +
      format(details.active_channel_cells) + " 个河道网格 · " + details.stations + " 个站点 · " +
      details.lake_count + " 个湖库"));
    result.append(element("small", "查看 DOMAIN、domain-config.json 和 domain-manifest.json。"));
  } else {
    const edits = Object.entries(status.summary.edits);
    result.append(element("p", edits.length ? "已写入 " + edits.length + " 项参数。" : "已创建基准试验。"));
    if (edits.length) {
      const changes = element("ul");
      for (const [name, record] of edits) {
        changes.append(element("li", (labels[name] || name) + " · " +
          rangeText(record.template_range) + " → " + rangeText(record.result_range)));
      }
      result.append(changes);
    }
    result.append(element("small", "FORCING → " + status.summary.forcing_target));
  }
}

async function watch(kind, status) {
  showStatus(kind, status);
  if (status.state !== "running") return;
  busy = true;
  syncControls();
  try {
    let current = status;
    while (current.state === "running") {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const next = await api("status/" + kind);
      if (next.state !== current.state || next.stage !== current.stage) showStatus(kind, next);
      current = next;
    }
  } catch (error) {
    showStatus(kind, { state: "error", error: error.message });
  } finally {
    busy = false;
    syncControls();
  }
}

async function run(kind, data) {
  busy = true;
  syncControls();
  showStatus(kind, { state: "running", stage: "", output: data.output });
  $(kind + "-result").scrollIntoView({ block: "nearest" });
  try {
    const status = await api("run/" + kind, data);
    await watch(kind, status);
  } catch (error) {
    showStatus(kind, { state: "error", error: error.message });
  } finally {
    busy = false;
    syncControls();
  }
}

domain.addEventListener("submit", (event) => {
  event.preventDefault();
  if (busy) return;
  const data = Object.fromEntries(new FormData(domain));
  for (const name of ["ratio", "threshold_cells", "month"]) data[name] = Number(data[name]);
  for (const name of ["reach", "lakes", "mask_to_stations"]) data[name] = domain.elements[name].checked;
  run("domain", data);
});

calibration.addEventListener("submit", (event) => {
  event.preventDefault();
  if (busy || loadedTemplate !== $("template").value.trim()) return;
  const changes = {};
  for (const row of $("parameter-rows").querySelectorAll("[data-parameter]")) {
    const input = row.querySelector("input");
    if (input.value !== "") changes[row.dataset.parameter] = { [row.querySelector("select").value]: input.valueAsNumber };
  }
  const data = { template: loadedTemplate, output: $("trial-output").value, changes };
  if ($("forcing-source").value === "custom") data.forcing_dir = $("forcing-dir").value;
  run("calibration", data);
});

const picker = $("picker");
let selection;
let listing;
let browseRead = 0;

function usePath(path) {
  const { input, newName } = selection;
  input.value = newName ? path.replace(/\/$/, "") + "/" + newName : path;
  input.dispatchEvent(new Event("input"));
  input.dispatchEvent(new Event("change"));
  picker.close();
  input.focus();
}

async function browse(path) {
  const request = ++browseRead;
  const extensions = selection.extensions;
  $("picker-select").disabled = true;
  $("picker-error").textContent = "";
  try {
    const result = await api("browse", { path, extensions });
    if (request !== browseRead || !picker.open) return;
    listing = result;
    $("picker-path").value = listing.path;
    $("picker-list").replaceChildren();
    if (listing.path !== listing.parent) {
      $("picker-list").append(button("↑ 上一级", () => browse(listing.parent)));
    }
    for (const entry of listing.entries) {
      const mark = entry.directory ? "▸  " : "·  ";
      $("picker-list").append(button(mark + entry.name,
        () => entry.directory ? browse(entry.path) : usePath(entry.path)));
    }
    if (!listing.entries.length) $("picker-list").append(element("p", "当前目录没有匹配的项目。", "empty"));
    $("picker-shortcuts").replaceChildren(...listing.shortcuts.map((path) => button(path, () => browse(path))));
    $("picker-select").disabled = Boolean(extensions.length);
  } catch (error) {
    if (request === browseRead) $("picker-error").textContent = error.message;
  }
}

for (const control of document.querySelectorAll("[data-pick]")) {
  control.addEventListener("click", () => {
    const input = $(control.dataset.pick);
    const extensions = control.dataset.extensions ? control.dataset.extensions.split(",") : [];
    const newName = control.dataset.new;
    selection = { input, extensions, newName };
    listing = undefined;
    const current = input.value.trim();
    const folder = newName || extensions.length
      ? (current.includes("/") ? current.slice(0, current.lastIndexOf("/")) || "/" : "")
      : current;
    $("picker-title").textContent = newName ? "选择输出父目录" : extensions.length ? "选择文件" : "选择目录";
    $("picker-select").hidden = Boolean(extensions.length);
    $("picker-path").value = folder;
    $("picker-shortcuts").replaceChildren();
    $("picker-list").replaceChildren();
    picker.showModal();
    browse(folder);
  });
}
$("picker-go").addEventListener("click", () => browse($("picker-path").value));
$("picker-path").addEventListener("keydown", (event) => {
  if (event.key === "Enter") browse($("picker-path").value);
});
for (const id of ["picker-close", "picker-cancel"]) $(id).addEventListener("click", () => picker.close());
$("picker-select").addEventListener("click", () => usePath(listing.path));

loadOptions();
for (const kind of ["domain", "calibration"]) {
  api("status/" + kind).then((status) => watch(kind, status)).catch(() => {});
}
