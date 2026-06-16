import { useState, useCallback } from "react";
import { storage } from "../lib/storage";
import type { ChatConversation } from "../types";

export function useConversations() {
  const [conversations, setConversations] = useState<ChatConversation[]>(
    () => storage.getConversations()
  );

  const saveConversation = useCallback((conv: ChatConversation) => {
    storage.saveConversation(conv);
    setConversations(storage.getConversations());
  }, []);

  const createConversation = useCallback(
    (firstMessage: string): ChatConversation => {
      const conv: ChatConversation = {
        id: crypto.randomUUID(),
        title: firstMessage.slice(0, 40) || "New conversation",
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [],
      };
      storage.saveConversation(conv);
      setConversations(storage.getConversations());
      return conv;
    },
    []
  );

  const deleteConversation = useCallback((id: string) => {
    storage.deleteConversation(id);
    setConversations(storage.getConversations());
  }, []);

  return {
    conversations,
    saveConversation,
    createConversation,
    deleteConversation,
  };
}
