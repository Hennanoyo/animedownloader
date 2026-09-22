from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element

from animedownloader_releases import Release
from defusedxml import ElementTree

SOURCE = "nyaa"


def parse_rss_feed(xml_text: str) -> list[Release]:
    root = ElementTree.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS channel was not found")

    releases: list[Release] = []
    for item in channel.findall("item"):
        title = _text(item, "title")
        link = _text(item, "link")
        guid = _text(item, "guid")

        if not title or not link:
            continue

        page_url = guid or link
        enclosure = item.find("enclosure")
        torrent_url = link
        if not torrent_url and enclosure is not None:
            torrent_url = enclosure.get("url", "")

        releases.append(
            Release(
                source=SOURCE,
                id=guid or link,
                title=title,
                page_url=page_url,
                torrent_url=torrent_url,
                published_at=_parse_date(_text(item, "pubDate")),
                size=_custom_text(item, "size"),
                seeders=_parse_int(_custom_text(item, "seeders")),
                leechers=_parse_int(_custom_text(item, "leechers")),
                downloads=_parse_int(_custom_text(item, "downloads")),
                info_hash=_custom_text(item, "infoHash"),
            )
        )

    return releases


def _text(element: Element, name: str) -> str | None:
    child = element.find(name)
    if child is None or child.text is None:
        return None

    value = child.text.strip()
    return value or None


def _custom_text(element: Element, local_name: str) -> str | None:
    for child in element:
        tag = child.tag
        if tag.rsplit("}", maxsplit=1)[-1] == local_name:
            if child.text is None:
                return None
            value = child.text.strip()
            return value or None

    return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def _parse_date(value: str | None) -> datetime | None:
    if value is None:
        return None

    try:
        return parsedate_to_datetime(value)
    except TypeError, ValueError, IndexError:
        return None
