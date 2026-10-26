function inlineNodes(text, keyPrefix) {
  const nodes = [];
  const pattern = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[[^\]]+\]\(https?:\/\/[^)\s]+\))/g;
  let last = 0;
  let index = 0;
  for (const match of text.matchAll(pattern)) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const token = match[0];
    const key = `${keyPrefix}-${index}`;
    index += 1;
    if (token.startsWith("`")) {
      nodes.push(
        <code key={key} className="rounded bg-ink px-1 py-0.5 font-mono text-[12px] text-hint">
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith("**")) {
      nodes.push(
        <strong key={key} className="font-semibold text-paper">
          {token.slice(2, -2)}
        </strong>,
      );
    } else {
      const label = token.slice(1, token.indexOf("]"));
      const href = token.slice(token.indexOf("(") + 1, -1);
      nodes.push(
        <a key={key} href={href} className="text-hint underline decoration-hint/40 underline-offset-2" target="_blank" rel="noreferrer">
          {label}
        </a>,
      );
    }
    last = match.index + token.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function parseBlocks(source) {
  const lines = String(source || "").replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }
    if (line.startsWith("```")) {
      const body = [];
      index += 1;
      while (index < lines.length && !lines[index].startsWith("```")) {
        body.push(lines[index]);
        index += 1;
      }
      index += 1;
      blocks.push({ type: "code", text: body.join("\n") });
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      blocks.push({ type: "h", level: heading[1].length, text: heading[2] });
      index += 1;
      continue;
    }
    if (/^(\s*[-*]\s+|\s*\d+\.\s+)/.test(line)) {
      const items = [];
      const ordered = /^\s*\d+\.\s+/.test(line);
      while (index < lines.length && /^(\s*[-*]\s+|\s*\d+\.\s+)/.test(lines[index])) {
        items.push(lines[index].replace(/^\s*(?:[-*]|\d+\.)\s+/, ""));
        index += 1;
      }
      blocks.push({ type: ordered ? "ol" : "ul", items });
      continue;
    }
    const para = [line];
    index += 1;
    while (index < lines.length && lines[index].trim() && !lines[index].startsWith("```") && !/^(#{1,3})\s+/.test(lines[index]) && !/^(\s*[-*]\s+|\s*\d+\.\s+)/.test(lines[index])) {
      para.push(lines[index]);
      index += 1;
    }
    blocks.push({ type: "p", text: para.join(" ") });
  }
  return blocks;
}

export function MarkdownView({ text }) {
  const blocks = parseBlocks(text);
  if (!blocks.length) return <p className="text-sm text-faint">Nothing to preview.</p>;
  return (
    <div className="space-y-3 text-sm leading-relaxed text-mute">
      {blocks.map((block, index) => {
        if (block.type === "h") {
          const Tag = block.level === 1 ? "h2" : "h3";
          return (
            <Tag key={index} className="font-semibold text-paper">
              {inlineNodes(block.text, `h${index}`)}
            </Tag>
          );
        }
        if (block.type === "code") {
          return (
            <pre key={index} className="overflow-x-auto rounded-lg border border-line bg-ink p-3 font-mono text-[12px] leading-relaxed text-paper">
              {block.text}
            </pre>
          );
        }
        if (block.type === "ul" || block.type === "ol") {
          const Tag = block.type === "ol" ? "ol" : "ul";
          return (
            <Tag key={index} className={`space-y-1 pl-5 ${block.type === "ol" ? "list-decimal" : "list-disc"}`}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{inlineNodes(item, `li${index}-${itemIndex}`)}</li>
              ))}
            </Tag>
          );
        }
        return <p key={index}>{inlineNodes(block.text, `p${index}`)}</p>;
      })}
    </div>
  );
}
