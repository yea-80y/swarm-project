# utils.py

import os
import json
import mimetypes
from decimal import Decimal

# --- Constants ---
CHUNK_SIZE_BYTES = Decimal(4096)  # 4 KB per chunk
PLUR_PER_xBZZ = Decimal(10**16)
BLOCK_TIME_SECONDS = Decimal(5)  # Gnosis block time
BLOCKS_PER_DAY = Decimal(86400) / BLOCK_TIME_SECONDS  # ~17280 blocks/day

# --- File Utilities ---
def get_file_size(file_path):
    """Return file size in bytes."""
    return os.path.getsize(file_path)

def bytes_to_mb(size_bytes):
    """Convert bytes to megabytes (MB)."""
    return Decimal(size_bytes) / (1024 ** 2)

def get_content_type(file_path):
    """Guess MIME type for the file."""
    return mimetypes.guess_type(file_path)[0] or "application/octet-stream"

def round_decimal(val, places=2):
    """Round a Decimal value to n places."""
    return round(val, places)

# --- Storage Calculation Utilities ---
def calculate_required_depth(file_size_bytes, encrypt=False):
    """
    Return the minimum depth needed for a file size, using Swarm's real effective volumes (unencrypted by default).
    
    Effective volume (Swarm April 2024): https://docs.ethswarm.org/docs/concepts/incentives/postage-stamps/
    """
    effective_volumes = {
        17: 3.48 * 1024**2,
        18: 6.97 * 1024**2,
        19: 13.93 * 1024**2,
        20: 27.86 * 1024**2,
        21: 55.73 * 1024**2,
        22: 111.47 * 1024**2,
        23: 222.95 * 1024**2,
        24: 445.90 * 1024**2,
        25: 891.80 * 1024**2,
        26: 1.78 * 1024**3,
        27: 3.56 * 1024**3,
        28: 7.13 * 1024**3,
    }

    if encrypt:
        # Reduce effective capacity by 50% for encrypted batches
        effective_volumes = {k: v * 0.5 for k, v in effective_volumes.items()}

    for depth in range(17, 29):
        if file_size_bytes <= effective_volumes[depth]:
            return depth

    return 28  # max fallback

def calculate_required_plur(depth, price_per_block):
    """
    Calculate:
    - price per chunk
    - total cost in PLUR
    - total cost in xBZZ (converted)
    for storing data at a given depth based on current price.
    """
    total_chunks = Decimal(2) ** Decimal(depth)
    amount_per_chunk = (price_per_block / BLOCK_TIME_SECONDS) * (7 * 24 * 60 * 60)  # 1 week TTL default
    total_plur = total_chunks * amount_per_chunk
    total_xbzz = total_plur / PLUR_PER_xBZZ
    return amount_per_chunk, total_plur, total_xbzz

# --- Notifications ---
from playsound import playsound

def play_notification_sound():
    """Play a notification sound when a batch becomes usable."""
    sound_path = os.path.join(os.path.dirname(__file__), "Bee.mp3")
    if os.path.exists(sound_path):
        try:
            playsound(sound_path)
        except Exception as e:
            print(f"⚠️ Could not play sound: {e}")
    else:
        print("🔇 Bee.mp3 not found. No sound played.")
