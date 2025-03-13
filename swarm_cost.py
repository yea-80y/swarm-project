import json
import os
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
    
    # Postage stamp contract address
    postage_contract_address = "0x45a1502382541Cd610CC9068e88727426b696293"
    
    # ABI for the PostageStamp contract
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
        # Get the last price per chunk
        price_per_chunk = contract.functions.lastPrice().call()
        print(f"Postage stamp price per chunk (in PLUR): {price_per_chunk}")
        
        # Conversion from PLUR to xBZZ
        PLUR_TO_XBZZ_CONVERSION_RATE = 10000000000000000  # 10^16 PLUR = 1 xBZZ
        price_per_chunk_in_xbzz = price_per_chunk / PLUR_TO_XBZZ_CONVERSION_RATE
        print(f"Postage stamp price per chunk (in xBZZ): {price_per_chunk_in_xbzz}")
        
        # File selection via CLI
        file_path = input("Enter the file path: ").strip()
        
        if not os.path.exists(file_path):
            print("Invalid file path. Exiting...")
        else:
            file_size_kb = os.path.getsize(file_path) / 1024  # Convert bytes to KB
            print(f"Selected file size: {file_size_kb:.2f} KB")
            
            CHUNK_SIZE_KB = 4  # Chunk size in KB
            
            def calculate_file_cost(file_size_kb, price_per_chunk_in_xbzz):
                num_chunks = (file_size_kb + CHUNK_SIZE_KB - 1) // CHUNK_SIZE_KB
                total_cost_per_chunk = num_chunks * price_per_chunk_in_xbzz
                
                BLOCK_TIME_SECONDS = 5  # Ethereum block time
                storage_time_seconds = price_per_chunk / (price_per_chunk / BLOCK_TIME_SECONDS)
                storage_time_hours = storage_time_seconds / 3600  # Convert to hours
                storage_time_years = storage_time_hours / (24 * 365)  # Convert to years
                
                cost_for_one_year = total_cost_per_chunk / storage_time_years
                
                return cost_for_one_year
            
            total_cost_in_xbzz = calculate_file_cost(file_size_kb, price_per_chunk_in_xbzz)
            print(f"Estimated cost to store {file_size_kb / 1000:.2f} MB file on Swarm for one year: {total_cost_in_xbzz:.8f} xBZZ")
    
    except Exception as e:
        print(f"Error connecting to Postage Stamp contract: {e}")
        
else:
    print("Failed to connect to the Ethereum Bee Node.")