// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IAccessControl } from "@openzeppelin/contracts/access/IAccessControl.sol";
import { THVProofRegistry } from "../src/THVProofRegistry.sol";

interface VmProof {
    function expectEmit(bool checkTopic1, bool checkTopic2, bool checkTopic3, bool checkData)
        external;
    function expectRevert(bytes calldata revertData) external;
    function expectRevert(bytes4 revertData) external;
    function prank(address sender) external;
    function warp(uint256 newTimestamp) external;
}

contract THVProofRegistryTest {
    event ProofRecorded(
        bytes32 indexed assetId,
        bytes32 indexed proofHash,
        uint64 indexed version,
        address signer,
        uint64 timestamp
    );

    VmProof private constant vm = VmProof(address(uint160(uint256(keccak256("hevm cheat code")))));

    address private constant ADMIN = 0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe;
    address private constant SIGNER = 0xBfA38182f0D24589e7898DD4892C58c3FDa58042;
    address private constant NEW_SIGNER = address(0xb0b);
    address private constant RANDOM_WALLET = address(0xbeef);

    bytes32 private constant ASSET_ID = keccak256("THV-ASSET-001");
    bytes32 private constant PROOF_HASH_V1 = keccak256("THV-PROOF-V1");
    bytes32 private constant PROOF_HASH_V2 = keccak256("THV-PROOF-V2");

    THVProofRegistry private registry;

    function setUp() public {
        registry = new THVProofRegistry(ADMIN, SIGNER);
    }

    function testInitialAdminAndSignerRolesAreSeparated() public view {
        _assertTrue(
            registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), ADMIN),
            "administrator is missing admin role"
        );
        _assertTrue(
            !registry.hasRole(registry.VERIFIER_ROLE(), ADMIN),
            "administrator must not receive verifier role"
        );
        _assertTrue(
            registry.hasRole(registry.VERIFIER_ROLE(), SIGNER), "signer is missing verifier role"
        );
        _assertTrue(
            !registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), SIGNER),
            "signer must not receive admin role"
        );
    }

    function testSignerCanRecordProof() public {
        uint64 timestamp = 1_735_689_600;
        vm.warp(timestamp);
        vm.expectEmit(true, true, true, true);
        emit ProofRecorded(ASSET_ID, PROOF_HASH_V1, 1, SIGNER, timestamp);

        vm.prank(SIGNER);
        registry.recordProof(ASSET_ID, PROOF_HASH_V1, 1);

        THVProofRegistry.Proof memory proof = registry.getProof(ASSET_ID, 1);
        _assertProof(proof, ASSET_ID, PROOF_HASH_V1, 1, timestamp, SIGNER, true);
    }

    function testRandomWalletCannotRecordProof() public {
        vm.expectRevert(
            abi.encodeWithSelector(
                IAccessControl.AccessControlUnauthorizedAccount.selector,
                RANDOM_WALLET,
                registry.VERIFIER_ROLE()
            )
        );
        vm.prank(RANDOM_WALLET);
        registry.recordProof(ASSET_ID, PROOF_HASH_V1, 1);
    }

    function testRejectsZeroAssetId() public {
        vm.expectRevert(THVProofRegistry.InvalidAssetId.selector);
        vm.prank(SIGNER);
        registry.recordProof(bytes32(0), PROOF_HASH_V1, 1);
    }

    function testRejectsZeroProofHash() public {
        vm.expectRevert(THVProofRegistry.InvalidProofHash.selector);
        vm.prank(SIGNER);
        registry.recordProof(ASSET_ID, bytes32(0), 1);
    }

    function testRejectsVersionZero() public {
        vm.expectRevert(THVProofRegistry.InvalidVersion.selector);
        vm.prank(SIGNER);
        registry.recordProof(ASSET_ID, PROOF_HASH_V1, 0);
    }

    function testRejectsDuplicateAssetIdAndVersion() public {
        vm.prank(SIGNER);
        registry.recordProof(ASSET_ID, PROOF_HASH_V1, 1);

        vm.expectRevert(
            abi.encodeWithSelector(
                THVProofRegistry.ProofAlreadyRecorded.selector, ASSET_ID, uint64(1)
            )
        );
        vm.prank(SIGNER);
        registry.recordProof(ASSET_ID, PROOF_HASH_V2, 1);
    }

    function testRecordsV2AfterV1WithoutOverwritingV1() public {
        vm.prank(SIGNER);
        registry.recordProof(ASSET_ID, PROOF_HASH_V1, 1);
        vm.prank(SIGNER);
        registry.recordProof(ASSET_ID, PROOF_HASH_V2, 2);

        THVProofRegistry.Proof memory versionOne = registry.getProof(ASSET_ID, 1);
        THVProofRegistry.Proof memory versionTwo = registry.getProof(ASSET_ID, 2);
        _assertProof(versionOne, ASSET_ID, PROOF_HASH_V1, 1, versionOne.recordedAt, SIGNER, true);
        _assertProof(versionTwo, ASSET_ID, PROOF_HASH_V2, 2, versionTwo.recordedAt, SIGNER, true);
        _assertTrue(versionOne.proofHash != versionTwo.proofHash, "V1 was overwritten");
    }

    function testGetProofReturnsMissingRecordWithExistsFalse() public view {
        THVProofRegistry.Proof memory proof = registry.getProof(ASSET_ID, 44);
        _assertTrue(!proof.exists, "missing proof must be explicit");
        _assertTrue(proof.assetId == bytes32(0), "missing proof must remain zero-valued");
    }

    function testVerifyProofReturnsExpectedResult() public {
        vm.prank(SIGNER);
        registry.recordProof(ASSET_ID, PROOF_HASH_V1, 1);

        _assertTrue(
            registry.verifyProof(ASSET_ID, 1, PROOF_HASH_V1), "expected proof did not verify"
        );
        _assertTrue(!registry.verifyProof(ASSET_ID, 1, PROOF_HASH_V2), "wrong hash verified");
        _assertTrue(!registry.verifyProof(ASSET_ID, 2, PROOF_HASH_V1), "missing proof verified");
    }

    function testAdminCanGrantNewSigner() public {
        bytes32 verifierRole = registry.VERIFIER_ROLE();
        vm.prank(ADMIN);
        registry.grantRole(verifierRole, NEW_SIGNER);
        _assertTrue(registry.hasRole(verifierRole, NEW_SIGNER), "new signer was not granted");

        vm.prank(NEW_SIGNER);
        registry.recordProof(ASSET_ID, PROOF_HASH_V1, 1);
    }

    function testAdminCanRevokeOldSignerAndRevokedSignerCannotRecord() public {
        bytes32 verifierRole = registry.VERIFIER_ROLE();
        vm.prank(ADMIN);
        registry.revokeRole(verifierRole, SIGNER);
        _assertTrue(!registry.hasRole(verifierRole, SIGNER), "old signer was not revoked");

        vm.expectRevert(
            abi.encodeWithSelector(
                IAccessControl.AccessControlUnauthorizedAccount.selector, SIGNER, verifierRole
            )
        );
        vm.prank(SIGNER);
        registry.recordProof(ASSET_ID, PROOF_HASH_V1, 1);
    }

    function testRejectsZeroOrCollidingRoleHolders() public {
        vm.expectRevert(THVProofRegistry.InvalidAdministrator.selector);
        new THVProofRegistry(address(0), SIGNER);

        vm.expectRevert(THVProofRegistry.InvalidVerifier.selector);
        new THVProofRegistry(ADMIN, address(0));

        vm.expectRevert(THVProofRegistry.RoleSeparationRequired.selector);
        new THVProofRegistry(ADMIN, ADMIN);
    }

    function _assertProof(
        THVProofRegistry.Proof memory proof,
        bytes32 expectedAssetId,
        bytes32 expectedProofHash,
        uint64 expectedVersion,
        uint64 expectedRecordedAt,
        address expectedSigner,
        bool expectedExists
    ) private pure {
        _assertTrue(proof.assetId == expectedAssetId, "unexpected asset id");
        _assertTrue(proof.proofHash == expectedProofHash, "unexpected proof hash");
        _assertTrue(proof.version == expectedVersion, "unexpected version");
        _assertTrue(proof.recordedAt == expectedRecordedAt, "unexpected recorded time");
        _assertTrue(proof.signer == expectedSigner, "unexpected signer");
        _assertTrue(proof.exists == expectedExists, "unexpected exists value");
    }

    function _assertTrue(bool condition, string memory message) private pure {
        require(condition, message);
    }
}
