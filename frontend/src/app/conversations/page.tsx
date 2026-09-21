"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, MessageSquare, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface ConversationItem {
  id: string;
  title: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchConversations = async () => {
    try {
      const res = await api.get<{ conversations: ConversationItem[]; total: number }>("/api/v1/chat/conversations");
      if (res && res.conversations) {
        setConversations(res.conversations);
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await api.delete(`/api/v1/chat/conversations/${id}`);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch {
      // Handle error
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center space-x-2">
            <span>Conversation History</span>
            <Badge variant="teal">Saved Sessions</Badge>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Historical multi-turn AI dialogues with recorded citation links and agent execution steps.
          </p>
        </div>

        <Link href="/chat">
          <Button variant="cyan" size="sm" className="space-x-1.5">
            <Plus className="h-4 w-4" />
            <span>New Chat Session</span>
          </Button>
        </Link>
      </div>

      {loading ? (
        <div className="text-center py-12 text-sm text-slate-500">Loading conversation history...</div>
      ) : conversations.length === 0 ? (
        <Card className="border-slate-800 bg-slate-900/40 p-12 text-center">
          <div className="mx-auto w-12 h-12 rounded-2xl bg-teal-500/10 text-teal-400 border border-teal-500/20 flex items-center justify-center mb-3">
            <MessageSquare className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200">No conversations recorded</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            Start a new conversation in the Autonomous AI Chat to ground answers in your tenant vector store.
          </p>
          <Link href="/chat" className="inline-block mt-4">
            <Button variant="primary" size="sm">Start First Chat</Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-3">
          {conversations.map((c) => (
            <Link key={c.id} href={`/chat?id=${c.id}`}>
              <Card className="border-slate-800 bg-slate-900/60 hover:border-teal-500/40 hover:bg-slate-900/90 transition-all cursor-pointer group">
                <CardContent className="p-5 flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="p-3 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
                      <MessageSquare className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-100 group-hover:text-teal-300 transition-colors">
                        {c.title || "Untitled Session"}
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {c.message_count} messages • Status: {c.status}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-slate-500">
                    <span>{formatDate(c.updated_at || c.created_at)}</span>
                    <button
                      onClick={(e) => handleDelete(c.id, e)}
                      className="p-1.5 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition-colors"
                      title="Delete conversation"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                    <ArrowUpRight className="h-4 w-4 text-slate-400 group-hover:text-teal-400 transition-colors" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
