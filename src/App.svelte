<script lang="ts">
  import type { 任务表, 进度表, APIResponse, APIError } from './types';
  import { SvelteDate } from 'svelte/reactivity';
  import { onDestroy } from 'svelte';

  import Settings from './components/Settings.svelte';
  import NextTask from './components/NextTask.svelte';
  import TotalView from './components/TotalView.svelte';
  import TaskTable from './components/TaskTable.svelte';
  import {
    calculateStats,
    calculateColumnStats,
    calculateTotal,
    calculateLastProgressRecord,
    calculateNextTask,
  } from './utils/calculations';

  // 状态管理
  let 任务列表 = $state<任务表[]>([]);
  let 进度列表 = $state<进度表[]>([]);
  let 速度累积时长 = $state(4); // 默认4小时
  let 日用时累积时长 = $state(3); // 默认3天
  let 当前时间 = new SvelteDate();
  let loading = $state(true);
  let error = $state('');
  let refreshStatus = $state<'idle' | 'refreshing' | 'success' | 'error'>('idle');

  // 从URL获取初始配置
  const urlParams = new URLSearchParams(window.location.search);
  const 速度累积时长Param = urlParams.get('速度累积时长');
  const 日用时累积时长Param = urlParams.get('日用时累积时长');

  if (速度累积时长Param) {
    速度累积时长 = Number(速度累积时长Param);
  }

  if (日用时累积时长Param) {
    日用时累积时长 = Number(日用时累积时长Param);
  }

  // 计算统计结果
  const 统计结果 = $derived(
    calculateStats(任务列表, 进度列表, 当前时间, 速度累积时长, 日用时累积时长)
  );

  const 列统计结果 = $derived(calculateColumnStats(统计结果));

  const 总统计结果 = $derived(
    calculateTotal(任务列表, 进度列表, 当前时间, 速度累积时长, 日用时累积时长)
  );

  const 上一个进度 = $derived(calculateLastProgressRecord(进度列表));

  const 下一个任务 = $derived(calculateNextTask(上一个进度?.名称 ?? '', 任务列表));

  const 下一个任务统计结果 = $derived(
    下一个任务 !== null ? (统计结果.find(任务 => 任务.名称 === 下一个任务) ?? null) : null
  );

  // 获取数据
  async function fetchData() {
    if (refreshStatus === 'refreshing') {
      return;
    }
    refreshStatus = 'refreshing';
    error = '';
    try {
      const response = await fetch('./api/get_table');
      const data = (await response.json()) as APIResponse | APIError;
      if ('success' in data && data.success) {
        任务列表 = data.任务;
        进度列表 = data.进度;
        当前时间.setTime(Date.now());
        refreshStatus = 'success';
        // 2秒后隐藏成功状态
        setTimeout(() => {
          refreshStatus = 'idle';
        }, 2000);
      } else {
        error = data.error;
        refreshStatus = 'error';
      }
    } catch (err) {
      error = 'Failed to fetch data';
      console.error(err);
      refreshStatus = 'error';
    } finally {
      loading = false;
    }
  }

  // 初始化数据
  fetchData();

  // 设置10秒自动刷新
  const refreshInterval = setInterval(fetchData, 10000);

  // 组件销毁时清除定时器
  onDestroy(() => {
    clearInterval(refreshInterval);
  });
</script>

<main>
  <!-- 刷新状态指示器 -->
  <div class="refresh-indicator">
    {#if refreshStatus === 'refreshing'}
      <div class="refresh-animation"></div>
    {:else if refreshStatus === 'error'}
      <div class="refresh-error">X</div>
    {:else if refreshStatus === 'success'}
      <div class="refresh-success">✓</div>
    {/if}
  </div>

  <!-- 设置区域 -->
  <Settings bind:速度累积时长 bind:日用时累积时长 />

  <!-- 错误信息 -->
  {#if error}
    <div class="error">{error}</div>
  {/if}

  <!-- 加载状态 -->
  {#if loading}
    <div class="loading">加载中...</div>
  {:else}
    <TotalView {总统计结果} />
    {#if 下一个任务统计结果 !== null}
      <NextTask 下一个任务={下一个任务统计结果} />
    {/if}
    <TaskTable {列统计结果} {总统计结果} 当前任务={上一个进度?.名称 ?? ''} />
  {/if}
</main>

<style>
  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    font-family: Arial, sans-serif;
    position: relative;
  }

  .error {
    color: red;
    background-color: #ffebee;
    padding: 10px;
    border-radius: 4px;
    margin-bottom: 20px;
  }

  .loading {
    text-align: center;
    padding: 20px;
    color: #666;
  }

  /* 刷新状态指示器 */
  .refresh-indicator {
    position: absolute;
    top: 20px;
    right: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* 刷新动画 */
  .refresh-animation {
    width: 20px;
    height: 20px;
    border: 2px solid #4a90e2;
    border-top: 2px solid transparent;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  /* 成功标记 */
  .refresh-success {
    width: 20px;
    height: 20px;
    color: #4caf50;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    line-height: 20px;
  }

  /* 错误标记 */
  .refresh-error {
    width: 20px;
    height: 20px;
    color: #f44336;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    line-height: 20px;
  }
</style>
