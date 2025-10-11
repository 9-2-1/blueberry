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

const appDiv = document.getElementById("app") as HTMLElement;
const pointsDiv = document.getElementById("points") as HTMLElement;
const nowtimeDiv = document.getElementById("nowtime") as HTMLElement;
const nowdateDiv = document.getElementById("nowdate") as HTMLElement;

function updatePoints() {
  const point_thresholds = [-100, -50, 0, 50, 100];
  const rating_lists: (keyof typeof colorMap)[] = [
    "D",
    "C",
    "B",
    "A",
    "AA",
    "AAA",
  ];
  fetch("get_points", { method: "get" })
    .then((response) => {
      if (response.status != 200) {
        throw new Error("获取失败");
      }
      return response.text();
    })
    .then((points) => {
      pointsDiv.innerText = points;
      let rating: keyof typeof colorMap = "D";
      for (const [i, x] of point_thresholds.entries()) {
        if (Number(points) >= x) {
          rating = rating_lists[i + 1];
        }
      }
      appDiv.style.color = colorMap[rating];
      setTimeout(updatePoints, 10000);
    })
    .catch((error) => {
      console.error(error);
      appDiv.style.color = colorMap["default"];
      pointsDiv.innerText = "----";
      setTimeout(updatePoints, 10000);
    });
}

function updateTime() {
  let now = new Date();
  // 50ms tolerance
  now.setTime(now.getTime() + 50);
  let hours = now.getHours();
  let minutes = now.getMinutes();
  let seconds = now.getSeconds();
  nowtimeDiv.innerText = `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  let day = now.getDate();
  let month = now.getMonth() + 1;
  let weekday = now.getDay();
  let week = ["日", "一", "二", "三", "四", "五", "六"];
  nowdateDiv.innerText = `${month}/${day} ${week[weekday]}`;
  setTimeout(updateTime, 1000 - now.getMilliseconds());
}

window.onload = function () {
  updatePoints();
  updateTime();
  const nosleep = new NoSleep();

  document.body.onclick = function () {
    appDiv.classList.toggle("layout-points");
    appDiv.classList.toggle("layout-time");
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
  appDiv.classList.add("load-font");
};
