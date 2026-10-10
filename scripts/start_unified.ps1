param([string]$Python, [string]$LanAddress, [string]$AccountsFile)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
if(!$Python){$Python=Join-Path $projectRoot '.venv/Scripts/python.exe';$savedRuntime=Join-Path $projectRoot '.cache/private/python-path.txt';if(!(Test-Path -LiteralPath $Python) -and (Test-Path -LiteralPath $savedRuntime)){$Python=(Get-Content -Raw -LiteralPath $savedRuntime).Trim()}}
if(!$AccountsFile){$savedAccounts=Join-Path $projectRoot '.cache/private/host-accounts.json';if(Test-Path -LiteralPath $savedAccounts){$AccountsFile=$savedAccounts}}
if(!$LanAddress){$savedLan=Join-Path $projectRoot '.cache/private/lan-address.txt';if(Test-Path -LiteralPath $savedLan){$LanAddress=(Get-Content -Raw -LiteralPath $savedLan).Trim()}}
if(!(Test-Path -LiteralPath $Python)){throw 'Pass -Python with your installed Python 3.12 virtual environment.'}
$env:TRAFFIX_HOST='127.0.0.1'
Remove-Item Env:\TRAFFIX_LAN_ADDRESS -ErrorAction SilentlyContinue
if($LanAddress){
 $parsedAddress=[System.Net.IPAddress]::Parse($LanAddress)
 if($parsedAddress.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork -or [System.Net.IPAddress]::IsLoopback($parsedAddress)){throw 'Use your laptop Wi-Fi IPv4 address.'}
 if($LanAddress -notmatch '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)'){throw 'Use a private Wi-Fi/hotspot IPv4 address, not a public address.'}
 $env:TRAFFIX_LAN_ADDRESS=$LanAddress
}
if($AccountsFile){$env:TRAFFIX_ACCOUNTS=Get-Content -Raw -LiteralPath $AccountsFile}
try{$existing=Invoke-RestMethod 'http://127.0.0.1:8005/openapi.json' -TimeoutSec 2;if($existing.info.title -eq 'Traffix unified API'){Write-Output 'Traffix is already running: http://127.0.0.1:8005/operator/index.html';return}}catch{}
Push-Location $projectRoot
try{
 Write-Output "Laptop dashboard: http://127.0.0.1:8005/operator/index.html"
 if($LanAddress){Write-Output "Phone host: http://${LanAddress}:8005/operator/phone.html"}
 Write-Output 'Keep this terminal open. Ctrl+C stops the host. For phones, use the same Wi-Fi/hotspot.'
 Write-Output 'If Windows asks, allow only Private networks. This is a local demo, not public deployment.'
 & $Python -m scripts.run_unified
 if($LASTEXITCODE -ne 0){throw "Host exited ($LASTEXITCODE). Read the error above; check whether port 8005 is already in use."}
}finally{Pop-Location}
