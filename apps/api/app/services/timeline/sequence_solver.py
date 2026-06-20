class ChronologicalSequenceSolver:
    def sort_and_validate(self, events: list[dict]) -> list[dict]:
        # Filter valid events with year attributes
        valid_events = [e for e in events if e.get("year") is not None]
        return sorted(valid_events, key=lambda x: x["year"])
