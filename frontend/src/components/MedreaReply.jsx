import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const HEADING_EMOJI = [
  [/clinical summary|interpretation/i, "🧠"],
  [/doctor|clinician|clinical information/i, "🩺"],
  [/lab(?:oratory)?|blood result|blood count/i, "🧪"],
  [/medication|medicine|drug/i, "💊"],
  [/record/i, "📋"],
  [/finding/i, "🔍"],
  [/caution|warning|follow[- ]?up/i, "⚠️"],
  [/concern|urgent|significant/i, "🚨"],
  [/reassur|confirmed/i, "✅"],
  [/what this means|explanation/i, "💡"],
  [/key point|important context|context/i, "📌"],
  [/timeline|date/i, "📅"],
  [/patient/i, "👤"],
  [/how hetu|flag|access|role/i, "💡"],
];

const HAS_EMOJI = /^\p{Extended_Pictographic}/u;

function childText(node) {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(childText).join("");
  if (node.props?.children != null) return childText(node.props.children);
  return "";
}

function withSectionEmoji(children) {
  const text = childText(children).trim();
  if (!text) return children;
  if (HAS_EMOJI.test(text)) return children;
  for (const [pattern, emoji] of HEADING_EMOJI) {
    if (pattern.test(text)) {
      return `${emoji} ${text}`;
    }
  }
  return children;
}

const markdownComponents = {
  h1: ({ children }) => (
    <h1 className="medrea-h1">{withSectionEmoji(children)}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="medrea-h2">{withSectionEmoji(children)}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="medrea-h3">{withSectionEmoji(children)}</h3>
  ),
  p: ({ children }) => <p className="medrea-p">{children}</p>,
  ul: ({ children }) => <ul className="medrea-ul">{children}</ul>,
  ol: ({ children }) => <ol className="medrea-ol">{children}</ol>,
  li: ({ children }) => <li className="medrea-li">{children}</li>,
  strong: ({ children }) => <strong className="medrea-strong">{children}</strong>,
  em: ({ children }) => <em className="medrea-em">{children}</em>,
  a: ({ href, children }) => (
    <a className="medrea-a" href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
  code: ({ className, children }) =>
    className ? (
      <code className={`medrea-code ${className}`}>{children}</code>
    ) : (
      <code className="medrea-code-inline">{children}</code>
    ),
  pre: ({ children }) => <pre className="medrea-pre">{children}</pre>,
  hr: () => <hr className="medrea-hr" />,
  blockquote: ({ children }) => <blockquote className="medrea-quote">{children}</blockquote>,
};

export default function MedreaReply({ text }) {
  const source = (text || "").trim();
  if (!source) return null;
  return (
    <div className="medrea-reply">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {source}
      </ReactMarkdown>
    </div>
  );
}
