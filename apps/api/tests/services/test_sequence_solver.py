import pytest
from app.services.timeline.sequence_solver import ChronologicalSequenceSolver

def test_chronological_ordering():
    solver = ChronologicalSequenceSolver()
    events = [
        {"name": "Thành lập triều Nguyễn", "year": 1802},
        {"name": "Trận Ngọc Hồi Đống Đa", "year": 1789}
    ]
    sorted_events = solver.sort_and_validate(events)
    assert sorted_events[0]["year"] == 1789
