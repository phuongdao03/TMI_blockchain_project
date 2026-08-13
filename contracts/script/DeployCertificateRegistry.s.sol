// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import { CertificateRegistry } from "../src/CertificateRegistry.sol";

interface Vm {
    function addr(uint256 privateKey) external returns (address);
    function envAddress(string calldata name) external returns (address);
    function envUint(string calldata name) external returns (uint256);
    function startBroadcast(address signer) external;
    function startBroadcast(uint256 privateKey) external;
    function stopBroadcast() external;
}

contract DeployCertificateRegistry {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    error UnsupportedChain(uint256 chainId);
    error InvalidDeployer();
    error InvalidAdministrator();
    error InvalidIssuer();
    error DeployerMismatch(address expected, address actual);
    error AdministratorMismatch(address expected, address actual);
    error IssuerMismatch(address expected, address actual);

    function run() external returns (CertificateRegistry registry) {
        if (block.chainid != 31_337 && block.chainid != 80_002) {
            revert UnsupportedChain(block.chainid);
        }
        bool local = block.chainid == 31_337;
        uint256 deployerPrivateKey;
        address deployer;
        if (local) {
            deployer = vm.envAddress("DEPLOYER_ADDRESS");
        } else {
            deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
            deployer = vm.addr(deployerPrivateKey);
        }
        address expectedDeployer = vm.envAddress("EXPECTED_DEPLOYER");
        address administrator = vm.envAddress("CONTRACT_ADMIN");
        address expectedAdministrator = vm.envAddress("EXPECTED_CONTRACT_ADMIN");
        address issuer = vm.envAddress("ISSUER_ADDRESS");
        address expectedIssuer = vm.envAddress("EXPECTED_ISSUER");
        validateInputs(
            block.chainid,
            deployer,
            expectedDeployer,
            administrator,
            expectedAdministrator,
            issuer,
            expectedIssuer
        );

        if (local) {
            vm.startBroadcast(deployer);
        } else {
            vm.startBroadcast(deployerPrivateKey);
        }
        registry = new CertificateRegistry(administrator);
        registry.grantIssuer(issuer);
        vm.stopBroadcast();
    }

    function validateInputs(
        uint256 chainId,
        address deployer,
        address expectedDeployer,
        address administrator,
        address expectedAdministrator,
        address issuer,
        address expectedIssuer
    ) public pure {
        if (chainId != 31_337 && chainId != 80_002) {
            revert UnsupportedChain(chainId);
        }
        if (deployer == address(0)) revert InvalidDeployer();
        if (administrator == address(0)) revert InvalidAdministrator();
        if (issuer == address(0)) revert InvalidIssuer();
        if (deployer != expectedDeployer) revert DeployerMismatch(expectedDeployer, deployer);
        if (administrator != expectedAdministrator) {
            revert AdministratorMismatch(expectedAdministrator, administrator);
        }
        if (issuer != expectedIssuer) revert IssuerMismatch(expectedIssuer, issuer);
    }
}
