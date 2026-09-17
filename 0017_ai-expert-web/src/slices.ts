export const PUBLIC_DATA_BASE_DEFAULT = "https://kabulab-cf.satoki252595.workers.dev";
export const STOCKS_JSON_URL =
  "https://raw.githubusercontent.com/satoki252595/kabulab_tool_cloudflare/main/public/vwap-analysis/data/stocks.json";

export function sliceUrls(base = PUBLIC_DATA_BASE_DEFAULT, code = "6098") {
  return {
    orders: `${base}/yuho-quant/api/screening?metric=orders&minYears=3&limit=30`,
    overseas: `${base}/yuho-quant/api/screening-overseas?minYears=3&limit=30`,
    trend: `${base}/yuho-quant/api/trend/${encodeURIComponent(code)}`,
    ir: `${base}/ir-catalog/api/stock/${encodeURIComponent(code)}`,
    yutai: `${base}/otakara-yutai/api/screening?limit=30&sort=total&order=desc`,
    daily: `${base}/vwap-analysis/api/daily?code=${encodeURIComponent(code)}`,
    margin: `${base}/vwap-analysis/api/margin?code=${encodeURIComponent(code)}&n=8`,
    stocks: STOCKS_JSON_URL,
  };
}

export const SCREENING_SLICES = ["地合い", "受注", "海外", "開示の流れ", "制約と既判断", "反証"] as const;
export const TRADE_SLICES = [
  "地合い",
  "開示の流れ",
  "直近開示",
  "価格条件",
  "需給",
  "サイズと破綻",
  "反証",
  "制約と既判断",
  "一次情報",
] as const;
