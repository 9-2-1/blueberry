export interface 任务表 {
  名称: string;
  开始: number; // timestamp in milliseconds
  结束: number; // timestamp in milliseconds
  总数: number;
  颜色?: string;
}

export interface 进度表 {
  时间: number; // timestamp in milliseconds
  名称: string;
  进度: number;
  用时?: number; // 单位为天
}

export interface APIResponse {
  success: true;
  任务: 任务表[];
  进度: 进度表[];
}

export interface APIError {
  success: false;
  error: string;
}

export type Response = APIResponse | APIError;
