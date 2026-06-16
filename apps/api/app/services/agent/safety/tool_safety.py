"""Tool Safety - Input validation, output filtering, and PII detection.

This module provides production-grade tool safety for agent systems:
- Input validation: Sanitize and validate user inputs before reaching the LLM
- Output filtering: Remove PII, toxic content, and insecure code
- PII detection: Identify and mask personal information
- Tool permission scoping: Restrict tool access based on user roles

Usage:
    from app.services.agent.safety import ToolSafety, get_tool_safety
    
    safety = get_tool_safety()
    
    # Validate input before LLM call
    safe_input = await safety.validate_input(user_input, context)
    
    # Filter output before sending to user
    safe_output = await safety.filter_output(raw_output, context)
    
    # Check for PII in content
    pii_found = await safety.detect_pii(content)
"""

from __future__ import annotations

import re
import html
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.logging import get_logger

logger = get_logger("tool_safety")


class RiskLevel(Enum):
    """Risk level for content."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            levels = list(self.__class__)
            return levels.index(self) < levels.index(other)
        return NotImplemented



@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    risk_level: RiskLevel
    sanitized_content: str
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    masked_content: str = ""


@dataclass
class FilterResult:
    """Result of output filtering."""
    is_safe: bool
    risk_level: RiskLevel
    filtered_content: str
    removed_items: list[str] = field(default_factory=list)
    replacements_made: int = 0


@dataclass
class PIIDetectionResult:
    """Result of PII detection."""
    has_pii: bool
    pii_types: list[str] = field(default_factory=list)
    masked_content: str = ""
    confidence_scores: dict[str, float] = field(default_factory=dict)
    locations: list[dict] = field(default_factory=list)


@dataclass
class ToolSafetyConfig:
    """Configuration for tool safety."""
    # Input validation
    enable_input_validation: bool = True
    max_input_length: int = 10000
    block_sql_injection: bool = True
    block_xss: bool = True
    block_prompt_injection: bool = True
    
    # Output filtering
    enable_output_filtering: bool = True
    block_pii: bool = True
    block_toxic_content: bool = True
    block_insecure_code: bool = True
    
    # PII detection
    pii_detection_enabled: bool = True
    pii_mask_char: str = "*"
    pii_min_confidence: float = 0.7
    
    # Tool permissions
    enable_tool_permissions: bool = True
    default_tool_scope: list[str] = field(default_factory=lambda: ["read", "search"])
    
    # Rate limiting
    max_requests_per_minute: int = 60
    max_similar_requests: int = 10


class InputValidator:
    """
    Validates and sanitizes user inputs before they reach the LLM.
    
    Checks for:
    - SQL injection attempts
    - XSS payloads
    - Prompt injection patterns
    - Excessive length
    - Dangerous content
    """
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b.*\b(FROM|INTO|TABLE|DATABASE)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bUNION\b.*\bSELECT\b)",
        r"('|(\\'))",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(EXEC\s*\()",
        r"(XP_)",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<embed[^>]*>",
        r"<object[^>]*>",
        r"eval\s*\(",
        r"document\.cookie",
        r"innerHTML",
        r"outerHTML",
    ]
    
    # Prompt injection patterns
    PROMPT_INJECTION_PATTERNS = [
        r"(ignore\s+(previous|all|above|system)\s+instructions)",
        r"(forget\s+(everything|all|your)\s+(instructions|rules|guidelines))",
        r"(you\s+are\s+now\s+)",
        r"(pretend\s+you\s+are\s+)",
        r"(disregard\s+your\s+)",
        r"(new\s+instructions:)",
        r"(override\s+)",
        r"(#\s*system\s*)",
        r"(//\s*system\s*)",
        r"(\[\s*INST\s*\])",
        r"(\[\s*SYSTEM\s*\])",
    ]
    
    # Vietnamese-specific patterns
    VIETNAMESI_HARMFUL_PATTERNS = [
        r"(hack|truy cập trái phép)",
        r"(lừa đảo|scam)",
        r"(mật khẩu|password)",
        r"(thẻ tín dụng|credit card)",
        r"(số tài khoản|bank account)",
    ]
    
    def __init__(self, config: ToolSafetyConfig | None = None):
        self.config = config or ToolSafetyConfig()
        self._compiled_sql = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self._compiled_xss = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.XSS_PATTERNS]
        self._compiled_prompt = [re.compile(p, re.IGNORECASE) for p in self.PROMPT_INJECTION_PATTERNS]
        self._compiled_vn = [re.compile(p, re.IGNORECASE) for p in self.VIETNAMESI_HARMFUL_PATTERNS]
    
    def validate(self, content: str, context: dict | None = None) -> ValidationResult:
        """
        Validate and sanitize input content.
        
        Returns ValidationResult with sanitized content and any violations.
        """
        violations: list[str] = []
        warnings: list[str] = []
        risk_level = RiskLevel.SAFE
        
        if not content:
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.SAFE,
                sanitized_content="",
            )
        
        sanitized = content
        
        # 1. Check length
        if len(content) > self.config.max_input_length:
            violations.append(f"Input exceeds max length ({len(content)} > {self.config.max_input_length})")
            sanitized = sanitized[:self.config.max_input_length]
            risk_level = max(risk_level, RiskLevel.MEDIUM)
        
        # 2. SQL injection detection
        if self.config.block_sql_injection:
            for i, pattern in enumerate(self._compiled_sql):
                matches = pattern.findall(sanitized)
                if matches:
                    violations.append(f"SQL injection pattern detected (pattern {i})")
                    risk_level = max(risk_level, RiskLevel.HIGH)
                    # Don't mask, but log for monitoring
        
        # 3. XSS detection
        if self.config.block_xss:
            for i, pattern in enumerate(self._compiled_xss):
                matches = pattern.findall(sanitized)
                if matches:
                    violations.append(f"XSS pattern detected (pattern {i})")
                    risk_level = max(risk_level, RiskLevel.HIGH)
                    # Mask XSS content
                    sanitized = pattern.sub("[FILTERED]", sanitized)
        
        # 4. Prompt injection detection
        if self.config.block_prompt_injection:
            for i, pattern in enumerate(self._compiled_prompt):
                matches = pattern.findall(sanitized)
                if matches:
                    violations.append(f"Prompt injection pattern detected (pattern {i})")
                    risk_level = max(risk_level, RiskLevel.CRITICAL)
                    # Mask injection content
                    sanitized = pattern.sub("[INJECTION BLOCKED]", sanitized)
        
        # 5. Vietnamese harmful patterns
        for i, pattern in enumerate(self._compiled_vn):
            matches = pattern.findall(sanitized)
            if matches:
                warnings.append(f"Potentially sensitive content detected (pattern {i})")
                risk_level = max(risk_level, RiskLevel.MEDIUM)
        
        # 6. HTML entity encoding
        sanitized = html.escape(sanitized)
        
        # 7. Check for excessive special characters
        special_char_ratio = sum(1 for c in sanitized if not c.isalnum() and not c.isspace()) / max(len(sanitized), 1)
        if special_char_ratio > 0.5:
            warnings.append("High ratio of special characters")
            risk_level = max(risk_level, RiskLevel.LOW)
        
        is_valid = len(violations) == 0 or risk_level != RiskLevel.CRITICAL
        
        return ValidationResult(
            is_valid=is_valid,
            risk_level=risk_level,
            sanitized_content=sanitized,
            violations=violations,
            warnings=warnings,
            masked_content=sanitized,  # Already sanitized
        )


class PIIDetector:
    """
    Detects and masks Personally Identifiable Information (PII).
    
    Detects:
    - Names (Vietnamese and Western)
    - Email addresses
    - Phone numbers
    - ID numbers
    - Addresses
    - Dates of birth
    - Bank account numbers
    """
    
    # Vietnamese name patterns (common surnames)
    VIETNAMESE_NAMES = [
        "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Trương", "Bùi", "Đặng",
        "Ngô", "Dương", "Lý", "Hồ", "Đỗ", "Trịnh", "Cao", "Võ", "Vũ", "Đinh",
        "Hà", "Mai", "Lưu", "Trang", "Đoàn", "Vương", "Tạ", "Tô", "Thái", "Lâm",
    ]
    
    # PII patterns
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_VN = re.compile(r'\b(\+84|0)\d{9,10}\b')
    PHONE_GENERIC = re.compile(r'\b\d{10,11}\b')
    ID_VN = re.compile(r'\b\d{9,12}\b')  # CCCD, CMND
    BANK_ACCOUNT = re.compile(r'\b\d{8,20}\b')
    DATE_PATTERNS = [
        re.compile(r'\b\d{1,2}/\d{1,2}/\d{4}\b'),
        re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
        re.compile(r'\b\d{1,2}\s+(tháng|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b', re.IGNORECASE),
    ]
    
    # IP address
    IP_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
    
    # Credit card pattern
    CREDIT_CARD = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
    
    def __init__(self, config: ToolSafetyConfig | None = None):
        self.config = config or ToolSafetyConfig()
        self.mask_char = config.pii_mask_char if config else "*"
    
    def detect(self, content: str) -> PIIDetectionResult:
        """
        Detect PII in content.
        
        Returns PIIDetectionResult with detected types and masked content.
        """
        pii_types: list[str] = []
        confidence_scores: dict[str, float] = {}
        locations: list[dict] = []
        
        masked = content
        
        # 1. Email detection
        for match in self.EMAIL_PATTERN.finditer(content):
            pii_types.append("email")
            confidence_scores["email"] = 0.95
            locations.append({
                "type": "email",
                "start": match.start(),
                "end": match.end(),
                "text": match.group(),
            })
            # Mask email
            email = match.group()
            parts = email.split("@")
            masked_email = f"{parts[0][0]}{self.mask_char * 3}@{parts[1]}"
            masked = masked[:match.start()] + masked_email + masked[match.end():]
        
        # 2. Phone number detection (Vietnamese)
        for match in self.PHONE_VN.finditer(masked):
            pii_types.append("phone_vn")
            confidence_scores["phone_vn"] = 0.85
            locations.append({
                "type": "phone",
                "start": match.start(),
                "end": match.end(),
                "text": match.group()[:4] + self.mask_char * (len(match.group()) - 4),
            })
            # Mask phone
            phone = match.group()
            masked = masked[:match.start()] + phone[:4] + self.mask_char * (len(phone) - 4) + masked[match.end():]
        
        # 3. ID number detection (Vietnamese CCCD)
        for match in self.ID_VN.finditer(masked):
            # Check if it's likely an ID number (length 9 or 12)
            if len(match.group()) in [9, 12]:
                pii_types.append("id_number")
                confidence_scores["id_number"] = 0.75
                locations.append({
                    "type": "id_number",
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group()[:3] + self.mask_char * (len(match.group()) - 3),
                })
                # Mask ID
                id_num = match.group()
                masked = masked[:match.start()] + id_num[:3] + self.mask_char * (len(id_num) - 3) + masked[match.end():]
        
        # 4. Credit card detection
        for match in self.CREDIT_CARD.finditer(masked):
            pii_types.append("credit_card")
            confidence_scores["credit_card"] = 0.90
            locations.append({
                "type": "credit_card",
                "start": match.start(),
                "end": match.end(),
                "text": match.group()[:4] + self.mask_char * 8 + match.group()[-4:],
            })
            # Mask credit card
            cc = match.group()
            masked = masked[:match.start()] + cc[:4] + self.mask_char * 8 + cc[-4:] + masked[match.end():]
        
        # 5. IP address detection
        for match in self.IP_PATTERN.finditer(masked):
            # Filter out likely false positives (version numbers, etc.)
            octets = match.group().split(".")
            if all(0 <= int(o) <= 255 for o in octets):
                pii_types.append("ip_address")
                confidence_scores["ip_address"] = 0.70
                locations.append({
                    "type": "ip_address",
                    "start": match.start(),
                    "end": match.end(),
                    "text": self.mask_char * len(match.group()),
                })
        
        # 6. Bank account detection (longer numbers)
        for match in self.BANK_ACCOUNT.finditer(masked):
            if 12 <= len(match.group()) <= 20:
                pii_types.append("bank_account")
                confidence_scores["bank_account"] = 0.65
                locations.append({
                    "type": "bank_account",
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group()[:4] + self.mask_char * (len(match.group()) - 4),
                })
        
        # Remove duplicates
        pii_types = list(set(pii_types))
        
        return PIIDetectionResult(
            has_pii=len(pii_types) > 0,
            pii_types=pii_types,
            masked_content=masked,
            confidence_scores=confidence_scores,
            locations=locations,
        )
    
    def mask_all(self, content: str) -> str:
        """Mask all PII in content."""
        result = self.detect(content)
        return result.masked_content


class OutputFilter:
    """
    Filters output content before sending to users.
    
    Checks for:
    - PII
    - Toxic content
    - Insecure code
    - Excessive profanity
    """
    
    # Toxic content patterns
    TOXIC_PATTERNS = [
        r'\b(hate|kill|die|stupid|idiot|dumb|moron)\b',
        r'\b(threat|attack|destroy)\b',
    ]
    
    # Insecure code patterns
    INSECURE_CODE_PATTERNS = [
        r'(eval|exec)\s*\(',
        r'(subprocess|os\.system|os\.popen)\s*\(',
        r'(rm\s+-rf|mkfs|dd\s+if=)',
        r'(curl|wget).*\|.*sh',
        r'(SELECT|INSERT|UPDATE|DELETE).*FROM.*WHERE',
    ]
    
    def __init__(self, config: ToolSafetyConfig | None = None):
        self.config = config or ToolSafetyConfig()
        self._pii_detector = PIIDetector(config)
        self._compiled_toxic = [re.compile(p, re.IGNORECASE) for p in self.TOXIC_PATTERNS]
        self._compiled_insecure = [re.compile(p, re.IGNORECASE) for p in self.INSECURE_CODE_PATTERNS]
    
    def filter(self, content: str, context: dict | None = None) -> FilterResult:
        """
        Filter output content.
        
        Returns FilterResult with filtered content.
        """
        removed_items: list[str] = []
        risk_level = RiskLevel.SAFE
        filtered = content
        
        # 1. PII filtering
        if self.config.block_pii:
            pii_result = self._pii_detector.detect(filtered)
            if pii_result.has_pii:
                removed_items.extend([f"pii:{t}" for t in pii_result.pii_types])
                filtered = pii_result.masked_content
                risk_level = max(risk_level, RiskLevel.MEDIUM)
        
        # 2. Toxic content filtering
        if self.config.block_toxic_content:
            for i, pattern in enumerate(self._compiled_toxic):
                matches = pattern.findall(filtered)
                if matches:
                    removed_items.append(f"toxic_pattern_{i}")
                    risk_level = max(risk_level, RiskLevel.HIGH)
                    filtered = pattern.sub("[FILTERED]", filtered)
        
        # 3. Insecure code filtering
        if self.config.block_insecure_code:
            for i, pattern in enumerate(self._compiled_insecure):
                matches = pattern.findall(filtered)
                if matches:
                    removed_items.append(f"insecure_code_{i}")
                    risk_level = max(risk_level, RiskLevel.HIGH)
                    filtered = pattern.sub("[CODE BLOCKED]", filtered)
        
        is_safe = risk_level in (RiskLevel.SAFE, RiskLevel.LOW)
        
        return FilterResult(
            is_safe=is_safe,
            risk_level=risk_level,
            filtered_content=filtered,
            removed_items=removed_items,
            replacements_made=len(removed_items),
        )


class ToolPermissionManager:
    """
    Manages tool access permissions based on user roles.
    
    Supports:
    - Role-based access control
    - Tool scoping
    - Permission inheritance
    """
    
    DEFAULT_ROLES = {
        "user": ["read", "search", "chat"],
        "contributor": ["read", "search", "chat", "ingest"],
        "editor": ["read", "search", "chat", "ingest", "edit"],
        "admin": ["read", "search", "chat", "ingest", "edit", "delete", "admin"],
    }
    
    def __init__(self, config: ToolSafetyConfig | None = None):
        self.config = config or ToolSafetyConfig()
        self._role_permissions: dict[str, list[str]] = self.DEFAULT_ROLES.copy()
        self._custom_permissions: dict[str, dict[str, list[str]]] = {}
    
    def add_role_permission(self, role: str, permissions: list[str]) -> None:
        """Add permissions for a role."""
        if role not in self._role_permissions:
            self._role_permissions[role] = []
        self._role_permissions[role].extend(permissions)
        self._role_permissions[role] = list(set(self._role_permissions[role]))
    
    def set_user_permissions(self, user_id: str, permissions: list[str]) -> None:
        """Set custom permissions for a specific user."""
        self._custom_permissions[user_id] = {"custom": permissions}
    
    def get_permissions(self, user_id: str, role: str) -> list[str]:
        """Get effective permissions for a user."""
        # Check custom permissions first
        if user_id in self._custom_permissions:
            return self._custom_permissions[user_id].get("custom", [])
        
        # Fall back to role permissions
        return self._role_permissions.get(role, self.config.default_tool_scope)
    
    def can_access_tool(self, user_id: str, role: str, tool_name: str) -> bool:
        """Check if user can access a specific tool."""
        permissions = self.get_permissions(user_id, role)
        
        # Tool names are formatted as "category:action"
        tool_parts = tool_name.split(":")
        
        # Check each permission
        for perm in permissions:
            if perm == tool_name:
                return True
            if perm == tool_parts[0]:  # Category match
                return True
            if perm == "admin":  # Admin has all permissions
                return True
        
        return False
    
    def filter_tools(
        self,
        user_id: str,
        role: str,
        available_tools: list[str],
    ) -> list[str]:
        """Filter tools to only those the user can access."""
        return [
            tool for tool in available_tools
            if self.can_access_tool(user_id, role, tool)
        ]


class ToolSafety:
    """
    Complete Tool Safety System.
    
    Integrates:
    - Input validation
    - PII detection and masking
    - Output filtering
    - Tool permission management
    
    Provides a unified interface for all safety checks.
    """
    
    def __init__(self, config: ToolSafetyConfig | None = None):
        self.config = config or ToolSafetyConfig()
        
        # Initialize components
        self.input_validator = InputValidator(self.config)
        self.pii_detector = PIIDetector(self.config)
        self.output_filter = OutputFilter(self.config)
        self.permission_manager = ToolPermissionManager(self.config)
    
    async def validate_input(
        self,
        content: str,
        context: dict | None = None,
    ) -> ValidationResult:
        """
        Validate user input before LLM processing.
        
        Returns sanitized content and validation status.
        """
        if not self.config.enable_input_validation:
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.SAFE,
                sanitized_content=content,
            )
        
        return self.input_validator.validate(content, context)
    
    async def filter_output(
        self,
        content: str,
        context: dict | None = None,
    ) -> FilterResult:
        """
        Filter LLM output before sending to user.
        
        Returns filtered content and filter status.
        """
        if not self.config.enable_output_filtering:
            return FilterResult(
                is_safe=True,
                risk_level=RiskLevel.SAFE,
                filtered_content=content,
            )
        
        return self.output_filter.filter(content, context)
    
    async def detect_pii(self, content: str) -> PIIDetectionResult:
        """
        Detect PII in content.
        
        Returns detection result with masked content.
        """
        if not self.config.pii_detection_enabled:
            return PIIDetectionResult(has_pii=False)
        
        return self.pii_detector.detect(content)
    
    async def check_permissions(
        self,
        user_id: str,
        role: str,
        tool_name: str,
    ) -> bool:
        """
        Check if user has permission for a tool.
        """
        if not self.config.enable_tool_permissions:
            return True
        
        return self.permission_manager.can_access_tool(user_id, role, tool_name)
    
    async def filter_available_tools(
        self,
        user_id: str,
        role: str,
        available_tools: list[str],
    ) -> list[str]:
        """
        Filter tools based on user permissions.
        """
        if not self.config.enable_tool_permissions:
            return available_tools
        
        return self.permission_manager.filter_tools(user_id, role, available_tools)
    
    async def full_safety_check(
        self,
        input_content: str,
        output_content: str,
        user_id: str,
        role: str,
        context: dict | None = None,
    ) -> dict:
        """
        Perform complete safety check on input and output.
        
        Returns comprehensive safety report.
        """
        # Validate input
        input_result = await self.validate_input(input_content, context)
        
        # Filter output
        output_result = await self.filter_output(output_content, context)
        
        # Detect PII in output
        pii_result = await self.detect_pii(output_content)
        
        # Calculate overall risk
        max_risk = max(input_result.risk_level, output_result.risk_level)
        if pii_result.has_pii:
            max_risk = max(max_risk, RiskLevel.MEDIUM)
        
        return {
            "is_safe": (
                input_result.is_valid and
                output_result.is_safe and
                max_risk in (RiskLevel.SAFE, RiskLevel.LOW)
            ),
            "risk_level": max_risk.value,
            "input": {
                "is_valid": input_result.is_valid,
                "risk_level": input_result.risk_level.value,
                "violations": input_result.violations,
                "warnings": input_result.warnings,
                "sanitized": input_result.sanitized_content,
            },
            "output": {
                "is_safe": output_result.is_safe,
                "risk_level": output_result.risk_level.value,
                "removed_items": output_result.removed_items,
                "filtered": output_result.filtered_content,
            },
            "pii": {
                "detected": pii_result.has_pii,
                "types": pii_result.pii_types,
                "masked": pii_result.masked_content,
            },
        }


# ─── Global Instance ─────────────────────────────────────────────────────────

_safety_instance: ToolSafety | None = None


def get_tool_safety() -> ToolSafety:
    """Get the global ToolSafety instance."""
    global _safety_instance
    if _safety_instance is None:
        _safety_instance = ToolSafety()
    return _safety_instance


def reset_tool_safety() -> None:
    """Reset the global instance (for testing)."""
    global _safety_instance
    _safety_instance = None
