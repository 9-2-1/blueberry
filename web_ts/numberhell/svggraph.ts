class SVGGraph {
  xPixel = 200;
  yPixel = 300;
  xMin = -10;
  xMax = 10;
  yMin = -10;
  yMax = 10;
  svg: string[] = [];
  constructor() {}

  setRange(xMin: number, xMax: number, yMin: number, yMax: number) {
    this.xMin = xMin;
    this.xMax = xMax;
    this.yMin = yMin;
    this.yMax = yMax;
  }

  autoRange(
    points: { x: number; y: number }[],
    reset: boolean,
    mode: "x" | "y" | "xy",
  ) {
    if (points.length == 0) {
      return;
    }
    let i = 0;
    if (reset) {
      if (mode == "x" || mode == "xy") {
        this.xMin = points[0].x;
        this.xMax = points[0].x;
      }
      if (mode == "y" || mode == "xy") {
        this.yMin = points[0].y;
        this.yMax = points[0].y;
      }
      i++;
    }
    for (; i < points.length; i++) {
      if (mode == "x" || mode == "xy") {
        this.xMin = Math.min(this.xMin, points[i].x);
        this.xMax = Math.max(this.xMax, points[i].x);
      }
      if (mode == "y" || mode == "xy") {
        this.yMin = Math.min(this.yMin, points[i].y);
        this.yMax = Math.max(this.yMax, points[i].y);
      }
    }
  }

  autoYRangeLine(points: { x: number; y: number }[], reset: boolean) {
    // 点需要从左到右连成线。从左到右
    let i = 0;
    // left bound
    while (i < points.length && points[i].x < this.xMin) {
      i++;
    }
    if (i >= points.length) {
      // 所有点都在xMin的左边
      if (reset) {
        this.yMin = points[points.length - 1].y;
        this.yMax = points[points.length - 1].y;
      }
      return;
    }
    if (i != 0) {
      const vY =
        points[i - 1].y +
        ((points[i].y - points[i - 1].y) * (this.xMin - points[i - 1].x)) /
          (points[i].x - points[i - 1].x);
      if (reset) {
        this.yMin = vY;
        this.yMax = vY;
      } else {
        this.yMin = Math.min(this.yMin, vY);
        this.yMax = Math.max(this.yMax, vY);
      }
    } else {
      if (reset) {
        this.yMin = points[0].y;
        this.yMax = points[0].y;
      } else {
        this.yMin = Math.min(this.yMin, points[0].y);
        this.yMax = Math.max(this.yMax, points[0].y);
      }
      i = 1;
    }
    while (i < points.length && points[i].x <= this.xMax) {
      this.yMin = Math.min(this.yMin, points[i].y);
      this.yMax = Math.max(this.yMax, points[i].y);
      i++;
    }
    if (i != points.length) {
      const vY =
        points[i - 1].y +
        ((points[i].y - points[i - 1].y) * (this.xMax - points[i - 1].x)) /
          (points[i].x - points[i - 1].x);
      this.yMin = Math.min(this.yMin, vY);
      this.yMax = Math.max(this.yMax, vY);
    }
  }

  // 修复y轴范围，防止y轴范围太小
  fixYRange() {
    const yRange = this.yMax - this.yMin;
    if (yRange < 1) {
      const avg = (this.yMin + this.yMax) / 2;
      this.yMin = avg - 1 / 2;
      this.yMax = avg + 1 / 2;
      if (this.yMin < 0) {
        this.yMax += -this.yMin;
        this.yMin = 0;
      }
    }
  }

  zoomRange(xZoom: number, yZoom: number) {
    const xChange = (this.xMax - this.xMin) * (xZoom - 1) / 2;
    const yChange = (this.yMax - this.yMin) * (yZoom - 1) / 2;
    this.xMin -= xChange;
    this.xMax += xChange;
    this.yMin -= yChange;
    this.yMax += yChange;
  }

  findXInterval(xUnit: number, xMinGap: number) {
    const xIntervalMin = ((this.xMax - this.xMin) / this.xPixel) * xMinGap;
    let xInterval = xUnit;
    while (xInterval < xIntervalMin) {
      xInterval *= 10;
    }
    if (xInterval > xUnit) {
      if (xInterval / 5 > xIntervalMin) {
        xInterval /= 5;
      } else if (xInterval / 2 > xIntervalMin) {
        xInterval /= 2;
      }
    }
    return xInterval;
  }

  findYInterval(yUnit: number, yMinGap: number) {
    const yIntervalMin = ((this.yMax - this.yMin) / this.yPixel) * yMinGap;
    let yInterval = yUnit;
    while (yInterval < yIntervalMin) {
      yInterval *= 10;
    }
    if (yInterval > yUnit) {
      if (yInterval / 5 > yIntervalMin) {
        yInterval /= 5;
      } else if (yInterval / 2 > yIntervalMin) {
        yInterval /= 2;
      }
    }
    return yInterval;
  }

  renderStart(cardDiv: HTMLDivElement) {
    this.xPixel = cardDiv.clientWidth;
    this.yPixel = cardDiv.clientHeight;
    this.svg = [`<svg viewBox="0 0 ${this.xPixel} ${this.yPixel}">`];
  }

  renderBackground(color: string) {
    this.svg.push(
      `<rect x="0" y="0" width="${this.xPixel}" height="${this.yPixel}" fill="${color}"/>`,
    );
  }

  // x轴
  renderXAxis(
    yPos: number,
    xInterval: number,
    xOffset: number,
    color: string,
    xTag: null | ((x: number) => string),
  ) {
    yPos = (this.yPixel * (this.yMax - yPos)) / (this.yMax - this.yMin);
    this.svg.push(
      `<line x1="0" y1="${yPos}" x2="${this.xPixel}" y2="${yPos}" stroke="${color}" stroke-width="1" />`,
    );
    const xBegin =
      Math.ceil((this.xMin - xOffset) / xInterval) * xInterval + xOffset;
    let x = xBegin;
    while (x <= this.xMax) {
      const xPos = (this.xPixel * (x - this.xMin)) / (this.xMax - this.xMin);
      // 绘制x轴刻度
      this.svg.push(
        `<line x1="${xPos}" y1="${yPos - 5}" x2="${xPos}" y2="${yPos + 5}" stroke="${color}" stroke-width="1" />`,
      );
      // 绘制x轴标签
      const xLabel = xTag === null ? x.toString() : xTag(x);
      this.svg.push(
        `<text x="${xPos}" y="${yPos - 5}" fill="${color}" font-size="12" text-anchor="middle">${xLabel}</text>`,
      );
      x += xInterval;
    }
  }

  // y轴
  renderYAxis(
    xPos: number,
    yInterval: number,
    yOffset: number,
    color: string,
    yTag: null | ((y: number) => string),
  ) {
    xPos = (this.xPixel * (xPos - this.xMin)) / (this.xMax - this.xMin);
    this.svg.push(
      `<line x1="${xPos}" y1="0" x2="${xPos}" y2="${this.yPixel}" stroke="${color}" stroke-width="1" />`,
    );
    const yBegin =
      Math.ceil((this.yMin - yOffset) / yInterval) * yInterval + yOffset;
    let y = yBegin;
    while (y <= this.yMax) {
      const yPos = (this.yPixel * (this.yMax - y)) / (this.yMax - this.yMin);
      // 绘制y轴刻度
      this.svg.push(
        `<line x1="${xPos - 5}" y1="${yPos}" x2="${xPos + 5}" y2="${yPos}" stroke="${color}" stroke-width="1" />`,
      );
      // 绘制y轴标签
      const yLabel = yTag === null ? y.toString() : yTag(y);
      this.svg.push(
        `<text x="${xPos - 10}" y="${yPos}" fill="${color}" font-size="12" text-anchor="end">${yLabel}</text>`,
      );
      y += yInterval;
    }
  }

  renderPoints(
    points: { x: number; y: number }[],
    color: string,
    width: number,
  ) {
    let posToPixel = (pos: { x: number; y: number }) => ({
      x: (this.xPixel * (pos.x - this.xMin)) / (this.xMax - this.xMin),
      y: (this.yPixel * (this.yMax - pos.y)) / (this.yMax - this.yMin),
    });
    const linePixel = points.map(posToPixel);
    while (linePixel.length > 1 && linePixel[0].x < -5) {
      linePixel.shift();
    }
    while (
      linePixel.length > 1 &&
      linePixel[linePixel.length - 1].x > this.xPixel + 5
    ) {
      linePixel.pop();
    }
    for (const p of linePixel) {
      this.svg.push(
        `<circle cx="${p.x}" cy="${p.y}" r="${width}" fill="${color}" />`,
      );
    }
  }

  renderLine(
    points: { x: number; y: number }[],
    color: string,
    style: "solid" | "dashed",
    width: number,
  ) {
    let posToPixel = (pos: { x: number; y: number }) => ({
      x: (this.xPixel * (pos.x - this.xMin)) / (this.xMax - this.xMin),
      y: (this.yPixel * (this.yMax - pos.y)) / (this.yMax - this.yMin),
    });
    const linePixel = points.map(posToPixel);
    while (linePixel.length > 1 && linePixel[1].x < 0) {
      linePixel.shift();
    }
    while (
      linePixel.length > 1 &&
      linePixel[linePixel.length - 2].x > this.xPixel
    ) {
      linePixel.pop();
    }
    const linePath = linePixel.map((p) => `${p.x} ${p.y}`).join("L");
    this.svg.push(
      `<path d="M${linePath}" stroke="${color}" stroke-linecap="round" stroke-linejoin="round"`,
    );
    this.svg.push(
      `stroke-width="${width}" fill="none" stroke-dasharray="${style === "dashed" ? "5,5" : ""}" />`,
    );
  }

  renderTitle(title: string, color: string) {
    this.svg.push(
      `<text x="5" y="21" fill="${color}" font-size="16" font-weight="bold" text-anchor="left">${title}</text>`,
    );
  }

  renderValue(value: number | string, color: string, size: number) {
    this.svg.push(
      `<text x="${this.xPixel / 2}" y="${this.yPixel / 2}" dominant-baseline="middle" text-anchor="middle"`,
    );
    this.svg.push(
      ` fill="${color}" font-size="${this.yPixel * size}" font-weight="bold">${value}`,
    );
    this.svg.push("</text>");
  }

  renderUpdateTime(value: number, color: string) {
    this.svg.push(
      `<text x="${this.xPixel}" y="${this.yPixel - 5}" fill="${color}" font-size="16" text-anchor="end">${new Date(value * 1000).toLocaleString()}</text>`,
    );
  }

  renderTo(cardDiv: HTMLDivElement) {
    cardDiv.innerHTML = this.svg.join("");
  }
}
