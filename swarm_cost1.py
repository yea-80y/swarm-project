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
    except requests.ConnectionError:
        return False
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
    base_depth = 17  # Minimum depth for smaller files
    max_volume = 1024 * 1024 * 1024 * 1024  # 1 TB in bytes

    if file_size >= max_volume:
        return base_depth

    proportion = file_size / max_volume
    required_depth = math.floor(base_depth + math.log2(proportion))

    return max(base_depth, required_depth)


def purchase_stamp(base_url, file_size):
    required_depth = calculate_required_depth(file_size)
    print(f"Calculated required depth for your file: {required_depth}")

    label = input("Enter a label for the new stamp: ").strip()

    try:
        response = requests.post(f'{base_url}/stamps', json={"depth": required_depth, "label": label})
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
