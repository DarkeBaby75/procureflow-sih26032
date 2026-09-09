param(
    [string]$SdkRoot = "$env:LOCALAPPDATA\Android\Sdk"
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path $PSScriptRoot).Path
$BuildDir = Join-Path $ProjectRoot 'build'
$ArtifactDir = Join-Path $ProjectRoot 'artifacts'

if (-not $BuildDir.StartsWith($ProjectRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unsafe build directory.'
}
if (Test-Path -LiteralPath $BuildDir) {
    Remove-Item -LiteralPath $BuildDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $BuildDir, $ArtifactDir | Out-Null

$BuildToolsDir = Get-ChildItem -LiteralPath (Join-Path $SdkRoot 'build-tools') -Directory |
    Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
$PlatformDir = Get-ChildItem -LiteralPath (Join-Path $SdkRoot 'platforms') -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName 'android.jar') } |
    Sort-Object { $value = $_.Name -replace '^android-', ''; if ($value -notmatch '\.') { $value += '.0' }; [version]$value } -Descending | Select-Object -First 1
if (-not $BuildToolsDir -or -not $PlatformDir) { throw 'Android SDK build tools or platform are missing.' }

$Aapt2 = Join-Path $BuildToolsDir.FullName 'aapt2.exe'
$Aapt = Join-Path $BuildToolsDir.FullName 'aapt.exe'
$D8 = Join-Path $BuildToolsDir.FullName 'd8.bat'
$ZipAlign = Join-Path $BuildToolsDir.FullName 'zipalign.exe'
$ApkSigner = Join-Path $BuildToolsDir.FullName 'apksigner.bat'
$AndroidJar = Join-Path $PlatformDir.FullName 'android.jar'
$Compiled = Join-Path $BuildDir 'compiled.zip'
$Unsigned = Join-Path $BuildDir 'ProcureFlow-unsigned.apk'
$Aligned = Join-Path $BuildDir 'ProcureFlow-aligned.apk'
$Generated = Join-Path $BuildDir 'generated'
$Classes = Join-Path $BuildDir 'classes'
$Dex = Join-Path $BuildDir 'dex'
$FinalApk = Join-Path $ArtifactDir 'ProcureFlow-Android-v1.0.1.apk'

New-Item -ItemType Directory -Force -Path $Generated, $Classes, $Dex | Out-Null
& $Aapt2 compile --dir (Join-Path $ProjectRoot 'res') -o $Compiled
if ($LASTEXITCODE -ne 0) { throw 'Android resource compilation failed.' }
& $Aapt2 link -o $Unsigned -I $AndroidJar --manifest (Join-Path $ProjectRoot 'AndroidManifest.xml') --java $Generated --min-sdk-version 24 --target-sdk-version 36 --version-code 2 --version-name 1.0.1 -A (Join-Path $ProjectRoot 'assets') $Compiled
if ($LASTEXITCODE -ne 0) { throw 'Android resource linking failed.' }

$JavaFiles = @(Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'src'), $Generated -Filter '*.java' -Recurse | ForEach-Object FullName)
& javac -encoding UTF-8 -source 11 -target 11 -classpath $AndroidJar -d $Classes $JavaFiles
if ($LASTEXITCODE -ne 0) { throw 'Java compilation failed.' }
$ClassFiles = @(Get-ChildItem -LiteralPath $Classes -Filter '*.class' -Recurse | ForEach-Object FullName)
& $D8 --lib $AndroidJar --min-api 24 --output $Dex $ClassFiles
if ($LASTEXITCODE -ne 0) { throw 'DEX compilation failed.' }

Copy-Item -LiteralPath (Join-Path $Dex 'classes.dex') -Destination (Join-Path $BuildDir 'classes.dex')
Push-Location $BuildDir
try { & $Aapt add $Unsigned 'classes.dex' } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw 'Adding DEX to the APK failed.' }
& $ZipAlign -p -f 4 $Unsigned $Aligned
if ($LASTEXITCODE -ne 0) { throw 'APK alignment failed.' }

$DebugKey = Join-Path $env:USERPROFILE '.android\debug.keystore'
if (-not (Test-Path -LiteralPath $DebugKey)) { throw 'Android debug signing key is missing.' }
& $ApkSigner sign --ks $DebugKey --ks-pass pass:android --key-pass pass:android --out $FinalApk $Aligned
if ($LASTEXITCODE -ne 0) { throw 'APK signing failed.' }
& $ApkSigner verify --verbose --print-certs $FinalApk
if ($LASTEXITCODE -ne 0) { throw 'APK signature verification failed.' }
Write-Host "APK: $FinalApk"
