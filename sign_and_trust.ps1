# PowerShell Script: Tu dong ky so CaptureToClipboard va cai dat chung chi

$ErrorActionPreference = "Stop"
$CertSubject = "CN=Capture To Clipboard, O=CaptureToClipboard, OU=Security"
$cerPath = Join-Path $PSScriptRoot "build\CaptureToClipboard.cer"

Write-Host "=== Capture To Clipboard Code Signing Tool ===" -ForegroundColor Cyan

# 1. Tim hoac tao chung chi Code Signing trong CurrentUser\My
$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $CertSubject -and $_.HasPrivateKey -and ($_.EnhancedKeyUsageList.FriendlyName -contains "Code Signing") } | Select-Object -First 1

if (-not $cert) {
    Write-Host "[1/3] Dang khoi tao chung chi Code Signing moi ($CertSubject)..." -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $CertSubject -CertStoreLocation "Cert:\CurrentUser\My" -NotAfter (Get-Date).AddYears(10)
} else {
    Write-Host "[1/3] Da tim thay chung chi Code Signing ($($cert.Thumbprint))." -ForegroundColor Green
}

# Xuat chung chi ra file .cer
if (-not (Test-Path (Join-Path $PSScriptRoot "build"))) {
    New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot "build") | Out-Null
}
Export-Certificate -Cert $cert -FilePath $cerPath -Force | Out-Null
Write-Host "      Da xuat file chung chi tai: $cerPath"

# 2. Kiem tra chung chi co nam trong Root hay khong
$isRootTrusted = Get-ChildItem Cert:\LocalMachine\Root, Cert:\CurrentUser\Root -ErrorAction SilentlyContinue | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }

if (-not $isRootTrusted) {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin) {
        Write-Host "[2/3] Dang cai dat chung chi vao LocalMachine\Root va LocalMachine\TrustedPublisher..." -ForegroundColor Yellow
        certutil -addstore -f "Root" "$cerPath" | Out-Null
        certutil -addstore -f "TrustedPublisher" "$cerPath" | Out-Null
        Write-Host "      Cai dat chung chi tin cay thanh cong!" -ForegroundColor Green
    } else {
        Write-Host "[2/3] Yeu cau quyen Administrator de cai dat chung chi vao he thong (Root Trust)..." -ForegroundColor Yellow
        try {
            $cmd = "certutil -addstore -f Root `"$cerPath`"; certutil -addstore -f TrustedPublisher `"$cerPath`""
            Start-Process powershell -Verb RunAs -Wait -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command $cmd"
            Write-Host "      Da gui yeu cau cap quyen he thong." -ForegroundColor Green
        } catch {
            Write-Host "      Khong the tu dong cap quyen Admin: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "[2/3] Chung chi da duoc tin cay tren he thong (Root Trust OK)." -ForegroundColor Green
}

# 3. Ky so Authenticode co kem Timestamp RFC 3161 va lam sach cache Smart App Control
Write-Host "[3/3] Dang lam sach cache Smart App Control va ky so Authenticode..." -ForegroundColor Yellow

$targets = @(
    (Join-Path $PSScriptRoot "dist\CaptureToClipboard.exe")
)

$timestampServer = "http://timestamp.digicert.com"

foreach ($exe in $targets) {
    if (Test-Path $exe) {
        # Thu ky kem timestamp, neu timeout thi ky khong timestamp
        try {
            Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -TimestampServer $timestampServer -ErrorAction Stop | Out-Null
        } catch {
            Set-AuthenticodeSignature -FilePath $exe -Certificate $cert | Out-Null
        }
        
        # Lam sach cache Extended Attributes (Smart App Control cache)
        $tmpSigned = "$exe.smv1_tmp"
        Copy-Item -Path $exe -Destination $tmpSigned -Force
        Remove-Item -Path $exe -Force
        Move-Item -Path $tmpSigned -Destination $exe -Force
        
        $sig = Get-AuthenticodeSignature -FilePath $exe
        Write-Host "      [SIGNED: $($sig.Status)] $exe" -ForegroundColor Green
        if ($sig.Status -ne "Valid") {
            Write-Host "      [NOTE] Trang thai: $($sig.Status) ($($sig.StatusMessage))" -ForegroundColor Yellow
        }
    }
}

Write-Host "=== Hoan tat ky so! ===" -ForegroundColor Cyan
