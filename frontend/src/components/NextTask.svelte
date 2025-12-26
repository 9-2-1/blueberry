<script lang="ts">
  import chroma from 'chroma-js';
  import type { 任务统计结果 } from '../types';
  import { formatTime, formatDate } from '../utils/formatters';

  // 使用$props()来接收属性
  const { 下一个任务 }: { 下一个任务: 任务统计结果 } = $props();

  const [, c, h] = $derived(chroma(下一个任务.颜色 ?? '#ddd').oklch());
  const accentColor = $derived(chroma.oklch(0.5, c, h).css());
</script>

<div class="numbers" style:--accent-color={accentColor}>
  <div>
    {下一个任务.名称}
  </div>
  <div>
    {formatTime(下一个任务.剩余时间)}
  </div>
  <div>
    {formatDate(下一个任务.预计完成时间)}
  </div>
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
    color: var(--accent-color);
  }
</style>
