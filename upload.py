# upload.py

import os
import time
import mimetypes
import requests
from bee_api import get_tag_progress, create_tag
from config import BEE_API_URL
from utils import play_notification_sound

def upload_file(file_path, batch_id, encrypt, topic_name=None):
    """
    Uploads a file to Swarm with a created tag and tracks upload progress.
    """
    try:
        # Step 1: Create a tag
        tag_uid = create_tag()
        if not tag_uid:
            print("\u274c Failed to create tag.")
            return None

        # Step 2: Prepare upload headers
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
            response = requests.post(f"{BEE_API_URL}/bzz?tag={tag_uid}", headers=headers, data=file)
            if response.status_code != 201:
                print(f"\u274c Upload failed: {response.status_code} {response.text}")
                return None

            print("\ud83d\udce4 Upload initiated. Tracking progress...")

        # Step 4: Track progress via tag
        for _ in range(300):  # up to 10 minutes
            time.sleep(2)
            progress = get_tag_progress(tag_uid)
            if progress is not None:
                print(f"Uploading... [{progress:.2f}%]", end="\r")
                if progress >= 100:
                    break
        else:
            print("\u274c Upload seems stuck or incomplete after timeout.")
            return None

        # Step 5: Finalize
        swarm_hash = response.json().get("reference")
        if swarm_hash:
            print(f"\n\u2705 File uploaded. Swarm Hash: {swarm_hash}")
            play_notification_sound()
            return swarm_hash
        else:
            print("\u274c No Swarm hash returned.")
            return None

    except Exception as e:
        print(f"\u274c Exception during upload: {e}")
        return None
