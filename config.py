# config.py

from decimal import Decimal
from web3 import Web3

# RPC and Bee Node API URLs
WEB3_RPC_URL = "https://rpc.gnosischain.com"
BEE_API_URL = "http://bee.swarm.public.dappnode:1633"  # or your DAppNode URL

# Swarm Postage Contract Info
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
PLUR_PER_xBZZ = Decimal(10**16)          # Conversion factor
CHUNK_SIZE_BYTES = Decimal(4096)         # 4KB per chunk
BLOCK_TIME_SECONDS = Decimal(5)          # Avg block time on Gnosis
STORAGE_TIME_SECONDS = Decimal(365 * 24 * 60 * 60)  # One year in seconds

# Local storage file for saved feed metadata
LOCAL_FEED_FILE = "local_feeds.json"

# Initialize Web3 connection
web3 = Web3(Web3.HTTPProvider(WEB3_RPC_URL))
if not web3.is_connected():  
    raise ConnectionError(f"Failed to connect to Web3 provider at {WEB3_RPC_URL}")
