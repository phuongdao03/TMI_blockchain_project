// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { DeployTHVProofRegistry } from "../script/DeployTHVProofRegistry.s.sol";

interface VmDeployment {
    function expectRevert(bytes calldata revertData) external;
    function expectRevert(bytes4 revertData) external;
}

contract DeployTHVProofRegistryTest {
    VmDeployment private constant vm =
        VmDeployment(address(uint160(uint256(keccak256("hevm cheat code")))));

    DeployTHVProofRegistry private deployment = new DeployTHVProofRegistry();

    address private constant DEPLOYER = address(0x1001);
    address private constant ADMIN = address(0x1002);
    address private constant SIGNER = address(0x1003);
    address private constant APPROVED_ADMINISTRATOR = 0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe;
    address private constant APPROVED_SIGNER = 0xBfA38182f0D24589e7898DD4892C58c3FDa58042;

    function testAcceptsApprovedLocalAmoyAndPolygonConfigurations() public view {
        deployment.validateInputs(
            31_337,
            31_337,
            keccak256("local"),
            DEPLOYER,
            DEPLOYER,
            APPROVED_ADMINISTRATOR,
            APPROVED_SIGNER,
            false
        );
        deployment.validateInputs(
            80_002,
            80_002,
            keccak256("amoy"),
            DEPLOYER,
            DEPLOYER,
            APPROVED_ADMINISTRATOR,
            APPROVED_SIGNER,
            false
        );
        deployment.validateInputs(
            137,
            137,
            keccak256("polygon"),
            DEPLOYER,
            DEPLOYER,
            APPROVED_ADMINISTRATOR,
            APPROVED_SIGNER,
            false
        );
    }

    function testAllowsNonProductionIdentitiesOnlyInExplicitLocalTestMode() public view {
        deployment.validateInputs(
            31_337, 31_337, keccak256("local"), DEPLOYER, DEPLOYER, ADMIN, SIGNER, true
        );
    }

    function testRejectsNonApprovedLocalIdentitiesWithoutExplicitTestMode() public {
        vm.expectRevert(
            abi.encodeWithSelector(
                DeployTHVProofRegistry.AdministratorNotApproved.selector,
                ADMIN,
                APPROVED_ADMINISTRATOR
            )
        );
        deployment.validateInputs(
            31_337, 31_337, keccak256("local"), DEPLOYER, DEPLOYER, ADMIN, SIGNER, false
        );
    }

    function testRejectsUnsupportedChainAndMismatchedNetwork() public {
        vm.expectRevert(
            abi.encodeWithSelector(DeployTHVProofRegistry.UnsupportedChain.selector, uint256(1))
        );
        deployment.validateInputs(
            1, 1, keccak256("unknown"), DEPLOYER, DEPLOYER, ADMIN, SIGNER, true
        );

        vm.expectRevert(
            abi.encodeWithSelector(
                DeployTHVProofRegistry.ConfiguredChainMismatch.selector,
                uint256(137),
                uint256(80_002)
            )
        );
        deployment.validateInputs(
            80_002, 137, keccak256("polygon"), DEPLOYER, DEPLOYER, ADMIN, SIGNER, true
        );

        vm.expectRevert(
            abi.encodeWithSelector(
                DeployTHVProofRegistry.ConfiguredNetworkMismatch.selector,
                keccak256("amoy"),
                keccak256("polygon")
            )
        );
        deployment.validateInputs(
            137, 137, keccak256("amoy"), DEPLOYER, DEPLOYER, ADMIN, SIGNER, true
        );
    }

    function testMainnetGuardRejectsAnyNonPolygonChain() public {
        vm.expectRevert(
            abi.encodeWithSelector(
                DeployTHVProofRegistry.ConfiguredChainMismatch.selector,
                uint256(137),
                uint256(31_337)
            )
        );
        deployment.validateInputs(
            31_337, 137, keccak256("polygon"), DEPLOYER, DEPLOYER, ADMIN, SIGNER, true
        );
    }

    function testRejectsWrongOrUnsafeIdentities() public {
        vm.expectRevert(
            abi.encodeWithSelector(
                DeployTHVProofRegistry.DeployerMismatch.selector, address(0x9999), DEPLOYER
            )
        );
        deployment.validateInputs(
            31_337, 31_337, keccak256("local"), DEPLOYER, address(0x9999), ADMIN, SIGNER, true
        );

        vm.expectRevert(DeployTHVProofRegistry.InvalidAdministrator.selector);
        deployment.validateInputs(
            31_337, 31_337, keccak256("local"), DEPLOYER, DEPLOYER, address(0), SIGNER, true
        );

        vm.expectRevert(DeployTHVProofRegistry.InvalidVerifier.selector);
        deployment.validateInputs(
            31_337, 31_337, keccak256("local"), DEPLOYER, DEPLOYER, ADMIN, address(0), true
        );

        vm.expectRevert(DeployTHVProofRegistry.RoleSeparationRequired.selector);
        deployment.validateInputs(
            31_337, 31_337, keccak256("local"), DEPLOYER, DEPLOYER, ADMIN, ADMIN, true
        );
    }

    function testRejectsNonApprovedProductionIdentities() public {
        vm.expectRevert(
            abi.encodeWithSelector(
                DeployTHVProofRegistry.AdministratorNotApproved.selector,
                ADMIN,
                APPROVED_ADMINISTRATOR
            )
        );
        deployment.validateInputs(
            137, 137, keccak256("polygon"), DEPLOYER, DEPLOYER, ADMIN, APPROVED_SIGNER, false
        );

        vm.expectRevert(
            abi.encodeWithSelector(
                DeployTHVProofRegistry.SignerNotApproved.selector, SIGNER, APPROVED_SIGNER
            )
        );
        deployment.validateInputs(
            137,
            137,
            keccak256("polygon"),
            DEPLOYER,
            DEPLOYER,
            APPROVED_ADMINISTRATOR,
            SIGNER,
            false
        );
    }

    function testRejectsTestModeOutsideAnvil() public {
        vm.expectRevert(
            abi.encodeWithSelector(
                DeployTHVProofRegistry.TestModeOnlyAllowedOnAnvil.selector, uint256(137)
            )
        );
        deployment.validateInputs(
            137,
            137,
            keccak256("polygon"),
            DEPLOYER,
            DEPLOYER,
            APPROVED_ADMINISTRATOR,
            APPROVED_SIGNER,
            true
        );
    }

    function testRejectsDeployerCollidingWithAdministratorOrSigner() public {
        vm.expectRevert(
            abi.encodeWithSelector(DeployTHVProofRegistry.DeployerRoleCollision.selector, ADMIN)
        );
        deployment.validateInputs(
            31_337, 31_337, keccak256("local"), ADMIN, ADMIN, ADMIN, SIGNER, true
        );

        vm.expectRevert(
            abi.encodeWithSelector(DeployTHVProofRegistry.DeployerRoleCollision.selector, SIGNER)
        );
        deployment.validateInputs(
            31_337, 31_337, keccak256("local"), SIGNER, SIGNER, ADMIN, SIGNER, true
        );
    }
}
