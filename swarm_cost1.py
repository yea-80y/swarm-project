import requests
import json
import os
import math

def is_connected_to_dappnode():
    url = 'http://bee.swarm.public.dappnode:1633/health'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Connected to DAppNode Bee node.")
            return True
        else:
            print("Failed to connect to Bee node. Status code:", response.status_code)
            return False
    except requests.ConnectionError:
        print("Failed to connect to Bee node. Connection error.")
        return False

def get_existing_stamps(base_url):
    try:
        response = requests.get(f'{base_url}/stamps')
        if response.status_code == 200:
            stamps = response.json().get('stamps', [])
            if isinstance(stamps, list):
                return stamps
            else:
                return []
        else:
            return []
    except requests.RequestException:
        return []

def select_stamp(existing_stamps):
    if not existing_stamps:
        return None

    print("\nExisting Stamps:")
    for stamp in existing_stamps:
        print(f"Stamp ID: {stamp['batchID']} - Usable: {stamp['usable']} - Label: {stamp.get('label', 'N/A')}")

    choice = input("Do you want to use an existing stamp? (yes/no): ").strip().lower()

    if choice == 'yes':
        stamp_id = input("Enter the Stamp ID you want to use: ").strip()
        return stamp_id
    else:
        return None

def calculate_required_depth(file_size):
    max_volumes = {i: 2 ** (i + 15) for i in range(17, 32)}  # Depths 17 to 31

    for depth, max_volume in max_volumes.items():
        if file_size <= max_volume:
            return depth

    return max(max_volumes.keys())  # If file is larger than all defined volumes, use the largest depth

def calculate_required_plur(file_size, depth):
    price_per_chunk_in_xbzz = 4.1245e-12  # Example value
    max_volume = 2 ** depth
    required_chunks = math.ceil(file_size / max_volume)
    required_plur = required_chunks / price_per_chunk_in_xbzz

    total_xbzz = required_plur * price_per_chunk_in_xbzz * 1e-18
    print(f"Price per chunk in xBZZ: {price_per_chunk_in_xbzz}")
    print(f"Total xBZZ required: {total_xbzz}")

    return int(required_plur)

def purchase_stamp(base_url, file_size):
    depth = calculate_required_depth(file_size)
    plur_amount = calculate_required_plur(file_size, depth)

    print(f"\nCalculated required depth for your file: {depth}")
    print(f"Calculated required PLUR amount: {plur_amount}")

    confirm = input("Do you want to proceed with purchasing this stamp? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Stamp purchase cancelled.")
        return None

    label = input("Enter a label for the new stamp: ").strip()

    try:
        response = requests.post(f'{base_url}/stamps', json={"amount": str(plur_amount), "depth": depth, "label": label})
        if response.status_code == 201:
            stamp_id = response.json().get('batchID')
            print(f"Stamp successfully purchased. Stamp ID: {stamp_id}")
            return stamp_id
        else:
            print(f"Failed to purchase stamp. Status code: {response.status_code}, Message: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Error purchasing stamp: {e}")
        return None

def upload_file(base_url, file_path, stamp_id, is_immutable):
    if stamp_id is None:
        raise Exception("No valid stamp ID provided for file upload.")

    with open(file_path, 'rb') as f:
        headers = {'swarm-postage-batch-id': stamp_id}

        if not is_immutable:
            headers['swarm-immutable'] = 'false'

        response = requests.post(f'{base_url}/bzz', files={'file': f}, headers=headers)

    if response.status_code == 201:
        return response.json().get('reference')
    else:
        raise Exception(f"File upload failed with status code {response.status_code}: {response.text}")

def main():
    base_url = 'http://localhost:1633'
    if is_connected_to_dappnode():
        base_url = 'http://bee.swarm.public.dappnode:1633'
    else:
        print("Error: Could not connect to Bee node. Exiting.")
        return

    existing_stamps = get_existing_stamps(base_url)
    stamp_id = select_stamp(existing_stamps)

    if not stamp_id:
        if input("No existing stamps selected. Do you want to purchase a new stamp? (yes/no): ").strip().lower() != 'yes':
            print("Exiting.")
            return

        file_path = input("Enter the path to the file you want to upload: ").strip()

        if not os.path.exists(file_path):
            print("Invalid file path. Exiting.")
            return

        file_size = os.path.getsize(file_path)
        stamp_id = purchase_stamp(base_url, file_size)

        if not stamp_id:
            print("Failed to obtain a valid stamp ID. Exiting.")
            return

    is_immutable = input("Do you want the file to be immutable? (yes/no): ").strip().lower() == 'yes'

    try:
        swarm_hash = upload_file(base_url, file_path, stamp_id, is_immutable)
        print(f"File successfully uploaded! Swarm hash: {swarm_hash}")
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
