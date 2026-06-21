import ReactMarkdown from "react-markdown";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  return (
    <div className={`prose prose-stone dark:prose-invert max-w-none text-[14.5px] leading-relaxed text-stone-700 dark:text-stone-300 font-sans ${className}`}>
      <ReactMarkdown
        components={{
          h1: ({ children }) => <h1 className="font-display text-2xl font-bold text-stone-900 dark:text-stone-100 mt-6 mb-3 border-b border-stone-200/60 pb-1.5">{children}</h1>,
          h2: ({ children }) => <h2 className="font-display text-xl font-bold text-stone-900 dark:text-stone-100 mt-5 mb-2.5">{children}</h2>,
          h3: ({ children }) => <h3 className="font-display text-lg font-semibold text-stone-850 dark:text-stone-200 mt-4 mb-2">{children}</h3>,
          p: ({ children }) => <p className="mb-3.5 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 mb-3.5 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 mb-3.5 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="pl-0.5">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-[#cc785c] pl-4 italic text-stone-600 dark:text-stone-400 my-4 bg-stone-50 dark:bg-stone-900/50 py-1 pr-2 rounded-r-lg">
              {children}
            </blockquote>
          ),
          code: ({ children }) => (
            <code className="bg-stone-100 dark:bg-stone-800 text-stone-800 dark:text-stone-200 px-1.5 py-0.5 rounded text-[13px] font-mono">
              {children}
            </code>
          ),
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-[#cc785c] hover:underline font-semibold transition-colors">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
