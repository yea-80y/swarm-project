# bee_api.py

import requests
import time
from config import BEE_API_URL, WAIT_FOR_BATCH_TIMEOUT, WAIT_FOR_BATCH_RETRY
from utils import play_notification_sound


def is_connected_to_bee():
    try:
        response = requests.get(f"{BEE_API_URL}/health")
        return response.status_code == 200
    except:
        return False


def get_wallet_balance():
    try:
        response = requests.get(f"{BEE_API_URL}/wallet")
        if response.status_code == 200:
            return int(response.json().get("bzzBalance", 0)) / 10**16
    except:
        return 0


def get_existing_stamps():
    try:
        response = requests.get(f"{BEE_API_URL}/stamps")
        if response.status_code == 200:
            return response.json().get("stamps", [])
    except:
        return []


def get_price_per_block():
    try:
        response = requests.get(f"{BEE_API_URL}/chainstate")
        if response.status_code == 200:
            return int(response.json().get("currentPrice", 0))
    except:
        return 0


def create_tag():
    try:
        response = requests.post(f"{BEE_API_URL}/tags")
        if response.status_code == 201:
            return response.json().get("uid")
    except:
        return None


def get_tag_progress(tag_uid):
    try:
        response = requests.get(f"{BEE_API_URL}/tags/{tag_uid}")
        if response.status_code == 200:
            split = response.json().get("split")
            total = response.json().get("total")
            if total:
                return round(split / total * 100)
    except:
        return None


def wait_for_stamp_usable(batch_id):
    """
    Waits for a batch to become usable, with timeout and connectivity checks.
    """
    print("⏳ Waiting for batch to become usable...")
    start_time = time.time()

    while time.time() - start_time < WAIT_FOR_BATCH_TIMEOUT:
        try:
            response = requests.get(f"{BEE_API_URL}/stamps/{batch_id}")
            if response.status_code == 200:
                if response.json().get("usable", False):
                    print("✅ Batch is now usable.")
                    play_notification_sound()
                    return True
                else:
                    print("...still waiting...")
            else:
                print(f"⚠️ Unexpected status while checking stamp: {response.status_code}")
        except Exception as e:
            print(f"❌ Connection error while checking batch usability: {e}")
            return False
        time.sleep(WAIT_FOR_BATCH_RETRY)

    print("❌ Timeout: Batch did not become usable within expected time.")
    return False
