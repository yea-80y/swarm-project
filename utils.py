# utils.py

import os
import json
import mimetypes
from decimal import Decimal

# --- Constants ---
CHUNK_SIZE_BYTES = Decimal(4096)
PLUR_PER_xBZZ = Decimal(10**16)
BLOCK_TIME_SECONDS = Decimal(5)
STORAGE_TIME_SECONDS = Decimal(365 * 24 * 60 * 60)  # 1 year

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
def calculate_required_depth(file_size):
    """
    Calculate the minimum batch depth required to store a file of the given size.
    Each depth corresponds to 2^depth * 4096 bytes of capacity.
    """
    for depth in range(17, 32):
        if file_size <= (2 ** depth) * CHUNK_SIZE_BYTES:
            return depth
    return 31  # Max depth fallback

def calculate_required_plur(depth, price_per_block):
    """
    Calculate:
    - price per chunk
    - total cost in PLUR
    - total cost in xBZZ (converted)
    for storing data at a given depth for 1 year.
    """
    amount_per_chunk = (price_per_block / BLOCK_TIME_SECONDS) * STORAGE_TIME_SECONDS
    total_chunks = Decimal(2) ** Decimal(depth)
    total_plur = total_chunks * amount_per_chunk
    total_xbzz = total_plur / PLUR_PER_xBZZ
    return amount_per_chunk, total_plur, total_xbzz
