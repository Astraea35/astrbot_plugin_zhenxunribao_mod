"""
IT之家 RSS 处理模块
"""
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Optional
from html import unescape

from astrbot.api import logger
from .base_api import BaseAPI


class ITHomeRSS(BaseAPI):
    def __init__(self,
                 session: Optional[aiohttp.ClientSession] = None,
                 http_proxy: Optional[str] = None,
                 https_proxy: Optional[str] = None,
                 retry_times: int = 3):
        super().__init__(session, http_proxy, https_proxy, retry_times)
        self.url = "https://www.ithome.com/rss/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def get_rss_async(self) -> Optional[ET.Element]:
        try:
            # 限制读取大小，防止 XML 炸弹
            max_size = 10 * 1024 * 1024
            content = await self._request_with_retry(
                method='GET',
                url=self.url,
                headers=self.headers,
                timeout=10
            )
            if len(content) > max_size:
                logger.warning(f"RSS内容过大 ({len(content)} bytes)，已截断至 {max_size} bytes")
                content = content[:max_size]
            return ET.fromstring(content)
        except Exception as e:
            logger.warning(f"获取 RSS 失败: {e}")
            return None

    def parse_news(self, rss_root: Optional[ET.Element], max_count: int = 5) -> List[str]:
        if not rss_root:
            return self._get_default_news()
        try:
            channel = rss_root.find('channel')
            if channel is None:
                return self._get_default_news()
            items = channel.findall('item')
            news_list = []
            for item in items[:max_count]:
                title_elem = item.find('title')
                if title_elem is not None and title_elem.text:
                    title = unescape(title_elem.text.strip())
                    title = ' '.join(title.split())
                    if title:
                        news_list.append(title)
            if not news_list:
                logger.warning("未找到新闻数据，使用默认数据")
                return self._get_default_news()
            return news_list
        except Exception as e:
            logger.error(f"解析 RSS 数据时出错: {e}", exc_info=True)
            return self._get_default_news()

    def _get_default_news(self) -> List[str]:
        return [
            '新AI模型发布，性能大幅提升',
            '科技公司发布最新产品',
            '开源项目获得重大更新',
            '网络安全事件引发关注',
            '云计算服务推出新功能'
        ]

    async def get_it_news_async(self, max_count: int = 5) -> List[str]:
        rss_root = await self.get_rss_async()
        return self.parse_news(rss_root, max_count)