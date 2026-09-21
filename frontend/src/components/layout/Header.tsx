"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Building2,
  Bell,
  Search,
  Plus,
  Cpu,
  CheckCircle2,
  ChevronDown,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/Button";

export function Header() {
  const { user } = useAuth();
  const [showOrgMenu, setShowOrgMenu] = useState(false);

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/60 backdrop-blur-xl px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Left: Organization Context */}
      <div className="flex items-center space-x-4">
        <div className="relative">
          <button
            onClick={() => setShowOrgMenu(!showOrgMenu)}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900 transition-all text-left"
          >
            <Building2 className="h-4 w-4 text-teal-400" />
            <div className="leading-tight">
              <span className="text-xs font-semibold text-slate-200">
                {user?.organization_name || "AEGIS Global Operations"}
              </span>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
          </button>

          {showOrgMenu && (
            <div className="absolute left-0 mt-2 w-64 rounded-xl border border-slate-700 bg-slate-900 p-2 shadow-2xl z-50 animate-in fade-in-0 zoom-in-95">
              <div className="px-3 py-2 border-b border-slate-800">
                <p className="text-[11px] font-medium text-slate-400">Current Organization</p>
                <p className="text-sm font-semibold text-slate-100 truncate">
                  {user?.organization_name || "AEGIS Global Operations"}
                </p>
                <p className="text-[10px] text-teal-400 mt-0.5">
                  Tenant ID: {user?.organization_id?.substring(0, 13) || "default"}...
                </p>
              </div>
              <div className="py-1">
                <div className="px-3 py-2 text-xs text-slate-400 flex items-center justify-between">
                  <span>Role Permission Tier</span>
                  <span className="bg-teal-500/20 text-teal-300 px-2 py-0.5 rounded font-mono text-[10px] font-bold">
                    {user?.role || "ADMIN"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* System Diagnostics Indicator */}
        <div className="hidden lg:flex items-center space-x-2 px-3 py-1 rounded-full border border-slate-800 bg-slate-900/40 text-[11px] text-slate-400">
          <Cpu className="h-3.5 w-3.5 text-teal-400" />
          <span>LLM: Gemini / OpenAI</span>
          <span className="text-slate-700">|</span>
          <span className="flex items-center space-x-1 text-emerald-400 font-medium">
            <CheckCircle2 className="h-3 w-3" />
            <span>Operational</span>
          </span>
        </div>
      </div>

      {/* Right: Actions & Tools */}
      <div className="flex items-center space-x-3">
        {/* Search trigger */}
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Search docs, agents, runs... (Ctrl+K)"
            className="h-9 w-64 rounded-lg border border-slate-800 bg-slate-900/60 pl-9 pr-4 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all"
          />
        </div>

        {/* Notifications */}
        <button className="relative p-2 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition-colors">
          <Bell className="h-4 w-4" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-teal-400" />
        </button>

        {/* New Chat Quick Button */}
        <Link href="/chat">
          <Button size="sm" variant="primary" className="space-x-1.5">
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">New Chat</span>
          </Button>
        </Link>
      </div>
    </header>
  );
}
