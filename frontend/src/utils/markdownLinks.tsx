import type { ReactNode } from 'react';

const linkClassName = 'text-indigo-400 hover:text-indigo-200 underline underline-offset-1 font-medium';

/** Trim trailing punctuation/brackets that's not part of the URL (e.g. "https://x.com/foo." -> "https://x.com/foo"). */
function trimUrlTrailingPunctuation(url: string): string {
  return url.replace(/[.,;:)!?'"<>]+$/, '');
}

/** Only allow http/https hrefs to prevent XSS (e.g. javascript:, data:). */
function isSafeHref(href: string): boolean {
  const h = href.trim().toLowerCase();
  return h.startsWith('https://') || h.startsWith('http://');
}

/** Normalize markdown links: collapse any whitespace (including newlines) between ] and ( so links parse correctly. */
export function normalizeMarkdownLinks(text: string): string {
  return text.replace(/\]\s*\(/g, '](');
}

/** Parse [text](url) markdown links and bare https?:// URLs; return React nodes (text and <a>). */
export function parseMarkdownLinks(text: string): ReactNode[] {
  const normalized = normalizeMarkdownLinks(text);
  const out: ReactNode[] = [];
  // Match [label](url) — allow optional whitespace between ] and (; or bare URL
  const re = /\[([^\]]+)\]\s*\((https?:\/\/[^)]+)\)|(https?:\/\/\S+)/g;
  let lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(normalized)) !== null) {
    if (m.index > lastIndex) {
      out.push(normalized.slice(lastIndex, m.index));
    }
    const isMarkdown = !!m[1];
    const rawHref = isMarkdown ? m[2]! : trimUrlTrailingPunctuation(m[3]!);
    const label = isMarkdown ? m[1] : rawHref;
    if (!isSafeHref(rawHref)) {
      out.push(normalized.slice(m.index, re.lastIndex));
      lastIndex = re.lastIndex;
      continue;
    }
    out.push(
      <a
        key={`${m.index}-${String(label).slice(0, 40)}`}
        href={rawHref}
        target="_blank"
        rel="noopener noreferrer"
        className={linkClassName}
        onClick={(e) => e.stopPropagation()}
      >
        {label}
      </a>
    );
    lastIndex = re.lastIndex;
  }
  if (lastIndex < normalized.length) {
    out.push(normalized.slice(lastIndex));
  }
  return out.length > 0 ? out : [normalized];
}

/** Render parsed nodes, turning newlines in text segments into <br /> so line breaks display correctly. */
export function renderWithLineBreaks(nodes: ReactNode[]): ReactNode[] {
  const result: ReactNode[] = [];
  let key = 0;
  for (const node of nodes) {
    if (typeof node === 'string' && node.includes('\n')) {
      const parts = node.split('\n');
      for (let i = 0; i < parts.length; i++) {
        if (i > 0) result.push(<br key={`br-${key++}`} />);
        result.push(parts[i]);
      }
    } else {
      result.push(node);
    }
  }
  return result;
}
