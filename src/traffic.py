#!/usr/bin/env python3

import requests

def get_train_table_zip(api: str, static_url: str):
    url = f'{static_url}?key={api}'
    response = requests.get(url)
    train_zip = response.content

    f = open('traffic.zip', 'wb')
    f.write(train_zip)
    f.close()


    print(response)

    if response.status_code != 200:
        print(f"Error {response.status_code}")
        return []


