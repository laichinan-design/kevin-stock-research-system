param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$bundleRoot = $PSScriptRoot
$catalog = Join-Path $bundleRoot '.agents\plugins\marketplace.json'
if (-not (Test-Path -LiteralPath $catalog)) { throw 'Extract the complete ZIP first. Marketplace catalog not found.' }
$meta = Get-Content -LiteralPath $catalog -Raw | ConvertFrom-Json
$marketplaceName = $meta.name
if ($marketplaceName -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid marketplace name.' }
$selector = 'kevin-stock-research@' + $marketplaceName
if ($DryRun) {
    Write-Output ('Marketplace root: ' + $bundleRoot)
    Write-Output ('Plugin selector: ' + $selector)
    Write-Output 'No settings changed.'
    exit 0
}
$codexTool = Get-Command codex -ErrorAction SilentlyContinue
if (-not $codexTool) { throw 'Codex CLI not found. Use the ChatGPT desktop local-project installation steps in START-HERE.md.' }
& $codexTool.Source plugin marketplace add $bundleRoot
if ($LASTEXITCODE -ne 0) { throw 'Marketplace registration failed. No plugin install attempted.' }
& $codexTool.Source plugin add $selector
if ($LASTEXITCODE -ne 0) { throw 'Plugin install failed; inspect the CLI output.' }
Write-Output 'CLI installation command completed. Restart the desktop app and test in a new chat.'
Write-Output 'If version 0.1 is enabled from personal, disable that old entry in the Plugins UI to avoid duplicate skills.'
Write-Output 'This does not start a schedule or migrate your research data.'
