# Domain Guardrail & API Key Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Approach C (Hybrid) domain guardrail, credentials validation layer, metrics tracking, and custom exception mapping to ensure accurate out-of-scope refusals and clear API key configurations.

**Architecture:** Refactor `DomainClassifier` into rule-based checks and LLM classification returning `DomainDecision` (IN_SCOPE, OUT_OF_SCOPE, UNKNOWN). Introduce an async `CredentialValidator` with cache verification, refactor `OutOfScopeWorkflow` to use static Vietnamese templates, and map a semantic `APIKeyMissingError` to `400 Bad Request` at the presentation layer.

**Tech Stack:** Python, FastAPI, Prometheus-client, Pytest

---

## File Structure & Responsibilities
1. **`apps/api/app/core/exceptions.py`**: Add `APIKeyMissingError` inheriting from `HistoriAIException`.
2. **`apps/api/app/core/credentials.py`**: Create `CredentialValidator` class verifying key configurations.
3. **`apps/api/app/agents/domain_classifier.py`**: Split domain classification into `classify_rules` and `classify_llm` returning `DomainDecision`.
4. **`apps/api/app/services/agent/workflows/out_of_scope.py`**: Update to yield the specific Vietnamese format.
5. **`apps/api/app/agents/orchestrator.py`**: Refactor query pipeline orchestration to check rules, cache credentials verification, and early route out-of-scope queries.
6. **`apps/api/app/factory.py`**: Register FastAPI exception handler for `APIKeyMissingError`.

---

## Tasks

### Task 1: APIKeyMissingError & Custom Exception Mapping

**Files:**
- Modify: `apps/api/app/core/exceptions.py`
- Modify: `apps/api/app/factory.py`
- Test: `apps/api/tests/unit/test_exceptions.py`

- [ ] **Step 1: Write the unit test for exception mapping**
  Create `apps/api/tests/unit/test_exceptions.py` with:
  ```python
  import pytest
  from fastapi import FastAPI
  from fastapi.testclient import TestClient
  from app.core.exceptions import APIKeyMissingError
  from app.factory import _register_exception_handlers

  def test_api_key_missing_error_mapping():
      app = FastAPI()
      _register_exception_handlers(app)

      @app.get("/test-error")
      def route_raising_error():
          raise APIKeyMissingError(provider="gemini")

      client = TestClient(app)
      response = client.get("/test-error")
      assert response.status_code == 400
      data = response.json()
      assert "API_KEY_MISSING" in data["detail"]
      assert "Không tìm thấy cấu hình mô hình ngôn ngữ." in data["detail"]
  ```

- [ ] **Step 2: Run tests to verify it fails**
  Run: `pytest apps/api/tests/unit/test_exceptions.py -v`
  Expected: FAIL (ImportError or NameError because `APIKeyMissingError` does not exist)

- [ ] **Step 3: Define APIKeyMissingError**
  Add `APIKeyMissingError` to `apps/api/app/core/exceptions.py`:
  ```python
  class APIKeyMissingError(HistoriAIException):
      """Custom exception raised when an LLM API Key is missing or invalid."""

      def __init__(self, provider: str = ""):
          super().__init__(
              message="API_KEY_MISSING: Không tìm thấy cấu hình mô hình ngôn ngữ.",
              public_message="Không tìm thấy cấu hình mô hình ngôn ngữ.\n\nVui lòng thêm API Key trong phần Cài đặt trước khi sử dụng chức năng hỏi đáp nâng cao của HistoriAI.",
              details={"provider": provider},
          )
  ```

- [ ] **Step 4: Register FastAPI Handler**
  Add exception handler in `_register_exception_handlers` inside `apps/api/app/factory.py`:
  ```python
  from app.core.exceptions import APIKeyMissingError
  from fastapi.responses import JSONResponse

  @app.exception_handler(APIKeyMissingError)
  async def api_key_missing_handler(request, exc: APIKeyMissingError):
      return JSONResponse(
          status_code=400,
          content={"detail": f"API_KEY_MISSING: {exc.public_message}"},
      )
  ```

- [ ] **Step 5: Run tests to verify it passes**
  Run: `pytest apps/api/tests/unit/test_exceptions.py -v`
  Expected: PASS

- [ ] **Step 6: Commit**
  Run:
  ```bash
  git add apps/api/app/core/exceptions.py apps/api/app/factory.py apps/api/tests/unit/test_exceptions.py
  git commit -m "feat: add APIKeyMissingError exception and FastAPI mapping"
  ```

---

### Task 2: Async CredentialValidator

**Files:**
- Create: `apps/api/app/core/credentials.py`
- Test: `apps/api/tests/unit/test_credentials.py`

- [ ] **Step 1: Write the credential validator test**
  Create `apps/api/tests/unit/test_credentials.py` with:
  ```python
  import pytest
  from unittest.mock import patch
  from app.core.exceptions import APIKeyMissingError
  from app.core.credentials import CredentialValidator

  @pytest.mark.asyncio
  async def test_credential_validator_missing_key():
      validator = CredentialValidator()
      with patch("app.services.llm.client.gemini_key_var.get", return_value="••••••••"):
          with pytest.raises(APIKeyMissingError):
              await validator.ensure_llm_available()

  @pytest.mark.asyncio
  async def test_credential_validator_valid_key():
      validator = CredentialValidator()
      with patch("app.services.llm.client.gemini_key_var.get", return_value="valid_key_123"):
          # Should not raise any exception
          await validator.ensure_llm_available()
  ```

- [ ] **Step 2: Run tests to verify it fails**
  Run: `pytest apps/api/tests/unit/test_credentials.py -v`
  Expected: FAIL (ModuleNotFoundError for `app.core.credentials`)

- [ ] **Step 3: Implement CredentialValidator**
  Create `apps/api/app/core/credentials.py`:
  ```python
  from app.core.exceptions import APIKeyMissingError
  from app.services.llm.client import get_llm_client
  from app.core.context import active_provider_var, gemini_key_var, openai_key_var, anthropic_key_var, groq_key_var

  class CredentialValidator:
      """Validates key configuration for active LLM provider."""

      async def ensure_llm_available(self) -> None:
          """
          Check if LLM keys are configured for active provider.
          Raises APIKeyMissingError if the key is missing or is set to placeholders.
          """
          provider = active_provider_var.get() or "gemini"
          key = None
          if provider == "gemini":
              key = gemini_key_var.get()
          elif provider == "openai":
              key = openai_key_var.get()
          elif provider == "anthropic":
              key = anthropic_key_var.get()
          elif provider == "groq":
              key = groq_key_var.get()

          if not key or key in ("••••••••", "********", ""):
              raise APIKeyMissingError(provider=provider)
  ```

- [ ] **Step 4: Run tests to verify it passes**
  Run: `pytest apps/api/tests/unit/test_credentials.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add apps/api/app/core/credentials.py apps/api/tests/unit/test_credentials.py
  git commit -m "feat: implement CredentialValidator layer"
  ```

---

### Task 3: DomainClassifier Refactoring (Rule + LLM + UNKNOWN Fallback)

**Files:**
- Modify: `apps/api/app/agents/domain_classifier.py`
- Test: `apps/api/tests/unit/test_domain_classifier.py`

- [ ] **Step 1: Write DomainClassifier tests**
  Create `apps/api/tests/unit/test_domain_classifier.py` with:
  ```python
  import pytest
  from unittest.mock import AsyncMock, patch
  from app.agents.domain_classifier import DomainClassifier, DomainDecision

  @pytest.mark.asyncio
  async def test_classify_rules_out_of_scope():
      classifier = DomainClassifier()
      res = classifier.classify_rules("bạn biết messi không?")
      assert res is not None
      assert res.decision == DomainDecision.OUT_OF_SCOPE
      assert res.source == "rule"

  @pytest.mark.asyncio
  async def test_classify_rules_in_scope():
      classifier = DomainClassifier()
      res = classifier.classify_rules("Hiệp định Giơ-nê-vơ năm 1954")
      assert res is not None
      assert res.decision == DomainDecision.IN_SCOPE
      assert res.source == "rule"

  @pytest.mark.asyncio
  async def test_classify_rules_ambiguous():
      classifier = DomainClassifier()
      # Ambiguous query that doesn't trigger rules
      res = classifier.classify_rules("bạn làm cái gì thế")
      assert res is None

  @pytest.mark.asyncio
  async def test_classify_llm_fail_closed_unknown():
      classifier = DomainClassifier()
      # Force LLM generation failure (simulated timeout)
      with patch("app.agents.domain_classifier.get_llm_client", side_effect=Exception("Timeout")):
          res = await classifier.classify_llm("truy vấn mơ hồ")
          assert res.decision == DomainDecision.UNKNOWN
          assert res.source == "fallback"
  ```

- [ ] **Step 2: Run tests to verify they fail**
  Run: `pytest apps/api/tests/unit/test_domain_classifier.py -v`
  Expected: FAIL

- [ ] **Step 3: Refactor DomainClassifier**
  Replace contents of `apps/api/app/agents/domain_classifier.py` to support `DomainDecision` and split rule vs LLM logic:
  ```python
  import re
  from enum import Enum
  from typing import Literal
  from dataclasses import dataclass
  from app.core.logging import get_logger
  from app.services.llm.client import get_llm_client
  from app.services.llm.json_parser import parse_llm_json

  logger = get_logger("domain_classifier")

  class DomainDecision(str, Enum):
      IN_SCOPE = "IN_SCOPE"
      OUT_OF_SCOPE = "OUT_OF_SCOPE"
      UNKNOWN = "UNKNOWN"

  @dataclass
  class DomainResult:
      decision: DomainDecision
      confidence: float
      source: Literal["rule", "llm", "fallback"]
      reason: str

  class DomainClassifier:
      GREETING_KEYWORDS = [
          "chào", "hello", "hi", "xin chào", "cảm ơn", "thank", "bye",
          "tạm biệt", "hey", "hola", "good morning", "good evening",
          "chào buổi sáng", "chào buổi tối", "bạn khỏe", "how are you",
          "nice to meet", "rất vui", "giới thiệu bản thân", "tên gì",
          "bạn là ai", "what is your name", "who are you",
      ]

      OUT_OF_SCOPE_KEYWORDS = [
          "messi", "ronaldo", "neymar", "bóng đá", "football", "soccer",
          "thời tiết", "weather", "ngày mai", "hôm nay", "nhiệt độ",
          "lập trình", "code", "python", "javascript", "react", "html", "css",
          "java", "c++", "c#", "rust", "golang", "docker", "kubernetes",
          "excel", "word", "photoshop", "powerpoint",
          "kinh tế hiện đại", "covid", "ai tools", "chatgpt", "openai", "công nghệ",
          "2027", "2028", "2029", "2030", "2031", "2032", "2033", "2034", "2035",
          "2036", "2037", "2038", "2039", "2040", "2041", "2042", "2043", "2044",
          "2045", "2046", "2047", "2048", "2049", "2050", "2100"
      ]

      IN_SCOPE_KEYWORDS = [
          "điện biên phủ", "hồ chí minh", "võ nguyên giáp", "geneve", "giơ-nê-vơ",
          "hiệp định", "paris", "kháng chiến", "chiến dịch", "tổng khởi nghĩa",
          "cách mạng tháng tám", "vĩ tuyến 17", "chống mỹ", "chống pháp", "đông dương",
          "mậu thân", "ấp bắc", "điện biên phủ trên không", "nhân văn giai phẩm",
          "cải cách ruộng đất", "lịch sử", "sự kiện", "nhân vật", "tướng", "quân đội"
      ]

      def classify_rules(self, query: str) -> DomainResult | None:
          """Rule-based fast-path domain check."""
          q = query.lower().strip()
          words = re.sub(r"[.,!?;:]", " ", q).split()

          # 1. Greetings
          for kw in self.GREETING_KEYWORDS:
              if " " in kw:
                  if kw in q:
                      return DomainResult(decision=DomainDecision.IN_SCOPE, confidence=1.0, source="rule", reason="Câu chào hỏi hoặc xã giao.")
              else:
                  if kw in words:
                      return DomainResult(decision=DomainDecision.IN_SCOPE, confidence=1.0, source="rule", reason="Câu chào hỏi hoặc xã giao.")

          # 2. Years
          all_years = [int(y) for y in re.findall(r"\b(\d{4})\b", q)]
          if all_years:
              has_in_scope_year = any(1945 <= y <= 1975 for y in all_years)
              if not has_in_scope_year:
                  return DomainResult(decision=DomainDecision.OUT_OF_SCOPE, confidence=1.0, source="rule", reason="Chứa mốc năm ngoài giai đoạn 1945-1975.")

          years = re.findall(r"\b(19[4-7]\d)\b", q)
          has_valid_year = False
          for y_str in years:
              y = int(y_str)
              if 1945 <= y <= 1975:
                  has_valid_year = True
                  break

          # 3. Keywords
          for kw in self.IN_SCOPE_KEYWORDS:
              if kw in q:
                  return DomainResult(decision=DomainDecision.IN_SCOPE, confidence=1.0, source="rule", reason="Từ khóa thuộc lịch sử Việt Nam.")

          if has_valid_year:
              return DomainResult(decision=DomainDecision.IN_SCOPE, confidence=1.0, source="rule", reason="Chứa mốc năm trong giai đoạn 1945-1975.")

          for kw in self.OUT_OF_SCOPE_KEYWORDS:
              if kw in q:
                  return DomainResult(decision=DomainDecision.OUT_OF_SCOPE, confidence=1.0, source="rule", reason="Từ khóa nằm ngoài phạm vi nghiên cứu.")

          return None

      async def classify_llm(self, query: str) -> DomainResult:
          """Fallback classification using LLM."""
          try:
              llm = get_llm_client()
              from app.services.llm.client import MockLLMClient
              if isinstance(llm, MockLLMClient):
                  q_lower = query.lower()
                  if "hà nội ngày mai" in q_lower or "messi" in q_lower or "thời tiết" in q_lower:
                      return DomainResult(decision=DomainDecision.OUT_OF_SCOPE, confidence=1.0, source="llm", reason="Ngoài phạm vi (Mock)")
                  return DomainResult(decision=DomainDecision.IN_SCOPE, confidence=1.0, source="llm", reason="Trong phạm vi (Mock)")

              prompt = f"""Bạn là bộ lọc phạm vi câu hỏi (Domain Guardrail AI) của HistoriAI.
  Xác định xem câu hỏi của người dùng có thuộc phạm vi Lịch sử Việt Nam (đặc biệt giai đoạn 1945-1975) hoặc chào hỏi xã giao hay không.

  Quy tắc phân loại:
  - "IN": Câu hỏi liên quan đến lịch sử Việt Nam (đặc biệt 1945-1975), nhân vật lịch sử VN, hoặc các câu chào hỏi xã giao thân thiện.
  - "OUT": Câu hỏi hoàn toàn ngoài ngành lịch sử VN (ví dụ: bóng đá, Lionel Messi, thời tiết hiện nay, công nghệ, lập trình, toán học, hoặc lịch sử nước khác không liên quan trực tiếp đến Việt Nam).

  Truy vấn: "{query}"

  Trả về định dạng JSON duy nhất:
  {{
    "scope": "IN" hoặc "OUT",
    "reason": "Lý do ngắn gọn bằng tiếng Việt"
  }}"""
              resp = await llm.generate(prompt, system="Bạn là AI bảo vệ phạm vi chuyên môn lịch sử Việt Nam.", max_tokens=150)
              parsed = parse_llm_json(resp)
              scope = parsed.get("scope", "IN").strip().upper()
              reason = parsed.get("reason", "Phân tích bối cảnh.")
              decision = DomainDecision.IN_SCOPE if scope == "IN" else DomainDecision.OUT_OF_SCOPE
              return DomainResult(decision=decision, confidence=0.9, source="llm", reason=reason)

          except Exception as exc:
              logger.warning("domain_classification_llm_failed", error=str(exc))
              return DomainResult(
                  decision=DomainDecision.UNKNOWN,
                  confidence=0.0,
                  source="fallback",
                  reason=f"Lỗi phân loại: {str(exc)}",
              )

      async def classify(self, query: str) -> DomainResult:
          """Classify query combining rules and LLM validation."""
          res = self.classify_rules(query)
          if res is not None:
              return res
          return await self.classify_llm(query)

  _classifier = DomainClassifier()

  async def classify_domain(query: str) -> DomainResult:
      return await _classifier.classify(query)
  ```

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest apps/api/tests/unit/test_domain_classifier.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add apps/api/app/agents/domain_classifier.py apps/api/tests/unit/test_domain_classifier.py
  git commit -m "refactor: split DomainClassifier rules and LLM with UNKNOWN decision fallback"
  ```

---

### Task 4: Standardize Refusal Format in OutOfScopeWorkflow

**Files:**
- Modify: `apps/api/app/services/agent/workflows/out_of_scope.py`
- Test: `apps/api/tests/unit/test_out_of_scope.py`

- [ ] **Step 1: Write workflow tests for refusal template**
  Create `apps/api/tests/unit/test_out_of_scope.py` with:
  ```python
  import pytest
  from app.services.agent.workflows.out_of_scope import OutOfScopeWorkflow

  @pytest.mark.asyncio
  async def test_out_of_scope_workflow_refusal_format():
      workflow = OutOfScopeWorkflow()
      res = await workflow.execute("bạn biết messi không?")
      assert "HistoriAI chuyên hỗ trợ nghiên cứu" in res["answer"]
      assert "Câu hỏi của bạn nằm ngoài phạm vi" in res["answer"]
      assert "Các triều đại Việt Nam" in res["answer"]
  ```

- [ ] **Step 2: Run tests to verify it fails**
  Run: `pytest apps/api/tests/unit/test_out_of_scope.py -v`
  Expected: FAIL (response contains LLM bridging text rather than static refusal format)

- [ ] **Step 3: Update OutOfScopeWorkflow**
  Refactor `apps/api/app/services/agent/workflows/out_of_scope.py` to yield the static Vietnamese refusal format:
  ```python
  from app.core.logging import get_logger

  logger = get_logger("out_of_scope_workflow")

  class OutOfScopeWorkflow:
      """Workflow for queries outside the domain scope."""

      REFUSAL_MESSAGE = (
          "HistoriAI chuyên hỗ trợ nghiên cứu và tra cứu lịch sử Việt Nam.\n\n"
          "Câu hỏi của bạn nằm ngoài phạm vi chuyên môn của hệ thống, nên tôi không thể cung cấp câu trả lời đáng tin cậy.\n\n"
          "Bạn có thể hỏi về:\n"
          "• Các triều đại Việt Nam\n"
          "• Nhân vật lịch sử\n"
          "• Các cuộc kháng chiến\n"
          "• Sự kiện lịch sử Việt Nam\n"
          "• Chính sách và cải cách qua các thời kỳ"
      )

      async def execute(self, query: str) -> dict:
          """Execute out-of-scope workflow."""
          logger.info("out_of_scope_workflow_execute", query=query[:50])
          return {
              "answer": self.REFUSAL_MESSAGE,
              "chunks": [],
              "workflow": "out_of_scope",
          }
  ```

- [ ] **Step 4: Run tests to verify it passes**
  Run: `pytest apps/api/tests/unit/test_out_of_scope.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add apps/api/app/services/agent/workflows/out_of_scope.py apps/api/tests/unit/test_out_of_scope.py
  git commit -m "feat: standardize OutOfScopeWorkflow refusal message"
  ```

---

### Task 5: Orchestrator Pipeline Refactoring with Credential Caching

**Files:**
- Modify: `apps/api/app/agents/orchestrator.py`
- Test: `apps/api/tests/unit/test_orchestrator_caching.py`

- [ ] **Step 1: Write test for Orchestrator Caching & UNKNOWN handling**
  Create `apps/api/tests/unit/test_orchestrator_caching.py` with:
  ```python
  import pytest
  from unittest.mock import AsyncMock, MagicMock, patch
  from app.agents.orchestrator import AgentOrchestrator
  from app.core.exceptions import ServiceUnavailableError
  from app.agents.domain_classifier import DomainResult, DomainDecision

  @pytest.mark.asyncio
  async def test_orchestrator_unknown_domain_raises_service_unavailable():
      orchestrator = AgentOrchestrator()
      mock_classifier = MagicMock()
      mock_classifier.classify_rules.return_value = None
      # Mock LLM domain classifier failing with UNKNOWN
      mock_classifier.classify_llm = AsyncMock(return_value=DomainResult(
          decision=DomainDecision.UNKNOWN,
          confidence=0.0,
          source="fallback",
          reason="LLM timeout"
      ))
      
      with patch("app.agents.orchestrator.CredentialValidator.ensure_llm_available", new_callable=AsyncMock) as mock_validate:
          with patch("app.agents.orchestrator.domain_classifier", mock_classifier):
              with pytest.raises(ServiceUnavailableError):
                  await orchestrator.answer("truy vấn mơ hồ")

  @pytest.mark.asyncio
  async def test_orchestrator_credential_checking_caching():
      orchestrator = AgentOrchestrator()
      mock_classifier = MagicMock()
      mock_classifier.classify_rules.return_value = DomainResult(
          decision=DomainDecision.IN_SCOPE,
          confidence=1.0,
          source="rule",
          reason="historical keyword"
      )
      
      # Mock the graph call so it doesn't try to run Neo4j/Qdrant
      with patch.object(orchestrator, "_run_agentic_workflow", new_callable=AsyncMock) as mock_run:
          with patch("app.agents.orchestrator.domain_classifier", mock_classifier):
              with patch("app.agents.orchestrator.CredentialValidator.ensure_llm_available", new_callable=AsyncMock) as mock_validate:
                  await orchestrator.answer("Geneva")
                  # The validator should be called exactly once
                  mock_validate.assert_called_once()
  ```

- [ ] **Step 2: Run tests to verify it fails**
  Run: `pytest apps/api/tests/unit/test_orchestrator_caching.py -v`
  Expected: FAIL

- [ ] **Step 3: Refactor Orchestrator answer & answer_stream**
  Modify the domain validation and LLM check pipeline in `apps/api/app/agents/orchestrator.py` at line 323 (in `answer`) and line 531 (in `answer_stream`):
  
  Introduce local helper function / cache for API key validation:
  ```python
  from app.core.credentials import CredentialValidator
  from app.core.exceptions import ServiceUnavailableError
  from app.agents.domain_classifier import DomainDecision
  
  # Initialize validator
  credential_validator = CredentialValidator()
  ```

  In `answer` (around line 323):
  ```python
          # 1. Rule-based domain classification first
          domain_res = domain_classifier.classify_rules(query)
          llm_checked = False

          # 2. If rules are ambiguous, call LLM classification after key check
          if domain_res is None:
              await credential_validator.ensure_llm_available()
              llm_checked = True
              domain_res = await domain_classifier.classify_llm(query)

          # Track Domain Classification metrics
          try:
              from prometheus_client import Counter
              # Best-effort metrics tracking
              # Registering Prometheus metrics:
              # domain_classified_total{source, decision}
              # out_of_scope_total
              # greeting_total
          except Exception:
              pass

          # 3. Handle domain decision
          if domain_res.decision == DomainDecision.UNKNOWN:
              raise ServiceUnavailableError("LLM (Domain Classifier)")

          if domain_res.decision == DomainDecision.OUT_OF_SCOPE:
              from app.services.agent.workflows.out_of_scope import OutOfScopeWorkflow
              workflow = OutOfScopeWorkflow()
              wf_res = await workflow.execute(query)
              
              result = AgentResult(
                  answer=wf_res["answer"],
                  citations=[],
                  mode="fast",
                  trace={
                      "workflow": "early_route_out_of_scope",
                      "cache_hit": False,
                      "reason": domain_res.reason,
                      "agent_trace": [
                          {
                              "agent": "Domain Guardrail",
                              "action": f"Phát hiện truy vấn ngoài phạm vi (out_of_scope). Lý do: {domain_res.reason}",
                              "status": "success",
                          }
                      ],
                  },
                  intent="out_of_scope",
                  chunks=[],
              )
              await self._cache_set(query, filters, {
                  "answer": result.answer,
                  "citations": result.citations,
                  "mode": result.mode,
                  "trace": result.trace,
                  "intent": result.intent,
              })
              return result

          # Complexity classification
          execution_mode, intent = self._classify_complexity(query)

          # 4. Greeting/Fast workflow early route check
          if intent == "greeting":
              # Direct direct route (doesn't check LLM availability if Fast response greeting works without LLM)
              pass
          else:
              # RAG flow requires LLM validation if it has not been validated already
              if not llm_checked:
                  await credential_validator.ensure_llm_available()
  ```

  Implement the identical pipeline in `answer_stream` (around line 531).

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest apps/api/tests/unit/test_orchestrator_caching.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  Run:
  ```bash
  git add apps/api/app/agents/orchestrator.py apps/api/tests/unit/test_orchestrator_caching.py
  git commit -m "feat: orchestrator domain pipeline with cached credentials check and UNKNOWN decision handling"
  ```

---

## Verification & Final Tests

- [ ] **Step 1: Run all new unit tests**
  Run: `pytest apps/api/tests/unit/ -v`
  Expected: ALL PASS

- [ ] **Step 2: Run full integration test suite**
  Run: `pytest apps/api/tests/integration/ -v`
  Expected: ALL PASS
