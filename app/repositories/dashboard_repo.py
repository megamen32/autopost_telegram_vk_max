from sqlalchemy import func, select

from app.db.models import AdapterInstanceORM, DeliveryJobORM, MessageLinkORM, ProcessedEventORM, RouteORM, SyncRuleORM
from app.repositories.base import SQLAlchemyRepo


class DashboardRepo(SQLAlchemyRepo):
    async def get_overview(self) -> dict:
        jobs_total = await self.session.scalar(select(func.count()).select_from(DeliveryJobORM)) or 0
        jobs_by_status_rows = (
            await self.session.execute(
                select(DeliveryJobORM.status, func.count()).group_by(DeliveryJobORM.status).order_by(DeliveryJobORM.status)
            )
        ).all()
        jobs_by_status = {status: count for status, count in jobs_by_status_rows}

        jobs_by_platform_rows = (
            await self.session.execute(
                select(DeliveryJobORM.target_platform, func.count())
                .group_by(DeliveryJobORM.target_platform)
                .order_by(DeliveryJobORM.target_platform)
            )
        ).all()
        jobs_by_platform = {platform: count for platform, count in jobs_by_platform_rows}

        links_total = await self.session.scalar(select(func.count()).select_from(MessageLinkORM)) or 0
        processed_events_total = await self.session.scalar(select(func.count()).select_from(ProcessedEventORM)) or 0
        routes_total = await self.session.scalar(select(func.count()).select_from(RouteORM)) or 0
        enabled_routes = (
            await self.session.scalar(select(func.count()).select_from(RouteORM).where(RouteORM.enabled.is_(True))) or 0
        )
        rules_total = await self.session.scalar(select(func.count()).select_from(SyncRuleORM)) or 0
        enabled_rules = (
            await self.session.scalar(select(func.count()).select_from(SyncRuleORM).where(SyncRuleORM.enabled.is_(True))) or 0
        )

        adapter_instances_total = await self.session.scalar(select(func.count()).select_from(AdapterInstanceORM)) or 0

        return {
            "jobs_total": jobs_total,
            "jobs_by_status": jobs_by_status,
            "jobs_by_platform": jobs_by_platform,
            "links_total": links_total,
            "processed_events_total": processed_events_total,
            "routes_total": routes_total,
            "enabled_routes": enabled_routes,
            "adapter_instances_total": adapter_instances_total,
            "rules_total": rules_total,
            "enabled_rules": enabled_rules,
        }
