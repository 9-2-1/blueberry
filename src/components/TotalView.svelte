<script lang="ts">
  import type { 总计结果 } from '../types';
  import { formatTime, formatDate, formatDailyTime } from '../utils/formatters';

  // 使用$props()来接收属性
  const { 总统计结果 }: { 总统计结果: 总计结果 } = $props();
</script>

<div class="numbers">
  <div>
    {formatTime(总统计结果.总剩余时间)}
    {#if 总统计结果.未决任务数 > 0}
      !{总统计结果.未决任务数}
    {/if}
  </div>
  <div>{formatDailyTime(总统计结果.总日用时)}</div>
  <div>{formatDate(总统计结果.预计完成时间)}</div>
</div>

<style>
  .numbers {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 40px;
  }
  .numbers div {
    font-size: 40px;
    font-weight: bold;
    font-family: 'Fira Mono', 'Courier New', Courier, monospace;
    color: rgb(0, 183, 255);
  }
</style>
