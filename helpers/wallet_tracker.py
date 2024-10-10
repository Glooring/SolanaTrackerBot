# wallet_tracker.py

import asyncio
import httpx
import datetime
import pytz
import cachetools.func
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

#TELEGRAM_TOKEN = '6849584733:AAF_3D2XkpsC7zDEUz35WOHahSRRXvGf0gs'
# Set up necessary variables and cache
url = "https://api.mainnet-beta.solana.com"
headers = {"Content-Type": "application/json"}
local_tz = pytz.timezone('Europe/Bucharest')  # Change to your timezone
cache = cachetools.func.TTLCache(maxsize=1000, ttl=600)

def lamports_to_sol(lamports):
    return lamports / 1_000_000_000.0

async def get_transaction_details(signature):
    if signature in cache:
        return cache[signature]
    payload_transaction_details = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload_transaction_details, headers=headers)
        if response.status_code == 200:
            data = response.json()
            cache[signature] = data  # Store the data in cache
            return data

async def start_periodic_task(chat_id, context, wallet_address, user_data):
    try:
        user = user_data[chat_id]
        last_transactions = user['last_transactions'].get(wallet_address, [])
        wallet_name = next((w['name'] for w in user['tracked_wallets'] if w['address'] == wallet_address), wallet_address)
        while True:
            payload_transactions = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getConfirmedSignaturesForAddress2",
                "params": [wallet_address, {"limit": 10}]
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload_transactions, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('result'):
                    new_signatures = [tx['signature'] for tx in data['result']]
                    # Log the list of the first 10 transactions
                    print(f"Refreshed transactions for wallet {wallet_name} ({wallet_address}):")
                    for idx, signature in enumerate(new_signatures):
                        print(f"{idx+1}: {signature}")
                    if not last_transactions:
                        # First run, initialize last_transactions
                        last_transactions = new_signatures
                        user['last_transactions'][wallet_address] = last_transactions
                    else:
                        # Find new transactions
                        new_tx_signatures = [sig for sig in new_signatures if sig not in last_transactions]
                        if new_tx_signatures:
                            # Process from oldest to newest
                            for signature in reversed(new_tx_signatures):
                                transaction_details = await get_transaction_details(signature)
                                if transaction_details and 'result' in transaction_details:
                                    transaction_info = transaction_details['result']
                                    block_time = datetime.datetime.utcfromtimestamp(
                                        transaction_info['blockTime']
                                    ).replace(
                                        tzinfo=pytz.utc
                                    ).astimezone(
                                        local_tz
                                    ).strftime('%Y-%m-%d %H:%M:%S %Z') if 'blockTime' in transaction_info else "Unknown Time"
                                    message_time = datetime.datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S %Z')
                                    message = f"Wallet: `{escape_markdown(wallet_name, version=2)}`\n"
                                    message += f"Signature: `{escape_markdown(signature, version=2)}`\n"

                                    for txn_detail in transaction_info.get('transaction', {}).get('message', {}).get('instructions', []):
                                        if 'parsed' in txn_detail:
                                            info = txn_detail['parsed']['info']
                                            txn_type = txn_detail['parsed']['type']
                                            message += f"Transaction Time: `{block_time}`\n" \
                                                       f"Message Sent Time: `{message_time}`\n" \
                                                       f"Type: `{txn_type}`\n"

                                            if txn_type == 'transfer':
                                                message += f"From: `{escape_markdown(info['source'], version=2)}`\n" \
                                                           f"To: `{escape_markdown(info['destination'], version=2)}`\n" \
                                                           f"Amount: `{lamports_to_sol(info['lamports']):.6f} SOL`\n"
                                            # Add other transaction types as needed
                                    print(message)
                                    user['last_transactions'][wallet_address] = last_transactions
                                    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN_V2)
                            # Update last_transactions
                            last_transactions = new_signatures
                            user['last_transactions'][wallet_address] = last_transactions
            else:
                message = f"Error: '{response.status_code}'\n"
                print(message)
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN_V2)
            await asyncio.sleep(5)  # Check for new transactions every 5 seconds
    except:
        print(f"Tracking task for wallet {wallet_address} was cancelled.")
        # Clean up if necessary
        raise
