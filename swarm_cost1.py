import requests
import json
import os
import math
import mimetypes
from web3 import Web3
from decimal import Decimal, getcontext

# Set higher precision for decimal calculations
getcontext().prec = 20

# Connect to Ethereum Bee Node
BEE_API_URL = "http://nethermind-xdai.dappnode:8545"
web3 = Web3(Web3.HTTPProvider(BEE_API_URL))

POSTAGE_CONTRACT_ADDRESS = "0x45a1502382541Cd610CC9068e88727426b696293"
POSTAGE_CONTRACT_ABI = [
    {"inputs": [], "name": "lastPrice", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
]

PLUR_PER_xBZZ = Decimal(10**16)  # Conversion factor
CHUNK_SIZE_BYTES = Decimal(4096)  # Chunk size in Bytes
BLOCKS_PER_YEAR = Decimal(6_307_200)  # Assuming 5s per block, 1 year

def is_connected_to_dappnode():
    url = 'http://bee.swarm.public.dappnode:1633/health'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Connected to DAppNode Bee node.")
            return True
        else:
            print("Failed to connect to Bee node. Status code:", response.status_code)
            return False
    except requests.ConnectionError:
        print("Failed to connect to Bee node. Connection error.")
        return False

def get_existing_stamps(base_url):
    try:
        response = requests.get(f'{base_url}/stamps')
        if response.status_code == 200:
            return response.json().get('stamps', [])
        else:
            print("Failed to fetch existing stamps. Status code:", response.status_code)
            return []
    except requests.RequestException:
        print("Error fetching existing stamps.")
        return []

def get_price_per_block():
    try:
        contract = web3.eth.contract(address=POSTAGE_CONTRACT_ADDRESS, abi=POSTAGE_CONTRACT_ABI)
        return Decimal(contract.functions.lastPrice().call())
    except Exception as e:
        print(f"Error fetching price per block from contract: {e}")
        return None

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

def calculate_required_depth(file_size):
    for depth in range(17, 32):
        max_volume_bytes = (Decimal(2) ** Decimal(depth)) * CHUNK_SIZE_BYTES
        if file_size <= max_volume_bytes:
            return depth
    return 31  # Default to the highest depth

def calculate_required_plur(depth, price_per_block):
    depth = Decimal(depth)
    max_volume_bytes = (Decimal(2) ** depth) * CHUNK_SIZE_BYTES
    max_volume_mb = max_volume_bytes / (Decimal(1024) * Decimal(1024))
    num_chunks = max_volume_bytes / CHUNK_SIZE_BYTES
    required_plur = price_per_block * BLOCKS_PER_YEAR  # PLUR required per year per chunk
    total_plur = required_plur * num_chunks  # Total required PLUR
    total_xbzz = total_plur / PLUR_PER_xBZZ

    print(f"\nDepth: {depth}")
    print(f"Max volume for depth: {max_volume_mb:.6f} MB")
    print(f"Chunk size: {CHUNK_SIZE_BYTES} Bytes")
    print(f"Number of chunks: {int(num_chunks)}")
    print(f"Price per block in PLUR: {price_per_block}")
    print(f"Total PLUR required: {total_plur:.6f}")
    print(f"Total xBZZ required: {total_xbzz:.6f}")
    
    return total_plur

def purchase_stamp(base_url, amount, depth, immutable, label):
    headers = {"immutable": "true" if immutable else "false"}
    url = f"{base_url}/stamps/{amount}/{depth}"
    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 201:
            batch_id = response.json().get("batchID")
            print(f"Stamp successfully purchased. Batch ID: {batch_id}")
            return batch_id
        else:
            print(f"Failed to purchase stamp. Status code: {response.status_code}, Message: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Error purchasing stamp: {e}")
        return None

def main():
    base_url = 'http://bee.swarm.public.dappnode:1633'
    if not is_connected_to_dappnode():
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
    if not os.path.exists(file_path):
        print("Invalid file path. Exiting.")
        return
    
    file_size = os.path.getsize(file_path)
    depth = calculate_required_depth(file_size)
    price_per_block = get_price_per_block()
    required_plur = calculate_required_plur(depth, price_per_block)
    
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    print(f"Detected Content-Type: {content_type}")
    
    should_be_mutable = input("Should the file be mutable? (yes/no): ").strip().lower() == 'yes'
    label = input("Enter a label for the new stamp: ").strip()
    batch_id = purchase_stamp(base_url, required_plur, depth, not should_be_mutable, label)
    if not batch_id:
        print("Error purchasing stamp. Exiting.")
        return

if __name__ == "__main__":
    main()
