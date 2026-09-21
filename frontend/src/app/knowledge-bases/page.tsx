"use client";

import React from "react";
import { Database, Plus, Search, Layers, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

const mockKnowledgeBases = [
  {
    id: "kb-01",
    name: "Enterprise Policies & Operations Manuals",
    description: "Standard operating procedures, governance protocols, and tenant compliance guidelines.",
    documentsCount: 42,
    dimension: 768,
    metric: "Cosine",
    status: "ACTIVE",
  },
  {
    id: "kb-02",
    name: "Financial Audits & Revenue Ledgers",
    description: "Quarterly earnings statements, SEC filings, and revenue projections for ML lag analysis.",
    documentsCount: 28,
    dimension: 768,
    metric: "Cosine",
    status: "ACTIVE",
  },
  {
    id: "kb-03",
    name: "Engineering Architecture & Tech Specs",
    description: "API schemas, microservice topologies, database ERDs, and deployment runbooks.",
    documentsCount: 72,
    dimension: 768,
    metric: "Cosine",
    status: "ACTIVE",
  },
];

export default function KnowledgeBasesPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center space-x-2">
            <span>Knowledge Bases</span>
            <Badge variant="cyan">pgvector Indexed</Badge>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Isolated vector collections partitioned with cosine similarity and metadata filters.
          </p>
        </div>
        <Button variant="primary" className="space-x-1.5">
          <Plus className="h-4 w-4" />
          <span>Create Knowledge Base</span>
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {mockKnowledgeBases.map((kb) => (
          <Card key={kb.id} className="border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-all flex flex-col justify-between">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  <Database className="h-5 w-5" />
                </div>
                <Badge variant="teal">{kb.status}</Badge>
              </div>
              <CardTitle className="text-base mt-3">{kb.name}</CardTitle>
              <CardDescription className="text-xs leading-relaxed mt-2">
                {kb.description}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0 border-t border-slate-800/60 mt-4 py-3 flex items-center justify-between text-xs text-slate-400">
              <span>{kb.documentsCount} documents</span>
              <span className="font-mono text-cyan-400">{kb.dimension}d • {kb.metric}</span>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
