import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

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
        chain_result=lambda chain: chain[0].text,
    )
    results = [result async for result in plugin.daily_news(event)]
    assert all(value in results[0] for value in ("新番", "热搜", "一言", "79", "世界新闻", "科技新闻"))
    assert "**世界新闻**\n\n1. 世界新闻\n\n2. 第二条新闻" in results[0]
    assert "**今日一言**\n\n一言\n\n出处：作者" in results[0]
    plugin._generate_daily_image.assert_not_awaited()


@pytest.mark.asyncio
async def test_telegram_report_attaches_new_anime_covers_in_order():
    plugin = module.ZhenxunReportPlugin.__new__(module.ZhenxunReportPlugin)
    plugin.config = {}
    plugin._fetch_all_data = AsyncMock(return_value=(
        [{"title": "新番A", "image": "https://image.test/a.jpg"},
         {"title": "新番B", "image": "https://image.test/b.jpg"}],
        [], {}, [], [], [],
    ))
    plugin._fetch_anime_cover = AsyncMock(side_effect=[b"image-a", b"image-b"])
    result = await plugin._generate_daily_chain()
    assert "新番A" in result.chain[0].text and "新番B" in result.chain[0].text
    assert len(result.chain) == 3
    assert all(isinstance(component, module.Image) for component in result.chain[1:])
    assert plugin._fetch_all_data.await_count == 1


@pytest.mark.asyncio
async def test_cover_download_uses_explicit_nas_proxy():
    plugin = module.ZhenxunReportPlugin.__new__(module.ZhenxunReportPlugin)
    plugin.config = {"tg_cover_proxy": "http://192.168.1.34:7890"}
    async def chunks():
        yield b"im"
        yield b"age"
    response = SimpleNamespace(
        headers={"Content-Type": "image/jpeg"},
        raise_for_status=Mock(), content=SimpleNamespace(iter_chunked=lambda size: chunks()),
    )
    manager = AsyncMock()
    manager.__aenter__.return_value = response
    session = SimpleNamespace(get=Mock(return_value=manager))
    assert await plugin._fetch_anime_cover(session, "https://image.test/a.jpg") == b"image"
    session.get.assert_called_once_with("https://image.test/a.jpg", proxy="http://192.168.1.34:7890")
