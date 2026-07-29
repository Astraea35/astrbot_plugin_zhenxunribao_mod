"""
节假日 API 处理模块
"""
import json
import aiohttp
from datetime import datetime, date
from typing import List, Dict, Optional

from astrbot.api import logger
from .base_api import BaseAPI


class HolidayAPI(BaseAPI):
    def __init__(self,
                 token: str,
                 session: Optional[aiohttp.ClientSession] = None,
                 http_proxy: Optional[str] = None,
                 https_proxy: Optional[str] = None,
                 retry_times: int = 3,
                 year: Optional[int] = None):
        super().__init__(session, http_proxy, https_proxy, retry_times)
        self.token = token
        self.url = "https://v3.alapi.cn/api/holiday"
        self.headers = {"Content-Type": "application/json"}
        self.year = year or datetime.now().year

    async def get_holidays_async(self) -> Optional[Dict]:
        try:
            params = {"token": self.token}
            content = await self._request_with_retry(
                method='GET',
                url=self.url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            return json.loads(content.decode('utf-8'))
        except Exception as e:
            logger.warning(f"请求节假日 API 失败: {e}")
            return None

    def parse_holidays(self, api_data: Optional[Dict], max_count: int = 3) -> List[Dict]:
        if not api_data:
            return self._get_default_holidays()
        try:
            holidays_data = api_data.get('data', [])
            if not isinstance(holidays_data, list) or len(holidays_data) == 0:
                return self._get_default_holidays()
            today = date.today()
            processed_holidays = []
            seen_holidays = set()
            for holiday in holidays_data:
                if not isinstance(holiday, dict):
                    continue
                if holiday.get('is_off_day') != 1:
                    continue
                date_str = holiday.get('date')
                if not date_str:
                    continue
                try:
                    holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    continue
                if holiday_date < today:
                    continue
                days_left = (holiday_date - today).days
                name = holiday.get('name', '未知')
                if name in seen_holidays:
                    for i, existing in enumerate(processed_holidays):
                        if existing['name'] == name:
                            if days_left < existing['days_left']:
                                processed_holidays[i] = {'name': name, 'days_left': days_left}
                            break
                else:
                    seen_holidays.add(name)
                    processed_holidays.append({'name': name, 'days_left': days_left})
            processed_holidays.sort(key=lambda x: x['days_left'])
            result = processed_holidays[:max_count]
            if not result:
                logger.warning("未找到未来的节假日数据，使用默认数据")
                return self._get_default_holidays()
            return result
        except Exception as e:
            logger.error(f"解析节假日数据时出错: {e}", exc_info=True)
            return self._get_default_holidays()

    def _get_default_holidays(self) -> List[Dict]:
        return [
            {'name': '周末', 'days_left': 3},
            {'name': '春节', 'days_left': 25},
            {'name': '清明节', 'days_left': 78}
        ]

    async def get_moyu_list_async(self, max_count: int = 3) -> List[Dict]:
        api_data = await self.get_holidays_async()
        return self.parse_holidays(api_data, max_count)