import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "_zhenxun_telegram_test"
package = type(sys)(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package
spec = importlib.util.spec_from_file_location(PACKAGE + ".main", ROOT / "main.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.asyncio
async def test_telegram_report_uses_all_original_sources_without_a_browser():
    plugin = module.ZhenxunReportPlugin.__new__(module.ZhenxunReportPlugin)
    plugin.config = {}
    plugin._fetch_all_data = AsyncMock(return_value=(
        [{"title": "新番"}], ["热搜"], {"hitokoto": "一言", "from": "作者"},
        [{"name": "元旦", "days_left": 79}], ["世界新闻", "第二条新闻"], ["科技新闻"],
    ))
    plugin._generate_daily_image = AsyncMock()
    event = SimpleNamespace(
        unified_msg_origin="nas_tg:FriendMessage:123",
        get_platform_name=lambda: "telegram",
        plain_result=lambda text: text,
    )
    results = [result async for result in plugin.daily_news(event)]
    assert all(value in results[0] for value in ("新番", "热搜", "一言", "79", "世界新闻", "科技新闻"))
    assert "**世界新闻**\n\n1. 世界新闻\n\n2. 第二条新闻" in results[0]
    assert "**今日一言**\n\n一言\n\n出处：作者" in results[0]
    plugin._generate_daily_image.assert_not_awaited()
