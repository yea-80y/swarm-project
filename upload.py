# upload.py

import os
import mimetypes
import requests
from config import BEE_API_URL
from utils import play_notification_sound

def upload_file(file_path, batch_id, encrypt, topic_name=None):
    try:
        # Step 1: Create a new tag
        tag_response = requests.post(f"{BEE_API_URL}/tags")
        tag_response.raise_for_status()
        tag_uid = tag_response.json().get("uid")
        if not tag_uid:
            print("❌ Failed to create a tag.")
            return None

        # Step 2: Prepare headers
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        headers = {
            "Swarm-Postage-Batch-Id": batch_id,
            "Swarm-Tag": str(tag_uid),
            "Content-Type": content_type,
            "Swarm-Encrypt": "true" if encrypt else "false"
        }

        if topic_name:
            headers["Swarm-Feed-Name"] = topic_name
            headers["Swarm-Feed-Type"] = "sequence"

        # Step 3: Upload the file
        print("\n📤 Attempting upload...")

        with open(file_path, "rb") as f:
            upload_response = requests.post(f"{BEE_API_URL}/bzz?tag=" + str(tag_uid), headers=headers, data=f)

        if upload_response.status_code == 201:
            swarm_hash = upload_response.json().get("reference")
            if not swarm_hash:
                print("❌ Upload finished but no swarm hash found!")
                return None

            print(f"\n✅ File uploaded successfully. Swarm Hash: {swarm_hash}")
            play_notification_sound()
            return swarm_hash
        else:
            print(f"❌ Upload failed: {upload_response.status_code} {upload_response.text}")
            return None

    except Exception as e:
        print(f"❌ Exception during upload: {e}")
        return None
