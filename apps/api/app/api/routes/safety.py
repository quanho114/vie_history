"""Safety & Agent Operations API Routes.

Provides endpoints for:
- Agent session management (kill switch, status)
- Safety configuration
- Anomaly detection monitoring
- Human-in-the-loop approvals
- Circuit breaker status

Usage:
    # Abort a session
    POST /api/v1/safety/sessions/{session_id}/abort
    
    # Get session status
    GET /api/v1/safety/sessions/{session_id}
    
    # Get pending approvals
    GET /api/v1/safety/approvals
    
    # Approve an action
    POST /api/v1/safety/approvals/{token}/decide
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.audit import get_audit_logger, AuditAction, AuditEvent, AuditLevel

logger = get_logger("safety_routes")

router = APIRouter(prefix="/safety", tags=["Safety & Agent Operations"])


# ─── Request/Response Models ──────────────────────────────────────────────────


class AbortRequest(BaseModel):
    """Request to abort a session."""
    reason: str = Field(default="user_requested", description="Reason for abort")
    force: bool = Field(default=False, description="Force abort even if in critical state")


class ApprovalRequest(BaseModel):
    """Request for human approval."""
    action: str = Field(..., description="Action requiring approval")
    details: dict[str, Any] = Field(default_factory=dict, description="Action details")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score")


class ApprovalDecision(BaseModel):
    """Decision on an approval request."""
    approved: bool = Field(..., description="Whether to approve the action")
    comments: str = Field(default="", description="Comments for the decision")


class SessionStatusResponse(BaseModel):
    """Response containing session safety status."""
    session_id: str
    status: str
    token_budget: dict[str, Any] | None = None
    tool_call_count: int = 0
    execution_count: int = 0
    anomalies: list[dict] = Field(default_factory=list)
    pending_approval: bool = False


class HealthResponse(BaseModel):
    """System health response."""
    overall: str
    circuit_breakers: dict[str, Any]
    anomalies: dict[str, Any]
    active_sessions: int = 0
    config: dict[str, bool]


class AnomalySummaryResponse(BaseModel):
    """Anomaly detection summary."""
    total_anomalies: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    recent_anomalies: list[dict]


# ─── Safety Dependency ────────────────────────────────────────────────────────


def get_safety_integration():
    """Dependency to get safety integration."""
    from app.services.agent.safety_integration import get_safety_integration
    return get_safety_integration()


# ─── Session Management ────────────────────────────────────────────────────────


@router.post(
    "/sessions/{session_id}/init",
    summary="Initialize a safety session",
    description="Initialize safety tracking for a new agent session",
)
async def init_session(
    session_id: str,
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Initialize a new safety session."""
    try:
        result = await integration.init_session(session_id)
        logger.info("session_initialized", session_id=session_id)
        return result
    except Exception as e:
        logger.error("session_init_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize session: {str(e)}",
        )


@router.get(
    "/sessions/{session_id}",
    summary="Get session status",
    description="Get detailed safety status for an agent session",
)
async def get_session_status(
    session_id: str,
    integration=Depends(get_safety_integration),
) -> SessionStatusResponse:
    """Get the safety status of a session."""
    try:
        status = await integration.get_session_status(session_id)
        
        if "error" in status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )
        
        return SessionStatusResponse(
            session_id=session_id,
            status=status.get("safety_status", {}).get("status", "unknown"),
            token_budget=status.get("safety_status", {}).get("token_budget"),
            tool_call_count=status.get("safety_status", {}).get("tool_call_count", 0),
            execution_count=status.get("safety_status", {}).get("execution_count", 0),
            anomalies=status.get("health", {}).get("anomalies", []),
            pending_approval=status.get("safety_status", {}).get("pending_approval", False),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("session_status_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session status: {str(e)}",
        )


@router.post(
    "/sessions/{session_id}/abort",
    summary="Abort a session",
    description="Immediately abort an agent session (kill switch)",
)
async def abort_session(
    session_id: str,
    request: AbortRequest | None = None,
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Abort an agent session (kill switch)."""
    try:
        reason = request.reason if request else "user_requested"
        success = await integration.abort_session(session_id, reason)
        
        if success:
            logger.warning("session_aborted_via_api", session_id=session_id, reason=reason)
            return {
                "success": True,
                "session_id": session_id,
                "message": f"Session aborted: {reason}",
            }
        else:
            return {
                "success": False,
                "session_id": session_id,
                "message": "Session not found or already aborted",
            }
    except Exception as e:
        logger.error("session_abort_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to abort session: {str(e)}",
        )


@router.get(
    "/sessions",
    summary="List active sessions",
    description="Get all active agent sessions",
)
async def list_active_sessions(
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Get all active sessions."""
    try:
        sessions = await integration.get_active_sessions()
        return {
            "count": len(sessions),
            "sessions": sessions,
        }
    except Exception as e:
        logger.error("list_sessions_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}",
        )


@router.post(
    "/abort-all",
    summary="Abort all sessions",
    description="Emergency stop - abort all active agent sessions",
)
async def abort_all_sessions(
    reason: str = "emergency_stop",
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Abort all active sessions (emergency stop)."""
    try:
        from app.services.agent.safety import get_agent_safety, AbortReason
        
        safety = get_agent_safety()
        count = await safety.abort_all_sessions(AbortReason.SYSTEM_SHUTDOWN, reason)
        
        logger.critical("all_sessions_aborted_via_api", count=count, reason=reason)
        
        return {
            "success": True,
            "aborted_count": count,
            "reason": reason,
        }
    except Exception as e:
        logger.error("abort_all_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to abort all sessions: {str(e)}",
        )


# ─── Human-in-the-Loop Approvals ─────────────────────────────────────────────


@router.post(
    "/approvals/request",
    summary="Request human approval",
    description="Request human approval for a critical action",
)
async def request_approval(
    request: ApprovalRequest,
    session_id: str = Query(..., description="Session ID"),
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Request human approval for an action."""
    try:
        from app.services.agent.safety import get_agent_safety
        
        safety = get_agent_safety()
        token = await safety.request_approval(
            session_id=session_id,
            action=request.action,
            details=request.details,
            confidence=request.confidence,
        )
        
        if token == "auto_approved":
            return {
                "status": "auto_approved",
                "token": token,
                "message": "Action was auto-approved due to high confidence",
            }
        
        return {
            "status": "pending",
            "token": token,
            "session_id": session_id,
            "action": request.action,
            "details": request.details,
        }
    except Exception as e:
        logger.error("approval_request_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to request approval: {str(e)}",
        )


@router.get(
    "/approvals",
    summary="List pending approvals",
    description="Get all pending approval requests",
)
async def list_pending_approvals(
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Get all pending approval requests."""
    try:
        from app.services.agent.safety import get_agent_safety
        
        safety = get_agent_safety()
        pending = await safety.get_pending_approvals()
        
        return {
            "count": len(pending),
            "approvals": pending,
        }
    except Exception as e:
        logger.error("list_approvals_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list approvals: {str(e)}",
        )


@router.post(
    "/approvals/{token}/decide",
    summary="Decide on an approval",
    description="Approve or deny an approval request",
)
async def decide_approval(
    token: str,
    decision: ApprovalDecision,
    approver_id: str = Query(default="api_user", description="ID of the approver"),
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Decide on an approval request."""
    try:
        from app.services.agent.safety import get_agent_safety
        
        safety = get_agent_safety()
        success, message = await safety.approve_action(
            approval_token=token,
            approver_id=approver_id,
            approved=decision.approved,
            comments=decision.comments,
        )
        
        return {
            "success": success,
            "message": message,
            "token": token,
            "approved": decision.approved,
            "approver_id": approver_id,
        }
    except Exception as e:
        logger.error("approval_decision_failed", token=token, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decide on approval: {str(e)}",
        )


# ─── Anomaly Detection ────────────────────────────────────────────────────────


@router.get(
    "/anomalies",
    summary="Get anomaly summary",
    description="Get summary of detected anomalies",
)
async def get_anomaly_summary(
    session_id: str | None = None,
    integration=Depends(get_safety_integration),
) -> AnomalySummaryResponse:
    """Get anomaly detection summary."""
    try:
        summary = await integration.get_anomaly_summary(session_id)
        
        return AnomalySummaryResponse(
            total_anomalies=summary.get("total_anomalies", 0),
            by_type=summary.get("by_type", {}),
            by_severity=summary.get("by_severity", {}),
            recent_anomalies=summary.get("recent_anomalies", []),
        )
    except Exception as e:
        logger.error("anomaly_summary_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get anomaly summary: {str(e)}",
        )


@router.post(
    "/sessions/{session_id}/check-anomalies",
    summary="Check session for anomalies",
    description="Manually trigger anomaly check for a session",
)
async def check_session_anomalies(
    session_id: str,
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Manually check for anomalies in a session."""
    try:
        anomalies = await integration.check_anomalies(session_id)
        
        return {
            "session_id": session_id,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
        }
    except Exception as e:
        logger.error("anomaly_check_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check anomalies: {str(e)}",
        )


# ─── Health & Status ──────────────────────────────────────────────────────────


@router.get(
    "/health",
    summary="Get safety health status",
    description="Get overall safety system health",
)
async def get_health(
    integration=Depends(get_safety_integration),
) -> HealthResponse:
    """Get overall safety system health."""
    try:
        health = await integration.get_health_status()
        active_sessions = await integration.get_active_sessions()
        
        return HealthResponse(
            overall=health.get("overall", "unknown"),
            circuit_breakers=health.get("circuit_breakers", {}),
            anomalies=health.get("anomalies", {}),
            active_sessions=len(active_sessions),
            config=health.get("config", {}),
        )
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health status: {str(e)}",
        )


@router.get(
    "/circuit-breakers",
    summary="Get circuit breaker status",
    description="Get status of all circuit breakers",
)
async def get_circuit_breaker_status(
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Get status of all circuit breakers."""
    try:
        health = await integration.get_health_status()
        
        return {
            "circuit_breakers": health.get("circuit_breakers", {}),
        }
    except Exception as e:
        logger.error("cb_status_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get circuit breaker status: {str(e)}",
        )


@router.post(
    "/circuit-breakers/{service}/reset",
    summary="Reset a circuit breaker",
    description="Manually reset a circuit breaker to closed state",
)
async def reset_circuit_breaker(
    service: str,
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Reset a circuit breaker."""
    try:
        from app.services.agent.safety import get_resilience
        
        resilience = get_resilience()
        cb = resilience.get_circuit_breaker(service)
        
        if cb:
            cb.reset()
            logger.info("circuit_breaker_reset", service=service)
            return {
                "success": True,
                "service": service,
                "state": "closed",
            }
        else:
            return {
                "success": False,
                "service": service,
                "message": f"No circuit breaker found for service: {service}",
            }
    except Exception as e:
        logger.error("cb_reset_failed", service=service, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset circuit breaker: {str(e)}",
        )


# ─── A2A Protocol ─────────────────────────────────────────────────────────────


@router.get(
    "/agents",
    summary="List registered agents",
    description="Get list of all registered agents in A2A protocol",
)
async def list_agents(
    capability: str | None = None,
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """List all registered agents."""
    try:
        agents = await integration.discover_agents(capability=capability)
        
        return {
            "count": len(agents),
            "agents": [a.to_dict() if hasattr(a, "to_dict") else a for a in agents],
        }
    except Exception as e:
        logger.error("list_agents_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}",
        )


# ─── Dead Letter Queue ────────────────────────────────────────────────────────


@router.get(
    "/dead-letter-queue",
    summary="Get dead letter queue entries",
    description="Get failed operations from the dead letter queue",
)
async def get_dead_letter_queue(
    limit: int = Query(default=50, ge=1, le=200),
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Get dead letter queue entries."""
    try:
        from app.services.agent.safety import get_resilience
        
        resilience = get_resilience()
        dlq = resilience.dead_letter_queue
        
        entries = await dlq.get_entries(limit=limit)
        
        return {
            "count": len(entries),
            "entries": entries,
        }
    except Exception as e:
        logger.error("dlq_fetch_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DLQ entries: {str(e)}",
        )


@router.post(
    "/dead-letter-queue/{entry_id}/retry",
    summary="Retry a failed operation",
    description="Retry a failed operation from the dead letter queue",
)
async def retry_dead_letter_entry(
    entry_id: str,
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Retry a failed operation from the DLQ."""
    try:
        from app.services.agent.safety import get_resilience
        
        resilience = get_resilience()
        dlq = resilience.dead_letter_queue
        
        success, message = await dlq.retry(entry_id)
        
        return {
            "success": success,
            "message": message,
            "entry_id": entry_id,
        }
    except Exception as e:
        logger.error("dlq_retry_failed", entry_id=entry_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry DLQ entry: {str(e)}",
        )


# ─── Input/Output Validation ──────────────────────────────────────────────────


@router.post(
    "/validate-input",
    summary="Validate input",
    description="Check if input passes safety validation",
)
async def validate_input(
    content: str = Body(..., description="Content to validate"),
    context: dict[str, Any] | None = None,
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Validate input content."""
    try:
        is_valid, reason, result = await integration.validate_input(content, context)
        
        if not is_valid or reason:
            get_audit_logger().log(AuditEvent(
                action=AuditAction.SAFETY_PII_DETECTED,
                resource_type="input_validation",
                details={"reason": reason, "content_length": len(content)},
                outcome="failure" if not is_valid else "partial",
                risk_level=AuditLevel.WARNING,
            ))
        
        return {
            "is_valid": is_valid,
            "reason": reason,
            "validation_result": result.to_dict() if hasattr(result, "to_dict") else result,
        }
    except Exception as e:
        logger.error("input_validation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate input: {str(e)}",
        )


@router.post(
    "/filter-output",
    summary="Filter output",
    description="Filter output content through safety filters",
)
async def filter_output(
    content: str = Body(..., description="Content to filter"),
    context: dict[str, Any] | None = None,
    integration=Depends(get_safety_integration),
) -> dict[str, Any]:
    """Filter output content."""
    try:
        filtered, is_safe, removed = await integration.filter_output(content, context)
        
        if removed:
            get_audit_logger().log(AuditEvent(
                action=AuditAction.SAFETY_OUTPUT_FILTERED,
                resource_type="output_filter",
                details={"removed_items": removed, "original_length": len(content)},
                outcome="partial" if removed else "success",
                risk_level=AuditLevel.WARNING,
            ))
        
        return {
            "original_length": len(content),
            "filtered_length": len(filtered),
            "is_safe": is_safe,
            "removed_items": removed,
            "filtered_content": filtered,
        }
    except Exception as e:
        logger.error("output_filter_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to filter output: {str(e)}",
        )
