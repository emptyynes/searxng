# searx/engines/gelbooru_frontend.py

from __future__ import annotations

import re
import typing as t
from urllib.parse import urlencode, urljoin, urlparse, parse_qs, urlunparse, unquote, quote

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

timeout = 5.0

SAFESEARCH_MAP = {
    2: "general",
    1: "sensitive",
    0: "explicit",
}

def request(query: str, params: dict[str, t.Any]) -> None:
    pageno = max(int(params.get("pageno", 1) or 1), 1) - 1

    safesearch = params.get("safesearch", 0)
    rating = SAFESEARCH_MAP.get(safesearch, "general")

    params["url"] = f"{base_url}/?{urlencode({
        'tags': query + '-futa -loli -pregnant -yaoi -futanari -scat -guro',
        'rating': rating,
        'sort': 'id',
        'page': pageno,
    })}"

    params["method"] = "GET"


def _thumb_to_guess_full(proxy_url: str) -> str:
    # разбираем внешний URL
    parsed = urlparse(proxy_url)
    qs = parse_qs(parsed.query)

    if "url" not in qs:
        return proxy_url  # нечего делать

    # достаём и декодируем внутренний URL
    inner = unquote(qs["url"][0])

    # делаем замену путей
    inner = inner.replace(
        "gelbooru.com/thumbnails/",
        "img2.gelbooru.com/samples/"
    )

    # заменяем thumbnail_ -> sample_
    inner = inner.replace("thumbnail_", "sample_")

    # обратно кодируем
    qs["url"] = [quote(inner, safe=":/")]

    # собираем обратно URL
    new_query = urlencode(qs, doseq=True)

    return urlunparse(parsed._replace(query=new_query))


def _extract_field_text(post: html.HtmlElement, field_name: str) -> str | None:
    """
    If the page contains a text dump like:
    FileURL:https://...
    PreviewURL:https://...
    SampleURL:https://...
    try to extract it directly.
    """
    text = post.text_content()
    m = re.search(rf"{re.escape(field_name)}:(\S+)", text)
    return m.group(1) if m else None


def response(resp: SXNG_Response) -> EngineResults:
    results = EngineResults()

    try:
        dom = html.fromstring(resp.text)
    except Exception:
        return results

    posts = eval_xpath_list(dom, "//div[contains(@class,'post')]")

    for post in posts:
        href = eval_xpath_getindex(post, ".//a/@href", 0, default=None)
        if not href:
            continue

        post_url = urljoin(base_url, href)
        post_id = href.rsplit("/", 1)[-1]

        thumb = eval_xpath_getindex(post, ".//img/@src", 0, default=None)
        if thumb:
            thumb = urljoin(base_url, thumb)

        # Best case: the page already exposes direct URLs in text/JSON-ish form.
        file_url = _extract_field_text(post, "FileURL")
        sample_url = _extract_field_text(post, "SampleURL")
        preview_url = _extract_field_text(post, "PreviewURL")

        # Fallbacks if the page doesn't explicitly expose them in the HTML fragment.
        if not file_url:
            file_url = _thumb_to_guess_full(thumb)
        if not preview_url:
            preview_url = thumb

        results.add(
            results.types.LegacyResult(
                template="images.html",
                title=f"Post {post_id}",
                url=post_url,

                # This is the important part:
                # full image here, thumbnail below.
                img_src=file_url or sample_url or preview_url or post_url,
                thumbnail_src=preview_url or sample_url or file_url or post_url,

                content=extract_text(
                    eval_xpath_getindex(post, ".//p[contains(@class,'post-score')]", 0, default=None),
                    allow_none=True,
                ) or "",
                source=base_url,
            )
        )

    return results
