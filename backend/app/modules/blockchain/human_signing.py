"""Pure primitives shared by the human-controlled wallet signing flow."""

from datetime import datetime
from uuid import UUID

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3


def normalize_wallet_address(address: str) -> str | None:
    """Return the canonical checksum address, or ``None`` for invalid input."""
    candidate = address.strip()
    if not Web3.is_address(candidate):
        return None
    return Web3.to_checksum_address(candidate)


def build_wallet_challenge_message(
    *,
    user_id: UUID,
    wallet_address: str,
    chain_id: int,
    nonce: str,
    expires_at: datetime,
) -> str:
    """Create a domain-specific, expiring ownership assertion for one wallet."""
    address = normalize_wallet_address(wallet_address)
    if address is None:
        raise ValueError("Wallet address is invalid.")
    if not nonce.strip():
        raise ValueError("Wallet challenge nonce is required.")
    if expires_at.tzinfo is None:
        raise ValueError("Wallet challenge expiry must include a timezone.")
    return "\n".join(
        (
            "THV Wallet Verification",
            "Purpose: Link this wallet to your THV signing account.",
            f"User: {user_id}",
            f"Wallet: {address}",
            f"Chain ID: {chain_id}",
            f"Nonce: {nonce}",
            f"Expires: {expires_at.isoformat()}",
            "This message does not authorize a blockchain transaction.",
        )
    )


def recover_wallet_address(message: str, signature: str) -> str | None:
    """Recover an EIP-191 signer without persisting the submitted signature."""
    try:
        address = Account.recover_message(
            encode_defunct(text=message),
            signature=signature,
        )
    except (TypeError, ValueError):
        return None
    return normalize_wallet_address(address)
