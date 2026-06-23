"""
zh_messages — 中文提示模板
TELEMETRY-ONLY: NO_STATE_MUTATION | FAIL_SILENT

轻量中文消息组装，不设计成复杂 i18n 系统。
每个函数输入关键参数，返回简短中文描述（1~2 行）。
"""


def workflow_started_zh(workflow_name: str) -> str:
    """workflow 开始时中文提示"""
    names = {
        "delivery_pipeline": "项目交付工作流",
        "debug_pipeline": "故障诊断工作流",
        "learning_pipeline": "学习工作流",
    }
    cn_name = names.get(workflow_name, workflow_name)
    return f"已进入 {cn_name}（{workflow_name}），开始执行当前任务。"


def stage_entered_zh(stage_index: int, total_stages: int, stage_name: str) -> str:
    """stage 进入时中文提示"""
    if total_stages > 0:
        return f"正在进入阶段 {stage_index}/{total_stages}：{stage_name}"
    return f"正在进入阶段：{stage_name}"


def stage_completed_zh(stage_index: int, total_stages: int, stage_name: str) -> str:
    """stage 完成时中文提示"""
    if total_stages > 0:
        return f"阶段 {stage_index}/{total_stages}（{stage_name}）已完成"
    return f"阶段（{stage_name}）已完成"


def stage_failed_zh(stage_index: int, stage_name: str, reason: str = "") -> str:
    """stage 失败时中文提示"""
    base = f"阶段 {stage_index}（{stage_name}）执行失败"
    if reason:
        base += f"，原因：{reason}"
    return base


def skill_started_zh(skill_name: str) -> str:
    """skill 启动时中文提示"""
    names = {
        "summarize": "知识整理",
        "planning": "任务规划",
        "debug": "故障诊断",
        "code_assistant": "代码编写",
        "reviewer": "代码审查",
        "changelog": "变更日志",
        "task_ledger": "任务记录",
        "teach-plus": "学习工作流",
        "ask": "需求澄清",
        "debug_log": "排查归档",
        "execution_guard": "执行校验",
        "knowledge-asset": "知识沉淀",
    }
    cn_name = names.get(skill_name, skill_name)
    return f"当前开始执行技能：{cn_name}（{skill_name}）"


def heartbeat_zh(action: str) -> str:
    """heartbeat 中文提示"""
    return f"正在{action}"


def workflow_completed_zh(workflow_name: str) -> str:
    """workflow 完成时中文提示"""
    names = {
        "delivery_pipeline": "项目交付工作流",
        "debug_pipeline": "故障诊断工作流",
        "learning_pipeline": "学习工作流",
    }
    cn_name = names.get(workflow_name, workflow_name)
    return f"{cn_name}（{workflow_name}）已完成。"


def workflow_failed_zh(workflow_name: str, stage_name: str = "", reason: str = "") -> str:
    """workflow 失败时中文提示"""
    names = {
        "delivery_pipeline": "项目交付工作流",
        "debug_pipeline": "故障诊断工作流",
        "learning_pipeline": "学习工作流",
    }
    cn_name = names.get(workflow_name, workflow_name)
    base = f"{cn_name}（{workflow_name}）执行失败"
    if stage_name:
        base += f"，失败于阶段：{stage_name}"
    if reason:
        base += f"，原因：{reason}"
    base += "。请检查失败原因或重试。"
    return base


def resume_hint_zh(workflow_name: str, stage_name: str, skill_name: str) -> str:
    """resume 断点恢复中文提示"""
    return (
        f"你上次执行在 {stage_name} 阶段中断，最近的技能是 {skill_name}。"
        f"如果当前任务与上次一致，建议从这个阶段继续，而不是重新开始整个工作流。"
    )


def router_hint_zh(intent: str, workflow: str) -> str:
    """Router 面板中文摘要"""
    intent_names = {
        "project_delivery": "项目交付类任务",
        "debug_issue": "故障诊断类任务",
        "learn_topic": "学习类任务",
    }
    cn_intent = intent_names.get(intent, intent)
    return f"中文提示：已识别为{cn_intent}，将进入 {workflow} 工作流，优先执行对应技能。"


def guard_hint_zh(status: str) -> str:
    """Guard 面板中文提示"""
    if status == "executing":
        return "中文提示：当前任务处于执行阶段，系统正在推进代码实现与文件修改。"
    elif status == "planning":
        return "中文提示：当前任务处于规划阶段，系统正在分析需求并制定执行计划。"
    elif status == "blocked":
        return "中文提示：当前任务被阻塞，请检查阻塞原因或提供所需信息。"
    elif status == "retrying":
        return "中文提示：当前任务正在重试，系统尝试恢复执行。"
    elif status == "stalled":
        return "中文提示：当前任务长时间未推进，建议检查是否卡在某个阶段或等待输入。"
    else:
        return "中文提示：当前任务正在处理中。"


def completion_pass_zh() -> str:
    """Completion Guard 通过中文提示"""
    return "中文提示：完成检查已通过，可以进入任务收尾或状态更新。"


def completion_fail_zh(missing_count: int) -> str:
    """Completion Guard 未通过中文提示"""
    return f"中文提示：当前还不能标记为完成，有 {missing_count} 项校验未通过，请检查交付物或状态文件。"
