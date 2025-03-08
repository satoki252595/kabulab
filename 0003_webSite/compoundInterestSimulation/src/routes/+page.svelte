<script lang="ts">
	import CompoundChart, { type DataPoint } from '$lib/components/CompoundChart.svelte';

	// フォーム入力用
	let initialInvestment: number = 100000; // 初期投資額
	let monthlyContribution: number = 30000; // 毎月の追加投資額
	let annualInterestRate: number = 5; // 年利(%)
	let years: number = 10; // 投資期間(年)
	let compoundFrequency: '年1回' | '月1回' = '年1回';

	// 結果
	let finalAmount: number = 0; // 最終的な総額
	let totalContributions: number = 0; // 累計拠出金
	let totalInterest: number = 0; // 累計運用益

	// グラフ描画用の配列  (x: 回数, y: 資産額)
	let chartData: DataPoint[] = [];

	/**
	 * 複利計算
	 * 年1回 or 月1回に利回りが付与される想定
	 * 計算結果を chartData, finalAmount, etc. に反映
	 */
	function calculateCompoundInterest() {
		const rate = annualInterestRate / 100;
		let balance = initialInvestment;

		chartData = []; // リセット

		if (compoundFrequency === '月1回') {
			const months = years * 12;
			const monthlyRate = rate / 12;

			// 最初のデータ点 (月0)
			chartData.push({ x: 0, y: balance });

			for (let m = 1; m <= months; m++) {
				balance *= 1 + monthlyRate;
				balance += monthlyContribution;

				chartData.push({ x: m, y: Math.floor(balance) });
			}
		} else {
			// 年1回複利
			chartData.push({ x: 0, y: balance });

			for (let y = 1; y <= years; y++) {
				balance *= 1 + rate;
				balance += monthlyContribution * 12;

				chartData.push({ x: y, y: Math.floor(balance) });
			}
		}

		finalAmount = Math.floor(balance);

		if (compoundFrequency === '月1回') {
			totalContributions = initialInvestment + monthlyContribution * (years * 12);
		} else {
			totalContributions = initialInvestment + monthlyContribution * 12 * years;
		}

		totalInterest = finalAmount - totalContributions;
	}

	// ページが読み込まれたら初期計算
	$: calculateCompoundInterest();
</script>

<div class="mx-auto max-w-4xl p-6">
	<h1 class="mb-4 text-2xl font-bold">複利シミュレーション</h1>

	<!-- 入力フォーム -->
	<div class="mb-6 grid grid-cols-1 gap-4 rounded bg-white p-4 shadow md:grid-cols-2">
		<div class="flex flex-col">
			<label class="mb-1 text-sm font-semibold">初期投資額(円)</label>
			<input
				type="number"
				class="rounded border border-gray-300 p-2"
				bind:value={initialInvestment}
				min="0"
			/>
		</div>

		<div class="flex flex-col">
			<label class="mb-1 text-sm font-semibold">毎月の追加投資額(円)</label>
			<input
				type="number"
				class="rounded border border-gray-300 p-2"
				bind:value={monthlyContribution}
				min="0"
			/>
		</div>

		<div class="flex flex-col">
			<label class="mb-1 text-sm font-semibold">年利(%)</label>
			<input
				type="number"
				step="0.1"
				class="rounded border border-gray-300 p-2"
				bind:value={annualInterestRate}
				min="0"
			/>
		</div>

		<div class="flex flex-col">
			<label class="mb-1 text-sm font-semibold">投資期間(年)</label>
			<input type="number" class="rounded border border-gray-300 p-2" bind:value={years} min="1" />
		</div>

		<div class="flex flex-col">
			<label class="mb-1 text-sm font-semibold">複利のタイミング</label>
			<select class="rounded border border-gray-300 p-2" bind:value={compoundFrequency}>
				<option value="年1回">年1回</option>
				<option value="月1回">月1回</option>
			</select>
		</div>

		<div class="mt-2 flex items-end justify-start">
			<button
				class="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
				on:click={calculateCompoundInterest}
			>
				再計算
			</button>
		</div>
	</div>

	<!-- 結果表示 -->
	<div class="mb-6 rounded bg-white p-4 shadow">
		<h2 class="mb-4 text-xl font-semibold">シミュレーション結果</h2>
		<div class="flex flex-col md:flex-row md:space-x-4">
			<div class="mb-4 flex-1 md:mb-0">
				<p class="mb-1 text-sm">最終的な資産総額:</p>
				<p class="text-lg font-bold">¥{finalAmount.toLocaleString()}</p>
			</div>
			<div class="mb-4 flex-1 md:mb-0">
				<p class="mb-1 text-sm">累計拠出額:</p>
				<p class="text-lg font-bold">¥{totalContributions.toLocaleString()}</p>
			</div>
			<div class="flex-1">
				<p class="mb-1 text-sm">累計運用益:</p>
				<p class="text-lg font-bold">
					<span class={totalInterest >= 0 ? 'text-green-600' : 'text-red-600'}>
						¥{totalInterest.toLocaleString()}
					</span>
				</p>
			</div>
		</div>
	</div>

	<!-- グラフ (D3) -->
	<div class="overflow-x-auto rounded bg-white p-4 shadow">
		<!-- width, height は任意に調整可能 -->
		<CompoundChart data={chartData} width={700} height={300} />
	</div>
</div>
