let g_point = null;
let g_speed = 5;
let g_error = true;
let g_time = new Date();

let g_a_point = null;
let g_a_speed = 5;

let canvas, ctx;
const colorMap = {
  // # rgb(r, g, b) only
  D: "rgb(255, 72, 72)",
  C: "rgb(255, 144, 17)",
  B: "rgb(239, 243, 0)",
  A: "rgb(0, 226, 19)",
  AA: "rgb(0, 227, 235)",
  AAA: "rgb(0, 153, 255)",
  default: "rgb(212, 212, 212)",
};
let g_color = colorMap["default"];

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

// {x, y, z, sx, sy, sz}
let g_bubbles = [];
let prevTime = new Date();
const RangeMin = { x: -2.0, y: -2.0, z: 0.9 };
const RangeMax = { x: 2.0, y: 2.0, z: 2.0 };
const BSD = 0.01;

function InitBubbles() {
  g_bubbles = [];
  for (let i = 0; i < 100; i++) {
    g_bubbles.push({
      x: Math.random() * (RangeMax.x - RangeMin.x) + RangeMin.x,
      y: Math.random() * (RangeMax.y - RangeMin.y) + RangeMin.y,
      z: Math.random() * (RangeMax.z - RangeMin.z) + RangeMin.z,
      sx: (Math.random() * 2 - 1) * BSD,
      sy: (Math.random() * 2 - 1) * BSD,
      sz: (Math.random() * 2 - 1) * BSD,
    });
  }
}

function backgroundBubbles() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  let nowTime = new Date();
  let dtime = (nowTime - prevTime) / 1000;
  prevTime = nowTime;
  for (const bubble of g_bubbles) {
    moveBubble(bubble, dtime, g_a_speed);
    drawBubble(bubble);
  }
}

function moveBubble(bubble, dtime, speed) {
  bubble.x += bubble.sx * dtime;
  bubble.y += (bubble.sy - speed) * dtime;
  bubble.z += bubble.sz * dtime;

  const attrs = ["x", "y", "z"];
  for (const attr of attrs) {
    if (bubble[attr] < RangeMin[attr] || bubble[attr] > RangeMax[attr]) {
      while (bubble[attr] < RangeMin[attr]) {
        bubble[attr] += RangeMax[attr] - RangeMin[attr];
      }
      while (bubble[attr] > RangeMax[attr]) {
        bubble[attr] -= RangeMax[attr] - RangeMin[attr];
      }
      for (const attr2 in attrs) {
        if (attr2 != attr) {
          bubble[attr2] =
            Math.random() * (RangeMax[attr2] - RangeMin[attr2]) +
            RangeMin[attr2];
        }
      }
    }
  }
}

function drawBubble(bubble) {
  const size =
    Math.sqrt((window.innerHeight * window.innerWidth) / 50) / bubble.z;
  const x = canvas.width * (0.5 + bubble.x / (2 * bubble.z));
  const y = canvas.height * (0.5 + bubble.y / (2 * bubble.z));
  let opacity = 0.3 * (1 - (bubble.z - RangeMin.z) / (RangeMax.z - RangeMin.z));
  if (bubble.z < RangeMin.z + 0.1) {
    opacity = (0.3 * (bubble.z - RangeMin.z)) / 0.1;
  }
  // rgb(r, g, b)
  ctx.fillStyle = `rgba(${g_color.slice(4, -1)}, ${opacity})`;
  ctx.beginPath();
  try {
    ctx.arc(x, y, size, 0, Math.PI * 2);
  } catch (error) {
    console.error(error);
  }
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
  if (!g_error) {
    let rating = "D";
    for (const [i, x] of point_thresholds.entries()) {
      if (g_a_point >= x) {
        rating = rating_lists[i + 1];
      }
    }
    g_color = colorMap[rating];
  } else {
    g_color = colorMap["default"];
  }
  document.getElementById("app").style.color = g_color;
  backgroundBubbles();
  requestAnimationFrame(() => setTimeout(animatePoints, 33));
}

function updateTime() {
  let now = new Date();
  // 50ms tolerance
  now.setTime(now.getTime() + 50);
  let hours = now.getHours();
  let minutes = now.getMinutes();
  let seconds = now.getSeconds();
  document.getElementById("nowtime").innerText =
    `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  let day = now.getDate();
  let month = now.getMonth() + 1;
  let weekday = now.getDay();
  let week = ["日", "一", "二", "三", "四", "五", "六"];
  document.getElementById("nowdate").innerText =
    `${month}/${day} ${week[weekday]}`;
  setTimeout(updateTime, 1000 - now.getMilliseconds());
}

window.onload = function () {
  // 初始化Canvas
  canvas = document.getElementById("bubbles");
  ctx = canvas.getContext("2d");

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    backgroundBubbles();
  }
  resizeCanvas();
  window.addEventListener("resize", resizeCanvas);

  InitBubbles();
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

  // font after script
  // new FontFace("Fira Mono", "url(FiraMono.ttf)");
  document.getElementById("app").classList.add("load-font");
};
