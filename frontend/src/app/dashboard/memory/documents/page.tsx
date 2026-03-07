"use client";

import { useState, useEffect, useRef } from "react";
import {
  Upload,
  FileText,
  Loader2,
  Trash2,
  CheckCircle2,
  Clock,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import {
  listKnowledgeDocuments,
  uploadKnowledgeDocument,
  deleteKnowledgeDocument,
  getDocumentStatus,
} from "@/lib/api";
import type { KnowledgeDocument } from "@/lib/types";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const FILE_ICONS: Record<string, string> = {
  pdf: "PDF",
  docx: "DOCX",
  md: "MD",
  txt: "TXT",
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listKnowledgeDocuments()
      .then(setDocuments)
      .catch(() => toast.error("Erro ao carregar documentos"))
      .finally(() => setLoading(false));
  }, []);

  // Poll for processing status
  useEffect(() => {
    const processing = documents.filter((d) => !d.processed);
    if (processing.length === 0) return;

    const interval = setInterval(async () => {
      for (const doc of processing) {
        try {
          const status = await getDocumentStatus(doc.id);
          if (status.processed) {
            setDocuments((prev) =>
              prev.map((d) => (d.id === doc.id ? { ...d, processed: true, entry_id: status.entry_id } : d))
            );
          }
        } catch {
          // ignore
        }
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [documents]);

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);

    for (const file of Array.from(files)) {
      try {
        const result = await uploadKnowledgeDocument(file);
        setDocuments((prev) => [
          {
            id: result.document_id,
            filename: file.name,
            file_type: file.name.split(".").pop() || "",
            file_size: file.size,
            processed: false,
            created_at: new Date().toISOString(),
          },
          ...prev,
        ]);
        toast.success(`${file.name} enviado`);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : `Erro ao enviar ${file.name}`);
      }
    }

    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleDelete(id: string) {
    try {
      await deleteKnowledgeDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      toast.success("Documento removido");
    } catch {
      toast.error("Erro ao remover");
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    handleUpload(e.dataTransfer.files);
  }

  return (
    <div className="p-5 lg:p-8 space-y-6 overflow-y-auto flex-1">
      <h2 className="text-lg font-semibold flex items-center gap-2">
        <Upload size={20} className="text-accent" />
        Documentos
      </h2>

      {/* Upload area */}
      <div
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer",
          dragActive ? "border-accent bg-accent-surface/20" : "border-border hover:border-accent/50"
        )}
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.md,.txt"
          onChange={(e) => handleUpload(e.target.files)}
          className="hidden"
        />
        {uploading ? (
          <div className="flex items-center justify-center gap-2 text-muted">
            <Loader2 size={20} className="animate-spin" />
            <span className="text-sm">Enviando...</span>
          </div>
        ) : (
          <>
            <Upload size={32} className="mx-auto text-muted mb-2" />
            <p className="text-sm text-muted">
              Arraste arquivos aqui ou clique para selecionar
            </p>
            <p className="text-xs text-muted mt-1">PDF, DOCX, MD, TXT (max 10MB)</p>
          </>
        )}
      </div>

      {/* Documents list */}
      {loading ? (
        <div className="flex items-center justify-center gap-2 py-12 text-muted text-sm">
          <Loader2 size={16} className="animate-spin" /> Carregando...
        </div>
      ) : documents.length === 0 ? (
        <p className="text-sm text-muted text-center py-8">Nenhum documento enviado.</p>
      ) : (
        <div className="rounded-xl border border-border bg-card-bg divide-y divide-border">
          {documents.map((doc) => (
            <div key={doc.id} className="group flex items-center gap-4 px-5 py-3">
              <div className="w-10 h-10 rounded-lg bg-accent-surface flex items-center justify-center shrink-0">
                <span className="text-[10px] font-bold text-accent-text">
                  {FILE_ICONS[doc.file_type] || doc.file_type.toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{doc.filename}</p>
                <div className="flex items-center gap-3 text-xs text-muted mt-0.5">
                  <span>{formatSize(doc.file_size)}</span>
                  {doc.uploaded_by_name && <span>{doc.uploaded_by_name}</span>}
                  <span>{new Date(doc.created_at).toLocaleDateString("pt-BR")}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {doc.processed ? (
                  <span className="inline-flex items-center gap-1 text-xs text-success">
                    <CheckCircle2 size={14} /> Indexado
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs text-warning">
                    <Clock size={14} className="animate-pulse" /> Processando
                  </span>
                )}
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="p-1.5 rounded-lg border border-border hover:bg-hover transition-colors text-danger opacity-0 group-hover:opacity-100"
                  title="Remover"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
