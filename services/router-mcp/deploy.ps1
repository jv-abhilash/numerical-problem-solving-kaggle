# PowerShell Deployment script for MCP Router Service (Windows)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "MCP Router Service Deployment (Windows)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker is not installed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker found" -ForegroundColor Green

# Check Docker Compose
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    # Try docker compose (new syntax)
    $composeCheck = docker compose version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Docker Compose is not installed" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✓ Docker Compose found" -ForegroundColor Green

# Check if Docker is running
$dockerRunning = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker daemon is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Docker daemon is running" -ForegroundColor Green

Write-Host ""

# Create .env if not exists
if (-not (Test-Path .env)) {
    Write-Host "Creating .env file from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "✓ .env file created" -ForegroundColor Green
    Write-Host "  Please edit .env file if you want to configure API key or other settings" -ForegroundColor Yellow
    Write-Host ""
}

# Create logs directory
if (-not (Test-Path logs)) {
    New-Item -ItemType Directory -Path logs | Out-Null
}
Write-Host "✓ Logs directory created" -ForegroundColor Green

Write-Host ""
Write-Host "Building Docker image..." -ForegroundColor Yellow
docker-compose build

Write-Host ""
Write-Host "Starting service..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "Waiting for service to be healthy..." -ForegroundColor Yellow
$timeout = 180  # 3 minutes
$elapsed = 0
$interval = 5

while ($elapsed -lt $timeout) {
    $status = docker-compose ps 2>&1
    if ($status -match "healthy") {
        Write-Host "✓ Service is healthy and ready!" -ForegroundColor Green
        break
    }
    Write-Host "Waiting... ($elapsed/$timeout seconds)"
    Start-Sleep -Seconds $interval
    $elapsed += $interval
}

if ($elapsed -ge $timeout) {
    Write-Host "✗ Service failed to become healthy within $timeout seconds" -ForegroundColor Red
    Write-Host ""
    Write-Host "Checking logs:" -ForegroundColor Yellow
    docker-compose logs --tail=50
    exit 1
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Service Status" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Service Information" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Get IP address
$ipAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notmatch "Loopback"} | Select-Object -First 1).IPAddress

Write-Host "Service URL:     " -NoNewline
Write-Host "http://${ipAddress}:7001" -ForegroundColor Green
Write-Host "Health Check:    " -NoNewline
Write-Host "http://${ipAddress}:7001/health" -ForegroundColor Green
Write-Host "API Docs:        " -NoNewline
Write-Host "http://${ipAddress}:7001/docs" -ForegroundColor Green
Write-Host "Server Info:     " -NoNewline
Write-Host "http://${ipAddress}:7001/info" -ForegroundColor Green
Write-Host ""

# Test the service
Write-Host "Testing service..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:7001/health" -Method Get -TimeoutSec 10
    if ($response.status -eq "healthy") {
        Write-Host "✓ Service test successful" -ForegroundColor Green
        Write-Host "Response: $($response | ConvertTo-Json -Compress)"
    } else {
        Write-Host "⚠ Service returned unexpected response" -ForegroundColor Yellow
        Write-Host "Response: $($response | ConvertTo-Json)"
    }
} catch {
    Write-Host "✗ Service test failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Useful Commands" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "View logs:        docker-compose logs -f"
Write-Host "Stop service:     docker-compose stop"
Write-Host "Restart service:  docker-compose restart"
Write-Host "Remove service:   docker-compose down"
Write-Host "Remove all:       docker-compose down -v"
Write-Host ""

Write-Host "Deployment complete!" -ForegroundColor Green
