// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import { AccessControl } from "@openzeppelin/contracts/access/AccessControl.sol";
import { Pausable } from "@openzeppelin/contracts/utils/Pausable.sol";

contract CertificateRegistry is AccessControl, Pausable {
    bytes32 public constant ISSUER_ROLE = keccak256("ISSUER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    struct CertificateRecord {
        bytes32 dossierHash;
        bytes32 metadataHash;
        bytes32 revocationReasonHash;
        uint64 issuedAt;
        uint64 expiresAt;
        uint32 version;
        bool revoked;
    }

    struct DocumentEvidenceRecord {
        bytes32 commitment;
        bytes32 previousEvidenceKey;
        uint64 recordedAt;
        uint32 version;
    }

    error CertificateAlreadyExists(bytes32 certificateId);
    error CertificateNotFound(bytes32 certificateId);
    error CertificateIsRevoked(bytes32 certificateId);
    error VersionNotIncreasing(uint32 currentVersion, uint32 requestedVersion);
    error DocumentEvidenceAlreadyExists(bytes32 evidenceKey);
    error DocumentEvidenceNotFound(bytes32 evidenceKey);
    error DocumentEvidencePredecessorUsed(bytes32 evidenceKey);
    error InvalidDocumentEvidence();
    error InvalidDocumentEvidenceLineage(uint32 version, bytes32 previousEvidenceKey);
    error InvalidAdministrator();

    event CertificateIssued(
        bytes32 indexed certificateId,
        bytes32 indexed dossierHash,
        bytes32 metadataHash,
        uint64 issuedAt,
        uint64 expiresAt
    );
    event CertificateUpdated(
        bytes32 indexed certificateId,
        bytes32 indexed dossierHash,
        bytes32 metadataHash,
        uint32 version
    );
    event CertificateRevoked(bytes32 indexed certificateId, bytes32 indexed reasonHash);
    event IssuerGranted(address indexed issuer, address indexed grantedBy);
    event IssuerRevoked(address indexed issuer, address indexed revokedBy);
    event DocumentEvidenceAnchored(
        bytes32 indexed evidenceKey,
        bytes32 indexed commitment,
        bytes32 indexed previousEvidenceKey,
        uint32 version,
        uint64 recordedAt
    );

    mapping(bytes32 certificateId => CertificateRecord record) private _certificates;
    mapping(bytes32 evidenceKey => DocumentEvidenceRecord record) private _documentEvidence;
    mapping(bytes32 evidenceKey => bytes32 successorKey) private _documentEvidenceSuccessor;

    constructor(address administrator) {
        if (administrator == address(0)) revert InvalidAdministrator();
        _grantRole(DEFAULT_ADMIN_ROLE, administrator);
        _grantRole(PAUSER_ROLE, administrator);
    }

    function issueCertificate(
        bytes32 certificateId,
        bytes32 dossierHash,
        bytes32 metadataHash,
        uint64 issuedAt,
        uint64 expiresAt
    ) external onlyRole(ISSUER_ROLE) whenNotPaused {
        if (_certificates[certificateId].version != 0) {
            revert CertificateAlreadyExists(certificateId);
        }
        _certificates[certificateId] = CertificateRecord({
            dossierHash: dossierHash,
            metadataHash: metadataHash,
            revocationReasonHash: bytes32(0),
            issuedAt: issuedAt,
            expiresAt: expiresAt,
            version: 1,
            revoked: false
        });
        emit CertificateIssued(certificateId, dossierHash, metadataHash, issuedAt, expiresAt);
    }

    function updateCertificate(
        bytes32 certificateId,
        bytes32 dossierHash,
        bytes32 metadataHash,
        uint32 version
    ) external onlyRole(ISSUER_ROLE) whenNotPaused {
        CertificateRecord storage record = _requiredCertificate(certificateId);
        if (record.revoked) revert CertificateIsRevoked(certificateId);
        if (version <= record.version) {
            revert VersionNotIncreasing(record.version, version);
        }
        record.dossierHash = dossierHash;
        record.metadataHash = metadataHash;
        record.version = version;
        emit CertificateUpdated(certificateId, dossierHash, metadataHash, version);
    }

    function revokeCertificate(bytes32 certificateId, bytes32 reasonHash)
        external
        onlyRole(ISSUER_ROLE)
        whenNotPaused
    {
        CertificateRecord storage record = _requiredCertificate(certificateId);
        if (record.revoked) revert CertificateIsRevoked(certificateId);
        record.revoked = true;
        record.revocationReasonHash = reasonHash;
        emit CertificateRevoked(certificateId, reasonHash);
    }

    function getCertificate(bytes32 certificateId)
        external
        view
        returns (CertificateRecord memory)
    {
        CertificateRecord storage record = _requiredCertificate(certificateId);
        return record;
    }

    function anchorDocumentEvidence(
        bytes32 evidenceKey,
        bytes32 commitment,
        bytes32 previousEvidenceKey,
        uint32 version,
        uint64 recordedAt
    ) external onlyRole(ISSUER_ROLE) whenNotPaused {
        if (evidenceKey == bytes32(0) || commitment == bytes32(0) || recordedAt == 0) {
            revert InvalidDocumentEvidence();
        }
        if (_documentEvidence[evidenceKey].version != 0) {
            revert DocumentEvidenceAlreadyExists(evidenceKey);
        }
        if (version == 1) {
            if (previousEvidenceKey != bytes32(0)) {
                revert InvalidDocumentEvidenceLineage(version, previousEvidenceKey);
            }
        } else {
            DocumentEvidenceRecord storage predecessor = _documentEvidence[previousEvidenceKey];
            if (
                previousEvidenceKey == bytes32(0) || predecessor.version == 0
                    || predecessor.version + 1 != version
            ) {
                revert InvalidDocumentEvidenceLineage(version, previousEvidenceKey);
            }
            if (_documentEvidenceSuccessor[previousEvidenceKey] != bytes32(0)) {
                revert DocumentEvidencePredecessorUsed(previousEvidenceKey);
            }
            _documentEvidenceSuccessor[previousEvidenceKey] = evidenceKey;
        }
        _documentEvidence[evidenceKey] = DocumentEvidenceRecord({
            commitment: commitment,
            previousEvidenceKey: previousEvidenceKey,
            recordedAt: recordedAt,
            version: version
        });
        emit DocumentEvidenceAnchored(
            evidenceKey, commitment, previousEvidenceKey, version, recordedAt
        );
    }

    function getDocumentEvidence(bytes32 evidenceKey)
        external
        view
        returns (DocumentEvidenceRecord memory)
    {
        DocumentEvidenceRecord storage record = _documentEvidence[evidenceKey];
        if (record.version == 0) revert DocumentEvidenceNotFound(evidenceKey);
        return record;
    }

    function verifyDocumentEvidence(bytes32 evidenceKey, bytes32 commitment)
        external
        view
        returns (bool)
    {
        DocumentEvidenceRecord storage record = _documentEvidence[evidenceKey];
        return record.version != 0 && record.commitment == commitment;
    }

    function grantIssuer(address issuer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (_grantRole(ISSUER_ROLE, issuer)) {
            emit IssuerGranted(issuer, msg.sender);
        }
    }

    function revokeIssuer(address issuer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (_revokeRole(ISSUER_ROLE, issuer)) {
            emit IssuerRevoked(issuer, msg.sender);
        }
    }

    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    function _requiredCertificate(bytes32 certificateId)
        private
        view
        returns (CertificateRecord storage record)
    {
        record = _certificates[certificateId];
        if (record.version == 0) revert CertificateNotFound(certificateId);
    }
}
