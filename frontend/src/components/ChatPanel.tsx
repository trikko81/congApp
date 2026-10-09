"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Upload,
  FileText,
  Sparkles,
  ExternalLink,
  Bot,
  User,
  ChevronDown,
  ChevronUp,
  Database,
  Search,
  CheckCircle2,
} from "lucide-react";
import MarkdownRenderer from "./MarkdownRenderer";

export interface CitationItem {
  docTitle: string;
  page: number;
  paragraph?: number;
  snippet: string;
  ordinanceId?: string;
  chapterId?: string;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  citations?: CitationItem[];
  timestamp: string;
}

interface ChatPanelProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onSendMessage: (query: string) => void;
  onUploadFile: (file: File) => void;
  onCitationClick: (citation: CitationItem) => void;
}

export default function ChatPanel({
  messages,
  isStreaming,
  onSendMessage,
  onUploadFile,
  onCitationClick,
}: ChatPanelProps) {
  const [inputQuery, setInputQuery] = useState("");
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const toggleEvidence = (msgId: string) => {
    setExpandedEvidence((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isStreaming) return;
    onSendMessage(inputQuery.trim());
    setInputQuery("");
  };

  const handleInlineCitationClick = (
    msg: ChatMessage,
    inlineCit: { docTitle: string; page: number; paragraph?: number; snippet?: string }
  ) => {
    // 1. Try to find an exact or fuzzy matching citation in msg.citations
    const queryDoc = inlineCit.docTitle.toLowerCase().replace(/\.pdf$/, "");
    let matched = msg.citations?.find((c) => {
      const cDoc = c.docTitle.toLowerCase().replace(/\.pdf$/, "");
      const titleMatch =
        queryDoc.length > 0 &&
        (cDoc.includes(queryDoc) ||
          queryDoc.includes(cDoc) ||
          c.ordinanceId?.toLowerCase().includes(queryDoc));
      return titleMatch && c.page === inlineCit.page;
    });

    if (!matched && msg.citations?.length) {
      // Fuzzy match by doc title only
      matched = msg.citations.find((c) => {
        const cDoc = c.docTitle.toLowerCase().replace(/\.pdf$/, "");
        return (
          queryDoc.length > 0 &&
          (cDoc.includes(queryDoc) ||
            queryDoc.includes(cDoc) ||
            c.ordinanceId?.toLowerCase().includes(queryDoc))
        );
      });
    }

    if (matched) {
      onCitationClick(matched);
      return;
    }

    // 2. Fallback: synthesize CitationItem from parsed inline citation
    let targetDoc = inlineCit.docTitle.trim();
    if (!targetDoc && msg.citations?.length) {
      targetDoc = msg.citations[0].docTitle;
    }
    if (!targetDoc) {
      targetDoc = "Virginia_Beach_City_Council_Agenda_2026.pdf";
    }
    if (!targetDoc.toLowerCase().endsWith(".pdf")) {
      targetDoc = `${targetDoc}.pdf`;
    }

    onCitationClick({
      docTitle: targetDoc,
      page: inlineCit.page || 1,
      paragraph: inlineCit.paragraph,
      snippet: inlineCit.snippet || "",
      ordinanceId: inlineCit.docTitle,
    });
  };

  return (
    <div className="chat-panel flex flex-col h-full bg-background border-r border-border">
      {/* Scope / Upload Bar */}
      <div className="p-3 border-b border-border bg-card/60 backdrop-blur flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isStreaming}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition cursor-pointer"
          >
            <Upload size={13} />
            <span>Upload Agenda / Minutes</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            disabled={isStreaming}
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUploadFile(file);
              e.target.value = "";
            }}
          />
        </div>

        <div className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground bg-muted/60 px-2.5 py-1 rounded-md">
          <Database size={11} className="text-primary" />
          <span>Local document library</span>
        </div>
      </div>

      {/* Message Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-muted-foreground">
            <div className="h-12 w-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-3">
              <Sparkles size={24} />
            </div>
            <h3 className="font-semibold text-foreground text-sm">Ask anything about municipal actions</h3>
            <p className="text-xs text-muted-foreground mt-1 max-w-sm">
              Synthesize ordinances, setback changes, civic funding resolutions, and parcel tax impacts across uploaded packets.
            </p>
            <div className="flex flex-wrap gap-2 mt-4 justify-center">
              <button
                onClick={() => onSendMessage("What are the zoning and setback changes in this agenda?")}
                className="text-[11px] bg-muted hover:bg-muted/80 text-foreground px-3 py-1.5 rounded-lg border border-border transition cursor-pointer"
              >
                &quot;What are the zoning & setback changes?&quot;
              </button>
              <button
                onClick={() => onSendMessage("Summarize any proposed tax or millage adjustments.")}
                className="text-[11px] bg-muted hover:bg-muted/80 text-foreground px-3 py-1.5 rounded-lg border border-border transition cursor-pointer"
              >
                &quot;Summarize tax/millage adjustments&quot;
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.sender === "assistant" && (
                <div className="h-7 w-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-0.5">
                  <Bot size={15} />
                </div>
              )}

              <div
                className={`max-w-[88%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                  msg.sender === "user"
                    ? "bg-primary text-primary-foreground font-medium rounded-br-none shadow-xs"
                    : "bg-card border border-border text-foreground rounded-bl-none shadow-xs"
                }`}
              >
                {msg.sender === "assistant" ? (
                  <div className="space-y-3">
                    <MarkdownRenderer
                      content={msg.text}
                      onCitationClick={(cit) => handleInlineCitationClick(msg, cit)}
                    />

                    {/* Grounded Citation Badges */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="pt-2.5 border-t border-border/50 space-y-2">
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {msg.citations.map((cit, cIdx) => (
                              <button
                                key={cIdx}
                                onClick={() => onCitationClick(cit)}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-primary/10 hover:bg-primary/20 text-[11px] font-semibold text-primary border border-primary/20 transition cursor-pointer"
                                title="Click to verify in PDF viewer"
                              >
                                <FileText size={11} />
                                <span>
                                  {[cit.ordinanceId, cit.chapterId].filter(Boolean).join(" · ") || "Citation"}: Page {cit.page}
                                </span>
                                <ExternalLink size={10} />
                              </button>
                            ))}

                          </div>

                          {/* Expandable Grounded Source Chunks Toggle */}
                          <button
                            onClick={() => toggleEvidence(msg.id)}
                            className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground font-medium transition cursor-pointer"
                          >
                            <Database size={10} />
                            <span>
                              {expandedEvidence[msg.id] ? "Hide Evidence Chunks" : `${msg.citations.length} Grounded Source Chunks`}
                            </span>
                            {expandedEvidence[msg.id] ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          </button>
                        </div>

                        {/* Expandable Grounded Evidence Chunks Drawer */}
                        {expandedEvidence[msg.id] && (
                          <div className="mt-2 space-y-1.5 p-2 rounded-lg bg-muted/60 border border-border text-[11px]">
                            <div className="flex items-center gap-1.5 text-muted-foreground font-semibold text-[10px] uppercase tracking-wider">
                              <CheckCircle2 size={11} className="text-emerald-500" />
                              <span>Retrieved Document Chunks Used in Synthesis</span>
                            </div>

                            {msg.citations.map((cit, i) => (
                              <div
                                key={i}
                                role="button"
                                tabIndex={0}
                                onClick={() => onCitationClick(cit)}
                                onKeyDown={(event) => {
                                  if (event.key === "Enter" || event.key === " ") {
                                    event.preventDefault();
                                    onCitationClick(cit);
                                  }
                                }}
                                className="p-2 rounded bg-card hover:bg-card/80 border border-border transition cursor-pointer flex flex-col gap-1"
                              >
                                <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                                  <span className="font-semibold text-foreground truncate max-w-[200px]">
                                    {cit.docTitle}
                                  </span>
                                  <span className="bg-primary/10 text-primary font-bold px-1.5 py-0.5 rounded">
                                    Page {cit.page}
                                  </span>
                                </div>
                                <p className="text-[11px] text-foreground/80 italic line-clamp-2">
                                  &ldquo;{cit.snippet || "Retrieved legal text excerpt from official city agenda."}&rdquo;
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div>{msg.text}</div>
                )}
              </div>

              {msg.sender === "user" && (
                <div className="h-7 w-7 rounded-lg bg-muted text-muted-foreground flex items-center justify-center shrink-0 mt-0.5">
                  <User size={15} />
                </div>
              )}
            </div>
          ))
        )}

        {isStreaming && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground p-2">
            <Sparkles size={14} className="animate-spin text-primary" />
            <span>Synthesizing civic documents & matching legal citations...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Query Bar */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-border bg-card/80 backdrop-blur">
        <div className="flex items-center gap-2 bg-background border border-border rounded-xl px-3 py-1.5 focus-within:ring-1 focus-within:ring-primary shadow-xs">
          <Search size={14} className="text-muted-foreground shrink-0" />
          <input
            type="text"
            aria-label="Search municipal agenda items"
            placeholder="Search & synthesize municipal agenda items, ordinances, or tax millage..."
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={isStreaming}
            className="flex-1 text-xs bg-transparent focus:outline-none text-foreground placeholder:text-muted-foreground py-1"
          />
          <button
            type="submit"
            disabled={!inputQuery.trim() || isStreaming}
            aria-label="Send message"
            className="h-7 w-7 rounded-lg bg-primary text-primary-foreground disabled:opacity-40 flex items-center justify-center hover:bg-primary/90 transition cursor-pointer shrink-0"
          >
            <Send size={13} />
          </button>
        </div>
      </form>
    </div>
  );
}
