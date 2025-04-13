# 🐝 Swarm Uploader

A Python-based tool to upload files to the [Ethereum Swarm](https://docs.ethswarm.org) decentralized storage network via your local Bee node.

It supports:
- Immutable and mutable (Swarm Feed) uploads
- Encryption
- Smart batch handling
- Local feed history using JSON

---

## 🔧 Features

- Upload files with a simple terminal flow
- Calculate and display file size and storage cost (1 year)
- Automatically determine appropriate batch depth
- Use or create stamp batches
- Support Swarm Feeds for versioned/mutable uploads
- Encrypted or plaintext file upload
- Store feed history in `local_feeds.json`
- Auto-dilute existing batch if not enough storage
- Waits until batch is usable before uploading

---

## 📁 Project Structure

```
swarm_uploader/
├── main.py           # Entry point, handles full upload flow
├── config.py         # Settings and constants (RPCs, PLUR conversion, etc.)
├── bee_api.py        # Bee node API: health, wallet, stamps
├── storage.py        # Depth calculation, pricing, dilution
├── upload.py         # Upload logic including tags, feeds, and encryption
├── feeds.py          # Swarm Feed-specific helpers
├── local_store.py    # Read/write local feed history JSON
├── utils.py          # Utility functions (file size, content type, etc.)
├── README.md         # This file
```

---

## ✅ Requirements

- Python 3.8+
- A Bee node running (e.g. `http://localhost:1633`)
- xBZZ tokens in your wallet (Gnosis chain)
- Internet access (for price lookups)

---

## 📦 Install Dependencies

Install required libraries:

```bash
pip install requests web3
```

Or create a `requirements.txt`:

```
requests
web3
```

And install with:

```bash
pip install -r requirements.txt
```

---

## 🚀 How to Run

Run the main script:

```bash
python main.py
```

The program will:
1. Check if Bee node is online
2. Print wallet balance and available batches
3. Ask to use an existing batch or create a new one
4. Ask for the file, encryption, immutability, and feed name (if mutable)
5. Estimate cost and perform upload
6. Prompt to save feed metadata locally

---

## 📝 Notes

- Files on **mutable batches** use **Swarm Feeds**, which allow updates using a consistent file name
- Feed data is saved in `local_feeds.json`
- If no local file is found, you’ll still be prompted to name/update your file manually
- Batch storage will be increased (diluted) if needed
- TTL will match existing chunks when increasing capacity

---

## 🌐 Useful Links

- 📖 [Swarm Docs](https://docs.ethswarm.org)
- 🔗 [Bee API Reference](https://docs.ethswarm.org/docs/access-the-swarm/api-reference/)
- 🧠 [Swarm Feeds](https://docs.ethswarm.org/docs/access-the-swarm/feeds/)
- 💰 [xBZZ Token](https://docs.ethswarm.org/docs/fundamentals/bzz-token/)
- 🧪 [Swarm GitHub](https://github.com/ethersphere)

---

## 🤝 License

This project is licensed under the MIT License.


