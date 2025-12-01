<script lang="ts">
  import type { 按列统计结果, 总计结果 } from '../types';
  import {
    formatTime,
    formatDate,
    formatSpeed,
    formatDailyTime,
    formatProgress,
  } from '../utils/formatters';
  import { getThemeColors } from '../utils/color';

  // 使用$props()来接收属性
  const {
    列统计结果,
    总统计结果,
    当前任务,
  }: { 列统计结果: 按列统计结果; 总统计结果: 总计结果; 当前任务: string } = $props();
</script>

<table class="stats">
  <thead>
    <tr>
      <th class="symbol"></th>
      <th>名称</th>
      <th>已完成</th>
      <th>剩余</th>
      <th>速度</th>
      <th>日用时</th>
      <th>剩余时间</th>
      <th>预计完成</th>
    </tr>
  </thead>
  <tbody>
    {#each 列统计结果.名称 as 名称, 索引 (名称)}
      <!-- 使用@const简化重复计算 -->
      {@const 已完成 = 列统计结果.已完成[索引]}
      {@const 剩余 = 列统计结果.剩余[索引]}
      {@const 速度 = 列统计结果.速度[索引]}
      {@const 日用时 = 列统计结果.日用时[索引]}
      {@const 剩余时间 = 列统计结果.剩余时间[索引]}
      {@const 预计完成时间 = 列统计结果.预计完成时间[索引]}
      {@const 颜色 = 列统计结果.颜色[索引]}
      {@const 主题色 = getThemeColors(颜色 ? 颜色 : '#ddd')}
      <tr
        style:--theme-color={颜色 ? 颜色 : '#ddd'}
        style:--text-color={主题色.文本颜色}
        style:--background-color={主题色.背景颜色}
        style:--highlight-color={主题色.强调字体颜色}
      >
        <td class="symbol">{当前任务 === 名称 ? '▶' : ''}</td>
        <td>{名称}</td>
        <td>{formatProgress(已完成)}</td>
        <td>{formatProgress(剩余)}</td>
        <td class:highlight={速度 === null || 速度 <= 0}>
          {formatSpeed(速度)}
        </td>
        <td class:highlight={日用时 === null || 日用时 <= 0}>
          {formatDailyTime(日用时)}
        </td>
        <td>
          {formatTime(剩余时间)}
        </td>
        <td>
          {formatDate(预计完成时间)}
        </td>
      </tr>
    {/each}
    <!-- 总计行 -->
    <tr class="total-row">
      <td class="symbol"></td>
      <td>总计</td>
      <td>&nbsp;&nbsp;&nbsp;-.--</td>
      <td>&nbsp;&nbsp;&nbsp;-.--</td>
      <td>{总统计结果.未决任务数 > 0 ? '!' + 总统计结果.未决任务数 : '   -.--/h'}</td>
      <td>{formatDailyTime(总统计结果.总日用时)}</td>
      <td>{formatTime(总统计结果.总剩余时间)}</td>
      <td>{formatDate(总统计结果.预计完成时间)}</td>
    </tr>
  </tbody>
</table>

<style>
  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
  }

  th,
  td {
    padding: 3px;
    text-align: center;
    border: 1px solid #ddd;
    white-space: pre;
  }

  th {
    background-color: #ddd;
    font-weight: bold;
    color: #333;
  }

  tr {
    color: var(--text-color);
    background-color: var(--background-color);
  }

  .highlight {
    font-weight: bold;
    color: var(--highlight-color);
  }

  .total-row {
    font-weight: bold;
    background-color: #ddd;
  }

  @font-face {
    font-family: 'Fira Mono';
    src: url('/font/FiraMono-Regular.ttf') format('truetype');
    src: url('/font/FiraMono-Regular.woff') format('woff');
    src: url('/font/FiraMono-Regular.woff2') format('woff2');
  }

  .stats {
    font-family: 'Fira Mono', 'Courier New', Courier, monospace;
  }

  .symbol {
    background-color: var(--theme-color, #ddd);
    width: 20px;
  }
</style>
