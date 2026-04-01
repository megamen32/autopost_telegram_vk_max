from copy import deepcopy

from app.domain.enums import Platform
from app.domain.models import UnifiedPost
from app.domain.policies import SyncRule


class TransformService:
    def transform_for_target(self, post: UnifiedPost, target_platform: Platform, rule: SyncRule) -> UnifiedPost:
        result = deepcopy(post)

        if rule.copy_text_template and result.text:
            result.text = rule.copy_text_template.format(text=result.text)

        if target_platform in {Platform.TELEGRAM, Platform.VK, Platform.MAX} and result.text:
            result.text = result.text[:4096]

        return result
