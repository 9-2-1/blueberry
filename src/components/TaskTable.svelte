<script lang="ts">
  import type { 任务表, 进度表 } from '../types';
  import {
    calculateTaskProgress,
    calculateSpeed,
    calculateDailyTime,
    formatTime,
    calculateRemainingTime,
    calculateEstimatedCompletion,
    calculateTotal,
  } from '../utils/calculations';
  import { getThemeColors } from '../utils/color';
  import { SvelteDate } from 'svelte/reactivity';

  // 使用$props()来接收属性
  const {
    当前时间 = new SvelteDate(),
    任务列表 = [],
    进度列表 = [],
    速度累积时长 = 72,
    日用时累积时长 = 3,
  }: {
    当前时间: SvelteDate;
    任务列表: 任务表[];
    进度列表: 进度表[];
    速度累积时长: number;
    日用时累积时长: number;
  } = $props();
  const 总计 = $derived(calculateTotal(当前时间, 任务列表, 进度列表, 速度累积时长, 日用时累积时长));
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
    {#each 任务列表 as 任务 (任务.名称)}
      <!-- 使用@const简化重复计算 -->
      {@const 已完成 = calculateTaskProgress(任务.名称, 进度列表)}
      {@const 剩余 = 任务.总数 - 已完成}
      {@const 速度 = calculateSpeed(任务.名称, 进度列表, 速度累积时长)}
      {@const 日用时 = calculateDailyTime(任务.名称, 进度列表, 日用时累积时长)}
      {@const 主题色 = getThemeColors(任务.颜色 ? 任务.颜色 : '#ddd')}
      <tr
        style:--theme-color={任务.颜色 ? 任务.颜色 : '#ddd'}
        style:--text-color={主题色.文本颜色}
        style:--background-color={主题色.背景颜色}
        style:--highlight-color={主题色.强调字体颜色}
      >
        <td class="symbol"></td>
        <td>{任务.名称}</td>
        <td>{已完成}</td>
        <td>{剩余}</td>
        <td class:highlight={速度 <= 0}>
          {速度.toFixed(2)}/h
        </td>
        <td class:highlight={日用时 <= 0}>
          {formatTime(日用时 * 3600)}/d
        </td>
        <td>
          {calculateRemainingTime(速度, 剩余)}
        </td>
        <td>
          {calculateEstimatedCompletion(当前时间, 速度, 日用时, 剩余)}
        </td>
      </tr>
    {/each}
    <!-- 总计行 -->
    <tr class="total-row">
      <td class="symbol"></td>
      <td>总计</td>
      <td>--</td>
      <td>--</td>
      <td>--</td>
      <td>{总计.总日用时}/d</td>
      <td>{总计.总剩余时间}</td>
      <td>{总计.预计完成时间}</td>
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
