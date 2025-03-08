<script context="module" lang="ts">
	/**
	 * グラフ描画用のデータ構造
	 * x: 横軸に相当するインデックス(例:経過月数)
	 * y: 資産額など縦軸に表示する数値
	 */
	export interface DataPoint {
		x: number;
		y: number;
	}
</script>

<script lang="ts">
	import { scaleLinear } from 'd3-scale';
	import type { ScaleLinear } from 'd3-scale';
	import { axisBottom, axisLeft } from 'd3-axis';
	import { line, curveLinear } from 'd3-shape';
	import { select, pointer } from 'd3-selection';
	import { bisector } from 'd3-array';
	import { onMount } from 'svelte';
	import { draw } from '$lib/transitions/draw';

	// 受け取るデータと、グラフサイズ
	export let data: DataPoint[] = [];
	export let width = 600;
	export let height = 300;

	// マージン
	const margin = { top: 20, right: 30, bottom: 30, left: 50 };

	let xAxisEl: SVGGElement;
	let yAxisEl: SVGGElement;

	// スケール
	let xScale!: ScaleLinear<number, number>;
	let yScale!: ScaleLinear<number, number>;

	/**
	 * 日本円表記のフォーマット
	 */
	function formatCurrencyJPY(value: number): string {
		if (value < 10_000) {
			return `${value.toLocaleString()}円`;
		} else if (value < 100_000_000) {
			const man = value / 10_000;
			return `${man.toFixed(1)}万円`;
		} else {
			const oku = value / 100_000_000;
			return `${oku.toFixed(2)}億円`;
		}
	}

	/**
	 * 軸とスケールを更新・描画する関数
	 */
	function updateAxesAndScales() {
		if (!xAxisEl || !yAxisEl || data.length === 0) return;

		const w = width - margin.left - margin.right;
		const h = height - margin.top - margin.bottom;

		// Xスケール
		xScale = scaleLinear<number, number>()
			.domain([0, data.length - 1])
			.range([0, w]);

		// Yスケール
		const yMax = Math.max(...data.map((d) => d.y));
		yScale = scaleLinear<number, number>().domain([0, yMax]).range([h, 0]).nice();

		// 軸を作成
		const xAxis = axisBottom<number>(xScale).ticks(Math.max(data.length - 1, 1));
		const yAxis = axisLeft<number>(yScale)
			.ticks(5)
			.tickFormat((value) => formatCurrencyJPY(value));

		// 軸を描画
		select(xAxisEl).call(xAxis);
		select(yAxisEl).call(yAxis);
	}

	// データ or サイズ変更時に自動更新
	$: updateAxesAndScales(), [data, width, height];

	/**
	 * 折れ線 (path要素の d属性) を生成する line generator
	 */
	$: lineGenerator = (() => {
		const w = width - margin.left - margin.right;
		const h = height - margin.top - margin.bottom;

		const yMax = Math.max(...data.map((d) => d.y)) || 0;

		xScale = scaleLinear<number, number>()
			.domain([0, data.length - 1])
			.range([0, w]);

		yScale = scaleLinear<number, number>().domain([0, yMax]).range([h, 0]).nice();

		return line<DataPoint>()
			.x((d) => xScale(d.x))
			.y((d) => yScale(d.y))
			.curve(curveLinear);
	})();

	// ----------------------
	// ツールチップ管理
	// ----------------------
	let tooltip = {
		visible: false,
		x: 0,
		y: 0,
		text: ''
	};

	/**
	 * グラフ領域上でのマウス移動時に呼ばれる関数
	 */
	function handleMouseMove(event: MouseEvent) {
		if (!xScale || !yScale || data.length === 0) return;

		// グラフ内座標 (マージン左上が原点)
		const [mx, my] = pointer(event);

		// xScaleを逆変換して、データ上のx値に相当する数値を求める
		const xVal = xScale.invert(mx);

		// data中で xVal に最も近い要素を見つける
		const bisectX = bisector((d: DataPoint) => d.x).left;
		let index = bisectX(data, xVal);
		// index を配列の範囲内に収める
		index = Math.max(0, Math.min(index, data.length - 1));

		const d = data[index];

		// ツールチップ表示位置（少しオフセットを加えてカーソルに被らないように）
		tooltip = {
			visible: true,
			x: mx + margin.left + 10,
			y: my + margin.top + 10,
			text: `x: ${d.x}, y: ${formatCurrencyJPY(d.y)}`
		};
	}

	function handleMouseLeave() {
		tooltip.visible = false;
	}
</script>

<!-- グラフとツールチップを重ねるため position: relative; を使用 -->
<div style="position: relative; width: {width}px; height: {height}px;">
	<svg {width} {height} style="overflow: visible;">
		<g transform={`translate(${margin.left}, ${margin.top})`}>
			<g bind:this={xAxisEl} transform={`translate(0, ${height - margin.top - margin.bottom})`} />
			<g bind:this={yAxisEl} />

			<path
				fill="none"
				stroke="#1d4ed8"
				stroke-width="2"
				d={lineGenerator(data) ?? ''}
				in:draw={{ duration: 1000 }}
			/>

			{#each data as d, i}
				<circle
					cx={lineGenerator.x()(d, i, data)}
					cy={lineGenerator.y()(d, i, data)}
					r="3"
					fill="#1d4ed8"
				/>
			{/each}

			<!-- マウスイベントを拾うための透明な領域 -->
			<rect
				fill="transparent"
				width={width - margin.left - margin.right}
				height={height - margin.top - margin.bottom}
				on:mousemove={handleMouseMove}
				on:mouseleave={handleMouseLeave}
				role="presentation"
			/>
		</g>
	</svg>

	<!-- ツールチップ (カーソル位置に表示) -->
	{#if tooltip.visible}
		<div
			class="tooltip"
			style="
				left: {tooltip.x}px;
				top: {tooltip.y}px;
			"
		>
			{tooltip.text}
		</div>
	{/if}
</div>

<!-- ツールチップ用の簡易CSS -->
<style>
	.tooltip {
		position: absolute;
		background: #fff;
		border: 1px solid #ccc;
		padding: 4px 8px;
		border-radius: 4px;
		box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2);
		pointer-events: none; /* マウスが重なってもイベントを受けない */
		white-space: nowrap;
		font-size: 0.9rem;
	}
</style>
