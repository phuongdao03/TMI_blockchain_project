# Signer onboarding

This procedure is for the designated human signer. It stops before any
production transaction.

1. A super administrator confirms that the designated THV account has the
   `SUPER_ADMIN` role and the `blockchain.sign` permission.
2. The person creates or receives a signer wallet outside THV, backs up its seed
   according to the organization’s secure-custody policy, and installs a
   compatible wallet such as MetaMask.
3. The governance process grants that public address `ISSUER_ROLE` on the target
   contract. Verify it with a read-only `hasRole` call.
4. In THV, sign in to the designated account, open **Ký blockchain**, connect
   the wallet and sign the one-time ownership message. This message is not a
   transaction and never requests a seed/private key.
5. For local verification, add Anvil (chain 31337) to the wallet and import only
   a disposable Anvil account. For staging, use Polygon Amoy (chain 80002) and
   test POL. Do not reuse either key in production.
6. Open a queue item, compare dossier/version/proof/network/contract, then
   approve the wallet popup. THV later reports broadcast/confirmed/failed state
   independently.

If wallet, network or THV account is different from the registered signer, do
not continue. Switch the wallet/network or contact the governance operator.
