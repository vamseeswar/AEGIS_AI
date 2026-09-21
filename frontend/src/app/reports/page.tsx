"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  FileCheck2,
  Download,
  Plus,
  Eye,
  Trash2,
  RefreshCw,
  Search,
  Sparkles,
  FileText,
  Clock,
  Layers,
  CheckCircle2,
  BarChart3,
  X,
  Printer,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { formatDate } from "@/lib/utils";
import { api } from "@/lib/api";

interface ReportItem {
  id: string;
  organization_id: string;
  user_id: string;
  agent_run_id?: string | null;
  title: string;
  summary?: string | null;
  format: "PDF" | "MARKDOWN" | string;
  content_markdown: string;
  pdf_storage_path?: string | null;
  charts_data?: Array<Record<string, unknown>> | null;
  metrics_data?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

const TEMPLATE_PRESETS = [
  {
    name: "Executive Operations & Agent Fleet Review",
    summary: "Comprehensive synthesis of multi-agent task execution, tool latencies, and autonomous workflows.",
    markdown: `# Executive Operations & Agent Fleet Review

## 1. Operational Overview
The autonomous agent fleet processed **4,820 operations** with an aggregate success rate of **99.4%**. No critical tool execution safety incidents were detected.

## 2. Agent Fleet Highlights
- **Supervisor Agent**: Dispatched 142 complex sub-tasks with a 380ms routing median.
- **SQL Analyst Agent**: Safely executed 812 queries with AST safety rails blocking 3 illegal DROP attempts.
- **ML Engine**: Delivered recursive 30-day forecasting with 92.4% validation accuracy.

## 3. Human-in-the-Loop Interventions
- 12 high-risk wire transfers authorized following dual-key supervisor review.
- 1 unauthorized broadcast outreach blocked.

## 4. Strategic Recommendations
- Expand vector index caching to reduce cold-start chunk retrieval latency.
- Scale SQL query timeout threshold from 5,000ms to 7,500ms for heavy financial end-of-month aggregations.`,
    metrics: {
      total_operations: 4820,
      fleet_uptime: "99.98%",
      mean_task_latency_ms: 412,
      accuracy_rate: "99.4%",
    },
  },
  {
    name: "Cybersecurity & Multi-Tenant Access Audit",
    summary: "Quarterly ISO27001 compliance audit confirming strict tenant boundary separation and cryptographic access verification.",
    markdown: `# Cybersecurity & Multi-Tenant Access Audit

## 1. Compliance Certification
Tenant isolation verification passed across 100% of tested database queries, vector similarity lookups, and file storage artifacts.

## 2. Authentication Integrity
- **Total Logins**: 18,940 authentication events validated with bcrypt/Argon2.
- **Blocked Attempts**: 47 anomalous brute-force attempts neutralized at API gateway.
- **RBAC Enforcement**: 0 privilege escalation vulnerabilities discovered.

## 3. Storage Boundary Checks
- Document vault storage scoped strictly to \`storage/{tenant_id}/*\` paths.
- Audit logs cryptographically linked and immutable.`,
    metrics: {
      audited_tenants: 84,
      violation_count: 0,
      auth_events_scanned: 18940,
      compliance_score: "100%",
    },
  },
  {
    name: "Financial Forecast & Anomaly Detection Brief",
    summary: "Machine learning time series projection with Isolation Forest residual outlier detection.",
    markdown: `# Financial Forecast & Anomaly Detection Brief

## 1. 30-Day Forward Revenue Projection
Machine learning forecasting models trained on historical transactional data project **$1,420,000** in forward quarterly revenue.

| Metric | Target | Projected | Variance |
|---|---|---|---|
| Enterprise Subscriptions | $950,000 | $985,000 | +3.6% |
| API Usage Overage | $320,000 | $345,000 | +7.8% |
| Professional Services | $120,000 | $118,000 | -1.6% |

## 2. Anomaly Detection Findings
Isolation Forest identified **2 transient invoice spikes** flagged for manual accounting audit. Both invoices reconciled with enterprise contract renegotiations.`,
    metrics: {
      projected_revenue: "$1.42M",
      forecast_confidence: "95%",
      holdout_rmse: 142.5,
      anomalies_flagged: 2,
    },
  },
];

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [formatFilter, setFormatFilter] = useState<string>("ALL");
  const [selectedReport, setSelectedReport] = useState<ReportItem | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // New report form state
  const [formTitle, setFormTitle] = useState<string>("");
  const [formSummary, setFormSummary] = useState<string>("");
  const [formMarkdown, setFormMarkdown] = useState<string>("");
  const [formMetrics, setFormMetrics] = useState<string>("");
  const [formFormat, setFormFormat] = useState<string>("PDF");

  const fetchReports = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await api.get<{ reports: ReportItem[]; total: number }>("/api/v1/reports");
      if (response && response.reports) {
        setReports(response.reports);
      }
    } catch {
      // Keep empty or existing
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleApplyPreset = (preset: (typeof TEMPLATE_PRESETS)[0]) => {
    setFormTitle(preset.name);
    setFormSummary(preset.summary);
    setFormMarkdown(preset.markdown);
    setFormMetrics(JSON.stringify(preset.metrics, null, 2));
  };

  const handleCreateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim() || !formMarkdown.trim()) return;

    setIsSubmitting(true);
    try {
      let parsedMetrics: Record<string, unknown> | undefined;
      if (formMetrics.trim()) {
        try {
          parsedMetrics = JSON.parse(formMetrics);
        } catch {
          // ignore parsing error
        }
      }

      await api.post<ReportItem>("/api/v1/reports", {
        title: formTitle,
        summary: formSummary || undefined,
        content_markdown: formMarkdown,
        format: formFormat,
        metrics_data: parsedMetrics,
      });

      setIsCreateModalOpen(false);
      setFormTitle("");
      setFormSummary("");
      setFormMarkdown("");
      setFormMetrics("");
      await fetchReports();
    } catch (err) {
      console.error("Failed to create report:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownloadPdf = async (reportId: string, title: string) => {
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("aegis_access_token") : null;
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
      const res = await fetch(`${apiBase}/api/v1/reports/${reportId}/pdf`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) throw new Error("Failed to download PDF");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title.toLowerCase().replace(/[^a-z0-9]/g, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Error downloading PDF:", err);
    }
  };

  const handleDeleteReport = async (reportId: string) => {
    if (!confirm("Are you sure you want to permanently delete this executive report?")) return;
    try {
      await api.delete(`/api/v1/reports/${reportId}`);
      if (selectedReport?.id === reportId) {
        setSelectedReport(null);
      }
      await fetchReports();
    } catch (err) {
      console.error("Failed to delete report:", err);
    }
  };

  const filteredReports = useMemo(() => {
    return reports.filter((rep) => {
      const matchesSearch =
        rep.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (rep.summary && rep.summary.toLowerCase().includes(searchQuery.toLowerCase())) ||
        rep.id.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesFormat = formatFilter === "ALL" || rep.format.toUpperCase() === formatFilter.toUpperCase();
      return matchesSearch && matchesFormat;
    });
  }, [reports, searchQuery, formatFilter]);

  const metrics = useMemo(() => {
    return {
      total: reports.length,
      withPdf: reports.filter((r) => r.format === "PDF" || r.pdf_storage_path).length,
      markdownOnly: reports.filter((r) => r.format === "MARKDOWN").length,
    };
  }, [reports]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-teal-500/10 rounded-lg border border-teal-500/20 text-teal-400">
              <FileCheck2 className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 flex items-center space-x-2">
                <span>Executive Reports Studio</span>
                <Badge variant="teal">ReportLab 4.2</Badge>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Publication-grade executive intelligence briefings compiled with ReportLab typography, KPI grids, and downloadable PDFs.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchReports}
            disabled={isLoading}
            className="border-slate-700 hover:bg-slate-800 text-slate-300"
          >
            <RefreshCw className={`h-4 w-4 mr-1.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              handleApplyPreset(TEMPLATE_PRESETS[0]);
              setIsCreateModalOpen(true);
            }}
            className="bg-teal-600 hover:bg-teal-500 text-white space-x-1.5 font-semibold shadow-md shadow-teal-950"
          >
            <Plus className="h-4 w-4" />
            <span>Generate Executive Report</span>
          </Button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs font-medium text-slate-400">Total Briefings</p>
          <p className="text-2xl font-bold text-slate-100 mt-1">{metrics.total}</p>
        </Card>
        <Card className="border-teal-500/20 bg-teal-950/10 p-4">
          <p className="text-xs font-medium text-teal-400">PDF Artifacts</p>
          <p className="text-2xl font-bold text-teal-300 mt-1">{metrics.withPdf}</p>
        </Card>
        <Card className="border-cyan-500/20 bg-cyan-950/10 p-4">
          <p className="text-xs font-medium text-cyan-400">Markdown Briefs</p>
          <p className="text-2xl font-bold text-cyan-300 mt-1">{metrics.markdownOnly}</p>
        </Card>
        <Card className="border-purple-500/20 bg-purple-950/10 p-4">
          <p className="text-xs font-medium text-purple-400">Engine Palette</p>
          <p className="text-sm font-semibold text-purple-300 mt-2">Executive Slate / Teal</p>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/70 p-3 rounded-xl border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search reports by title or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/50"
          />
        </div>
        <div className="flex items-center space-x-1.5 w-full sm:w-auto">
          {["ALL", "PDF", "MARKDOWN"].map((tab) => (
            <button
              key={tab}
              onClick={() => setFormatFilter(tab)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
                formatFilter === tab
                  ? "bg-teal-600 text-white font-semibold"
                  : "bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              {tab === "ALL" ? "All Formats" : tab}
            </button>
          ))}
        </div>
      </div>

      {/* Reports Table */}
      <Card className="border-slate-800 bg-slate-900/60">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Compiled Executive Archives</CardTitle>
          <CardDescription className="text-xs">
            Downloadable executive briefs compiled from agent findings, SQL telemetry, and RAG grounding.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {filteredReports.length === 0 ? (
            <div className="text-center py-12 px-4">
              <FileCheck2 className="h-12 w-12 mx-auto text-slate-600 mb-3" />
              <p className="text-slate-300 font-medium">No executive reports found</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Generate your first executive briefing or choose one of our templates to compile a styled ReportLab PDF.
              </p>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  handleApplyPreset(TEMPLATE_PRESETS[0]);
                  setIsCreateModalOpen(true);
                }}
                className="mt-4 bg-teal-600 hover:bg-teal-500 text-xs"
              >
                Compile First Report
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-transparent">
                  <TableHead className="text-xs text-slate-400">Report Title</TableHead>
                  <TableHead className="text-xs text-slate-400">Format</TableHead>
                  <TableHead className="text-xs text-slate-400">Summary</TableHead>
                  <TableHead className="text-xs text-slate-400">Date Compiled</TableHead>
                  <TableHead className="text-xs text-slate-400 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredReports.map((rep) => (
                  <TableRow key={rep.id} className="border-slate-800/60 hover:bg-slate-800/40 transition-colors">
                    <TableCell className="font-medium text-slate-200">
                      <div className="flex items-center space-x-2">
                        <FileText className="h-4 w-4 text-teal-400 flex-shrink-0" />
                        <div>
                          <p className="text-sm font-semibold">{rep.title}</p>
                          <p className="font-mono text-[10px] text-slate-500">{rep.id}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={rep.format === "PDF" ? "teal" : "secondary"} className="text-[10px]">
                        {rep.format}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-slate-400 max-w-xs truncate">
                      {rep.summary || "No summary provided."}
                    </TableCell>
                    <TableCell className="text-xs text-slate-400 whitespace-nowrap">
                      {formatDate(rep.created_at)}
                    </TableCell>
                    <TableCell className="text-right whitespace-nowrap space-x-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setSelectedReport(rep)}
                        className="h-8 w-8 text-cyan-400 hover:bg-cyan-950/40"
                        title="View Report Content"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDownloadPdf(rep.id, rep.title)}
                        className="h-8 w-8 text-teal-400 hover:bg-teal-950/40"
                        title="Download PDF"
                      >
                        <Download className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteReport(rep.id)}
                        className="h-8 w-8 text-rose-400 hover:bg-rose-950/40"
                        title="Delete Report"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* View Report Detail Modal */}
      {selectedReport && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <FileCheck2 className="h-5 w-5 text-teal-400" />
                <h3 className="text-base font-semibold text-slate-100 truncate">{selectedReport.title}</h3>
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleDownloadPdf(selectedReport.id, selectedReport.title)}
                  className="bg-teal-600 hover:bg-teal-500 text-white text-xs space-x-1"
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>Download PDF</span>
                </Button>
                <button
                  onClick={() => setSelectedReport(null)}
                  className="p-1 rounded-md text-slate-400 hover:text-slate-200"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 text-slate-200 text-xs leading-relaxed">
              {selectedReport.summary && (
                <div className="bg-slate-950/70 p-3.5 rounded-lg border-l-4 border-teal-500 text-slate-300">
                  <span className="font-semibold text-teal-400">Executive Summary: </span>
                  {selectedReport.summary}
                </div>
              )}

              {selectedReport.metrics_data && Object.keys(selectedReport.metrics_data).length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
                  {Object.entries(selectedReport.metrics_data).map(([k, v]) => (
                    <div key={k} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-center">
                      <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
                        {k.replace(/_/g, " ")}
                      </p>
                      <p className="text-base font-bold text-slate-100 mt-0.5">{String(v)}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 font-mono text-[11px] whitespace-pre-wrap leading-relaxed text-slate-300">
                {selectedReport.content_markdown}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Generate Report Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Sparkles className="h-5 w-5 text-teal-400" />
                <h3 className="text-base font-semibold text-slate-100">Compile New Executive Briefing</h3>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateReport} className="p-6 overflow-y-auto space-y-4">
              {/* Presets Bar */}
              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1.5">
                  Load Template Preset:
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {TEMPLATE_PRESETS.map((preset) => (
                    <button
                      key={preset.name}
                      type="button"
                      onClick={() => handleApplyPreset(preset)}
                      className="px-2.5 py-1 text-[11px] bg-slate-800 text-teal-300 rounded hover:bg-slate-700 border border-slate-700"
                    >
                      {preset.name}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Report Title *</label>
                <input
                  type="text"
                  required
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="e.g., Q3 Executive Operations & Autonomous Agent Review"
                  className="w-full text-xs bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-teal-500/50"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Executive Summary</label>
                <textarea
                  rows={2}
                  value={formSummary}
                  onChange={(e) => setFormSummary(e.target.value)}
                  placeholder="Brief synopsis highlighting primary conclusions..."
                  className="w-full text-xs bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-teal-500/50"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">
                  Report Body (Markdown supported) *
                </label>
                <textarea
                  rows={8}
                  required
                  value={formMarkdown}
                  onChange={(e) => setFormMarkdown(e.target.value)}
                  placeholder="# Section Heading&#10;&#10;Key findings and tabular analysis..."
                  className="w-full text-xs font-mono bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-teal-500/50"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">
                  Key Metrics JSON (optional)
                </label>
                <textarea
                  rows={3}
                  value={formMetrics}
                  onChange={(e) => setFormMetrics(e.target.value)}
                  placeholder='{"total_revenue": 1420000, "growth_rate": "18.4%"}'
                  className="w-full text-xs font-mono bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-teal-500/50"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsCreateModalOpen(false)}
                  disabled={isSubmitting}
                  className="text-slate-400 border-slate-700 text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isSubmitting}
                  className="bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold"
                >
                  {isSubmitting ? "Compiling PDF..." : "Compile & Save Report"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
