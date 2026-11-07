import type { ReactNode } from 'react';

function inline(text: string, keyBase: string): ReactNode[] {
  // **bold** and `code`; everything else is plain text (never HTML).
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let i = 0;
  for (const m of text.matchAll(re)) {
    const idx = m.index ?? 0;
    if (idx > last) parts.push(text.slice(last, idx));
    const token = m[0];
    if (token.startsWith('**')) parts.push(<b key={`${keyBase}-${i++}`}>{token.slice(2, -2)}</b>);
    else parts.push(<code key={`${keyBase}-${i++}`}>{token.slice(1, -1)}</code>);
    last = idx + token.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

/** The subset of markdown the memo uses: ### headings, bullets, bold, code spans, paragraphs. */
export default function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  const lines = text.split(/\r?\n/);
  let list: string[] = [];
  let para: string[] = [];
  const flushList = () => {
    if (list.length) {
      blocks.push(<ul key={`ul-${blocks.length}`}>{list.map((item, i) => <li key={i}>{inline(item, `li-${blocks.length}-${i}`)}</li>)}</ul>);
      list = [];
    }
  };
  const flushPara = () => {
    if (para.length) {
      blocks.push(<p key={`p-${blocks.length}`}>{inline(para.join(' '), `p-${blocks.length}`)}</p>);
      para = [];
    }
  };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flushList();
      flushPara();
      continue;
    }
    const heading = line.match(/^#{1,6}\s+(.*)$/);
    if (heading) {
      flushList();
      flushPara();
      blocks.push(<h3 key={`h-${blocks.length}`}>{inline(heading[1], `h-${blocks.length}`)}</h3>);
      continue;
    }
    const bullet = line.match(/^[-*]\s+(.*)$/);
    if (bullet) {
      flushPara();
      list.push(bullet[1]);
      continue;
    }
    flushList();
    para.push(line);
  }
  flushList();
  flushPara();
  return <div className="rf-memo">{blocks}</div>;
}
