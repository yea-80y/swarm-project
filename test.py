import requests
from web3 import Web3

# Bee Node API URL (adjust this if needed)
BEE_API_URL = "http://bee.swarm.public.dappnode:1633"

# Manually request to check /eth/blockNumber endpoint
try:
    # Check if /eth/blockNumber returns valid data
    response = requests.get(BEE_API_URL + "/eth/blockNumber")
    
    if response.status_code == 200:
        print("Successfully connected to Bee Node. Response received:")
        print(response.json())  # Print the actual JSON response to inspect it
    else:
        print(f"Failed to connect to Bee Node. Status code: {response.status_code}")

    # Now use Web3 to check Ethereum block number if the connection is successful
    web3 = Web3(Web3.HTTPProvider(BEE_API_URL))
    
    if web3.is_connected():
        print("Successfully connected to the Ethereum Bee Node.")
        
        # Fetch the latest Ethereum block number
        block_number = web3.eth.block_number
        print(f"Latest Ethereum block number: {block_number}")
        
        # Assuming the postage stamp contract address (from previous info)
        postage_contract_address = "0x30d155478eF27Ab32A1D578BE7b84BC5988aF381"
        
        # ABI of the PostageStamp contract (simplified for example)
        postage_contract_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "getPrice",
                "outputs": [{"name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            }
        ]
        
        # Create contract instance
        contract = web3.eth.contract(address=postage_contract_address, abi=postage_contract_abi)
        
        # Get the price of the postage stamp (in PLUR)
        price_per_chunk = contract.functions.getPrice().call()
        print(f"Postage stamp price per chunk (in PLUR): {price_per_chunk}")
        
        # Convert PLUR to xBZZ (correct conversion rate)
        PLUR_TO_XBZZ_CONVERSION_RATE = 1000000000000000000  # 1 PLUR = 1 xBZZ / 10^18
        price_per_chunk_in_xbzz = price_per_chunk / PLUR_TO_XBZZ_CONVERSION_RATE
        print(f"Postage stamp price per chunk (in xBZZ): {price_per_chunk_in_xbzz}")
        
        # Now we need to calculate how many chunks are needed for a file
        # Correct chunk size is 4KB
        CHUNK_SIZE_KB = 4  # Chunk size in KB
        
        def calculate_file_cost(file_size_kb):
            # Calculate number of chunks needed (round up to nearest chunk)
            num_chunks = (file_size_kb + CHUNK_SIZE_KB - 1) // CHUNK_SIZE_KB
            total_cost = num_chunks * price_per_chunk_in_xbzz
            return total_cost
        
        # Example: Let's assume the user has a file of 100MB (100,000KB)
        file_size_kb = 100000
        total_cost_in_xbzz = calculate_file_cost(file_size_kb)
        print(f"Estimated cost to store {file_size_kb/1000}MB file on Swarm: {total_cost_in_xbzz} xBZZ")
        
    else:
        print("Failed to connect to the Ethereum Bee Node.")
except Exception as e:
    print(f"Error: {e}")