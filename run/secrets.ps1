# SPDX-License-Identifier: AGPL-3.0-or-later
# Hors démonstration (SALUBRI_DEMO_MODE=false dans .env) : génère une fois le code de service et la clé de session
# manquants ou laissés à leur valeur de démonstration, les écrit dans .env et les affiche une seule fois.
$ErrorActionPreference = 'Stop'
$envFile = Join-Path (Split-Path -Parent $PSScriptRoot) '.env'
if (-not (Test-Path $envFile)) { exit 0 }
$lines = @(Get-Content -LiteralPath $envFile -Encoding UTF8)
if (-not ($lines | Where-Object { $_ -match '^\s*SALUBRI_DEMO_MODE\s*=\s*false\s*$' })) { exit 0 }

function New-Secret {
  $b = New-Object byte[] 32
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
  return (($b | ForEach-Object { $_.ToString('x2') }) -join '')
}
function Get-Value($name) {
  $l = $lines | Where-Object { $_ -match "^\s*$name\s*=" } | Select-Object -Last 1
  if ($l) { return ($l -split '=', 2)[1].Trim() } else { return '' }
}

$created = @()
foreach ($name in 'SALUBRI_ADMIN_TOKEN', 'SALUBRI_SECRET_KEY') {
  $v = Get-Value $name
  if ($v -eq '' -or $v -eq 'ouaga2026' -or $v.Length -lt 16) {
    $new = New-Secret
    $lines = @($lines | Where-Object { $_ -notmatch "^\s*$name\s*=" }) + "$name=$new"
    $created += "$name=$new"
  }
}
if ($created.Count -gt 0) {
  # UTF-8 sans BOM : un BOM casserait la première variable lue par docker compose
  [System.IO.File]::WriteAllLines($envFile, [string[]]$lines, (New-Object System.Text.UTF8Encoding($false)))
  Write-Host ''
  Write-Host 'Mode production : secrets générés et enregistrés dans .env (affichés une seule fois) :'
  $created | ForEach-Object { Write-Host "  $_" }
  Write-Host 'Gardez le fichier .env privé. Créez le premier compte admin : run\admin <login>'
  Write-Host ''
}
