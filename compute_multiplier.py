# Add your etherscan API Key to a .env file in the same directory of this function containing the line below (without #):
# ETHERSCAN_API_KEY = YOUR_KEY
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

    ORIGIN_WALLET = "0x439ceE4cC4EcBD75DC08D9a17E92bDdCc11CDb8C"
    TOKEN_CONTRACT = "0xF42e2B8bc2aF8B110b65be98dB1321B1ab8D44f5"
    LP_ADDRESS = "0x65f7a98D87BC21A3748545047632FEf4d3Ff9a67"

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
        Get all ERC-20 transfers to target_wallet from origin_wallet on Arbitrum One
        using the official Arbiscan API endpoint.
        """
        ARBISCAN_API_URL = "https://api.etherscan.io/v2/api?chainid=42161"
        
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': target_wallet,
            'startblock': 0,
            'endblock': 99999999,
            'sort': 'asc',
            'page': 1,
            'offset': 100,
            'apikey': api_key
        }
        
        response = requests.get(ARBISCAN_API_URL, params=params)
        data = response.json()
        
        if data['status'] != '1':
            print(f"API Error: {data.get('message')}")
            return []
        
        return [
            tx for tx in data['result']
            if tx['from'].lower() == origin_wallet.lower()
        ]

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
        df['token_value'] = df['value'] / (10**18)  # Assuming 18 decimals
        
    
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
        Analyze token flows between wallets and LP using Etherscan API v2
        Returns comprehensive token flow metrics
        """
        transactions = get_transactions(target_wallet, origin_wallet, api_key)    
        decimals = get_token_decimals(token_contract_address)
        
        received_from_origin = 0
        sent_to_origin = 0
        sent_to_lp = 0
        received_from_lp = 0
        
        for tx in transactions:
            if tx['contractAddress'].lower() != token_contract_address.lower():
                continue
                
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
                
            # Received from LP (e.g., removing liquidity)
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

    def check_nft_mints(transactions, target_wallet, name_keywords, token_contract_address):
        """
        Args:
            name_keywords: List of words that should appear in NFT name (case insensitive)
        Returns:
            tuple: (minted: bool, total_amount_paid: float)
        """
        total = 0.0
        minted = False
        keywords = [kw.lower() for kw in name_keywords]
        
        for tx in transactions:
            if (tx['to'].lower() == target_wallet.lower() and
                tx['from'] == '0x0000000000000000000000000000000000000000'):
                
                # Check if all keywords are in NFT name
                tx_name = tx.get('tokenName', '').lower()
                if all(kw in tx_name for kw in keywords):
                    minted = True
                    for internal_tx in tx.get('internalTransactions', []):
                        if (internal_tx.get('contractAddress', '').lower() == token_contract_address.lower()):
                            total += int(internal_tx.get('value', 0)) / (10 ** int(tx.get('tokenDecimal', 18)))
        
        return minted, total

    transaction_flow = analyze_token_flows(
            target_wallet=TARGET_WALLET,
            origin_wallet=ORIGIN_WALLET,
            token_contract_address=TOKEN_CONTRACT,
            lp_address=LP_ADDRESS,
            api_key=ETHERSCAN_API_KEY
        )

    _, membership = check_nft_mints(
        transactions=get_transactions(TARGET_WALLET, ORIGIN_WALLET, ETHERSCAN_API_KEY),
        target_wallet=TARGET_WALLET,
        name_keywords=["EthTrader", "Special","Membership"],
        token_contract_address=TOKEN_CONTRACT
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

    ratio = 100*(1 - (current_balance + sent_to_lp + membership) / earned)

    def compute_multiplier(x):
        if x < 25:
            return 1
        else:
            return -0.012 * x + 1.3

    multiplier = compute_multiplier(ratio)

    return multiplier

# To use this function to add a multiplier column to a round_XXX.csv file, uncomment the lines below.

# dist_data = pd.read_csv(PATH_TO_FILE)
# multipliers = []
#for i in range(0,len(dist_data)):
#  multipliers.append(get_multiplier(data['blockchain_address'][i])
#dist_data['multipliers'] = multipliers
