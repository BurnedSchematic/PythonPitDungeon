Write-Host "Installing PythonPitDungeon..."

# --- Check for Python ---
Write-Host "Checking for Python..."
$python = Get-Command python -ErrorAction SilentlyContinue

if (-not $python) {
    Write-Host "Python not found. Attempting installation..."

    # Try winget first
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install -e --id Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "Winget not available. Please install Python manually from https://www.python.org/downloads/"
        exit
    }

    # Re-check Python
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Host "Python installation failed. Install manually and rerun this script."
        exit
    }
}

Write-Host "Python found at $($python.Source)"

# --- Install dependencies ---
Write-Host "Installing required packages..."
python -m pip install pygame websockets paho-mqtt

# --- Run the game ---
Write-Host "Installation complete."
$choice = Read-Host "Run PythonPitDungeon now? (y/n)"

if ($choice -eq "y") {
    python PythonPitDungeon.pyw
}
