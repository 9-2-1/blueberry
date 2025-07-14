let g_point = null;
let g_speed = 5;
let g_error = true;
let g_time = new Date();

let g_a_point = null;
let g_a_speed = 5;

// Canvas相关全局变量
let canvas, ctx;
const colorMap = {
  D: "rgb(255, 72, 72)",
  C: "rgb(255, 144, 17)",
  B: "rgb(239, 243, 0)",
  A: "rgb(0, 226, 19)",
  AA: "rgb(0, 227, 235)",
  AAA: "rgb(0, 153, 255)",
  default: "rgb(212, 212, 212)",
};
let g_currentColor = colorMap["default"];

function updatePoints() {
  fetch("get_points_experience", { method: "get" })
    .then((response) => {
      if (response.status != 200) {
        throw new Error("获取失败");
      }
      return response.json();
    })
    .then((points) => {
      // {"point": number, "speed": number}
      g_point = points.point;
      g_speed = points.speed;
      g_error = false;
      g_time = new Date();
      setTimeout(updatePoints, 10000);
    })
    .catch((error) => {
      g_error = true;
      console.error(error);
      setTimeout(updatePoints, 10000);
    });
}

let g_bubbles = [];
let prevTime = new Date();
const ZMin = 0.7;
const ZMax = 4;
const ZDensity = 0.005;
let g_zaccomulate = ZMin - ZMax;
// {x: number, y: number, z: number, element: HTMLElement}
function backgroundBubbles() {
  // 清除画布
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // move bubbles by g_speed
  let deletions = [];
  let nowTime = new Date();
  let dtime = (nowTime - prevTime) / 1000;
  prevTime = nowTime;
  deltaZ = -g_a_speed * dtime;

  for (const bubble of g_bubbles) {
    bubble.z += deltaZ;
    // 移除超出范围的气泡
    if (bubble.z > ZMax || bubble.z <= ZMin) {
      deletions.push(bubble);
    } else {
      // 绘制气泡
      drawBubble(bubble);
    }
  }

  // 移除删除的气泡
  for (const bubble of deletions) {
    g_bubbles.splice(g_bubbles.indexOf(bubble), 1);
  }

  // 添加新气泡
  g_zaccomulate += deltaZ;
  if (g_zaccomulate > ZMax - ZMin) {
    g_zaccomulate = ZMax - ZMin;
  }
  if (g_zaccomulate < ZMin - ZMax) {
    g_zaccomulate = ZMin - ZMax;
  }

  if (g_zaccomulate > 0) {
    for (let i = 0; i < Math.floor(g_zaccomulate / ZDensity); i++) {
      g_bubbles.push(createBubble(ZMin, ZMin + g_zaccomulate));
      g_zaccomulate -= ZDensity;
    }
  } else {
    for (let i = 0; i < Math.floor(-g_zaccomulate / ZDensity); i++) {
      g_bubbles.push(createBubble(ZMax - -g_zaccomulate, ZMax));
      g_zaccomulate += ZDensity;
    }
  }
}

function createBubble(zMin, zMax) {
  let a = Math.random() * 2 * Math.PI;
  return {
    x: Math.cos(a),
    y: Math.sin(a),
    z: Math.random() * (zMax - zMin) + zMin,
  };
}

function drawBubble(bubble) {
  const size = 10 / bubble.z;
  const x = canvas.width * (0.5 + bubble.x / (2 * bubble.z));
  const y = canvas.height * (0.5 + bubble.y / (2 * bubble.z));
  const opacity = (0.8 * (1 / ZMax - 1 / bubble.z)) / (1 / ZMax - 1 / ZMin);

  const rgbValues = g_currentColor.match(/\d+/g);
  const r = rgbValues[0],
    g = rgbValues[1],
    b = rgbValues[2];
  ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${opacity})`;
  ctx.beginPath();
  ctx.arc(x, y, size, 0, Math.PI * 2);
  ctx.fill();
}

function animatePoints() {
  const point_thresholds = [-500, -200, 0, 200, 500];
  const rating_lists = ["D", "C", "B", "A", "AA", "AAA"];
  let now = new Date();
  if (g_point === null) {
    document.getElementById("points").innerText = "----";
  } else {
    let point = g_point + ((now - g_time) * g_speed) / 1000;
    if (g_a_point === null) {
      g_a_point = point;
    }
    g_a_point += (point - g_a_point) * 0.05;
    g_a_speed += (g_speed - g_a_speed) * 0.05;
    document.getElementById("points").innerText = Math.floor(g_a_point + 0.5);
  }
  for (const x of rating_lists) {
    document.getElementById("app").classList.remove("status-" + x);
  }
  if (!g_error) {
    let rating = "D";
    for (const [i, x] of point_thresholds.entries()) {
      if (g_a_point >= x) {
        rating = rating_lists[i + 1];
      }
    }
    document.getElementById("app").classList.add("status-" + rating);
    g_currentColor = colorMap[rating];
  } else {
    g_currentColor = colorMap["default"];
  }
  backgroundBubbles();
  requestAnimationFrame(animatePoints);
}

function updateTime() {
  let now = new Date();
  let hours = now.getHours();
  let minutes = now.getMinutes();
  let seconds = now.getSeconds();
  document.getElementById("nowtime").innerText =
    `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  setTimeout(updateTime, 100);
  let day = now.getDate();
  let month = now.getMonth() + 1;
  let weekday = now.getDay();
  let week = ["日", "一", "二", "三", "四", "五", "六"];
  document.getElementById("nowdate").innerText =
    `${month}/${day} ${week[weekday]}`;
}

window.onload = function () {
  // 初始化Canvas
  canvas = document.getElementById("bubbles");
  ctx = canvas.getContext("2d");

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resizeCanvas();
  window.addEventListener("resize", resizeCanvas);

  animatePoints();
  updatePoints();
  updateTime();
  const nosleep = new NoSleep();

  document.body.onclick = function () {
    document.getElementById("app").classList.toggle("layout-points");
    document.getElementById("app").classList.toggle("layout-time");
  };

  document.body.oncontextmenu = function (e) {
    // toggle fullscreen
    if (document.fullscreenElement) {
      document.exitFullscreen();
      nosleep.disable();
    } else {
      document.documentElement.requestFullscreen();
      nosleep.enable();
    }
    e.preventDefault();
  };
};
