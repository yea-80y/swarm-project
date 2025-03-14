import requests
import json
import os
import math
from web3 import Web3

# Connect to Ethereum Bee Node
BEE_API_URL = "http://nethermind-xdai.dappnode:8545"
web3 = Web3(Web3.HTTPProvider(BEE_API_URL))

POSTAGE_CONTRACT_ADDRESS = "0x45a1502382541Cd610CC9068e88727426b696293"
POSTAGE_CONTRACT_ABI = [
    {"inputs": [], "name": "lastPrice", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
]

PLUR_PER_xBZZ = 10**16  # Conversion factor
CHUNK_SIZE_KB = 4.096  # Chunk size in KB
BLOCKS_PER_YEAR = 6_307_200  # Assuming 5s per block, 1 year

# Correct max volume per depth based on Swarm Docs
MAX_VOLUMES_MB = {
    17: 536.87, 18: 1073.74, 19: 2147.48, 20: 4294.97,
    21: 8589.93, 22: 17179.87, 23: 34359.74, 24: 68719.48,
    25: 137438.95, 26: 274877.91, 27: 549755.81, 28: 1099511.63,
    29: 2199023.26, 30: 4398046.51, 31: 8796093.02
}

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
    """Fetch the latest price per block from the Postage contract."""
    try:
        contract = web3.eth.contract(address=POSTAGE_CONTRACT_ADDRESS, abi=POSTAGE_CONTRACT_ABI)
        return contract.functions.lastPrice().call()
    except Exception as e:
        print(f"Error fetching price per block from contract: {e}")
        return None

def calculate_required_depth(file_size):
    """Determine the depth required for the file."""
    for depth, max_volume in MAX_VOLUMES_MB.items():
        if file_size <= max_volume * 1024 * 1024:
            return depth
    return max(MAX_VOLUMES_MB.keys())

def calculate_required_plur(depth, price_per_block):
    """Calculate required PLUR and xBZZ cost based on full depth."""
    max_volume = MAX_VOLUMES_MB[depth] * 1024 * 1024  # Convert MB to Bytes
    num_chunks = math.ceil(max_volume / (CHUNK_SIZE_KB * 1024))  # Convert to chunks

    # Adjust calculation to match Swarm pricing structure
    required_plur = price_per_block * num_chunks * BLOCKS_PER_YEAR  # PLUR required for 1 year
    total_xbzz = required_plur / PLUR_PER_xBZZ  # Convert to xBZZ

    print(f"\nDepth: {depth}")
    print(f"Max volume for depth: {MAX_VOLUMES_MB[depth]} MB")
    print(f"Chunk size: {CHUNK_SIZE_KB} KB")
    print(f"Number of chunks: {num_chunks}")
    print(f"Price per block in PLUR: {price_per_block}")
    print(f"Total PLUR required: {required_plur:.2f}")
    print(f"Total xBZZ required: {total_xbzz:.6f}")
    
    return required_plur

def main():
    base_url = 'http://localhost:1633'
    if is_connected_to_dappnode():
        base_url = 'http://bee.swarm.public.dappnode:1633'
    else:
        print("Error: Could not connect to Bee node. Exiting.")
        return

    price_per_block = get_price_per_block()
    if price_per_block is None:
        print("Error: Could not retrieve the price per block. Exiting.")
        return

    existing_stamps = get_existing_stamps(base_url)
    if existing_stamps:
        print("\nExisting Stamps:")
        for stamp in existing_stamps:
            ttl_days = stamp.get('batchTTL', 0) / (24 * 3600)
            print(f"Stamp ID: {stamp['batchID']} - Usable: {stamp['usable']} - Label: {stamp.get('label', 'N/A')} - TTL: {ttl_days:.2f} days")

        use_existing = input("Do you want to use an existing stamp? (yes/no): ").strip().lower()
        if use_existing == 'yes':
            return  # Exit as user selected existing stamp

    buy_new_stamp = input("Do you want to purchase a new stamp? (yes/no): ").strip().lower()
    if buy_new_stamp != 'yes':
        print("Exiting.")
        return

    file_path = input("Enter the path to the file you want to upload: ").strip()
    
    if not os.path.exists(file_path):
        print("Invalid file path. Exiting.")
        return
    
    file_size = os.path.getsize(file_path)
    depth = calculate_required_depth(file_size)
    required_plur = calculate_required_plur(depth, price_per_block)
    
    print(f"\nCalculated required depth for your file: {depth}")
    print(f"Calculated required PLUR amount: {required_plur:.2f}")
    
    confirm = input("Do you want to proceed with purchasing this stamp? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Stamp purchase cancelled.")
        return
    
    label = input("Enter a label for the new stamp: ").strip()
    try:
        response = requests.post(f'{base_url}/stamps', json={"amount": str(required_plur), "depth": depth, "label": label})
        if response.status_code == 201:
            stamp_id = response.json().get('batchID')
            print(f"Stamp successfully purchased. Stamp ID: {stamp_id}")
        else:
            print(f"Failed to purchase stamp. Status code: {response.status_code}, Message: {response.text}")
    except requests.RequestException as e:
        print(f"Error purchasing stamp: {e}")
    
    print("Process completed successfully.")

if __name__ == "__main__":
    main()
