"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  BarChart2,
  CheckCircle2,
  Clock,
  Code2,
  Database,
  FileCode,
  FileSearch,
  FileText,
  Globe,
  Layers,
  Play,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
  Terminal,
  TrendingUp,
  Wrench,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";

interface MCPTool {
  name: string;
  description: string;
  inputSchema: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
  };
  category: string;
  required_permission: string;
  requires_approval: boolean;
  is_sensitive: boolean;
  rate_limit_per_minute: number;
}

interface ToolExecutionResult {
  tool_name: string;
  status: "SUCCESS" | "FAILED" | "BLOCKED" | "PENDING_APPROVAL";
  output: any;
  error?: string | null;
  execution_time_ms: number;
  requires_approval: boolean;
  audit_log_id?: string | null;
}

interface AuditRecord {
  id: string;
  tool_name: string;
  status: string;
  user_id: string;
  details: any;
  created_at: string;
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  RAG: <FileSearch className="h-4 w-4 text-sky-400" />,
  DATABASE: <Database className="h-4 w-4 text-emerald-400" />,
  ANALYTICS: <BarChart2 className="h-4 w-4 text-indigo-400" />,
  ML: <TrendingUp className="h-4 w-4 text-purple-400" />,
  REPORTING: <FileText className="h-4 w-4 text-amber-400" />,
  WEB: <Globe className="h-4 w-4 text-cyan-400" />,
  SYSTEM: <Activity className="h-4 w-4 text-teal-400" />,
  GENERAL: <Wrench className="h-4 w-4 text-zinc-400" />,
};

const DEFAULT_ARGUMENTS: Record<string, Record<string, any>> = {
  search_documents: { query: "enterprise security protocols", top_k: 3 },
  query_database: { query: "SELECT id, action, status FROM audit_logs WHERE organization_id = :org_id;", limit: 5 },
  analyze_csv: { csv_content: "region,latency_ms,cost_usd\nus-east,24.5,120.0\nus-west,38.1,95.0\neu-central,41.2,145.0\n", operation: "profile" },
  run_forecast: { horizon_steps: 14 },
  detect_anomalies: { contamination: 0.05 },
  generate_report: {
    title: "Executive Infrastructure Efficiency Review",
    summary: "Cloud utilization optimization reduced latency by 32% while maintaining compliance.",
    key_findings: ["P99 latency down to 24ms", "Cluster utilization reached 81%"],
    metrics: { p99_latency_ms: 24.2, monthly_savings_percent: 18.5 },
  },
  search_web: { query: "autonomous AI agent governance trends 2026", num_results: 3 },
  get_system_status: { include_counts: true },
};

export default function ToolsPage() {
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);
  const [argumentsJson, setArgumentsJson] = useState("");
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<ToolExecutionResult | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditRecord[]>([]);
  const [activeTab, setActiveTab] = useState<"catalog" | "logs">("catalog");

  const fetchToolsAndLogs = async () => {
    setLoading(true);
    try {
      const [toolsData, logsData] = await Promise.all([
        api.get<MCPTool[]>("/api/v1/tools"),
        api.get<AuditRecord[]>("/api/v1/tools/audit/logs").catch(() => []),
      ]);
      if (toolsData && toolsData.length > 0) {
        setTools(toolsData);
        if (!selectedTool) {
          setSelectedTool(toolsData[0]);
          const defaultArgs = DEFAULT_ARGUMENTS[toolsData[0].name] || {};
          setArgumentsJson(JSON.stringify(defaultArgs, null, 2));
        }
      }
      if (logsData) {
        setAuditLogs(logsData);
      }
    } catch (err) {
      console.error("Failed to load MCP tools:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchToolsAndLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectTool = (tool: MCPTool) => {
    setSelectedTool(tool);
    setExecutionResult(null);
    const defaultArgs = DEFAULT_ARGUMENTS[tool.name] || {};
    setArgumentsJson(JSON.stringify(defaultArgs, null, 2));
  };

  const handleExecuteTool = async () => {
    if (!selectedTool) return;
    setExecuting(true);
    setExecutionResult(null);

    let parsedArgs: Record<string, any> = {};
    try {
      parsedArgs = JSON.parse(argumentsJson);
    } catch (e) {
      alert("Invalid JSON format in tool arguments.");
      setExecuting(false);
      return;
    }

    try {
      const res = await api.post<ToolExecutionResult>(`/api/v1/tools/${selectedTool.name}/execute`, {
        arguments: parsedArgs,
      });
      setExecutionResult(res);
      // Refresh audit logs
      const updatedLogs = await api.get<AuditRecord[]>("/api/v1/tools/audit/logs").catch(() => []);
      if (updatedLogs) setAuditLogs(updatedLogs);
    } catch (err: any) {
      setExecutionResult({
        tool_name: selectedTool.name,
        status: "FAILED",
        output: null,
        error: err?.message || "Execution failed",
        execution_time_ms: 0,
        requires_approval: false,
      });
    } finally {
      setExecuting(false);
    }
  };

  const filteredTools = tools.filter((t) => {
    const matchesCategory = categoryFilter === "ALL" || t.category === categoryFilter;
    const matchesSearch =
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const categories = ["ALL", ...Array.from(new Set(tools.map((t) => t.category)))];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-bold tracking-tight text-white">Model Context Protocol (MCP) Tools</h1>
            <Badge variant="purple" className="border-indigo-500/30 bg-indigo-500/10 text-indigo-400">
              MCP v1.0
            </Badge>
          </div>
          <p className="mt-1 text-sm text-zinc-400">
            Standardized tool discovery, strict RBAC permission gates, parameter schemas, and immutable audit logging.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant={activeTab === "catalog" ? "primary" : "outline"}
            size="sm"
            onClick={() => setActiveTab("catalog")}
            className="flex items-center gap-1.5"
          >
            <Wrench className="h-4 w-4" />
            Tools Studio
          </Button>
          <Button
            variant={activeTab === "logs" ? "primary" : "outline"}
            size="sm"
            onClick={() => setActiveTab("logs")}
            className="flex items-center gap-1.5"
          >
            <Clock className="h-4 w-4" />
            Audit Trail ({auditLogs.length})
          </Button>
          <Button variant="ghost" size="sm" onClick={fetchToolsAndLogs} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* KPI Overview */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card className="border-zinc-800 bg-zinc-950/60 backdrop-blur">
          <CardHeader className="p-4 pb-2">
            <CardDescription className="text-xs text-zinc-400">Registered Tools</CardDescription>
            <CardTitle className="text-2xl font-bold text-white">{tools.length}</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 text-xs text-zinc-500">MCP Compliant</CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-950/60 backdrop-blur">
          <CardHeader className="p-4 pb-2">
            <CardDescription className="text-xs text-zinc-400">Tool Categories</CardDescription>
            <CardTitle className="text-2xl font-bold text-indigo-400">
              {new Set(tools.map((t) => t.category)).size}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 text-xs text-zinc-500">RAG, DB, ML, Web, Analytics</CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-950/60 backdrop-blur">
          <CardHeader className="p-4 pb-2">
            <CardDescription className="text-xs text-zinc-400">RBAC Gated</CardDescription>
            <CardTitle className="text-2xl font-bold text-emerald-400">100%</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 text-xs text-zinc-500">Strict Permission Guards</CardContent>
        </Card>
        <Card className="border-zinc-800 bg-zinc-950/60 backdrop-blur">
          <CardHeader className="p-4 pb-2">
            <CardDescription className="text-xs text-zinc-400">Audit Logs Persisted</CardDescription>
            <CardTitle className="text-2xl font-bold text-purple-400">{auditLogs.length}</CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0 text-xs text-zinc-500">Immutable Execution History</CardContent>
        </Card>
      </div>

      {activeTab === "catalog" ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Left Column: Tool Catalog & Search (5 cols) */}
          <div className="space-y-4 lg:col-span-5">
            {/* Filter and Search Bar */}
            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Search tools or capabilities..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-md border border-zinc-800 bg-zinc-900/80 py-2 pl-9 pr-4 text-sm text-zinc-200 placeholder-zinc-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Category Pills */}
            <div className="flex flex-wrap gap-1.5">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={`rounded-full px-2.5 py-1 text-xs font-medium transition ${
                    categoryFilter === cat
                      ? "bg-indigo-600 text-white"
                      : "bg-zinc-800/80 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Tools List */}
            <div className="space-y-2.5">
              {filteredTools.map((tool) => {
                const isSelected = selectedTool?.name === tool.name;
                return (
                  <div
                    key={tool.name}
                    onClick={() => handleSelectTool(tool)}
                    className={`group cursor-pointer rounded-lg border p-3.5 transition ${
                      isSelected
                        ? "border-indigo-500/60 bg-indigo-950/20 shadow-lg shadow-indigo-500/5"
                        : "border-zinc-800/80 bg-zinc-900/40 hover:border-zinc-700 hover:bg-zinc-900/70"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <div className="rounded p-1.5 bg-zinc-800/80">
                          {CATEGORY_ICONS[tool.category] || <Wrench className="h-4 w-4 text-zinc-400" />}
                        </div>
                        <div>
                          <h3 className="text-sm font-semibold text-zinc-200 group-hover:text-white font-mono">
                            {tool.name}
                          </h3>
                          <span className="text-[11px] text-zinc-400">{tool.category}</span>
                        </div>
                      </div>
                      <Badge variant="secondary" className="border-zinc-700 text-[10px] text-zinc-400">
                        {tool.required_permission}
                      </Badge>
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-zinc-400 line-clamp-2">
                      {tool.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Interactive Tool Playground & Inspector (7 cols) */}
          <div className="space-y-4 lg:col-span-7">
            {selectedTool ? (
              <Card className="border-zinc-800 bg-zinc-950/60 backdrop-blur">
                <CardHeader className="pb-3 border-b border-zinc-800/80">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-lg font-mono text-white flex items-center gap-2">
                          <Terminal className="h-5 w-5 text-indigo-400" />
                          {selectedTool.name}
                        </CardTitle>
                        <Badge variant="purple" className="border-indigo-500/40 text-indigo-400">
                          {selectedTool.category}
                        </Badge>
                      </div>
                      <CardDescription className="mt-1 text-xs text-zinc-400">
                        {selectedTool.description}
                      </CardDescription>
                    </div>
                    <Button
                      size="sm"
                      onClick={handleExecuteTool}
                      disabled={executing}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 font-medium"
                    >
                      {executing ? (
                        <>
                          <RefreshCw className="h-4 w-4 animate-spin" />
                          Executing...
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 fill-white" />
                          Execute Tool
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Metadata Tags */}
                  <div className="flex flex-wrap gap-2 pt-2">
                    <span className="inline-flex items-center gap-1 text-[11px] text-zinc-400 bg-zinc-900 border border-zinc-800 rounded px-2 py-0.5">
                      <Shield className="h-3 w-3 text-emerald-400" />
                      Requires: <span className="font-mono text-zinc-300">{selectedTool.required_permission}</span>
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] text-zinc-400 bg-zinc-900 border border-zinc-800 rounded px-2 py-0.5">
                      <Activity className="h-3 w-3 text-amber-400" />
                      Rate Limit: <span className="font-mono text-zinc-300">{selectedTool.rate_limit_per_minute}/min</span>
                    </span>
                    {selectedTool.requires_approval && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-amber-400 bg-amber-950/30 border border-amber-800/40 rounded px-2 py-0.5">
                        <ShieldAlert className="h-3 w-3" />
                        Human Approval Mandated
                      </span>
                    )}
                  </div>
                </CardHeader>

                <CardContent className="space-y-4 pt-4">
                  {/* JSON Arguments Editor */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                        <Code2 className="h-3.5 w-3.5 text-zinc-400" />
                        Input Arguments (JSON)
                      </label>
                      <button
                        onClick={() => {
                          const def = DEFAULT_ARGUMENTS[selectedTool.name] || {};
                          setArgumentsJson(JSON.stringify(def, null, 2));
                        }}
                        className="text-[11px] text-indigo-400 hover:text-indigo-300"
                      >
                        Reset Defaults
                      </button>
                    </div>
                    <textarea
                      rows={5}
                      value={argumentsJson}
                      onChange={(e) => setArgumentsJson(e.target.value)}
                      className="w-full rounded-md border border-zinc-800 bg-zinc-900/90 p-3 font-mono text-xs text-zinc-200 placeholder-zinc-600 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>

                  {/* Schema Parameters Quick Reference */}
                  <div>
                    <h4 className="text-xs font-semibold text-zinc-400 mb-1.5">Expected Parameters:</h4>
                    <div className="rounded-md border border-zinc-800/80 bg-zinc-900/40 p-2.5 space-y-1">
                      {Object.entries(selectedTool.inputSchema.properties || {}).map(([key, prop]: [string, any]) => (
                        <div key={key} className="flex items-center justify-between text-xs font-mono">
                          <span className="text-indigo-400">
                            {key}
                            {selectedTool.inputSchema.required?.includes(key) && (
                              <span className="text-red-400 ml-0.5">*</span>
                            )}
                          </span>
                          <span className="text-zinc-500 text-[11px]">
                            {prop.type || "any"} {prop.description ? `— ${prop.description}` : ""}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Execution Results Viewer */}
                  {executionResult && (
                    <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-900/80 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {executionResult.status === "SUCCESS" ? (
                            <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 flex items-center gap-1">
                              <CheckCircle2 className="h-3 w-3" />
                              SUCCESS
                            </Badge>
                          ) : (
                            <Badge className="bg-red-500/20 text-red-400 border-red-500/30 flex items-center gap-1">
                              <AlertCircle className="h-3 w-3" />
                              {executionResult.status}
                            </Badge>
                          )}
                          <span className="text-xs text-zinc-400 font-mono">
                            {executionResult.execution_time_ms} ms
                          </span>
                        </div>
                        {executionResult.audit_log_id && (
                          <span className="text-[10px] text-zinc-500 font-mono">
                            Audit ID: {executionResult.audit_log_id.slice(0, 8)}...
                          </span>
                        )}
                      </div>

                      {executionResult.error ? (
                        <div className="rounded p-3 bg-red-950/30 border border-red-800/30 text-xs text-red-300 font-mono">
                          {executionResult.error}
                        </div>
                      ) : (
                        <div className="max-h-72 overflow-y-auto rounded bg-zinc-950 p-3 font-mono text-xs text-zinc-300">
                          <pre>{JSON.stringify(executionResult.output, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <div className="rounded-lg border border-dashed border-zinc-800 p-12 text-center text-zinc-500">
                Select a tool from the catalog to inspect schema and execute.
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Audit Trail Table */
        <Card className="border-zinc-800 bg-zinc-950/60 backdrop-blur">
          <CardHeader>
            <CardTitle className="text-lg text-white flex items-center gap-2">
              <Clock className="h-5 w-5 text-indigo-400" />
              Immutable Tool Execution Audit Trail
            </CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Complete audit log capturing all tool invocations, duration, caller identity, and validation verdicts.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {auditLogs.length === 0 ? (
              <div className="py-8 text-center text-xs text-zinc-500">
                No tool execution audit records recorded yet. Run a tool in the Studio to generate logs.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-zinc-300">
                  <thead className="border-b border-zinc-800 bg-zinc-900/50 text-[11px] text-zinc-400">
                    <tr>
                      <th className="py-2.5 px-3">Timestamp</th>
                      <th className="py-2.5 px-3">Tool</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Execution Time</th>
                      <th className="py-2.5 px-3">User ID</th>
                      <th className="py-2.5 px-3">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60 font-mono">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-zinc-900/40">
                        <td className="py-2.5 px-3 text-zinc-400">
                          {new Date(log.created_at).toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-white">
                          {log.tool_name}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${
                              log.status === "SUCCESS"
                                ? "bg-emerald-500/20 text-emerald-400"
                                : log.status === "BLOCKED"
                                ? "bg-amber-500/20 text-amber-400"
                                : "bg-red-500/20 text-red-400"
                            }`}
                          >
                            {log.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-zinc-400">
                          {log.details?.execution_time_ms ? `${log.details.execution_time_ms} ms` : "—"}
                        </td>
                        <td className="py-2.5 px-3 text-zinc-500 text-[11px]">
                          {log.user_id ? log.user_id.slice(0, 8) + "..." : "System"}
                        </td>
                        <td className="py-2.5 px-3 text-zinc-400 text-[11px] max-w-xs truncate">
                          {JSON.stringify(log.details?.arguments || log.details || {})}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
