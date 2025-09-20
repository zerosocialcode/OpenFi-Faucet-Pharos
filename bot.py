import asyncio
import json
import os
import random
from datetime import datetime

from web3 import Web3
from web3.exceptions import TransactionNotFound
from eth_account import Account
from colorama import Fore, Style, init
import pytz

init(autoreset=True)
wib = pytz.timezone('Asia/Jakarta')

RPC_URL = "https://api.zan.top/node/v1/pharos/testnet/238d87abf88745eabb849aacaa82ce4f"
FAUCET_ROUTER_ADDRESS = "0x0E29d74Af0489f4B08fBfc774e25C0D3b5f43285"
ERC20_CONTRACT_ABI = json.loads('''[
    {"type":"function","name":"decimals","stateMutability":"view","inputs":[],"outputs":[{"name":"","type":"uint8"}]}
]''')
OPENFI_CONTRACT_ABI = [
    {
        "type": "function",
        "name": "isMintable",
        "stateMutability": "view",
        "inputs": [
            { "internalType": "address", "name": "asset", "type": "address" }
        ],
        "outputs": [
            { "internalType": "bool", "name": "", "type": "bool" }
        ]
    },
    {
        "type": "function",
        "name": "mint",
        "stateMutability": "nonpayable",
        "inputs": [
            { "internalType": "address", "name": "token", "type": "address" },
            { "internalType": "address", "name": "to", "type": "address" },
            { "internalType": "uint256", "name": "amount", "type": "uint256" }
        ],
        "outputs": [
            { "internalType": "uint256", "name": "", "type": "uint256" }
        ]
    }
]
ASSETS = [
    ("GOLD", "0xAaf03Cbb486201099EdD0a52E03Def18cd0c7354"),
    ("TSLA", "0xA778b48339d3c6b4Bc5a75B37c6Ce210797076b1"),
    ("NVIDIA", "0xAaF3A7F1676385883593d7Ea7ea4FcCc675EE5d6"),
]

MINT_DELAY_SECONDS = (2, 3)   # random delay between mints per account
CYCLE_DELAY_SECONDS = 5       # delay between cycles (all accounts minted)

def log(message):
    print(
        f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
        f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
        flush=True
    )

def mask_account(account):
    return account[:6] + '*' * 6 + account[-6:]

def get_web3():
    return Web3(Web3.HTTPProvider(RPC_URL))

def generate_address(account):
    try:
        acc = Account.from_key(account)
        return acc.address
    except Exception as e:
        log(f"{Fore.RED}Generate Address Failed: {str(e)}{Style.RESET_ALL}")
        return None

async def send_raw_transaction_with_retries(account, web3, tx, nonce, retries=5):
    for attempt in range(retries):
        try:
            signed_tx = web3.eth.account.sign_transaction(tx, account)
            raw_tx = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = web3.to_hex(raw_tx)
            return tx_hash
        except TransactionNotFound:
            pass
        except Exception as e:
            log(f"{Fore.YELLOW}[Attempt {attempt + 1}] Send TX Error: {str(e)}{Style.RESET_ALL}")
        await asyncio.sleep(2 ** attempt)
    raise Exception("Transaction Hash Not Found After Maximum Retries")

async def wait_for_receipt_with_retries(web3, tx_hash, retries=5):
    for attempt in range(retries):
        try:
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            return receipt
        except TransactionNotFound:
            pass
        except Exception as e:
            log(f"{Fore.YELLOW}[Attempt {attempt + 1}] Wait for Receipt Error: {str(e)}{Style.RESET_ALL}")
        await asyncio.sleep(2 ** attempt)
    raise Exception("Transaction Receipt Not Found After Maximum Retries")

async def mint_faucet(account: str, address: str, asset_address: str, ticker: str):
    web3 = get_web3()
    router_address = web3.to_checksum_address(FAUCET_ROUTER_ADDRESS)
    router_contract = web3.eth.contract(address=router_address, abi=OPENFI_CONTRACT_ABI)

    asset_address = web3.to_checksum_address(asset_address)
    asset_contract = web3.eth.contract(address=asset_address, abi=ERC20_CONTRACT_ABI)
    decimals = asset_contract.functions.decimals().call()

    # Check mintable
    is_mintable = router_contract.functions.isMintable(asset_address).call()
    if not is_mintable:
        log(f"{Fore.YELLOW}Asset not mintable: {ticker}{Style.RESET_ALL}")
        return None, None

    amount_to_wei = int(100 * (10 ** decimals))
    mint_data = router_contract.functions.mint(asset_address, address, amount_to_wei)
    estimated_gas = mint_data.estimate_gas({"from": address})

    max_priority_fee = web3.to_wei(1, "gwei")
    max_fee = max_priority_fee
    nonce = web3.eth.get_transaction_count(address, "pending")

    mint_tx = mint_data.build_transaction({
        "from": address,
        "gas": int(estimated_gas * 1.2),
        "maxFeePerGas": int(max_fee),
        "maxPriorityFeePerGas": int(max_priority_fee),
        "nonce": nonce,
        "chainId": web3.eth.chain_id,
    })

    tx_hash = await send_raw_transaction_with_retries(account, web3, mint_tx, nonce)
    receipt = await wait_for_receipt_with_retries(web3, tx_hash)
    block_number = receipt.blockNumber
    explorer = f"https://testnet.pharosscan.xyz/tx/{tx_hash}"

    log(f"{Fore.GREEN}Mint 100 {ticker} Faucet Success{Style.RESET_ALL}")
    log(f"{Fore.WHITE}Block: {block_number}{Style.RESET_ALL}")
    log(f"{Fore.WHITE}Tx Hash: {tx_hash}{Style.RESET_ALL}")
    log(f"{Fore.WHITE}Explorer: {explorer}{Style.RESET_ALL}")
    return tx_hash, block_number

async def nonstop_mint():
    try:
        with open('accounts.txt', 'r') as file:
            accounts = [line.strip() for line in file if line.strip()]
        log(f"{Fore.GREEN}Accounts Loaded: {len(accounts)}{Style.RESET_ALL}")

        cycle = 0
        while True:
            cycle += 1
            log(f"{Fore.BLUE}{'-'*10} Minting Cycle {cycle} {'-'*10}{Style.RESET_ALL}")
            for account in accounts:
                address = generate_address(account)
                if not address:
                    log(f"{Fore.RED}Invalid Private Key: {account}{Style.RESET_ALL}")
                    continue

                separator = "=" * 25
                log(f"{Fore.CYAN}{separator}[{Style.RESET_ALL}{Fore.WHITE}{mask_account(address)}{Style.RESET_ALL}{Fore.CYAN}]{separator}{Style.RESET_ALL}")

                # Mint for each asset
                for ticker, asset_address in ASSETS:
                    log(f"{Fore.BLUE}Minting Faucet for {ticker}{Style.RESET_ALL}")
                    await mint_faucet(account, address, asset_address, ticker)
                    await asyncio.sleep(random.randint(*MINT_DELAY_SECONDS))

            log(f"{Fore.MAGENTA}All accounts processed for this cycle. Waiting {CYCLE_DELAY_SECONDS} seconds before next cycle...{Style.RESET_ALL}")
            await asyncio.sleep(CYCLE_DELAY_SECONDS)

    except FileNotFoundError:
        log(f"{Fore.RED}File 'accounts.txt' Not Found.{Style.RESET_ALL}")
    except Exception as e:
        log(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        raise e

if __name__ == "__main__":
    try:
        asyncio.run(nonstop_mint())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] Faucet Mint Script{Style.RESET_ALL}                                       "
        )
