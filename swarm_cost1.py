import requests
import json
import os
import mimetypes
import time
from web3 import Web3
from decimal import Decimal, getcontext

# --- Precision and Constants Setup ---
getcontext().prec = 20  # Precision for decimal calculations

# Set up connection details
WEB3_RPC_URL = "https://rpc.gnosischain.com"
BEE_API_URL = "http://bee.swarm.public.dappnode:1633"
web3 = Web3(Web3.HTTPProvider(WEB3_RPC_URL))

# Smart contract address and ABI for xBZZ price lookups
POSTAGE_CONTRACT_ADDRESS = "0x45a1502382541Cd610CC9068e88727426b696293"
POSTAGE_CONTRACT_ABI = [
    {"inputs": [], "name": "lastPrice", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
]

# Constants for conversion and calculations
PLUR_PER_xBZZ = Decimal(10**16)
CHUNK_SIZE_BYTES = Decimal(4096)
BLOCK_TIME_SECONDS = Decimal(5)
STORAGE_TIME_SECONDS = Decimal(365 * 24 * 60 * 60)  # 1 year

# Local storage for saved feed metadata
LOCAL_FEED_FILE = "local_feeds.json"

# --- Bee Node and Web3 Utilities ---

# Check if Bee node is healthy and available
def is_connected_to_bee():
    try:
        return requests.get(f'{BEE_API_URL}/health').status_code == 200
    except:
        return False

# Get the current storage price per block from the Swarm oracle contract
def get_price_per_block():
    try:
        contract = web3.eth.contract(address=POSTAGE_CONTRACT_ADDRESS, abi=POSTAGE_CONTRACT_ABI)
        return Decimal(contract.functions.lastPrice().call())
    except:
        return None

# Retrieve current wallet balance (converted to xBZZ)
def get_wallet_balance():
    try:
        res = requests.get(f"{BEE_API_URL}/wallet")
        if res.status_code == 200:
            balance_plur = Decimal(res.json().get('bzzBalance', 0))
            return balance_plur / PLUR_PER_xBZZ
    except:
        return Decimal(0)

# --- Swarm Batch Logic ---

# Find the required depth for a file size
def calculate_required_depth(file_size):
    for depth in range(17, 32):
        if file_size <= (2 ** depth) * CHUNK_SIZE_BYTES:
            return depth
    return 31

# Calculate cost (in PLUR and xBZZ) for a given depth
def calculate_required_plur(depth, price_per_block):
    amount_per_chunk = (price_per_block / BLOCK_TIME_SECONDS) * STORAGE_TIME_SECONDS
    total_chunks = Decimal(2) ** Decimal(depth)
    total_plur = total_chunks * amount_per_chunk
    return amount_per_chunk, total_plur, total_plur / PLUR_PER_xBZZ

# Request a tag from Bee to track file upload progress
def create_tag():
    try:
        res = requests.post(f"{BEE_API_URL}/tags")
        if res.status_code == 201:
            return res.json().get("uid")
    except:
        return None

# Check percentage of completed file upload using tag
def get_tag_progress(tag_uid):
    try:
        res = requests.get(f"{BEE_API_URL}/tags/{tag_uid}")
        if res.status_code == 200:
            tag = res.json()
            total = tag.get("total", 1)
            processed = tag.get("processed", 0)
            return int((processed / total) * 100) if total > 0 else 0
    except:
        return None

# Wait until a batch becomes usable (after ~10 blocks)
def wait_for_stamp_usable(batch_id, blocks=10):
    time.sleep(int(blocks) * int(BLOCK_TIME_SECONDS))
    while True:
        try:
            res = requests.get(f"{BEE_API_URL}/stamps/{batch_id}")
            if res.status_code == 200 and res.json().get("usable", False):
                break
        except:
            pass
        time.sleep(5)

# Upload the file to Swarm using a batch
def upload_file(file_path, batch_id, content_type, encrypt, topic_name=None):
    tag_uid = create_tag()
    if not tag_uid:
        print("❌ Failed to create tag.")
        return

    headers = {
        "Swarm-Postage-Batch-Id": batch_id,
        "Content-Type": content_type,
        "Swarm-Encrypt": "true" if encrypt else "false"
    }

    if topic_name:
        headers["Swarm-Feed-Name"] = topic_name
        headers["Swarm-Feed-Type"] = "sequence"

    with open(file_path, 'rb') as f:
        res = requests.post(f"{BEE_API_URL}/bzz?tag={tag_uid}", headers=headers, data=f)
        if res.status_code == 201:
            while True:
                percent = get_tag_progress(tag_uid)
                if percent is not None:
                    print(f"Uploading... [{percent}%]", end='\r')
                    if percent >= 100:
                        break
                time.sleep(1)
            swarm_hash = res.json().get("reference")
            print(f"\n✅ File uploaded. Swarm Hash: {swarm_hash}")
            if topic_name:
                if input("Would you like to save this file and hash locally? (yes/no): ").strip().lower() == "yes":
                    save_local_feed(batch_id, topic_name, swarm_hash)
                else:
                    print("⚠️ Be sure to note your topic name and Swarm hash.")
            return swarm_hash
        else:
            print(f"❌ Upload failed: {res.status_code} {res.text}")
            return None

# Fetch existing batch stamps from Bee node
def get_existing_stamps():
    try:
        res = requests.get(f"{BEE_API_URL}/stamps")
        if res.status_code == 200:
            return res.json().get("stamps", [])
    except:
        return []
    return []

# Dilute a batch to increase its depth (and capacity)
def dilute_batch(batch_id, new_depth):
    try:
        return requests.patch(f"{BEE_API_URL}/stamps/topup/{batch_id}/{new_depth}").status_code == 200
    except:
        return False

# Purchase a new stamp/batch for uploading data
def purchase_postage_stamp(amount, depth, label, mutable):
    try:
        headers = {"immutable": "false" if mutable else "true", "label": label}
        res = requests.post(f"{BEE_API_URL}/stamps/{int(amount)}/{depth}", headers=headers)
        if res.status_code == 201:
            return res.json().get('batchID')
    except:
        return None

# --- Local JSON Feed Tracking ---

# Load local file -> topic mappings
def load_local_feeds():
    if os.path.exists(LOCAL_FEED_FILE):
        with open(LOCAL_FEED_FILE, "r") as f:
            return json.load(f)
    return {}

# Save a feed to local JSON after upload
def save_local_feed(batch_id, topic_name, swarm_hash):
    feeds = load_local_feeds()
    if batch_id not in feeds:
        feeds[batch_id] = {}
    feeds[batch_id][topic_name] = swarm_hash
    with open(LOCAL_FEED_FILE, "w") as f:
        json.dump(feeds, f, indent=2)
    print(f"📝 Saved locally: {topic_name} -> {swarm_hash}")

# --- Main Application Logic ---

def main():
    if not is_connected_to_bee():
        print("Error: Could not connect to Bee node.")
        return

    print("Connected to Bee node.\n")
    wallet_balance = get_wallet_balance()
    print(f"Your xBZZ Balance: {wallet_balance:.6f} xBZZ")

    local_feeds = load_local_feeds()
    stamps = get_existing_stamps()

    if stamps:
        print("\nAvailable Batches:")
        usable_batches = []
        for i, stamp in enumerate(stamps):
            if stamp.get("usable", False):
                depth = int(stamp["depth"])
                total_mb = (2 ** depth) * CHUNK_SIZE_BYTES / (1024 ** 2)
                utilization = Decimal(stamp.get("utilization", 0))
                remaining_mb = total_mb * (1 - utilization)
                label = stamp.get("label", "N/A")
                ttl_days = round(stamp['batchTTL'] / 86400, 2)
                print(f"{i+1}) Label: {label} | TTL: {ttl_days} days | Remaining: {round(remaining_mb,2)} MB")
                usable_batches.append((stamp, remaining_mb))

        if usable_batches and input("\nUse an existing batch? (yes/no): ").strip().lower() == 'yes':
            idx = 0
            if len(usable_batches) > 1:
                idx = int(input("Select batch number: ")) - 1
            stamp, remaining_mb = usable_batches[idx]
            batch_id = stamp['batchID']
            depth = int(stamp['depth'])
            mutable = not stamp.get("immutable", True)

            # Show local saved topics for that batch
            if batch_id in local_feeds:
                print("\nSaved Files:")
                for name in local_feeds[batch_id]:
                    print(f"- {name}")

            use_feed = input("Do you want to update an existing file? (yes/no): ").strip().lower() == 'yes'
            if use_feed:
                topic_name = input("Enter the existing file name to update: ").strip()
            else:
                topic_name = input("Enter a name for this file (topic): ").strip()

            file_path = input("Enter file path to upload: ").strip()
            file_size = os.path.getsize(file_path)
            file_mb = Decimal(file_size) / (1024 ** 2)
            content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

            # Handle dilution if capacity is too low
            if file_mb > remaining_mb:
                new_depth = depth + 1
                _, add_plur, add_xbzz = calculate_required_plur(new_depth, get_price_per_block())
                print(f"\n⚠️ Not enough space. Need: {round(file_mb,2)} MB | Remaining: {round(remaining_mb,2)} MB")
                print(f"Cost to increase capacity: {add_xbzz:.6f} xBZZ")
                if wallet_balance < add_xbzz:
                    print("❌ Not enough xBZZ to increase storage.")
                    return
                if input("Increase storage? (yes/no): ").strip().lower() != 'yes':
                    return
                if not dilute_batch(batch_id, new_depth):
                    print("❌ Failed to increase storage.")
                    return

            encrypt = input("Should the file be encrypted? (yes/no): ").strip().lower() == 'yes'
            immutable = not mutable or input("Should the file be immutable? (yes/no): ").strip().lower() != 'no'
            wait_for_stamp_usable(batch_id)
            upload_file(file_path, batch_id, content_type, encrypt, topic_name)
            return

    # --- New Batch Upload Path ---

    file_path = input("Enter path to file you want to upload: ").strip()
    file_size = os.path.getsize(file_path)
    file_mb = Decimal(file_size) / (1024 ** 2)
    depth = calculate_required_depth(file_size)
    price = get_price_per_block()
    _, plur_cost, xbzz_cost = calculate_required_plur(depth, price)

    print(f"\nFile size: {round(file_mb,2)} MB")
    print(f"Estimated cost (1 year storage): {xbzz_cost:.6f} xBZZ")

    if wallet_balance < xbzz_cost:
        print("❌ Not enough xBZZ to purchase new batch.")
        return

    mutable = input("Should this batch allow file updates? (yes/no): ").strip().lower() == 'yes'
    label = input("Enter label for new batch: ")
    batch_id = purchase_postage_stamp(plur_cost, depth, label, mutable)
    if not batch_id:
        print("❌ Failed to create new batch.")
        return

    topic_name = input("Enter a name for this file (topic): ").strip()
    encrypt = input("Should the file be encrypted? (yes/no): ").strip().lower() == 'yes'
    immutable = not mutable or input("Should the file be immutable? (yes/no): ").strip().lower() != 'no'
    wait_for_stamp_usable(batch_id)
    upload_file(file_path, batch_id, mimetypes.guess_type(file_path)[0] or "application/octet-stream", encrypt, topic_name)

if __name__ == "__main__":
    main()
