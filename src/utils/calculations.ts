import type { 任务表, 进度表, 任务统计结果, 按列统计结果, 总计结果 } from '../types';
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
export function calculateSpeed(
  任务名称: string,
  进度列表: 进度表[],
  速度累积时长: number
): number | null {
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
): number | null {
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

// 计算剩余时间
export function calculateRemainingTime(速度: number | null, 剩余: number): number | null {
  if (速度 === null || 速度 <= 0) return null;
  return (剩余 / 速度) * 3600; // 转换为秒
}

// 计算预计完成时间
export function calculateEstimatedCompletion(
  当前时间: SvelteDate,
  速度: number | null,
  日用时: number | null,
  剩余: number
): number | null {
  if (速度 === null || 日用时 === null || 速度 <= 0 || 日用时 <= 0) return null;
  const 剩余时间 = 剩余 / 速度; // 小时
  const 预计天数 = 剩余时间 / 日用时;
  return 当前时间.getTime() + 预计天数 * 24 * 60 * 60 * 1000; // 转换为时间戳
}

// 计算单个任务的统计结果
export function calculateTaskStats(
  任务: 任务表,
  进度列表: 进度表[],
  当前时间: SvelteDate,
  速度累积时长: number,
  日用时累积时长: number
): 任务统计结果 {
  const 已完成 = calculateTaskProgress(任务.名称, 进度列表);
  const 剩余 = 任务.总数 - 已完成;
  const 速度 = calculateSpeed(任务.名称, 进度列表, 速度累积时长);
  const 日用时 = calculateDailyTime(任务.名称, 进度列表, 日用时累积时长);
  const 剩余时间 = calculateRemainingTime(速度, 剩余);
  const 预计完成时间 = calculateEstimatedCompletion(当前时间, 速度, 日用时, 剩余);

  return { 名称: 任务.名称, 已完成, 剩余, 速度, 日用时, 剩余时间, 预计完成时间, 颜色: 任务.颜色 };
}

// 计算统计结果
export function calculateStats(
  任务列表: 任务表[],
  进度列表: 进度表[],
  当前时间: SvelteDate,
  速度累积时长: number,
  日用时累积时长: number
): 任务统计结果[] {
  return 任务列表.map(任务 =>
    calculateTaskStats(任务, 进度列表, 当前时间, 速度累积时长, 日用时累积时长)
  );
}

// 计算按列分类的统计结果
export function calculateColumnStats(任务统计结果列表: 任务统计结果[]): 按列统计结果 {
  return {
    名称: 任务统计结果列表.map(统计 => 统计.名称),
    已完成: 任务统计结果列表.map(统计 => 统计.已完成),
    剩余: 任务统计结果列表.map(统计 => 统计.剩余),
    速度: 任务统计结果列表.map(统计 => 统计.速度),
    日用时: 任务统计结果列表.map(统计 => 统计.日用时),
    剩余时间: 任务统计结果列表.map(统计 => 统计.剩余时间),
    预计完成时间: 任务统计结果列表.map(统计 => 统计.预计完成时间),
    颜色: 任务统计结果列表.map(统计 => 统计.颜色),
  };
}

// 计算总计
export function calculateTotal(
  任务列表: 任务表[],
  进度列表: 进度表[],
  当前时间: SvelteDate,
  速度累积时长: number,
  日用时累积时长: number
): 总计结果 {
  const 任务统计结果列表 = 任务列表.map(任务 =>
    calculateTaskStats(任务, 进度列表, 当前时间, 速度累积时长, 日用时累积时长)
  );

  let 总日用时 = 0;
  let 总剩余时间 = 0;
  let 未决任务数 = 0;

  for (const 统计 of 任务统计结果列表) {
    if (统计.日用时 !== null && 统计.日用时 > 0) {
      总日用时 += 统计.日用时;
    }

    if (统计.剩余时间 !== null && 统计.剩余时间 > 0) {
      总剩余时间 += 统计.剩余时间;
    } else {
      未决任务数++;
    }
  }

  let 预计完成时间: number | null = null;
  if (总日用时 > 0 && 总剩余时间 > 0) {
    const 预计天数 = 总剩余时间 / 3600 / 总日用时;
    预计完成时间 = 当前时间.getTime() + 预计天数 * 24 * 60 * 60 * 1000;
  }

  return { 总日用时, 总剩余时间, 预计完成时间, 未决任务数 };
}

export function calculateLastProgressRecord(进度列表: 进度表[]): 进度表 | null {
  const 最后进度记录 = 进度列表.find(记录 => 记录.用时 !== undefined);
  return 最后进度记录 ?? null;
}

export function calculateNextTask(名称: string, 任务列表: 任务表[]): string | null {
  const 任务索引 = 任务列表.findIndex(任务 => 任务.名称 === 名称);
  const 有效索引 = 任务索引 === -1 ? 0 : 任务索引 + 1;
  return 任务列表[有效索引]?.名称;
}
