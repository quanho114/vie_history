import { useState, useCallback } from "react";
import { storage } from "../lib/storage";
import type { ChatDocument } from "../types";

async function extractText(file: File): Promise<string> {
  const ext = file.name.split(".").pop()?.toLowerCase();

  if (ext === "txt" || ext === "md") {
    return await file.text();
  }

  if (ext === "pdf") {
    throw new Error("Hỗ trợ PDF sắp có. Hiện tại chỉ hỗ trợ file .txt và .md");
  }

  if (ext === "docx") {
    throw new Error("Hỗ trợ DOCX sắp có. Hiện tại chỉ hỗ trợ file .txt và .md");
  }

  throw new Error(`Không hỗ trợ định dạng .${ext}`);
}

export function useDocuments() {
  const [documents, setDocuments] = useState<ChatDocument[]>(
    () => storage.getDocuments()
  );
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const uploadDocument = useCallback(async (file: File) => {
    if (documents.length >= 5) {
      setUploadError("Tối đa 5 tài liệu. Xóa bớt để tải lên.");
      return;
    }

    const MAX_SIZE = 10 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      setUploadError("File quá lớn. Tối đa 10MB.");
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      const content = await extractText(file);
      const doc: ChatDocument = {
        id: crypto.randomUUID(),
        name: file.name,
        size: file.size,
        type: file.name.split(".").pop() || "txt",
        content: content.slice(0, 50000),
        uploadedAt: Date.now(),
      };
      storage.saveDocument(doc);
      setDocuments(storage.getDocuments());
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Lỗi khi đọc file.");
    } finally {
      setUploading(false);
    }
  }, [documents]);

  const deleteDocument = useCallback((id: string) => {
    storage.deleteDocument(id);
    setDocuments(storage.getDocuments());
  }, []);

  const openFilePicker = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".txt,.md";
    input.multiple = false;
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) uploadDocument(file);
    };
    input.click();
  }, [uploadDocument]);

  return {
    documents,
    uploading,
    uploadError,
    uploadDocument,
    deleteDocument,
    openFilePicker,
  };
}
