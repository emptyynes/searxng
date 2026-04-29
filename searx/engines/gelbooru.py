# searx/engines/gelbooru_frontend.py
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import logging
import typing as t
from urllib.parse import urlencode, urljoin

from lxml import html

from searx.enginelib.traits import EngineTraits
from searx.extended_types import SXNG_Response
from searx.network import get
from searx.result_types import EngineResults
from searx.utils import eval_xpath_getindex, eval_xpath_list, extract_text

logger = logging.getLogger(__name__)

about = {
    "website": "https://cum.hnpse.com/",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

base_url = "https://cum.hnpse.com"
categories = ["images"]
engine_type = "online"
paging = True

# Defaults can be overridden in settings.yml
default_rating = "general"
default_sort = "id"
timeout = 5.0

# If your post pages expose the full image nicely, keep this enabled.
# If it feels too slow, set it to False in the module or override in settings.
fetch_post_page = True


def request(query: str, params: dict[str, t.Any]) -> None:
    pageno = max(int(params.get("pageno", 1) or 1), 1)

    tags = query.strip()
    if not tags:
        tags = ""

    args = {
        "tags": tags,
        "rating": default_rating,
        "sort": default_sort,
    }
    if pageno > 1:
        args["page"] = pageno

    params["url"] = f"{base_url}/?{urlencode(args)}"
    params["method"] = "GET"

    params["headers"]["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    params["headers"]["Referer"] = f"{base_url}/?tags=&rating={default_rating}&sort={default_sort}"
    params["cookies"]["rating"] = default_rating


def _first_nonempty(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _extract_full_image_url(post_url: str, thumb_url: str | None) -> str | None:
    if not fetch_post_page:
        return thumb_url

    try:
        resp = get(
            post_url,
            timeout=timeout,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": base_url,
            },
        )
    except Exception:
        return thumb_url

    if not getattr(resp, "ok", False):
        return thumb_url

    try:
        dom = html.fromstring(resp.text)
    except Exception:
        return thumb_url

    candidates: list[str | None] = [
        eval_xpath_getindex(dom, "//meta[@property='og:image']/@content", 0, default=None),
        eval_xpath_getindex(dom, "//meta[@name='twitter:image']/@content", 0, default=None),
        eval_xpath_getindex(dom, "//img[@id='image']/@src", 0, default=None),
        eval_xpath_getindex(dom, "//img[contains(@class, 'image')]/@src", 0, default=None),
        eval_xpath_getindex(dom, "//img[not(contains(@src, 'thumbnail_'))]/@src", 0, default=None),
    ]

    picked = _first_nonempty(*candidates)
    if not picked:
        return thumb_url

    return urljoin(base_url, picked)


def response(resp: SXNG_Response) -> EngineResults:
    res = EngineResults()

    try:
        dom = html.fromstring(resp.text)
    except Exception:
        return res

    for post in eval_xpath_list(dom, "//div[contains(@class, 'post')]"):
        href = eval_xpath_getindex(post, ".//a/@href", 0, default=None)
        if not href:
            continue

        post_url = urljoin(base_url, href)

        thumb = eval_xpath_getindex(post, ".//img/@src", 0, default=None)
        if thumb:
            thumb = urljoin(base_url, thumb)

        score = extract_text(
            eval_xpath_getindex(post, ".//p[contains(@class, 'post-score')]", 0, default=None),
            allow_none=True,
        )
        post_id = href.rsplit("/", 1)[-1].strip("/") if href else ""
        title = f"Post {post_id}" if post_id else "Image result"

        full_img = _extract_full_image_url(post_url, thumb)

        item = res.types.LegacyResult(
            template="images.html",
            url=post_url,
            title=title,
            img_src=full_img or thumb or post_url,
            thumbnail_src=thumb or full_img or post_url,
            content=score or "",
            source=base_url,
        )
        res.add(item)

    return res


def fetch_traits(engine_traits: EngineTraits) -> None:
    # No special locale/region discovery needed.
    return None
