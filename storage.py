# storage.py

import os
import time
import mimetypes
import requests
from decimal import Decimal
from bee_api import get_price_per_block, get_tag_progress, create_tag, wait_for_stamp_usable
from config import BEE_API_URL, CHUNK_SIZE_BYTES, BLOCK_TIME_SECONDS, STORAGE_TIME_SECONDS, PLUR_PER_xBZZ


def calculate_required_depth(file_size):
    """Determine the minimum batch depth required for the given file size."""
    for depth in range(17, 32):
        if file_size <= (2 ** depth) * CHUNK_SIZE_BYTES:
            return depth
    return 31


def calculate_required_plur(depth, price_per_block):
    """Calculate PLUR and xBZZ required to store at the given depth for 1 week (testing)."""
    amount_per_chunk = (price_per_block / BLOCK_TIME_SECONDS) * STORAGE_TIME_SECONDS
    total_chunks = Decimal(2) ** Decimal(depth)
    total_plur = total_chunks * amount_per_chunk
    return amount_per_chunk, total_plur, total_plur / PLUR_PER_xBZZ


def dilute_batch(batch_id, old_depth, new_depth, price_per_block):
    """Dilute the batch and immediately top up to align TTL with quoted price."""
    try:
        response = requests.patch(f"{BEE_API_URL}/stamps/topup/{batch_id}/{new_depth}")
        print(f"🛠️ Dilution response: {response.status_code} - {response.text}")
        if response.status_code != 200:
            return False

        # Calculate how many new chunks were unlocked
        extra_chunks = Decimal(2) ** Decimal(new_depth) - Decimal(2) ** Decimal(old_depth)
        amount_per_chunk = (price_per_block / BLOCK_TIME_SECONDS) * STORAGE_TIME_SECONDS
        topup_plur = extra_chunks * amount_per_chunk

        # Perform top-up to match TTL for new chunks
        topup_response = requests.patch(f"{BEE_API_URL}/stamps/topup/{batch_id}")
        print(f"🛠️ TTL Top-Up response: {topup_response.status_code} - {topup_response.text}")

        return topup_response.status_code == 200

    except Exception as e:
        print(f"❌ Error during batch dilution or top-up: {e}")
        return False


def purchase_postage_stamp(amount, depth, label, mutable):
    """Purchase a new batch with the desired depth and TTL settings."""
    try:
        headers = {"immutable": "false" if mutable else "true", "label": label}
        response = requests.post(f"{BEE_API_URL}/stamps/{int(amount)}/{depth}", headers=headers)
        if response.status_code == 201:
            return response.json().get("batchID")
    except:
        return None


def upload_file(file_path, batch_id, encrypt, topic_name=None):
    """Upload the file to Swarm, optionally via a feed."""
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
