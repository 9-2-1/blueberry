<script lang="ts">
  import type { 任务表, 进度表, APIResponse, APIError } from './types';
  import { SvelteDate } from 'svelte/reactivity';

  import Settings from './components/Settings.svelte';
  import TaskTable from './components/TaskTable.svelte';

  // 状态管理
  let 任务列表 = $state<任务表[]>([]);
  let 进度列表 = $state<进度表[]>([]);
  let 速度累积时长 = $state(72); // 默认3天（小时）
  let 日用时累积时长 = $state(3); // 默认3天
  let 当前时间 = $state(new SvelteDate());
  let loading = $state(true);
  let error = $state('');

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

  // 获取数据
  async function fetchData() {
    loading = true;
    error = '';
    try {
      const response = await fetch('http://localhost:26019/api/get_table');
      const data = (await response.json()) as APIResponse | APIError;
      if ('success' in data && data.success) {
        任务列表 = data.任务;
        进度列表 = data.进度;
        当前时间 = new SvelteDate();
      } else {
        error = data.error;
      }
    } catch (err) {
      error = 'Failed to fetch data';
      console.error(err);
    } finally {
      loading = false;
    }
  }

  // 初始化数据
  fetchData();
</script>

<main>
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
    <!-- 任务表格 -->
    <TaskTable {当前时间} {任务列表} {进度列表} {速度累积时长} {日用时累积时长} />
  {/if}
</main>

<style>
  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    font-family: Arial, sans-serif;
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
</style>
