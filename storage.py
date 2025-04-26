# storage.py

import os
import time
import mimetypes
import requests
from decimal import Decimal
from bee_api import get_price_per_block, get_tag_progress, create_tag, wait_for_stamp_usable
from config import BEE_API_URL, CHUNK_SIZE_BYTES, BLOCK_TIME_SECONDS, STORAGE_TIME_SECONDS, DILUTION_TOPUP_TTL, PLUR_PER_xBZZ
from utils import play_notification_sound
import urllib.parse

# Utilisation rates from Swarm documentation for effective capacity by batch depth
EFFECTIVE_UTILISATION = {
    17: 0.32, 18: 0.35, 19: 0.39, 20: 0.42, 21: 0.46, 22: 0.5,
    23: 0.53, 24: 0.57, 25: 0.6, 26: 0.64, 27: 0.67, 28: 0.71,
    29: 0.74, 30: 0.78, 31: 0.81
}

BUCKET_DEPTH = 16  # Always 16 in Swarm


def get_effective_capacity_mb(batch_depth):
    theoretical_chunks_per_bucket = Decimal(2) ** Decimal(batch_depth - BUCKET_DEPTH)
    total_buckets = Decimal(2) ** Decimal(BUCKET_DEPTH)
    total_chunks = theoretical_chunks_per_bucket * total_buckets
    utilisation = Decimal(EFFECTIVE_UTILISATION.get(batch_depth, 0.5))
    effective_chunks = total_chunks * utilisation
    return (effective_chunks * CHUNK_SIZE_BYTES) / (1024 ** 2)  # Return in MB


def format_storage_size(mb_value):
    if mb_value >= 1024 * 1024:
        return f"{mb_value / (1024 * 1024):.2f} TB"
    elif mb_value >= 1024:
        return f"{mb_value / 1024:.2f} GB"
    else:
        return f"{mb_value:.2f} MB"


def calculate_required_depth(file_size):
    for depth in range(17, 32):
        if file_size <= get_effective_capacity_mb(depth) * 1024 ** 2:
            return depth
    return 31


def calculate_required_plur_for_chunks(num_chunks, price_per_block, ttl_seconds):
    amount_per_chunk = (price_per_block / BLOCK_TIME_SECONDS) * ttl_seconds
    total_plur = Decimal(num_chunks) * amount_per_chunk
    return amount_per_chunk, total_plur, total_plur / PLUR_PER_xBZZ


def calculate_required_plur(depth, price_per_block):
    total_chunks = Decimal(2) ** Decimal(depth)
    return calculate_required_plur_for_chunks(total_chunks, price_per_block, STORAGE_TIME_SECONDS)


def dilute_batch(batch_id, bucket_depth, new_depth):
    try:
        batch_id = batch_id.replace(" ", "")

        response = requests.patch(f"{BEE_API_URL}/stamps/dilute/{batch_id}/{new_depth}")
        print(f"🛠️ Dilution response: {response.status_code} - {response.text}")
        if response.status_code != 202:
            return False

        try:
            parsed = response.json()
            batch_id = parsed.get("batchID", batch_id).replace(" ", "")
        except Exception as e:
            print(f"⚠️ Could not re-parse batch ID from response: {e}")

        start_time = time.time()
        print(f"🔍 Waiting for depth update... View txn: https://gnosisscan.io/tx/{parsed.get('txHash', '')}")
        print("⏳ Waiting for diluted batch to reflect updated depth...")

        while time.time() - start_time < 3600:
            time.sleep(15)
            stamp_check = requests.get(f"{BEE_API_URL}/stamps/{batch_id}")
            if stamp_check.status_code != 200:
                print("❌ Failed to verify updated stamp.")
                return False

            data = stamp_check.json()
            actual_depth = int(data.get("depth", 0))
            if actual_depth >= new_depth:
                break
            print(f"...still waiting... current depth: {actual_depth}")
        else:
            print("⚠️ Dilution did not increase depth after timeout.")
            return False

        new_capacity_mb = get_effective_capacity_mb(new_depth)
        updated_ttl = Decimal(data.get("batchTTL", 0)) / 86400

        print(f"📏 New effective capacity: {format_storage_size(new_capacity_mb)}")
        print(f"📆 TTL remaining after dilution: {updated_ttl:.2f} days")

        choice = input("Would you like to top up TTL to match original amount? (yes/no): ").strip().lower()
        if choice == "yes":
            topup_response = requests.patch(f"{BEE_API_URL}/stamps/topup/{batch_id}")
            print(f"🛠️ TTL Top-Up response: {topup_response.status_code} - {topup_response.text}")
            if topup_response.status_code == 200:
                play_notification_sound()
        return True

    except Exception as e:
        print(f"❌ Error during batch dilution or TTL check: {e}")
        return False


def purchase_postage_stamp(amount, depth, label, mutable, quoted_xbzz=None):
    try:
        clean_label = label.encode("ascii", "ignore").decode().strip()[:32] or "UnnamedBatch"
        actual_xbzz = Decimal(amount) / PLUR_PER_xBZZ

        if quoted_xbzz and actual_xbzz > Decimal(quoted_xbzz) * 2:
            print("❌ Aborted: Stamp cost exceeds 2x the quoted estimate. Check calculation logic.")
            return None

        encoded_label = urllib.parse.quote(clean_label)
        immutable_flag = "false" if mutable else "true"
        url = f"{BEE_API_URL}/stamps/{int(amount)}/{depth}?label={encoded_label}&immutable={immutable_flag}"

        print(f"📦 Creating batch with label: '{clean_label}'")
        response = requests.post(url)
        print(f"📦 Stamp creation response: {response.status_code} - {response.text}")

        if response.status_code == 201:
            return response.json().get("batchID")
    except Exception as e:
        print(f"❌ Exception during stamp creation: {e}")
    return None


def upload_file(file_path, batch_id, encrypt, topic_name=None):
    tag_uid = create_tag()
    if not tag_uid:
        print("❌ Failed to create tag.")
        return

    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    headers = {
        "Swarm-Postage-Batch-Id": batch_id,
        "Content-Type": content_type,
        "Swarm-Encrypt": "true" if encrypt else "false"
    }

    if topic_name:
        headers["Swarm-Feed-Name"] = topic_name
        headers["Swarm-Feed-Type"] = "sequence"

    with open(file_path, 'rb') as file:
        response = requests.post(f"{BEE_API_URL}/bzz?tag={tag_uid}", headers=headers, data=file)
        if response.status_code == 201:
            while True:
                percent = get_tag_progress(tag_uid)
                if percent is not None:
                    print(f"Uploading... [{percent}%]", end='\r')
                    if percent >= 100:
                        break
                time.sleep(1)
            swarm_hash = response.json().get("reference")
            print(f"\n✅ File uploaded. Swarm Hash: {swarm_hash}")
            return swarm_hash
        else:
            print(f"❌ Upload failed: {response.status_code} {response.text}")
            return None
