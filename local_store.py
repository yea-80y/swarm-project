import os
import json

# Local JSON file that stores feed (file) names and corresponding Swarm hashes per batch
LOCAL_FEED_FILE = "local_feeds.json"

def load_local_feeds():
    """
    Loads locally saved file name -> Swarm hash mappings for each batch.
    Returns:
        dict: A dictionary where keys are batch IDs and values are file name/hash pairs.
    """
    if os.path.exists(LOCAL_FEED_FILE):
        try:
            with open(LOCAL_FEED_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load local feeds: {e}")
    return {}

def save_local_feed(batch_id, file_name, swarm_hash):
    """
    Saves a file name and its Swarm hash under a given batch ID to local storage.
    Creates a new batch entry if it doesn't exist.

    Args:
        batch_id (str): ID of the batch.
        file_name (str): Human-readable file name used as the Swarm Feed name.
        swarm_hash (str): Swarm hash of the uploaded file.
    """
    feeds = load_local_feeds()
    if batch_id not in feeds:
        feeds[batch_id] = {}
    feeds[batch_id][file_name] = swarm_hash

    try:
        with open(LOCAL_FEED_FILE, "w") as f:
            json.dump(feeds, f, indent=2)
        print(f"🗘️ Saved locally: {file_name} -> {swarm_hash}")
    except Exception as e:
        print(f"❌ Failed to save feed: {e}")
