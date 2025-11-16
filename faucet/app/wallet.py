"""
ZecKit Faucet - Wallet Management
Simple wallet for managing faucet funds
"""
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import hashlib

from .zebra_rpc import ZebraRPCClient, ZebraRPCError

logger = logging.getLogger(__name__)


class FaucetWallet:
    """
    Simple wallet for faucet operations
    Manages a single transparent address and tracks transactions
    """
    
    def __init__(self, zebra_client: ZebraRPCClient, wallet_file: str = "/var/faucet/wallet.json"):
        """
        Initialize faucet wallet
        
        Args:
            zebra_client: Zebra RPC client
            wallet_file: Path to wallet state file
        """
        self.zebra_client = zebra_client
        self.wallet_file = wallet_file
        self.address = None
        self.created_at = None
        self.transaction_history: List[Dict[str, Any]] = []
        self.initial_balance: float = 0.0  # Track initial funding
        
        # Try to load existing wallet or create new
        if os.path.exists(wallet_file):
            self._load_wallet()
        else:
            self._create_wallet()
    
    def _load_wallet(self) -> bool:
        """
        Load wallet from file
        
        Returns:
            True if loaded successfully
        """
        try:
            logger.info(f"Loading wallet from {self.wallet_file}")
            with open(self.wallet_file, 'r') as f:
                data = json.load(f)
            
            self.address = data.get('address')
            self.created_at = data.get('created_at')
            self.transaction_history = data.get('transaction_history', [])
            self.initial_balance = data.get('initial_balance', 0.0)
            
            if not self.address:
                logger.error("Wallet file missing address")
                return False
            
            logger.info(f"✓ Wallet loaded: {self.address}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load wallet: {e}")
            return False
    
    def _create_wallet(self) -> bool:
        """
        Create new wallet
        
        Returns:
            True if created successfully
        """
        try:
            logger.info("Creating new faucet wallet")
            
            # Try to generate new address from Zebra
            try:
                self.address = self.zebra_client.get_new_address("transparent")
                logger.info(f"✓ Generated new address from Zebra: {self.address}")
            except Exception as e:
                logger.warning(f"Could not generate address from Zebra: {e}")
                logger.info("Using fallback regtest address")
                # Fallback: Use a known regtest address
                # This is safe for regtest only - never use in production
                self.address = "tmBsTi2xWTjUdEXnuTceL7fecEQKeWu4u6d"
            
            self.created_at = datetime.utcnow().isoformat() + "Z"
            self.transaction_history = []
            
            # Save to file
            self._save_wallet()
            
            logger.info(f"✓ New wallet created: {self.address}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create wallet: {e}")
            return False
    
    def _save_wallet(self) -> bool:
        """
        Save wallet to file
        
        Returns:
            True if saved successfully
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.wallet_file), exist_ok=True)
            
            data = {
                'address': self.address,
                'created_at': self.created_at,
                'initial_balance': self.initial_balance,
                'transaction_history': self.transaction_history[-1000:]  # Keep last 1000
            }
            
            with open(self.wallet_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to save wallet: {e}")
            return False
    
    def is_loaded(self) -> bool:
        """Check if wallet is loaded and ready"""
        return self.address is not None
    
    def get_address(self) -> Optional[str]:
        """Get faucet address"""
        return self.address
    
    def get_balance(self) -> float:
        """
        Get current balance
        
        Returns:
            Balance in ZEC
        """
        try:
            if not self.is_loaded():
                return 0.0
            
            # Calculate balance from initial funding minus sent transactions
            sent = sum(tx.get('amount', 0.0) for tx in self.transaction_history)
            balance = self.initial_balance - sent
            
            return max(0.0, balance)  # Never return negative
        
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0.0
    
    def add_funds(self, amount: float, txid: Optional[str] = None) -> bool:
        """
        Add funds to wallet (called when receiving funds)
        
        Args:
            amount: Amount received in ZEC
            txid: Optional transaction ID
        
        Returns:
            True if successful
        """
        try:
            self.initial_balance += amount
            logger.info(f"✓ Added {amount} ZEC to wallet. New balance: {self.get_balance()}")
            self._save_wallet()
            return True
        except Exception as e:
            logger.error(f"Failed to add funds: {e}")
            return False
    
    def send_funds(
        self,
        to_address: str,
        amount: float,
        memo: Optional[str] = None
    ) -> Optional[str]:
        """
        Send funds from faucet to address
        
        IMPORTANT: Zebra doesn't support wallet RPCs (sendtoaddress, etc.)
        For regtest/development, we simulate transactions
        
        Args:
            to_address: Destination address
            amount: Amount in ZEC
            memo: Optional memo (for shielded addresses)
        
        Returns:
            Transaction ID if successful, None otherwise
        """
        try:
            if not self.is_loaded():
                logger.error("Wallet not loaded")
                return None
            
            # Check balance
            balance = self.get_balance()
            if balance < amount:
                logger.error(f"Insufficient balance: {balance} < {amount}")
                return None
            
            # MOCK TRANSACTION MODE
            # Zebra doesn't have wallet RPCs - we simulate for dev/testing
            logger.info(f"Simulating send of {amount} ZEC to {to_address}")
            
            # Generate a mock TXID (deterministic but unique)
            mock_data = f"{to_address}{amount}{datetime.utcnow().isoformat()}"
            txid = hashlib.sha256(mock_data.encode()).hexdigest()
            
            logger.warning(f"⚠ MOCK TRANSACTION (Zebra has no wallet) - TXID: {txid}")
            
            # Record transaction
            tx_record = {
                'txid': txid,
                'to_address': to_address,
                'amount': amount,
                'timestamp': datetime.utcnow().isoformat() + "Z",
                'memo': memo,
                'mock': True  # Flag as simulated
            }
            self.transaction_history.append(tx_record)
            self._save_wallet()
            
            logger.info(f"✓ Simulated send of {amount} ZEC (mock txid: {txid[:16]}...)")
            return txid
        
        except Exception as e:
            logger.error(f"Failed to send funds: {e}")
            return None
    
    def get_transaction_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent transaction history
        
        Args:
            limit: Maximum number of transactions to return
        
        Returns:
            List of transaction records
        """
        return self.transaction_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get wallet statistics
        
        Returns:
            Dictionary with wallet stats
        """
        total_sent = sum(tx['amount'] for tx in self.transaction_history)
        
        return {
            'address': self.address,
            'created_at': self.created_at,
            'current_balance': self.get_balance(),
            'total_transactions': len(self.transaction_history),
            'total_sent': total_sent
        }