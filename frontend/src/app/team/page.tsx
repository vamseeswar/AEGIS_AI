"use client";

import React from "react";
import { Users, UserPlus, Shield, Mail } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { useAuth } from "@/context/AuthContext";

export default function TeamPage() {
  const { user } = useAuth();

  const mockMembers = [
    {
      name: user?.full_name || "Lead Administrator",
      email: user?.email || "admin@aegis.ai",
      role: user?.role || "ADMIN",
      status: "ACTIVE",
    },
    {
      name: "Marcus Vance",
      email: "marcus@aegis.ai",
      role: "MANAGER",
      status: "ACTIVE",
    },
    {
      name: "Elena Rostova",
      email: "elena@aegis.ai",
      role: "MEMBER",
      status: "ACTIVE",
    },
    {
      name: "David Kim",
      email: "david@aegis.ai",
      role: "VIEWER",
      status: "ACTIVE",
    },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center space-x-2">
            <span>Team & Role-Based Access Control</span>
            <Badge variant="teal">4-Tier RBAC</Badge>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage organization members, role assignments (`ADMIN`, `MANAGER`, `MEMBER`, `VIEWER`), and permissions.
          </p>
        </div>
        <Button variant="primary" className="space-x-1.5">
          <UserPlus className="h-4 w-4" />
          <span>Invite Member</span>
        </Button>
      </div>

      <Card className="border-slate-800 bg-slate-900/60">
        <CardHeader>
          <CardTitle className="text-base">Organization Roster</CardTitle>
          <CardDescription>
            Active members for {user?.organization_name || "AEGIS Global Operations"}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Member Name</TableHead>
                <TableHead>Email Address</TableHead>
                <TableHead>Role Assignment</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockMembers.map((m, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium text-slate-200">{m.name}</TableCell>
                  <TableCell className="text-xs text-slate-400 font-mono">{m.email}</TableCell>
                  <TableCell>
                    <Badge variant={m.role === "ADMIN" ? "teal" : "secondary"}>
                      {m.role}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="success">Active</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
