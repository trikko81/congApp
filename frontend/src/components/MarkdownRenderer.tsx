"use client";

import React, { useMemo } from "react";
import { FileText, ExternalLink } from "lucide-react";

export interface MarkdownCitationClickPayload {
  docTitle: string;
  page: number;
  paragraph?: number;
  snippet?: string;
}

interface MarkdownRendererProps {
  content: string;
  className?: string;
  onCitationClick?: (citation: MarkdownCitationClickPayload) => void;
}

export default function MarkdownRenderer({
  content,
  className = "",
  onCitationClick,
}: MarkdownRendererProps) {
  const renderedElements = useMemo(() => {
    if (!content) return null;

    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeBlockLines: string[] = [];
    let currentList: { type: "ul" | "ol"; items: string[] } | null = null;
    let currentBlockquote: string[] = [];

    const flushList = () => {
      if (currentList) {
        const ListTag = currentList.type;
        elements.push(
          <ListTag key={`list-${elements.length}`} className={`markdown-${currentList.type}`}>
            {currentList.items.map((item, idx) => (
              <li key={idx}>{renderInlineMarkdown(item, onCitationClick)}</li>
            ))}
          </ListTag>
        );
        currentList = null;
      }
    };

    const flushBlockquote = () => {
      if (currentBlockquote.length > 0) {
        elements.push(
          <blockquote key={`quote-${elements.length}`} className="markdown-blockquote">
            {currentBlockquote.map((qLine, idx) => (
              <p key={idx}>{renderInlineMarkdown(qLine, onCitationClick)}</p>
            ))}
          </blockquote>
        );
        currentBlockquote = [];
      }
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Code Block Boundary
      if (line.trim().startsWith("```")) {
        if (inCodeBlock) {
          elements.push(
            <pre key={`code-${elements.length}`} className="markdown-code-block">
              <code>{codeBlockLines.join("\n")}</code>
            </pre>
          );
          inCodeBlock = false;
          codeBlockLines = [];
        } else {
          flushList();
          flushBlockquote();
          inCodeBlock = true;
          codeBlockLines = [];
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockLines.push(line);
        continue;
      }

      // Horizontal Rule
      if (/^(\*{3,}|-{3,}|_{3,})$/.test(line.trim())) {
        flushList();
        flushBlockquote();
        elements.push(<hr key={`hr-${elements.length}`} className="markdown-hr" />);
        continue;
      }

      // Blockquotes
      if (line.trim().startsWith(">")) {
        flushList();
        const quoteText = line.trim().replace(/^>\s?/, "");
        currentBlockquote.push(quoteText);
        continue;
      } else {
        flushBlockquote();
      }

      // Headings
      const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
      if (headingMatch) {
        flushList();
        const level = Math.min(Math.max(headingMatch[1].length, 1), 6);
        const headingText = headingMatch[2];
        const HeadingTag = `h${level}` as "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
        elements.push(
          <HeadingTag key={`h-${elements.length}`} className={`markdown-heading markdown-h${level}`}>
            {renderInlineMarkdown(headingText, onCitationClick)}
          </HeadingTag>
        );
        continue;
      }

      // Unordered Lists: - item, * item, • item
      const ulMatch = line.match(/^(\s*)(?:[-*•])\s+(.*)$/);
      if (ulMatch) {
        if (!currentList || currentList.type !== "ul") {
          flushList();
          currentList = { type: "ul", items: [] };
        }
        currentList.items.push(ulMatch[2]);
        continue;
      }

      // Ordered Lists: 1. item
      const olMatch = line.match(/^(\s*)\d+\.\s+(.*)$/);
      if (olMatch) {
        if (!currentList || currentList.type !== "ol") {
          flushList();
          currentList = { type: "ol", items: [] };
        }
        currentList.items.push(olMatch[2]);
        continue;
      }

      // Empty Lines
      if (!line.trim()) {
        flushList();
        continue;
      }

      // Normal Paragraph
      flushList();
      elements.push(
        <p key={`p-${elements.length}`} className="markdown-p">
          {renderInlineMarkdown(line, onCitationClick)}
        </p>
      );
    }

    flushList();
    flushBlockquote();

    if (inCodeBlock && codeBlockLines.length > 0) {
      elements.push(
        <pre key={`code-${elements.length}`} className="markdown-code-block">
          <code>{codeBlockLines.join("\n")}</code>
        </pre>
      );
    }

    return elements;
  }, [content, onCitationClick]);

  return <div className={`markdown-content ${className}`}>{renderedElements}</div>;
}

/**
 * Parses inline tokens: code, bold, italics, markdown links, and citations.
 */
function renderInlineMarkdown(
  text: string,
  onCitationClick?: (citation: MarkdownCitationClickPayload) => void
): React.ReactNode[] {
  if (!text) return [];

  // Regex matches:
  // 1. Markdown link: [Label](url)
  // 2. Citation bracket: [DocTitle, p. X, par. Y] or [DocTitle, p. X] or [p. X]
  // 3. Inline code: `code`
  // 4. Bold: **bold** or __bold__
  // 5. Italic: *italic* or _italic_
  const tokenRegex = /(https?:\/\/[^\s]+|\[[^\]]+\]\([^)]+\)|\[(?:[^\]]+,\s*p\.\s*\d+[^\]]*|p\.\s*\d+[^\]]*)\]|`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_)/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, index) => {
    if (!part) return null;

    // Markdown Link: [text](url)
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      const linkText = linkMatch[1];
      const linkUrl = linkMatch[2];

      // If link points to PDF or has page reference
      const isPdfLink = linkUrl.toLowerCase().includes(".pdf") || linkUrl.includes("/api/documents/");
      const pageMatch = linkUrl.match(/(?:#|\?|&)page=(\d+)/i) || linkText.match(/(?:p\.|page)\s*(\d+)/i);
      const targetPage = pageMatch ? parseInt(pageMatch[1], 10) : 1;

      if (isPdfLink && onCitationClick) {
        const rawDoc = linkUrl.split("/").pop()?.split("#")[0]?.split("?")[0] || linkText;
        const cleanDoc = rawDoc.endsWith(".pdf") ? rawDoc : `${rawDoc}.pdf`;

        return (
          <button
            type="button"
            key={index}
            onClick={() =>
              onCitationClick({
                docTitle: cleanDoc,
                page: targetPage,
                snippet: linkText,
              })
            }
            className="markdown-citation-interactive"
            title={`View ${cleanDoc} (Page ${targetPage})`}
          >
            <FileText size={11} className="inline mr-1 text-primary" />
            <span>{linkText}</span>
            <ExternalLink size={10} className="inline ml-1 opacity-70" />
          </button>
        );
      }

      return (
        <a
          key={index}
          href={linkUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="markdown-link"
        >
          {linkText}
        </a>
      );
    }

    // Inline Code
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      return (
        <code key={index} className="markdown-inline-code">
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold (**text** or __text__)
    if (
      (part.startsWith("**") && part.endsWith("**") && part.length >= 4) ||
      (part.startsWith("__") && part.endsWith("__") && part.length >= 4)
    ) {
      return (
        <strong key={index} className="markdown-bold">
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Italic (*text* or _text_)
    if (
      (part.startsWith("*") && part.endsWith("*") && part.length >= 2) ||
      (part.startsWith("_") && part.endsWith("_") && part.length >= 2)
    ) {
      return (
        <em key={index} className="markdown-italic">
          {part.slice(1, -1)}
        </em>
      );
    }

    // Citation Match Tag e.g. [DocTitle, p. 1, par. 2] or [Virginia_HB_2095_2021.pdf, p. 1, par. 1]
    if (part.startsWith("[") && part.endsWith("]") && /p\.\s*\d+/i.test(part)) {
      const inner = part.slice(1, -1).trim();

      // Extract page number
      const pageMatch = inner.match(/p\.\s*(\d+)/i);
      const page = pageMatch ? parseInt(pageMatch[1], 10) : 1;

      // Extract paragraph if present
      const parMatch = inner.match(/par\.\s*(\d+)/i);
      const paragraph = parMatch ? parseInt(parMatch[1], 10) : undefined;

      // Extract doc title (everything before ", p.")
      let docTitle = "";
      const docMatch = inner.split(/,\s*p\./i);
      if (docMatch && docMatch.length > 1) {
        docTitle = docMatch[0].trim();
      }

      if (onCitationClick) {
        return (
          <button
            type="button"
            key={index}
            onClick={() =>
              onCitationClick({
                docTitle,
                page,
                paragraph,
                snippet: inner,
              })
            }
            className="markdown-citation-interactive"
            title={`Click to open ${docTitle || "document"} at Page ${page}`}
          >
            <FileText size={11} className="inline mr-1 text-primary shrink-0" />
            <span>{inner}</span>
            <ExternalLink size={10} className="inline ml-1 opacity-70 shrink-0" />
          </button>
        );
      }

      return (
        <span key={index} className="markdown-citation-tag">
          {part}
        </span>
      );
    }

    return part;
  });
}
