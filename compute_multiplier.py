# Have your ETHERSCAN_API_KEY in an .env file before running this code.
import os
import requests
from dotenv import load_dotenv
from web3 import Web3
import pandas as pd
from datetime import datetime


def get_multiplier(TARGET_WALLET):
    """
    Returns the multiplier for the distributions from r/EthTrader.
    
    inputs: TARGET_WALLET [str]
    output: multiplier
    """

    load_dotenv()
    ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
    ARBISCAN_API_URL = "https://api.etherscan.io/v2/api?chainid=42161"
    ARBITRUM_RPC = "https://arb1.arbitrum.io/rpc"

    w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to Arbitrum RPC")

    ERC20_ABI = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],  # Add input parameter
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        }
    ]

    def get_token_decimals(token_contract_address):
        """Get token decimals (Arbitrum-compatible)"""
        contract = w3.eth.contract(address=token_contract_address, abi=ERC20_ABI)
        return contract.functions.decimals().call()

    def get_token_balance(wallet_address, token_contract_address):
        """Get token balance on Arbitrum"""
        contract = w3.eth.contract(address=token_contract_address, abi=ERC20_ABI)
        balance = contract.functions.balanceOf(wallet_address).call()
        decimals = get_token_decimals(token_contract_address)
        return balance / (10 ** decimals)

    def get_transactions(target_wallet, origin_wallet, api_key):
        """
        Get ALL ERC-20 transfers from origin_wallet to target_wallet on Arbitrum One
        """
        ARBISCAN_API_URL = "https://api.etherscan.io/v2/api?chainid=42161"
        
        all_transactions = []
        page = 1
        offset = 10000
        
        while True:
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': '0xF42e2B8bc2aF8B110b65be98dB1321B1ab8D44f5',
                'address': target_wallet,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'asc',
                'page': page,
                'offset': offset,
                'apikey': api_key
            }
            
            response = requests.get(ARBISCAN_API_URL, params=params)
            data = response.json()
            
            if data['status'] != '1':
                print(f"API Error: {data.get('message')}")
                break
                
            transactions = data['result']
            if not transactions:
                break
                
            filtered = [
                tx for tx in transactions
                if (tx['from'].lower() == origin_wallet.lower() and 
                    tx['to'].lower() == target_wallet.lower() and
                    tx['contractAddress'].lower() == '0xf42e2b8bc2af8b110b65be98db1321b1ab8d44f5')
            ]
            all_transactions.extend(filtered)
            
            if len(transactions) < offset:
                break
                
            page += 1
        
        return all_transactions

    def transactions_to_dataframe(transactions):
        """
        Convert transaction data to a formatted pandas DataFrame.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Formatted pandas DataFrame
        """
        if not transactions:
            return pd.DataFrame()  
        
        df = pd.DataFrame(transactions)
        
        df['value'] = df['value'].astype(float)
        df['blockNumber'] = df['blockNumber'].astype(int)
        df['timeStamp'] = df['timeStamp'].astype(int)
        df['datetime'] = pd.to_datetime(df['timeStamp'], unit='s')
        df['token_value'] = df['value'] / (10**18)
        

        pd.set_option('display.float_format', '{:.8f}'.format)
        
        display_cols = [
            'datetime', 'blockNumber', 'hash', 
            'from', 'to', 'contractAddress',
            'token_value', 'value'
        ]
        
        return df[display_cols].rename(columns={
            'blockNumber': 'block',
            'hash': 'tx_hash',
            'contractAddress': 'token_address',
            'value': 'raw_value'
        })

    def analyze_token_flows(target_wallet, origin_wallet, token_contract_address, lp_address, api_key):
        """
        Analyze token flows between wallets and LP
        Returns comprehensive token flow metrics
        """

        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': token_contract_address,
            'address': target_wallet,
            'startblock': 0,
            'endblock': 99999999,
            'sort': 'asc',
            'page': 1,
            'offset': 10000,
            'apikey': api_key
        }
        
        response = requests.get("https://api.etherscan.io/v2/api?chainid=42161", params=params)
        data = response.json()
        
        if data['status'] != '1':
            print(f"API Error: {data.get('message')}")

        decimals = get_token_decimals(token_contract_address)
        transactions = data['result']
        
        received_from_origin = 0
        sent_to_origin = 0
        sent_to_lp = 0
        received_from_lp = 0
        
        for tx in transactions:
            value = int(tx['value']) / (10 ** decimals)
            
            # Received from origin
            if (tx['to'].lower() == target_wallet.lower() and 
                tx['from'].lower() == origin_wallet.lower()):
                received_from_origin += value
                
            # Sent to origin
            elif (tx['from'].lower() == target_wallet.lower() and 
                tx['to'].lower() == origin_wallet.lower()):
                sent_to_origin += value
                
            # Sent to LP
            elif (tx['from'].lower() == target_wallet.lower() and 
                tx['to'].lower() == lp_address.lower()):
                sent_to_lp += value
                
            # Received from LP
            elif (tx['to'].lower() == target_wallet.lower() and 
                tx['from'].lower() == lp_address.lower()):
                received_from_lp += value
        
        current_balance = get_token_balance(target_wallet, token_contract_address)
        lp_current_balance = get_token_balance(lp_address, token_contract_address)
        net_lp_contribution = sent_to_lp - received_from_lp
        remaining_in_lp = max(0, net_lp_contribution * (lp_current_balance / (lp_current_balance + net_lp_contribution)))
        
        net_from_origin = received_from_origin - sent_to_origin
        net_transferred_to_lp = sent_to_lp - received_from_lp - remaining_in_lp
        
        return {
            'tokens_received_from_origin': received_from_origin,
            'tokens_sent_to_origin': sent_to_origin,
            'net_from_origin': net_from_origin,
            'tokens_sent_to_lp': sent_to_lp,
            'tokens_received_from_lp': received_from_lp,
            'tokens_still_in_lp': remaining_in_lp,
            'net_transferred_to_lp': net_transferred_to_lp,
            'current_wallet_balance': current_balance,
            'final_calculation': net_from_origin - net_transferred_to_lp,
            'total_transactions_processed': len(transactions)
        }

    def check_nft_mints(target_wallet, name_keywords, token_contract_address, api_key):
        """
        Check for NFT mints paid with ERC-20 token burns
        Returns: (minted: bool, total_amount_paid: float)
        """

        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': token_contract_address,
            'address': target_wallet,
            'startblock': 0,
            'endblock': 99999999,
            'sort': 'asc',
            'page': 1,
            'offset': 10000,
            'apikey': api_key
        }
        
        response = requests.get("https://api.etherscan.io/v2/api?chainid=42161", params=params)
        data = response.json()
        
        if data['status'] != '1':
            print(f"API Error: {data.get('message')}")
            return False, 0.0

        nft_params = {
            'module': 'account',
            'action': 'tokennfttx',
            'address': target_wallet,
            'startblock': 0,
            'endblock': 99999999,
            'sort': 'asc',
            'page': 1,
            'offset': 10000,
            'apikey': api_key
        }
        
        nft_response = requests.get("https://api.etherscan.io/v2/api?chainid=42161", params=nft_params)
        nft_data = nft_response.json()
        
        keywords = [kw.lower() for kw in name_keywords]
        total_paid = 0.0
        minted = False
        
        if nft_data['status'] == '1':
            for nft_tx in nft_data['result']:
                if (nft_tx['to'].lower() == target_wallet.lower() and
                    nft_tx['from'] == '0x0000000000000000000000000000000000000000'):
                    
                    tx_name = nft_tx.get('tokenName', '').lower()
                    if any(kw in tx_name for kw in keywords):
                        minted = True
                        
                        for token_tx in data['result']:
                            if (abs(int(token_tx['blockNumber']) - int(nft_tx['blockNumber'])) <= 5 and
                                token_tx['from'].lower() == target_wallet.lower()):
                                
                                value = int(token_tx.get('value', 0))
        
                                decimals = int(token_tx.get('tokenDecimal', 18))
                                total_paid += value / (10 ** decimals)
        
        return minted, total_paid

    ORIGIN_WALLET = "0x439ceE4cC4EcBD75DC08D9a17E92bDdCc11CDb8C"
    TOKEN_CONTRACT = "0xF42e2B8bc2aF8B110b65be98dB1321B1ab8D44f5"
    LP_ADDRESS = "0x65f7a98D87BC21A3748545047632FEf4d3Ff9a67"

    transactions = get_transactions(TARGET_WALLET, ORIGIN_WALLET, ETHERSCAN_API_KEY)

    _, membership = check_nft_mints(
        target_wallet=TARGET_WALLET,
        name_keywords=["EthTrader", "Special","Membership"],
        token_contract_address=TOKEN_CONTRACT,
        api_key=ETHERSCAN_API_KEY
    )

    results = analyze_token_flows(
        target_wallet=TARGET_WALLET,
        origin_wallet=ORIGIN_WALLET,
        token_contract_address=TOKEN_CONTRACT,
        lp_address=LP_ADDRESS,
        api_key=ETHERSCAN_API_KEY
    )

    earned = results['tokens_received_from_origin']
    current_balance = results['current_wallet_balance']
    sent_to_lp = results['tokens_sent_to_lp']
    net_lp = results['net_transferred_to_lp']

    if net_lp < 0:
        net_lp = 0

    if earned > 0:
        ratio = 100*(1 - (current_balance + net_lp + membership) / earned)
    else:
        ratio = 25
    
    if ratio < 0:
        ratio = 0

    def compute_multiplier(x):
        if x <= 25:
            return 1
        else:
            return -0.012 * x + 1.3

    def need_to_buy(current_balance, earned, lp, membership):
        c = 0.6*earned - (current_balance+lp+membership)
        if c and c < 0:
            return 0
        else:
            return 0.6*earned - (current_balance+lp+membership)
    
    need_to_buy = need_to_buy(current_balance, earned, net_lp, membership)

    if not transactions: 
        multiplier = 1.0
    else:
        multiplier = compute_multiplier(ratio)

    return multiplier, need_to_buy, current_balance, earned, sent_to_lp, membership
