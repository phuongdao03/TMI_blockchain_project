// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { THVProofRegistry } from "../src/THVProofRegistry.sol";

interface VmDeployProofRegistry {
    function addr(uint256 privateKey) external returns (address);
    function envAddress(string calldata name) external returns (address);
    function envString(string calldata name) external returns (string memory);
    function envUint(string calldata name) external returns (uint256);
    function envOr(string calldata name, bool defaultValue) external returns (bool);
    function startBroadcast(address signer) external;
    function startBroadcast(uint256 privateKey) external;
    function stopBroadcast() external;
}

/// @notice Foundry deployment entrypoint for the append-only THV proof registry.
/// @dev Uses a local unlocked deployer on Anvil and a deployer key only for remote broadcast.
contract DeployTHVProofRegistry {
    uint256 public constant ANVIL_CHAIN_ID = 31_337;
    uint256 public constant AMOY_CHAIN_ID = 80_002;
    uint256 public constant POLYGON_CHAIN_ID = 137;

    bytes32 public constant LOCAL_NETWORK_HASH = keccak256("local");
    bytes32 public constant AMOY_NETWORK_HASH = keccak256("amoy");
    bytes32 public constant POLYGON_NETWORK_HASH = keccak256("polygon");
    bytes32 public constant MAINNET_CONFIRMATION_HASH =
        keccak256("DEPLOY_THV_PROOF_REGISTRY_TO_POLYGON_MAINNET");

    /// @dev The Mainnet and Amoy release must preserve this governance separation.
    address public constant APPROVED_ADMINISTRATOR =
        0xec5FcdFab3FCafCEFCED55CC702CD3B13f54B4Fe;
    address public constant APPROVED_SIGNER = 0xBfA38182f0D24589e7898DD4892C58c3FDa58042;

    VmDeployProofRegistry private constant vm =
        VmDeployProofRegistry(address(uint160(uint256(keccak256("hevm cheat code")))));

    error UnsupportedChain(uint256 chainId);
    error ConfiguredChainMismatch(uint256 configuredChainId, uint256 actualChainId);
    error ConfiguredNetworkMismatch(bytes32 configuredNetwork, bytes32 expectedNetwork);
    error MainnetDeploymentNotConfirmed();
    error InvalidDeployer();
    error InvalidAdministrator();
    error InvalidVerifier();
    error RoleSeparationRequired();
    error AdministratorNotApproved(address provided, address approved);
    error SignerNotApproved(address provided, address approved);
    error TestModeOnlyAllowedOnAnvil(uint256 actualChainId);
    error DeployerRoleCollision(address deployer);
    error DeployerMismatch(address expected, address actual);

    function run() external returns (THVProofRegistry registry) {
        uint256 configuredChainId = vm.envUint("BLOCKCHAIN_CHAIN_ID");
        bytes32 configuredNetwork = keccak256(bytes(vm.envString("BLOCKCHAIN_NETWORK")));
        address administrator = vm.envAddress("ADMIN_WALLET_ADDRESS");
        address signer = vm.envAddress("SIGNER_WALLET_ADDRESS");
        bool localTestMode = vm.envOr("THV_PROOF_REGISTRY_TEST_MODE", false);

        bool local = block.chainid == ANVIL_CHAIN_ID;
        uint256 deployerPrivateKey;
        address deployer;
        if (local) {
            deployer = vm.envAddress("DEPLOYER_ADDRESS");
        } else {
            deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
            deployer = vm.addr(deployerPrivateKey);
        }

        validateInputs(
            block.chainid,
            configuredChainId,
            configuredNetwork,
            deployer,
            vm.envAddress("EXPECTED_DEPLOYER"),
            administrator,
            signer,
            localTestMode
        );

        if (block.chainid == POLYGON_CHAIN_ID) {
            bytes32 confirmation = keccak256(bytes(vm.envString("MAINNET_DEPLOY_CONFIRMATION")));
            if (confirmation != MAINNET_CONFIRMATION_HASH) revert MainnetDeploymentNotConfirmed();
        }

        if (local) {
            vm.startBroadcast(deployer);
        } else {
            vm.startBroadcast(deployerPrivateKey);
        }
        registry = new THVProofRegistry(administrator, signer);
        vm.stopBroadcast();
    }

    function validateInputs(
        uint256 actualChainId,
        uint256 configuredChainId,
        bytes32 configuredNetwork,
        address deployer,
        address expectedDeployer,
        address administrator,
        address signer,
        bool localTestMode
    ) public pure {
        bytes32 expectedNetwork = expectedNetworkHash(actualChainId);
        if (configuredChainId != actualChainId) {
            revert ConfiguredChainMismatch(configuredChainId, actualChainId);
        }
        if (configuredNetwork != expectedNetwork) {
            revert ConfiguredNetworkMismatch(configuredNetwork, expectedNetwork);
        }
        if (deployer == address(0)) revert InvalidDeployer();
        if (administrator == address(0)) revert InvalidAdministrator();
        if (signer == address(0)) revert InvalidVerifier();
        if (administrator == signer) revert RoleSeparationRequired();
        if (localTestMode && actualChainId != ANVIL_CHAIN_ID) {
            revert TestModeOnlyAllowedOnAnvil(actualChainId);
        }
        if (deployer == administrator || deployer == signer) {
            revert DeployerRoleCollision(deployer);
        }
        if (deployer != expectedDeployer) revert DeployerMismatch(expectedDeployer, deployer);
        if (!localTestMode && administrator != APPROVED_ADMINISTRATOR) {
            revert AdministratorNotApproved(administrator, APPROVED_ADMINISTRATOR);
        }
        if (!localTestMode && signer != APPROVED_SIGNER) {
            revert SignerNotApproved(signer, APPROVED_SIGNER);
        }
    }

    function expectedNetworkHash(uint256 chainId) public pure returns (bytes32) {
        if (chainId == ANVIL_CHAIN_ID) return LOCAL_NETWORK_HASH;
        if (chainId == AMOY_CHAIN_ID) return AMOY_NETWORK_HASH;
        if (chainId == POLYGON_CHAIN_ID) return POLYGON_NETWORK_HASH;
        revert UnsupportedChain(chainId);
    }
}
