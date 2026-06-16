import sys
from pathlib import Path
from uuid import uuid4

# Add parent path to allow python imports from app
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.graph import KnowledgeNode, KnowledgeEdge
from app.services.graph.graph_service import _slugify

def seed():
    print(f"Connecting to database: {settings.SYNC_DATABASE_URL}")
    engine = create_engine(settings.SYNC_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Preparing node data...")
    nodes_data = [
        # Original 14 Nodes
        {"name": "Chiến dịch Hồ Chí Minh", "type": "Event", "desc": "Chiến dịch quân sự cuối cùng trong Chiến tranh Việt Nam, giải phóng hoàn toàn miền Nam."},
        {"name": "Chiến dịch Tây Nguyên", "type": "Event", "desc": "Chiến dịch mở màn then chốt, tạo bước ngoặt chiến lược dẫn đến Chiến dịch Hồ Chí Minh."},
        {"name": "Chiến dịch Huế - Đà Nẵng", "type": "Event", "desc": "Chiến dịch tiến công tiêu diệt quân đoàn I quân lực Việt Nam Cộng hòa, tạo đà trực tiếp cho chiến dịch cuối."},
        {"name": "Đại tướng Văn Tiến Dũng", "type": "Person", "desc": "Tư lệnh Bộ chỉ huy Chiến dịch Hồ Chí Minh."},
        {"name": "Đại tướng Võ Nguyên Giáp", "type": "Person", "desc": "Tổng Tư lệnh Quân đội Nhân dân Việt Nam, người phê duyệt quyết định mở chiến dịch."},
        {"name": "Lê Duẩn", "type": "Person", "desc": "Tổng Bí thư Ban Chấp hành Trung ương Đảng, trực tiếp chỉ đạo chiến dịch giải phóng."},
        {"name": "Dương Văn Minh", "type": "Person", "desc": "Tổng thống cuối cùng của Việt Nam Cộng hòa, người tuyên bố đầu hàng không điều kiện vào trưa 30/4/1975."},
        {"name": "Sài Gòn - Gia Định", "type": "Location", "desc": "Địa bàn trọng điểm xảy ra toàn bộ năm hướng tiến công của Chiến dịch Hồ Chí Minh."},
        {"name": "Dinh Độc Lập", "type": "Location", "desc": "Nơi cắm lá cờ giải phóng lúc 11h30 ngày 30/4/1975, đánh dấu chiến dịch thành công."},
        {"name": "Xe tăng 390", "type": "Document", "desc": "Chiếc xe tăng húc đổ cổng Dinh Độc Lập trưa ngày 30/4/1975."},
        {"name": "Quân giải phóng miền Nam Việt Nam", "type": "Organization", "desc": "Lực lượng trực tiếp tham gia chiến đấu giải phóng miền Nam."},
        {"name": "Bộ Chính trị khóa III", "type": "Organization", "desc": "Cơ quan đầu não chỉ đạo trực tiếp toàn bộ cuộc Tổng tiến công và nổi dậy."},
        {"name": "30 tháng 4, 1975", "type": "Period", "desc": "Ngày kết thúc hoàn toàn Chiến dịch Hồ Chí Minh lịch sử."},
        {"name": "Chiến dịch giải phóng miền Nam", "type": "Event", "desc": "Cuộc tổng tiến công chiến lược vĩ đại mùa xuân năm 1975."},
        
        # Enriched Nodes
        {"name": "Chiến dịch Xuân 1975", "type": "Event", "desc": "Cuộc Tổng tiến công và nổi dậy giải phóng hoàn toàn miền Nam, thống nhất đất nước."},
        {"name": "Hiệp định Paris 1973", "type": "Document", "desc": "Hiệp định chấm dứt chiến tranh, lập lại hòa bình ở Việt Nam, buộc Mỹ rút quân tạo ưu thế chiến lược."},
        {"name": "Đại tướng Hoàng Văn Thái", "type": "Person", "desc": "Phó Tổng tư lệnh Quân đội Nhân dân Việt Nam, người giúp lập kế hoạch tác chiến chiến lược giải phóng miền Nam."},
        {"name": "Trung tướng Trần Văn Trà", "type": "Person", "desc": "Phó Tư lệnh Chiến dịch Hồ Chí Minh, trực tiếp chỉ huy hướng đông tiến công Sài Gòn."},
        {"name": "Bùi Quang Thận", "type": "Person", "desc": "Đại úy, người cắm lá cờ giải phóng trên nóc Dinh Độc Lập trưa ngày 30/4/1975."},
        {"name": "Lữ đoàn xe tăng 203", "type": "Organization", "desc": "Lực lượng tăng - thiết giáp dẫn đầu mũi đột kích thọc sâu vào trung tâm Sài Gòn."},
        {"name": "Quân đoàn 1", "type": "Organization", "desc": "Binh đoàn thọc sâu từ phía Bắc, tiến công đánh chiếm Bộ Tổng Tham mưu ngụy."},
        {"name": "Quân đoàn 2", "type": "Organization", "desc": "Quân đoàn tiến công từ hướng Đông, đánh chiếm Dinh Độc Lập phối hợp Lữ đoàn 203."},
        {"name": "Quân đoàn 3", "type": "Organization", "desc": "Quân đoàn tiến công từ hướng Tây Bắc, đánh chiếm Sân bay Tân Sơn Nhất."},
        {"name": "Quân đoàn 4", "type": "Organization", "desc": "Quân đoàn tiến công từ hướng Đông và Đông Bắc, vượt qua Biên Hòa đánh vào Biên Hòa và Sài Gòn."},
        {"name": "Đoàn 232", "type": "Organization", "desc": "Binh đoàn cánh Tây Nam tiến vào Sài Gòn đánh chiếm Biệt khu Thủ đô."},
        {"name": "Xuân Lộc", "type": "Location", "desc": "Cánh cửa thép phía Đông của Sài Gòn, nơi diễn ra trận chiến đập tan lá chắn phòng thủ của địch."},
        {"name": "Biên Hòa", "type": "Location", "desc": "Căn cứ quân sự khổng lồ ở cửa ngõ Sài Gòn, điểm tiến công quyết định của Quân đoàn 4."},
        {"name": "Sân bay Tân Sơn Nhất", "type": "Location", "desc": "Căn cứ không quân huyết mạch bị khống chế hoàn toàn bởi pháo binh và phi đội Quyết Thắng."},
        {"name": "Phi đội Quyết Thắng", "type": "Organization", "desc": "Phi đội máy bay A-37 tịch thu của địch ném bom oanh tạc sân bay Tân Sơn Nhất chiều 28/4/1975."},
        {"name": "Nguyễn Thành Trung", "type": "Person", "desc": "Phi công tình báo ném bom Dinh Độc Lập ngày 8/4 và dẫn đầu Phi đội Quyết Thắng oanh tạc Tân Sơn Nhất."},
        {"name": "Cầu Thị Nghè", "type": "Location", "desc": "Cầu huyết mạch dẫn lối trực tiếp vào Dinh Độc Lập, địa điểm giao tranh quyết liệt trưa 30/4."},
        {"name": "Tàu Không Số", "type": "Document", "desc": "Hệ thống tàu vận tải thuộc đường Hồ Chí Minh trên biển, tiếp tế vũ khí cho chiến trường Nam Bộ."},
        {"name": "Bản Di chúc Bác Hồ", "type": "Document", "desc": "Di chúc thiêng liêng của Chủ tịch Hồ Chí Minh thúc giục toàn dân tiến lên giành thắng lợi cuối cùng."},
        {"name": "Lá cờ giải phóng", "type": "Document", "desc": "Cờ Mặt trận Dân tộc Giải phóng miền Nam Việt Nam tung bay trên Dinh Độc Lập."},
    ]

    print("Cleaning up old seeder records dynamically to prevent UniqueConstraint errors...")
    for nd in nodes_data:
        slug = _slugify(nd["name"])
        node = session.query(KnowledgeNode).filter_by(slug=slug).first()
        if node:
            # Delete any existing edges associated with this node
            session.query(KnowledgeEdge).filter(
                (KnowledgeEdge.source_id == node.id) | (KnowledgeEdge.target_id == node.id)
            ).delete(synchronize_session=False)
            session.delete(node)
    session.commit()
    print("Cleanup successful.")

    print("Creating historical nodes...")
    created_nodes = {}
    for nd in nodes_data:
        slug = _slugify(nd["name"])
        node = KnowledgeNode(
            id=str(uuid4()),
            node_type=nd["type"],
            name=nd["name"],
            slug=slug,
            description=nd["desc"]
        )
        session.add(node)
        created_nodes[nd["name"]] = node
    session.commit()
    print(f"Successfully created {len(created_nodes)} nodes.")

    print("Creating historical edges (relations)...")
    edges_data = [
        # Core Center Event relationships (Outgoings)
        ("Chiến dịch Hồ Chí Minh", "30 tháng 4, 1975", "LED_TO"),
        ("Chiến dịch Hồ Chí Minh", "Dinh Độc Lập", "HAPPENED_AT"),
        ("Chiến dịch Hồ Chí Minh", "Sài Gòn - Gia Định", "HAPPENED_AT"),
        ("Chiến dịch Hồ Chí Minh", "Dương Văn Minh", "RELATED_TO"),
        ("Chiến dịch Hồ Chí Minh", "Chiến dịch giải phóng miền Nam", "PART_OF"),
        ("Chiến dịch Hồ Chí Minh", "Đại tướng Võ Nguyên Giáp", "LED_BY"),
        ("Chiến dịch Hồ Chí Minh", "Đại tướng Văn Tiến Dũng", "LED_BY"),
        ("Chiến dịch Hồ Chí Minh", "Lê Duẩn", "LED_BY"),
        ("Chiến dịch Hồ Chí Minh", "Xe tăng 390", "PARTICIPATED_IN"),
        ("Chiến dịch Hồ Chí Minh", "Bộ Chính trị khóa III", "LED_BY"),
        ("Chiến dịch Hồ Chí Minh", "Quân giải phóng miền Nam Việt Nam", "PARTICIPATED_IN"),

        # Enriched Node links pointing out from HCM Campaign
        ("Chiến dịch Hồ Chí Minh", "Bùi Quang Thận", "RELATED_TO"),
        ("Chiến dịch Hồ Chí Minh", "Trung tướng Trần Văn Trà", "LED_BY"),
        ("Chiến dịch Hồ Chí Minh", "Lữ đoàn xe tăng 203", "PARTICIPATED_IN"),
        ("Chiến dịch Hồ Chí Minh", "Quân đoàn 1", "PARTICIPATED_IN"),
        ("Chiến dịch Hồ Chí Minh", "Quân đoàn 2", "PARTICIPATED_IN"),
        ("Chiến dịch Hồ Chí Minh", "Quân đoàn 3", "PARTICIPATED_IN"),
        ("Chiến dịch Hồ Chí Minh", "Quân đoàn 4", "PARTICIPATED_IN"),
        ("Chiến dịch Hồ Chí Minh", "Đoàn 232", "PARTICIPATED_IN"),
        ("Chiến dịch Hồ Chí Minh", "Xuân Lộc", "HAPPENED_AT"),
        ("Chiến dịch Hồ Chí Minh", "Biên Hòa", "HAPPENED_AT"),
        ("Chiến dịch Hồ Chí Minh", "Sân bay Tân Sơn Nhất", "HAPPENED_AT"),
        ("Chiến dịch Hồ Chí Minh", "Phi đội Quyết Thắng", "PARTICIPATED_IN"),
        ("Chiến dịch Hồ Chí Minh", "Lá cờ giải phóng", "RELATED_TO"),

        # Sequential events pointing to HCM Campaign
        ("Chiến dịch Tây Nguyên", "Chiến dịch Hồ Chí Minh", "LED_TO"),
        ("Chiến dịch Huế - Đà Nẵng", "Chiến dịch Hồ Chí Minh", "LED_TO"),
        ("Chiến dịch Hồ Chí Minh", "Chiến dịch Xuân 1975", "PART_OF"),

        # Detailed tactical relationships
        ("Hiệp định Paris 1973", "Chiến dịch Xuân 1975", "LED_TO"),
        ("Bộ Chính trị khóa III", "Chiến dịch Xuân 1975", "LED_BY"),
        ("Đại tướng Võ Nguyên Giáp", "Đại tướng Hoàng Văn Thái", "RELATED_TO"),
        ("Bộ Chính trị khóa III", "Đại tướng Hoàng Văn Thái", "LED_BY"),
        ("Lữ đoàn xe tăng 203", "Xe tăng 390", "PART_OF"),
        ("Lữ đoàn xe tăng 203", "Bùi Quang Thận", "LED_BY"),
        ("Bùi Quang Thận", "Lá cờ giải phóng", "SIGNED_BY"),
        ("Bùi Quang Thận", "Dinh Độc Lập", "HAPPENED_AT"),
        ("Xe tăng 390", "Dinh Độc Lập", "HAPPENED_AT"),
        ("Quân đoàn 2", "Lữ đoàn xe tăng 203", "RELATED_TO"),
        
        # Additional tactical points
        ("Quân đoàn 3", "Sân bay Tân Sơn Nhất", "HAPPENED_AT"),
        ("Quân đoàn 4", "Biên Hòa", "HAPPENED_AT"),
        ("Quân đoàn 4", "Xuân Lộc", "HAPPENED_AT"),
        ("Trung tướng Trần Văn Trà", "Quân đoàn 2", "RELATED_TO"),
        ("Trung tướng Trần Văn Trà", "Quân đoàn 4", "RELATED_TO"),
        ("Phi đội Quyết Thắng", "Sân bay Tân Sơn Nhất", "HAPPENED_AT"),
        ("Nguyễn Thành Trung", "Phi đội Quyết Thắng", "LED_BY"),
        ("Nguyễn Thành Trung", "Dinh Độc Lập", "HAPPENED_AT"),
        ("Quân đoàn 2", "Cầu Thị Nghè", "HAPPENED_AT"),
        ("Cầu Thị Nghè", "Dinh Độc Lập", "LED_TO"),
        ("Tàu Không Số", "Quân giải phóng miền Nam Việt Nam", "RELATED_TO"),
        ("Bản Di chúc Bác Hồ", "Chiến dịch giải phóng miền Nam", "RELATED_TO"),
    ]

    edges_count = 0
    for src_name, tgt_name, edge_type in edges_data:
        src_node = created_nodes.get(src_name)
        tgt_node = created_nodes.get(tgt_name)
        if src_node and tgt_node:
            edge = KnowledgeEdge(
                id=str(uuid4()),
                source_id=src_node.id,
                target_id=tgt_node.id,
                edge_type=edge_type,
            )
            session.add(edge)
            edges_count += 1
    session.commit()
    print(f"Successfully created {edges_count} relations.")
    print("Database seeding finished successfully!")

if __name__ == "__main__":
    seed()
