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
  progress: {
    time: number;
    done: number;
  }[];
};
let numbers: NumberTask[] = [];

let numberMap: Record<string, HTMLDivElement> = {};

let workloadTot = 0;
let workloadHistory: { time: number; left: number }[] = [];
let workloadBoundary: { time: number; left: number; keyPoint: boolean }[] = [];

function updateWorkload() {
  const tnow = new Date().getTime() / 1000;

  // History
  let base = 0;
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
    base += (task.tot - cur) / task.speed;
  }
  records.sort((a, b) => b.time - a.time);
  workloadHistory = [{ time: tnow, left: base }];
  for (const rec of records) {
    workloadHistory.unshift({ time: rec.time, left: base });
    base += rec.fin;
  }
  workloadTot = base;

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
  record2s.sort((a, b) => b.time - a.time);
  base = 0;
  workloadBoundary = [];
  for (const rec of record2s) {
    workloadBoundary.unshift({ time: rec.time, left: base, keyPoint: false });
    base += rec.load;
  }
  workloadBoundary.unshift({ time: starttime, left: base, keyPoint: false });

  // keyPoint
  workloadBoundary[0].keyPoint = true;
  for (let i = 0; i < workloadBoundary.length - 1; ) {
    const boundary = workloadBoundary[i];
    const point = workloadBoundary[i + 1];
    let nexti = i + 1;
    // steep 是个负数
    // minsteep 越小代表着相同时间需要减小（完成）的数量更多
    let minsteep = (point.left - boundary.left) / (point.time - boundary.time);
    for (let j = i + 2; j < workloadBoundary.length; j++) {
      const point = workloadBoundary[j];
      const steep = (point.left - boundary.left) / (point.time - boundary.time);
      if (steep < minsteep) {
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
} = {
  showFinished: false,
  timeRange: 0,
  direction: "left",
  display: "abs",
};

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

// 处理有数据情况的函数
function renderDataCard(
  cardDiv: HTMLDivElement,
  name: string,
  task: NumberTask,
  tnow: number,
) {
  const graph = new SVGGraph();
  graph.renderStart(cardDiv);
  // 计算x轴时间范围
  // 已完成?
  let finished = false;
  if (task.progress[task.progress.length - 1].done >= task.tot) {
    finished = true;
  }
  // 历史记录
  const historyList = Array.from(task.progress);
  const points = historyList.map((history) => ({
    x: history.time,
    y: history.done,
  }));
  const boundary1 = [
    { x: task.starttime, y: 0 },
    { x: task.endtime, y: 0 },
    { x: task.endtime, y: task.tot },
  ];
  const boundary2 = [
    { x: task.starttime, y: 0 },
    { x: task.endtime, y: task.tot },
    { x: tnow, y: task.tot },
  ];
  if (config.direction == "left") {
    // 反转图表，显示剩余的量。
    points.forEach((point) => {
      point.y = task.tot - point.y;
    });
    boundary1.forEach((point) => {
      point.y = task.tot - point.y;
    });
    boundary2.forEach((point) => {
      point.y = task.tot - point.y;
    });
  }
  if (!finished) {
    // 进行中，延长x轴范围
    points.push({
      x: tnow,
      y: points[points.length - 1].y,
    });
  }
  graph.autoRange(points, true, "x");
  if (config.timeRange != 0) {
    // 限定时间范围
    graph.xMin = graph.xMax - config.timeRange * 24 * 60 * 60;
  }
  // 计算y轴范围
  graph.autoYRangeLine(points, true);
  if (config.timeRange == 0) {
    // 显示完整的边界
    graph.autoRange(boundary1, false, "xy");
    graph.autoRange(boundary2, false, "xy");
  }
  graph.fixYRange();

  const origYMin = graph.yMin;
  const origXMax = graph.xMax;
  graph.zoomRange(1.2, 1.2);

  const xAxisYv = origYMin;
  const yAxisXv = Math.min(origXMax, tnow);

  const tzoffset = new Date().getTimezoneOffset() * 60;
  const xInterval = graph.findXInterval(24 * 60 * 60, 30);
  const yInterval = graph.findYInterval(1, 20);

  const bgColor = rgbtostr(rgb(255, 255, 255));
  const labelColor = rgbtostr(rgb(0, 0, 0));
  const lineColor = rgbtostr(rgb(59, 188, 54));
  const warnLineColor = rgbtostr(rgb(215, 66, 66));
  let titleColor = rgbtostr(rgb(127, 127, 127));
  let numColor = rgbtostr(rgb(210, 210, 210));
  if (task.progress[task.progress.length - 1].done >= task.tot) {
    titleColor = rgbtostr(rgb(66, 149, 212));
    numColor = rgbtostr(rgb(194, 229, 255));
  } else if (tnow >= task.endtime) {
    titleColor = rgbtostr(rgb(255, 0, 0));
    numColor = rgbtostr(rgb(255, 180, 180));
  }

  const title = name;

  graph.renderBackground(bgColor);
  graph.renderTitle(title, titleColor);
  // graph.renderUpdateTime(lasttime, titleColor);
  let displayText = "";
  if (config.direction == "left") {
    // 反转图表，显示剩余的量。
    displayText = (
      task.tot - task.progress[task.progress.length - 1].done
    ).toString();
  } else {
    displayText = task.progress[task.progress.length - 1].done.toString();
  }
  graph.renderValue(displayText, numColor, 0.4);
  graph.renderXAxis(xAxisYv, xInterval, tzoffset, labelColor, fdate);
  graph.renderYAxis(yAxisXv, yInterval, 0, labelColor, null);
  graph.renderLine(points, lineColor, "solid", 2);
  graph.renderPoints(points, lineColor, 2);

  graph.renderLine(boundary1, warnLineColor, "solid", 1);
  graph.renderLine(boundary2, warnLineColor, "dashed", 1);

  graph.renderTo(cardDiv);
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

// 处理预计时间数据
function renderWorkload(cardDiv: HTMLDivElement, tnow: number) {
  const graph = new SVGGraph();
  graph.renderStart(cardDiv);
  const points = workloadHistory.map((history) => ({
    x: history.time,
    y: history.left,
  }));
  const boundary1 = [];
  let lastY = 0;
  for (const boundary of workloadBoundary) {
    if (lastY > 0) {
      boundary1.push({
        x: boundary.time,
        y: lastY,
      });
    }
    boundary1.push({
      x: boundary.time,
      y: boundary.left,
    });
    lastY = boundary.left;
  }
  const boundary2 = workloadBoundary
    .filter((boundary) => boundary.keyPoint)
    .map((boundary) => ({
      x: boundary.time,
      y: boundary.left,
    }));

  if (config.direction == "fin-all") {
    // 反转图表，显示已用时长。
    points.forEach((point) => {
      point.y = workloadTot - point.y;
    });
    boundary1.forEach((point) => {
      point.y = workloadTot - point.y;
    });
    boundary2.forEach((point) => {
      point.y = workloadTot - point.y;
    });
  }

  // 计算x轴时间范围
  graph.autoRange(points, true, "x");
  if (config.timeRange > 0) {
    graph.xMin = graph.xMax - config.timeRange * 24 * 60 * 60;
  }
  // 计算y轴范围
  const yRange = 1;
  const yMinMin = 0;
  graph.autoYRangeLine(points, true);
  if (config.timeRange == 0) {
    // 显示完整的边界
    graph.autoRange(boundary1, false, "xy");
    graph.autoRange(boundary2, false, "xy");
  }
  graph.fixYRange();

  const origYMin = graph.yMin;
  const origXMax = graph.xMax;
  graph.zoomRange(1.2, 1.2);

  const xAxisYv = origYMin;
  const yAxisXv = Math.min(origXMax, tnow);

  const tzoffset = new Date().getTimezoneOffset() * 60;
  const xInterval = graph.findXInterval(24 * 60 * 60, 30);
  const yInterval = graph.findYInterval(1, 20);

  const bgColor = rgbtostr(rgb(255, 255, 255));
  const labelColor = rgbtostr(rgb(0, 0, 0));
  const lineColor = rgbtostr(rgb(59, 188, 54));
  const boundaryColor = rgbtostr(rgb(215, 66, 66));
  let titleColor = rgbtostr(rgb(0, 0, 0));
  let numColor = rgbtostr(rgb(196, 196, 196));

  graph.renderBackground(bgColor);

  const title = "Workload";
  graph.renderTitle(title, titleColor);
  // graph.renderUpdateTime(lasttime, titleColor);

  let lastLeft = workloadHistory[workloadHistory.length - 1].left;
  let displayText = "";
  if (config.direction == "fin-all") {
    // 反转图表，显示已用时长。
    displayText = (workloadTot - lastLeft).toFixed(2);
  } else {
    displayText = lastLeft.toFixed(2);
  }
  graph.renderValue(displayText, numColor, 0.4);
  graph.renderXAxis(xAxisYv, xInterval, tzoffset, labelColor, fdate);
  graph.renderYAxis(yAxisXv, yInterval, 0, labelColor, null);
  graph.renderLine(points, lineColor, "solid", 2);
  graph.renderPoints(points, lineColor, 2);
  graph.renderLine(boundary1, boundaryColor, "solid", 1);
  graph.renderLine(boundary2, boundaryColor, "dashed", 1);

  graph.renderTo(cardDiv);
}
