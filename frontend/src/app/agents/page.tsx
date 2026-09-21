"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  Bot,
  Database,
  FileSearch,
  FileText,
  Network,
  Play,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";

interface AgentItem {
  id: string;
  name: string;
  role: string;
  icon: string;
  description: string;
  capabilities: string[];
  default_tools: string[];
}

const iconMap: Record<string, React.ReactNode> = {
  Network: <Network className="h-5 w-5" />,
  BookOpen: <BookOpen className="h-5 w-5" />,
  Database: <Database className="h-5 w-5" />,
  BarChart3: <BarChart3 className="h-5 w-5" />,
  TrendingUp: <TrendingUp className="h-5 w-5" />,
  FileSearch: <FileSearch className="h-5 w-5" />,
  ShieldCheck: <ShieldCheck className="h-5 w-5" />,
  FileText: <FileText className="h-5 w-5" />,
};

export default function AgentsPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedLeadAgent, setSelectedLeadAgent] = useState("supervisor");
  const [dispatchPrompt, setDispatchPrompt] = useState("");
  const [dispatching, setDispatching] = useState(false);
  const [dispatchError, setDispatchError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const data = await api.get<AgentItem[]>("/api/v1/agents");
        if (data && data.length > 0) {
          setAgents(data);
        }
      } catch {
        // Handled silently
      } finally {
        setLoading(false);
      }
    };
    fetchAgents();
  }, []);

  const handleOpenDispatch = (agentId: string) => {
    setSelectedLeadAgent(agentId);
    setDispatchPrompt("");
    setDispatchError(null);
    setModalOpen(true);
  };

  const handleExecuteRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dispatchPrompt.trim()) return;

    setDispatching(true);
    setDispatchError(null);

    try {
      const run = await api.post<{ id: string }>("/api/v1/agents/runs", {
        prompt: dispatchPrompt.trim(),
        lead_agent: selectedLeadAgent,
        workflow_name: "autonomous_supervisor",
      });

      setModalOpen(false);
      router.push(`/agent-runs?runId=${run.id}`);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Failed to execute agent run";
      setDispatchError(errorMsg);
    } finally {
      setDispatching(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center space-x-2">
            <span>Autonomous Agent Fleet</span>
            <Badge variant="teal">LangGraph Runtime</Badge>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            8 coordinated specialist agents executing under a Supervisor state graph with step-by-step tracing.
          </p>
        </div>
        <Button
          variant="primary"
          className="space-x-1.5"
          onClick={() => handleOpenDispatch("supervisor")}
        >
          <Play className="h-4 w-4" />
          <span>Execute Multi-Agent Workflow</span>
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-16 text-sm text-slate-500">Loading agent fleet metadata...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {agents.map((agent) => (
            <Card
              key={agent.id}
              className="border-slate-800 bg-slate-900/60 hover:border-teal-500/30 transition-all flex flex-col justify-between"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="p-2.5 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
                    {iconMap[agent.icon] || <Bot className="h-5 w-5" />}
                  </div>
                  <Badge variant="teal">ACTIVE</Badge>
                </div>
                <CardTitle className="text-base mt-3 text-slate-100">{agent.name}</CardTitle>
                <span className="text-[11px] font-mono text-cyan-400">{agent.role}</span>
                <CardDescription className="text-xs leading-relaxed mt-2 text-slate-400">
                  {agent.description}
                </CardDescription>

                <div className="mt-3 pt-3 border-t border-slate-800/80">
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block mb-1.5">
                    Core Capabilities
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {agent.capabilities.slice(0, 3).map((cap, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0 border-t border-slate-800/60 mt-2 py-3 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  {agent.default_tools.length} Tools Bound
                </span>
                <Button
                  size="sm"
                  variant="cyan"
                  className="h-7 text-xs px-2.5 space-x-1"
                  onClick={() => handleOpenDispatch(agent.id)}
                >
                  <Play className="h-3 w-3" />
                  <span>Dispatch</span>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Dispatch Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Sparkles className="h-5 w-5 text-teal-400" />
                <h2 className="text-lg font-bold text-slate-100">Dispatch Multi-Agent Workflow</h2>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 p-1"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleExecuteRun} className="space-y-4 mt-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">
                  Designated Lead Agent
                </label>
                <select
                  value={selectedLeadAgent}
                  onChange={(e) => setSelectedLeadAgent(e.target.value)}
                  className="w-full text-xs bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-teal-500"
                >
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.role})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1">
                  Operational Directive / Prompt
                </label>
                <textarea
                  rows={4}
                  value={dispatchPrompt}
                  onChange={(e) => setDispatchPrompt(e.target.value)}
                  placeholder="e.g. Audit database query latency, run 14-day ML forecast, verify grounding, and prepare executive briefing."
                  className="w-full text-xs bg-slate-950 border border-slate-700 rounded-lg p-3 text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-teal-500"
                  required
                />
              </div>

              {dispatchError && (
                <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                  {dispatchError}
                </div>
              )}

              <div className="flex justify-end space-x-2 pt-3 border-t border-slate-800">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setModalOpen(false)}
                  disabled={dispatching}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={dispatching || !dispatchPrompt.trim()}
                  className="space-x-1"
                >
                  <Play className="h-3.5 w-3.5" />
                  <span>{dispatching ? "Executing Workflow..." : "Launch Execution"}</span>
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
