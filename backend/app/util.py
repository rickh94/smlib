from collections import defaultdict
from typing import Optional

import aiohttp
from fastapi import HTTPException

from app.dependencies import mailgun_enpoint, mailgun_key
from app.sheets import models


async def send_email(
    to: str,
    subject: str,
    text: str,
    from_address: str,
    from_name: str,
    reply_to: Optional[str] = None,
    high_priority: bool = False,
):
    message_data = {
        "from": f"{from_name} <{from_address}>",
        "to": to,
        "subject": subject,
        "text": text,
    }
    if reply_to:
        message_data["h:Reply-To"] = reply_to
    if high_priority:
        message_data["h:X-Priority"] = 1
        message_data["h:X-MSMail-Priority"] = "High"
        message_data["h:Importance"] = "High"
    async with aiohttp.ClientSession() as session:
        res = await session.post(
            mailgun_enpoint,
            auth=aiohttp.BasicAuth("api", mailgun_key),
            data=message_data,
        )
        if res.status != 200:
            raise HTTPException(status_code=500, detail="Could not send email.")


def get_next_prev_page_urls(url, page):
    next_page = url.remove_query_params(["page"]).include_query_params(page=(page + 1))
    prev_page = None
    if page > 1:
        prev_page = url.remove_query_params(["page"]).include_query_params(
            page=(page - 1)
        )
    return prev_page, next_page


def get_sort_links(url, sort, direction):
    sort_links = defaultdict(lambda: "")
    for field in models.Sheet.sortable_fields():
        sort_links[field] = url.remove_query_params(
            ["sort", "direction"]
        ).include_query_params(sort=field)
        if field == sort:
            sort_links[field] = (
                sort_links[field]
                .remove_query_params(["direction"])
                .include_query_params(direction=direction * -1)
            )
    return sort_links
