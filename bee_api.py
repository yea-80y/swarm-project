# bee_api.py

import requests
from decimal import Decimal
from config import BEE_API_URL, web3, POSTAGE_CONTRACT_ADDRESS, POSTAGE_CONTRACT_ABI, PLUR_PER_xBZZ


def is_connected_to_bee():
    """Check if the Bee node is up and healthy."""
    try:
        return requests.get(f"{BEE_API_URL}/health").status_code == 200
    except:
        return False


def get_wallet_balance():
    """Get the wallet balance from Bee and return it in xBZZ."""
    try:
        response = requests.get(f"{BEE_API_URL}/wallet")
        if response.status_code == 200:
            balance_plur = Decimal(response.json().get("bzzBalance", 0))
            return balance_plur / PLUR_PER_xBZZ
    except:
        return Decimal(0)


def get_existing_stamps():
    """Retrieve a list of all batches (stamps) from the Bee node."""
    try:
        response = requests.get(f"{BEE_API_URL}/stamps")
        if response.status_code == 200:
            return response.json().get("stamps", [])
    except:
        return []
    return []


def create_tag():
    """Create a tag for tracking upload progress."""
    try:
        response = requests.post(f"{BEE_API_URL}/tags")
        if response.status_code == 201:
            return response.json().get("uid")
    except:
        return None


def get_tag_progress(tag_uid):
    """Check how much of the upload has been processed using a tag UID."""
    try:
        response = requests.get(f"{BEE_API_URL}/tags/{tag_uid}")
        if response.status_code == 200:
            tag = response.json()
            total = tag.get("total", 1)
            processed = tag.get("processed", 0)
            return int((processed / total) * 100) if total > 0 else 0
    except:
        return None


def wait_for_stamp_usable(batch_id, blocks=10, block_time=5):
    """Pause and then poll until a new stamp batch becomes usable."""
    import time

    time.sleep(int(blocks) * block_time)
    while True:
        try:
            res = requests.get(f"{BEE_API_URL}/stamps/{batch_id}")
            if res.status_code == 200 and res.json().get("usable", False):
                break
        except:
            pass
        time.sleep(5)


def get_price_per_block():
    """Fetch the current price per block from the Swarm postage contract."""
    try:
        contract = web3.eth.contract(address=POSTAGE_CONTRACT_ADDRESS, abi=POSTAGE_CONTRACT_ABI)
        return Decimal(contract.functions.lastPrice().call())
    except:
        return None
