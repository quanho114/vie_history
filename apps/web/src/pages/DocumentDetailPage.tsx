import { useEffect, useState, useMemo, useCallback, memo } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useDocumentStore } from "@/stores/documentStore"
import { formatDate } from "@/lib/utils/format"
import { cn } from "@/lib/utils/cn"
import {
  ArrowLeft,
  FileText,
  Loader2,
  User,
  MapPin,
  Calendar,
  Award,
  BookOpen,
  Globe,
  Sparkles,
  Trash2,
  Copy,
  Check,
} from "lucide-react"
import ReactMarkdown from "react-markdown"

// Decode URL-encoded titles and clean Wikipedia strings
function decodeTitle(title: string): string {
  try {
    let decoded = decodeURIComponent(title)
    if (decoded.startsWith("https://")) {
      const parts = decoded.split("/")
      let lastPart = parts[parts.length - 1]
      lastPart = lastPart.split("#")[0]
      decoded = lastPart.replace(/_/g, " ")
    }
    return decoded
  } catch (e) {
    return title.replace(/_/g, " ")
  }
}

// Elegant color-coding for historical entities and categories
function getTagClass(tag: string): string {
  if (/^\d{4}/.test(tag) || tag.endsWith("s")) {
    return "bg-[#fdf6e2] text-[#b28b2a] border border-[#f5ebcd]"
  }
  const keyLeaders = ["Hồ Chí Minh", "Võ Nguyên Giáp", "Lê Duẩn", "Trần Phú", "Trường Chinh"]
  if (keyLeaders.some(leader => tag.includes(leader))) {
    return "bg-[#eefcf7] text-[#0f7652] border border-[#d2f3e8]"
  }
  if (tag === "chat-upload") {
    return "bg-amber-50 text-amber-700 border border-amber-200"
  }
  return "bg-[#f5f1ea] text-[#6f675d] border border-[#e7e1d8]"
}

const MemoizedReactMarkdown = memo(
  ({ content, components }: { content: string; components?: React.ComponentProps<typeof ReactMarkdown>["components"] }) => {
    return <ReactMarkdown components={components}>{content}</ReactMarkdown>
  },
  (prevProps, nextProps) => prevProps.content === nextProps.content
)

const latexMarkdownComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className="font-display text-2xl font-normal text-stone-900 mt-10 mb-4 pb-1 border-b border-stone-200">
      {children}
    </h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className="font-display text-xl font-normal text-stone-900 mt-8 mb-3">
      {children}
    </h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className="font-display text-lg font-medium text-stone-850 mt-6 mb-2">
      {children}
    </h3>
  ),
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="text-[15px] leading-relaxed text-stone-850 text-justify my-4 first-line:indent-8 font-serif">
      {children}
    </p>
  ),
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="overflow-x-auto my-6 select-text">
      <table className="w-full font-serif text-[13.5px] text-stone-850 border-t-2 border-b-2 border-stone-900 border-collapse">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }: { children?: React.ReactNode }) => (
    <thead className="border-b border-stone-900 bg-stone-50/50">
      {children}
    </thead>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="py-2.5 px-3 font-bold text-stone-950 text-left">
      {children}
    </th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="py-2.5 px-3 border-b border-stone-100">
      {children}
    </td>
  ),
}

// Preprocess to filter out messy Wikipedia navigation sidebars, quality warnings, metadata, and bibliographies
function parseAndCleanToLatex(content: string): string {
  if (!content) return "";
  
  // 1. Initial cleaning of inline citation noises and tags
  let cleaned = content;
  
  // Clean Wikipedia edit markers: [sửa | sửa mã nguồn], [sửa]
  cleaned = cleaned.replace(/\[\s*sửa\s*(?:\|\s*sửa\s*mã\s*nguồn)?\s*\]/g, "");
  
  cleaned = cleaned.replace(/\[\s*cần\s*dẫn\s*nguồn\s*\]/gi, "");
  cleaned = cleaned.replace(/\[\s*cần\s*chú\s*thích\s*\]/gi, "");
  cleaned = cleaned.replace(/\[\s*liên\s*kết\s*hỏng\*?\s*\]/gi, "");
  
  // Strip footnote reference indices like [1], [15], etc.
  cleaned = cleaned.replace(/\[\d+\]/g, "");

  // Strip Wikipedia "Chú ý" inline annotation glued to a word (e.g. "lớnChú ý ở")
  cleaned = cleaned.replace(/Chú\s*ý/g, "");

  // Strip Wikipedia interwiki "(en)" markers (e.g. "cao nguyên Đông Miến (en)")
  cleaned = cleaned.replace(/\s*\(en\)/gi, "");

  // Strip consecutive bare citation numbers stuck together like "101112131415" or "9101112" at end of sentence or between spaces
  // Pattern: 2+ digits that are purely numbers and not a year/coordinate (not preceded by a letter that makes a real word)
  cleaned = cleaned.replace(/(?<=\s|[,.:;!?"'])\d{2,}(?=\s|$)/gm, (match) => {
    // Preserve 4-digit years (1940-2030 range) and coordinates
    const n = parseInt(match, 10);
    if (n >= 1000 && n <= 2100) return match;
    return "";
  });

  // Strip table separator lines like |---|, ||--||, |:---:|, |-|-| (before per-line processing)
  cleaned = cleaned.replace(/^[\s|:-]+$/gm, "");
  // Strip patterns like ||--|| or |||---|||  mid-line
  cleaned = cleaned.replace(/[|-]+([|:-]+[|:-]+)+/g, " ");
  // Strip remaining double-dash table fillers --
  cleaned = cleaned.replace(/--+/g, " ");

  // Strip trailing citation numbers glued to words like "đời khác.1" -> "đời khác." or "tiền đề. 1" -> "tiền đề."
  cleaned = cleaned.replace(/([a-zA-ZáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ])\.(\d+)(?=\s|$|\n)/g, "$1.");
  cleaned = cleaned.replace(/([a-zA-ZáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ])\s+(\d+)(?=\s|$|\n)/g, "$1");
  
  // Strip generic Wikipedia page title lines: "<anything> – Wikipedia tiếng Việt"
  cleaned = cleaned.replace(/^.+–\s*Wikipedia tiếng Việt\s*$/gm, "");

  // Strip blank Wikipedia date templates that weren't parsed: "ngày tháng năm", "tháng năm"
  cleaned = cleaned.replace(/\bngày\s+tháng\s+năm\b/g, "");
  cleaned = cleaned.replace(/(?<![\wđĐáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ])tháng\s+năm(?![\wđĐáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ])/g, "");

  // Strip standalone system lines
  cleaned = cleaned.replace(/^Lịch sử Việt Nam – Wikipedia tiếng Việt$/gm, "");
  cleaned = cleaned.replace(/^Biên niên sử Việt Nam thời kỳ 1945–1975 – Wikipedia tiếng Việt$/gm, "");
  cleaned = cleaned.replace(/^Sách:\s*.*$/gm, "");
  cleaned = cleaned.replace(/^Abstract$/gm, "");
  cleaned = cleaned.replace(/^Thập niên\s*$/gmi, "");

  const lines = cleaned.split("\n");
  const cleanedLines: string[] = [];
  let inTable = false;
  let currentTableLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // Skip if line matches warning banners
    const lowerLine = line.toLowerCase();
    if (
      lowerLine.includes("chú thích nguồn gốc") ||
      lowerLine.includes("kiểm chứng thông tin") ||
      lowerLine.includes("bổ sung chú thích") ||
      lowerLine.includes("không có nguồn") ||
      lowerLine.includes("nguồn đáng tin cậy") ||
      lowerLine.includes("bị nghi ngờ và xóa bỏ") ||
      lowerLine.includes("xóa thông báo này") ||
      lowerLine.includes("bài viết này")
    ) {
      continue;
    }

    // TRUNCATION RULES (Wikipedia metadata and links end sections)
    const upperLine = line.toUpperCase();
    if (
      upperLine === "THƯ MỤC" || 
      upperLine === "ĐỌC THÊM" || 
      upperLine === "LIÊN KẾT NGOÀI" || 
      upperLine === "XEM THÊM" || 
      upperLine === "CHUYÊN KHẢO" || 
      upperLine === "TUYỂN TẬP BIÊN KHẢO" || 
      upperLine === "NGUỒN SƠ CẤP" ||
      upperLine === "THAM KHẢO" ||
      upperLine === "CHÚ THÍCH" ||
      upperLine === "NGUỒN" ||
      line.startsWith("## Thư mục") ||
      line.startsWith("## Đọc thêm") ||
      line.startsWith("## Liên kết ngoài") ||
      line.startsWith("## Xem thêm") ||
      line.startsWith("## Tham khảo") ||
      line.startsWith("## Chú thích") ||
      line.startsWith("## Nguồn") ||
      line.startsWith("### Thư mục") ||
      line.startsWith("### Đọc thêm") ||
      line.startsWith("### Liên kết ngoài") ||
      line.startsWith("### Xem thêm") ||
      line.startsWith("### Tham khảo") ||
      line.startsWith("### Chú thích") ||
      line.startsWith("### Nguồn") ||
      line.startsWith("Thể loại:") ||
      line.startsWith("Thể loại ẩn:") ||
      line.startsWith("Cổng thông tin:") ||
      line.startsWith("Lấy từ “") ||
      line.includes("50 ngôn ngữ") ||
      line.includes("Thêm đề tài") ||
      line.includes("Tìm kiếm")
    ) {
      // Stop completely! Discard all remaining bibliography lists and metadata categories.
      break;
    }

    // Detect table blocks
    if (line.startsWith("|")) {
      if (!inTable) {
        inTable = true;
        currentTableLines = [lines[i]];
      } else {
        currentTableLines.push(lines[i]);
      }
      continue;
    } else {
      if (inTable) {
        inTable = false;
        const tableStr = currentTableLines.join("\n").toLowerCase();
        
        // Skip navigational, infobox, or quality warning tables
        const isNavigation = 
          tableStr.includes("loạt bài") || 
          tableStr.includes("một phần của") || 
          tableStr.includes("cổng thông tin") || 
          tableStr.includes("kháng chiến trong lịch sử") || 
          tableStr.includes("chuyên đề") || 
          tableStr.includes("lịch sử đông nam á") ||
          tableStr.includes("sửa dữ liệu") || 
          tableStr.includes("wikidata") ||
          tableStr.includes("lịch sử châu á") ||
          tableStr.includes("lịch sử các nước") ||
          tableStr.includes("tên gọi việt nam") ||
          tableStr.includes("bản mẫu") ||
          tableStr.includes("trung lập") || 
          tableStr.includes("tranh cãi") || 
          tableStr.includes("wiki hóa") ||
          tableStr.includes("gây tranh cãi") ||
          tableStr.includes("cần được") ||
          tableStr.includes("nguồn gốc") ||
          tableStr.includes("chú thích") ||
          tableStr.includes("x - t - s") ||
          // Infobox tables for states/countries/people
          tableStr.includes("quốc ca") ||
          tableStr.includes("thủ đô") ||
          tableStr.includes("tiền thân") ||
          tableStr.includes("kế tục") ||
          tableStr.includes("tuyên bố chủ quyền") ||
          tableStr.includes("chính phủ cách mạng") ||
          tableStr.includes("ngôn ngữ thông dụng") ||
          tableStr.includes("đơn vị tiền tệ") ||
          tableStr.includes("diện tích") ||
          // Infobox bullet-point row markers
          (tableStr.includes("• ") && tableStr.includes("thành lập")) ||
          (tableStr.includes("• ") && tableStr.includes("chủ tịch")) ||
          // Geographic/location infoboxes
          tableStr.includes("tọa độ") ||
          tableStr.includes("đỉnh cao nhất") ||
          tableStr.includes("hành chính") ||
          tableStr.includes("múi giờ") ||
          (tableStr.includes("địa lý") && tableStr.includes("vị trí"));

        if (!isNavigation) {
          cleanedLines.push(...currentTableLines);
        }
        currentTableLines = [];
      }
    }
    
    // Skip boilerplate sidebar template indicators
    if (line.includes("icon Cổng thông tin") || line.includes("flag Cổng thông tin") || line.includes("- x - t - s")) {
      continue;
    }
    
    // Skip bibliography reference numbers or inline author notes
    if (/^\^\s*(?:Việt|Phan|Đào|Trần|William|Tran|Peycam|Keith|Nguyen|Miller|Taylor|Goscha|Vu|Kort|Dror|Holcombe|Li|Asselin|Luu)/.test(line)) {
      continue;
    }

    // Skip empty lines or decade heading fragments
    if (line === "" && cleanedLines.length > 0 && cleanedLines[cleanedLines.length - 1] === "") {
      continue;
    }

    cleanedLines.push(lines[i]);
  }

  if (inTable) {
    const tableStr = currentTableLines.join("\n").toLowerCase();
    const isNavigation = 
      tableStr.includes("loạt bài") || 
      tableStr.includes("một phần của") || 
      tableStr.includes("cổng thông tin") ||
      tableStr.includes("trung lập") || 
      tableStr.includes("tranh cãi") ||
      tableStr.includes("chú thích") ||
      tableStr.includes("wiki hóa") ||
      tableStr.includes("quốc ca") ||
      tableStr.includes("thủ đô") ||
      tableStr.includes("tiền thân") ||
      tableStr.includes("kế tục") ||
      tableStr.includes("tuyên bố chủ quyền") ||
      tableStr.includes("ngôn ngữ thông dụng") ||
      tableStr.includes("đơn vị tiền tệ") ||
      tableStr.includes("tọa độ") ||
      tableStr.includes("đỉnh cao nhất") ||
      tableStr.includes("múi giờ") ||
      (tableStr.includes("địa lý") && tableStr.includes("vị trí"));
    if (!isNavigation) {
      cleanedLines.push(...currentTableLines);
    }
  }

  let finalContent = cleanedLines.join("\n");
  finalContent = finalContent.replace(/\n{3,}/g, "\n\n");
  return finalContent.trim();
}

export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { getDocument, deleteDocument } = useDocumentStore()
  const [document, setDocument] = useState<(Document & { markdown_content?: string | null }) | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLatexMode, setIsLatexMode] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showConfirmDelete, setShowConfirmDelete] = useState(false)
  const [copiedRaw, setCopiedRaw] = useState(false)
  const [copiedLatex, setCopiedLatex] = useState(false)

  useEffect(() => {
    if (id) {
      getDocument(id).then(setDocument).finally(() => setIsLoading(false))
    }
  }, [id, getDocument])

  const prettyTitle = useMemo(() => {
    return document ? decodeTitle(document.title) : ""
  }, [document?.title])

  const cleanedLatexMarkdown = useMemo(() => {
    return parseAndCleanToLatex(document?.markdown_content || "")
  }, [document?.markdown_content])

  const handleCopyRaw = useCallback(async () => {
    if (!document?.markdown_content) return
    try {
      await navigator.clipboard.writeText(document.markdown_content)
      setCopiedRaw(true)
      setTimeout(() => setCopiedRaw(false), 2000)
    } catch (err) {
      console.error("Failed to copy raw text: ", err)
    }
  }, [document?.markdown_content])

  const handleCopyLatex = useCallback(async () => {
    if (!cleanedLatexMarkdown) return
    try {
      await navigator.clipboard.writeText(cleanedLatexMarkdown)
      setCopiedLatex(true)
      setTimeout(() => setCopiedLatex(false), 2000)
    } catch (err) {
      console.error("Failed to copy LaTeX text: ", err)
    }
  }, [cleanedLatexMarkdown])

  const academicLatexView = useMemo(() => {
    if (!document) return null
    return (
      <div className="bg-white rounded-2xl border border-[#e7e1d8] shadow-md px-10 py-16 md:px-14 md:py-20 latex-paper relative overflow-hidden">
        {/* Copy Button */}
        <div className="absolute top-4 right-4 z-10">
          <button
            onClick={handleCopyLatex}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl transition-all duration-200 border shadow-sm active:scale-95 bg-white",
              copiedLatex
                ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                : "text-stone-500 border-stone-200 hover:text-stone-850 hover:bg-stone-50"
            )}
            title="Sao chép nội dung học thuật đã làm sạch"
          >
            {copiedLatex ? (
              <>
                <Check className="w-3.5 h-3.5" />
                Đã sao chép
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                Sao chép bản sạch
              </>
            )}
          </button>
        </div>
        {/* Visual A4 paper corner marker */}
        <div className="absolute top-0 right-0 w-16 h-16 pointer-events-none border-t border-r border-[#e7e1d8]/40" />

        {/* Paper Header Title */}
        <div className="text-center mb-10">
          <h1 className="font-display text-3.5xl md:text-4xl text-stone-900 font-normal tracking-tight leading-tight max-w-2xl mx-auto my-3">
            {prettyTitle}
          </h1>
          <div className="text-stone-600 text-sm font-serif italic mt-3.5 flex items-center justify-center gap-1.5">
            <span>{document.author || "Hệ thống Tri thức Lịch sử Việt"}</span>
            {document.source_domain && (
              <>
                <span>•</span>
                <span>{document.source_domain}</span>
              </>
            )}
          </div>
          <div className="text-stone-500 text-xs font-serif mt-1">
            {formatDate(document.created_at)}
          </div>
          <div className="w-24 h-[1px] bg-stone-300 mx-auto mt-7" />
        </div>

        {/* Abstract Section */}
        {document.summary && (
          <div className="mx-4 md:mx-10 my-8 text-justify border-y border-stone-100 py-6">
            <div className="text-center font-bold text-stone-950 uppercase tracking-widest text-[11px] mb-2.5 font-serif">
              Abstract
            </div>
            <p className="italic text-stone-700 text-sm leading-relaxed font-serif indent-0">
              {document.summary}
            </p>
          </div>
        )}

        {/* Main Body Text Content */}
        <div className="latex-compiled-body prose prose-stone max-w-none text-stone-900 leading-relaxed font-serif text-[15px]">
          {cleanedLatexMarkdown ? (
            <MemoizedReactMarkdown
              content={cleanedLatexMarkdown}
              components={latexMarkdownComponents}
            />
          ) : (
            <div className="text-center text-stone-400 py-10 font-serif italic">
              Nội dung văn kiện trống
            </div>
          )}
        </div>

        {/* Final End Of Paper Document Tag */}
        <div className="text-center font-mono text-[10px] text-[#cc785c] tracking-widest mt-16 pt-6 border-t border-stone-100 select-none">
          \end{'{'}document{'}'}
        </div>
      </div>
    )
  }, [prettyTitle, cleanedLatexMarkdown, document, copiedLatex, handleCopyLatex])

  const rawMarkdownView = useMemo(() => {
    if (!document) return null
    return (
      <div className="space-y-6">
        {/* Metadata Attributes Card */}
        <div className="bg-white rounded-2xl p-6 border border-[#e7e1d8] shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[4px] bg-[var(--coral)]" />
          <h3 className="font-bold text-[#2d2a26] mb-5 text-sm flex items-center gap-2.5 border-b border-[#f5f1ea] pb-3">
            <FileText className="w-4 h-4 text-[#8a8175]" />
            Thuộc tính tư liệu RAG
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {document.author && (
              <div className="flex items-center gap-2.5 text-sm bg-stone-50/50 p-2.5 rounded-xl border border-[#f5f1ea]">
                <User className="w-4 h-4 text-[#8a8175] flex-shrink-0" />
                <span className="text-[#8a8175] font-medium">Tác giả:</span>
                <span className="text-[#2d2a26] font-bold">{document.author}</span>
              </div>
            )}
            {document.source_type && (
              <div className="flex items-center gap-2.5 text-sm bg-stone-50/50 p-2.5 rounded-xl border border-[#f5f1ea]">
                <BookOpen className="w-4 h-4 text-[#8a8175] flex-shrink-0" />
                <span className="text-[#8a8175] font-medium">Loại tệp:</span>
                <span className="text-[#2d2a26] font-bold capitalize">{document.source_type}</span>
              </div>
            )}
            {document.detected_years && document.detected_years.length > 0 && (
              <div className="flex items-center gap-2.5 text-sm bg-stone-50/50 p-2.5 rounded-xl border border-[#f5f1ea]">
                <Calendar className="w-4 h-4 text-[#8a8175] flex-shrink-0" />
                <span className="text-[#8a8175] font-medium">Năm phát hiện:</span>
                <span className="text-[#2d2a26] font-bold">{document.detected_years.join(", ")}</span>
              </div>
            )}
            {document.quality_score > 0 && (
              <div className="flex items-center gap-2.5 text-sm bg-stone-50/50 p-2.5 rounded-xl border border-[#f5f1ea]">
                <Award className="w-4 h-4 text-[#8a8175] flex-shrink-0" />
                <span className="text-[#8a8175] font-medium">Chất lượng tệp:</span>
                <span className="text-emerald-600 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                  {(document.quality_score * 100).toFixed(0)}%
                </span>
              </div>
            )}
          </div>

          {document.tags && document.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-5 pt-4 border-t border-[#f5f1ea]">
              {document.tags.map((tag) => (
                <span
                  key={tag}
                  className={cn(
                    "px-3 py-1 text-xs rounded-md font-medium transition-all shadow-sm",
                    getTagClass(tag)
                  )}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Entities Card */}
        {(document.entity_persons?.length || document.entity_places?.length || document.entity_organizations?.length) && (
          <div className="bg-white rounded-2xl p-6 border border-[#e7e1d8] shadow-sm">
            <h3 className="font-bold text-[#2d2a26] mb-4 text-sm flex items-center gap-2 border-b border-[#f5f1ea] pb-3">
              <Sparkles className="w-4 h-4 text-[#8a8175]" />
              Thực thể Lịch sử nhận diện tự động
            </h3>
            <div className="space-y-4">
              {document.entity_persons && document.entity_persons.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <User className="w-3.5 h-3.5 text-[#8a8175]" />
                    <span className="text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider">Nhân vật lịch sử</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {document.entity_persons.map((p) => (
                      <span key={p} className="px-3 py-1 text-xs bg-[#eefcf7] text-[#0f7652] rounded-lg border border-[#d2f3e8] shadow-sm font-medium">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {document.entity_places && document.entity_places.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <MapPin className="w-3.5 h-3.5 text-[#8a8175]" />
                    <span className="text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider">Địa danh lịch sử</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {document.entity_places.map((p) => (
                      <span key={p} className="px-3 py-1 text-xs bg-[#fdf6e2] text-[#b28b2a] rounded-lg border border-[#f5ebcd] shadow-sm font-medium">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {document.entity_organizations && document.entity_organizations.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Globe className="w-3.5 h-3.5 text-[#8a8175]" />
                    <span className="text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider">Tổ chức liên quan</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {document.entity_organizations.map((p) => (
                      <span key={p} className="px-3 py-1 text-xs bg-stone-50 text-stone-600 rounded-lg border border-[#e7e1d8] shadow-sm font-medium">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Summary */}
        {document.summary && (
          <div className="bg-white rounded-2xl p-6 border border-[#e7e1d8] shadow-sm">
            <h3 className="font-bold text-[#2d2a26] mb-3.5 text-sm border-b border-[#f5f1ea] pb-2">Tóm lược tư liệu</h3>
            <p className="text-[#6f675d] leading-relaxed text-sm">{document.summary}</p>
          </div>
        )}

        {/* Raw Markdown */}
        {document.markdown_content && (
          <div className="bg-white rounded-2xl p-7 border border-[#e7e1d8] shadow-sm">
            <div className="flex justify-between items-center mb-5 border-b border-[#f5f1ea] pb-3">
              <h3 className="font-bold text-[#2d2a26] text-sm">Nội dung văn kiện (Raw Markdown)</h3>
              <button
                onClick={handleCopyRaw}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl transition-all duration-200 border shadow-sm active:scale-95",
                  copiedRaw
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : "bg-white text-stone-700 border-[#e7e1d8] hover:bg-[#FAF9F5] hover:text-[#2d2a26]"
                )}
                title="Sao chép toàn bộ nội dung"
              >
                {copiedRaw ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    Đã sao chép
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    Sao chép dữ liệu
                  </>
                )}
              </button>
            </div>
            <div className="prose prose-stone prose-sm max-w-none prose-headings:text-[#2d2a26] prose-p:text-[#6f675d] prose-a:text-[var(--coral)] prose-strong:text-stone-900 leading-relaxed text-sm">
              <MemoizedReactMarkdown content={document.markdown_content} />
            </div>
          </div>
        )}
      </div>
    )
  }, [document, copiedRaw, handleCopyRaw])

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#FAF9F5] gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--coral)]" />
        <span className="text-sm font-semibold text-[#8a8175]">Đang đọc dữ liệu tài liệu...</span>
      </div>
    )
  }

  if (!document) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#FAF9F5] text-[#8a8175] p-6 text-center">
        <FileText className="w-14 h-14 text-stone-300 mb-4" />
        <p className="font-bold text-lg text-[#2d2a26]">Không tìm thấy tài liệu này</p>
        <p className="text-xs text-[#8a8175] mt-1 max-w-xs">
          Tài liệu có thể đã bị xóa hoặc không khả dụng trong hệ thống tri thức.
        </p>
        <button
          onClick={() => navigate("/documents")}
          className="mt-5 px-5 py-2.5 bg-[#2f2a25] text-white font-semibold rounded-xl hover:bg-stone-800 transition-all text-sm shadow-sm"
        >
          Quay lại danh sách tài liệu
        </button>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-[#FAF9F5]">
      {/* Header */}
      <header className="px-8 py-5 border-b border-[#e7e1d8] bg-white flex items-center gap-4 shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
        <button
          onClick={() => navigate("/documents")}
          className="p-2 hover:bg-[#f5f1ea] rounded-xl transition-all border border-transparent hover:border-[#e7e1d8] flex-shrink-0"
          title="Quay lại danh sách"
        >
          <ArrowLeft className="w-5 h-5 text-[#6f675d]" />
        </button>
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-bold text-[#2d2a26] truncate">{prettyTitle}</h2>
          <div className="flex items-center gap-2 text-xs text-[#aaa39a] font-medium mt-0.5">
            {document.source_domain && <span className="text-[#8a8175]">{document.source_domain}</span>}
            <span>·</span>
            <span>{formatDate(document.created_at)}</span>
          </div>
        </div>
        
        {/* Delete Button */}
        <button
          onClick={() => setShowConfirmDelete(true)}
          disabled={isDeleting}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold text-red-600 hover:text-white bg-red-50 hover:bg-red-600 border border-red-200 hover:border-red-600 rounded-xl transition-all shadow-sm flex-shrink-0 disabled:opacity-50"
        >
          {isDeleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
          {isDeleting ? "Đang xóa..." : "Xóa tài liệu"}
        </button>

        <span
          className={cn(
            "px-3 py-1.5 text-xs rounded-xl font-bold border flex-shrink-0 shadow-sm",
            document.status === "approved" && "bg-[#eefcf7] text-[#0f7652] border-[#d2f3e8]",
            document.status === "pending" && "bg-[#fffbeb] text-[#b25e09] border-[#fef3c7]",
            document.status === "rejected" && "bg-[#fef2f2] text-[#b91c1c] border-[#fee2e2]",
          )}
        >
          {document.status === "approved" && "✓ Đã duyệt"}
          {document.status === "pending" && "⏱ Chờ duyệt"}
          {document.status === "rejected" && "✕ Từ chối"}
        </span>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 md:p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Document Presentation Mode Switcher */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white border border-[#e7e1d8] rounded-2xl p-3 px-4 shadow-[0_1px_3px_rgba(0,0,0,0.01)] gap-3">
            <span className="text-xs font-bold text-[#6f675d] flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-[var(--coral)]" />
              Chế độ hiển thị văn bản:
            </span>
            <div className="flex bg-[#FAF9F5] p-1 rounded-xl border border-[#e7e1d8] w-full sm:w-auto">
              <button
                onClick={() => setIsLatexMode(true)}
                className={cn(
                  "flex-1 sm:flex-none px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5",
                  isLatexMode
                    ? "bg-white text-stone-900 shadow-sm border border-[#e7e1d8]"
                    : "text-[#8a8175] hover:text-[#6f675d]"
                )}
              >
                📄 Trình bày Academic LaTeX
              </button>
              <button
                onClick={() => setIsLatexMode(false)}
                className={cn(
                  "flex-1 sm:flex-none px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5",
                  !isLatexMode
                    ? "bg-white text-stone-900 shadow-sm border border-[#e7e1d8]"
                    : "text-[#8a8175] hover:text-[#6f675d]"
                )}
              >
                📝 Dữ liệu thô (Markdown)
              </button>
            </div>
          </div>

          {/* ========================================
             ACADEMIC LATEX COMPILED SHEET VIEW
             ======================================== */}
          <div style={{ display: isLatexMode ? "block" : "none" }} className="space-y-6">
            {academicLatexView}
          </div>

          {/* ========================================
             RAW STANDARD MARKDOWN DEVELOPER VIEW
             ======================================== */}
          <div style={{ display: !isLatexMode ? "block" : "none" }} className="space-y-6">
            {rawMarkdownView}
          </div>
        </div>
      </div>

      {/* Custom Confirmation Modal */}
      {showConfirmDelete && (
        <div 
          className="fixed inset-0 bg-black/45 backdrop-blur-[3px] z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => {
            if (!isDeleting) {
              setShowConfirmDelete(false)
            }
          }}
        >
          <div 
            className="bg-white rounded-3xl border border-[#e7e1d8] p-7 max-w-md w-full shadow-2xl animate-in zoom-in-95 slide-in-from-bottom-8 duration-300 text-center relative overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Visual accent background pattern */}
            <div className="absolute top-0 left-0 right-0 h-[6px] bg-red-600" />
            
            <div className="w-14 h-14 rounded-2xl bg-red-50 border border-red-100 flex items-center justify-center text-red-600 mb-5 mx-auto shadow-sm">
              <Trash2 className="w-6 h-6 animate-pulse" />
            </div>

            <h3 className="text-lg font-bold text-[#2d2a26] mb-2 leading-snug">
              Xóa tài liệu khỏi hệ thống?
            </h3>
            
            <p className="text-xs text-[#8a8175] font-medium px-1 mb-5">
              Bạn đang yêu cầu xóa tài liệu:
              <span className="block font-bold text-red-600 my-2 text-[13px] bg-red-50/50 py-2 px-3 rounded-lg border border-red-100/50 italic break-words">
                "{prettyTitle}"
              </span>
              Hành động này sẽ dọn sạch hoàn toàn các vector nhúng (Qdrant), chỉ mục BM25 (Elasticsearch), các tệp vật lý lưu trên ổ đĩa và các chunks trong PostgreSQL.
            </p>

            <div className="flex gap-3 justify-center">
              <button
                disabled={isDeleting}
                onClick={() => setShowConfirmDelete(false)}
                className="flex-1 px-4 py-2.5 bg-stone-50 hover:bg-stone-100 border border-[#e7e1d8] text-xs font-bold text-[#6f675d] rounded-xl transition-all shadow-sm disabled:opacity-50"
              >
                Hủy bỏ
              </button>
              <button
                disabled={isDeleting}
                onClick={async () => {
                  setIsDeleting(true)
                  try {
                    await deleteDocument(document!.id)
                    setShowConfirmDelete(false)
                    navigate("/documents")
                  } catch (err) {
                    alert("Không thể xóa tài liệu: " + (err instanceof Error ? err.message : String(err)))
                    setIsDeleting(false)
                  }
                }}
                className="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 shadow-md shadow-red-200/50 disabled:opacity-50"
              >
                {isDeleting ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    Đang xóa...
                  </>
                ) : (
                  "Xác nhận xóa"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
