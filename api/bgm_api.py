"""
BGM (Bangumi) API 处理模块
"""
import json
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional

from astrbot.api import logger
from .base_api import BaseAPI


class BGMAPI(BaseAPI):
    def __init__(self,
                 session: Optional[aiohttp.ClientSession] = None,
                 http_proxy: Optional[str] = None,
                 https_proxy: Optional[str] = None,
                 retry_times: int = 3):
        super().__init__(session, http_proxy, https_proxy, retry_times)
        self.url = "https://api.bgm.tv/calendar"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def get_calendar_async(self) -> Optional[List]:
        try:
            content = await self._request_with_retry(
                method='GET',
                url=self.url,
                headers=self.headers,
                timeout=10
            )
            return json.loads(content.decode('utf-8'))
        except Exception as e:
            logger.warning(f"请求 BGM API 失败: {e}")
            return None

    def parse_today_anime(self, api_data: Optional[List], max_count: int = 4) -> List[Dict]:
        if not api_data or not isinstance(api_data, list):
            return self._get_default_anime()
        try:
            today_weekday = datetime.now().weekday() + 1
            anime_list = []
            for day_data in api_data:
                if not isinstance(day_data, dict):
                    continue
                weekday_info = day_data.get('weekday', {})
                weekday_id = weekday_info.get('id')
                if weekday_id == today_weekday:
                    items = day_data.get('items', [])
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        name_cn = item.get('name_cn', '')
                        name_jp = item.get('name', '')
                        title = name_cn if name_cn else name_jp
                        images = item.get('images', {})
                        image_url = images.get('medium', '') or images.get('common', '')
                        if title and image_url:
                            anime_list.append({'title': title, 'image': image_url})
                        if len(anime_list) >= max_count:
                            break
                    break
            if not anime_list:
                logger.warning("未找到今日新番数据，使用默认数据")
                return self._get_default_anime()
            return anime_list
        except Exception as e:
            logger.error(f"解析 BGM 数据时出错: {e}", exc_info=True)
            return self._get_default_anime()

    def _get_default_anime(self) -> List[Dict]:
        # 使用在线占位图避免本地文件缺失警告
        return [
            {'title': '葬送的芙莉莲 第二季', 'image': 'https://via.placeholder.com/84x126/cccccc/ffffff?text=No+Image'},
            {'title': '咒术回战 涉谷事变篇', 'image': 'https://via.placeholder.com/84x126/cccccc/ffffff?text=No+Image'},
            {'title': '间谍过家家 第三季', 'image': 'https://via.placeholder.com/84x126/cccccc/ffffff?text=No+Image'},
            {'title': '鬼灭之刃 柱训练篇', 'image': 'https://via.placeholder.com/84x126/cccccc/ffffff?text=No+Image'}
        ]

    async def get_today_anime_async(self, max_count: int = 4) -> List[Dict]:
        api_data = await self.get_calendar_async()
        return self.parse_today_anime(api_data, max_count)