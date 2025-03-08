import type { TransitionConfig } from 'svelte/transition';

export function draw(
  node: SVGPathElement,
  { duration = 1000 }: { duration?: number }
): TransitionConfig {
  // 線の全長を取得
  const length = node.getTotalLength();

  return {
    duration,
    css: (t: number) => `
      stroke-dasharray: ${length};
      stroke-dashoffset: ${(1 - t) * length};
    `
  };
}