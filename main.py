from config import BEE_API_URL
from bee_api import (
    is_connected_to_bee,
    get_wallet_balance,
    get_existing_stamps,
    get_price_per_block,
    wait_for_stamp_usable
)
from storage import (
    calculate_required_depth,
    calculate_required_plur,
    purchase_postage_stamp,   # ✅ moved here from bee_api
    dilute_batch
)
from upload import (
    upload_file
)
from local_store import (
    load_local_feeds,
    save_local_feed
)
import os
import mimetypes
from decimal import Decimal


def main():
    if not is_connected_to_bee():
        print("Error: Could not connect to Bee node.")
        return

    print("Connected to Bee node.\n")
    wallet_balance = get_wallet_balance()
    print(f"Your xBZZ Balance: {wallet_balance:.6f} xBZZ")

    local_feeds = load_local_feeds()
    stamps = get_existing_stamps()

    if stamps:
        print("\nAvailable Batches:")
        usable_batches = []
        for i, stamp in enumerate(stamps):
            if stamp.get("usable", False):
                depth = int(stamp["depth"])
                total_mb = (2 ** depth) * Decimal(4096) / (1024 ** 2)
                utilization = Decimal(stamp.get("utilization", 0))
                remaining_mb = total_mb * (1 - utilization)
                label = stamp.get("label", "N/A")
                ttl_days = round(stamp['batchTTL'] / 86400, 2)
                print(f"{i+1}) Label: {label} | TTL: {ttl_days} days | Remaining: {round(remaining_mb,2)} MB")
                usable_batches.append((stamp, remaining_mb))

        if usable_batches and input("\nUse an existing batch? (yes/no): ").strip().lower() == 'yes':
            idx = 0
            if len(usable_batches) > 1:
                idx = int(input("Select batch number: ")) - 1
            stamp, remaining_mb = usable_batches[idx]
            batch_id = stamp['batchID']
            depth = int(stamp['depth'])
            mutable = not stamp.get("immutable", True)

            if batch_id in local_feeds:
                print("\nSaved Files:")
                for name in local_feeds[batch_id]:
                    print(f"- {name}")

            use_feed = input("Do you want to update an existing file? (yes/no): ").strip().lower() == 'yes'
            if use_feed:
                file_name = input("Enter the existing file name to update: ").strip()
            else:
                file_name = input("Enter a name for this file: ").strip()

            file_path = input("Enter file path to upload: ").strip()
            file_size = os.path.getsize(file_path)
            file_mb = Decimal(file_size) / (1024 ** 2)
            content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

            if file_mb > remaining_mb:
                new_depth = depth + 1
                _, add_plur, add_xbzz = calculate_required_plur(new_depth, get_price_per_block())
                print(f"\n⚠️ Not enough space. Need: {round(file_mb,2)} MB | Remaining: {round(remaining_mb,2)} MB")
                print(f"Cost to increase capacity: {add_xbzz:.6f} xBZZ")
                if wallet_balance < add_xbzz:
                    print("❌ Not enough xBZZ to increase storage.")
                    return
                if input("Increase storage? (yes/no): ").strip().lower() != 'yes':
                    return
                if not dilute_batch(batch_id, new_depth):
                    print("❌ Failed to increase storage.")
                    return

            encrypt = input("Should the file be encrypted? (yes/no): ").strip().lower() == 'yes'
            immutable = not mutable or input("Should the file be immutable? (yes/no): ").strip().lower() != 'no'
            wait_for_stamp_usable(batch_id)
            swarm_hash = upload_file(file_path, batch_id, encrypt, file_name)
            if swarm_hash:
                print(f"\nℹ️ File name: {file_name}")
                print(f"ℹ️ Swarm hash: {swarm_hash}")
                if input("Would you like to save this file and hash locally? (yes/no): ").strip().lower() == "yes":
                    save_local_feed(batch_id, file_name, swarm_hash)
                else:
                    print("⚠️ Be sure to note your file name and Swarm hash.")
            return

    # --- New Batch Upload Path ---

    file_path = input("Enter path to file you want to upload: ").strip()
    file_size = os.path.getsize(file_path)
    file_mb = Decimal(file_size) / (1024 ** 2)
    depth = calculate_required_depth(file_size)
    price = get_price_per_block()
    _, plur_cost, xbzz_cost = calculate_required_plur(depth, price)

    print(f"\nFile size: {round(file_mb,2)} MB")
    print(f"Estimated cost (1 year storage): {xbzz_cost:.6f} xBZZ")

    if wallet_balance < xbzz_cost:
        print("❌ Not enough xBZZ to purchase new batch.")
        return

    mutable = input("Should this batch allow file updates? (yes/no): ").strip().lower() == 'yes'
    label = input("Enter label for new batch: ")
    batch_id = purchase_postage_stamp(plur_cost, depth, label, mutable)
    if not batch_id:
        print("❌ Failed to create new batch.")
        return

    file_name = input("Enter a name for this file: ").strip()
    encrypt = input("Should the file be encrypted? (yes/no): ").strip().lower() == 'yes'
    immutable = not mutable or input("Should the file be immutable? (yes/no): ").strip().lower() != 'no'
    wait_for_stamp_usable(batch_id)
    swarm_hash = upload_file(file_path, batch_id, mimetypes.guess_type(file_path)[0] or "application/octet-stream", encrypt, file_name)
    if swarm_hash:
        print(f"\nℹ️ File name: {file_name}")
        print(f"ℹ️ Swarm hash: {swarm_hash}")
        if input("Would you like to save this file and hash locally? (yes/no): ").strip().lower() == "yes":
            save_local_feed(batch_id, file_name, swarm_hash)
        else:
            print("⚠️ Be sure to note your file name and Swarm hash.")


if __name__ == "__main__":
    main()
