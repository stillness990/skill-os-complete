"""
Orchestration Types — 编排层统一类型定义
Phase 2: 固定系统"怎么描述工作流"的枚举和常量

用途：
- 所有模块引用统一的 intent / workflow / stage_status / execution_status 枚举
- 消除词汇不一致问题（v1 vs v4）
"""

from enum import Enum


# ── Intent ──────────────────────────────────────────────

class Intent(str, Enum):
    """用户意图分类（与 intent_schema.md 保持一致）"""
    PROJECT_DELIVERY = "project_delivery"
    DEBUG_ISSUE = "debug_issue"
    LEARN_TOPIC = "learn_topic"
    UNKNOWN = "unknown"  # fallback: 无法明确分类时使用


# ── Workflow ────────────────────────────────────────────

class Workflow(str, Enum):
    """工作流名称（与 workflow_templates.json 保持一致）"""
    DELIVERY = "delivery_pipeline"
    DEBUG = "debug_pipeline"
    LEARNING = "learning_pipeline"


WORKFLOW_STAGES = {
    Workflow.DELIVERY: [
        {"phase": "understand", "skill": "summarize", "mode": "briefing", "required": True},
        {"phase": "plan", "skill": "planning", "mode": "project", "required": True},
        {"phase": "track", "skill": "task_ledger", "mode": "auto", "required": True},
        {"phase": "execute", "skill": "code_assistant", "mode": "on_demand", "required": False},
        {"phase": "review", "skill": "reviewer", "mode": "on_demand", "required": False},
        {"phase": "release", "skill": "changelog", "mode": "on_demand", "required": False},
    ],
    Workflow.DEBUG: [
        {"phase": "summarize_optional", "skill": "summarize", "mode": "briefing", "required": False},
        {"phase": "diagnose", "skill": "debug", "mode": "full", "required": True},
        {"phase": "fix", "skill": "code_assistant", "mode": "on_demand", "required": False},
        {"phase": "archive", "skill": "debug_log", "mode": "on_demand", "required": False},
    ],
    Workflow.LEARNING: [
        {"phase": "clarify", "skill": "ask", "mode": "on_demand", "required": False},
        {"phase": "summarize", "skill": "summarize", "mode": "briefing", "required": True},
        {"phase": "plan", "skill": "planning", "mode": "learning", "required": True},
        {"phase": "explain", "skill": "teach-plus", "mode": "explain", "required": False},
        {"phase": "practice", "skill": "teach-plus", "mode": "practice", "required": False},
        {"phase": "track", "skill": "task_ledger", "mode": "auto", "required": False},
        {"phase": "review", "skill": "teach-plus", "mode": "review", "required": False},
    ],
}

# Workflow 最少 required stages
WORKFLOW_MINIMUM_REQUIRED = {
    Workflow.DELIVERY: ["understand", "plan"],
    Workflow.DEBUG: ["diagnose"],
    Workflow.LEARNING: ["summarize", "plan"],
}


# ── Task Status (v4 unified vocabulary) ─────────────────

class TaskStatus(str, Enum):
    """任务状态 — v4 统一词汇（全系统唯一来源）"""
    QUEUED = "queued"
    PLANNING = "planning"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    RETRYING = "retrying"
    STALLED = "stalled"
    DONE = "done"
    CANCELLED = "cancelled"


# v1 → v4 词汇映射（迁移用）
V1_TO_V4_STATUS = {
    "in_progress": TaskStatus.EXECUTING,
    "retry": TaskStatus.RETRYING,
}

# 终态集合
TERMINAL_STATUSES = {TaskStatus.DONE, TaskStatus.CANCELLED}

# 活动态集合
ACTIVE_STATUSES = {
    TaskStatus.QUEUED,
    TaskStatus.PLANNING,
    TaskStatus.EXECUTING,
    TaskStatus.BLOCKED,
    TaskStatus.RETRYING,
    TaskStatus.STALLED,
}

# 合法状态转移表（来源 → 可去往）
LEGAL_TRANSITIONS = {
    TaskStatus.QUEUED: {TaskStatus.PLANNING, TaskStatus.CANCELLED},
    TaskStatus.PLANNING: {TaskStatus.EXECUTING, TaskStatus.BLOCKED, TaskStatus.DONE, TaskStatus.CANCELLED},
    TaskStatus.EXECUTING: {TaskStatus.BLOCKED, TaskStatus.RETRYING, TaskStatus.DONE, TaskStatus.CANCELLED},
    TaskStatus.BLOCKED: {TaskStatus.PLANNING, TaskStatus.EXECUTING, TaskStatus.CANCELLED},
    TaskStatus.RETRYING: {TaskStatus.EXECUTING, TaskStatus.BLOCKED, TaskStatus.STALLED, TaskStatus.CANCELLED},
    TaskStatus.STALLED: {TaskStatus.PLANNING, TaskStatus.EXECUTING, TaskStatus.CANCELLED},
    TaskStatus.DONE: set(),       # 终态不可逆
    TaskStatus.CANCELLED: set(),  # 终态不可逆
}

# 非法转移列表
ILLEGAL_TRANSITIONS = [
    (TaskStatus.QUEUED, TaskStatus.DONE),
    (TaskStatus.PLANNING, TaskStatus.DONE),   # plan_only 除外
    (TaskStatus.BLOCKED, TaskStatus.DONE),
    (TaskStatus.RETRYING, TaskStatus.DONE),
    (TaskStatus.STALLED, TaskStatus.DONE),
]


# ── Stage Status ────────────────────────────────────────

class StageStatus(str, Enum):
    """RoutePlan 中单个 stage 的执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ── Execution Status ────────────────────────────────────

class ExecutionStatus(str, Enum):
    """workflow 级执行状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"       # 降级运行（如 semantic 不可用）
    SAFE_MODE = "safe_mode"     # 安全模式


# ── Safe Mode Status ────────────────────────────────────

class SafeModeStatus(str, Enum):
    """SAFE MODE 状态"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    TRIGGERED = "triggered"     # 刚触发，待确认


# ── Task Type ───────────────────────────────────────────

class TaskType(str, Enum):
    """任务类型"""
    DELIVERY = "delivery"
    DEBUG = "debug"
    LEARNING = "learning"
    PLAN_ONLY = "plan_only"


# ── Route Source ────────────────────────────────────────

class RouteSource(str, Enum):
    """路由候选来源"""
    RULE = "rule"
    SEMANTIC = "semantic"
    FALLBACK = "fallback"


# ── Failure Type ────────────────────────────────────────

class FailureType(str, Enum):
    """失败类型（用于 retry 上限统计）"""
    EMBEDDING_UNAVAILABLE = "embedding_unavailable"
    STAGE_TIMEOUT = "stage_timeout"
    ARTIFACT_MISSING = "artifact_missing"
    ILLEGAL_TRANSITION = "illegal_transition"
    GUARD_REJECTED = "guard_rejected"
    ROLLBACK_SECURITY = "rollback_security"
    UNKNOWN = "unknown"


# ── Helper functions ────────────────────────────────────

def is_legal_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """检查状态转移是否合法"""
    return to_status in LEGAL_TRANSITIONS.get(from_status, set())


def normalize_v1_status(status: str) -> TaskStatus:
    """将 v1 状态词汇转换为 v4 TaskStatus"""
    if status in V1_TO_V4_STATUS:
        return V1_TO_V4_STATUS[status]
    try:
        return TaskStatus(status)
    except ValueError:
        return TaskStatus.QUEUED


def workflow_for_intent(intent: Intent) -> Workflow:
    """意图 → workflow 映射"""
    mapping = {
        Intent.PROJECT_DELIVERY: Workflow.DELIVERY,
        Intent.DEBUG_ISSUE: Workflow.DEBUG,
        Intent.LEARN_TOPIC: Workflow.LEARNING,
    }
    return mapping.get(intent, Workflow.DELIVERY)


def required_stages_for_workflow(workflow: Workflow) -> list:
    """返回 workflow 的必选 stage phase 名称列表"""
    stages = WORKFLOW_STAGES.get(workflow, [])
    return [s["phase"] for s in stages if s.get("required", False)]
