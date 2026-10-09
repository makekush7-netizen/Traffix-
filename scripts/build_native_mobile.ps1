param([switch]$Install, [string]$Device)
$ErrorActionPreference='Stop'
$TraffixRoot=Split-Path -Parent $PSScriptRoot
$MobileRoot=Join-Path $TraffixRoot 'mobile-app'
$Adb=Join-Path $env:LOCALAPPDATA 'Android/Sdk/platform-tools/adb.exe'
$Java=Join-Path $env:ProgramFiles 'Android/Android Studio/jbr'
if(!(Test-Path -LiteralPath $Java)){throw 'Install Android Studio, or adapt the Java path to JDK 21.'}
if(!(Test-Path -LiteralPath $Adb)){throw 'Install the Android SDK platform tools.'}
if(!(Test-Path -LiteralPath (Join-Path $MobileRoot 'node_modules/expo/package.json'))){throw 'Run npm ci inside mobile-app first.'}
if($Install -and !$Device){throw 'Specify -Device from adb devices. Do not guess between phones.'}
$env:JAVA_HOME=$Java
$env:ANDROID_HOME=Join-Path $env:LOCALAPPDATA 'Android/Sdk'
$env:NODE_ENV='production'
$env:GRADLE_OPTS='-Djava.net.preferIPv4Stack=true'
$Snapshot=(& node (Join-Path $MobileRoot 'tools/build-snapshot.cjs') | ConvertFrom-Json).path
if($LASTEXITCODE -or !$Snapshot){throw 'Could not create the short physical build snapshot.'}
$Resolved=[IO.Path]::GetFullPath($Snapshot)
$TempRoot=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
$Marker=Join-Path $Resolved '.traffix-native-snapshot'
if(!$Resolved.StartsWith($TempRoot,[StringComparison]::OrdinalIgnoreCase) -or
   !(Split-Path $Resolved -Leaf).StartsWith('tfx-') -or
   !(Test-Path -LiteralPath $Marker) -or
   (Get-Content -LiteralPath $Marker -Raw) -ne $MobileRoot){throw 'Snapshot identity check failed.'}
$Compiled=$false
try {
    Push-Location -LiteralPath $Resolved
    try {
        & npx.cmd expo prebuild --platform android --no-install
        if($LASTEXITCODE){throw 'Expo prebuild failed.'}
        Push-Location android
        try {
            & .\gradlew.bat assembleRelease --no-daemon --max-workers=2 '-PreactNativeArchitectures=arm64-v8a' '-Pkotlin.incremental=false' '-Dorg.gradle.jvmargs=-Xmx3072m -XX:MaxMetaspaceSize=768m -Djava.net.preferIPv4Stack=true'
            if($LASTEXITCODE){throw 'Android compilation failed.'}
        } finally { Pop-Location }
    } finally { Pop-Location }
    $Builds=Join-Path $MobileRoot 'builds'
    New-Item -ItemType Directory -Force -Path $Builds | Out-Null
    $Apk=Join-Path $Builds 'traffix-preview.apk'
    Copy-Item -LiteralPath (Join-Path $Resolved 'android/app/build/outputs/apk/release/app-release.apk') -Destination $Apk -Force
    $Compiled=$true
    Write-Host "Standalone ARM64 preview: $Apk"
    if($Install){
        & $Adb -s $Device install -r $Apk
        if($LASTEXITCODE){throw 'Installation failed. Unlock the phone and respond to its install dialog.'}
        & $Adb -s $Device reverse tcp:8004 tcp:8004
        & $Adb -s $Device shell am start -n in.traffix.driver/.MainActivity
    }
} finally {
    if($Compiled){
        # The checked, freshly created temp snapshot contains only this app's copy.
        Remove-Item -LiteralPath $Resolved -Recurse -Force
    } else {
        Write-Host "Build diagnostics retained at $Resolved"
    }
}
