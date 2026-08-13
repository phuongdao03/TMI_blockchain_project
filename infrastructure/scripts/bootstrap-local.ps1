$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $projectRoot

docker compose --profile frontend up -d --build --wait --wait-timeout 240
if ($LASTEXITCODE -ne 0) { throw "Local services did not become healthy." }

$runtimeDirectory = Join-Path $projectRoot ".runtime"
$runtimeFile = Join-Path $runtimeDirectory "local-contract.env"
$broadcastFile = Join-Path $projectRoot "contracts/broadcast/DeployCertificateRegistry.s.sol/31337/run-latest.json"
$contractAddress = ""
if (Test-Path $runtimeFile) {
    $addressLine = Get-Content $runtimeFile | Where-Object { $_ -like "CERTIFICATE_CONTRACT_ADDRESS=*" } | Select-Object -First 1
    if ($addressLine) { $contractAddress = $addressLine.Split("=", 2)[1] }
}
if ($contractAddress -notmatch "^0x[0-9a-fA-F]{40}$" -and (Test-Path $broadcastFile)) {
    $previousBroadcast = Get-Content $broadcastFile -Raw | ConvertFrom-Json
    $contractAddress = ($previousBroadcast.receipts | Where-Object { $_.contractAddress } | Select-Object -Last 1).contractAddress
}

$contractAlive = $false
if ($contractAddress -match "^0x[0-9a-fA-F]{40}$") {
    $rpcBody = @{ jsonrpc = "2.0"; method = "eth_getCode"; params = @($contractAddress, "latest"); id = 1 } | ConvertTo-Json -Compress
    $code = (Invoke-RestMethod -Method Post -ContentType "application/json" -Body $rpcBody http://localhost:8545).result
    $contractAlive = $code -and $code -ne "0x"
}

if (-not $contractAlive) {
    docker compose --profile tools run --rm contract-deps
    if ($LASTEXITCODE -ne 0) { throw "Contract dependencies could not be installed." }
    docker compose --profile tools run --rm contract-deployer
    if ($LASTEXITCODE -ne 0) { throw "Local certificate contract deployment failed." }
    $broadcast = Get-Content $broadcastFile -Raw | ConvertFrom-Json
    $contractAddress = ($broadcast.receipts | Where-Object { $_.contractAddress } | Select-Object -Last 1).contractAddress
    if ($contractAddress -notmatch "^0x[0-9a-fA-F]{40}$") { throw "Deployment output did not contain a contract address." }
}

$anvilLogs = (docker compose logs --no-color anvil) -join "`n"
$privateKeyMatch = [regex]::Match($anvilLogs, "\(0\) (0x[0-9a-fA-F]{64})")
if (-not $privateKeyMatch.Success) { throw "Could not read the ephemeral Anvil signer key." }

New-Item -ItemType Directory -Force $runtimeDirectory | Out-Null
@(
    "# Generated local-only runtime values. This file is gitignored."
    "CERTIFICATE_CONTRACT_ADDRESS=$contractAddress"
    "BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES=$contractAddress"
    "BLOCKCHAIN_SIGNER_PRIVATE_KEY=$($privateKeyMatch.Groups[1].Value)"
) | Set-Content -Encoding Ascii $runtimeFile

docker compose --profile frontend up -d --force-recreate --wait --wait-timeout 180 backend worker scheduler frontend nginx
if ($LASTEXITCODE -ne 0) { throw "Application services did not reload contract settings." }
docker compose exec -T backend python -m app.scripts.seed_local
if ($LASTEXITCODE -ne 0) { throw "Local development identities could not be seeded." }

Write-Host "Local bootstrap complete. Contract: $contractAddress"
Write-Host "Local password for all seeded accounts: LocalOnly!23456"
