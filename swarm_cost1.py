import requests
import json
import os
import mimetypes
import time
from web3 import Web3
from decimal import Decimal, getcontext

# --- Configuration and Constants ---

# Set higher precision for xBZZ math
getcontext().prec = 20

# Bee and Gnosis Chain endpoints
WEB3_RPC_URL = "https://rpc.gnosischain.com"
BEE_API_URL = "http://localhost:1633"

# Connect to web3 for pricing info
web3 = Web3(Web3.HTTPProvider(WEB3_RPC_URL))

# Postage stamp contract info
POSTAGE_CONTRACT_ADDRESS = "0x45a1502382541Cd610CC9068e88727426b696293"
POSTAGE_CONTRACT_ABI = [
    {"inputs": [], "name": "lastPrice", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
]

# Conversion constants and Swarm assumptions
PLUR_PER_xBZZ = Decimal(10**16)
CHUNK_SIZE_BYTES = Decimal(4096)
BLOCK_TIME_SECONDS = Decimal(5)
STORAGE_TIME_SECONDS = Decimal(365 * 24 * 60 * 60)  # 1 year

# --- Helper Functions ---

# Ping Bee node to ensure it's healthy
def is_connected_to_bee():
    try:
        response = requests.get(f'{BEE_API_URL}/health')
        return response.status_code == 200
    except requests.ConnectionError:
        return False

# Fetch current on-chain storage price
def get_price_per_block():
    try:
        contract = web3.eth.contract(address=POSTAGE_CONTRACT_ADDRESS, abi=POSTAGE_CONTRACT_ABI)
        return Decimal(contract.functions.lastPrice().call())
    except:
        return None

# Get xBZZ wallet balance from Bee node
def get_wallet_balance(base_url):
    try:
        response = requests.get(f'{base_url}/wallet')
        if response.status_code == 200:
            balance_plur = Decimal(response.json().get('bzzBalance', 0))
            return balance_plur / PLUR_PER_xBZZ
    except:
        pass
    return Decimal(0)

# Determine required depth to fit a file of given size
def calculate_required_depth(file_size):
    for depth in range(17, 32):
        if file_size <= (2 ** depth) * CHUNK_SIZE_BYTES:
            return depth
    return 31

# Calculate cost to store at specific depth
def calculate_required_plur(depth, price_per_block):
    amount_per_chunk = (price_per_block / BLOCK_TIME_SECONDS) * STORAGE_TIME_SECONDS
    total_chunks = Decimal(2) ** Decimal(depth)
    total_plur = total_chunks * amount_per_chunk
    return amount_per_chunk, total_plur, total_plur / PLUR_PER_xBZZ

# Fetch existing batches from Bee node
def get_existing_stamps(base_url):
    try:
        response = requests.get(f'{base_url}/stamps')
        if response.status_code == 200:
            return response.json().get('stamps', [])
    except:
        pass
    return []

# Create tag for upload progress tracking
def create_tag(base_url):
    try:
        response = requests.post(f"{base_url}/tags")
        if response.status_code == 201:
            return response.json().get("uid")
    except:
        pass
    return None

# Get upload progress via tag
def get_tag_progress(base_url, tag_uid):
    try:
        response = requests.get(f"{base_url}/tags/{tag_uid}")
        if response.status_code == 200:
            tag = response.json()
            total = tag.get("total", 1)
            processed = tag.get("processed", 0)
            return int((processed / total) * 100) if total > 0 else 0
    except:
        pass
    return None

# Wait for batch to become usable (10+ blocks confirmed)
def wait_for_stamp_usable(base_url, batch_id, min_blocks=10):
    print("\nUpload pending... This usually takes less than a minute.")
    time.sleep(int(min_blocks) * int(BLOCK_TIME_SECONDS))
    while True:
        try:
            response = requests.get(f"{base_url}/stamps/{batch_id}")
            if response.status_code == 200:
                if response.json().get("usable", False):
                    break
        except:
            pass
        time.sleep(5)

# Buy a new batch of postage stamps
def purchase_postage_stamp(base_url, amount, depth, label, mutable):
    try:
        response = requests.post(
            f'{base_url}/stamps/{int(amount)}/{depth}',
            headers={"immutable": "false" if mutable else "true", "label": label}
        )
        if response.status_code == 201:
            return response.json().get('batchID')
    except:
        pass
    return None

# Increase storage capacity (depth) of existing batch
def dilute_batch(base_url, batch_id, new_depth):
    try:
        response = requests.patch(f'{base_url}/stamps/topup/{batch_id}/{new_depth}')
        return response.status_code == 200
    except:
        return False

# Perform file upload with tracking
def upload_file(base_url, file_path, batch_id, content_type, encrypt):
    tag_uid = create_tag(base_url)
    if not tag_uid:
        print("❌ Failed to create tag. Upload aborted.")
        return

    headers = {
        "Swarm-Postage-Batch-Id": batch_id,
        "Content-Type": content_type,
        "Swarm-Encrypt": "true" if encrypt else "false"
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
                print(f"\n✅ File uploaded. Swarm Hash: {response.json().get('reference')}")
            else:
                print(f"❌ Upload failed: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ Upload error: {e}")

# --- Main Program Flow ---

def main():
    if not is_connected_to_bee():
        print("Error: Could not connect to Bee node.")
        return

    print("Connected to Bee node.\n")
    base_url = BEE_API_URL
    wallet_balance = get_wallet_balance(base_url)
    print(f"Your xBZZ Balance: {wallet_balance:.6f} xBZZ")

    # Step 1: Load file and calculate upload cost
    file_path = input("\nEnter the path to the file you want to upload: ").strip()
    file_size = os.path.getsize(file_path)
    file_mb = Decimal(file_size) / (1024 ** 2)
    print(f"File size: {round(file_mb, 2)} MB")

    price_per_block = get_price_per_block()
    depth = calculate_required_depth(file_size)
    _, total_plur, total_xbzz = calculate_required_plur(depth, price_per_block)
    print(f"Estimated storage cost for 1 year: {total_xbzz:.6f} xBZZ")

    # Step 2: Show existing usable batches (if any)
    existing_stamps = get_existing_stamps(base_url)
    if existing_stamps:
        print("\nAvailable Batches:")
        usable_batches = []
        for i, stamp in enumerate(existing_stamps):
            if stamp.get("usable", False):
                batch_depth = int(stamp["depth"])
                utilization = Decimal(stamp.get("utilization", 0))
                total_mb = ((2 ** batch_depth) * CHUNK_SIZE_BYTES) / (1024 ** 2)
                used_mb = total_mb * utilization
                remaining_mb = total_mb - used_mb
                label = stamp.get("label", "N/A")
                print(f"{i+1}) Label: {label} | TTL: {round(stamp['batchTTL']/86400,2)} days | Remaining: {round(remaining_mb, 2)} MB")
                usable_batches.append((stamp, remaining_mb))

        # Step 3: Ask user if they want to use an existing batch
        if usable_batches:
            use_existing = input("\nUse an existing batch? (yes/no): ").strip().lower()
            if use_existing == 'yes':
                selection = 0
                if len(usable_batches) > 1:
                    selection = int(input("Select batch number: ")) - 1

                selected_stamp, remaining_mb = usable_batches[selection]
                selected_batch_id = selected_stamp['batchID']
                batch_depth = int(selected_stamp['depth'])

                if file_mb > remaining_mb:
                    print(f"\n⚠️ Not enough storage left. Required: {round(file_mb, 2)} MB | Remaining: {round(remaining_mb, 2)} MB")
                    new_depth = batch_depth + 1
                    _, add_plur, add_xbzz = calculate_required_plur(new_depth, price_per_block)
                    print(f"💡 To upload this file, your batch will need more storage.")
                    print(f"Cost to increase capacity: {add_xbzz:.4f} xBZZ")

                    if wallet_balance < add_xbzz:
                        print("❌ Not enough funds to increase batch capacity.")
                        return

                    proceed = input("Do you want to increase storage? (yes/no): ").strip().lower()
                    if proceed != 'yes':
                        return

                    if not dilute_batch(base_url, selected_batch_id, new_depth):
                        print("❌ Failed to increase storage.")
                        return

                # Ask about encryption + immutability (if batch allows)
                encrypt = input("Should the file be encrypted? (yes/no): ").strip().lower() == 'yes'
                if selected_stamp.get("immutable") is False:
                    immutable = input("Should the file be immutable? (yes/no): ").strip().lower() != 'no'
                else:
                    immutable = True  # Enforced by batch config

                wait_for_stamp_usable(base_url, selected_batch_id)
                upload_file(base_url, file_path, selected_batch_id, content_type=mimetypes.guess_type(file_path)[0] or "application/octet-stream", encrypt=encrypt)
                return

    # Step 4: Fallback to creating a new batch
    if wallet_balance < total_xbzz:
        print("❌ Insufficient funds to create new batch.")
        return

    mutable = input("Should this batch allow future updates? (yes/no): ").strip().lower() == 'yes'
    label = input("Enter a label for the new batch: ")
    batch_id = purchase_postage_stamp(base_url, amount=total_plur, depth=depth, label=label, mutable=mutable)
    if not batch_id:
        print("❌ Failed to create new batch.")
        return

    encrypt = input("Should the file be encrypted? (yes/no): ").strip().lower() == 'yes'
    if mutable:
        immutable = input("Should the file be immutable? (yes/no): ").strip().lower() != 'no'
    else:
        immutable = True

    wait_for_stamp_usable(base_url, batch_id)
    upload_file(base_url, file_path, batch_id, content_type=mimetypes.guess_type(file_path)[0] or "application/octet-stream", encrypt=encrypt)

if __name__ == "__main__":
    main()
