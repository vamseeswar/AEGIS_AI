"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sparkles, ArrowRight, Shield, Lock, Mail } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const { error: toastError, success: toastSuccess } = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(email, password);
      toastSuccess("Authentication successful", "Welcome to AEGIS AI Operations.");
      router.push("/dashboard");
    } catch (err: any) {
      toastError("Login failed", err.message || "Invalid credentials provided.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUseDemoAdmin = () => {
    setEmail("admin@aegis.ai");
    setPassword("Admin123!");
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-slate-950 bg-cyber-grid relative overflow-hidden">
      {/* Glow Orbs */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

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
            <CardTitle className="text-xl">Sign in to your organization</CardTitle>
            <CardDescription>
              Access your autonomous agents, RAG knowledge bases, and analytics.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Work Email"
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                icon={<Mail className="h-4 w-4" />}
              />

              <Input
                label="Password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                icon={<Lock className="h-4 w-4" />}
              />

              <Button
                type="submit"
                variant="primary"
                className="w-full h-11"
                isLoading={isLoading}
              >
                <span>Authenticate Session</span>
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </form>

            {/* Quick Demo Fill */}
            <div className="mt-5 pt-5 border-t border-slate-800">
              <button
                type="button"
                onClick={handleUseDemoAdmin}
                className="w-full py-2 px-3 rounded-lg border border-slate-700/60 bg-slate-800/40 text-xs text-slate-300 hover:text-teal-300 hover:border-teal-500/40 hover:bg-slate-800/70 transition-all flex items-center justify-center space-x-2"
              >
                <Shield className="h-3.5 w-3.5 text-teal-400" />
                <span>Fill Default Admin Credentials (admin@aegis.ai)</span>
              </button>
            </div>

            <div className="mt-5 text-center text-xs text-slate-400">
              <span>Don&apos;t have an enterprise account? </span>
              <Link
                href="/register"
                className="text-teal-400 hover:text-teal-300 font-semibold underline-offset-4 hover:underline"
              >
                Create an Organization
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
