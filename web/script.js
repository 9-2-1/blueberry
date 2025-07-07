function updatePoints() {
  fetch("/get_points", { method: "post" })
    .then((response) => response.json())
    .then((points) => {
      document.getElementById("points").innerText = points;
      setTimeout(updatePoints, 10000);
    })
    .catch((error) => {
      console.error(error);
      document.getElementById("points").innerText = "----";
      setTimeout(updatePoints, 10000);
    });
}

document.body.onload = updatePoints;

document.body.onclick = function () {
  // toggle fullscreen
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else {
    document.documentElement.requestFullscreen();
  }
};
