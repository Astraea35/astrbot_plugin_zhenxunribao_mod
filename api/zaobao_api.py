"""
早报 API 处理模块
"""
import json
import re
import aiohttp
from typing import List, Dict, Optional

from astrbot.api import logger
from .base_api import BaseAPI

NUMBER_PREFIX_PATTERN = re.compile(r'^\d+[\.、]\s*')


class ZaobaoAPI(BaseAPI):
    def __init__(self,
                 token: str,
                 session: Optional[aiohttp.ClientSession] = None,
                 http_proxy: Optional[str] = None,
                 https_proxy: Optional[str] = None,
                 retry_times: int = 3):
        super().__init__(session, http_proxy, https_proxy, retry_times)
        self.token = token
        self.url = "https://v3.alapi.cn/api/zaobao"
        self.headers = {"Content-Type": "application/json"}

    async def get_zaobao_async(self) -> Optional[Dict]:
        try:
            params = {"token": self.token, "format": "json"}
            content = await self._request_with_retry(
                method='GET',
                url=self.url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            return json.loads(content.decode('utf-8'))
        except Exception as e:
            logger.warning(f"请求早报 API 失败: {e}")
            return None

    def parse_news(self, api_data: Optional[Dict], max_count: int = 5) -> List[str]:
        if not api_data:
            return self._get_default_news()
        try:
            if 'data' in api_data and isinstance(api_data['data'], dict):
                news_data = api_data['data'].get('news', [])
                if isinstance(news_data, list):
                    news_list = []
                    for item in news_data:
                        if isinstance(item, str):
                            cleaned = item.strip()
                            cleaned = NUMBER_PREFIX_PATTERN.sub('', cleaned)
                            if cleaned:
                                news_list.append(cleaned)
                        if len(news_list) >= max_count:
                            break
                    if news_list:
                        return news_list
            logger.warning("未找到新闻数据，使用默认数据")
            return self._get_default_news()
        except Exception as e:
            logger.error(f"解析早报数据时出错: {e}", exc_info=True)
            return self._get_default_news()

    def _get_default_news(self) -> List[str]:
        return [
            '全球科技峰会召开，AI发展成焦点',
            '国际油价波动引发市场关注',
            '新政策影响国际贸易',
            '环保议题持续升温',
            '体育赛事精彩纷呈'
        ]

    async def get_world_news_async(self, max_count: int = 5) -> List[str]:
        api_data = await self.get_zaobao_async()
        return self.parse_news(api_data, max_count)