# searx/engines/gelbooru_frontend.py

from __future__ import annotations

import typing as t
from urllib.parse import urlencode, urljoin
from lxml import html

from searx.extended_types import SXNG_Response
from searx.result_types import EngineResults
from searx.utils import eval_xpath_list, eval_xpath_getindex, extract_text

about = {
    "website": "https://cum.hnpse.com/",
    "use_official_api": False,
    "results": "HTML",
}

base_url = "https://cum.hnpse.com"

categories = ["images"]
paging = True
engine_type = "online"

timeout = 4.0

# 🔥 ключевая настройка: больше НЕ ходим в пост-страницы
enable_full_fetch = False


# -------------------------
# REQUEST (list mode only)
# -------------------------
def request(query: str, params: dict[str, t.Any]) -> None:
    pageno = max(int(params.get("pageno", 1) or 1), 1)

    params["url"] = f"{base_url}/?{urlencode({
        'tags': query,
        'rating': 'general',
        'sort': 'id',
        'page': pageno
    })}"

    params["method"] = "GET"


# -------------------------
# RESPONSE (FAST MODE)
# -------------------------
def response(resp: SXNG_Response) -> EngineResults:
    results = EngineResults()

    dom = html.fromstring(resp.text)

    posts = eval_xpath_list(dom, "//div[contains(@class, 'post')]")

    for post in posts:
        href = eval_xpath_getindex(post, ".//a/@href", 0, default=None)
        if not href:
            continue

        post_url = urljoin(base_url, href)

        thumb = eval_xpath_getindex(post, ".//img/@src", 0, default=None)
        if thumb:
            thumb = urljoin(base_url, thumb)

        score = extract_text(
            eval_xpath_getindex(post, ".//p[contains(@class,'post-score')]", 0, default=None),
            allow_none=True,
        )

        post_id = href.rsplit("/", 1)[-1]

        results.add(
            results.types.LegacyResult(
                template="images.html",

                # FAST MODE: всё только через thumbnail
                img_src=thumb or post_url,
                thumbnail_src=thumb or post_url,

                url=post_url,
                title=f"Post {post_id}",
                content=score or "",
                source=base_url,
            )
        )

    return results
