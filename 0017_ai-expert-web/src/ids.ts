export const NOTION_PARENT_PAGE_ID = "3ddd74ff-84cd-8178-9abb-cf86708626c0";
export const NOTION_PARENT_PAGE_NAME = "AI投資エージェント";

/** Live 2026-09-16. database_id = DB page. data_source_id without collection:// */
export const NOTION_IDS = {
  agent: {
    database_id: "0bbeee51-024a-4930-937e-e27390c12572",
    data_source_id: "f716eb85-55d8-4989-8693-575ed3a77387",
  },
  rule: {
    database_id: "ebe48548-1475-4139-9fed-d9becc1aefe2",
    data_source_id: "517560c4-ff55-4524-a8f9-374e6d534d7c",
  },
  job: {
    database_id: "dd841447-06d0-4385-811e-ee52abf3185e",
    data_source_id: "c8e1c2a2-18e2-4fcc-b853-927ee8975ec9",
  },
  decision: {
    database_id: "64bbb3ed-1a36-4d0b-8d4f-25f44ea219da",
    data_source_id: "22d332de-be5e-4193-9280-c509262c7629",
  },
  review: {
    database_id: "f6553c22-36d6-40de-a0c1-a38adc178790",
    data_source_id: "cc35ddd1-7c2d-4678-9476-9cb1a6ae9a36",
  },
} as const;

export const JOB_VIEWS = {
  waiting: "https://app.notion.com/p/dd84144706d04385811eee52abf3185e?v=3ddd74ff84cd81b08dc5000cfecbf101",
  resume: "https://app.notion.com/p/dd84144706d04385811eee52abf3185e?v=3ddd74ff84cd810d8762000cd0892b29",
  today: "https://app.notion.com/p/dd84144706d04385811eee52abf3185e?v=3ddd74ff84cd8126ae31000c95dfd617",
} as const;
