from __future__ import annotations

import logging
import mimetypes
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx

from app.domain.enums import ContentType
from app.domain.models import MediaItem

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page, Playwright

logger = logging.getLogger(__name__)
_CREATE_BUTTON_RE = re.compile(r"^(Создать|Create)$")
_NEW_POST_RE = re.compile(r"^(Новый пост|New post)$")
_TEXTBOX_RE = re.compile(r"(Напишите что-нибудь|Write something)")
_NEXT_BUTTON_RE = re.compile(r"^(Далее|Next)$")
_PUBLISH_BUTTON_RE = re.compile(r"^(Опубликовать|Publish)$")
_POST_LINK_RE = re.compile(r"wall-\d+_(\d+)")
_UPLOAD_ERROR_RE = re.compile(r"(Не удалось загрузить|Upload failed)", re.IGNORECASE)
_FILE_CONTENT_TYPES = {
    ContentType.IMAGE,
    ContentType.VIDEO,
    ContentType.AUDIO,
    ContentType.DOCUMENT,
}


class VkBrowserPublishError(RuntimeError):
    pass


class VkBrowserPublisher:
    def __init__(self, *, cdp_url: str, group_id: int, timeout_ms: int = 120_000) -> None:
        self.cdp_url = cdp_url
        self.group_id = group_id
        self.timeout_ms = timeout_ms

    async def publish_post(self, *, text: str, media: list[MediaItem]) -> str:
        if not self.cdp_url:
            raise VkBrowserPublishError("vk browser cdp url is not configured")

        try:
            from playwright.async_api import async_playwright
        except Exception as exc:
            raise VkBrowserPublishError(
                "browser fallback requires optional dependency 'playwright'; install it via `pip install .[vk-browser]`"
            ) from exc

        temp_dir = Path(tempfile.mkdtemp(prefix="vk-browser-publish-"))
        page: Any | None = None
        playwright: Any | None = None
        prepared_files: list[Path] = []

        try:
            prepared_files = await self._prepare_files(media=media, temp_dir=temp_dir)
            playwright = await async_playwright().start()
            browser = await playwright.chromium.connect_over_cdp(self.cdp_url, timeout=self.timeout_ms)
            if not browser.contexts:
                raise VkBrowserPublishError("no browser contexts available over CDP")

            context = browser.contexts[0]
            page = await context.new_page()
            page.set_default_timeout(self.timeout_ms)
            await page.goto(f"https://vk.com/club{self.group_id}", wait_until="domcontentloaded", timeout=self.timeout_ms)
            await self._open_new_post_dialog(page)
            if prepared_files:
                await self._upload_files(page=page, file_paths=prepared_files)
            if text:
                await self._fill_text(page=page, text=text)
            await self._advance_to_publish(page)
            await self._publish(page)
            return await self._extract_post_id(page=page, expected_text=text)
        finally:
            if page is not None:
                await page.close()
            if playwright is not None:
                await playwright.stop()
            for file_path in prepared_files:
                if file_path.exists() and file_path.parent == temp_dir:
                    file_path.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()

    async def _prepare_files(self, *, media: list[MediaItem], temp_dir: Path) -> list[Path]:
        files: list[Path] = []
        for index, item in enumerate(media):
            if item.type not in _FILE_CONTENT_TYPES:
                continue
            location = str(item.url or item.file_id or "").strip()
            if not location:
                continue
            extension = self._detect_extension(
                item=item,
                fallback={
                    ContentType.IMAGE: ".jpg",
                    ContentType.VIDEO: ".mp4",
                    ContentType.AUDIO: ".mp3",
                    ContentType.DOCUMENT: ".bin",
                }.get(item.type, ".bin"),
            )
            if location.startswith(("http://", "https://")):
                target = temp_dir / f"{item.type.value}-{index}{extension}"
                async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                    response = await client.get(location)
                    response.raise_for_status()
                    target.write_bytes(response.content)
                files.append(target)
                continue

            path = Path(location)
            if not path.exists():
                logger.warning(f"vk browser fallback skipping unavailable media file: {location}")
                continue
            files.append(path)
        return files

    async def _open_new_post_dialog(self, page: Any) -> None:
        create_button = page.get_by_role("button", name=_CREATE_BUTTON_RE).first
        await create_button.click()
        dialog = page.get_by_role("dialog", name=_NEW_POST_RE).first
        try:
            await dialog.wait_for(state="visible", timeout=5_000)
        except Exception:
            await create_button.press("Enter")
            await dialog.wait_for(state="visible", timeout=self.timeout_ms)

    async def _upload_files(self, *, page: Any, file_paths: list[Path]) -> None:
        dialog = page.get_by_role("dialog", name=_NEW_POST_RE).first
        file_input = dialog.locator("input[type='file']").last
        await file_input.set_input_files([str(path) for path in file_paths])
        await page.wait_for_timeout(2_000)
        error_message = page.get_by_text(_UPLOAD_ERROR_RE).first
        if await self._is_visible(error_message):
            raise VkBrowserPublishError("vk web ui rejected the uploaded media")

    async def _fill_text(self, *, page: Any, text: str) -> None:
        composer = page.get_by_role("textbox", name=_TEXTBOX_RE).first
        await composer.fill(text)

    async def _advance_to_publish(self, page: Any) -> None:
        next_button = page.get_by_role("button", name=_NEXT_BUTTON_RE).first
        if await self._is_visible(next_button):
            await next_button.click()
        publish_button = page.get_by_role("button", name=_PUBLISH_BUTTON_RE).first
        await publish_button.wait_for(state="visible", timeout=self.timeout_ms)

    async def _publish(self, page: Any) -> None:
        publish_button = page.get_by_role("button", name=_PUBLISH_BUTTON_RE).first
        await publish_button.click()

    async def _extract_post_id(self, *, page: Any, expected_text: str) -> str:
        article_locator = page.locator("article").first
        text = expected_text.strip()
        if text:
            article_locator = page.locator("article").filter(has_text=text.splitlines()[0]).first
        await article_locator.wait_for(state="visible", timeout=self.timeout_ms)
        link_locator = article_locator.locator("a[href*='wall-']").last
        href = str(await link_locator.get_attribute("href") or "")
        match = _POST_LINK_RE.search(href)
        if match is None:
            raise VkBrowserPublishError(f"could not determine post id from href: {href}")
        return match.group(1)

    async def _is_visible(self, locator: Any) -> bool:
        try:
            return await locator.is_visible(timeout=1_000)
        except Exception:
            return False

    def _detect_extension(self, *, item: MediaItem, fallback: str) -> str:
        candidate = str(item.filename or "").strip()
        if candidate:
            suffix = Path(candidate).suffix.lower()
            if suffix:
                return suffix

        parsed = urlparse(str(item.url or ""))
        suffix = Path(parsed.path).suffix.lower()
        if suffix:
            return suffix

        if item.mime_type:
            guessed = mimetypes.guess_extension(item.mime_type)
            if guessed:
                return guessed

        return fallback
