# config.py

from decimal import Decimal
from web3 import Web3

# Bee & Web3 RPC
WEB3_RPC_URL = "https://rpc.gnosischain.com"
BEE_API_URL = "http://bee.swarm.public.dappnode:1633"

# Swarm Postage Contract (for future on-chain price reads)
POSTAGE_CONTRACT_ADDRESS = "0x45a1502382541Cd610CC9068e88727426b696293"
POSTAGE_CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "lastPrice",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    }
]

# Constants
PLUR_PER_xBZZ = Decimal(10**16)           # Conversion factor
CHUNK_SIZE_BYTES = Decimal(4096)          # 4KB per chunk
BLOCK_TIME_SECONDS = Decimal(5)           # Gnosis block time

# ✅ TTL settings for testing
STORAGE_TIME_SECONDS = Decimal(7 * 24 * 60 * 60)       # ⏳ 1 week TTL for new batches
DILUTION_TOPUP_TTL = Decimal(7 * 24 * 60 * 60)         # ⏳ 1 week TTL for dilution top-ups

# Stamp readiness wait config
WAIT_FOR_BATCH_TIMEOUT = 3600   # 1 hour
WAIT_FOR_BATCH_RETRY = 15       # 15 seconds between checks

# Local feed file
LOCAL_FEED_FILE = "local_feeds.json"

# Web3 init
web3 = Web3(Web3.HTTPProvider(WEB3_RPC_URL))
if not web3.is_connected():
    raise ConnectionError(f"❌ Failed to connect to Web3 at {WEB3_RPC_URL}")
