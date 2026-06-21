import pytest
from app.services.citation.verifier import CitationVerifier

def test_numeric_verification_integers():
    verifier = CitationVerifier()
    # Identical integers
    assert verifier._calculate_numeric_score("Năm 1975 giải phóng miền Nam", "Sự kiện diễn ra vào năm 1975") == 1.0
    # Mismatched integers
    assert verifier._calculate_numeric_score("Năm 1975 giải phóng miền Nam", "Sự kiện diễn ra vào năm 1972") == 0.0

def test_numeric_verification_decimals():
    verifier = CitationVerifier()
    # Float with dot vs float with comma
    assert verifier._calculate_numeric_score("Tăng trưởng 1.5% trong năm", "Đạt mức tăng trưởng 1,5 phần trăm") == 1.0
    assert verifier._calculate_numeric_score("Đạt 2,25 tỷ USD", "Số tiền là 2.25 tỷ") == 1.0
    # Mismatched float
    assert verifier._calculate_numeric_score("Tỷ lệ 1.5%", "Tỷ lệ là 1.8%") == 0.0

def test_numeric_verification_vietnamese_text():
    verifier = CitationVerifier()
    # Text number vs digits
    assert verifier._calculate_numeric_score("Có ba mươi lăm người tham gia", "Số lượng là 35 người") == 1.0
    assert verifier._calculate_numeric_score("Năm một nghìn chín trăm bảy mươi lăm", "Sự kiện diễn ra năm 1975") == 1.0
    assert verifier._calculate_numeric_score("Tăng trưởng một phẩy năm phần trăm", "Đạt mức 1.5%") == 1.0
    # Mixed textual and digits
    assert verifier._calculate_numeric_score("Được chia thành 3 phần", "Chia thành ba phần bằng nhau") == 1.0
