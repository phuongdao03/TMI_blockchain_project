// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import { DeployCertificateRegistry } from "../script/DeployCertificateRegistry.s.sol";

interface VmDeploy {
    function expectRevert(bytes calldata revertData) external;
}

contract DeployCertificateRegistryTest {
    VmDeploy private constant vm =
        VmDeploy(address(uint160(uint256(keccak256("hevm cheat code")))));
    DeployCertificateRegistry private deployment = new DeployCertificateRegistry();

    address private constant DEPLOYER = address(0x1001);
    address private constant ADMINISTRATOR = address(0x1002);
    address private constant ISSUER = address(0x1003);

    function testValidLocalAndAmoyInputs() public view {
        deployment.validateInputs(
            31_337, DEPLOYER, DEPLOYER, ADMINISTRATOR, ADMINISTRATOR, ISSUER, ISSUER
        );
        deployment.validateInputs(
            80_002, DEPLOYER, DEPLOYER, ADMINISTRATOR, ADMINISTRATOR, ISSUER, ISSUER
        );
    }

    function testRejectsUnsupportedChain() public {
        vm.expectRevert(
            abi.encodeWithSelector(DeployCertificateRegistry.UnsupportedChain.selector, 1)
        );
        deployment.validateInputs(
            1, DEPLOYER, DEPLOYER, ADMINISTRATOR, ADMINISTRATOR, ISSUER, ISSUER
        );
    }

    function testRejectsUnexpectedDeployerAdministratorAndIssuer() public {
        vm.expectRevert(
            abi.encodeWithSelector(
                DeployCertificateRegistry.DeployerMismatch.selector, address(0x9999), DEPLOYER
            )
        );
        deployment.validateInputs(
            31_337, DEPLOYER, address(0x9999), ADMINISTRATOR, ADMINISTRATOR, ISSUER, ISSUER
        );

        vm.expectRevert(
            abi.encodeWithSelector(
                DeployCertificateRegistry.AdministratorMismatch.selector,
                address(0x9999),
                ADMINISTRATOR
            )
        );
        deployment.validateInputs(
            31_337, DEPLOYER, DEPLOYER, ADMINISTRATOR, address(0x9999), ISSUER, ISSUER
        );

        vm.expectRevert(
            abi.encodeWithSelector(
                DeployCertificateRegistry.IssuerMismatch.selector, address(0x9999), ISSUER
            )
        );
        deployment.validateInputs(
            31_337, DEPLOYER, DEPLOYER, ADMINISTRATOR, ADMINISTRATOR, ISSUER, address(0x9999)
        );
    }
}
