"""
API 基类模块 - 支持代理和重试机制
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any

from astrbot.api import logger


class BaseAPI:
    """API 基类 - 统一管理 HTTP Session，并支持代理重试"""

    def __init__(self,
                 session: Optional[aiohttp.ClientSession] = None,
                 http_proxy: Optional[str] = None,
                 https_proxy: Optional[str] = None,
                 retry_times: int = 3):
        """
        初始化
        Args:
            session: 可复用的 aiohttp.ClientSession
            http_proxy: HTTP 代理地址
            https_proxy: HTTPS 代理地址（默认为 http_proxy）
            retry_times: 最大重试次数（含首次）
        """
        self._session = session
        self._own_session = False
        self.http_proxy = http_proxy
        self.https_proxy = https_proxy or http_proxy
        self.retry_times = max(1, retry_times)

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 session，如果已有则复用，否则创建新的"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self._session

    async def _close_session(self):
        """关闭自己创建的 session"""
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self._own_session = False

    def set_session(self, session: aiohttp.ClientSession):
        """设置新的 session（用于 session 重置）"""
        self._session = session
        self._own_session = False

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        data: Any = None,
        timeout: int = 10,
        **kwargs
    ) -> bytes:
        """
        统一请求方法：首次直连，失败后使用代理重试
        返回 bytes 原始内容，由调用方自行解析
        """
        last_exception = None
        for attempt in range(1, self.retry_times + 1):
            try:
                # 首次尝试或未配置代理 → 直连
                if attempt == 1 or not self.http_proxy:
                    session = await self._get_session()
                    async with session.request(
                        method, url,
                        headers=headers,
                        params=params,
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                        **kwargs
                    ) as resp:
                        resp.raise_for_status()
                        return await resp.read()
                else:
                    # 使用代理新建独立 session（避免污染共享 session）
                    proxy = self.https_proxy if url.startswith('https') else self.http_proxy
                    connector = aiohttp.TCPConnector()
                    async with aiohttp.ClientSession(connector=connector) as proxy_session:
                        async with proxy_session.request(
                            method, url,
                            proxy=proxy,
                            headers=headers,
                            params=params,
                            data=data,
                            timeout=aiohttp.ClientTimeout(total=timeout),
                            **kwargs
                        ) as resp:
                            resp.raise_for_status()
                            return await resp.read()
            except Exception as e:
                last_exception = e
                logger.warning(f"请求失败 (尝试 {attempt}/{self.retry_times}): {e}")
                if attempt < self.retry_times:
                    await asyncio.sleep(0.5)  # 重试前短暂等待
                continue
        raise last_exception or Exception(f"所有重试失败: {url}")