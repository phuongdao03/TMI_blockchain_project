// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { AccessControl } from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title THVProofRegistry
/// @notice Append-only registry of approved THV asset proof hashes.
/// @dev Files, URLs, dossier data and personal data must remain off-chain.
contract THVProofRegistry is AccessControl {
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");

    struct Proof {
        bytes32 assetId;
        bytes32 proofHash;
        uint64 version;
        uint64 recordedAt;
        address signer;
        bool exists;
    }

    error InvalidAdministrator();
    error InvalidVerifier();
    error RoleSeparationRequired();
    error InvalidAssetId();
    error InvalidProofHash();
    error InvalidVersion();
    error ProofAlreadyRecorded(bytes32 assetId, uint64 version);

    event ProofRecorded(
        bytes32 indexed assetId,
        bytes32 indexed proofHash,
        uint64 indexed version,
        address signer,
        uint64 timestamp
    );

    mapping(bytes32 assetId => mapping(uint64 version => Proof proof)) private _proofs;

    /// @notice Creates a registry with separated governance and proof-recording roles.
    /// @param administrator Holder of DEFAULT_ADMIN_ROLE.
    /// @param signer Initial holder of VERIFIER_ROLE; it never receives admin access here.
    constructor(address administrator, address signer) {
        if (administrator == address(0)) revert InvalidAdministrator();
        if (signer == address(0)) revert InvalidVerifier();
        if (administrator == signer) revert RoleSeparationRequired();

        _grantRole(DEFAULT_ADMIN_ROLE, administrator);
        _grantRole(VERIFIER_ROLE, signer);
    }

    /// @notice Stores a new immutable proof for an asset version.
    /// @dev A later change must use a new version. Existing versions can never be overwritten.
    function recordProof(bytes32 assetId, bytes32 proofHash, uint64 version)
        external
        onlyRole(VERIFIER_ROLE)
    {
        if (assetId == bytes32(0)) revert InvalidAssetId();
        if (proofHash == bytes32(0)) revert InvalidProofHash();
        if (version == 0) revert InvalidVersion();
        if (_proofs[assetId][version].exists) {
            revert ProofAlreadyRecorded(assetId, version);
        }

        uint64 timestamp = uint64(block.timestamp);
        _proofs[assetId][version] = Proof({
            assetId: assetId,
            proofHash: proofHash,
            version: version,
            recordedAt: timestamp,
            signer: msg.sender,
            exists: true
        });

        emit ProofRecorded(assetId, proofHash, version, msg.sender, timestamp);
    }

    /// @notice Returns a proof record, or an all-zero record with `exists == false` if absent.
    function getProof(bytes32 assetId, uint64 version) external view returns (Proof memory) {
        return _proofs[assetId][version];
    }

    /// @notice Checks that a stored proof exists and matches an expected hash exactly.
    function verifyProof(bytes32 assetId, uint64 version, bytes32 expectedHash)
        external
        view
        returns (bool)
    {
        Proof storage proof = _proofs[assetId][version];
        return proof.exists && proof.proofHash == expectedHash;
    }
}
