import express from 'express';
import cors from 'cors';
import path from 'path';
import morgan from 'morgan';
import readXlsxFile from 'read-excel-file/node';
import type { 任务表, 进度表, APIResponse, APIError } from './types';
import { config } from './config';

const app = express();
const port = 26019;

app.use(morgan('combined'));
app.use(express.text({ type: () => true }));
app.use(cors());

// Serve static files from the frontend dist directory
app.use(express.static(path.join(__dirname, '../../dist')));

// 获取记录表格的所有内容
app.get('/api/get_table', async (req, res) => {
  try {
    const excelPath = path.join(__dirname, '../../记录.xlsx');
    
    // 读取任务表
    const 任务表Rows = await readXlsxFile(excelPath, {
      sheet: '任务'
    });
    
    // 读取进度表
    const 进度表Rows = await readXlsxFile(excelPath, {
      sheet: '进度'
    });
    
    // 转换任务表数据
    const 任务: 任务表[] = [];
    const 任务表头 = 任务表Rows[0];
    for (let i = 1; i < 任务表Rows.length; i++) {
      const row = 任务表Rows[i];
      if (row.every(cell => cell === null || cell === '')) continue; // 忽略完全空白的行
      
      const 开始日期 = new Date(row[任务表头.indexOf('开始')] as string);
      const 结束日期 = new Date(row[任务表头.indexOf('结束')] as string);
      
      // 假设Excel表格内时间的时区处于东八区，转换为UTC时间戳
      const 开始时间戳 = 开始日期.getTime() - config.excelTimezoneOffset;
      const 结束时间戳 = 结束日期.getTime() - config.excelTimezoneOffset;
      
      const 任务项: 任务表 = {
        名称: row[任务表头.indexOf('名称')] as string,
        开始: 开始时间戳,
        结束: 结束时间戳,
        总数: Number(row[任务表头.indexOf('总数')]),
        颜色: row[任务表头.indexOf('颜色')] as string || undefined
      };
      
      任务.push(任务项);
    }
    
    // 转换进度表数据
    const 进度: 进度表[] = [];
    const 进度表头 = 进度表Rows[0];
    for (let i = 1; i < 进度表Rows.length; i++) {
      const row = 进度表Rows[i];
      if (row.every(cell => cell === null || cell === '')) continue; // 忽略完全空白的行
      
      const 时间日期 = new Date(row[进度表头.indexOf('时间')] as string);
      // 假设Excel表格内时间的时区处于东八区，转换为UTC时间戳
      const 时间戳 = 时间日期.getTime() - config.excelTimezoneOffset;
      
      const 进度项: 进度表 = {
        时间: 时间戳,
        名称: row[进度表头.indexOf('名称')] as string,
        进度: Number(row[进度表头.indexOf('进度')]),
        用时: row[进度表头.indexOf('用时')] ? Number(row[进度表头.indexOf('用时')]) : undefined
      };
      
      进度.push(进度项);
    }
    
    // 按时间升序排序进度表
    进度.sort((a, b) => a.时间 - b.时间);
    
    const response: APIResponse = {
      success: true,
      任务,
      进度
    };
    
    res.json(response);
  } catch (error) {
    console.error('Error fetching task table:', error);
    const errorResponse: APIError = {
      success: false,
      error: 'Failed to fetch task table: ' + (error as Error).message
    };
    res.status(500).json(errorResponse);
  }
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

// Handle SPA routing - serve index.html for any non-API routes
app.get(/^(?!\/api\/).*/, (req, res) => {
  res.sendFile(path.join(__dirname, '../../dist/index.html'));
});
