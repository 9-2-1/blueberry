export type { 任务表, 进度表, APIResponse, APIError } from '../server/src/types';

// 单个任务的统计结果
export interface 任务统计结果 {
  名称: string;
  已完成: number;
  剩余: number;
  速度: number | null;
  日用时: number | null;
  剩余时间: number | null;
  预计完成时间: number | null;
  颜色?: string;
}

// 按列分类的统计结果
export interface 按列统计结果 {
  名称: string[];
  已完成: number[];
  剩余: number[];
  速度: (number | null)[];
  日用时: (number | null)[];
  剩余时间: (number | null)[];
  预计完成时间: (number | null)[];
  颜色: (string | undefined)[];
}

// 总计结果
export interface 总计结果 {
  总日用时: number | null;
  总剩余时间: number | null;
  预计完成时间: number | null;
  未决任务数: number;
}
