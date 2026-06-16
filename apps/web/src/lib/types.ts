export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  tags?: string[];
  attachedDocs?: string[];
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
}

export interface Document {
  id: string;
  name: string;
  size: number;
  type: string;
  content: string;
  uploadedAt: number;
}
