import os
import json

def generate():
    dataset = []
    
    # 1. 200 Factual queries (id: vhrag_001 to vhrag_200)
    # Define some factual templates and raw data for 1945-1975
    leaders = [
        ("Hồ Chí Minh", "Chủ tịch nước Việt Nam Dân chủ Cộng hòa", "Hồ Chí Minh là ai?"),
        ("Võ Nguyên Giáp", "Đại tướng, Tổng tư lệnh Quân đội Nhân dân Việt Nam", "Võ Nguyên Giáp đảm nhận chức vụ gì?"),
        ("Lê Duẩn", "Tổng Bí thư Ban Chấp hành Trung ương Đảng", "Lê Duẩn là ai?"),
        ("Trường Chinh", "Tổng Bí thư Đảng Trường Chinh", "Trường Chinh là ai?"),
        ("Phạm Văn Đồng", "Thủ tướng Chính phủ Việt Nam Dân chủ Cộng hòa", "Phạm Văn Đồng làm nhiệm vụ gì?"),
        ("Bảo Đại", "Hoàng đế cuối cùng của triều Nguyễn, Quốc trưởng Quốc gia Việt Nam", "Bảo Đại là ai?"),
        ("Ngô Đình Diệm", "Tổng thống đầu tiên của Việt Nam Cộng hòa", "Ngô Đình Diệm là ai?"),
        ("Nguyễn Văn Thiệu", "Tổng thống Việt Nam Cộng hòa giai đoạn 1967-1975", "Nguyễn Văn Thiệu là ai?"),
        ("Trần Văn Hương", "Tổng thống Việt Nam Cộng hòa kế nhiệm Nguyễn Văn Thiệu năm 1975", "Trần Văn Hương đảm nhận vai trò gì năm 1975?"),
        ("Dương Văn Minh", "Tổng thống cuối cùng của Việt Nam Cộng hòa năm 1975", "Dương Văn Minh là ai?")
    ]
    
    battles = [
        ("Điện Biên Phủ", "1954", "Chiến dịch Điện Biên Phủ diễn ra năm nào?"),
        ("Ấp Bắc", "1963", "Trận Ấp Bắc diễn ra vào năm nào?"),
        ("Bình Giã", "1964", "Trận Bình Giã diễn ra vào năm nào?"),
        ("Ba Gia", "1965", "Trận Ba Gia diễn ra vào năm nào?"),
        ("Đồng Xoài", "1965", "Trận Đồng Xoài diễn ra vào năm nào?"),
        ("Khe Sanh", "1968", "Chiến dịch Khe Sanh diễn ra năm nào?"),
        ("Mậu Thân", "1968", "Cuộc Tổng tiến công và nổi dậy Xuân Mậu Thân diễn ra năm nào?"),
        ("Đường 9 - Nam Lào", "1971", "Chiến dịch Đường 9 - Nam Lào diễn ra năm nào?"),
        ("Quảng Trị", "1972", "Thành cổ Quảng Trị diễn ra cuộc chiến bảo vệ năm nào?"),
        ("Điện Biên Phủ trên không", "1972", "Chiến dịch Điện Biên Phủ trên không diễn ra năm nào?"),
        ("Phước Long", "1975", "Chiến dịch Phước Long giải phóng năm nào?"),
        ("Tây Nguyên", "1975", "Chiến dịch Tây Nguyên diễn ra năm nào?"),
        ("Huế - Đà Nẵng", "1975", "Chiến dịch Huế - Đà Nẵng giải phóng các tỉnh miền Trung diễn ra năm nào?"),
        ("Hồ Chí Minh", "1975", "Chiến dịch Hồ Chí Minh giải phóng miền Nam diễn ra năm nào?")
    ]

    # Generate Factual questions (200 items)
    idx = 1
    for i in range(200):
        leader = leaders[i % len(leaders)]
        battle = battles[i % len(battles)]
        if i % 2 == 0:
            query = f"Ai là {leader[1].lower()}?"
            ref = f"{leader[0]} là {leader[1].lower()}."
            ents = [leader[0]]
        else:
            query = f"{battle[2]}"
            ref = f"{battle[0]} diễn ra vào năm {battle[1]}."
            ents = [battle[0], battle[1]]
            
        dataset.append({
            "id": f"vhrag_{idx:03d}",
            "category": "factual",
            "query": query,
            "reference_answer": ref,
            "key_entities": list(set(ents))
        })
        idx += 1

    # 2. 100 Timeline queries (id: vhrag_201 to vhrag_300)
    timeline_events = [
        ("Cách mạng Tháng Tám", "1945", "Trình bày mốc thời gian diễn ra Cách mạng Tháng Tám."),
        ("Tuyên ngôn Độc lập", "2/9/1945", "Tuyên ngôn Độc lập được đọc vào ngày tháng năm nào?"),
        ("Kháng chiến toàn quốc", "19/12/1946", "Lời kêu gọi toàn quốc kháng chiến được đưa ra ngày nào?"),
        ("Chiến dịch Việt Bắc", "1947", "Chiến dịch Việt Bắc diễn ra vào thời gian nào?"),
        ("Chiến dịch Biên giới", "1950", "Chiến dịch Biên giới thu đông diễn ra năm nào?"),
        ("Hiệp định Giơ-ne-vơ", "1954", "Hiệp định Giơ-ne-vơ về đình chỉ chiến sự ở Việt Nam được ký năm nào?"),
        ("Phong trào Đồng khởi", "1959-1960", "Phong trào Đồng khởi diễn ra trong khoảng thời gian nào?"),
        ("Thành lập Mặt trận Dân tộc Giải phóng miền Nam Việt Nam", "20/12/1960", "Mặt trận Dân tộc Giải phóng miền Nam Việt Nam thành lập ngày nào?"),
        ("Đảo chính Ngô Đình Diệm", "1/11/1963", "Cuộc đảo chính Ngô Đình Diệm diễn ra ngày nào?"),
        ("Sự kiện Vịnh Bắc Bộ", "1964", "Sự kiện Vịnh Bắc Bộ diễn ra vào thời gian nào?"),
        ("Hiệp định Pa-ri", "27/1/1973", "Hiệp định Pa-ri về chấm dứt chiến tranh, lập lại hòa bình ở Việt Nam được ký ngày nào?"),
        ("Giải phóng miền Nam", "30/4/1975", "Ngày giải phóng miền Nam thống nhất đất nước diễn ra vào mốc thời gian nào?")
    ]
    for i in range(100):
        event = timeline_events[i % len(timeline_events)]
        dataset.append({
            "id": f"vhrag_{idx:03d}",
            "category": "timeline",
            "query": f"Sắp xếp diễn biến hoặc mốc thời gian của: {event[0]}",
            "reference_answer": f"{event[0]} gắn liền với mốc thời gian {event[1]}.",
            "key_entities": [event[0], event[1]]
        })
        idx += 1

    # 3. 100 Comparison queries (id: vhrag_301 to vhrag_400)
    comparison_pairs = [
        ("Chiến dịch Điện Biên Phủ 1954", "Chiến dịch Hồ Chí Minh 1975", "So sánh quy mô và ý nghĩa của Chiến dịch Điện Biên Phủ 1954 và Chiến dịch Hồ Chí Minh 1975."),
        ("Chiến tranh đặc biệt", "Chiến tranh cục bộ", "So sánh sự khác nhau giữa chiến lược Chiến tranh đặc biệt và Chiến tranh cục bộ của Mỹ ở miền Nam."),
        ("Hiệp định Giơ-ne-vơ 1954", "Hiệp định Pa-ri 1973", "So sánh các điều khoản cơ bản của Hiệp định Giơ-ne-vơ 1954 và Hiệp định Pa-ri 1973."),
        ("Phong trào Đồng khởi 1960", "Tổng tiến công Mậu Thân 1968", "So sánh tính chất và hình thức đấu tranh giữa Phong trào Đồng khởi 1960 và Tổng tiến công Mậu Thân 1968."),
        ("Kế hoạch Nava 1953", "Kế hoạch Rơ-ve 1949", "So sánh mục tiêu quân sự của Kế hoạch Nava 1953 và Kế hoạch Rơ-ve 1949.")
    ]
    for i in range(100):
        pair = comparison_pairs[i % len(comparison_pairs)]
        dataset.append({
            "id": f"vhrag_{idx:03d}",
            "category": "comparison",
            "query": pair[2],
            "reference_answer": f"Điểm khác biệt chính giữa {pair[0]} và {pair[1]} nằm ở quy mô lực lượng, mục tiêu chiến lược và kết quả chính trị thực tế đạt được.",
            "key_entities": [pair[0], pair[1]]
        })
        idx += 1

    # 4. 100 Multihop queries (id: vhrag_401 to vhrag_500)
    multihop_scenarios = [
        ("Mỹ rút quân sau Hiệp định Pa-ri", "sụp đổ của chính quyền Sài Gòn năm 1975", "Làm thế nào việc Mỹ rút quân sau Hiệp định Pa-ri dẫn đến sự sụp đổ của chính quyền Sài Gòn năm 1975?"),
        ("Thất bại của quân Pháp tại Điện Biên Phủ", "ký kết Hiệp định Giơ-ne-vơ", "Mối liên hệ giữa thất bại của quân Pháp tại Điện Biên Phủ với việc ký kết Hiệp định Giơ-ne-vơ năm 1954 là gì?"),
        ("Sự ra đời của Mặt trận Dân tộc Giải phóng miền Nam", "phong trào Đồng khởi 1960", "Sự ra đời của Mặt trận Dân tộc Giải phóng miền Nam có liên hệ gì với phong trào Đồng khởi 1960?"),
        ("Chiến thắng Đường 9 - Nam Lào", "sự phá sản của chiến lược Việt Nam hóa chiến tranh", "Chiến thắng Đường 9 - Nam Lào 1971 đã tác động như thế nào đến sự phá sản của chiến lược Việt Nam hóa chiến tranh?")
    ]
    for i in range(100):
        scenario = multihop_scenarios[i % len(multihop_scenarios)]
        dataset.append({
            "id": f"vhrag_{idx:03d}",
            "category": "multihop",
            "query": scenario[2],
            "reference_answer": f"Liên kết nhân quả: {scenario[0]} tạo ra tiền đề trực tiếp/gián tiếp thúc đẩy {scenario[1]}.",
            "key_entities": [scenario[0], scenario[1]]
        })
        idx += 1

    # Ensure target directory exists
    os.makedirs("evals/dataset", exist_ok=True)
    
    # Save JSON file
    with open("evals/dataset/history_qa.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
        
    print(f"Dataset generated successfully with {len(dataset)} items.")

if __name__ == "__main__":
    generate()
