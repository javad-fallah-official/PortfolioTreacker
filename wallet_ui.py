#!/usr/bin/env python3
"""
Simple Web UI for Wallex Wallet Balance Display
"""

import os
import json
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
from wallex import WallexClient
from wallex.exceptions import WallexError, WallexAuthenticationError

# Load environment variables
load_dotenv()

app = Flask(__name__)

def get_wallet_data():
    """Fetch wallet data from Wallex API"""
    api_key = os.getenv('WALLEX_API_KEY')
    
    if not api_key:
        return {'error': 'API key not found in .env file'}
    
    try:
        client = WallexClient(api_key=api_key)
        
        # Get account info
        account_info = client.get_account_info()
        
        # Get balances
        balances = client.get_balances()
        
        if not balances.get('success'):
            return {'error': 'Failed to fetch balances'}
        
        # Process balance data
        wallet_data = {
            'account': {
                'email': account_info.get('result', {}).get('email', 'N/A'),
                'verified': account_info.get('result', {}).get('is_verified', False),
                'two_factor': account_info.get('result', {}).get('two_factor_enabled', False)
            },
            'balances': [],
            'total_assets': 0,
            'non_zero_assets': 0
        }
        
        # Process each balance
        for asset_name, balance_data in balances['result'].items():
            if isinstance(balance_data, dict):
                free = float(balance_data.get('value', 0))
                locked = float(balance_data.get('locked', 0))
                total = free + locked
                
                wallet_data['total_assets'] += 1
                
                if total > 0:
                    wallet_data['non_zero_assets'] += 1
                
                wallet_data['balances'].append({
                    'asset': balance_data.get('asset', asset_name),
                    'name': balance_data.get('faName', asset_name),
                    'free': free,
                    'locked': locked,
                    'total': total,
                    'icon': balance_data.get('asset_svg_icon', ''),
                    'is_fiat': balance_data.get('fiat', False),
                    'has_balance': total > 0
                })
        
        # Sort by total balance (descending) and then by asset name
        wallet_data['balances'].sort(key=lambda x: (-x['total'], x['asset']))
        
        return wallet_data
        
    except WallexAuthenticationError:
        return {'error': 'Authentication failed. Please check your API key.'}
    except WallexError as e:
        return {'error': f'Wallex API error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}

@app.route('/')
def index():
    """Main wallet dashboard"""
    return render_template('wallet.html')

@app.route('/api/wallet')
def api_wallet():
    """API endpoint for wallet data"""
    return jsonify(get_wallet_data())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)