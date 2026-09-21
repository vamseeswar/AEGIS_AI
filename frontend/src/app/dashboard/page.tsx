"use client";

import React from "react";
import Link from "next/link";
import {
  Bot,
  FileText,
  Database,
  CheckSquare,
  ArrowUpRight,
  TrendingUp,
  Cpu,
  ShieldCheck,
  Zap,
  Clock,
  Sparkles,
  MessageSquare,
  BarChart2,
  FileSpreadsheet,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

// Mock operational telemetry data for dashboard visualization
const throughputData = [
  { time: "00:00", tokens: 12000, queries: 45, latency: 180 },
  { time: "04:00", tokens: 8000, queries: 20, latency: 150 },
  { time: "08:00", tokens: 35000, queries: 140, latency: 220 },
  { time: "12:00", tokens: 68000, queries: 290, latency: 240 },
  { time: "16:00", tokens: 82000, queries: 380, latency: 260 },
  { time: "20:00", tokens: 49000, queries: 190, latency: 195 },
  { time: "23:59", tokens: 28000, queries: 95, latency: 170 },
];

const latencyByToolData = [
  { tool: "Vector Search", ms: 42 },
  { tool: "SQL AST Check", ms: 14 },
  { tool: "LLM Synthesizer", ms: 380 },
  { tool: "ML Forecast", ms: 125 },
  { tool: "PDF Parsing", ms: 210 },
];

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900/90 via-slate-900/50 to-slate-950 backdrop-blur-xl shadow-2xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
              Welcome back, {user?.full_name || "Operations Lead"}
            </h1>
            <Badge variant="teal">Online</Badge>
          </div>
          <p className="text-xs text-slate-400">
            Autonomous multi-agent orchestration active for{" "}
            <span className="text-teal-400 font-semibold">
              {user?.organization_name || "AEGIS Global Operations"}
            </span>
            . All safety rails and tenant boundaries enforced.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Link href="/chat">
            <Button variant="primary" className="space-x-1.5 shadow-lg shadow-teal-500/20">
              <MessageSquare className="h-4 w-4" />
              <span>Launch AI Chat</span>
            </Button>
          </Link>
          <Link href="/agents">
            <Button variant="outline" className="space-x-1.5">
              <Bot className="h-4 w-4 text-teal-400" />
              <span>View Agents</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Active Agents */}
        <Card className="border-slate-800/80 bg-slate-900/60 hover:border-teal-500/30 transition-all group">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Autonomous Agents
              </span>
              <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20 group-hover:scale-110 transition-transform">
                <Bot className="h-5 w-5" />
              </div>
            </div>
            <div className="mt-4">
              <div className="text-2xl font-bold text-slate-100">8 Deployed</div>
              <div className="flex items-center space-x-1.5 mt-1 text-xs text-emerald-400 font-medium">
                <TrendingUp className="h-3.5 w-3.5" />
                <span>LangGraph State Graph Active</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Indexed Documents */}
        <Card className="border-slate-800/80 bg-slate-900/60 hover:border-cyan-500/30 transition-all group">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Knowledge Documents
              </span>
              <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 group-hover:scale-110 transition-transform">
                <FileText className="h-5 w-5" />
              </div>
            </div>
            <div className="mt-4">
              <div className="text-2xl font-bold text-slate-100">142 Indexed</div>
              <div className="flex items-center space-x-1.5 mt-1 text-xs text-cyan-400 font-medium">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>pgvector Cosine Similarity</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Card 3: SQL Analyst Queries */}
        <Card className="border-slate-800/80 bg-slate-900/60 hover:border-purple-500/30 transition-all group">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                SQL Queries Verified
              </span>
              <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 group-hover:scale-110 transition-transform">
                <Database className="h-5 w-5" />
              </div>
            </div>
            <div className="mt-4">
              <div className="text-2xl font-bold text-slate-100">1,842 Executed</div>
              <div className="flex items-center space-x-1.5 mt-1 text-xs text-purple-400 font-medium">
                <Zap className="h-3.5 w-3.5" />
                <span>100% AST Safety Guarded</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Card 4: Pending Approvals */}
        <Card className="border-slate-800/80 bg-slate-900/60 hover:border-amber-500/30 transition-all group">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                HITL Approvals
              </span>
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 group-hover:scale-110 transition-transform">
                <CheckSquare className="h-5 w-5" />
              </div>
            </div>
            <div className="mt-4">
              <div className="text-2xl font-bold text-slate-100">3 Pending</div>
              <div className="flex items-center space-x-1.5 mt-1 text-xs text-amber-400 font-medium">
                <Clock className="h-3.5 w-3.5" />
                <span>Human-in-the-loop Guard</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Analytics & Throughput Visualization */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart */}
        <Card className="lg:col-span-2 border-slate-800/80 bg-slate-900/60">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-base">Operations Throughput & Agent Volume</CardTitle>
              <CardDescription>
                Tokens processed and autonomous multi-agent tool calls across 24h.
              </CardDescription>
            </div>
            <Badge variant="cyan">Live Telemetry</Badge>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={throughputData}>
                  <defs>
                    <linearGradient id="tokenGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#14b8a6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: "8px",
                      color: "#f8fafc",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="tokens"
                    name="Tokens Ingested"
                    stroke="#14b8a6"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#tokenGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Latency by Subsystem */}
        <Card className="border-slate-800/80 bg-slate-900/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Latency by Subsystem</CardTitle>
            <CardDescription>Average response execution time (ms).</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={latencyByToolData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                  <XAxis type="number" stroke="#64748b" fontSize={10} />
                  <YAxis
                    dataKey="tool"
                    type="category"
                    stroke="#94a3b8"
                    fontSize={11}
                    width={95}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="ms" name="Latency (ms)" fill="#06b6d4" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Agents Status & Recent Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Agents Grid */}
        <Card className="border-slate-800/80 bg-slate-900/60">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base">LangGraph Agent Fleet</CardTitle>
              <CardDescription>Specialized operational agents in runtime state.</CardDescription>
            </div>
            <Link href="/agents" className="text-xs text-teal-400 hover:underline flex items-center">
              <span>View fleet</span>
              <ArrowUpRight className="h-3 w-3 ml-0.5" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              {
                name: "Supervisor Agent",
                role: "Graph Orchestrator & Dispatcher",
                status: "Monitoring",
                variant: "teal" as const,
              },
              {
                name: "RAG Research Agent",
                role: "pgvector Semantic Chunk Retriever",
                status: "Query Ingestion",
                variant: "cyan" as const,
              },
              {
                name: "SQL Analyst Agent",
                role: "AST Guarded NL-to-SQL Compiler",
                status: "Idle",
                variant: "secondary" as const,
              },
              {
                name: "ML Forecasting Agent",
                role: "Ridge Regression & Isolation Forest",
                status: "Training Model",
                variant: "purple" as const,
              },
            ].map((agent) => (
              <div
                key={agent.name}
                className="flex items-center justify-between p-3 rounded-lg border border-slate-800/70 bg-slate-950/40 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-slate-800 text-teal-400">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-200">{agent.name}</h4>
                    <p className="text-[11px] text-slate-500">{agent.role}</p>
                  </div>
                </div>
                <Badge variant={agent.variant}>{agent.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Recent Audit Trail */}
        <Card className="border-slate-800/80 bg-slate-900/60">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base">Security & Audit Trail</CardTitle>
              <CardDescription>Real-time tenant operation log.</CardDescription>
            </div>
            <Link href="/admin" className="text-xs text-teal-400 hover:underline flex items-center">
              <span>Full audit</span>
              <ArrowUpRight className="h-3 w-3 ml-0.5" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              {
                event: "JWT Session Authorized",
                actor: user?.email || "admin@aegis.ai",
                time: "2 mins ago",
                badge: "AUTH_SUCCESS",
                variant: "success" as const,
              },
              {
                event: "AST Safety Check: Permitted SELECT",
                actor: "SQL Analyst Agent",
                time: "14 mins ago",
                badge: "SQL_SAFE",
                variant: "cyan" as const,
              },
              {
                event: "Document Chunking & Embedding Complete",
                actor: "RAG Engine",
                time: "42 mins ago",
                badge: "RAG_INDEXED",
                variant: "purple" as const,
              },
              {
                event: "HITL Action Queued: Approval #1042",
                actor: "Validation Agent",
                time: "1 hour ago",
                badge: "PENDING_APPROVAL",
                variant: "warning" as const,
              },
            ].map((log, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-lg border border-slate-800/70 bg-slate-950/40"
              >
                <div className="space-y-0.5">
                  <p className="text-xs font-medium text-slate-200">{log.event}</p>
                  <p className="text-[10px] text-slate-500">
                    {log.actor} • {log.time}
                  </p>
                </div>
                <Badge variant={log.variant}>{log.badge}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Quick Launchpad Action Bar */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40">
        <h3 className="text-sm font-semibold text-slate-200 mb-4 uppercase tracking-wider">
          Quick Operational Triggers
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Link href="/chat">
            <button className="w-full p-4 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-teal-500/40 hover:bg-slate-900 transition-all flex flex-col items-center justify-center text-center group">
              <MessageSquare className="h-6 w-6 text-teal-400 group-hover:scale-110 transition-transform mb-2" />
              <span className="text-xs font-semibold text-slate-200">Start AI Chat</span>
              <span className="text-[10px] text-slate-500 mt-0.5">With Citations</span>
            </button>
          </Link>
          <Link href="/documents">
            <button className="w-full p-4 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-cyan-500/40 hover:bg-slate-900 transition-all flex flex-col items-center justify-center text-center group">
              <FileText className="h-6 w-6 text-cyan-400 group-hover:scale-110 transition-transform mb-2" />
              <span className="text-xs font-semibold text-slate-200">Ingest Document</span>
              <span className="text-[10px] text-slate-500 mt-0.5">PDF, DOCX, CSV</span>
            </button>
          </Link>
          <Link href="/analytics">
            <button className="w-full p-4 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-purple-500/40 hover:bg-slate-900 transition-all flex flex-col items-center justify-center text-center group">
              <Database className="h-6 w-6 text-purple-400 group-hover:scale-110 transition-transform mb-2" />
              <span className="text-xs font-semibold text-slate-200">Query SQL</span>
              <span className="text-[10px] text-slate-500 mt-0.5">Natural Language</span>
            </button>
          </Link>
          <Link href="/ml">
            <button className="w-full p-4 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-emerald-500/40 hover:bg-slate-900 transition-all flex flex-col items-center justify-center text-center group">
              <TrendingUp className="h-6 w-6 text-emerald-400 group-hover:scale-110 transition-transform mb-2" />
              <span className="text-xs font-semibold text-slate-200">Train ML Model</span>
              <span className="text-[10px] text-slate-500 mt-0.5">Forecast & Anomaly</span>
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}
