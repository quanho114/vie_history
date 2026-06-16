import type { ChatConversation, ChatDocument } from "../types";

const CONVERSATIONS_KEY = "histori_conversations";
const DOCUMENTS_KEY = "histori_documents";

export const storage = {
  getConversations(): ChatConversation[] {
    try {
      const raw = localStorage.getItem(CONVERSATIONS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },

  saveConversation(conv: ChatConversation): void {
    const all = storage.getConversations();
    const idx = all.findIndex((c) => c.id === conv.id);
    if (idx >= 0) {
      all[idx] = conv;
    } else {
      all.unshift(conv);
    }
    localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(all.slice(0, 50)));
  },

  deleteConversation(id: string): void {
    const all = storage.getConversations().filter((c) => c.id !== id);
    localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(all));
  },

  getDocuments(): ChatDocument[] {
    try {
      const raw = localStorage.getItem(DOCUMENTS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },

  saveDocument(doc: ChatDocument): void {
    const all = storage.getDocuments();
    localStorage.setItem(DOCUMENTS_KEY, JSON.stringify([...all, doc]));
  },

  deleteDocument(id: string): void {
    const all = storage.getDocuments().filter((d) => d.id !== id);
    localStorage.setItem(DOCUMENTS_KEY, JSON.stringify(all));
  },
};
