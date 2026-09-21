"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  MessagesSquare,
  FileText,
  Database,
  Bot,
  PlayCircle,
  CheckSquare,
  BarChart3,
  BrainCircuit,
  FileCheck2,
  ShieldCheck,
  Users,
  Settings,
  ShieldAlert,
  LogOut,
  Sparkles,
  Wrench,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

interface NavItem {
  title: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
}

interface NavGroup {
  group: string;
  items: NavItem[];
}

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const navigation: NavGroup[] = [
    {
      group: "Operations",
      items: [
        {
          title: "Dashboard",
          href: "/dashboard",
          icon: <LayoutDashboard className="h-4 w-4" />,
        },
        {
          title: "AI Chat",
          href: "/chat",
          icon: <MessageSquare className="h-4 w-4" />,
          badge: "Live",
        },
        {
          title: "Conversations",
          href: "/conversations",
          icon: <MessagesSquare className="h-4 w-4" />,
        },
      ],
    },
    {
      group: "Knowledge & RAG",
      items: [
        {
          title: "Documents",
          href: "/documents",
          icon: <FileText className="h-4 w-4" />,
        },
        {
          title: "Knowledge Bases",
          href: "/knowledge-bases",
          icon: <Database className="h-4 w-4" />,
        },
      ],
    },
    {
      group: "Autonomous Agents",
      items: [
        {
          title: "Agents",
          href: "/agents",
          icon: <Bot className="h-4 w-4" />,
          badge: "LangGraph",
        },
        {
          title: "Agent Runs",
          href: "/agent-runs",
          icon: <PlayCircle className="h-4 w-4" />,
        },
        {
          title: "MCP Tools",
          href: "/tools",
          icon: <Wrench className="h-4 w-4" />,
          badge: "MCP",
        },
        {
          title: "Approvals",
          href: "/approvals",
          icon: <CheckSquare className="h-4 w-4" />,
          badge: "HITL",
        },
      ],
    },
    {
      group: "Analytics & ML",
      items: [
        {
          title: "SQL & Analytics",
          href: "/analytics",
          icon: <BarChart3 className="h-4 w-4" />,
        },
        {
          title: "ML Studio",
          href: "/ml",
          icon: <BrainCircuit className="h-4 w-4" />,
          badge: "ML",
        },
        {
          title: "Reports",
          href: "/reports",
          icon: <FileCheck2 className="h-4 w-4" />,
        },
        {
          title: "Evaluations",
          href: "/evaluations",
          icon: <ShieldCheck className="h-4 w-4" />,
        },
      ],
    },
    {
      group: "Platform",
      items: [
        {
          title: "Team & RBAC",
          href: "/team",
          icon: <Users className="h-4 w-4" />,
        },
        {
          title: "Settings",
          href: "/settings",
          icon: <Settings className="h-4 w-4" />,
        },
        {
          title: "Security Audit",
          href: "/admin",
          icon: <ShieldAlert className="h-4 w-4" />,
          badge: "Audit",
        },
      ],
    },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-950/90 flex flex-col h-screen sticky top-0 z-40 backdrop-blur-xl">
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-6 border-b border-slate-800/80">
        <Link href="/dashboard" className="flex items-center space-x-3 group">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center shadow-lg shadow-teal-500/25 group-hover:shadow-teal-500/40 transition-all">
            <Sparkles className="h-5 w-5 text-slate-950 font-bold" />
          </div>
          <div>
            <span className="font-bold text-base tracking-wider bg-gradient-to-r from-slate-100 to-slate-300 bg-clip-text text-transparent">
              AEGIS AI
            </span>
            <div className="flex items-center space-x-1.5 mt-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-[10px] uppercase tracking-widest text-emerald-400 font-semibold">
                Autonomous
              </span>
            </div>
          </div>
        </Link>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        {navigation.map((group) => (
          <div key={group.group} className="space-y-1">
            <h4 className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              {group.group}
            </h4>
            <div className="mt-1 space-y-0.5">
              {group.items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 group",
                      isActive
                        ? "bg-teal-500/10 text-teal-300 border border-teal-500/30 font-semibold shadow-sm"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/80"
                    )}
                  >
                    <div className="flex items-center space-x-2.5">
                      <span
                        className={cn(
                          "transition-colors",
                          isActive
                            ? "text-teal-400"
                            : "text-slate-500 group-hover:text-slate-300"
                        )}
                      >
                        {item.icon}
                      </span>
                      <span>{item.title}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={cn(
                          "text-[10px] px-1.5 py-0.2 rounded font-semibold",
                          isActive
                            ? "bg-teal-500/20 text-teal-300"
                            : "bg-slate-800 text-slate-400"
                        )}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* User Footer Profile */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 min-w-0">
            <div className="h-8 w-8 rounded-full bg-slate-800 border border-teal-500/30 flex items-center justify-center text-xs font-bold text-teal-400 flex-shrink-0">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-slate-200 truncate">
                {user?.full_name || "Operations User"}
              </p>
              <div className="flex items-center space-x-1 mt-0.5">
                <span className="text-[10px] text-teal-400 bg-teal-500/10 px-1 rounded font-medium">
                  {user?.role || "ADMIN"}
                </span>
                <span className="text-[10px] text-slate-500 truncate">
                  {user?.organization_name || "Aegis Corp"}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log out"
            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-900 rounded-lg transition-colors flex-shrink-0"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
