"""Repository for Replanning, Candidate Options, Recommendations, and Approvals."""

import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from backend.app.domains.replanning.models import (
    ReplanModel,
    ReplanOptionModel,
    RecommendationModel,
    ApprovalModel,
)


class ReplanRepository:
    """Handles database persistence and queries for the replanning and approval domain."""

    def __init__(self, session: Session):
        self.session = session

    # ============================================================
    # 1. REPLANS
    # ============================================================

    def create_replan(self, replan: ReplanModel) -> ReplanModel:
        self.session.add(replan)
        self.session.flush()
        return replan

    def get_replan_by_id(self, replan_id: uuid.UUID) -> Optional[ReplanModel]:
        return self.session.get(ReplanModel, replan_id)

    def get_replan_by_code(self, code: str) -> Optional[ReplanModel]:
        stmt = select(ReplanModel).where(ReplanModel.replan_code == code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_replans(
        self,
        expedition_id: Optional[uuid.UUID] = None,
        mission_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ReplanModel], int]:
        stmt = select(ReplanModel)
        count_stmt = select(func.count(ReplanModel.id))

        if expedition_id:
            stmt = stmt.where(ReplanModel.expedition_id == expedition_id)
            count_stmt = count_stmt.where(ReplanModel.expedition_id == expedition_id)
        if mission_id:
            stmt = stmt.where(ReplanModel.mission_id == mission_id)
            count_stmt = count_stmt.where(ReplanModel.mission_id == mission_id)
        if status:
            stmt = stmt.where(ReplanModel.status == status)
            count_stmt = count_stmt.where(ReplanModel.status == status)

        total = self.session.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(desc(ReplanModel.created_at)).offset((page - 1) * page_size).limit(page_size)
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def update_replan(self, replan: ReplanModel) -> ReplanModel:
        self.session.add(replan)
        self.session.flush()
        return replan

    # ============================================================
    # 2. CANDIDATE OPTIONS
    # ============================================================

    def create_option(self, option: ReplanOptionModel) -> ReplanOptionModel:
        self.session.add(option)
        self.session.flush()
        return option

    def get_option_by_id(self, option_id: uuid.UUID) -> Optional[ReplanOptionModel]:
        return self.session.get(ReplanOptionModel, option_id)

    def list_options_by_replan(self, replan_id: uuid.UUID) -> List[ReplanOptionModel]:
        stmt = (
            select(ReplanOptionModel)
            .where(ReplanOptionModel.replan_id == replan_id)
            .order_by(ReplanOptionModel.option_code)
        )
        return list(self.session.execute(stmt).scalars().all())

    # ============================================================
    # 3. RECOMMENDATIONS
    # ============================================================

    def create_recommendation(self, rec: RecommendationModel) -> RecommendationModel:
        self.session.add(rec)
        self.session.flush()
        return rec

    def get_recommendation_by_id(self, rec_id: uuid.UUID) -> Optional[RecommendationModel]:
        return self.session.get(RecommendationModel, rec_id)

    def list_recommendations_by_replan(self, replan_id: uuid.UUID) -> List[RecommendationModel]:
        stmt = (
            select(RecommendationModel)
            .where(RecommendationModel.replan_id == replan_id)
            .order_by(desc(RecommendationModel.created_at))
        )
        return list(self.session.execute(stmt).scalars().all())

    def update_recommendation(self, rec: RecommendationModel) -> RecommendationModel:
        self.session.add(rec)
        self.session.flush()
        return rec

    # ============================================================
    # 4. APPROVALS
    # ============================================================

    def create_approval(self, approval: ApprovalModel) -> ApprovalModel:
        self.session.add(approval)
        self.session.flush()
        return approval

    def get_approval_by_id(self, approval_id: uuid.UUID) -> Optional[ApprovalModel]:
        return self.session.get(ApprovalModel, approval_id)

    def get_latest_approval_for_recommendation(self, rec_id: uuid.UUID) -> Optional[ApprovalModel]:
        stmt = (
            select(ApprovalModel)
            .where(ApprovalModel.recommendation_id == rec_id)
            .order_by(desc(ApprovalModel.created_at))
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def update_approval(self, approval: ApprovalModel) -> ApprovalModel:
        self.session.add(approval)
        self.session.flush()
        return approval
