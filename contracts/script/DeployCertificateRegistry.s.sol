// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import { CertificateRegistry } from "../src/CertificateRegistry.sol";

interface Vm {
    function addr(uint256 privateKey) external returns (address);
    function envAddress(string calldata name) external returns (address);
    function envOr(string calldata name, address defaultValue) external returns (address);
    function envUint(string calldata name) external returns (uint256);
    function startBroadcast(address signer) external;
    function startBroadcast(uint256 privateKey) external;
    function stopBroadcast() external;
}

contract DeployCertificateRegistry {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    error UnsupportedChain(uint256 chainId);
    error AdministratorMismatch(address expected, address actual);

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
        address administrator = vm.envOr("CONTRACT_ADMIN", deployer);
        address expectedAdministrator = vm.envAddress("EXPECTED_CONTRACT_ADMIN");
        if (administrator != expectedAdministrator) {
            revert AdministratorMismatch(expectedAdministrator, administrator);
        }

        if (local) {
            vm.startBroadcast(deployer);
        } else {
            vm.startBroadcast(deployerPrivateKey);
        }
        registry = new CertificateRegistry(administrator);
        address issuer = vm.envOr("ISSUER_ADDRESS", address(0));
        if (issuer != address(0)) {
            registry.grantIssuer(issuer);
        }
        vm.stopBroadcast();
    }
}
