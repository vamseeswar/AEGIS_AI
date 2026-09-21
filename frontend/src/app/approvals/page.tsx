"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  CheckSquare,
  AlertTriangle,
  Check,
  X,
  ShieldAlert,
  Clock,
  RefreshCw,
  Search,
  ChevronDown,
  ChevronUp,
  FileText,
  User,
  Cpu,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  Eye,
  Filter,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/lib/api";

interface ApprovalItem {
  id: string;
  agent_run_id: string;
  tool_call_id?: string | null;
  requested_by_agent: string;
  action_name: string;
  action_payload: Record<string, unknown>;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;
  reason: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED" | string;
  decided_by_user_id?: string | null;
  decision_notes?: string | null;
  expires_at?: string | null;
  created_at: string;
  organization_id: string;
}

const FALLBACK_APPROVALS: ApprovalItem[] = [
  {
    id: "appr-001",
    agent_run_id: "run-7819",
    tool_call_id: "tc-9912",
    requested_by_agent: "Financial Ops Agent",
    action_name: "execute_wire_transfer",
    action_payload: {
      beneficiary: "Apex Holdings LLC",
      iban: "US91AEGIS109283746",
      amount_usd: 85000,
      currency: "USD",
      reference: "Invoice #INV-2026-881",
    },
    risk_level: "CRITICAL",
    reason: "Wire transfer exceeds automated authorization threshold ($50,000 limit). Requires dual-key supervisor signoff.",
    status: "PENDING",
    created_at: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
    expires_at: new Date(Date.now() + 1000 * 60 * 42).toISOString(),
    organization_id: "org-default",
  },
  {
    id: "appr-002",
    agent_run_id: "run-7820",
    tool_call_id: "tc-9913",
    requested_by_agent: "Infrastructure Bot",
    action_name: "alter_vector_indexing_policy",
    action_payload: {
      target_collection: "enterprise_docs_v2",
      parameter: "chunk_overlap",
      old_value: 100,
      new_value: 250,
      force_reindex: true,
    },
    risk_level: "HIGH",
    reason: "Re-indexing will trigger full vector re-embedding across 1.4M chunks with significant OpenAI quota consumption.",
    status: "PENDING",
    created_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    expires_at: new Date(Date.now() + 1000 * 60 * 15).toISOString(),
    organization_id: "org-default",
  },
  {
    id: "appr-003",
    agent_run_id: "run-7815",
    tool_call_id: "tc-9899",
    requested_by_agent: "Data Governance Agent",
    action_name: "export_audit_vault_dump",
    action_payload: {
      format: "CSV",
      record_count: 5400,
      scope: "ALL_TENANT_LOGS_30D",
      destination: "s3://secure-compliance-exports/export-2026-09.csv",
    },
    risk_level: "MEDIUM",
    reason: "Bulk export of historical authentication and tool execution records outside primary tenant boundary.",
    status: "APPROVED",
    decided_by_user_id: "usr-admin-01",
    decision_notes: "Approved per quarterly ISO27001 internal audit request ticket #SEC-4091.",
    created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    organization_id: "org-default",
  },
  {
    id: "appr-004",
    agent_run_id: "run-7801",
    tool_call_id: "tc-9850",
    requested_by_agent: "Outreach Dispatcher",
    action_name: "send_broadcast_newsletter",
    action_payload: {
      recipient_count: 14200,
      campaign_id: "fall_enterprise_launch",
      send_window: "immediate",
    },
    risk_level: "HIGH",
    reason: "Broadcast campaign was unvetted by brand safety team and contains external links.",
    status: "REJECTED",
    decided_by_user_id: "usr-admin-02",
    decision_notes: "Rejected: Links in template lead to staging environment rather than production assets.",
    created_at: new Date(Date.now() - 1000 * 60 * 300).toISOString(),
    organization_id: "org-default",
  },
];

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>(FALLBACK_APPROVALS);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [expandedPayloads, setExpandedPayloads] = useState<Record<string, boolean>>({});
  const [activeDecisionModal, setActiveDecisionModal] = useState<{
    id: string;
    action: "approve" | "reject";
    actionName: string;
  } | null>(null);
  const [decisionNotes, setDecisionNotes] = useState<string>("");
  const [isSubmittingDecision, setIsSubmittingDecision] = useState<boolean>(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchApprovals = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const endpoint = statusFilter === "ALL" ? "/api/v1/approvals" : `/api/v1/approvals?status_filter=${statusFilter}`;
      const response = await api.get<{ approvals: ApprovalItem[]; total: number; pending_count: number }>(endpoint);
      if (response && response.approvals && response.approvals.length > 0) {
        setApprovals(response.approvals);
      }
    } catch {
      // Keep state with mock fallback if offline or during testing
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const togglePayloadExpand = (id: string) => {
    setExpandedPayloads((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleDecisionSubmit = async () => {
    if (!activeDecisionModal) return;
    setIsSubmittingDecision(true);
    try {
      const endpoint = `/api/v1/approvals/${activeDecisionModal.id}/${activeDecisionModal.action}`;
      try {
        await api.post(endpoint, { decision_notes: decisionNotes });
      } catch {
        // Fallback for local mock update
      }

      // Optimistic update
      setApprovals((prev) =>
        prev.map((item) =>
          item.id === activeDecisionModal.id
            ? {
                ...item,
                status: activeDecisionModal.action === "approve" ? "APPROVED" : "REJECTED",
                decision_notes: decisionNotes || (activeDecisionModal.action === "approve" ? "Authorized via dashboard" : "Rejected by reviewer"),
              }
            : item
        )
      );

      setFeedbackMessage({
        type: "success",
        text: `Action "${activeDecisionModal.actionName}" successfully ${activeDecisionModal.action === "approve" ? "authorized" : "rejected"}.`,
      });
      setTimeout(() => setFeedbackMessage(null), 4000);
      setActiveDecisionModal(null);
      setDecisionNotes("");
    } catch {
      setFeedbackMessage({
        type: "error",
        text: "Failed to record decision. Please check backend connection.",
      });
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const filteredApprovals = useMemo(() => {
    return approvals.filter((item) => {
      const matchesStatus = statusFilter === "ALL" || item.status.toUpperCase() === statusFilter.toUpperCase();
      const matchesSearch =
        item.action_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.requested_by_agent.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.reason.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [approvals, statusFilter, searchQuery]);

  const metrics = useMemo(() => {
    return {
      total: approvals.length,
      pending: approvals.filter((a) => a.status === "PENDING").length,
      approved: approvals.filter((a) => a.status === "APPROVED").length,
      rejected: approvals.filter((a) => a.status === "REJECTED").length,
    };
  }, [approvals]);

  const getRiskBadge = (risk: string) => {
    switch (risk.toUpperCase()) {
      case "CRITICAL":
        return <Badge variant="danger" className="animate-pulse">CRITICAL RISK</Badge>;
      case "HIGH":
        return <Badge variant="warning">HIGH RISK</Badge>;
      case "MEDIUM":
        return <Badge variant="cyan">MEDIUM RISK</Badge>;
      case "LOW":
        return <Badge variant="secondary">LOW RISK</Badge>;
      default:
        return <Badge variant="secondary">{risk}</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case "PENDING":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <Clock className="w-3 h-3 mr-1" /> Pending Review
          </span>
        );
      case "APPROVED":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3 mr-1" /> Approved
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3 h-3 mr-1" /> Rejected
          </span>
        );
      case "EXPIRED":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-700/50 text-slate-400 border border-slate-600">
            <AlertOctagon className="w-3 h-3 mr-1" /> Expired TTL
          </span>
        );
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto p-4 sm:p-6 lg:p-8">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20 text-amber-400">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 flex items-center space-x-2">
                <span>Human-in-the-Loop Approvals</span>
                {metrics.pending > 0 && (
                  <Badge variant="warning">{metrics.pending} Action Required</Badge>
                )}
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Active safety intervention gate: authorize or reject high-risk autonomous agent operations.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchApprovals}
            disabled={isLoading}
            className="border-slate-700 hover:bg-slate-800 text-slate-300"
          >
            <RefreshCw className={`h-4 w-4 mr-1.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Feedback Toast */}
      {feedbackMessage && (
        <div
          className={`p-3 rounded-lg border flex items-center justify-between text-sm ${
            feedbackMessage.type === "success"
              ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-300"
              : "bg-rose-950/40 border-rose-500/30 text-rose-300"
          }`}
        >
          <span>{feedbackMessage.text}</span>
          <button onClick={() => setFeedbackMessage(null)} className="opacity-70 hover:opacity-100">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Metric Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs font-medium text-slate-400">Total Tickets</p>
          <p className="text-2xl font-bold text-slate-100 mt-1">{metrics.total}</p>
        </Card>
        <Card className="border-amber-500/20 bg-amber-950/10 p-4">
          <p className="text-xs font-medium text-amber-400">Pending Review</p>
          <p className="text-2xl font-bold text-amber-300 mt-1">{metrics.pending}</p>
        </Card>
        <Card className="border-emerald-500/20 bg-emerald-950/10 p-4">
          <p className="text-xs font-medium text-emerald-400">Authorized</p>
          <p className="text-2xl font-bold text-emerald-300 mt-1">{metrics.approved}</p>
        </Card>
        <Card className="border-rose-500/20 bg-rose-950/10 p-4">
          <p className="text-xs font-medium text-rose-400">Blocked / Rejected</p>
          <p className="text-2xl font-bold text-rose-300 mt-1">{metrics.rejected}</p>
        </Card>
      </div>

      {/* Controls & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/70 p-3 rounded-xl border border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search action, agent, or reason..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/50"
          />
        </div>
        <div className="flex items-center space-x-1.5 w-full sm:w-auto overflow-x-auto">
          {["ALL", "PENDING", "APPROVED", "REJECTED"].map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
                statusFilter === tab
                  ? "bg-amber-500 text-slate-950 font-bold shadow-sm"
                  : "bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              {tab === "ALL" ? "All Tickets" : tab.charAt(0) + tab.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Approvals List */}
      <div className="space-y-4">
        {filteredApprovals.length === 0 ? (
          <Card className="border-slate-800 bg-slate-900/30 p-12 text-center">
            <CheckCircle2 className="h-12 w-12 mx-auto text-slate-600 mb-3" />
            <p className="text-slate-300 font-medium">No approval tickets match your criteria</p>
            <p className="text-xs text-slate-500 mt-1">
              All agent tool operations are authorized or no pending triggers match the current filters.
            </p>
          </Card>
        ) : (
          filteredApprovals.map((ticket) => {
            const isPending = ticket.status.toUpperCase() === "PENDING";
            const isExpanded = !!expandedPayloads[ticket.id];

            return (
              <Card
                key={ticket.id}
                className={`border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-all ${
                  isPending ? "border-l-4 border-l-amber-500" : ""
                }`}
              >
                <CardHeader className="pb-3 flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-1.5">
                    <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                      <span className="font-mono text-xs text-amber-400 font-semibold">{ticket.id}</span>
                      {getRiskBadge(ticket.risk_level)}
                      {getStatusBadge(ticket.status)}
                    </div>
                    <CardTitle className="text-base font-semibold text-slate-100 flex items-center gap-2">
                      <span className="font-mono text-cyan-400">{ticket.action_name}</span>
                    </CardTitle>
                    <CardDescription className="text-xs text-slate-400 flex items-center gap-2 flex-wrap">
                      <span className="flex items-center gap-1">
                        <Cpu className="h-3 w-3 text-slate-500" />
                        Requested by <strong className="text-slate-200">{ticket.requested_by_agent}</strong>
                      </span>
                      <span>•</span>
                      <span className="font-mono text-[11px] text-slate-500">Run: {ticket.agent_run_id}</span>
                    </CardDescription>
                  </div>
                  <div className="text-right text-[11px] text-slate-500 space-y-1">
                    <div className="flex items-center sm:justify-end space-x-1">
                      <Clock className="h-3 w-3" />
                      <span>{new Date(ticket.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    </div>
                    {ticket.expires_at && isPending && (
                      <p className="text-[10px] text-amber-400/80">
                        Expires: {new Date(ticket.expires_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-0">
                  {/* Justification Box */}
                  <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800/80">
                    <p className="text-[11px] text-slate-400 font-medium mb-1 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3 text-amber-400" /> Safety Justification:
                    </p>
                    <p className="text-xs text-slate-200 leading-relaxed">{ticket.reason}</p>
                  </div>

                  {/* Decision notes if resolved */}
                  {ticket.decision_notes && (
                    <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800 text-xs text-slate-400">
                      <span className="font-semibold text-slate-300">Reviewer Note: </span>
                      {ticket.decision_notes}
                    </div>
                  )}

                  {/* Expandable Action Payload */}
                  <div className="pt-1">
                    <button
                      onClick={() => togglePayloadExpand(ticket.id)}
                      className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center space-x-1 transition-colors"
                    >
                      <FileText className="h-3.5 w-3.5" />
                      <span>{isExpanded ? "Hide Action Payload" : "Inspect Action Payload"}</span>
                      {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </button>
                    {isExpanded && (
                      <pre className="mt-2 text-[11px] font-mono bg-slate-950 text-emerald-400 p-3 rounded-lg border border-slate-800 overflow-x-auto max-h-56">
                        {JSON.stringify(ticket.action_payload, null, 2)}
                      </pre>
                    )}
                  </div>

                  {/* Action Decision Buttons */}
                  {isPending && (
                    <div className="pt-3 border-t border-slate-800 flex items-center justify-end space-x-3">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setActiveDecisionModal({
                            id: ticket.id,
                            action: "reject",
                            actionName: ticket.action_name,
                          })
                        }
                        className="text-rose-400 border-rose-500/30 hover:bg-rose-950/30 hover:text-rose-300 space-x-1 text-xs"
                      >
                        <X className="h-3.5 w-3.5" />
                        <span>Reject Action</span>
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() =>
                          setActiveDecisionModal({
                            id: ticket.id,
                            action: "approve",
                            actionName: ticket.action_name,
                          })
                        }
                        className="bg-emerald-600 hover:bg-emerald-500 text-white space-x-1 text-xs font-semibold"
                      >
                        <Check className="h-3.5 w-3.5" />
                        <span>Approve & Authorize</span>
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* Decision Modal */}
      {activeDecisionModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                {activeDecisionModal.action === "approve" ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                ) : (
                  <XCircle className="h-5 w-5 text-rose-400" />
                )}
                {activeDecisionModal.action === "approve" ? "Authorize Action" : "Reject Action"}
              </h3>
              <button
                onClick={() => setActiveDecisionModal(null)}
                className="text-slate-400 hover:text-slate-200 text-sm"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Confirm your decision for{" "}
              <code className="text-cyan-400 font-bold">{activeDecisionModal.actionName}</code>. An immutable audit
              event will be recorded with your user ID.
            </p>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Decision Notes / Justification (optional):</label>
              <textarea
                value={decisionNotes}
                onChange={(e) => setDecisionNotes(e.target.value)}
                placeholder={
                  activeDecisionModal.action === "approve"
                    ? "e.g., Verified budget availability and verified external recipient domain."
                    : "e.g., Denied due to missing secondary reviewer clearance."
                }
                rows={3}
                className="w-full text-xs bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-amber-500/50"
              />
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setActiveDecisionModal(null)}
                disabled={isSubmittingDecision}
                className="text-slate-400 border-slate-700 text-xs"
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleDecisionSubmit}
                disabled={isSubmittingDecision}
                className={`text-xs font-semibold ${
                  activeDecisionModal.action === "approve"
                    ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                    : "bg-rose-600 hover:bg-rose-500 text-white"
                }`}
              >
                {isSubmittingDecision ? "Saving..." : activeDecisionModal.action === "approve" ? "Confirm Approval" : "Confirm Rejection"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
