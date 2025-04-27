# upload.py

import os
import time
import mimetypes
import requests
from bee_api import create_tag
from config import BEE_API_URL
from utils import play_notification_sound


def upload_file(file_path, batch_id, encrypt, topic_name=None):
    try:
        # Step 1: Create a tag
        tag_response = requests.post(f"{BEE_API_URL}/tags")
        tag_response.raise_for_status()
        tag_uid = tag_response.json().get("uid")
        if not tag_uid:
            print("❌ Failed to get tag UID from response.")
            return None
    except Exception as e:
        print(f"❌ Error creating tag: {e}")
        return None

    # Step 2: Prepare headers
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    headers = {
        "Swarm-Postage-Batch-Id": batch_id,
        "Content-Type": content_type,
        "Swarm-Encrypt": "true" if encrypt else "false",
        "Swarm-Tag": str(tag_uid)
    }

    if topic_name:
        headers["Swarm-Feed-Name"] = topic_name
        headers["Swarm-Feed-Type"] = "sequence"

    # Step 3: Upload the file
    with open(file_path, 'rb') as file:
        upload_response = requests.post(f"{BEE_API_URL}/bzz?tag={tag_uid}", headers=headers, data=file)

    if upload_response.status_code != 201:
        print(f"❌ Upload failed: {upload_response.status_code} {upload_response.text}")
        return None

    print("📤 Upload initiated. Tracking progress...")

    # Step 4: Track progress with smarter timeout and retries
    max_wait_time = 600  # seconds (10 minutes)
    last_seen = 0
    start_time = time.time()

    while True:
        time.sleep(2)
        try:
            status = requests.get(f"{BEE_API_URL}/tags/{tag_uid}").json()
            total = status.get("total", 0)
            seen = status.get("seen", 0)

            if total > 0:
                progress = (seen / total) * 100
                elapsed = int(time.time() - start_time)
                print(f"Uploading... {progress:.2f}% complete ({seen}/{total} chunks) [{elapsed}s elapsed]", end="\r")

                if seen == total:
                    print("\n✅ Upload complete!")
                    break

                if seen > last_seen:
                    last_seen = seen
                    start_time = time.time()  # Reset timer if progress is happening
            else:
                print("Waiting for upload to register chunks...", end="\r")

        except Exception as e:
            print(f"⚠️ Error checking tag progress: {e}", end="\r")

        # If no progress in max_wait_time seconds, abort
        if time.time() - start_time > max_wait_time:
            print("\n❌ Upload stuck. Timeout reached.")
            return None

    swarm_hash = upload_response.json().get("reference")
    if swarm_hash:
        play_notification_sound()
        print(f"✅ File uploaded successfully. Swarm Hash: {swarm_hash}")
        return swarm_hash
    else:
        print("❌ Could not retrieve Swarm hash after upload.")
        return None
