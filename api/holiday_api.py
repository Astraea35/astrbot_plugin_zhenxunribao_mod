"""
节假日 API 处理模块
"""
import json
import aiohttp
from datetime import datetime, date, timedelta
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

    def parse_holidays(self, api_data: Optional[Dict], max_count: int = 5) -> List[Dict]:
        try:
            today = date.today()
            processed_holidays = self._get_calendar_festivals(today)
            seen_holidays = {holiday['name'] for holiday in processed_holidays}
            holidays_data = api_data.get('data', []) if api_data else []

            # ALAPI supplies the authoritative dates for statutory days off.
            # Calendar festivals below keep the report useful when the API only
            # returns a small number of remaining days off.
            if not isinstance(holidays_data, list):
                holidays_data = []
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

    def _get_calendar_festivals(self, today: date) -> List[Dict]:
        """Return upcoming fixed-date and lunar festivals for this and next year."""
        fixed_festivals = {
            (1, 1): '元旦',
            (2, 14): '情人节',
            (3, 8): '妇女节',
            (5, 1): '劳动节',
            (5, 4): '青年节',
            (6, 1): '儿童节',
            (8, 1): '建军节',
            (9, 10): '教师节',
            (10, 1): '国庆节',
            (12, 24): '平安夜',
            (12, 25): '圣诞节',
        }
        lunar_festivals = {
            (1, 1): '春节',
            (1, 15): '元宵节',
            (5, 5): '端午节',
            (7, 7): '七夕节',
            (7, 15): '中元节',
            (8, 15): '中秋节',
            (9, 9): '重阳节',
            (12, 8): '腊八节',
        }
        festivals = []
        seen_names = set()

        def add_festival(festival_date: date, name: str) -> None:
            if festival_date < today or name in seen_names:
                return
            seen_names.add(name)
            festivals.append({'name': name, 'days_left': (festival_date - today).days})

        for year in (today.year, today.year + 1):
            for (month, day), name in fixed_festivals.items():
                add_festival(date(year, month, day), name)
            add_festival(date(year, 4, self._get_qingming_day(year)), '清明节')

        try:
            from zhdate import ZhDate
            current = date(today.year, 1, 1)
            end = date(today.year + 1, 12, 31)
            while current <= end:
                lunar = ZhDate.from_datetime(datetime.combine(current, datetime.min.time()))
                name = lunar_festivals.get((lunar.lunar_month, lunar.lunar_day))
                if name:
                    add_festival(current, name)
                current += timedelta(days=1)
        except ImportError:
            logger.warning("未安装 zhdate，跳过农历节日计算")
        except Exception as e:
            logger.warning(f"计算农历节日失败: {e}")

        return festivals

    @staticmethod
    def _get_qingming_day(year: int) -> int:
        """Calculate Qingming's Gregorian day for years 2000-2099."""
        return int((year % 100) * 0.2422 + 4.81) - int((year % 100) / 4)

    def _get_default_holidays(self) -> List[Dict]:
        return [
            {'name': '周末', 'days_left': 3},
            {'name': '春节', 'days_left': 25},
            {'name': '清明节', 'days_left': 78}
        ]

    async def get_moyu_list_async(self, max_count: int = 5) -> List[Dict]:
        api_data = await self.get_holidays_async()
        return self.parse_holidays(api_data, max_count)
