function updatePoints() {
  fetch("/get_points", { method: "post" })
    .then((response) => response.json())
    .then((points) => {
      document.getElementById("points").innerText = points;
      document.getElementById("app").classList.remove("status-D");
      document.getElementById("app").classList.remove("status-C");
      document.getElementById("app").classList.remove("status-B");
      document.getElementById("app").classList.remove("status-A");
      document.getElementById("app").classList.remove("status-AA");
      const point_thresholds = [-500, -200, 0, 200, 500];
      const rating_lists = ["D", "C", "B", "A", "AA", "AAA"];
      let rating = "D";
      for (const x of rating_lists) {
        document.getElementById("app").classList.remove("status-" + x);
      }
      for (const [i, x] of point_thresholds.entries()) {
        if (points >= x) {
          rating = rating_lists[i + 1];
        }
      }
      document.getElementById("app").classList.add("status-" + rating);
      setTimeout(updatePoints, 10000);
    })
    .catch((error) => {
      console.error(error);
      document.getElementById("points").innerText = "----";
      setTimeout(updatePoints, 10000);
    });
}

function updateTime() {
  let now = new Date();
  let hours = now.getHours();
  let minutes = now.getMinutes();
  let seconds = now.getSeconds();
  document.getElementById("nowtime").innerText =
    `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  setTimeout(updateTime, 1000);
  let day = now.getDate();
  let month = now.getMonth() + 1;
  let weekday = now.getDay();
  let week = ["日", "一", "二", "三", "四", "五", "六"];
  document.getElementById("nowdate").innerText =
    `${month.toString().padStart(2, "0")}/${day.toString().padStart(2, "0")} ${week[weekday]}`;
}

window.onload = function () {
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
