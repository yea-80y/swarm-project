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
    
    # Postage stamp contract address
    postage_contract_address = "0x344A2CC7304B32A87EfDC5407cD4bEC7cf98F035"
    
    # ABI for the PostageStamp contract
    postage_contract_abi = [
        # ABI contents here, the contract ABI you've provided
        {"inputs":[{"internalType":"address","name":"_postageStamp","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},
        {"anonymous":False,"inputs":[{"indexed":False,"internalType":"uint256","name":"price","type":"uint256"}],"name":"PriceUpdate","type":"event"},
        {"inputs":[],"name":"currentPrice","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        # Other ABI items omitted for brevity
    ]
    
    # Create contract instance
    contract = web3.eth.contract(address=postage_contract_address, abi=postage_contract_abi)
    
    try:
        # Attempt to call the currentPrice function to get the price
        price_per_chunk = contract.functions.currentPrice().call()
        print(f"Postage stamp price per chunk (in PLUR): {price_per_chunk}")
        
        # Conversion from PLUR to xBZZ
        PLUR_TO_XBZZ_CONVERSION_RATE = 10000000000000000  # 10^16 PLUR = 1 xBZZ
        price_per_chunk_in_xbzz = price_per_chunk / PLUR_TO_XBZZ_CONVERSION_RATE
        print(f"Postage stamp price per chunk (in xBZZ): {price_per_chunk_in_xbzz}")
        
        # Example file size calculation (100MB file, 100000KB)
        CHUNK_SIZE_KB = 4  # Chunk size in KB
        file_size_kb = 100000  # Example: 100MB file
        
        def calculate_file_cost(file_size_kb, price_per_chunk_in_xbzz):
            # Calculate number of chunks needed (round up to nearest chunk)
            num_chunks = (file_size_kb + CHUNK_SIZE_KB - 1) // CHUNK_SIZE_KB
            total_cost = num_chunks * price_per_chunk_in_xbzz
            return total_cost
        
        # Now call the function with the price value retrieved
        total_cost_in_xbzz = calculate_file_cost(file_size_kb, price_per_chunk_in_xbzz)
        print(f"Estimated cost to store {file_size_kb/1000}MB file on Swarm: {total_cost_in_xbzz} xBZZ")
    
    except Exception as e:
        print(f"Error connecting to Postage Stamp contract: {e}")
        
else:
    print("Failed to connect to the Ethereum Bee Node.")