"""
今日一言 API 处理模块
"""
import json
import aiohttp
from typing import Optional, Dict

from astrbot.api import logger
from .base_api import BaseAPI


class HitokotoAPI(BaseAPI):
    def __init__(self,
                 token: str,
                 session: Optional[aiohttp.ClientSession] = None,
                 http_proxy: Optional[str] = None,
                 https_proxy: Optional[str] = None,
                 retry_times: int = 3):
        super().__init__(session, http_proxy, https_proxy, retry_times)
        self.token = token
        self.url = "https://v3.alapi.cn/api/hitokoto"
        self.headers = {"Content-Type": "application/json"}

    def _get_default_hitokoto(self) -> Dict[str, str]:
        return {
            'hitokoto': '生活就像骑自行车，想保持平衡就得往前走。',
            'from': '未知'
        }

    async def get_hitokoto_async(self) -> Dict[str, str]:
        try:
            params = {"token": self.token}
            content = await self._request_with_retry(
                method='GET',
                url=self.url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            data = json.loads(content.decode('utf-8'))
            code = data.get("code")
            success = data.get("success", False)
            if (code == 200 or success) and data.get("data"):
                hitokoto_data = data["data"]
                from_value = hitokoto_data.get("from") or hitokoto_data.get("from_who") or ""
                if not from_value or (isinstance(from_value, str) and (from_value.strip() == "" or from_value.strip() == "网络")):
                    from_value = "佚名"
                else:
                    from_value = str(from_value).strip()
                hitokoto_text = hitokoto_data.get("hitokoto", "")
                return {'hitokoto': hitokoto_text, 'from': from_value}
            else:
                logger.warning(f"API返回异常: code={code}, message={data.get('message', '未知错误')}")
                return self._get_default_hitokoto()
        except Exception as e:
            logger.error(f"获取今日一言失败: {e}", exc_info=True)
            return self._get_default_hitokoto()