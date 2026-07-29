"""
Bilibili API 处理模块
"""
import json
import aiohttp
from typing import List, Optional, Dict

from astrbot.api import logger
from .base_api import BaseAPI


class BilibiliAPI(BaseAPI):
    def __init__(self,
                 session: Optional[aiohttp.ClientSession] = None,
                 http_proxy: Optional[str] = None,
                 https_proxy: Optional[str] = None,
                 retry_times: int = 3):
        super().__init__(session, http_proxy, https_proxy, retry_times)
        self.url = "https://s.search.bilibili.com/main/hotword"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def _get_default_hotwords(self) -> List[str]:
        return [
            'AI技术新突破引发热议',
            '游戏更新引发玩家讨论',
            '科技区UP主发布新视频',
            '二次元新番话题持续升温'
        ]

    async def get_hotwords_async(self, max_count: int = 4) -> List[str]:
        try:
            content = await self._request_with_retry(
                method='GET',
                url=self.url,
                headers=self.headers,
                timeout=10
            )
            # B站 API 可能返回非标准 JSON，但仍是合法 JSON
            data = json.loads(content.decode('utf-8'))
            if data.get("code") == 0 and data.get("list"):
                return self.parse_hotwords_data(data, max_count)
            else:
                logger.warning(f"API返回异常: code={data.get('code')}")
                return self._get_default_hotwords()[:max_count]
        except Exception as e:
            logger.error(f"获取B站热点失败: {e}", exc_info=True)
            return self._get_default_hotwords()[:max_count]

    def parse_hotwords_data(self, api_data: Optional[Dict], max_count: int = 4) -> List[str]:
        hotwords = []
        if not api_data or not api_data.get("list"):
            return self._get_default_hotwords()[:max_count]
        for item in api_data["list"][:max_count]:
            title = item.get("show_name") or item.get("keyword", "")
            if title:
                hotwords.append(title)
        if len(hotwords) < max_count:
            default_list = self._get_default_hotwords()
            hotwords.extend(default_list[:max_count - len(hotwords)])
        return hotwords[:max_count]