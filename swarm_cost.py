import os
import requests
import math
from web3 import Web3

# Bee Node API URL (adjust this if needed)
BEE_API_URL = "http://bee.swarm.public.dappnode:1633"

# Set up Web3 connection to the Bee node
web3 = Web3(Web3.HTTPProvider(BEE_API_URL))

# Function to get the PostageStamp contract address from the Bee node API
def get_postage_contract_address():
    try:
        # Query the Bee node's /info endpoint to get the PostageStamp contract address
        response = requests.get(f"{BEE_API_URL}?getprice")
        response.raise_for_status()
        
        # Parse the response JSON to extract the contract address
        data = response.json()
        
        # Assuming the address is returned in a field like "postageStampContractAddress"
        postage_contract_address = data.get("postageStampContractAddress")
        
        if not postage_contract_address:
            print("\nError: PostageStamp contract address not found in Bee node response.")
            return None
        
        return postage_contract_address
    except Exception as e:
        print(f"\nError: Unable to fetch contract address. {e}")
        return None

# ABI of the PostageStamp contract
POSTAGE_CONTRACT_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getPricePerChunk",
        "outputs": [
            {
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

# Fetch contract address automatically
POSTAGE_CONTRACT_ADDRESS = get_postage_contract_address()

if not POSTAGE_CONTRACT_ADDRESS:
    print("\nError: Contract address could not be determined. Exiting.")
    exit(1)

# Connect to the PostageStamp contract
postage_contract = web3.eth.contract(address=POSTAGE_CONTRACT_ADDRESS, abi=POSTAGE_CONTRACT_ABI)

def get_price_per_chunk():
    """Fetch the current price per chunk from the PostageStamp contract."""
    try:
        price_per_chunk_plur = postage_contract.functions.getPricePerChunk().call()
        return price_per_chunk_plur
    except Exception as e:
        print(f"\nError: Unable to fetch storage price. {e}")
        return None

def get_file_size():
    """Prompt user for a file and return its size in bytes."""
    file_path = input("Enter the file path: ").strip()
    file_path = os.path.normpath(file_path)

    if os.path.isfile(file_path):
        return os.path.getsize(file_path)
    else:
        print("\nError: File not found. Please enter a valid file path.")
        return None

def estimate_storage_cost(file_size_bytes, price_per_chunk):
    """Estimate xBZZ cost for storing the file for one year."""
    CHUNK_SIZE = 4096  # 4 KB per chunk
    PLUR_TO_XBZZ = 1_000_000_000  # 1 xBZZ = 1 billion PLUR

    required_chunks = math.ceil(file_size_bytes / CHUNK_SIZE)  # Round up to full chunks
    total_cost_xBZZ = (required_chunks * price_per_chunk) / PLUR_TO_XBZZ

    return total_cost_xBZZ

def main():
    print("Ethereum Swarm Storage Cost Estimator\n")

    file_size_bytes = get_file_size()
    if file_size_bytes is None:
        return

    price_per_chunk_plur = get_price_per_chunk()
    if price_per_chunk_plur is None:
        return

    estimated_cost = estimate_storage_cost(file_size_bytes, price_per_chunk_plur)

    print(f"\nEstimated xBZZ Cost for 1 Year: {estimated_cost:.9f} xBZZ")

if __name__ == "__main__":
    main()