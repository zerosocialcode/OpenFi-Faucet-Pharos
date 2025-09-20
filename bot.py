import asyncio
import json
import random
from datetime import datetime
import pytz

from web3 import Web3
from web3.exceptions import TransactionNotFound
from eth_account import Account
from colorama import Fore, Style, init

init(autoreset=True)
zone = pytz.timezone('Asia/Jakarta')

NODE_ENDPOINT = "https://api.zan.top/node/v1/pharos/testnet/238d87abf88745eabb849aacaa82ce4f"
ROUTER_ADDR = "0x0E29d74Af0489f4B08fBfc774e25C0D3b5f43285"

ERC20_ABI = json.loads('[{"type":"function","name":"decimals","stateMutability":"view","inputs":[],"outputs":[{"name":"","type":"uint8"}]},'
                       '{"type":"function","name":"balanceOf","stateMutability":"view","inputs":[{"name":"account","type":"address"}],"outputs":[{"name":"","type":"uint256"}]}]')
OPENFI_ABI = [
    {"type":"function","name":"isMintable","stateMutability":"view","inputs":[{"internalType":"address","name":"asset","type":"address"}],"outputs":[{"internalType":"bool","name":"","type":"bool"}]},
    {"type":"function","name":"mint","stateMutability":"nonpayable","inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"outputs":[{"internalType":"uint256","name":"","type":"uint256"}]}
]
TOKENS = [
    ("GOLD", "0xAaf03Cbb486201099EdD0a52E03Def18cd0c7354"),
    ("TSLA", "0xA778b48339d3c6b4Bc5a75B37c6Ce210797076b1"),
    ("NVIDIA", "0xAaF3A7F1676385883593d7Ea7ea4FcCc675EE5d6"),
]

SLEEP_RANGE = (2, 3)
LOOP_PAUSE = 5

BOT_NAME = "OpenFi Faucet"
DEV_NAME = "zerosocialcode"

def banner(msg, clr=Fore.BLUE):
    timestamp = datetime.now().astimezone(zone).strftime('%Y-%m-%d %H:%M:%S %Z')
    print(f"{clr}[{timestamp}]{Style.RESET_ALL} {Fore.WHITE}{msg}{Style.RESET_ALL}", flush=True)

def header():
    banner(f"{Fore.CYAN}==== {BOT_NAME} by {DEV_NAME} ====", Fore.CYAN)

def obfuscate(addr):
    return f"{addr[:4]}...{addr[-4:]}"

def fetch_web3():
    return Web3(Web3.HTTPProvider(NODE_ENDPOINT))

def derive_addr(priv):
    try:
        return Account.from_key(priv).address
    except Exception as e:
        banner(f"{Fore.RED}Address error: {e}")
        return None

async def push_tx(priv, web3, tx, nonce, max_retry=5):
    for i in range(max_retry):
        try:
            signed = web3.eth.account.sign_transaction(tx, priv)
            tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
            return web3.to_hex(tx_hash)
        except Exception as e:
            banner(f"{Fore.YELLOW}[Retry {i+1}] TX failed: {e}")
        await asyncio.sleep(2 ** i)
    raise Exception("TX push failed after retries")

async def await_receipt(web3, tx_hash, max_retry=5):
    for i in range(max_retry):
        try:
            return web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        except Exception as e:
            banner(f"{Fore.YELLOW}[Retry {i+1}] Receipt wait error: {e}")
        await asyncio.sleep(2 ** i)
    raise Exception("Receipt not found after retries")

async def faucet_mint(priv, addr, asset_addr, label):
    web3 = fetch_web3()
    router = web3.eth.contract(address=web3.to_checksum_address(ROUTER_ADDR), abi=OPENFI_ABI)
    asset = web3.eth.contract(address=web3.to_checksum_address(asset_addr), abi=ERC20_ABI)
    decimals = asset.functions.decimals().call()
    if not router.functions.isMintable(web3.to_checksum_address(asset_addr)).call():
        banner(f"{Fore.YELLOW}Not mintable: {label}")
        return None, None

    amt = int(100 * (10 ** decimals))
    tx_obj = router.functions.mint(asset_addr, addr, amt)
    gas = int(tx_obj.estimate_gas({'from': addr}) * 1.15)
    prio_fee = web3.to_wei(1, "gwei")
    nonce = web3.eth.get_transaction_count(addr, "pending")

    tx = tx_obj.build_transaction({
        "from": addr,
        "gas": gas,
        "maxFeePerGas": prio_fee,
        "maxPriorityFeePerGas": prio_fee,
        "nonce": nonce,
        "chainId": web3.eth.chain_id,
    })

    tx_hash = await push_tx(priv, web3, tx, nonce)
    receipt = await await_receipt(web3, tx_hash)
    block = receipt.blockNumber
    explorer = f"https://testnet.pharosscan.xyz/tx/{tx_hash}"

    banner(f"{Fore.GREEN}Minted 100 {label} successfully")
    banner(f"{Fore.WHITE}Block: {block}")
    banner(f"{Fore.WHITE}Tx: {tx_hash}")
    banner(f"{Fore.WHITE}Explorer: {explorer}")
    return tx_hash, block

def get_balances(addr):
    web3 = fetch_web3()
    results = []
    for label, asset_addr in TOKENS:
        contract = web3.eth.contract(address=web3.to_checksum_address(asset_addr), abi=ERC20_ABI)
        try:
            decimals = contract.functions.decimals().call()
            balance = contract.functions.balanceOf(addr).call() / (10 ** decimals)
            results.append((label, balance))
        except Exception as e:
            results.append((label, "ERR"))
    return results

async def mint_loop():
    header()
    try:
        with open('accounts.txt', 'r') as f:
            privs = [l.strip() for l in f if l.strip()]
        banner(f"{Fore.GREEN}Loaded {len(privs)} accounts")

        count = 0
        while True:
            count += 1
            banner(f"{Fore.MAGENTA}--- Cycle {count} ---")
            for priv in privs:
                addr = derive_addr(priv)
                if not addr:
                    banner(f"{Fore.RED}Bad key: {priv}")
                    continue
                banner(f"{Fore.BLUE}Account: {obfuscate(addr)}")
                for label, asset_addr in TOKENS:
                    banner(f"{Fore.CYAN}Minting {label}")
                    await faucet_mint(priv, addr, asset_addr, label)
                    await asyncio.sleep(random.randint(*SLEEP_RANGE))
            # Show balances after each cycle
            banner(f"{Fore.WHITE}=== WALLET STATUS: Faucet Token Balances ===", Fore.WHITE)
            for priv in privs:
                addr = derive_addr(priv)
                if not addr:
                    continue
                balances = get_balances(addr)
                balance_str = " | ".join([f"{lbl}: {bal}" for lbl, bal in balances])
                banner(f"{Fore.YELLOW}{obfuscate(addr)} -> {balance_str}", Fore.YELLOW)
            banner(f"{Fore.YELLOW}Cycle complete. Waiting {LOOP_PAUSE}s.")
            await asyncio.sleep(LOOP_PAUSE)
    except FileNotFoundError:
        banner(f"{Fore.RED}Missing accounts.txt")
    except Exception as e:
        banner(f"{Fore.RED}Fatal error: {e}")
        raise e

if __name__ == "__main__":
    try:
        asyncio.run(mint_loop())
    except KeyboardInterrupt:
        banner(f"{Fore.RED}[EXIT] Mint script terminated.")
