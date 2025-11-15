"""
ZecKit Faucet - Zebra RPC Client
Wrapper for making JSON-RPC calls to Zebra node
"""
import requests
from typing import Dict, List, Optional, Any, Union
import logging
from requests.auth import HTTPBasicAuth


logger = logging.getLogger(__name__)


class ZebraRPCError(Exception):
    """Exception raised for Zebra RPC errors"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"RPC Error {code}: {message}")


class ZebraRPCClient:
    """
    Client for interacting with Zebra node via JSON-RPC
    
    Usage:
        client = ZebraRPCClient("http://127.0.0.1:8232")
        info = client.get_blockchain_info()
        balance = client.get_balance()
    """
    
    def __init__(
        self,
        url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize RPC client
        
        Args:
            url: Zebra RPC endpoint (e.g., http://127.0.0.1:8232)
            username: Optional RPC username
            password: Optional RPC password
            timeout: Request timeout in seconds
        """
        self.url = url
        self.timeout = timeout
        self.auth = HTTPBasicAuth(username, password) if username and password else None
        self._request_id = 0
    
    def _call(self, method: str, params: Optional[List] = None) -> Any:
        """
        Make a JSON-RPC call to Zebra
        
        Args:
            method: RPC method name
            params: Method parameters (default: [])
        
        Returns:
            RPC result
        
        Raises:
            ZebraRPCError: If RPC returns an error
            requests.exceptions.RequestException: If connection fails
        """
        if params is None:
            params = []
        
        self._request_id += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": str(self._request_id),
            "method": method,
            "params": params
        }
        
        logger.debug(f"RPC call: {method} {params}")
        
        try:
            response = requests.post(
                self.url,
                json=payload,
                auth=self.auth,
                timeout=self.timeout,
                headers={"content-type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data and data["error"] is not None:
                error = data["error"]
                raise ZebraRPCError(
                    code=error.get("code", -1),
                    message=error.get("message", "Unknown error")
                )
            
            return data.get("result")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"RPC connection error: {e}")
            raise
    
    # ===== Node Information =====
    
    def get_info(self) -> Dict[str, Any]:
        """Get general node information"""
        return self._call("getinfo")
    
    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        return self._call("getblockchaininfo")
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        return self._call("getnetworkinfo")
    
    def get_block_count(self) -> int:
        """Get current block height"""
        return self._call("getblockcount")
    
    def get_best_block_hash(self) -> str:
        """Get hash of the best (tip) block"""
        return self._call("getbestblockhash")
    
    # ===== Wallet Operations =====
    
    def get_balance(self, minconf: int = 1) -> float:
        """
        Get wallet balance
        
        Args:
            minconf: Minimum confirmations (default: 1)
        
        Returns:
            Balance in ZEC
        """
        return self._call("z_getbalance", [minconf])
    
    def get_new_address(self, address_type: str = "transparent") -> str:
        """
        Generate a new address
        
        Args:
            address_type: "transparent", "sapling", or "unified"
        
        Returns:
            New address
        """
        if address_type == "transparent":
            return self._call("getnewaddress")
        elif address_type == "sapling":
            return self._call("z_getnewaddress", ["sapling"])
        elif address_type == "unified":
            return self._call("z_getnewaddress", ["unified"])
        else:
            raise ValueError(f"Invalid address type: {address_type}")
    
    def validate_address(self, address: str) -> Dict[str, Any]:
        """
        Validate an address
        
        Args:
            address: Address to validate
        
        Returns:
            Validation result with 'isvalid' field
        """
        # Try z_validateaddress first (handles all types in newer Zebra)
        try:
            return self._call("z_validateaddress", [address])
        except ZebraRPCError:
            # Fallback to validateaddress for transparent
            return self._call("validateaddress", [address])
    
    def send_to_address(
        self,
        address: str,
        amount: float,
        memo: Optional[str] = None,
        minconf: int = 1
    ) -> str:
        """
        Send ZEC to an address
        
        Args:
            address: Destination address
            amount: Amount in ZEC
            memo: Optional memo (for shielded addresses)
            minconf: Minimum confirmations for inputs
        
        Returns:
            Transaction ID (txid)
        """
        # For transparent addresses
        if address.startswith('t'):
            return self._call("sendtoaddress", [address, amount])
        
        # For shielded/unified addresses, use z_sendmany
        outputs = [{
            "address": address,
            "amount": amount
        }]
        if memo:
            outputs[0]["memo"] = memo
        
        # z_sendmany: [from_address, outputs, minconf, fee]
        # Use default from address (transparent)
        from_addr = self.get_new_address("transparent")
        return self._call("z_sendmany", [from_addr, outputs, minconf])
    
    def list_unspent(
        self,
        minconf: int = 1,
        maxconf: int = 9999999,
        addresses: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List unspent transaction outputs
        
        Args:
            minconf: Minimum confirmations
            maxconf: Maximum confirmations
            addresses: Optional list of addresses to filter
        
        Returns:
            List of unspent outputs
        """
        params = [minconf, maxconf]
        if addresses:
            params.append(addresses)
        return self._call("listunspent", params)
    
    # ===== Transaction Operations =====
    
    def get_transaction(self, txid: str) -> Dict[str, Any]:
        """
        Get transaction details
        
        Args:
            txid: Transaction ID
        
        Returns:
            Transaction details
        """
        return self._call("gettransaction", [txid])
    
    def get_raw_transaction(
        self,
        txid: str,
        verbose: bool = True
    ) -> Union[str, Dict[str, Any]]:
        """
        Get raw transaction
        
        Args:
            txid: Transaction ID
            verbose: If True, return decoded transaction; if False, return hex
        
        Returns:
            Raw transaction (hex or decoded)
        """
        return self._call("getrawtransaction", [txid, 1 if verbose else 0])
    
    # ===== Mining (Regtest Only) =====
    
    def generate(self, num_blocks: int, address: Optional[str] = None) -> List[str]:
        """
        Generate blocks (regtest only)
        
        Args:
            num_blocks: Number of blocks to generate
            address: Optional address to receive coinbase (default: miner address)
        
        Returns:
            List of generated block hashes
        """
        if address:
            return self._call("generatetoaddress", [num_blocks, address])
        return self._call("generate", [num_blocks])
    
    # ===== Health Checks =====
    
    def ping(self) -> bool:
        """
        Check if Zebra is responsive
        
        Returns:
            True if responsive, False otherwise
        """
        try:
            self.get_block_count()
            return True
        except Exception as e:
            logger.warning(f"Zebra ping failed: {e}")
            return False
    
    def is_synced(self, tolerance: int = 10) -> bool:
        """
        Check if Zebra is synced (for regtest, always True)
        
        Args:
            tolerance: Maximum block difference to consider synced
        
        Returns:
            True if synced
        """
        try:
            info = self.get_blockchain_info()
            chain = info.get("chain", "")
            
            # In regtest, we're always synced
            if chain.lower() in ["regtest", "test"]:
                return True
            
            # For mainnet/testnet, check headers vs blocks
            headers = info.get("headers", 0)
            blocks = info.get("blocks", 0)
            return abs(headers - blocks) <= tolerance
        
        except Exception as e:
            logger.warning(f"Sync check failed: {e}")
            return False