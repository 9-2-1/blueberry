// 格式化时间
export function formatTime(seconds: number | null): string {
  if (seconds === null || seconds < 0) return '   -:--';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${pad4S(hours)}:${pad2(minutes)}`;
}

function pad4S(x: number) {
  return x.toString().padStart(4, ' ');
}

function pad2(x: number) {
  return x.toString().padStart(2, '0');
}

// 格式化日期
export function formatDate(timestamp: number | null): string {
  if (timestamp === null) return '--/-- --:';
  const date = new Date(timestamp);
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = date.getHours();
  return `${pad2(month)}/${pad2(day)} ${pad2(hours)}:`;
}

// 格式化速度
export function formatSpeed(speed: number | null): string {
  if (speed === null || speed < 0) return '   -.--/h';
  return `${speed.toFixed(2).padStart(7, ' ')}/h`;
}

// 格式化日用时
export function formatDailyTime(time: number | null): string {
  if (time === null || time < 0) return ' -:--/d';
  return `${formatTime(time * 3600)}/d`;
}

// 格式化进度
export function formatProgress(progress: number | null): string {
  if (progress === null) return '   -.--';
  let retn = progress.toFixed(2);
  retn = retn.padStart(7, ' ');
  retn = stripTrailingZero(retn);
  retn = retn.padEnd(7, ' ');
  return retn;
}

function stripTrailingZero(value: string): string {
  return value.replace(/\.?0+$/, '');
}
