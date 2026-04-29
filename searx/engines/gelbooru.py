# SPDX-License-Identifier: AGPL-3.0-or-later
"""Gelbooru image search engine for SearXNG."""

from urllib.parse import urlencode

about = {
    "website": "https://gelbooru.com/",
    "official_api_documentation": "https://gelbooru.com/index.php?page=help&topic=dapi",
    "use_official_api": True,
    "require_api_key": True,
    "results": "JSON",
}

categories = ["images"]
engine_type = "online"
paging = True
safesearch = True

base_url = "https://gelbooru.com/index.php"

api_key = ""
user_id = ""
per_page = 100


def setup(engine_settings):
    global api_key, user_id, per_page

    api_key = str(engine_settings.get("api_key", "")).strip()
    user_id = str(engine_settings.get("user_id", "")).strip()

    if not api_key or not user_id:
        return False

    try:
        per_page = int(engine_settings.get("per_page", 100))
    except Exception:
        return False

    if per_page < 1 or per_page > 100:
        return False

    return True


def _apply_safesearch(query, params):
    tags = query.split()

    if params.get("safesearch"):
        if "rating:safe" not in tags:
            tags.append("rating:safe")

    return " ".join(tags).strip()


def request(query, params):
    query = _apply_safesearch(query, params)

    query_params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "json": "1",
        "tags": query,
        "limit": per_page,
        "pid": max(int(params.get("pageno", 1)) - 1, 0),
        "api_key": api_key,
        "user_id": user_id,
    }

    params["url"] = base_url + "?" + urlencode(query_params)
    return params


def response(resp):
    results = []

    try:
        data = resp.json()
    except Exception:
        return results

    posts = data.get("post", [])

    if isinstance(posts, dict):
        posts = [posts]

    for post in posts:
        file_url = post.get("file_url") or ""
        preview_url = post.get("preview_url") or ""
        sample_url = post.get("sample_url") or ""

        if not file_url:
            continue

        img_src = sample_url if sample_url else file_url

        tags = post.get("tags", "") or ""
        rating = post.get("rating", "") or ""
        width = post.get("width")
        height = post.get("height")
        source = post.get("source", "") or ""

        title = post.get("title") or " ".join(tags.split()[:6])

        results.append(
            {
                "template": "images.html",
                "url": file_url,
                "img_src": img_src,
                "thumbnail_src": preview_url if preview_url else img_src,
                "title": title,
                "content": "rating: " + rating if rating else None,
                "source": source,
                "resolution": str(width) + "x" + str(height) if width and height else None,
            }
        )

    return results
