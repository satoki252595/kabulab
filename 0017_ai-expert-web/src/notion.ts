/** 5DB の「状態」は Notion status 型ではなく select。判断ID は title。 */

export function selectEquals(property: string, name: string) {
  return { property, select: { equals: name } };
}

export function selectIsEmpty(property: string) {
  return { property, select: { is_empty: true } };
}

export function setSelect(name: string) {
  return { select: { name } };
}

export function setTitle(text: string) {
  return { title: [{ type: "text" as const, text: { content: text.slice(0, 2000) } }] };
}

export function setRichText(text: string) {
  return { rich_text: [{ type: "text" as const, text: { content: text.slice(0, 2000) } }] };
}

export function setCheckbox(checked: boolean) {
  return { checkbox: checked };
}

export function setDate(isoDate: string) {
  return { date: { start: isoDate } };
}

export function setRelation(pageId: string) {
  return { relation: [{ id: pageId }] };
}

export function titlePlain(prop: unknown): string {
  const p = prop as { title?: { plain_text?: string }[] } | undefined;
  return (p?.title ?? []).map((t) => t.plain_text ?? "").join("");
}

export function richPlain(prop: unknown): string {
  const p = prop as { rich_text?: { plain_text?: string }[] } | undefined;
  return (p?.rich_text ?? []).map((t) => t.plain_text ?? "").join("");
}

export function selectName(prop: unknown): string {
  const p = prop as { select?: { name?: string } | null } | undefined;
  return p?.select?.name ?? "";
}

export function checkboxVal(prop: unknown): boolean {
  const p = prop as { checkbox?: boolean } | undefined;
  return Boolean(p?.checkbox);
}

export function dateStart(prop: unknown): string {
  const p = prop as { date?: { start?: string } | null } | undefined;
  return p?.date?.start ?? "";
}

export function relationIds(prop: unknown): string[] {
  const p = prop as { relation?: { id: string }[] } | undefined;
  return (p?.relation ?? []).map((r) => r.id);
}

export type NotionPage = {
  id: string;
  url?: string;
  properties: Record<string, unknown>;
};

const API = "https://api.notion.com/v1";
const VERSION = "2022-06-28";

export class NotionClient {
  constructor(
    private token: string,
    readonly ids: {
      agent: string;
      rule: string;
      job: string;
      decision: string;
      review: string;
    },
  ) {}

  configured(): boolean {
    return Boolean(this.token) && Object.values(this.ids).every(Boolean);
  }

  private async req(path: string, init: RequestInit = {}): Promise<Response> {
    return fetch(`${API}${path}`, {
      ...init,
      headers: {
        authorization: `Bearer ${this.token}`,
        "notion-version": VERSION,
        "content-type": "application/json",
        ...(init.headers ?? {}),
      },
    });
  }

  async query(
    databaseId: string,
    body: Record<string, unknown>,
  ): Promise<{ results: NotionPage[]; error?: string }> {
    const res = await this.req(`/databases/${databaseId}/query`, {
      method: "POST",
      body: JSON.stringify({ page_size: 20, ...body }),
    });
    const json = (await res.json()) as { results?: NotionPage[]; message?: string };
    if (!res.ok) return { results: [], error: json.message ?? `http_${res.status}` };
    return { results: json.results ?? [] };
  }

  async getPage(pageId: string): Promise<NotionPage | null> {
    const res = await this.req(`/pages/${pageId}`);
    if (!res.ok) return null;
    return (await res.json()) as NotionPage;
  }

  async pagePlainText(pageId: string, maxBlocks = 40): Promise<string> {
    const res = await this.req(`/blocks/${pageId}/children?page_size=${maxBlocks}`);
    if (!res.ok) return "";
    const json = (await res.json()) as {
      results?: { type: string; [k: string]: unknown }[];
    };
    const lines: string[] = [];
    for (const b of json.results ?? []) {
      const rich = (b[b.type] as { rich_text?: { plain_text?: string }[] } | undefined)?.rich_text;
      if (rich?.length) lines.push(rich.map((t) => t.plain_text ?? "").join(""));
    }
    return lines.join("\n");
  }

  async createPage(databaseId: string, properties: Record<string, unknown>): Promise<{ id: string } | { error: string }> {
    const res = await this.req("/pages", {
      method: "POST",
      body: JSON.stringify({ parent: { database_id: databaseId }, properties }),
    });
    const json = (await res.json()) as { id?: string; message?: string };
    if (!res.ok || !json.id) return { error: json.message ?? `http_${res.status}` };
    return { id: json.id };
  }

  async updatePage(pageId: string, properties: Record<string, unknown>): Promise<{ ok: true } | { error: string }> {
    const res = await this.req(`/pages/${pageId}`, {
      method: "PATCH",
      body: JSON.stringify({ properties }),
    });
    if (!res.ok) {
      const json = (await res.json()) as { message?: string };
      return { error: json.message ?? `http_${res.status}` };
    }
    return { ok: true };
  }
}

export function jstToday(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}
