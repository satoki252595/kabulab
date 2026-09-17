import { escapeHtml, maskShared } from "./mask";

export function layout(title: string, body: string, user?: { name: string; email: string }): string {
  const nav = user
    ? `<nav>
        <a href="/">ホーム</a>
        <a href="/onboarding">設定</a>
        <a href="/jobs/new">今日の入力</a>
        <a href="/reports">レポート</a>
        <a href="/rules">発効ルール</a>
        <form class="logout" method="post" action="/logout"><button type="submit">ログアウト</button></form>
      </nav>`
    : "";
  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>${escapeHtml(title)} — AI投資エージェント</title>
  <style>
    :root { --ink:#1c1917; --paper:#f7f3eb; --line:#d6cfc3; --accent:#1f4d3a; --muted:#6b6458; }
    * { box-sizing: border-box; }
    body { margin:0; font: 16px/1.55 "Hiragino Mincho ProN", "Yu Mincho", serif; background: var(--paper); color: var(--ink); }
    header, main, footer { max-width: 840px; margin: 0 auto; padding: 1rem 1.25rem; }
    header { display:flex; justify-content:space-between; align-items:baseline; border-bottom: 1px solid var(--line); }
    header h1 { font-size: 1.05rem; font-weight: 600; letter-spacing: .04em; }
    nav { display:flex; gap:.9rem; flex-wrap:wrap; font-size:.92rem; }
    a { color: var(--accent); }
    .muted { color: var(--muted); font-size:.9rem; }
    .card { background:#fffdf8; border:1px solid var(--line); padding:1rem 1.1rem; margin: 1rem 0; }
    label { display:block; margin:.7rem 0 .25rem; font-size:.92rem; }
    input, select, textarea { width:100%; padding:.45rem .5rem; font: inherit; border:1px solid var(--line); background:#fff; }
    button, .btn { display:inline-block; background: var(--accent); color:#f7f3eb; border:0; padding:.5rem .9rem; cursor:pointer; font: inherit; text-decoration:none; }
    .logout { display:inline; } .logout button { background:transparent; color:var(--accent); padding:0; }
    table { width:100%; border-collapse: collapse; font-size:.95rem; }
    th, td { text-align:left; border-bottom:1px solid var(--line); padding:.4rem .3rem; vertical-align:top; }
    pre { white-space: pre-wrap; font-family: ui-monospace, monospace; font-size:.9rem; }
    .warn { color:#7f1d1d; }
    footer { border-top:1px solid var(--line); font-size:.85rem; color: var(--muted); }
  </style>
</head>
<body>
  <header>
    <h1>AI投資エージェント</h1>
    ${nav}
  </header>
  <main>${body}</main>
  <footer>投資助言ではありません。最終判断は人だけ。発注機能はありません。円の数値は本人画面のみ。</footer>
</body>
</html>`;
}

export function loginPage(googleReady: boolean, err?: string): string {
  const errHtml = err ? `<p class="warn">${escapeHtml(err)}</p>` : "";
  const btn = googleReady
    ? `<p><a class="btn" href="/auth/google">Google でログイン</a></p>`
    : `<p class="warn">GOOGLE_CLIENT_ID が未設定です。README のデプロイ手順を見てください。</p>`;
  return layout(
    "ログイン",
    `${errHtml}
    <div class="card">
      <h2>ログイン</h2>
      <p>会員向けです。匿名の閲覧はありません。ログイン後、他人の発効ルールとレポート（円なし）を読めます。円帯は本人だけです。</p>
      ${btn}
    </div>`,
  );
}

export function cardForm(title: string, inner: string): string {
  return `<div class="card"><h2>${escapeHtml(title)}</h2>${inner}</div>`;
}

export function maskedPre(text: string): string {
  return `<pre>${escapeHtml(maskShared(text))}</pre>`;
}
