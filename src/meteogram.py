"""Keep meteogram labels readable when the image is compressed vertically."""

from functools import lru_cache
from time import time
from xml.etree import ElementTree as ET

import requests

YR_METEOGRAM_URL = "https://www.yr.no/en/content/2-2693678/meteogram.svg"


@lru_cache(maxsize=2)
def _download_svg(cache_period):
    response = requests.get(YR_METEOGRAM_URL, timeout=10)
    response.raise_for_status()
    return response.content


def readable_meteogram(local_path=None, vertical_scale=1.0):
    source = local_path.read_bytes() if local_path else _download_svg(int(time() // 1800))
    root = ET.fromstring(source)
    for parent in root.iter():
        for child in list(parent):
            if "location-header" in child.get("class", "").split():
                parent.remove(child)
    # Counter the page's vertical stretch around each label's own center,
    # keeping labels at 85% size with consistent proportions in both layouts.
    style = ET.SubElement(root, "{http://www.w3.org/2000/svg}style")
    style.text = (
        "text { transform-box: fill-box; transform-origin: center; "
        f"transform: scale(0.85, {0.85 / vertical_scale:.9f}); }}"
    )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
