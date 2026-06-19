# Bản thiết kế: Tái cấu trúc giao diện dòng thời gian (Timeline Split-Screen Redesign)

Bản tài liệu đặc tả thiết kế chi tiết (Spec) cho việc tối ưu hóa giao diện TimelinePage trên HistoriAI, giải quyết vấn đề khoảng trống thừa bên phải màn hình và kích thước thẻ sự kiện quá lớn.

---

## 1. Mục tiêu (Goals)
- Tận dụng tối đa không gian màn hình rộng trên máy tính bằng cách triển khai bố cục chia đôi màn hình (Split-Screen).
- Thu gọn kích thước thẻ sự kiện bên dòng thời gian (Timeline) để giao diện cô đọng và dễ theo dõi hơn.
- Hiển thị thông tin phân tích AI (RAG Insights, Sơ đồ liên kết tri thức) một cách trực quan, cố định ở cột bên phải mà không che khuất dòng thời gian chính.
- Đảm bảo trải nghiệm di động hoạt động mượt mà bằng cách tự động co về 1 cột và chuyển bảng phân tích thành Drawer/Bottom-sheet.

---

## 2. Đặc tả Bố cục & Cấu trúc (Layout & Structure)

### Trải nghiệm Desktop (Chiều rộng màn hình >= 1024px)
- **Cấu trúc lưới chính**: Sử dụng CSS Grid chia màn hình thành 10 phần (`grid grid-cols-10 h-[calc(100vh-180px)] overflow-hidden gap-6 bg-[#faf8f3]`).
- **Cột Trái (Dòng thời gian - 60% / `lg:col-span-6`)**:
  - Cuộn độc lập với class `h-full overflow-y-auto pr-4 scrollbar-thin`.
  - Giữ lại đường trục lịch sử dọc (`border-l-2 border-[#e8ddd0] ml-4`).
- **Cột Phải (Bảng AI Insights - 40% / `lg:col-span-4`)**:
  - Đứng yên (cố định), hiển thị thông tin chi tiết của mốc sự kiện được chọn.
  - Class: `h-full overflow-y-auto bg-white border border-[#e8ddd0] rounded-lg flex flex-col`.

### Trải nghiệm Mobile & Tablet (Chiều rộng màn hình < 1024px)
- Giao diện chuyển thành 1 cột duy nhất (`grid-cols-1`). Cột Timeline giãn hết cỡ.
- Cột AI Insights Panel bên phải tự động ẩn đi. Khi người dùng bấm vào một thẻ sự kiện, thông tin chi tiết sẽ được mở trong một Drawer/Bottom-sheet trượt lên từ dưới cùng màn hình.

---

## 3. Chi tiết thẻ sự kiện tối giản (Timeline Compact Cards)

Để thu nhỏ chiều cao thẻ và làm sạch giao diện, chúng tôi áp dụng thiết kế thẻ siêu tối giản (Compact Card):
- **Kích thước**: Thay đổi padding từ `p-4 pl-5` thành `p-2.5 pl-3.5 pr-2.5`. Khoảng cách giữa các thẻ trong năm giảm xuống còn `space-y-2`.
- **Lược bỏ thông tin**:
  - Bỏ phần tóm tắt (Summary) khỏi danh sách thẻ chính.
  - Bỏ phần footer chứa liên kết ("Xem liên kết & phân tích ->" hoặc "Khám phá ->") để tránh lặp lại hành vi.
- **Cấu trúc nội dung**:
  - Dòng 1 (Inline Flex): 
    - Nhãn danh mục (Category) siêu nhỏ bên trái (`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-[#f0eae1] text-[#5c544a]`).
    - Ngày tháng sự kiện bên phải (`font-mono text-[9px] text-[#a09589]`).
  - Dòng 2: Tiêu đề sự kiện (Title) sử dụng font Serif tinh tế (`font-serif text-[13px] font-bold text-[#1c1a17] leading-snug mt-1.5`).
- **Hiệu ứng Trạng thái**:
  - Hover: Nền đổi sang kem nhạt (`hover:bg-[#faf8f3]`), viền đổi sang màu cam đất nhạt (`hover:border-[#cc785c]/40`), di chuyển nhẹ sang phải 1px (`hover:translate-x-0.5`).
  - Selected (Được click chọn): Viền chuyển màu cam đậm (`border-[#cc785c]`), nền màu cam nhạt tinh tế (`bg-[#cc785c]/5`), vạch chỉ thị mép trái hiện rõ (`w-[3px] bg-[#cc785c]`), chữ tiêu đề chuyển màu cam (`text-[#cc785c]`).

---

## 4. Đặc tả Bảng phân tích AI Insights (AI Insights Panel)

Bảng cột phải chứa các khối thông tin chuyên sâu của sự kiện, được cấu trúc như sau:

### Trạng thái Mặc định (Chưa chọn sự kiện nào)
- Tiêu đề thời kỳ đang lọc hiện tại (ví dụ: "Kháng chiến chống Pháp (1945-1954)").
- **Biểu đồ phân bổ sự kiện (Stats Grid)**: Hiển thị tổng số mốc lịch sử trong thời kỳ và biểu đồ phân bổ loại sự kiện (Quân sự, Ngoại giao, Chính trị, Văn hóa) dạng thanh đo mỏng tinh giản.
- **Trợ lý AI gợi ý**: Danh sách 3 câu hỏi gợi ý để bắt đầu cuộc trò chuyện lịch sử.

### Trạng thái Chi tiết (Khi đã chọn một sự kiện cụ thể)
- **Phần đầu (Header)**: Tiêu đề đầy đủ của sự kiện (không giới hạn dòng), nhãn thời kỳ lịch sử và ngày tháng cụ thể.
- **Ý nghĩa lịch sử (Summary Block)**: Nội dung mô tả chi tiết của sự kiện (`summary`) hiển thị đầy đủ bằng font Serif nghiêng (`font-serif italic text-[12.5px] text-[#1c1a17]/90`), đặt trong khung nền bo góc mềm mại.
- **Mạng lưới tri thức (Knowledge Graph)**: Hiển thị sơ đồ các thực thể liên quan (Ví dụ: Nhân vật, Địa danh, Văn kiện) bay xung quanh sự kiện trung tâm.
- **Gợi ý RAG hỏi nhanh**: 2 thẻ câu hỏi nhanh phục vụ tính năng RAG giúp người dùng chuyển ngay đến khung chat để hỏi chi tiết hơn.
- **Chân trang cố định (Sticky Footer)**:
  - Nút "📖 Đọc tài liệu Wiki" (nếu có liên kết wiki).
  - Nút "💬 Hỏi AI Assistant" (chuyển hướng kèm bối cảnh chat).

---

## 5. Kế hoạch kiểm thử & Xác minh (Verification Plan)
- **Kiểm tra Responsive**: Xác minh giao diện hiển thị đúng 2 cột trên Desktop (>=1024px) và tự động ẩn cột phải, kích hoạt Drawer trên Mobile (<1024px).
- **Kiểm tra Trạng thái Thẻ**: Đảm bảo các hiệu ứng Hover, Selected hoạt động chính xác, màu sắc tương đồng với hệ thống màu chủ đạo của dự án.
- **Kiểm tra Cuộn độc lập**: Xác nhận cuộn danh sách sự kiện bên cột trái không ảnh hưởng đến vị trí hiển thị của bảng thông tin bên cột phải.
- **Kiểm tra Tính nhất quán dữ liệu**: Khi click chọn thẻ sự kiện bất kỳ ở cột trái, bảng AI Insights bên cột phải phải cập nhật ngay lập tức thông tin tương ứng.
