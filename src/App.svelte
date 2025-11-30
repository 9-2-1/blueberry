<script lang="ts">
	import type { 任务表, 进度表, APIResponse, APIError } from './types';

	// 状态管理
	let 任务列表 = $state<任务表[]>([]);
	let 进度列表 = $state<进度表[]>([]);
	let 速度累积时长 = $state(72); // 默认3天（小时）
	let 日用时累积时长 = $state(3); // 默认3天
	let loading = $state(true);
	let error = $state('');
    $inspect(进度列表)

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

	// 更新URL参数
	function updateURL() {
		const url = new URL(window.location.href);
		url.searchParams.set('速度累积时长', 速度累积时长.toString());
		url.searchParams.set('日用时累积时长', 日用时累积时长.toString());
		window.history.replaceState({}, '', url);
	}

	// 获取数据
	async function fetchData() {
		loading = true;
		error = '';
		try {
			const response = await fetch('http://localhost:26019/api/get_table');
			const data = await response.json() as APIResponse | APIError;
			if ('success' in data && data.success) {
				任务列表 = data.任务;
				进度列表 = data.进度;
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

	// 计算任务进度
	function calculateTaskProgress(任务名称: string) {
		const 任务进度记录 = 进度列表.filter(record => record.名称 === 任务名称).sort((a, b) => a.时间 - b.时间);
		if (任务进度记录.length === 0) return 0;
		return 任务进度记录[任务进度记录.length - 1].进度;
	}

	// 计算速度
	function calculateSpeed(任务名称: string) {
		const 任务进度记录 = 进度列表.filter(record => record.名称 === 任务名称).sort((a, b) => a.时间 - b.时间);
		if (任务进度记录.length < 2) return 0;

		let 完成总数 = 0;
		let 用时总量 = 0;
		const 时间范围 = 速度累积时长 * 60 * 60 * 1000; // 转换为毫秒
		const 现在 = Date.now();

		for (let i = 任务进度记录.length - 1; i > 0; i--) {
			const 当前记录 = 任务进度记录[i];
			const 之前记录 = 任务进度记录[i - 1];

			if (!当前记录.用时) continue; // 跳过没有用时的记录

			const 完成数量 = 当前记录.进度 - 之前记录.进度;
			const 记录时间 = 当前记录.时间;
			const 之前记录时间 = 之前记录.时间;
			const 记录用时 = 当前记录.用时; // 单位为天

			// 计算记录的时间范围
			const 记录开始时间 = Math.max(之前记录时间, 现在 - 时间范围);
			const 记录结束时间 = Math.min(记录时间, 现在);
			const 有效时间比例 = (记录结束时间 - 记录开始时间) / (记录时间 - 之前记录时间);

			if (有效时间比例 <= 0) continue;

			const 有效完成数量 = 完成数量 * 有效时间比例;
			const 有效用时 = 记录用时 * 有效时间比例 * 24 * 60 * 60 * 1000; // 转换为毫秒

			if (用时总量 + 有效用时 >= 时间范围) {
				const 剩余时间 = 时间范围 - 用时总量;
				const 比例 = 剩余时间 / 有效用时;
				完成总数 += 有效完成数量 * 比例;
				用时总量 = 时间范围;
				break;
			} else {
				完成总数 += 有效完成数量;
				用时总量 += 有效用时;
			}
		}

		if (用时总量 === 0) return 0;
		return 完成总数 / (用时总量 / (1000 * 60 * 60)); // 转换为每小时速度
	}

	// 计算日用时
	function calculateDailyTime(任务名称: string) {
		const 任务进度记录 = 进度列表.filter(record => record.名称 === 任务名称).sort((a, b) => a.时间 - b.时间);
		if (任务进度记录.length < 2) return 0;

		let 总用时 = 0;
		const 时间范围 = 日用时累积时长 * 24 * 60 * 60 * 1000; // 转换为毫秒
		const 现在 = Date.now();

		for (let i = 任务进度记录.length - 1; i > 0; i--) {
			const 当前记录 = 任务进度记录[i];
			const 之前记录 = 任务进度记录[i - 1];

			if (!当前记录.用时) continue; // 跳过没有用时的记录

			const 记录时间 = 当前记录.时间;
			const 之前记录时间 = 之前记录.时间;
			const 记录用时 = 当前记录.用时; // 单位为天

			// 计算记录的时间范围
			const 记录开始时间 = Math.max(之前记录时间, 现在 - 时间范围);
			const 记录结束时间 = Math.min(记录时间, 现在);
			const 有效时间比例 = (记录结束时间 - 记录开始时间) / (记录时间 - 之前记录时间);

			if (有效时间比例 <= 0) continue;

			const 有效用时 = 记录用时 * 有效时间比例 * 24; // 转换为小时
			总用时 += 有效用时;
		}

		return 总用时 / 日用时累积时长; // 平均日用时，单位为小时
	}

	// 格式化时间
	function formatTime(seconds: number): string {
		if (seconds <= 0) return '0:00';
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		return `${hours}:${minutes.toString().padStart(2, '0')}`;
	}

	// 格式化日期
	function formatDate(date: Date): string {
		const month = date.getMonth() + 1;
		const day = date.getDate();
		const hours = date.getHours();
		return `${month}/${day} ${hours}:`;
	}

	// 计算剩余时间
	function calculateRemainingTime(速度: number, 剩余: number): string {
		if (速度 <= 0) return '----:--';
		const 剩余时间 = 剩余 / 速度;
		return formatTime(剩余时间 * 3600);
	}

	// 计算预计完成时间
	function calculateEstimatedCompletion(速度: number, 日用时: number, 剩余: number): string {
		if (速度 <= 0 || 日用时 <= 0) return '--/-- --:';
		const 剩余时间 = 剩余 / 速度;
		const 预计天数 = 剩余时间 / 日用时;
		const 预计完成日期 = new Date(Date.now() + 预计天数 * 24 * 60 * 60 * 1000);
		return formatDate(预计完成日期);
	}

	// 计算总计
	function calculateTotal() {
		let 总日用时 = 0;
		let 总剩余时间 = 0;
		let 有效任务数 = 0;

		for (const 任务 of 任务列表) {
			const 已完成 = calculateTaskProgress(任务.名称);
			const 剩余 = 任务.总数 - 已完成;
			const 速度 = calculateSpeed(任务.名称);
			const 日用时 = calculateDailyTime(任务.名称);

			if (日用时 > 0) {
				总日用时 += 日用时;
				有效任务数++;
			}

			if (速度 > 0) {
				总剩余时间 += 剩余 / 速度;
			}
		}

		const 平均日用时 = 有效任务数 > 0 ? 总日用时 / 有效任务数 : 0;
		const 预计完成时间 = 平均日用时 > 0 ? calculateEstimatedCompletion(1, 平均日用时, 总剩余时间) : '--/-- --:';

		return {
			总日用时: formatTime(平均日用时 * 3600),
			总剩余时间: formatTime(总剩余时间 * 3600),
			预计完成时间
		};
	}

	// 初始化数据
	fetchData();
</script>

<main>
	<!-- 设置区域 -->
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

	<!-- 错误信息 -->
	{#if error}
		<div class="error">{error}</div>
	{/if}

	<!-- 加载状态 -->
	{#if loading}
		<div class="loading">加载中...</div>
	{:else}
		<!-- 任务表格 -->
		<table class="stats">
			<thead>
				<tr>
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
				<tr style:background-color={任务.颜色 || 'transparent'}>
					<td>{任务.名称}</td>
					<td>{calculateTaskProgress(任务.名称)}</td>
					<td>{任务.总数 - calculateTaskProgress(任务.名称)}</td>
					<td class:highlight={calculateSpeed(任务.名称) <= 0}>
						{calculateSpeed(任务.名称).toFixed(2)}/h
					</td>
					<td class:highlight={calculateDailyTime(任务.名称) <= 0}>
						{formatTime(calculateDailyTime(任务.名称) * 3600)}/d
					</td>
					<td>
						{calculateRemainingTime(calculateSpeed(任务.名称), 任务.总数 - calculateTaskProgress(任务.名称))}
					</td>
					<td>
						{calculateEstimatedCompletion(
							calculateSpeed(任务.名称),
							calculateDailyTime(任务.名称),
							任务.总数 - calculateTaskProgress(任务.名称)
						)}
					</td>
				</tr>
			{/each}
				<!-- 总计行 -->
				<tr class="total-row">
					<td>总计</td>
					<td>--</td>
					<td>--</td>
					<td>--</td>
					<td>{calculateTotal().总日用时}/d</td>
					<td>{calculateTotal().总剩余时间}</td>
					<td>{calculateTotal().预计完成时间}</td>
				</tr>
			</tbody>
		</table>
	{/if}
</main>

<style>
	main {
		max-width: 1200px;
		margin: 0 auto;
		padding: 20px;
		font-family: Arial, sans-serif;
	}

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

	input[type="number"] {
		width: 100px;
		padding: 5px;
		border: 1px solid #ddd;
		border-radius: 4px;
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

	table {
		width: 100%;
		border-collapse: collapse;
		margin-top: 20px;
	}

	th, td {
		padding: 3px;
		text-align: center;
		border: 1px solid #ddd;
	}

	th {
		background-color: #f2f2f2;
		font-weight: bold;
		color: #333;
	}

	.highlight {
        font-weight: bold;
        color: grey;
	}

	.total-row {
		font-weight: bold;
		background-color: #dbdbdb;
	}

    @font-face {
        font-family: 'Fira Mono';
        src: url('./assets/FiraMono-Regular.ttf') format('truetype');
        src: url('./assets/FiraMono-Regular.woff') format('woff');
        src: url('./assets/FiraMono-Regular.woff2') format('woff2');
    }

    .stats {
        font-family: 'Fira Mono', 'Courier New', Courier, monospace;
    }
</style>
