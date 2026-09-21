"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  ExternalLink,
  Layers,
  Network,
  PlayCircle,
  RefreshCw,
  Sparkles,
  Terminal,
  Wrench,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface AgentStepItem {
  id: string;
  step_number: number;
  agent_name: string;
  input_state?: Record<string, unknown>;
  output_state?: Record<string, unknown>;
  status: string;
  duration_ms?: number;
}

interface ToolCallItem {
  id: string;
  tool_name: string;
  tool_input?: Record<string, unknown>;
  tool_output?: Record<string, unknown>;
  is_sensitive: boolean;
  status: string;
  execution_time_ms?: number;
}

interface AgentRunDetail {
  id: string;
  workflow_name: string;
  request_prompt: string;
  status: string;
  plan_json?: { plan?: string[]; descriptions?: string[] };
  execution_summary?: string;
  error_details?: string;
  total_duration_ms?: number;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  steps: AgentStepItem[];
  tool_calls: ToolCallItem[];
}

interface AgentRunListItem {
  id: string;
  workflow_name: string;
  request_prompt: string;
  status: string;
  step_count: number;
  total_duration_ms?: number;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

function AgentRunsContent() {
  const searchParams = useSearchParams();
  const queryRunId = searchParams.get("runId");

  const [runs, setRuns] = useState<AgentRunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<AgentRunDetail | null>(null);
  const [inspecting, setInspecting] = useState(false);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  const fetchRuns = async () => {
    setLoading(true);
    try {
      const res = await api.get<{ runs: AgentRunListItem[]; total: number }>("/api/v1/agents/runs");
      if (res && res.runs) {
        setRuns(res.runs);
      }
    } catch {
      // Offline fallback
    } finally {
      setLoading(false);
    }
  };

  const loadRunDetail = async (runId: string) => {
    setInspecting(true);
    try {
      const detail = await api.get<AgentRunDetail>(`/api/v1/agents/runs/${runId}`);
      if (detail) {
        setSelectedRun(detail);
      }
    } catch {
      // Failed to load
    } finally {
      setInspecting(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  useEffect(() => {
    if (queryRunId) {
      loadRunDetail(queryRunId);
    }
  }, [queryRunId]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center space-x-2">
            <span>Agent Execution Traces</span>
            <Badge variant="cyan">LangGraph DAG State</Badge>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Auditable execution steps, agent transitions, and tool invocations across tenant runs.
          </p>
        </div>
        <Button variant="outline" size="sm" className="space-x-1.5" onClick={fetchRuns}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Traces</span>
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <Card className="border-slate-800 bg-slate-900/60">
          <CardHeader>
            <CardTitle className="text-base">Recent Workflow Runs</CardTitle>
            <CardDescription>Click any execution trace to inspect the step-by-step DAG timeline.</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-12 text-sm text-slate-500">Loading execution traces...</div>
            ) : runs.length === 0 ? (
              <div className="text-center py-12 text-sm text-slate-500">
                No agent runs dispatched yet. Visit the Agents Fleet page to launch a workflow.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Run ID</TableHead>
                    <TableHead>Task Objective</TableHead>
                    <TableHead>Workflow</TableHead>
                    <TableHead>Steps</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Executed At</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow
                      key={run.id}
                      onClick={() => loadRunDetail(run.id)}
                      className="cursor-pointer hover:bg-slate-800/60 transition-colors"
                    >
                      <TableCell className="font-mono text-xs text-teal-400">
                        {run.id.slice(0, 8)}...
                      </TableCell>
                      <TableCell className="font-medium text-slate-200 max-w-sm truncate">
                        {run.request_prompt}
                      </TableCell>
                      <TableCell className="text-xs font-mono text-cyan-400">
                        {run.workflow_name}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-300">
                        {run.step_count} steps
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-400">
                        {run.total_duration_ms ? `${(run.total_duration_ms / 1000).toFixed(2)}s` : "—"}
                      </TableCell>
                      <TableCell>
                        {run.status === "COMPLETED" ? (
                          <Badge variant="success">Completed</Badge>
                        ) : run.status === "FAILED" ? (
                          <Badge variant="danger">Failed</Badge>
                        ) : (
                          <Badge variant="warning">Running</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-slate-400">
                        {formatDate(run.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="ghost" className="h-7 text-xs text-teal-400">
                          Inspect
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Trace Inspector Drawer / Modal */}
      {selectedRun && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-950/70 backdrop-blur-sm">
          <div className="w-full max-w-2xl h-full bg-slate-900 border-l border-slate-800 p-6 flex flex-col shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-200">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Network className="h-5 w-5 text-teal-400" />
                <h2 className="text-lg font-bold text-slate-100">Workflow Execution Trace</h2>
              </div>
              <button
                onClick={() => setSelectedRun(null)}
                className="p-1 text-slate-400 hover:text-slate-100 rounded-md"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="py-4 space-y-6 flex-1">
              {/* Directive Header */}
              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                    Task Directive
                  </span>
                  <Badge
                    variant={
                      selectedRun.status === "COMPLETED"
                        ? "success"
                        : selectedRun.status === "FAILED"
                        ? "danger"
                        : "warning"
                    }
                  >
                    {selectedRun.status}
                  </Badge>
                </div>
                <p className="text-sm font-semibold text-slate-200">{selectedRun.request_prompt}</p>
                <div className="flex items-center space-x-4 text-xs text-slate-400 pt-1">
                  <span>Duration: <strong className="text-slate-300">{selectedRun.total_duration_ms ? `${(selectedRun.total_duration_ms / 1000).toFixed(2)}s` : "—"}</strong></span>
                  <span>Steps: <strong className="text-slate-300">{selectedRun.steps.length}</strong></span>
                  <span>Tools: <strong className="text-slate-300">{selectedRun.tool_calls.length}</strong></span>
                </div>
              </div>

              {/* Execution Plan */}
              {selectedRun.plan_json?.plan && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Supervisor Execution Plan
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedRun.plan_json.plan.map((agent, idx) => (
                      <div
                        key={idx}
                        className="flex items-center text-xs px-2.5 py-1 rounded-lg border border-teal-500/30 bg-teal-950/40 text-teal-300 font-mono"
                      >
                        <span className="text-[10px] text-teal-500 mr-1.5 font-bold">#{idx + 1}</span>
                        <span>{agent}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Visual Step Timeline */}
              <div>
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                  Execution DAG Timeline ({selectedRun.steps.length} Steps)
                </h3>
                <div className="space-y-3">
                  {selectedRun.steps.map((step) => {
                    const isExpanded = expandedStep === step.step_number;
                    return (
                      <div
                        key={step.id}
                        className="rounded-xl border border-slate-800 bg-slate-950/40 overflow-hidden"
                      >
                        <div
                          onClick={() => setExpandedStep(isExpanded ? null : step.step_number)}
                          className="p-3.5 flex items-center justify-between cursor-pointer hover:bg-slate-800/40 transition-colors"
                        >
                          <div className="flex items-center space-x-3">
                            <span className="w-6 h-6 rounded-full bg-teal-500/20 text-teal-400 flex items-center justify-center text-xs font-bold font-mono">
                              {step.step_number}
                            </span>
                            <div>
                              <div className="flex items-center space-x-2">
                                <span className="text-xs font-bold font-mono text-slate-200">
                                  {step.agent_name}
                                </span>
                                <Badge variant="teal" className="text-[9px] py-0 px-1.5">
                                  {step.status}
                                </Badge>
                              </div>
                              <p className="text-[11px] text-slate-400 mt-0.5">
                                Completed in {step.duration_ms || 100}ms
                              </p>
                            </div>
                          </div>
                          <div className="text-slate-400">
                            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          </div>
                        </div>

                        {/* Expandable State Inspector */}
                        {isExpanded && (
                          <div className="p-3.5 border-t border-slate-800/80 bg-slate-950/80 space-y-3 text-xs font-mono">
                            <div>
                              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block mb-1">
                                Output State
                              </span>
                              <pre className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-teal-300 overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(step.output_state, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Tool Calls Audited */}
              {selectedRun.tool_calls.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center space-x-1">
                    <Wrench className="h-3.5 w-3.5 text-cyan-400" />
                    <span>Audited Tool Invocations ({selectedRun.tool_calls.length})</span>
                  </h3>
                  <div className="space-y-1.5">
                    {selectedRun.tool_calls.map((tool) => (
                      <div
                        key={tool.id}
                        className="p-2.5 rounded-lg border border-slate-800 bg-slate-950/40 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center space-x-2">
                          <Terminal className="h-3.5 w-3.5 text-slate-500" />
                          <span className="font-mono text-cyan-300 font-semibold">{tool.tool_name}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="text-[11px] font-mono text-slate-400">{tool.execution_time_ms || 50}ms</span>
                          <Badge variant="cyan" className="text-[9px] py-0 px-1.5">{tool.status}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Executive Summary */}
              {selectedRun.execution_summary && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center space-x-1">
                    <Sparkles className="h-3.5 w-3.5 text-teal-400" />
                    <span>Executive Briefing Synthesis</span>
                  </h3>
                  <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
                    {selectedRun.execution_summary}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-slate-800">
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => setSelectedRun(null)}
              >
                Close Trace Inspector
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AgentRunsPage() {
  return (
    <Suspense fallback={<div className="text-center py-16 text-slate-500 text-sm">Loading Trace Explorer...</div>}>
      <AgentRunsContent />
    </Suspense>
  );
}
