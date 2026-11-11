from datetime import UTC, datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.app.ai.models import AiUsageLog, AiUsageStatus
from backend.app.ai.schemas import AiUsageScenarioRead, AiUsageSummaryRead


def get_usage_summary(session: Session) -> AiUsageSummaryRead:
    rows = session.execute(
        select(
            AiUsageLog.scenario,
            func.count(AiUsageLog.id),
            func.sum(case((AiUsageLog.status == AiUsageStatus.SUCCEEDED, 1), else_=0)),
            func.sum(case((AiUsageLog.status == AiUsageStatus.FAILED, 1), else_=0)),
            func.sum(AiUsageLog.input_tokens),
            func.sum(AiUsageLog.output_tokens),
        )
        .group_by(AiUsageLog.scenario)
        .order_by(AiUsageLog.scenario.asc())
    ).all()
    items = [
        AiUsageScenarioRead(
            scenario=scenario,
            request_count=request_count,
            success_count=success_count,
            error_count=error_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )
        for (
            scenario,
            request_count,
            success_count,
            error_count,
            input_tokens,
            output_tokens,
        ) in rows
    ]
    input_tokens = sum(item.input_tokens for item in items)
    output_tokens = sum(item.output_tokens for item in items)
    return AiUsageSummaryRead(
        request_count=sum(item.request_count for item in items),
        success_count=sum(item.success_count for item in items),
        error_count=sum(item.error_count for item in items),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        items=items,
        generated_at=datetime.now(UTC),
    )
