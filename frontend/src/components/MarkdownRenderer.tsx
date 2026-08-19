"use client";

import React, { useMemo } from "react";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export default function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  const renderedElements = useMemo(() => {
    if (!content) return null;

    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeBlockLang = "";
    let codeBlockLines: string[] = [];
    let currentList: { type: "ul" | "ol"; items: string[] } | null = null;
    let currentBlockquote: string[] = [];

    const flushList = () => {
      if (currentList) {
        const ListTag = currentList.type;
        elements.push(
          <ListTag key={`list-${elements.length}`} className={`markdown-${currentList.type}`}>
            {currentList.items.map((item, idx) => (
              <li key={idx}>{renderInlineMarkdown(item)}</li>
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
              <p key={idx}>{renderInlineMarkdown(qLine)}</p>
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
          codeBlockLang = "";
        } else {
          flushList();
          flushBlockquote();
          inCodeBlock = true;
          codeBlockLang = line.trim().slice(3).trim();
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
        const level = headingMatch[1].length;
        const headingText = headingMatch[2];
        const HeadingTag = `h${level}` as keyof JSX.IntrinsicElements;
        elements.push(
          <HeadingTag key={`h-${elements.length}`} className={`markdown-heading markdown-h${level}`}>
            {renderInlineMarkdown(headingText)}
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
          {renderInlineMarkdown(line)}
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
  }, [content]);

  return <div className={`markdown-content ${className}`}>{renderedElements}</div>;
}

/**
 * Parses bold (**text**), italics (*text*), inline code (`code`), and citation markers ([Doc, p. X, par. Y])
 */
function renderInlineMarkdown(text: string): React.ReactNode[] {
  if (!text) return [];

  // Regex splitting inline code, bold, italic, and citations
  const tokenRegex = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|\[(?:[^\]]+,\s*p\.\s*\d+[^\]]*)\])/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, index) => {
    if (!part) return null;

    // Inline Code
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      return (
        <code key={index} className="markdown-inline-code">
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold (**text** or __text__)
    if ((part.startsWith("**") && part.endsWith("**") && part.length >= 4) ||
        (part.startsWith("__") && part.endsWith("__") && part.length >= 4)) {
      return (
        <strong key={index} className="markdown-bold">
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Italic (*text* or _text_)
    if ((part.startsWith("*") && part.endsWith("*") && part.length >= 2) ||
        (part.startsWith("_") && part.endsWith("_") && part.length >= 2)) {
      return (
        <em key={index} className="markdown-italic">
          {part.slice(1, -1)}
        </em>
      );
    }

    // Citation Match Tag e.g. [Doc, p. 1, par. 2]
    if (part.startsWith("[") && part.endsWith("]") && /p\.\s*\d+/i.test(part)) {
      return (
        <span key={index} className="markdown-citation-tag">
          {part}
        </span>
      );
    }

    return part;
  });
}
