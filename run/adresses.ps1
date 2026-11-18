# Salubri - affiche l'adresse du serveur a saisir dans l'application Android (meme Wi-Fi que ce PC).
param([string]$Port = '80')
$suffixe = if ($Port -ne '80') { ":$Port" } else { '' }
Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
  Where-Object { $_.IPAddress -match '^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)' -and $_.InterfaceAlias -notmatch 'vEthernet|WSL|Docker|VirtualBox|VMware|Loopback' } |
  ForEach-Object { "Sur le telephone, adresse du serveur : http://$($_.IPAddress)$suffixe" }
Write-Host "Si le telephone n'atteint pas le serveur, autorisez le port $Port (PowerShell en administrateur) :"
Write-Host "  New-NetFirewallRule -DisplayName 'Salubri' -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -Profile Private"
