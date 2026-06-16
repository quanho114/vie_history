const dict: Record<string, Record<string, string>> = {
  vi: {
    // sidebar
    "new_chat": "Cuộc trò chuyện mới",
    "chat": "Trò chuyện",
    "wiki": "Wiki Lịch sử",
    "timeline": "Mốc thời gian",
    "knowledge_map": "Bản đồ Tri thức",
    "knowledge_translate": "Biên dịch Tri thức",
    "documents": "Kho tài liệu",
    "settings": "Cài đặt",
    "logout": "Đăng xuất",
    // settings general
    "profile": "Hồ sơ",
    "ai_api": "AI & API Keys",
    "rag_search": "RAG & Tìm kiếm",
    "preferences": "Tùy chọn",
    "save_settings": "Lưu cài đặt",
    "cancel": "Hủy",
    // profile tab
    "personal_info": "Thông tin cá nhân",
    "username": "Tên người dùng",
    "email": "Email liên hệ",
    "new_password_placeholder": "Mật khẩu mới (để trống nếu không đổi)",
    // AI tab
    "provider": "Nền tảng (Provider)",
    "active_model": "Mô hình hoạt động",
    "api_key": "API Key",
    "ollama_url": "Ollama Host URL",
    "ollama_model": "Tên mô hình Ollama",
    // RAG tab
    "rag_mode": "Chọn cơ chế tìm kiếm",
    "rag_hybrid": "Hybrid Search (Kết hợp)",
    "rag_vector": "Semantic Search (Vector)",
    "rag_keyword": "Lexical Search (Từ khóa/BM25)",
    "chunk_limit": "Giới hạn Chunk (RAG)",
    "temperature": "Độ sáng tạo (Temperature)",
    // preferences tab
    "theme": "Giao diện (Theme)",
    "theme_light": "Ấm áp (Light)",
    "theme_dark": "Tối giản (Dark)",
    "language": "Ngôn ngữ",
    "lang_vi": "Tiếng Việt",
    "lang_en": "English",
    // alerts & general
    "saved_success": "Cấu hình thành công!",
    "save_failed": "Cấu hình thất bại!",
    "loading": "Đang xử lý...",
    "recent_chats": "Gần đây",
    "api_key_missing_warning": "Bạn chưa cấu hình API Key cho mô hình hiện tại. Vui lòng nhập API Key để bắt đầu trò chuyện và tránh nhận câu trả lời không chính xác.",
    "configure_now": "Cấu hình API Key ngay",
  },
  en: {
    // sidebar
    "new_chat": "New Chat",
    "chat": "Chat",
    "wiki": "History Wiki",
    "timeline": "Timeline",
    "knowledge_map": "Knowledge Graph",
    "knowledge_translate": "Translate Knowledge",
    "documents": "Documents",
    "settings": "Settings",
    "logout": "Log Out",
    // settings general
    "profile": "Profile",
    "ai_api": "AI & API Keys",
    "rag_search": "RAG & Search",
    "preferences": "Preferences",
    "save_settings": "Save Settings",
    "cancel": "Cancel",
    // profile tab
    "personal_info": "Personal Info",
    "username": "Username",
    "email": "Contact Email",
    "new_password_placeholder": "New password (leave blank if unchanged)",
    // AI tab
    "provider": "Provider",
    "active_model": "Active Model",
    "api_key": "API Key",
    "ollama_url": "Ollama Host URL",
    "ollama_model": "Ollama Model Name",
    // RAG tab
    "rag_mode": "Search Retrieval Mode",
    "rag_hybrid": "Hybrid Search (RRF)",
    "rag_vector": "Semantic Search (Vector)",
    "rag_keyword": "Lexical Search (BM25)",
    "chunk_limit": "Chunk Limit (RAG)",
    "temperature": "LLM Temperature",
    // preferences tab
    "theme": "Appearance (Theme)",
    "theme_light": "Warm Cream (Light)",
    "theme_dark": "Dark Charcoal (Dark)",
    "language": "Language",
    "lang_vi": "Tiếng Việt",
    "lang_en": "English",
    // alerts & general
    "saved_success": "Settings saved successfully!",
    "save_failed": "Failed to save settings!",
    "loading": "Processing...",
    "recent_chats": "Recents",
    "api_key_missing_warning": "API Key is not configured for the active provider. Please enter your API Key to start chatting and avoid inaccurate responses.",
    "configure_now": "Configure API Key Now",
  }
};

export function t(key: string): string {
  const lang = localStorage.getItem("language") || "vi";
  return dict[lang]?.[key] || dict["vi"]?.[key] || key;
}
