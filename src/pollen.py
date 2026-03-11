import requests
from bs4 import BeautifulSoup


POLLEN_LEVEL_KEYWORDS = (
    (5, ("mycket höga", "very high", "extrem")),
    (4, ("höga", "high")),
    (3, ("måttliga", "moderate", "medel")),
    (1, ("mycket låga", "very low")),
    (2, ("låga", "low")),
    (0, ("ingen", "none")),
)


def parse_pollen_level(amount: str) -> int:
    normalized_amount = amount.strip().lower()

    if not normalized_amount:
        return 0

    for level, keywords in POLLEN_LEVEL_KEYWORDS:
        if any(keyword in normalized_amount for keyword in keywords):
            return level

    digits = "".join(char for char in normalized_amount if char.isdigit())
    if digits:
        return max(0, min(int(digits), 5))

    return 0


def get_pollen(city: str) -> dict[str, dict[str, str | int]]:

    URL = f"https://pollenkoll.se/pollenprognos/{city}"
   
    response = None
    try:
        res = requests.get(URL)
        res.raise_for_status()
        response = res
    except requests.exceptions.RequestException as e:
        return {"Error": {"raw_level": str(e), "level": 0}}

    pollen_dict = dict()
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        pollen_items = soup.find_all(class_="pollen-city__item")


        for pollen_item in pollen_items:

            plant = pollen_item.find('div', class_='pollen-city__item-name').get_text(strip=True)
            pollen_amount = pollen_item.find('div', class_='pollen-city__item-desc').get_text(strip=True)

            pollen_dict[plant] = {
                "raw_level": pollen_amount,
                "level": parse_pollen_level(pollen_amount),
            }
    
    return pollen_dict
