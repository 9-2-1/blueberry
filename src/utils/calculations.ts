import type { 任务表, 进度表 } from '../types';
import { SvelteDate } from 'svelte/reactivity';

// 计算任务进度
export function calculateTaskProgress(任务名称: string, 进度列表: 进度表[]): number {
  const 任务进度记录 = 进度列表
    .filter(record => record.名称 === 任务名称)
    .sort((a, b) => a.时间 - b.时间);
  if (任务进度记录.length === 0) return 0;
  return 任务进度记录[任务进度记录.length - 1].进度;
}

// 计算速度
export function calculateSpeed(任务名称: string, 进度列表: 进度表[], 速度累积时长: number): number {
  const 任务进度记录 = 进度列表
    .filter(record => record.名称 === 任务名称)
    .sort((a, b) => a.时间 - b.时间);
  if (任务进度记录.length < 2) return 0;

  let 完成总数 = 0;
  let 用时总量 = 0;
  const 时间范围 = 速度累积时长 * 60 * 60 * 1000; // 转换为毫秒
  const 现在 = Date.now();

  for (let i = 任务进度记录.length - 1; i > 0; i--) {
    const 当前记录 = 任务进度记录[i];
    const 之前记录 = 任务进度记录[i - 1];

    if (!当前记录.用时) continue; // 跳过没有用时的记录

    const 完成数量 = 当前记录.进度 - 之前记录.进度;
    const 记录时间 = 当前记录.时间;
    const 之前记录时间 = 之前记录.时间;
    const 记录用时 = 当前记录.用时; // 单位为天

    // 计算记录的时间范围
    const 记录开始时间 = Math.max(之前记录时间, 现在 - 时间范围);
    const 记录结束时间 = Math.min(记录时间, 现在);
    const 有效时间比例 = (记录结束时间 - 记录开始时间) / (记录时间 - 之前记录时间);

    if (有效时间比例 <= 0) continue;

    const 有效完成数量 = 完成数量 * 有效时间比例;
    const 有效用时 = 记录用时 * 有效时间比例 * 24 * 60 * 60 * 1000; // 转换为毫秒

    if (用时总量 + 有效用时 >= 时间范围) {
      const 剩余时间 = 时间范围 - 用时总量;
      const 比例 = 剩余时间 / 有效用时;
      完成总数 += 有效完成数量 * 比例;
      用时总量 = 时间范围;
      break;
    } else {
      完成总数 += 有效完成数量;
      用时总量 += 有效用时;
    }
  }

  if (用时总量 === 0) return 0;
  return 完成总数 / (用时总量 / (1000 * 60 * 60)); // 转换为每小时速度
}

// 计算日用时
export function calculateDailyTime(
  任务名称: string,
  进度列表: 进度表[],
  日用时累积时长: number
): number {
  const 任务进度记录 = 进度列表
    .filter(record => record.名称 === 任务名称)
    .sort((a, b) => a.时间 - b.时间);
  if (任务进度记录.length < 2) return 0;

  let 总用时 = 0;
  const 时间范围 = 日用时累积时长 * 24 * 60 * 60 * 1000; // 转换为毫秒
  const 现在 = Date.now();

  for (let i = 任务进度记录.length - 1; i > 0; i--) {
    const 当前记录 = 任务进度记录[i];
    const 之前记录 = 任务进度记录[i - 1];

    if (!当前记录.用时) continue; // 跳过没有用时的记录

    const 记录时间 = 当前记录.时间;
    const 之前记录时间 = 之前记录.时间;
    const 记录用时 = 当前记录.用时; // 单位为天

    // 计算记录的时间范围
    const 记录开始时间 = Math.max(之前记录时间, 现在 - 时间范围);
    const 记录结束时间 = Math.min(记录时间, 现在);
    const 有效时间比例 = (记录结束时间 - 记录开始时间) / (记录时间 - 之前记录时间);

    if (有效时间比例 <= 0) continue;

    const 有效用时 = 记录用时 * 有效时间比例 * 24; // 转换为小时
    总用时 += 有效用时;
  }

  return 总用时 / 日用时累积时长; // 平均日用时，单位为小时
}

// 格式化时间
export function formatTime(seconds: number): string {
  if (seconds <= 0) return '0:00';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours.toString().padStart(4, ' ')}:${minutes.toString().padStart(2, '0')}`;
}

// 格式化日期
export function formatDate(date: Date): string {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = date.getHours();
  return `${month}/${day} ${hours}:`;
}

// 计算剩余时间
export function calculateRemainingTime(速度: number, 剩余: number): string {
  if (速度 <= 0) return '----:--';
  const 剩余时间 = 剩余 / 速度;
  return formatTime(剩余时间 * 3600);
}

// 计算预计完成时间
export function calculateEstimatedCompletion(
  当前时间: SvelteDate,
  速度: number,
  日用时: number,
  剩余: number
): string {
  if (速度 <= 0 || 日用时 <= 0) return '--/-- --:';
  const 剩余时间 = 剩余 / 速度;
  const 预计天数 = 剩余时间 / 日用时;
  const 预计完成日期 = new Date(当前时间.getTime() + 预计天数 * 24 * 60 * 60 * 1000);
  return formatDate(预计完成日期);
}

// 计算总计
export function calculateTotal(
  当前时间: SvelteDate,
  任务列表: 任务表[],
  进度列表: 进度表[],
  速度累积时长: number,
  日用时累积时长: number
) {
  let 总日用时 = 0;
  let 总剩余时间 = 0;
  let 未决任务数 = 0;

  for (const 任务 of 任务列表) {
    const 已完成 = calculateTaskProgress(任务.名称, 进度列表);
    const 剩余 = 任务.总数 - 已完成;
    const 速度 = calculateSpeed(任务.名称, 进度列表, 速度累积时长);
    const 日用时 = calculateDailyTime(任务.名称, 进度列表, 日用时累积时长);

    if (日用时 > 0) {
      总日用时 += 日用时;
    }

    if (速度 > 0) {
      总剩余时间 += 剩余 / 速度;
    } else {
      未决任务数++;
    }
  }

  const 预计完成时间 =
    总日用时 > 0 ? calculateEstimatedCompletion(当前时间, 1, 总日用时, 总剩余时间) : '--/-- --:';

  return {
    总日用时: formatTime(总日用时 * 3600),
    总剩余时间: formatTime(总剩余时间 * 3600),
    预计完成时间,
    未决任务数,
  };
}
