"use client";

import React, { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Bot,
  CheckCircle2,
  ExternalLink,
  FileText,
  Layers,
  MessageSquare,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { getValidAuthToken } from "@/lib/auth-token";

interface Citation {
  citation_token: string;
  document_id: string;
  document_title: string;
  filename: string;
  page_number: number | null;
  excerpt: string;
  score: number;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
  timestamp?: string;
}

interface ConversationItem {
  id: string;
  title: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

function ChatContent() {
  const searchParams = useSearchParams();
  const initialConvId = searchParams.get("id");

  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(initialConvId);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Welcome to AEGIS AI Autonomous Operations Assistant. I provide real-time, grounded intelligence directly from your tenant vector store with verifiable document citations. Ask a question or trigger a task below.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [activeModel, setActiveModel] = useState("gemini-2.5-flash");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Load conversations list
  const fetchConversations = async () => {
    try {
      const res = await api.get<{ conversations: ConversationItem[]; total: number }>("/api/v1/chat/conversations");
      if (res && res.conversations) {
        setConversations(res.conversations);
      }
    } catch {
      // Offline / unauthenticated fallback
    }
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  // Load messages if active conversation changes
  useEffect(() => {
    if (!activeConversationId) return;

    const loadMessages = async () => {
      try {
        const res = await api.get<{ messages: Array<{ id: string; role: string; content: string; citations_json?: Citation[]; created_at: string }> }>(
          `/api/v1/chat/conversations/${activeConversationId}/messages`
        );
        if (res && res.messages && res.messages.length > 0) {
          setMessages(
            res.messages.map((m) => ({
              id: m.id,
              role: m.role as "user" | "assistant",
              content: m.content,
              citations: m.citations_json || undefined,
              timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            }))
          );
        }
      } catch {
        // Handle error silently
      }
    };

    loadMessages();
  }, [activeConversationId]);

  const handleStartNewChat = () => {
    setActiveConversationId(null);
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content:
          "New conversation started. Knowledge base vectors and verifiable citations are active for your tenant.",
      },
    ]);
  };

  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.delete(`/api/v1/chat/conversations/${convId}`);
      if (activeConversationId === convId) {
        handleStartNewChat();
      }
      fetchConversations();
    } catch {
      // Handle error
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userPrompt = input.trim();
    setInput("");

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: userPrompt,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const assistantPlaceholderId = `asst-${Date.now()}`;
    const assistantMsg: ChatMessage = {
      id: assistantPlaceholderId,
      role: "assistant",
      content: "",
      citations: [],
      timestamp: "Streaming...",
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    try {
      const token = await getValidAuthToken();
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";

      const response = await fetch(`${apiUrl}/api/v1/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: userPrompt,
          conversation_id: activeConversationId || undefined,
          model: activeModel,
        }),
      });

      if (!response.ok || !response.body) {
        const errText = await response.text().catch(() => "");
        throw new Error(
          response.status === 401
            ? "Authentication error — please refresh the page and try again."
            : response.status === 422
            ? "Invalid request parameters — please check your message and try again."
            : `Server error (${response.status}): ${errText || "Failed to initialize AI stream"}`
        );
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = "";
      let accumulatedCitations: Citation[] = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data:")) {
            const dataStr = trimmed.slice(5).trim();
            if (!dataStr) continue;

            try {
              const event = JSON.parse(dataStr);

              if (event.type === "metadata") {
                if (event.conversation_id && !activeConversationId) {
                  setActiveConversationId(event.conversation_id);
                  fetchConversations();
                }
              } else if (event.type === "token") {
                accumulatedContent += event.content;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantPlaceholderId
                      ? { ...msg, content: accumulatedContent }
                      : msg
                  )
                );
              } else if (event.type === "citations") {
                accumulatedCitations = event.citations || [];
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantPlaceholderId
                      ? { ...msg, citations: accumulatedCitations }
                      : msg
                  )
                );
              } else if (event.type === "done") {
                fetchConversations();
              }
            } catch {
              // Parse error ignored
            }
          }
        }
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "An unexpected error occurred.";
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantPlaceholderId
            ? {
                ...msg,
                content:
                  msg.content ||
                  `⚠️ ${errorMessage}\n\nPlease try again or refresh the page.`,
              }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleSuggestionClick = (prompt: string) => {
    setInput(prompt);
  };

  return (
    <div className="h-[calc(100vh-7.5rem)] flex gap-4 max-w-7xl mx-auto">
      {/* Sidebar: Conversation Sessions */}
      <div className="w-72 hidden md:flex flex-col rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2 text-slate-200 font-semibold text-sm">
            <MessageSquare className="h-4 w-4 text-teal-400" />
            <span>Conversations</span>
          </div>
          <Button
            size="sm"
            variant="cyan"
            className="h-7 text-xs px-2.5 rounded-lg flex items-center space-x-1"
            onClick={handleStartNewChat}
          >
            <Plus className="h-3.5 w-3.5" />
            <span>New</span>
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto py-3 space-y-1.5">
          {conversations.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-500">
              No saved sessions yet.
            </div>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => setActiveConversationId(c.id)}
                className={`group flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition-all ${
                  activeConversationId === c.id
                    ? "bg-teal-500/15 border border-teal-500/30 text-teal-300 font-medium"
                    : "text-slate-400 hover:bg-slate-800/70 hover:text-slate-200 border border-transparent"
                }`}
              >
                <div className="truncate pr-2">
                  <p className="truncate font-medium">{c.title || "Untitled Session"}</p>
                  <span className="text-[10px] text-slate-500">
                    {c.message_count} messages
                  </span>
                </div>
                <button
                  onClick={(e) => handleDeleteConversation(c.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 rounded transition-opacity"
                  title="Delete conversation"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Model Selector */}
        <div className="pt-3 border-t border-slate-800">
          <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Active Intelligence Engine
          </label>
          <select
            value={activeModel}
            onChange={(e) => setActiveModel(e.target.value)}
            className="w-full text-xs bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-teal-500"
          >
            <option value="gemini-2.5-flash">Gemini 2.5 Flash ⚡ (Recommended)</option>
            <option value="gemini-2.5-pro">Gemini 2.5 Pro 🔬 (Deep Reasoning)</option>
            <option value="gemini-flash-latest">Gemini Flash Latest 🚀</option>
            <option value="mock-aegis-core">AEGIS Core 🔒 (Offline/Deterministic)</option>
          </select>
        </div>
      </div>

      {/* Main Chat Panel */}
      <div className="flex-1 flex flex-col rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-md overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3.5 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-base font-bold text-slate-100">
                  {conversations.find((c) => c.id === activeConversationId)?.title ||
                    "Autonomous Operations Dialogue"}
                </h1>
                <Badge variant="teal" className="text-[10px] py-0 px-2">
                  <ShieldCheck className="h-3 w-3 mr-1 inline" />
                  Grounded
                </Badge>
              </div>
              <p className="text-[11px] text-slate-400">
                Tenant vector isolated • Recursive character chunking • Ground truth citations
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="cyan" className="text-xs">
              SSE Stream
            </Badge>
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start space-x-3 ${
                msg.role === "user" ? "flex-row-reverse space-x-reverse" : ""
              }`}
            >
              <div
                className={`h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-semibold ${
                  msg.role === "assistant"
                    ? "bg-gradient-to-br from-teal-500 to-cyan-600 text-slate-950 font-bold shadow-lg shadow-teal-500/20"
                    : "bg-slate-800 text-slate-200 border border-slate-700"
                }`}
              >
                {msg.role === "assistant" ? <Sparkles className="h-4 w-4" /> : "U"}
              </div>
              <div
                className={`max-w-2xl rounded-2xl p-4 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-teal-500/15 border border-teal-500/30 text-slate-100 shadow-md"
                    : "bg-slate-900/90 border border-slate-800 text-slate-200 shadow-xl"
                }`}
              >
                <div className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed">
                  {msg.content || (
                    <span className="inline-flex items-center text-slate-400 text-xs">
                      <span className="animate-pulse mr-2">●</span> Synthesizing response with pgvector grounding...
                    </span>
                  )}
                </div>

                {/* Verified Citation Badges */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                      <span className="flex items-center">
                        <CheckCircle2 className="h-3 w-3 text-teal-400 mr-1 inline" />
                        Verified Source Grounding ({msg.citations.length})
                      </span>
                      <span className="text-slate-500">Click to view source excerpt</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {msg.citations.map((c, idx) => (
                        <button
                          key={`${c.citation_token}-${idx}`}
                          onClick={() => setSelectedCitation(c)}
                          className="inline-flex items-center text-[11px] px-2.5 py-1 rounded-md border border-cyan-500/30 bg-cyan-950/40 text-cyan-300 hover:bg-cyan-500/20 hover:border-cyan-400 transition-all cursor-pointer font-mono"
                        >
                          <FileText className="h-3 w-3 mr-1 text-cyan-400" />
                          <span>{c.citation_token}</span>
                          <span className="ml-1 text-[10px] text-cyan-400/80 truncate max-w-[120px]">
                            {c.document_title}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestion Prompts */}
        {messages.length <= 1 && (
          <div className="px-6 pb-2">
            <p className="text-xs text-slate-500 mb-2 font-medium">Suggested operational directives:</p>
            <div className="flex flex-wrap gap-2">
              {[
                "Summarize failover protocols in our operations manual",
                "What are our tenant isolation security standards?",
                "Analyze Q3 forecasting metrics and database health",
              ].map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-teal-300 hover:border-teal-500/40 transition-all text-left"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Bar */}
        <form onSubmit={handleSend} className="p-4 border-t border-slate-800 bg-slate-900/80">
          <div className="relative rounded-xl border border-slate-700 bg-slate-950/90 shadow-2xl p-2 flex items-center space-x-2 focus-within:border-teal-500 transition-colors">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isStreaming}
              placeholder={isStreaming ? "Streaming response..." : "Ask questions, explore documentation, or dispatch autonomous tasks..."}
              className="flex-1 bg-transparent px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
            />
            <Button
              type="submit"
              size="sm"
              variant="primary"
              disabled={isStreaming || !input.trim()}
              className="space-x-1.5"
            >
              <span>Send</span>
              <Send className="h-3.5 w-3.5" />
            </Button>
          </div>
        </form>
      </div>

      {/* Source Preview Drawer / Modal */}
      {selectedCitation && (
        <div className="w-80 rounded-2xl border border-slate-800 bg-slate-900/90 backdrop-blur-md p-4 flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-2 text-slate-100 font-semibold text-sm">
              <Layers className="h-4 w-4 text-cyan-400" />
              <span>Source Preview</span>
            </div>
            <button
              onClick={() => setSelectedCitation(null)}
              className="text-slate-400 hover:text-slate-100 p-1 rounded-md"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto py-4 space-y-4">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Citation Token</span>
              <p className="text-xs font-mono text-cyan-300 mt-0.5 bg-cyan-950/40 p-1.5 rounded border border-cyan-500/20">
                {selectedCitation.citation_token}
              </p>
            </div>

            <div>
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Document Title</span>
              <p className="text-sm font-semibold text-slate-200 mt-0.5">{selectedCitation.document_title}</p>
              <p className="text-xs text-slate-400">{selectedCitation.filename}</p>
            </div>

            <div className="flex items-center space-x-3 text-xs">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block">Page</span>
                <Badge variant="teal" className="mt-1">
                  Page {selectedCitation.page_number || 1}
                </Badge>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block">Similarity</span>
                <Badge variant="cyan" className="mt-1">
                  {Math.round(selectedCitation.score * 100)}% match
                </Badge>
              </div>
            </div>

            <div>
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Verified Excerpt</span>
              <div className="mt-1.5 p-3 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap max-h-60 overflow-y-auto">
                {selectedCitation.excerpt}
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800">
            <Button
              size="sm"
              variant="outline"
              className="w-full text-xs flex items-center justify-center space-x-1"
              onClick={() => setSelectedCitation(null)}
            >
              <span>Close Drawer</span>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="text-slate-400 p-8 text-center text-sm">Loading AI Chat...</div>}>
      <ChatContent />
    </Suspense>
  );
}
