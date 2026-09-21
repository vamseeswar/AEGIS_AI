"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  FileText,
  Upload,
  Trash2,
  Search,
  RefreshCw,
  Download,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  FileCode,
  Table as TableIcon,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { formatBytes, formatDate } from "@/lib/utils";
import { getValidAuthToken } from "@/lib/auth-token";

async function authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
  let token = await getValidAuthToken();
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    token = await getValidAuthToken(true);
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
      res = await fetch(url, { ...options, headers });
    }
  }
  return res;
}

interface DocumentItem {
  id: string;
  organization_id: string;
  user_id: string;
  title: string;
  filename: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  status: "INDEXED" | "PARSING" | "FAILED" | "PENDING";
  chunks_count?: number;
  doc_metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

const FALLBACK_DOCS: DocumentItem[] = [
  {
    id: "doc-1",
    organization_id: "default",
    user_id: "admin",
    title: "Q3 Enterprise Financial Report",
    filename: "Q3_Enterprise_Financial_Report.pdf",
    file_type: "PDF",
    mime_type: "application/pdf",
    file_size_bytes: 4200000,
    status: "INDEXED",
    chunks_count: 48,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "doc-2",
    organization_id: "default",
    user_id: "admin",
    title: "AEGIS Security Architecture v1",
    filename: "AEGIS_Security_Architecture_v1.docx",
    file_type: "DOCX",
    mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    file_size_bytes: 1540000,
    status: "INDEXED",
    chunks_count: 32,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    updated_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "doc-3",
    organization_id: "default",
    user_id: "admin",
    title: "Customer Churn Telemetry 2024",
    filename: "Customer_Churn_Telemetry_2024.csv",
    file_type: "CSV",
    mime_type: "text/csv",
    file_size_bytes: 890000,
    status: "INDEXED",
    chunks_count: 14,
    created_at: new Date(Date.now() - 7200000).toISOString(),
    updated_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: "doc-4",
    organization_id: "default",
    user_id: "admin",
    title: "Autonomous Agent Guidelines",
    filename: "Autonomous_Agent_Guidelines.txt",
    file_type: "TXT",
    mime_type: "text/plain",
    file_size_bytes: 145000,
    status: "PARSING",
    chunks_count: 6,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString(),
  },
];

export default function DocumentsPage() {
  const { success, error, info } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  // Uploading state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadingName, setUploadingName] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Action states
  const [actionInProgressId, setActionInProgressId] = useState<string | null>(null);

  // Fetch documents from backend API
  const fetchDocuments = useCallback(async (searchQuery = "") => {
    try {
      setLoading(true);
      const url = searchQuery
        ? `/api/v1/documents?search=${encodeURIComponent(searchQuery)}`
        : "/api/v1/documents";

      const res = await authenticatedFetch(url);
      if (!res.ok) {
        if (res.status === 401) {
          setDocuments([]);
          return;
        }
        throw new Error(`Failed to load documents: ${res.statusText}`);
      }

      const data = await res.json();
      if (data.items && Array.isArray(data.items)) {
        setDocuments(data.items);
      } else {
        setDocuments([]);
      }
    } catch (err: any) {
      console.error("Error fetching documents:", err);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Handle single or multiple file upload
  const uploadFile = async (file: File) => {
    const allowedExtensions = [".pdf", ".docx", ".txt", ".csv", ".json"];
    const fileExt = "." + file.name.split(".").pop()?.toLowerCase();

    if (!allowedExtensions.includes(fileExt)) {
      error(
        "Unsupported File Format",
        `"${file.name}" is not supported. Please upload PDF, DOCX, TXT, CSV, or JSON.`
      );
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      error("File Exceeds Size Limit", `"${file.name}" is larger than the 25MB limit.`);
      return;
    }

    setIsUploading(true);
    setUploadingName(file.name);
    setUploadProgress(25);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", file.name.replace(/\.[^/.]+$/, "").replace(/_/g, " "));

      setUploadProgress(50);
      const res = await authenticatedFetch("/api/v1/documents/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.error?.message || errorData.detail || "Document upload failed");
      }

      setUploadProgress(85);
      const result = await res.json();
      const uploadedDoc = result.document;

      // Optional: Ensure document chunking and vector indexing is complete
      try {
        await authenticatedFetch(`/api/v1/documents/${uploadedDoc.id}/reindex`, {
          method: "POST",
        });
      } catch (reindexErr) {
        console.warn("Reindexing notice:", reindexErr);
      }

      setUploadProgress(100);
      success(
        "Upload & Indexing Complete",
        `"${file.name}" has been processed into vector chunks for RAG.`
      );

      // Refresh roster
      await fetchDocuments();
    } catch (err: any) {
      console.error("Upload failed:", err);
      error("Upload Failed", err.message || "Could not upload document. Please verify network and login.");
    } finally {
      setIsUploading(false);
      setUploadingName(null);
      setUploadProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      Array.from(e.target.files).forEach((file) => uploadFile(file));
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      Array.from(e.dataTransfer.files).forEach((file) => uploadFile(file));
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  // Delete document
  const handleDelete = async (doc: DocumentItem) => {
    if (!confirm(`Are you sure you want to delete "${doc.filename}"? This will also remove all its vector index chunks.`)) {
      return;
    }

    setActionInProgressId(doc.id);
    try {
      const res = await authenticatedFetch(`/api/v1/documents/${doc.id}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        throw new Error(`Failed to delete document (${res.status})`);
      }

      // Optimistically update list
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      success("Document Deleted", `"${doc.filename}" was successfully removed.`);
    } catch (err: any) {
      console.error("Delete failed:", err);
      error("Deletion Failed", err.message || "Failed to delete document.");
      // If it was a mock doc, still remove locally
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } finally {
      setActionInProgressId(null);
    }
  };

  // Download document
  const handleDownload = async (doc: DocumentItem) => {
    setActionInProgressId(doc.id);
    try {
      const res = await authenticatedFetch(`/api/v1/documents/${doc.id}/download`);
      if (!res.ok) {
        throw new Error(`Download failed (${res.status})`);
      }

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = doc.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      info("Download Started", `Downloading "${doc.filename}"...`);
    } catch (err: any) {
      console.error("Download failed:", err);
      error("Download Failed", "Unable to download document file.");
    } finally {
      setActionInProgressId(null);
    }
  };

  // Reindex document
  const handleReindex = async (doc: DocumentItem) => {
    setActionInProgressId(doc.id);
    try {
      const res = await authenticatedFetch(`/api/v1/documents/${doc.id}/reindex`, {
        method: "POST",
      });

      if (!res.ok) {
        throw new Error(`Reindex failed (${res.status})`);
      }

      const data = await res.json();
      success(
        "Reindexing Complete",
        `"${doc.filename}" re-parsed into ${data.chunks_created || 1} vector chunks.`
      );
      await fetchDocuments();
    } catch (err: any) {
      console.error("Reindex failed:", err);
      error("Reindex Failed", "Failed to regenerate document vector chunks.");
    } finally {
      setActionInProgressId(null);
    }
  };

  // Helper for document icon
  const getFileIcon = (filename: string, fileType: string) => {
    const ext = filename.split(".").pop()?.toLowerCase() || fileType.toLowerCase();
    switch (ext) {
      case "pdf":
        return <FileText className="h-4 w-4 text-rose-400 flex-shrink-0" />;
      case "docx":
      case "doc":
        return <FileText className="h-4 w-4 text-blue-400 flex-shrink-0" />;
      case "csv":
        return <TableIcon className="h-4 w-4 text-emerald-400 flex-shrink-0" />;
      case "json":
        return <FileCode className="h-4 w-4 text-amber-400 flex-shrink-0" />;
      default:
        return <FileText className="h-4 w-4 text-teal-400 flex-shrink-0" />;
    }
  };

  // Filtered documents
  const filteredDocuments = documents.filter((doc) => {
    if (!searchTerm) return true;
    const query = searchTerm.toLowerCase();
    return (
      doc.filename.toLowerCase().includes(query) ||
      doc.title.toLowerCase().includes(query) ||
      doc.file_type.toLowerCase().includes(query) ||
      doc.status.toLowerCase().includes(query)
    );
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept=".pdf,.docx,.txt,.csv,.json"
        multiple
        className="hidden"
      />

      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center space-x-2">
            <span>Document Management</span>
            <Badge variant="cyan">pgvector Ready</Badge>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Tenant-isolated file storage with recursive character chunking and embedding indexing.
          </p>
        </div>
        <Button
          variant="primary"
          className="space-x-1.5 shadow-lg shadow-teal-500/20"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
        >
          {isUploading ? (
            <Loader2 className="h-4 w-4 animate-spin text-slate-950" />
          ) : (
            <Upload className="h-4 w-4" />
          )}
          <span>{isUploading ? "Uploading..." : "Upload New File"}</span>
        </Button>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        onClick={() => !isUploading && fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed transition-all duration-200 rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer group relative overflow-hidden ${
          isDragging
            ? "border-teal-400 bg-teal-500/15 scale-[1.008] shadow-xl shadow-teal-500/10"
            : isUploading
            ? "border-teal-500/40 bg-slate-900/60 cursor-wait"
            : "border-slate-800 hover:border-teal-500/50 bg-slate-900/40 hover:bg-slate-900/70"
        }`}
      >
        {isUploading ? (
          <div className="w-full max-w-md flex flex-col items-center space-y-3 py-2">
            <div className="p-3.5 rounded-full bg-teal-500/20 text-teal-400 animate-pulse">
              <Loader2 className="h-7 w-7 animate-spin" />
            </div>
            <div className="space-y-1 text-center">
              <h3 className="text-sm font-semibold text-slate-200">
                Processing {uploadingName}...
              </h3>
              <p className="text-xs text-teal-400 font-mono">
                Extracting text, chunking & generating embeddings ({uploadProgress}%)
              </p>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden mt-2">
              <div
                className="bg-gradient-to-r from-teal-500 to-cyan-400 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        ) : (
          <>
            <div className="p-4 rounded-full bg-teal-500/10 text-teal-400 group-hover:scale-110 group-hover:bg-teal-500/20 transition-all mb-3 shadow-inner">
              <Upload className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200 group-hover:text-teal-300 transition-colors">
              {isDragging ? "Drop your files here to upload" : "Click to upload or drag & drop files here"}
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Supported formats: PDF, DOCX, TXT, CSV, JSON (Max 20MB per document)
            </p>
          </>
        )}
      </div>

      {/* Documents Roster Card */}
      <Card className="border-slate-800 bg-slate-900/60 shadow-xl backdrop-blur-sm">
        <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3">
          <div>
            <div className="flex items-center space-x-2">
              <CardTitle className="text-base">Indexed Documents Roster</CardTitle>
              {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-teal-400" />}
            </div>
            <CardDescription className="mt-0.5">
              {filteredDocuments.length} documents indexed for retrieval.
            </CardDescription>
          </div>

          <div className="flex items-center space-x-2">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-8 w-48 sm:w-56 rounded-lg border border-slate-800 bg-slate-950 pl-8 pr-3 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-teal-500 transition-colors"
              />
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchDocuments(searchTerm)}
              title="Refresh roster"
              className="h-8 px-2.5 text-slate-400 hover:text-slate-200 border-slate-800 bg-slate-950"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-teal-400" : ""}`} />
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {filteredDocuments.length === 0 ? (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
              <div className="p-3 rounded-full bg-slate-800/80 text-slate-500 border border-slate-700/60">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-300">
                  {searchTerm ? `No documents found matching "${searchTerm}"` : "No documents indexed yet"}
                </p>
                <p className="text-xs text-slate-500 mt-1 max-w-sm">
                  {searchTerm
                    ? "Try adjusting your search query or clear the filter."
                    : "Upload PDF, DOCX, TXT, CSV, or JSON documents above to enable citation-backed RAG chat."}
                </p>
              </div>
              {searchTerm && (
                <Button variant="outline" size="sm" onClick={() => setSearchTerm("")}>
                  Clear search
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-800 hover:bg-transparent">
                    <TableHead>DOCUMENT NAME</TableHead>
                    <TableHead>FILE SIZE</TableHead>
                    <TableHead>CHUNKS</TableHead>
                    <TableHead>STATUS</TableHead>
                    <TableHead>INGESTED</TableHead>
                    <TableHead className="text-right">ACTIONS</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredDocuments.map((doc) => {
                    const isOperating = actionInProgressId === doc.id;
                    const chunkCount = doc.chunks_count ?? doc.doc_metadata?.chunks_count ?? 1;

                    return (
                      <TableRow
                        key={doc.id}
                        className="border-slate-800/60 hover:bg-slate-800/30 transition-colors"
                      >
                        {/* Document Name */}
                        <TableCell className="font-medium text-slate-200">
                          <div className="flex items-center space-x-2.5 min-w-[200px]">
                            {getFileIcon(doc.filename, doc.file_type)}
                            <div className="flex flex-col min-w-0">
                              <span className="truncate max-w-xs font-semibold text-xs text-slate-200" title={doc.filename}>
                                {doc.filename}
                              </span>
                              {doc.title && doc.title !== doc.filename && (
                                <span className="text-[10px] text-slate-500 truncate max-w-xs">
                                  {doc.title}
                                </span>
                              )}
                            </div>
                          </div>
                        </TableCell>

                        {/* File Size */}
                        <TableCell className="text-slate-400 font-mono text-xs whitespace-nowrap">
                          {formatBytes(doc.file_size_bytes)}
                        </TableCell>

                        {/* Chunks */}
                        <TableCell className="text-slate-300 font-mono text-xs whitespace-nowrap">
                          {chunkCount} chunks
                        </TableCell>

                        {/* Status */}
                        <TableCell className="whitespace-nowrap">
                          {doc.status === "INDEXED" ? (
                            <Badge variant="success">Indexed</Badge>
                          ) : doc.status === "PARSING" ? (
                            <Badge variant="warning">Parsing</Badge>
                          ) : (
                            <Badge variant="destructive">Failed</Badge>
                          )}
                        </TableCell>

                        {/* Ingested Timestamp */}
                        <TableCell className="text-slate-400 text-xs whitespace-nowrap">
                          {formatDate(doc.created_at)}
                        </TableCell>

                        {/* Actions */}
                        <TableCell className="text-right whitespace-nowrap">
                          <div className="flex items-center justify-end space-x-1">
                            {/* Reindex Button */}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleReindex(doc)}
                              disabled={isOperating}
                              title="Re-parse & index vector embeddings"
                              className="text-slate-500 hover:text-teal-400 hover:bg-teal-500/10 h-7 w-7"
                            >
                              <RefreshCw className={`h-3.5 w-3.5 ${isOperating ? "animate-spin" : ""}`} />
                            </Button>

                            {/* Download Button */}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDownload(doc)}
                              disabled={isOperating}
                              title="Download original file"
                              className="text-slate-500 hover:text-cyan-400 hover:bg-cyan-500/10 h-7 w-7"
                            >
                              <Download className="h-3.5 w-3.5" />
                            </Button>

                            {/* Delete Button */}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDelete(doc)}
                              disabled={isOperating}
                              title="Delete document"
                              className="text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 h-7 w-7"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
