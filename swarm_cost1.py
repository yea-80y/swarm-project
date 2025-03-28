import requests
import json
import os
import math
import mimetypes
import time
from web3 import Web3
from decimal import Decimal, getcontext

# Set higher precision for decimal calculations
getcontext().prec = 20

# Connect to Ethereum Bee Node and Web3 provider
WEB3_RPC_URL = "https://rpc.gnosischain.com"
BEE_API_URL = "http://localhost:1633"
web3 = Web3(Web3.HTTPProvider(WEB3_RPC_URL))

# Contract details for fetching price per block
POSTAGE_CONTRACT_ADDRESS = "0x45a1502382541Cd610CC9068e88727426b696293"
POSTAGE_CONTRACT_ABI = [
    {"inputs": [], "name": "lastPrice", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
]

# Constants for conversion and storage duration
PLUR_PER_xBZZ = Decimal(10**16)  # Conversion factor
CHUNK_SIZE_BYTES = Decimal(4096)  # Size of each chunk in bytes
BLOCKS_PER_YEAR = Decimal(6_307_200)  # Estimated number of blocks in one year
BLOCK_TIME_SECONDS = Decimal(5)  # Block interval on Gnosis Chain
STORAGE_TIME_SECONDS = Decimal(365 * 24 * 60 * 60)  # 1 year in seconds

# Checks connection to the Bee node
def is_connected_to_bee():
    url = f'{BEE_API_URL}/health'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Connected to local Bee node.")
            return True
        else:
            print("Failed to connect to Bee node. Status code:", response.status_code)
            return False
    except requests.ConnectionError:
        print("Failed to connect to Bee node. Connection error.")
        return False

# Retrieves existing stamps from the Bee node
def get_existing_stamps(base_url):
    try:
        response = requests.get(f'{base_url}/stamps')
        if response.status_code == 200:
            stamps = response.json().get('stamps', [])
            if not stamps:
                print("No existing stamps found.")
            return stamps
        else:
            print("No existing stamps found.")
            return []
    except requests.RequestException:
        print("Error fetching existing stamps.")
        return []

# Fetches the current postage price per block from the contract
def get_price_per_block():
    try:
        contract = web3.eth.contract(address=POSTAGE_CONTRACT_ADDRESS, abi=POSTAGE_CONTRACT_ABI)
        return Decimal(contract.functions.lastPrice().call())
    except Exception as e:
        print(f"Error fetching price per block from contract: {e}")
        return None

# Gets the xBZZ wallet balance from the Bee node
def get_wallet_balance(base_url):
    try:
        response = requests.get(f'{base_url}/wallet')
        if response.status_code == 200:
            balance_data = response.json()
            balance_plur = Decimal(balance_data.get('bzzBalance', 0))
            balance_xbzz = balance_plur / PLUR_PER_xBZZ
            return balance_xbzz
        else:
            print("Failed to fetch wallet balance. Status code:", response.status_code)
            return None
    except requests.RequestException:
        print("Error fetching wallet balance.")
        return None

# Calculates the minimum depth required to store a file of the given size
def calculate_required_depth(file_size):
    for depth in range(17, 32):
        max_volume_bytes = (Decimal(2) ** Decimal(depth)) * CHUNK_SIZE_BYTES
        if file_size <= max_volume_bytes:
            return depth
    return 31  # Use max depth as fallback

# Calculates required PLUR and xBZZ to store a file for 1 year
def calculate_required_plur(depth, price_per_block):
    depth = Decimal(depth)
    amount = (price_per_block / BLOCK_TIME_SECONDS) * STORAGE_TIME_SECONDS
    total_plur = (Decimal(2) ** depth) * amount
    total_xbzz = total_plur / PLUR_PER_xBZZ

    print(f"\nDepth: {depth}")
    print(f"Amount per chunk: {amount:.6f} PLUR")
    print(f"Total PLUR required: {total_plur:.6f}")
    print(f"Total xBZZ required: {total_xbzz:.6f}")

    return amount, total_plur, total_xbzz

# Creates a tag to track upload progress
def create_tag(base_url):
    try:
        response = requests.post(f"{base_url}/tags")
        if response.status_code == 201:
            return response.json().get("uid")
    except requests.RequestException as e:
        print(f"Error creating tag: {e}")
    return None

# Polls the tag to check upload progress and return percentage complete
def get_tag_progress(base_url, tag_uid):
    try:
        response = requests.get(f"{base_url}/tags/{tag_uid}")
        if response.status_code == 200:
            tag = response.json()
            total = tag.get("total", 1)
            processed = tag.get("processed", 0)
            percent = int((processed / total) * 100) if total > 0 else 0
            return percent
    except requests.RequestException:
        pass
    return None

# Purchases a new postage stamp
def purchase_postage_stamp(base_url, amount, depth, label, mutable):
    immutable_flag = "false" if mutable else "true"
    try:
        response = requests.post(f'{base_url}/stamps/{int(amount)}/{depth}', headers={"immutable": immutable_flag})
        if response.status_code == 201:
            batch_id = response.json().get('batchID')
            print(f"Stamp successfully purchased with label '{label}'. Batch ID: {batch_id}")
            return batch_id
        else:
            print(f"Failed to purchase stamp. Status code: {response.status_code}, Message: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Error purchasing stamp: {e}")
        return None

# Waits for the newly created stamp to become usable (after 10+ blocks)
def wait_for_stamp_usable(base_url, batch_id, min_wait_blocks=10):
    print("\nUpload pending... This usually takes less than a minute.")
    time.sleep(int(min_wait_blocks) * int(BLOCK_TIME_SECONDS))
    while True:
        try:
            response = requests.get(f"{base_url}/stamps/{batch_id}")
            if response.status_code == 200:
                usable = response.json().get("usable", False)
                if usable:
                    break
        except requests.RequestException:
            pass
        time.sleep(5)

# Uploads the file to the Bee node using the specified batch
def upload_file(base_url, file_path, batch_id, content_type, encrypt):
    encrypt_flag = "true" if encrypt else "false"
    tag_uid = create_tag(base_url)
    if not tag_uid:
        print("Failed to create tag. Upload cannot proceed.")
        return

    headers = {
        "Swarm-Postage-Batch-Id": batch_id,
        "Content-Type": content_type,
        "Swarm-Encrypt": encrypt_flag
    }

    try:
        with open(file_path, 'rb') as file:
            response = requests.post(f'{base_url}/bzz?tag={tag_uid}', headers=headers, data=file)
            if response.status_code == 201:
                while True:
                    percent = get_tag_progress(base_url, tag_uid)
                    if percent is not None:
                        print(f"Uploading... [{percent}%]", end='\r')
                        if percent >= 100:
                            break
                    time.sleep(1)
                swarm_hash = response.json().get('reference')
                print(f"\n✅ File successfully uploaded. Swarm Hash: {swarm_hash}")
            else:
                print(f"Failed to upload file. Status code: {response.status_code}, Message: {response.text}")
    except requests.RequestException as e:
        print(f"Error uploading file: {e}")

# Entry point of the program
def main():
    base_url = BEE_API_URL
    if not is_connected_to_bee():
        print("Error: Could not connect to Bee node. Exiting.")
        return

    wallet_balance = get_wallet_balance(base_url) or Decimal(0.0)
    print(f"\nYour xBZZ Balance: {wallet_balance:.6f} xBZZ")

    existing_stamps = get_existing_stamps(base_url)
    if existing_stamps:
        print("\nExisting Stamps:")
        for stamp in existing_stamps:
            ttl_days = stamp.get('batchTTL', 0) / (24 * 3600)
            print(f"Stamp ID: {stamp['batchID']} - Usable: {stamp['usable']} - Label: {stamp.get('label', 'N/A')} - TTL: {ttl_days:.2f} days")

        use_existing = input("Do you want to use an existing stamp? (yes/no): ").strip().lower()
        if use_existing == 'yes':
            return

    file_path = input("Enter the path to the file you want to upload: ").strip()
    file_size = os.path.getsize(file_path)
    depth = calculate_required_depth(file_size)
    price_per_block = get_price_per_block()
    amount, total_plur, total_xbzz = calculate_required_plur(depth, price_per_block)

    if wallet_balance < total_xbzz:
        print("\n❌ Insufficient funds. Your wallet does not have enough xBZZ to cover this upload.")
        return

    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    mutable = input("Should the file be mutable? (yes/no): ").strip().lower() == 'yes'
    label = input("Enter a label for the new stamp: ")
    batch_id = purchase_postage_stamp(base_url, amount, depth, label, mutable)
    if not batch_id:
        return

    encrypt = input("Should the file be encrypted? (yes/no): ").strip().lower() == 'yes'
    wait_for_stamp_usable(base_url, batch_id)
    print("\nUploading file...")
    upload_file(base_url, file_path, batch_id, content_type, encrypt)

if __name__ == "__main__":
    main()
