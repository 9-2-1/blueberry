function toFixed0(num: number, digits: number) {
  const str = num.toFixed(digits);
  return str.replace(/\.?0*$/, "");
}

function toTimeString(sec: number): string {
  if (sec < 0) {
    return "-" + toTimeString(-sec);
  }
  if (sec < 60) {
    const s = Math.floor(sec);
    return `${s}sec!`;
  }
  if (sec < 3600) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec - m * 60);
    return `${m}m${s}s!`;
  }
  if (sec < 86400) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec - h * 3600) / 60);
    return `${h}h${m}m!`;
  }
  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec - d * 86400) / 3600);
  return `${d}d${h}h`;
}

function rgb(r: number, g: number, b: number) {
  return { r: r / 255, g: g / 255, b: b / 255 };
}

function oklchtorgbstr({ l, c, h }: { l: number; c: number; h: number }) {
  for (let c1 = c; c1 >= 0; c1 -= 0.01) {
    const rgb = convertOklchToRgb({ l, c: c1, h });
    if (
      0 <= rgb.r &&
      rgb.r <= 1 &&
      0 <= rgb.g &&
      rgb.g <= 1 &&
      0 <= rgb.b &&
      rgb.b <= 1
    ) {
      return rgbtostr(rgb);
    }
  }
  return "rgb(255, 0, 255)";
}

function rgbtostr(rgb: { r: number; g: number; b: number }) {
  return `rgb(${Math.round(rgb.r * 255)}, ${Math.round(rgb.g * 255)}, ${Math.round(rgb.b * 255)})`;
}

type NumberTask = {
  name: string;
  mode: "long" | "short";
  tot: number;
  speed: number;
  starttime: number;
  endtime: number;
  progress: { time: number; done: number }[];
};
let numbers: NumberTask[] = [];

let numberMap: Record<string, HTMLDivElement> = {};

let workloadTot = 0;
let workloadHistory: { time: number; left: number }[] = [];
let workloadBoundary: { time: number; done: number; keyPoint: boolean }[] = [];

function updateWorkload() {
  const tnow = new Date().getTime() / 1000;

  // History
  let records: { time: number; fin: number }[] = [];
  for (const task of numbers) {
    if (task.speed == 0) {
      continue;
    }
    let cur = 0;
    for (const prog of task.progress) {
      const fin = prog.done - cur;
      records.push({ time: prog.time, fin: fin / task.speed });
      cur = prog.done;
    }
  }
  records.sort((a, b) => a.time - b.time);
  let base = 0;
  workloadHistory = [];
  for (const rec of records) {
    base += rec.fin;
    workloadHistory.push({ time: rec.time, left: base });
  }

  // Boundary
  let record2s: { time: number; load: number }[] = [];
  let starttime = tnow;
  for (const task of numbers) {
    if (task.starttime < starttime) {
      starttime = task.starttime;
    }
    const load = task.tot / task.speed;
    record2s.push({ time: task.endtime, load: load });
  }
  record2s.sort((a, b) => a.time - b.time);
  base = 0;
  workloadBoundary = [];
  workloadBoundary.push({ time: starttime, done: base, keyPoint: false });
  for (const rec of record2s) {
    base += rec.load;
    workloadBoundary.push({ time: rec.time, done: base, keyPoint: false });
  }
  workloadTot = base;

  // keyPoint
  workloadBoundary[0].keyPoint = true;
  for (let i = 0; i < workloadBoundary.length - 1; ) {
    const boundary = workloadBoundary[i];
    const point = workloadBoundary[i + 1];
    let nexti = i + 1;
    // minsteep 越大代表着相同时间需要完成的数量更多
    let minsteep = (point.done - boundary.done) / (point.time - boundary.time);
    for (let j = i + 2; j < workloadBoundary.length; j++) {
      const point = workloadBoundary[j];
      const steep = (point.done - boundary.done) / (point.time - boundary.time);
      if (steep > minsteep) {
        minsteep = steep;
        nexti = j;
      }
    }
    i = nexti;
    workloadBoundary[i].keyPoint = true;
  }
}

async function updateNumberAsync() {
  numbers = await (await fetch("../get_numbers")).json();
  updateWorkload();
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let config: {
  showFinished: boolean;
  timeRange: number;
  direction: "left" | "fin" | "fin-all";
  display: "abs" | "ref" | "3day";
} = { showFinished: false, timeRange: 0, direction: "left", display: "abs" };

function updateConfig() {
  const showFinishedElement = document.getElementById(
    "cfg_show_finished",
  )! as HTMLInputElement;
  const timeRangeElement = document.getElementById(
    "cfg_time_range",
  )! as HTMLSelectElement;
  const directionElement = document.getElementById(
    "cfg_direction",
  )! as HTMLSelectElement;
  const displayElement = document.getElementById(
    "cfg_display",
  )! as HTMLSelectElement;
  const cfg = {
    showFinished: showFinishedElement.checked,
    timeRange: parseInt(timeRangeElement.value),
    direction: directionElement.value,
    display: displayElement.value,
  };
  config = cfg as typeof config;
}

function onConfigChange() {
  updateConfig();
  initNumbersDiv();
  updateNumberDiv();
}
window.addEventListener("load", async () => {
  updateConfig();
  // 监听配置变化
  document
    .getElementById("cfg_show_finished")!
    .addEventListener("change", onConfigChange);
  document
    .getElementById("cfg_time_range")!
    .addEventListener("change", onConfigChange);
  document
    .getElementById("cfg_direction")!
    .addEventListener("change", onConfigChange);
  document
    .getElementById("cfg_display")!
    .addEventListener("change", onConfigChange);
  while (1) {
    try {
      await updateNumberAsync();
      initNumbersDiv();
      updateNumberDiv();
    } catch (error) {
      console.error("Error updating numbers:", error);
      // 自动重试
    }
    await sleep(10 * 1000);
  }
});

window.addEventListener("resize", () => {
  updateNumberDiv();
});

function initNumbersDiv() {
  const tnow = new Date().getTime() / 1000;
  numberMap = {};

  const totDiv = document.getElementById("tot")!;
  totDiv.innerHTML = "";
  const cardDiv = document.createElement("div");
  cardDiv.classList.add("number_card");
  cardDiv.classList.add("number_tot_card");
  totDiv.appendChild(cardDiv);
  numberMap["<tot>"] = cardDiv;

  const numberDiv = document.getElementById("tasks")!;
  numberDiv.innerHTML = "";
  for (const task of numbers) {
    if (
      !config.showFinished &&
      task.progress.length > 0 &&
      task.progress[task.progress.length - 1].done >= task.tot &&
      tnow >= task.endtime
    ) {
      continue;
    }
    // 不追踪短期任务（但短期任务包含在工作时间总计中）
    if (task.mode === "short") {
      continue;
    }
    const cardDiv = document.createElement("div");
    cardDiv.classList.add("number_card");
    numberDiv.appendChild(cardDiv);
    numberMap[task.name] = cardDiv;
  }
}

function updateNumberDiv() {
  const tnow = new Date().getTime() / 1000;
  for (const task of numbers) {
    const cardDiv = numberMap[task.name];
    if (!cardDiv) {
      continue;
    }

    if (task.progress.length === 0) {
      renderNoDataCard(cardDiv, task.name);
    } else {
      renderDataCard(cardDiv, task.name, task, tnow);
    }
  }
  renderWorkload(numberMap["<tot>"], tnow);
}

// 同一主题色系列颜色
function colorSeries(themeColor: { r: number; g: number; b: number }) {
  const { l: tl, c: tc, h: th } = convertRgbToOklch(themeColor);
  return {
    titleColor: oklchtorgbstr({ l: 0.6, c: tc, h: th }),
    numColor: oklchtorgbstr({ l: 0.6, c: tc, h: th }),
    labelColor: oklchtorgbstr({ l: 0.7, c: tc, h: th }),
    lineColor: oklchtorgbstr({ l: 0.7, c: tc, h: th }),
    bgColor: oklchtorgbstr({ l: 0.95, c: tc, h: th }),
  };
}

function fdate(time: number) {
  const date = new Date(time * 1000);
  return date.getMonth() + 1 + "/" + date.getDate().toString();
}

// 搜索折线中特定横坐标的位置
function xsearch(points: { x: number; y: number }[], x: number) {
  if (x <= points[0].x) {
    return points[0].y;
  }
  for (let i = 1; i < points.length; i++) {
    if (x <= points[i].x) {
      // 线性插值
      const k = (x - points[i - 1].x) / (points[i].x - points[i - 1].x);
      return points[i - 1].y + (points[i].y - points[i - 1].y) * k;
    }
  }
  return points[points.length - 1].y;
}

// 搜索折线中特定纵坐标的位置
function ysearch(points: { x: number; y: number }[], y: number) {
  if (y <= points[0].y) {
    return points[0].x;
  }
  for (let i = 1; i < points.length; i++) {
    if (y <= points[i].y) {
      // 线性插值
      const k = (y - points[i - 1].y) / (points[i].y - points[i - 1].y);
      return points[i - 1].x + (points[i].x - points[i - 1].x) * k;
    }
  }
  return points[points.length - 1].x;
}

// 处理有数据情况的函数
function renderDataCard(
  cardDiv: HTMLDivElement,
  name: string,
  task: NumberTask,
  tnow: number,
) {
  const progress = task.progress.map((history) => ({
    x: history.time,
    y: history.done,
  }));
  const boundary = [
    { x: task.starttime, y: 0 },
    { x: task.endtime, y: 0 },
    { x: task.endtime, y: task.tot },
  ];
  const safeLine = [
    { x: task.starttime, y: 0 },
    { x: task.endtime, y: task.tot },
  ];
  const day3safemap = (point: { x: number; y: number }) => {
    const left = task.endtime - point.x;
    const day3 = 3 * 24 * 60 * 60;
    if (left < day3) {
      return { x: task.endtime, y: task.tot };
    }
    const k = day3 / left;
    return { x: point.x + day3, y: point.y + (task.tot - point.y) * k };
  };
  const day3SafeLine = progress.map(day3safemap);
  day3SafeLine.push({ x: task.endtime, y: task.tot });
  const data = {
    title: name,
    total: task.tot,
    invert: config.direction == "left",
    progress,
    boundary,
    safeLine,
    day3SafeLine,
    endtime: task.endtime,
    tnow,
  };
  renderCard(cardDiv, data);
}

// 处理无数据情况的函数
function renderNoDataCard(cardDiv: HTMLDivElement, name: string) {
  const graph = new SVGGraph();
  const title = name;
  const bgColor = rgbtostr(rgb(255, 255, 255));
  const titleColor = rgbtostr(rgb(181, 55, 55));
  const numColor = rgbtostr(rgb(181, 55, 55));
  graph.renderStart(cardDiv);
  graph.renderBackground(bgColor);
  graph.renderTitle(title, titleColor);
  graph.renderValue("NoData", numColor, 0.4);
  graph.renderTo(cardDiv);
}

function keyPoint(point: { x: number; y: number }) {
  let i = 0;
  // steep 是个负数
  // minsteep 越小代表着相同时间需要减小（完成）的数量更多
  // 跳过过往已完成的点
  while (i < workloadBoundary.length) {
    if (workloadBoundary[i].time > point.x) {
      break;
    }
    if (workloadBoundary[i].done > point.y) {
      return i; // overdue
    }
    i++;
  }
  // 跳过已经达到的目标点
  while (i < workloadBoundary.length) {
    if (workloadBoundary[i].done > point.y) {
      break;
    }
    i++;
  }
  if (i == workloadBoundary.length) {
    return i - 1;
  }
  const boundary = workloadBoundary[i];
  let minsteep = (point.y - boundary.done) / (point.x - boundary.time);
  for (let j = i + 1; j < workloadBoundary.length; j++) {
    const boundary = workloadBoundary[j];
    const steep = (point.y - boundary.done) / (point.x - boundary.time);
    if (steep > minsteep) {
      minsteep = steep;
      i = j;
    }
  }
  return i;
}

// 处理预计时间数据
function renderWorkload(cardDiv: HTMLDivElement, tnow: number) {
  const progress = workloadHistory.map((history) => ({
    x: history.time,
    y: history.left,
  }));
  const boundary = [];
  let lastY = 0;
  for (const bound of workloadBoundary) {
    if (lastY > 0) {
      boundary.push({ x: bound.time, y: lastY });
    }
    boundary.push({ x: bound.time, y: bound.done });
    lastY = bound.done;
  }
  const safeLine = workloadBoundary
    .filter((boundary) => boundary.keyPoint)
    .map((boundary) => ({ x: boundary.time, y: boundary.done }));
  const day3safemap = (point: { x: number; y: number }) => {
    const taski = keyPoint(point);
    const task = workloadBoundary[taski];
    const left = task.time - point.x;
    const day3 = 3 * 24 * 60 * 60;
    if (left < day3) {
      return { x: task.time, y: task.done };
    }
    const k = day3 / left;
    return { x: point.x + day3, y: point.y + (task.done - point.y) * k };
  };
  const day3SafeLine = progress.map(day3safemap);
  if (day3SafeLine.length > 0) {
    let point = day3SafeLine[day3SafeLine.length - 1];
    for (let t = 0; t < 100; t++) {
      let nexti = keyPoint(point);
      let next = workloadBoundary[nexti];
      point = { x: next.time, y: next.done };
      day3SafeLine.push({ x: point.x, y: point.y });
      if (nexti == workloadBoundary.length - 1) {
        break;
      }
    }
  }
  const data = {
    title: "Workload",
    total: workloadTot,
    invert: config.direction != "fin-all",
    progress,
    boundary,
    safeLine,
    day3SafeLine,
    endtime: workloadBoundary[workloadBoundary.length - 1].time,
    tnow,
  };
  renderCard(cardDiv, data);
}

type CardDef = {
  title: string;
  total: number;
  invert: boolean;
  progress: { x: number; y: number }[];
  boundary: { x: number; y: number }[];
  safeLine: { x: number; y: number }[];
  day3SafeLine: { x: number; y: number }[];
  endtime: number;
  tnow: number;
};
function renderCard(cardDiv: HTMLDivElement, data: CardDef) {
  const graph = new SVGGraph();
  graph.renderStart(cardDiv);
  // 计算x轴时间范围
  // 已完成?
  const fin = data.progress[data.progress.length - 1];
  let finished = false;
  if (fin.y >= data.total) {
    finished = true;
  }
  // 历史记录
  const progress = Array.from(data.progress); // 复制防止意外修改原数组
  const boundary = Array.from(data.boundary); // 复制防止意外修改原数组
  const safeLine = Array.from(data.safeLine); // 复制防止意外修改原数组
  const day3SafeLine = Array.from(data.day3SafeLine); // 复制防止意外修改原数组

  // 计算差距参考值
  let displayText = "";
  let themeColor = rgb(127, 127, 127);
  let refLine: { x: number; y: number }[] = [];
  if (config.display == "3day" || config.display == "ref") {
    let ref: { x: number; y: number }[];
    if (config.display == "3day") {
      ref = day3SafeLine;
    } else if (config.display == "ref") {
      ref = safeLine;
    } else {
      throw new Error("Impossible");
    }
    const y = xsearch(ref, data.tnow);
    if (fin.y < y) {
      themeColor = rgb(255, 180, 180);
      displayText = "*" + toFixed0(y - fin.y, 2);
      refLine = [
        { x: data.tnow, y: y },
        { x: data.tnow, y: fin.y },
      ];
    } else {
      if (fin.y >= data.total) {
        themeColor = rgb(140, 209, 255);
        displayText = "✓∞";
      } else {
        const x = ysearch(ref, fin.y);
        if (x - data.tnow < 1 * 24 * 60 * 60) {
          themeColor = rgb(232, 230, 140);
        } else if (x - data.tnow < 2 * 24 * 60 * 60) {
          themeColor = rgb(136, 231, 146);
        } else {
          themeColor = rgb(140, 209, 255);
        }
        displayText = "⧖" + toTimeString(x - data.tnow);
        refLine = [
          { x: data.tnow, y: fin.y },
          { x: x, y: fin.y },
        ];
      }
    }
  } else {
    // 普通，无相对的模式
    // 根据完成情况显示颜色
    if (fin.y >= data.total) {
      themeColor = rgb(140, 209, 255);
    } else if (data.tnow >= data.endtime) {
      themeColor = rgb(255, 180, 180);
    }
    if (data.invert) {
      // 反转图表，显示剩余的量。
      displayText = toFixed0(data.total - fin.y, 2);
    } else {
      displayText = toFixed0(fin.y, 2);
    }
  }

  if (data.invert) {
    // 反转图表，显示剩余的量。
    progress.forEach((point) => {
      point.y = data.total - point.y;
    });
    boundary.forEach((point) => {
      point.y = data.total - point.y;
    });
    safeLine.forEach((point) => {
      point.y = data.total - point.y;
    });
    day3SafeLine.forEach((point) => {
      point.y = data.total - point.y;
    });
    refLine.forEach((point) => {
      point.y = data.total - point.y;
    });
  }
  if (!finished) {
    // 进行中，延长x轴范围
    progress.push({ x: data.tnow, y: progress[progress.length - 1].y });
    safeLine.push({ x: data.tnow, y: safeLine[safeLine.length - 1].y });
  }
  graph.autoRange(progress, true, "x");
  if (config.timeRange != 0) {
    // 限定时间范围
    graph.xMin = graph.xMax - config.timeRange * 24 * 60 * 60;
  }
  // 计算y轴范围
  graph.autoYRangeLine(progress, true);
  if (config.timeRange == 0) {
    // 显示完整的边界
    graph.autoRange(boundary, false, "xy");
    graph.autoRange(safeLine, false, "xy");
  }
  graph.autoRange(refLine, false, "xy");
  graph.fixYRange();

  const origYMin = graph.yMin;
  const origXMax = graph.xMax;
  graph.zoomRange(1.2, 1.2);

  // 延长 safeLine
  safeLine.push({ x: graph.xMax, y: safeLine[safeLine.length - 1].y });

  // 延长 day3SafeLine
  day3SafeLine.unshift({ x: graph.xMin, y: day3SafeLine[0].y });
  day3SafeLine.push({
    x: graph.xMax,
    y: day3SafeLine[day3SafeLine.length - 1].y,
  });

  const xAxisYv = origYMin;
  const yAxisXv = Math.min(origXMax, data.tnow);

  const tzoffset = new Date().getTimezoneOffset() * 60;
  const xInterval = graph.findXInterval(24 * 60 * 60, 30);
  const yInterval = graph.findYInterval(1, 20);

  const bgColor = rgbtostr(rgb(255, 255, 255));
  const labelColor = rgbtostr(rgb(0, 0, 0));
  const lineColor = rgbtostr(rgb(59, 188, 54));
  const warnLineColor = rgbtostr(rgb(215, 66, 66));
  const safeLineColor = rgbtostr(rgb(215, 183, 66));
  const { l: tl, c: tc, h: th } = convertRgbToOklch(themeColor);

  const titleColor = oklchtorgbstr({ l: 0.6, c: tc, h: th });
  const numColor = oklchtorgbstr({ l: 0.9, c: tc, h: th });
  const refLineColor = oklchtorgbstr({ l: 0.8, c: tc, h: th });

  graph.renderBackground(bgColor);
  graph.renderTitle(data.title, titleColor);
  // graph.renderUpdateTime(lasttime, titleColor);
  graph.renderValue(displayText, numColor, 0.4);
  graph.renderXAxis(xAxisYv, xInterval, tzoffset, labelColor, fdate);
  graph.renderYAxis(yAxisXv, yInterval, 0, labelColor, null);

  graph.renderLine(progress, lineColor, "solid", 2);
  graph.renderPoints(progress, lineColor, 2);
  graph.renderLine(boundary, warnLineColor, "solid", 1);
  if (config.display == "3day") {
    graph.renderLine(day3SafeLine, safeLineColor, "dashed", 1);
  } else {
    graph.renderLine(safeLine, warnLineColor, "dashed", 1);
  }
  graph.renderLine(refLine, refLineColor, "dashed", 1);
  graph.renderPoints(refLine, refLineColor, 4);

  console.log(graph);
  graph.renderTo(cardDiv);
}
