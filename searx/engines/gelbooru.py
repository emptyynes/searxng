from __future__ import annotations

import typing as t
from urllib.parse import urlencode, urljoin
from lxml import html

from searx.extended_types import SXNG_Response
from searx.result_types import EngineResults
from searx.utils import eval_xpath_list, eval_xpath_getindex

base_url = "https://cum.hnpse.com"

categories = ["images"]
paging = True
timeout = 4.0


def request(query: str, params: dict[str, t.Any]) -> None:
    params["url"] = f"{base_url}/?{urlencode({
        "tags": query,
        "rating": "general",
        "sort": "id",
    })}"
    params["method"] = "GET"


# ----------------------------
# TRY TO RECONSTRUCT FULL IMAGE
# ----------------------------
def _thumb_to_full(url: str) -> str:
    """
    Gelbooru-style trick:
    thumbnails usually contain /thumbnails/
    full images usually are in /images/ or direct CDN path
    """
    if not url:
        return url

    return (
        url
        .replace("/thumbnails/", "/images/")
        .replace("thumbnail_", "")
    )


def response(resp: SXNG_Response) -> EngineResults:
    results = EngineResults()
    dom = html.fromstring(resp.text)

    posts = eval_xpath_list(dom, "//div[contains(@class,'post')]")

    for post in posts:
        href = eval_xpath_getindex(post, ".//a/@href", 0, default=None)
        if not href:
            continue

        post_url = urljoin(base_url, href)

        thumb = eval_xpath_getindex(post, ".//img/@src", 0, default=None)
        if thumb:
            thumb = urljoin(base_url, thumb)

        post_id = href.rsplit("/", 1)[-1]

        # 🔥 FULL IMAGE GUESS (IMPORTANT PART)
        full_img = _thumb_to_full(thumb)

        results.add(
            results.types.LegacyResult(
                template="images.html",

                title=f"Post {post_id}",
                url=post_url,

                # 🔥 THIS is what fixes click-open behavior
                img_src=full_img,

                thumbnail_src=thumb,

                content="",
                source=base_url,
            )
        )

    return results
