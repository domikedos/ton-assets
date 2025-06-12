import csv
import json
import os
import shutil

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from utlis import normalize_address

TON_VIEWER_URL = "https://tonviewer.com/"
TON_API_ACCOUNT_URL = "https://tonapi.io/v2/accounts/"

TON_LABELS_DIR = "ton-labels/"
ASSETS_DIR = "assets/"
TO_REVIEW_CSV_DIR = "to_review/"
TO_REVIEW_CSV = "to_review/to_review.csv"
RETURN_DIR = "../"

class AssetData:
    address: str
    link: str
    types: str
    label: str
    category: str

    def __init__(self, address: str, link: str, types: str, label: str, category: str):
        self.address = address
        self.link = link
        self.types = types
        self.label = label
        self.category = category

    def __repr__(self):
        return f'Asset({self.address} - {self.link} - {self.types} - {self.label} - {self.category})'

def get_types_from_tonapi(address: str) -> list[str]:
    url = TON_API_ACCOUNT_URL + address
    session = requests.Session()
    retry_strategy = Retry(
        backoff_factor=0.5,
        status_forcelist=[429, 502]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount('https://', adapter)
    response = session.get(url)
    if response.status_code != 200:
        return []

    data = response.json()
    if not "interfaces" in data:
        return []

    return data["interfaces"]

def get_dirs_from_env() -> list[str]:
    dirs = os.getenv("DIRS", "")
    if dirs == "":
        return []

    return dirs.split(",")

def create_csv(assets: list[AssetData]):
    if not os.path.exists(TO_REVIEW_CSV_DIR): # create dir if not exists
        os.mkdir(TO_REVIEW_CSV_DIR)
    with open(TO_REVIEW_CSV, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["link", "category", "label", "types", "address"])

        for asset in assets:
            writer.writerow([asset.link, asset.category, asset.label, asset.types, asset.address])

def clone_ton_labels_repo():
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    repo = f'https://{username}:{password}@github.com/ton-studio/ton-labels.git'

    os.system("git clone " + repo)

def rm_ton_labels_dir():
    shutil.rmtree(TON_LABELS_DIR)

def retrieve_assets_from_json_file(file: str) -> list[AssetData]:
    assets = []
    with open(file, 'r') as f:
        data = json.load(f)

        label = data['metadata']['label']
        category = data['metadata']['category']
        for addr in data['addresses']:
            address = addr['address']
            link = TON_VIEWER_URL + address
            types = get_types_from_tonapi(address)

            assets.append(AssetData(address, link, types, label, category))

    return assets

def retrieve_assets_from_dir(curr_dir: str) -> list[AssetData]:
    try:
        os.chdir(curr_dir)
    except FileNotFoundError: # do nothing if dir not found
        return []

    assets_from_files = []
    for file in os.listdir("."):
        if not file.endswith(".json"):
            continue # skip not *.json files

        assets_from_file = retrieve_assets_from_json_file(file)
        assets_from_files.extend(assets_from_file)

    os.chdir(RETURN_DIR)

    return assets_from_files

def retrieve_assets_from_dirs(dirs: list[str]) -> list[AssetData]:
    os.chdir(TON_LABELS_DIR)
    os.chdir(ASSETS_DIR)

    all_assets = []
    if len(dirs) == 0: # if env DIRS is missing, then iterate throw all dirs
        dirs = os.listdir()

    for curr_dir in dirs:
        if os.path.isfile(curr_dir): # skip files
            continue

        assets_from_dir = retrieve_assets_from_dir(curr_dir)
        all_assets.extend(assets_from_dir)

    os.chdir(RETURN_DIR)
    os.chdir(RETURN_DIR)

    return all_assets

def get_known_assets_addresses() -> set[str]:
    addresses = set()
    for file in os.listdir("."):
        if not file.endswith(".json"): # skip not .json files
            continue

        data_list = json.load(open(file))
        for curr in data_list:
            if "address" not in curr:
                continue # skip if dont contain address

            addresses.add(curr["address"])

    return addresses

def main():
    try:
        clone_ton_labels_repo()

        dirs = get_dirs_from_env()
        assets = retrieve_assets_from_dirs(dirs)

        known_addresses = get_known_assets_addresses()

        unknown_assets = []
        for asset in assets:
            normalized_addr = normalize_address(asset.address, True)
            if not normalized_addr in known_addresses:
                unknown_assets.append(asset)

        create_csv(unknown_assets)
    finally:
        rm_ton_labels_dir()

if __name__ == "__main__":
    main()