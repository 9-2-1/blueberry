import express from 'express';
import cors from 'cors';
import path from 'path';
import morgan from 'morgan';
import readXlsxFile from 'read-excel-file/node';
import type { TaskTable } from './types';

const app = express();
const port = 26019;

app.use(morgan('combined'));
app.use(express.text({ type: () => true }));
app.use(cors());

// Serve static files from the frontend dist directory
app.use(express.static(path.join(__dirname, '../../dist')));

// 获取记录表格的所有内容
app.get('/api/get_numbers', (req, res) => {
  try {
    // TODO
    const ret: TaskTable = { example: 0 };
    res.json(ret);
  } catch (error) {
    console.error('Error fetching task table:', error);
    res.status(500).json({ error: 'Failed to fetch task table' });
  }
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

// Handle SPA routing - serve index.html for any non-API routes
app.get(/^(?!\/api\/).*/, (req, res) => {
  res.sendFile(path.join(__dirname, '../../dist/index.html'));
});
