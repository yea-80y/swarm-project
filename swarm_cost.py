import json
from web3 import Web3

# Bee Node API URL (adjust this if needed)
BEE_API_URL = "http://nethermind-xdai.dappnode:8545"

# Connect to the Ethereum Bee Node
web3 = Web3(Web3.HTTPProvider(BEE_API_URL))

# Check connection
if web3.is_connected():
    print("Successfully connected to the Ethereum Bee Node.")
    
    # Fetch the latest Ethereum block number
    block_number = web3.eth.block_number
    print(f"Latest Ethereum block number: {block_number}")
    
    # Postage stamp contract address (updated to correct address)
    postage_contract_address = "0x45a1502382541Cd610CC9068e88727426b696293"
    
    # ABI for the PostageStamp contract (from the provided ABI)
    postage_contract_abi = [
        {
            "inputs": [],
            "name": "lastPrice",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]
    
    # Create contract instance
    contract = web3.eth.contract(address=postage_contract_address, abi=postage_contract_abi)
    
    try:
        # Attempt to call the lastPrice function to get the price
        price_per_chunk = contract.functions.lastPrice().call()
        print(f"Postage stamp price per chunk (in PLUR): {price_per_chunk}")
        
        # Conversion from PLUR to xBZZ (10,000,000,000,000,000 PLUR = 1 xBZZ)
        PLUR_TO_XBZZ_CONVERSION_RATE = 10000000000000000  # 10^16 PLUR = 1 xBZZ
        price_per_chunk_in_xbzz = price_per_chunk / PLUR_TO_XBZZ_CONVERSION_RATE
        print(f"Postage stamp price per chunk (in xBZZ): {price_per_chunk_in_xbzz}")
        
        # Example file size calculation (100MB file, 100000KB)
        CHUNK_SIZE_KB = 4  # Chunk size in KB
        file_size_kb = 100000  # Example: 100MB file

        def calculate_file_cost(file_size_kb, price_per_chunk_in_xbzz):
            # Calculate number of chunks needed (round up to nearest chunk)
            num_chunks = (file_size_kb + CHUNK_SIZE_KB - 1) // CHUNK_SIZE_KB
            total_cost_per_chunk = num_chunks * price_per_chunk_in_xbzz
            
            # Swarm storage duration calculation
            BLOCK_TIME_SECONDS = 5  # Ethereum block time
            storage_time_seconds = price_per_chunk / (price_per_chunk / BLOCK_TIME_SECONDS)
            storage_time_hours = storage_time_seconds / 3600  # Convert to hours
            storage_time_years = storage_time_hours / (24 * 365)  # Convert to years
            
            # Cost for one year of storage
            cost_for_one_year = total_cost_per_chunk / storage_time_years
            
            return cost_for_one_year
        
        # Now call the function with the price value retrieved
        total_cost_in_xbzz = calculate_file_cost(file_size_kb, price_per_chunk_in_xbzz)
        print(f"Estimated cost to store {file_size_kb/1000}MB file on Swarm for one year: {total_cost_in_xbzz} xBZZ")
    
    except Exception as e:
        print(f"Error connecting to Postage Stamp contract: {e}")
        
else:
    print("Failed to connect to the Ethereum Bee Node.")
