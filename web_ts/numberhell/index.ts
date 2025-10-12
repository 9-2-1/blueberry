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

async function updateNumberAsync() {
  numbers = await (await fetch("../get_numbers")).json();
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

window.addEventListener("load", async () => {
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
  const numberDiv = document.getElementById("numbers")!;
  numberDiv.innerHTML = "";
  numberMap = {};
  for (const number of numbers) {
    const cardDiv = document.createElement("div");
    cardDiv.classList.add("number_card");
    numberDiv.appendChild(cardDiv);
    numberMap[number.name] = cardDiv;
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
  let i = 0;
  let xMin = tnow;
  while (i < task.progress.length) {
    if (task.progress[i].done > 0) {
      xMin = task.progress[i].time;
      break;
    }
    i++;
  }
  if (xMin > task.starttime) {
    xMin = task.starttime;
  }
  let xMax = tnow;
  i = task.progress.length - 1;
  while (i >= 0) {
    if (task.progress[i].done >= task.tot) {
      xMax = task.progress[i].time;
    } else {
      break;
    }
    i--;
  }
  if (xMax < task.endtime) {
    xMax = task.endtime;
  }
  graph.xMin = xMin;
  graph.xMax = xMax;
  const lasttime = task.progress[task.progress.length - 1].time;
  // 历史记录
  const historyList = Array.from(task.progress);
  historyList.push({
    time: tnow,
    done: task.progress[task.progress.length - 1].done,
  });
  const points = historyList.map((history) => ({
    x: history.time,
    y: history.done,
  }));
  // 计算y轴范围
  const yRange = 1;
  const yMinMin = 0;
  graph.autoYRange(points);
  graph.yMin = yMinMin;
  if (graph.yMax < task.tot) {
    graph.yMax = task.tot;
  }
  if (graph.yMax - graph.yMin < yRange) {
    const avg = (graph.yMin + graph.yMax) / 2;
    graph.yMin = avg - yRange / 2;
    graph.yMax = avg + yRange / 2;
  }
  if (graph.yMin < yMinMin) {
    graph.yMax += yMinMin - graph.yMin;
    graph.yMin = yMinMin;
  }

  const xPad = (graph.xMax - graph.xMin) * 0.1;
  graph.xMin -= xPad;
  graph.xMax += xPad;

  const yPad = (graph.yMax - graph.yMin) * 0.1;
  graph.yMin -= yPad;
  graph.yMax += yPad;

  const xAxisYv = graph.yMin + yPad;
  const yAxisXv = Math.min(graph.xMax - xPad, tnow);

  const tzoffset = new Date().getTimezoneOffset() * 60;
  const xInterval = graph.findXInterval(24 * 60 * 60, 30);
  const yInterval = graph.findYInterval(1, 20);

  const bgColor = rgbtostr(rgb(255, 255, 255));
  const labelColor = rgbtostr(rgb(0, 0, 0));
  const lineColor = rgbtostr(rgb(59, 188, 54));
  const warnLineColor = rgbtostr(rgb(215, 66, 66));
  let titleColor = rgbtostr(rgb(0, 0, 0));
  let numColor = rgbtostr(rgb(0, 0, 0));
  if (task.progress[task.progress.length - 1].done >= task.tot) {
    titleColor = rgbtostr(rgb(66, 149, 212));
    numColor = rgbtostr(rgb(42, 100, 145));
  } else if (tnow >= task.endtime) {
    titleColor = rgbtostr(rgb(255, 0, 0));
    numColor = rgbtostr(rgb(166, 49, 49));
  }

  graph.renderBackground(bgColor);
  graph.renderXAxis(xAxisYv, xInterval, tzoffset, labelColor, fdate);
  graph.renderYAxis(yAxisXv, yInterval, 0, labelColor, null);
  graph.renderLine(points, lineColor, "solid", 2);
  graph.renderPoints(points, lineColor, 2);

  let boundary1 = [
    { x: task.starttime, y: 0 },
    { x: task.endtime, y: 0 },
    { x: task.endtime, y: task.tot },
  ];
  graph.renderLine(boundary1, warnLineColor, "solid", 1);
  let boundary2 = [
    { x: task.starttime, y: 0 },
    { x: task.endtime, y: task.tot },
    { x: graph.xMax, y: task.tot },
  ];
  graph.renderLine(boundary2, warnLineColor, "solid", 1);

  const title = name;
  graph.renderTitle(title, titleColor);
  graph.renderValue(task.progress[task.progress.length - 1].done, numColor);
  // graph.renderUpdateTime(lasttime, titleColor);

  graph.renderTo(cardDiv);
}

function renderNoDataCard(cardDiv: HTMLDivElement, name: string) {
  const graph = new SVGGraph();
  const title = name;
  const bgColor = rgbtostr(rgb(255, 255, 255));
  const titleColor = rgbtostr(rgb(181, 55, 55));
  const numColor = rgbtostr(rgb(181, 55, 55));
  graph.renderStart(cardDiv);
  graph.renderBackground(bgColor);
  graph.renderTitle(name, titleColor);
  graph.renderValue("NoData", numColor);
  graph.renderTo(cardDiv);
}
