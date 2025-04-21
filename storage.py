# storage.py

import os
import time
import mimetypes
import requests
from decimal import Decimal
from bee_api import get_price_per_block, get_tag_progress, create_tag, wait_for_stamp_usable
from config import BEE_API_URL, CHUNK_SIZE_BYTES, BLOCK_TIME_SECONDS, STORAGE_TIME_SECONDS, DILUTION_TOPUP_TTL, PLUR_PER_xBZZ
from utils import play_notification_sound


def calculate_required_depth(file_size):
    """Determine the minimum batch depth required for the given file size."""
    for depth in range(17, 32):
        if file_size <= (2 ** depth) * CHUNK_SIZE_BYTES:
            return depth
    return 31


def calculate_required_plur_for_chunks(num_chunks, price_per_block, ttl_seconds):
    """Calculate PLUR and xBZZ required to store a number of chunks for a given TTL."""
    amount_per_chunk = (price_per_block / BLOCK_TIME_SECONDS) * ttl_seconds
    total_plur = Decimal(num_chunks) * amount_per_chunk
    return amount_per_chunk, total_plur, total_plur / PLUR_PER_xBZZ


def calculate_required_plur(depth, price_per_block):
    """Calculate PLUR and xBZZ required to store at the given depth for the current STORAGE_TIME_SECONDS."""
    total_chunks = Decimal(2) ** Decimal(depth)
    return calculate_required_plur_for_chunks(total_chunks, price_per_block, STORAGE_TIME_SECONDS)


def dilute_batch(batch_id, old_depth, new_depth, price_per_block):
    """Dilute the batch and top up to match TTL only if depth was successfully increased."""
    try:
        batch_id = batch_id.replace(" ", "")

        response = requests.patch(f"{BEE_API_URL}/stamps/topup/{batch_id}/{new_depth}")
        print(f"🛠️ Dilution response: {response.status_code} - {response.text}")
        if response.status_code != 202:
            return False

        try:
            parsed = response.json()
            batch_id = parsed.get("batchID", batch_id).replace(" ", "")
        except Exception as e:
            print(f"⚠️ Could not re-parse batch ID from response: {e}")

        for attempt in range(5):
            time.sleep(3)
            stamp_check = requests.get(f"{BEE_API_URL}/stamps/{batch_id}")
            if stamp_check.status_code != 200:
                print("❌ Failed to verify updated stamp.")
                return False

            data = stamp_check.json()
            actual_depth = int(data.get("bucketDepth", 0))
            if actual_depth >= new_depth:
                break
            print(f"⏳ Attempt {attempt + 1}: Depth still at {actual_depth}. Waiting...")
        else:
            print("⚠️ Dilution did not increase depth after multiple checks. Skipping TTL top-up.")
            return False

        extra_chunks = Decimal(2) ** Decimal(new_depth) - Decimal(2) ** Decimal(old_depth)
        amount_per_chunk, topup_plur, topup_xbzz = calculate_required_plur_for_chunks(extra_chunks, price_per_block, DILUTION_TOPUP_TTL)

        print(f"📏 New storage unlocked: {extra_chunks} chunks")
        print(f"💰 Top-up for 1 week TTL: {topup_xbzz:.6f} xBZZ")

        topup_response = requests.patch(f"{BEE_API_URL}/stamps/topup/{batch_id}")
        print(f"🛠️ TTL Top-Up response: {topup_response.status_code} - {topup_response.text}")

        if topup_response.status_code == 200:
            play_notification_sound()
        return topup_response.status_code == 200

    except Exception as e:
        print(f"❌ Error during batch dilution or top-up: {e}")
        return False


def purchase_postage_stamp(amount, depth, label, mutable, quoted_xbzz=None):
    """Purchase a new batch with the desired depth and TTL settings."""
    try:
        clean_label = label.encode("ascii", "ignore").decode().strip()[:32] or "UnnamedBatch"
        actual_xbzz = Decimal(amount) / PLUR_PER_xBZZ

        if quoted_xbzz and actual_xbzz > Decimal(quoted_xbzz) * 2:
            print("❌ Aborted: Stamp cost exceeds 2x the quoted estimate. Check calculation logic.")
            return None

        headers = {
            "immutable": "false" if mutable else "true",
            "label": clean_label
        }
        response = requests.post(f"{BEE_API_URL}/stamps/{int(amount)}/{depth}", headers=headers)
        print(f"📦 Stamp creation response: {response.status_code} - {response.text}")
        if response.status_code == 201:
            return response.json().get("batchID")
    except Exception as e:
        print(f"❌ Exception during stamp creation: {e}")
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
