import { useState } from "react";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { Bold, Italic, Code, Link, Heading1, Heading2, Heading3, List, ListOrdered, Eye, Edit2 } from "lucide-react";

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minHeight?: string;
}

export function MarkdownEditor({ value, onChange, placeholder = "Viết nội dung bằng Markdown...", minHeight = "250px" }: MarkdownEditorProps) {
  const [activeTab, setActiveTab] = useState<"edit" | "preview">("edit");

  const insertText = (before: string, after: string = "") => {
    const textarea = document.getElementById("md-textarea") as HTMLTextAreaElement;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selected = text.substring(start, end);
    const replacement = before + selected + after;

    onChange(text.substring(0, start) + replacement + text.substring(end));

    // Refocus and set cursor position
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + before.length, start + before.length + selected.length);
    }, 0);
  };

  const toolbarActions = [
    { icon: <Heading1 size={15} />, label: "H1", onClick: () => insertText("# ", "") },
    { icon: <Heading2 size={15} />, label: "H2", onClick: () => insertText("## ", "") },
    { icon: <Heading3 size={15} />, label: "H3", onClick: () => insertText("### ", "") },
    { icon: <Bold size={15} />, label: "Đậm", onClick: () => insertText("**", "**") },
    { icon: <Italic size={15} />, label: "Nghiêng", onClick: () => insertText("*", "*") },
    { icon: <Code size={15} />, label: "Mã", onClick: () => insertText("`", "`") },
    { icon: <Link size={15} />, label: "Liên kết", onClick: () => insertText("[", "](url)") },
    { icon: <List size={15} />, label: "Danh sách", onClick: () => insertText("- ", "") },
    { icon: <ListOrdered size={15} />, label: "Thứ tự", onClick: () => insertText("1. ", "") },
  ];

  return (
    <div className="border border-stone-200 dark:border-stone-850 rounded-2xl overflow-hidden bg-white dark:bg-stone-900 shadow-sm flex flex-col transition-all focus-within:ring-2 focus-within:ring-[#cc785c]/20">
      {/* Editor Header */}
      <div className="flex items-center justify-between border-b border-stone-150 dark:border-stone-800 px-4 py-2 bg-stone-50 dark:bg-stone-900/80">
        {/* Formatting Toolbar */}
        <div className="flex flex-wrap gap-1.5">
          {toolbarActions.map((action, i) => (
            <button
              key={i}
              type="button"
              onClick={action.onClick}
              disabled={activeTab === "preview"}
              className="p-1.5 rounded-lg text-stone-500 dark:text-stone-400 hover:text-stone-800 dark:hover:text-stone-200 hover:bg-stone-200/50 dark:hover:bg-stone-800 transition-all disabled:opacity-30 disabled:pointer-events-none"
              title={action.label}
              aria-label={action.label}
            >
              {action.icon}
            </button>
          ))}
        </div>

        {/* Edit / Preview Tabs */}
        <div className="flex bg-stone-200/55 dark:bg-stone-800 p-0.5 rounded-xl">
          <button
            type="button"
            onClick={() => setActiveTab("edit")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "edit"
                ? "bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-sm"
                : "text-stone-500 dark:text-stone-400 hover:text-stone-700"
            }`}
          >
            <Edit2 size={12} />
            Soạn thảo
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("preview")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "preview"
                ? "bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 shadow-sm"
                : "text-stone-500 dark:text-stone-400 hover:text-stone-700"
            }`}
          >
            <Eye size={12} />
            Xem trước
          </button>
        </div>
      </div>

      {/* Editor Content Area */}
      <div className="relative flex-1">
        {activeTab === "edit" ? (
          <textarea
            id="md-textarea"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            style={{ minHeight }}
            className="w-full p-4 border-0 focus:ring-0 bg-transparent text-[14px] text-stone-800 dark:text-stone-200 font-mono leading-relaxed placeholder-stone-400 focus:outline-none resize-y"
          />
        ) : (
          <div className="p-4 overflow-y-auto bg-stone-50/40 dark:bg-stone-950/20" style={{ minHeight }}>
            {value.trim() ? (
              <MarkdownRenderer content={value} />
            ) : (
              <p className="text-xs text-stone-400 italic">Chưa có nội dung xem trước.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
