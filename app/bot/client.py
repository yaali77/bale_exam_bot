"""
کلاینت سبک برای فراخوانی متدهای Bale Bot API.
مستندات Bale مشابه ساختار Telegram Bot API است.
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

BASE_URL = f"{settings.BALE_API_BASE_URL}/bot{settings.BALE_BOT_TOKEN}"


class BaleClient:
    def __init__(self):
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=15.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def _post(self, method: str, payload: dict) -> dict:
        response = await self._client.post(f"/{method}", json=payload)
        response.raise_for_status()
        return response.json()

    async def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None) -> dict:
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            return await self._post("sendMessage", payload)
        except httpx.HTTPError as exc:
            logger.error("Failed to send message to %s: %s", chat_id, exc)
            raise

    async def send_document(self, chat_id: int, file_path: str, caption: str = "") -> dict:
        files = {"document": open(file_path, "rb")}
        data = {"chat_id": chat_id, "caption": caption}
        response = await self._client.post("/sendDocument", data=data, files=files)
        response.raise_for_status()
        return response.json()

    async def request_contact_keyboard(self, chat_id: int, text: str) -> dict:
        """درخواست شماره تماس واقعی کاربر (نه تایپی) با دکمه اشتراک‌گذاری Contact"""
        keyboard = {
            "keyboard": [[{"text": "📱 ارسال شماره تماس من", "request_contact": True}]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        }
        return await self.send_message(chat_id, text, reply_markup=keyboard)

    async def set_webhook(self) -> dict:
        webhook_url = f"{settings.PUBLIC_BASE_URL}{settings.BALE_WEBHOOK_PATH}"
        return await self._post("setWebhook", {"url": webhook_url})

    async def close(self):
        await self._client.aclose()


bale_client = BaleClient()
