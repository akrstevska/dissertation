from typing import TypedDict, Literal, Optional, Any

Severity = Literal["Not classified", "Information", "Warning", "Average", "High", "Disaster"]
Scope = Literal["none", "single_customer", "pon_port", "olt", "router", "multi_customer"]


class Detection(TypedDict):
    status: Literal["anomaly_detected", "no_anomaly"]
    signals: list[dict]
    preliminary_severity: Severity
    affected_scope: Scope
    affected_lineids: list[str]
    olt_id: Optional[str]
    interface: Optional[str]
    summary: str


class Diagnosis(TypedDict):
    fault_type: str
    root_cause: str
    confidence: float
    affected_scope: Scope
    affected_lineids: list[str]
    evidence: list[str]
    cached_vs_live_discrepancy: bool
    discrepancy_detail: Optional[str]


class Remediation(TypedDict):
    action: str
    automated: bool
    reason: str
    instructions: str
    alternatives_considered: list[dict]


class Escalation(TypedDict):
    priority: Severity
    category: str
    requires_human_review: bool
    review_reason: Optional[str]
    summary: str
    affected_customer_count: int
    service_impact: bool


class PipelineState(TypedDict, total=False):
    trigger: str
    trigger_input: dict
    detection: Optional[Detection]
    diagnosis: Optional[Diagnosis]
    remediation: Optional[Remediation]
    escalation: Optional[Escalation]
    trace: list[dict]
