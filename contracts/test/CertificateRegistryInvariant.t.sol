// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import { CertificateRegistry } from "../src/CertificateRegistry.sol";

contract CertificateRegistryHandler {
    CertificateRegistry public immutable registry;
    bytes32 public constant CERTIFICATE_ID = keccak256("invariant-certificate");
    bool public issued;
    bool public revoked;

    constructor(CertificateRegistry registry_) {
        registry = registry_;
    }

    function issue(bytes32 dossierHash, bytes32 metadataHash, uint64 issuedAt, uint64 expiresAt)
        external
    {
        if (issued) return;
        registry.issueCertificate(CERTIFICATE_ID, dossierHash, metadataHash, issuedAt, expiresAt);
        issued = true;
    }

    function update(bytes32 dossierHash, bytes32 metadataHash, uint32 version) external {
        if (!issued || revoked) return;
        try registry.updateCertificate(CERTIFICATE_ID, dossierHash, metadataHash, version) { }
            catch { }
    }

    function revoke(bytes32 reasonHash) external {
        if (!issued || revoked) return;
        registry.revokeCertificate(CERTIFICATE_ID, reasonHash);
        revoked = true;
    }
}

contract CertificateRegistryInvariantTest {
    CertificateRegistry private registry;
    CertificateRegistryHandler private handler;
    address[] private targets;

    function setUp() public {
        registry = new CertificateRegistry(address(this));
        handler = new CertificateRegistryHandler(registry);
        registry.grantIssuer(address(handler));
        targets.push(address(handler));
    }

    function targetContracts() public view returns (address[] memory) {
        return targets;
    }

    fallback(bytes calldata) external returns (bytes memory) {
        return abi.encode(new address[](0));
    }

    function invariantAdministrativeRolesRemainStable() public view {
        require(registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), address(this)), "admin role");
        require(registry.hasRole(registry.PAUSER_ROLE(), address(this)), "pauser role");
        require(registry.hasRole(registry.ISSUER_ROLE(), address(handler)), "issuer role");
    }

    function invariantKnownCertificateStateIsConsistent() public view {
        if (!handler.issued()) return;
        CertificateRegistry.CertificateRecord memory record =
            registry.getCertificate(handler.CERTIFICATE_ID());
        require(record.version >= 1, "version");
        require(record.revoked == handler.revoked(), "revocation state");
    }
}
