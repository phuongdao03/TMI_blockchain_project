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
}
