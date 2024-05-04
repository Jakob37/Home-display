import requests
from bs4 import BeautifulSoup

def get_pollen(city: str) -> dict[str,str]:

    URL = f"https://pollenkoll.se/pollenprognos/{city}"

    response = requests.get(URL)

    pollen_dict = dict()
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        pollen_items = soup.find_all(class_="pollen-city__item")


        for pollen_item in pollen_items:

            plant = pollen_item.find('div', class_='pollen-city__item-name').get_text(strip=True)
            pollen_amount = pollen_item.find('div', class_='pollen-city__item-desc').get_text(strip=True)

            pollen_dict[plant] = pollen_amount
    
    return pollen_dict
