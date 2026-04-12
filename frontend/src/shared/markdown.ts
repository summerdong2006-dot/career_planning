function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderInlineMarkdown(value: string): string {
  return escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

export function renderMarkdownToHtml(markdown: string, emptyHtml?: string): string {
  const normalized = markdown.replace(/\r\n/g, "\n").trim();
  if (!normalized) {
    return emptyHtml ?? '<p class="preview-empty">No content.</p>';
  }

  const lines = normalized.split("\n");
  const htmlParts: string[] = [];
  let unorderedItems: string[] = [];
  let orderedItems: string[] = [];

  const flushLists = () => {
    if (unorderedItems.length > 0) {
      htmlParts.push(`<ul>${unorderedItems.join("")}</ul>`);
      unorderedItems = [];
    }
    if (orderedItems.length > 0) {
      htmlParts.push(`<ol>${orderedItems.join("")}</ol>`);
      orderedItems = [];
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushLists();
      continue;
    }

    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      flushLists();
      const level = headingMatch[1].length;
      htmlParts.push(`<h${level}>${renderInlineMarkdown(headingMatch[2])}</h${level}>`);
      continue;
    }

    const orderedMatch = line.match(/^\d+\.\s+(.+)$/);
    if (orderedMatch) {
      unorderedItems = [];
      orderedItems.push(`<li>${renderInlineMarkdown(orderedMatch[1])}</li>`);
      continue;
    }

    const bulletMatch = line.match(/^[-*]\s+(.+)$/);
    if (bulletMatch) {
      orderedItems = [];
      unorderedItems.push(`<li>${renderInlineMarkdown(bulletMatch[1])}</li>`);
      continue;
    }

    flushLists();
    htmlParts.push(`<p>${renderInlineMarkdown(line)}</p>`);
  }

  flushLists();
  return htmlParts.join("");
}
