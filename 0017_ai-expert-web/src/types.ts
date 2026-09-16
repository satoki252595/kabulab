export type Env = {
  DB: D1Database;
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
  SESSION_SECRET?: string;
  NOTION_TOKEN?: string;
  YEN_STORE_SECRET?: string;
  PUBLIC_DATA_BASE: string;
  NOTION_PARENT_PAGE_NAME: string;
  NOTION_PARENT_PAGE_ID?: string;
  NOTION_AGENT_DB_ID: string;
  NOTION_AGENT_DS_ID?: string;
  NOTION_RULE_DB_ID: string;
  NOTION_RULE_DS_ID?: string;
  NOTION_JOB_DB_ID: string;
  NOTION_JOB_DS_ID?: string;
  NOTION_DECISION_DB_ID: string;
  NOTION_DECISION_DS_ID?: string;
  NOTION_REVIEW_DB_ID: string;
  NOTION_REVIEW_DS_ID?: string;
  APP_ORIGIN?: string;
};

export type SessionUser = {
  userId: string;
  email: string;
  name: string;
};

export type YenRow = {
  notion_decision_id: string;
  user_id: string;
  code: string;
  side: string | null;
  as_of: string | null;
  entry_yen: number | null;
  stop_yen: number | null;
  take_yen: number | null;
  size_yen: number | null;
  result_pct: number | null;
  vs_close_pct: number | null;
  vs_topix_pct: number | null;
  source: string | null;
};

export type YenWrite = {
  notion_decision_id: string;
  user_id: string;
  code: string;
  side?: string;
  as_of?: string;
  entry_yen?: number | null;
  stop_yen?: number | null;
  take_yen?: number | null;
  size_yen?: number | null;
  result_pct?: number | null;
  vs_close_pct?: number | null;
  vs_topix_pct?: number | null;
  source?: string;
};
