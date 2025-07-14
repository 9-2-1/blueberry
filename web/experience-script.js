let g_point = null;
let g_speed = 5;
let g_error = true;
let g_time = new Date();

let g_a_point = null;
let g_a_speed = 5;

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
const ZMax = 5;
const ZDensity = 0.02;
let g_zaccomulate = ZMin - ZMax;
// {x: number, y: number, z: number, element: HTMLElement}
function backgroundBubbles() {
  // move bubbles by g_speed
  let deletions = [];
  let nowTime = new Date();
  let dtime = (nowTime - prevTime) / 1000;
  prevTime = nowTime;
  deltaZ = -g_a_speed * dtime;
  for (const bubble of g_bubbles) {
    bubble.z += deltaZ;
    // remove bubbles that are out of screen
    if (bubble.z > ZMax || bubble.z <= ZMin) {
      removeBubble(bubble);
      deletions.push(bubble);
    } else {
      updateBubble(bubble);
    }
  }
  // remove deleted bubbles
  for (const bubble of deletions) {
    g_bubbles.splice(g_bubbles.indexOf(bubble), 1);
  }
  // add new bubbles on empty places
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
  const element = document.createElement("div");
  element.classList.add("bubble");
  document.getElementById("bubbles").appendChild(element);
  let a = Math.random() * 2 * Math.PI;
  let bubble = {
    x: Math.cos(a),
    y: Math.sin(a),
    z: Math.random() * (zMax - zMin) + zMin,
    element: element,
  };
  updateBubble(bubble);
  return bubble;
}

function updateBubble(bubble) {
  bubble.element.style.left = 50 - (bubble.x * 50) / bubble.z + "%";
  bubble.element.style.top = 50 - (bubble.y * 50) / bubble.z + "%";
  bubble.element.style.height = 20 / bubble.z + "px";
  bubble.element.style.width = 20 / bubble.z + "px";
  bubble.element.style.opacity = (50 * (ZMax - bubble.z)) / (ZMax - ZMin) + "%";
}

function removeBubble(bubble) {
  document.getElementById("bubbles").removeChild(bubble.element);
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
