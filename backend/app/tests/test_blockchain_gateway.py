import asyncio
import json
import os
from pathlib import Path

import pytest
from web3 import AsyncHTTPProvider, AsyncWeb3, Web3

from app.modules.blockchain.gateway import BlockchainGateway

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ABI_PATH = REPOSITORY_ROOT / "contracts" / "artifacts" / "CertificateRegistry.abi.json"
MANIFEST_PATH = REPOSITORY_ROOT / "contracts" / "deployments" / "local.json"


def test_gateway_encodes_registry_write_calls() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    gateway = BlockchainGateway(
        rpc_url="http://127.0.0.1:8545",
        network="local",
        chain_id=31_337,
        contract_address=manifest["certificateRegistry"],
        abi_path=ABI_PATH,
        allowed_networks={"local": 31_337},
        allowed_contracts={"local": {manifest["certificateRegistry"]}},
    )

    payload = gateway.encode_issue_certificate(
        certificate_id=b"\x01" * 32,
        dossier_hash=b"\x02" * 32,
        metadata_hash=b"\x03" * 32,
        issued_at=100,
        expires_at=200,
    )

    assert (
        payload[:4]
        == Web3.keccak(text="issueCertificate(bytes32,bytes32,bytes32,uint64,uint64)")[
            :4
        ]
    )

    evidence_payload = gateway.encode_anchor_document_evidence(
        evidence_key=b"\x04" * 32,
        commitment=b"\x05" * 32,
        previous_evidence_key=b"\x00" * 32,
        version=1,
        recorded_at=1_700_000_000,
    )
    assert evidence_payload[:4] == Web3.keccak(
        text="anchorDocumentEvidence(bytes32,bytes32,bytes32,uint32,uint64)"
    )[:4]


@pytest.mark.skipif(
    os.getenv("BLOCKCHAIN_INTEGRATION") != "1",
    reason="Anvil integration is opt-in.",
)
def test_gateway_reads_certificate_from_anvil() -> None:
    async def exercise() -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        address = manifest["certificateRegistry"]
        abi = json.loads(ABI_PATH.read_text(encoding="utf-8"))
        web3 = AsyncWeb3(AsyncHTTPProvider("http://127.0.0.1:8545"))
        account = (await web3.eth.accounts)[0]
        contract = web3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=abi,
        )
        certificate_id = Web3.keccak(text="gateway-integration")
        transaction_hash = await contract.functions.issueCertificate(
            certificate_id,
            Web3.keccak(text="dossier"),
            Web3.keccak(text="metadata"),
            100,
            200,
        ).transact({"from": account})
        await web3.eth.wait_for_transaction_receipt(transaction_hash)

        gateway = BlockchainGateway(
            rpc_url="http://127.0.0.1:8545",
            network="local",
            chain_id=31_337,
            contract_address=address,
            abi_path=ABI_PATH,
            allowed_networks={"local": 31_337},
            allowed_contracts={"local": {address}},
        )
        record = await gateway.get_certificate(bytes(certificate_id))

        assert record.version == 1
        assert record.issued_at == 100
        assert not record.revoked

        evidence_key = Web3.keccak(text="gateway-document-evidence")
        commitment = Web3.keccak(text="gateway-document-commitment")
        evidence_tx = await contract.functions.anchorDocumentEvidence(
            evidence_key,
            commitment,
            bytes(32),
            1,
            1_700_000_000,
        ).transact({"from": account})
        await web3.eth.wait_for_transaction_receipt(evidence_tx)
        evidence = await gateway.get_document_evidence(bytes(evidence_key))

        assert evidence.commitment == bytes(commitment)
        assert evidence.version == 1
        assert await gateway.verify_document_evidence(
            evidence_key=bytes(evidence_key),
            commitment=bytes(commitment),
        )
        assert not await gateway.verify_document_evidence(
            evidence_key=bytes(evidence_key),
            commitment=bytes(Web3.keccak(text="modified")),
        )

    asyncio.run(exercise())
