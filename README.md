OpenFi Faucet Bot is a Python utility designed to automate the minting of testnet asset tokens (GOLD, TSLA, NVIDIA) from the OpenFi Faucet on the Pharos testnet. It supports batch processing of multiple wallets and provides an optional feature to use HTTP proxies for each wallet, enhancing privacy and bypassing rate limits. After every minting cycle, the bot reports the current balance of each token for every wallet used.

## What does it do?

- **Automated Faucet Minting:** Mints 100 units of each supported asset for every wallet listed in `accounts.txt`.
- **Multi-Wallet Support:** Processes multiple wallets in parallel.
- **Proxy Option:** Can assign one HTTP proxy per wallet from `proxy.txt` (format `http://username:password@ip:port`). If a proxy fails, it switches to the next.
- **Balance Reporting:** After each cycle, prints the balance of minted tokens for every wallet.
- **Interactive Launch:** On startup, lets you choose to run with proxies or without.

## How to Install

1. **Clone the Repository**
    ```bash
    git clone https://github.com/zerosocialcode/OpenFi-Faucet-Pharos.git
    cd OpenFi-Faucet-Pharos
    ```

2. **Install Python Dependencies**
    ```bash
    pip install -r requirements.txt
    ```
    If `requirements.txt` is missing, install manually:
    ```bash
    pip install web3 colorama pytz eth-account
    ```

3. **Prepare Your Files**
    - **accounts.txt:** Each line should contain a private key for a wallet.
    - **proxy.txt:** (Optional) Each line should be in the format `http://username:password@ip:port`.

4. **Run the Bot**
    ```bash
    python bot.py
    ```
    - Choose `[1] Run with proxy` if you want to use proxies (requires `proxy.txt`).
    - Choose `[2] Run without proxy` for regular operation.

## Example Usage

```
==== OpenFi Faucet by zerosocialcode ====
[1] Run with proxy
[2] Run without proxy
Choose option (1/2): 2
```
Minting starts, and after each cycle, wallet balances are printed.

## Developer Info

- **Author:** zerosocialcode
- **Contact:** [GitHub Profile](https://github.com/zerosocialcode)
