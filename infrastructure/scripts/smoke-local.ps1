$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $projectRoot

function Assert-HttpStatus([string]$Name, [string]$Url, [int]$Expected = 200) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing $Url
        if ($response.StatusCode -ne $Expected) { throw "HTTP $($response.StatusCode)" }
    } catch {
        throw "$Name failed at $Url. Run 'docker compose ps' and 'docker compose logs $Name'. $($_.Exception.Message)"
    }
}

& (Join-Path $PSScriptRoot "bootstrap-local.ps1")
Assert-HttpStatus "frontend" "http://localhost:3000"
Assert-HttpStatus "backend" "http://localhost:8000/ready"
Assert-HttpStatus "mailpit" "http://localhost:8025/api/v1/info"
Assert-HttpStatus "firebase-emulator" "http://localhost:9099/emulator/v1/projects/tmi-local/config"

$migration = docker compose exec -T postgres psql -U tmi_local -d tmi_local -tAc "select version_num from alembic_version"
if ($LASTEXITCODE -ne 0 -or -not $migration.Trim()) { throw "postgres failed. Inspect 'docker compose logs postgres migrate'." }
$redis = docker compose exec -T redis redis-cli ping
if ($LASTEXITCODE -ne 0 -or $redis.Trim() -ne "PONG") { throw "redis failed. Inspect 'docker compose logs redis'." }
$chain = Invoke-RestMethod -Method Post -ContentType "application/json" -Body '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' http://localhost:8545
if ($chain.result -ne "0x7a69") { throw "anvil returned the wrong chain ID. Inspect 'docker compose logs anvil'." }

Write-Host "Local smoke passed: frontend, backend, PostgreSQL, Redis, Mailpit, Firebase and Anvil."
