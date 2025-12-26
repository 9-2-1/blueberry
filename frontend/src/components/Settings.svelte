<script lang="ts">
  // 使用$props()和$bindable()来实现双向绑定
  let {
    速度累积时长 = $bindable(),
    日用时累积时长 = $bindable(),
  }: { 速度累积时长: number; 日用时累积时长: number } = $props();

  // 更新URL参数
  function updateURL() {
    const url = new URL(window.location.href);
    url.searchParams.set('速度累积时长', 速度累积时长.toString());
    url.searchParams.set('日用时累积时长', 日用时累积时长.toString());
    window.history.replaceState({}, '', url);
  }
</script>

<div class="settings">
  <div class="setting-item">
    <label for="速度累积时长">速度累积时长（小时）：</label>
    <input
      id="速度累积时长"
      type="number"
      bind:value={速度累积时长}
      min="1"
      step="1"
      onchange={updateURL}
    />
  </div>
  <div class="setting-item">
    <label for="日用时累积时长">日用时累积时长（天）：</label>
    <input
      id="日用时累积时长"
      type="number"
      bind:value={日用时累积时长}
      min="1"
      step="1"
      onchange={updateURL}
    />
  </div>
</div>

<style>
  .settings {
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
    padding: 15px;
    background-color: #f5f5f5;
    border-radius: 8px;
  }

  .setting-item {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  input[type='number'] {
    width: 100px;
    padding: 5px;
    border: 1px solid #ddd;
    border-radius: 4px;
  }
</style>
