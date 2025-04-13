# upload.py

import requests
import mimetypes
import time
import os
from bee_api import create_tag, get_tag_progress, wait_for_stamp_usable
from local_store import save_local_feed  # ✅ Corrected import

# Upload file to Bee node
def upload_file(file_path, batch_id, encrypt=False, topic_name=None):
    tag_uid = create_tag()
    if not tag_uid:
        print("❌ Failed to create tag. Upload aborted.")
        return None

    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    headers = {
        "Swarm-Postage-Batch-Id": batch_id,
        "Content-Type": content_type,
        "Swarm-Encrypt": "true" if encrypt else "false"
    }

    if topic_name:
        headers["Swarm-Feed-Name"] = topic_name
        headers["Swarm-Feed-Type"] = "sequence"

    with open(file_path, 'rb') as f:
        try:
            response = requests.post(f"http://localhost:1633/bzz?tag={tag_uid}", headers=headers, data=f)
            if response.status_code == 201:
                while True:
                    percent = get_tag_progress(tag_uid)
                    if percent is not None:
                        print(f"Uploading... [{percent}%]", end='\r')
                        if percent >= 100:
                            break
                    time.sleep(1)

                swarm_hash = response.json().get("reference")
                print(f"\n✅ File uploaded successfully.")
                print(f"📦 Swarm Hash: {swarm_hash}")
                if topic_name:
                    if input("Would you like to save this file and hash locally? (yes/no): ").strip().lower() == "yes":
                        save_local_feed(batch_id, topic_name, swarm_hash)
                    else:
                        print("⚠️ Make sure to note your file name and Swarm hash for future access.")
                return swarm_hash
            else:
                print(f"❌ Upload failed: {response.status_code} {response.text}")
                return None
        except requests.RequestException as e:
            print(f"❌ Upload error: {e}")
            return None
