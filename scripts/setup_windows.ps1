<#
.SYNOPSIS
    Notion2PDF Windows 설치 스크립트.

.DESCRIPTION
    프로젝트 로컬 .venv 가상환경을 만들고 requirements.txt를 설치합니다.
    WeasyPrint는 Pango/Cairo 같은 GTK 런타임 라이브러리를 필요로 하므로,
    설치가 끝나면 weasyprint import 가능 여부를 점검하고 안내를 출력합니다.

.EXAMPLE
    # 프로젝트 루트에서 PowerShell 실행 후:
    #   (최초 1회) 스크립트 실행 정책 허용
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\scripts\setup_windows.ps1
#>

$ErrorActionPreference = "Stop"

# 프로젝트 루트(스크립트 상위 폴더)로 이동
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
Write-Host "[*] 프로젝트 루트: $ProjectRoot"

# Python 실행기 찾기 (py 런처 우선)
$PythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py -3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} else {
    Write-Error "Python을 찾을 수 없습니다. https://www.python.org/downloads/ 에서 64-bit Python을 설치하세요."
}
Write-Host "[*] Python: $PythonCmd"

# venv 생성
if (-not (Test-Path ".venv")) {
    Write-Host "[*] .venv 가상환경 생성 중..."
    Invoke-Expression "$PythonCmd -m venv .venv"
} else {
    Write-Host "[*] 기존 .venv 사용"
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

# 의존성 설치
Write-Host "[*] pip 업그레이드 및 requirements 설치 중..."
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

# WeasyPrint 동작 확인 (GTK 런타임 필요)
Write-Host "[*] WeasyPrint import 점검 중..."
& $VenvPython -c "import weasyprint; print('WeasyPrint', weasyprint.__version__, 'OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Warning @"
WeasyPrint를 불러오지 못했습니다. Windows에서는 GTK(Pango/Cairo) 런타임이 필요합니다.

권장 방법 (MSYS2):
  1. https://www.msys2.org/ 에서 MSYS2 설치
  2. MSYS2 터미널에서: pacman -S mingw-w64-x86_64-pango
  3. C:\msys64\mingw64\bin 을 시스템 PATH에 추가
  4. PowerShell을 새로 열고 이 스크립트를 다시 실행

자세한 내용: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows
"@
    exit 1
}

Write-Host ""
Write-Host "[✓] 설치 완료!" -ForegroundColor Green
Write-Host "샘플 변환:  .\.venv\Scripts\python.exe convert.py templates\sample.html output\sample.pdf"
