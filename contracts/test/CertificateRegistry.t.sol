// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import { CertificateRegistry } from "../src/CertificateRegistry.sol";

interface Vm {
    function assume(bool condition) external;
    function expectRevert() external;
    function expectRevert(bytes calldata revertData) external;
    function prank(address sender) external;
}

contract CertificateRegistryTest {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    CertificateRegistry private registry;
    address private constant ISSUER = address(0xBEEF);
    address private constant STRANGER = address(0xCAFE);
    bytes32 private constant CERTIFICATE_ID = keccak256("certificate-1");
    bytes32 private constant DOSSIER_HASH = keccak256("dossier-1");
    bytes32 private constant METADATA_HASH = keccak256("metadata-1");
    bytes32 private constant EVIDENCE_KEY = keccak256("document-evidence-1");
    bytes32 private constant EVIDENCE_COMMITMENT = keccak256("document-commitment-1");

    function setUp() public {
        registry = new CertificateRegistry(address(this));
        registry.grantIssuer(ISSUER);
    }

    function testIssuerCanIssueUpdateAndRevoke() public {
        vm.prank(ISSUER);
        registry.issueCertificate(CERTIFICATE_ID, DOSSIER_HASH, METADATA_HASH, 100, 200);

        vm.prank(ISSUER);
        registry.updateCertificate(
            CERTIFICATE_ID, keccak256("dossier-2"), keccak256("metadata-2"), 2
        );

        vm.prank(ISSUER);
        registry.revokeCertificate(CERTIFICATE_ID, keccak256("superseded"));

        CertificateRegistry.CertificateRecord memory record =
            registry.getCertificate(CERTIFICATE_ID);
        require(record.version == 2, "version");
        require(record.revoked, "revoked");
    }

    function testDuplicateIssueReverts() public {
        vm.prank(ISSUER);
        registry.issueCertificate(CERTIFICATE_ID, DOSSIER_HASH, METADATA_HASH, 100, 200);

        vm.expectRevert(
            abi.encodeWithSelector(
                CertificateRegistry.CertificateAlreadyExists.selector, CERTIFICATE_ID
            )
        );
        vm.prank(ISSUER);
        registry.issueCertificate(CERTIFICATE_ID, DOSSIER_HASH, METADATA_HASH, 100, 200);
    }

    function testUnauthorizedWriterReverts() public {
        vm.expectRevert();
        vm.prank(STRANGER);
        registry.issueCertificate(CERTIFICATE_ID, DOSSIER_HASH, METADATA_HASH, 100, 200);
    }

    function testPauseBlocksWritesButNotReads() public {
        vm.prank(ISSUER);
        registry.issueCertificate(CERTIFICATE_ID, DOSSIER_HASH, METADATA_HASH, 100, 200);
        registry.pause();
        vm.expectRevert();
        vm.prank(ISSUER);
        registry.issueCertificate(keccak256("certificate-2"), DOSSIER_HASH, METADATA_HASH, 100, 200);

        registry.getCertificate(CERTIFICATE_ID);
    }

    function testFuzzVersionMustStrictlyIncrease(uint32 nextVersion) public {
        vm.assume(nextVersion <= 1);
        vm.prank(ISSUER);
        registry.issueCertificate(CERTIFICATE_ID, DOSSIER_HASH, METADATA_HASH, 100, 200);

        vm.expectRevert(
            abi.encodeWithSelector(
                CertificateRegistry.VersionNotIncreasing.selector, 1, nextVersion
            )
        );
        vm.prank(ISSUER);
        registry.updateCertificate(CERTIFICATE_ID, DOSSIER_HASH, METADATA_HASH, nextVersion);
    }

    function testRevokedCertificateCannotBeUpdated() public {
        vm.prank(ISSUER);
        registry.issueCertificate(CERTIFICATE_ID, DOSSIER_HASH, METADATA_HASH, 100, 200);
        vm.prank(ISSUER);
        registry.revokeCertificate(CERTIFICATE_ID, keccak256("revoked"));

        vm.expectRevert(
            abi.encodeWithSelector(
                CertificateRegistry.CertificateIsRevoked.selector, CERTIFICATE_ID
            )
        );
        vm.prank(ISSUER);
        registry.updateCertificate(CERTIFICATE_ID, DOSSIER_HASH, METADATA_HASH, 2);
    }

    function testIssuerCanAnchorAndVerifyDocumentEvidence() public {
        vm.prank(ISSUER);
        registry.anchorDocumentEvidence(
            EVIDENCE_KEY, EVIDENCE_COMMITMENT, bytes32(0), 1, 1_700_000_000
        );

        CertificateRegistry.DocumentEvidenceRecord memory record =
            registry.getDocumentEvidence(EVIDENCE_KEY);
        require(record.commitment == EVIDENCE_COMMITMENT, "commitment");
        require(record.previousEvidenceKey == bytes32(0), "predecessor");
        require(record.version == 1, "version");
        require(record.recordedAt == 1_700_000_000, "recordedAt");
        require(registry.verifyDocumentEvidence(EVIDENCE_KEY, EVIDENCE_COMMITMENT), "verification");
        require(
            !registry.verifyDocumentEvidence(EVIDENCE_KEY, keccak256("modified")),
            "modified bytes must not verify"
        );
    }

    function testDocumentEvidenceIsAppendOnlyAndVersioned() public {
        bytes32 nextKey = keccak256("document-evidence-2");
        vm.prank(ISSUER);
        registry.anchorDocumentEvidence(
            EVIDENCE_KEY, EVIDENCE_COMMITMENT, bytes32(0), 1, 1_700_000_000
        );
        vm.prank(ISSUER);
        registry.anchorDocumentEvidence(
            nextKey, keccak256("document-commitment-2"), EVIDENCE_KEY, 2, 1_700_000_100
        );

        vm.expectRevert(
            abi.encodeWithSelector(
                CertificateRegistry.DocumentEvidenceAlreadyExists.selector, EVIDENCE_KEY
            )
        );
        vm.prank(ISSUER);
        registry.anchorDocumentEvidence(
            EVIDENCE_KEY, keccak256("replacement"), bytes32(0), 1, 1_700_000_200
        );

        vm.expectRevert(
            abi.encodeWithSelector(
                CertificateRegistry.DocumentEvidencePredecessorUsed.selector, EVIDENCE_KEY
            )
        );
        vm.prank(ISSUER);
        registry.anchorDocumentEvidence(
            keccak256("fork"), keccak256("fork-commitment"), EVIDENCE_KEY, 2, 1_700_000_300
        );
    }

    function testDocumentEvidenceRejectsInvalidLineageAndUnauthorizedWriter() public {
        vm.expectRevert();
        vm.prank(STRANGER);
        registry.anchorDocumentEvidence(
            EVIDENCE_KEY, EVIDENCE_COMMITMENT, bytes32(0), 1, 1_700_000_000
        );

        vm.expectRevert(
            abi.encodeWithSelector(
                CertificateRegistry.InvalidDocumentEvidenceLineage.selector, uint32(2), bytes32(0)
            )
        );
        vm.prank(ISSUER);
        registry.anchorDocumentEvidence(
            EVIDENCE_KEY, EVIDENCE_COMMITMENT, bytes32(0), 2, 1_700_000_000
        );
    }
}
