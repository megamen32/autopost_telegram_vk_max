from sqlalchemy import delete, select

from app.db.models import SyncRuleORM
from app.domain.enums import Platform
from app.domain.policies import SyncRule
from app.repositories.base import SQLAlchemyRepo
from app.repositories.sql.converters import orm_to_rule, rule_to_orm, update_rule_orm


class RulesRepo(SQLAlchemyRepo):
    async def upsert(self, rule: SyncRule) -> SyncRule:
        row = (
            await self.session.execute(
                select(SyncRuleORM).where(
                    SyncRuleORM.source_platform == rule.source_platform.value,
                    SyncRuleORM.target_platform == rule.target_platform.value,
                )
            )
        ).scalar_one_or_none()

        if row is None:
            row = rule_to_orm(rule)
            self.session.add(row)
        else:
            update_rule_orm(row, rule)

        await self.session.commit()
        await self.session.refresh(row)
        return orm_to_rule(row)

    async def get_rule(self, source_platform: Platform, target_platform: Platform) -> SyncRule | None:
        row = (
            await self.session.execute(
                select(SyncRuleORM).where(
                    SyncRuleORM.source_platform == source_platform.value,
                    SyncRuleORM.target_platform == target_platform.value,
                )
            )
        ).scalar_one_or_none()
        return orm_to_rule(row) if row else None

    async def list_all(self) -> list[SyncRule]:
        rows = (
            await self.session.execute(
                select(SyncRuleORM).order_by(SyncRuleORM.source_platform, SyncRuleORM.target_platform)
            )
        ).scalars().all()
        return [orm_to_rule(row) for row in rows]

    async def delete(self, source_platform: Platform, target_platform: Platform) -> bool:
        result = await self.session.execute(
            delete(SyncRuleORM).where(
                SyncRuleORM.source_platform == source_platform.value,
                SyncRuleORM.target_platform == target_platform.value,
            )
        )
        await self.session.commit()
        return (result.rowcount or 0) > 0
