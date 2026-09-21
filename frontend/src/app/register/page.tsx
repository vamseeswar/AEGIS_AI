"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sparkles, ArrowRight, Building2, User, Mail, Lock } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const { error: toastError, success: toastSuccess } = useToast();

  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password.length < 8) {
      toastError("Weak Password", "Password must be at least 8 characters long.");
      return;
    }

    setIsLoading(true);
    try {
      await register(email, password, fullName, organizationName);
      toastSuccess(
        "Organization Provisioned",
        `Welcome ${fullName}! Your workspace '${organizationName}' is ready.`
      );
      router.push("/dashboard");
    } catch (err: any) {
      toastError(
        "Registration Failed",
        err.message || "Failed to register organization."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-slate-950 bg-cyber-grid relative overflow-hidden">
      {/* Glow Orbs */}
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Brand Banner */}
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center shadow-xl shadow-teal-500/25 mb-4">
            <Sparkles className="h-6 w-6 text-slate-950 font-bold" />
          </div>
          <h1 className="text-2xl font-bold tracking-wider text-slate-100">
            AEGIS AI
          </h1>
          <p className="text-xs text-slate-400 mt-1 uppercase tracking-widest font-medium">
            Autonomous AI Operations Platform
          </p>
        </div>

        <Card className="border-slate-800 bg-slate-900/90 shadow-2xl backdrop-blur-xl">
          <CardHeader className="pb-4">
            <CardTitle className="text-xl">Create your Organization</CardTitle>
            <CardDescription>
              Provision a secure, isolated multi-tenant environment with RBAC and autonomous agents.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Full Name"
                type="text"
                placeholder="Dr. Jane Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                icon={<User className="h-4 w-4" />}
              />

              <Input
                label="Organization Name"
                type="text"
                placeholder="Acme Intelligence Corp"
                value={organizationName}
                onChange={(e) => setOrganizationName(e.target.value)}
                required
                icon={<Building2 className="h-4 w-4" />}
              />

              <Input
                label="Work Email"
                type="email"
                placeholder="jane@acme.corp"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                icon={<Mail className="h-4 w-4" />}
              />

              <Input
                label="Password"
                type="password"
                placeholder="At least 8 chars, uppercase & digit"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                icon={<Lock className="h-4 w-4" />}
                helperText="Must include uppercase, lowercase, and numeric characters."
              />

              <Button
                type="submit"
                variant="primary"
                className="w-full h-11"
                isLoading={isLoading}
              >
                <span>Provision Organization</span>
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </form>

            <div className="mt-6 text-center text-xs text-slate-400 border-t border-slate-800 pt-4">
              <span>Already registered? </span>
              <Link
                href="/login"
                className="text-teal-400 hover:text-teal-300 font-semibold underline-offset-4 hover:underline"
              >
                Sign in to existing account
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
