const FORBIDDEN = [
  "買い推奨",
  "売り推奨",
  "おすすめ",
  "目標株価",
  "明日上がる",
  "今すぐ",
  "必ず",
  "絶対",
  "爆益",
  "急騰確実",
];

/** Mask yen amounts so shared HTML never shows private prices. */
export function maskYen(text: string): string {
  if (!text) return text;
  return text
    .replace(/(?:¥|￥)\s*\d{1,3}(?:,\d{3})+(?:\.\d+)?/g, "［円は本人画面］")
    .replace(/(?:¥|￥)\s*\d+(?:\.\d+)?/g, "［円は本人画面］")
    .replace(/\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*円/g, "［円は本人画面］")
    .replace(/\d+(?:\.\d+)?\s*円/g, "［円は本人画面］");
}

export function findForbidden(text: string): string[] {
  if (!text) return [];
  return FORBIDDEN.filter((w) => text.includes(w));
}

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function maskShared(text: string): string {
  return maskYen(text);
}

const CODE_RE = /^\d{4}$/;

export function parseWatchCodes(raw: string, max = 30): string[] {
  const codes = raw
    .split(/[,、\s]+/)
    .map((c) => c.replace(/\.T$/i, "").trim())
    .filter((c) => CODE_RE.test(c));
  return [...new Set(codes)].slice(0, max);
}

export function isJpStockCode(code: string): boolean {
  return CODE_RE.test(code);
}
