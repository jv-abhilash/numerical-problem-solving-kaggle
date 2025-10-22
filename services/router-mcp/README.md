# MCP Router Service

GPU-accelerated question routing service using Qwen2.5-Math-7B-Instruct model with Docker deployment.

## Overview

This service provides a Model Context Protocol (MCP) compatible API for classifying mathematical questions into topic categories and difficulty levels. It uses a 7B parameter language model running on GPU for accurate classification.

## Architecture

```
┌─────────────────────────────────────┐
│  KCET Solver Main Application      │
│  (P2 Routing Stage)                 │
└──────────────┬──────────────────────┘
               │ HTTP POST /mcp
               │ (batch of questions)
               ▼
┌─────────────────────────────────────┐
│  MCP Router Service                 │
│  ┌───────────────────────────────┐ │
│  │  FastAPI Server (Port 7001)   │ │
│  └───────────┬───────────────────┘ │
│              │                       │
│  ┌───────────▼───────────────────┐ │
│  │  Qwen2.5-Math-7B-Instruct     │ │
│  │  (GPU Accelerated)            │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Features

- **GPU Acceleration**: Uses NVIDIA CUDA for fast inference
- **8-bit Quantization**: Efficient memory usage with bitsandbytes
- **Batch Processing**: Handles multiple questions in one request
- **Topic Classification**: algebra, calculus, discrete, geometry
- **Difficulty Assessment**: Easy (E), Medium (M), Hard (H)
- **Health Monitoring**: Built-in health check endpoints
- **API Authentication**: Optional API key protection
- **Docker Deployment**: Single-command deployment with GPU support

## Prerequisites

### Hardware Requirements

- **GPU**: NVIDIA GPU with 8GB+ VRAM (recommended)
  - GTX 1080 Ti / RTX 2060 or better
  - For CPU-only: possible but slower
- **RAM**: 16GB minimum, 32GB recommended
- **Disk**: 15GB for model cache

### Software Requirements

- **Docker**: 20.10+ with Docker Compose
- **NVIDIA Docker Runtime**: For GPU support
  - Install: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
- **CUDA**: 12.1+ (via Docker image)

## Quick Start

### 1. Install NVIDIA Container Toolkit (Linux)

```bash
# Add NVIDIA package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install nvidia-docker2
sudo apt-get update
sudo apt-get install -y nvidia-docker2

# Restart Docker daemon
sudo systemctl restart docker

# Test GPU access
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### 2. Configure Environment

```bash
cd services/router-mcp
cp .env.example .env

# Optional: Edit .env to set API key
nano .env
```

### 3. Deploy Service

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows (PowerShell):**
```powershell
.\deploy.ps1
```

The deployment script will:
- Check prerequisites
- Build Docker image
- Start the service
- Wait for health check
- Display service information

### 4. Verify Deployment

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Test health endpoint
curl http://localhost:7001/health

# Get server info (including GPU info)
curl http://localhost:7001/info
```

Expected output:
```json
{
  "status": "healthy",
  "model": "Qwen/Qwen2.5-Math-7B-Instruct",
  "device": "cuda",
  "model_loaded": true
}
```

## Usage

### API Endpoints

#### 1. Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "model": "Qwen/Qwen2.5-Math-7B-Instruct",
  "device": "cuda",
  "model_loaded": true
}
```

#### 2. Server Information
```bash
GET /info
```

Response:
```json
{
  "model_id": "Qwen/Qwen2.5-Math-7B-Instruct",
  "device": "cuda",
  "topics": ["algebra", "calculus", "discrete", "geometry"],
  "difficulties": ["E", "M", "H"],
  "gpu_info": {
    "gpu_count": 1,
    "gpu_name": "NVIDIA GeForce RTX 3080",
    "gpu_memory_allocated": "6.45 GB",
    "gpu_memory_reserved": "7.12 GB"
  },
  "authentication": "disabled"
}
```

#### 3. Batch Routing (Main MCP Endpoint)
```bash
POST /mcp
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY  # Optional
```

Request:
```json
{
  "tool": "route_questions",
  "inputs": [
    {
      "qid": "Q1",
      "stem": "Solve the equation 3x + 8 < 17",
      "options": ["x<1", "x<2", "x<3", "x<4"]
    },
    {
      "qid": "Q2",
      "stem": "Find the derivative of x^2 + 3x",
      "options": ["2x+3", "x+3", "2x", "3"]
    }
  ]
}
```

Response:
```json
[
  {
    "qid": "Q1",
    "topic": "algebra",
    "difficulty": "E",
    "subtopic": "linear inequalities",
    "needs_tools": ["sympy"],
    "confidence": 0.95,
    "notes": null
  },
  {
    "qid": "Q2",
    "topic": "calculus",
    "difficulty": "E",
    "subtopic": "differentiation",
    "needs_tools": ["sympy"],
    "confidence": 0.98,
    "notes": null
  }
]
```

#### 4. Single Question Classification
```bash
POST /classify
Content-Type: application/json
```

Request:
```json
{
  "qid": "Q1",
  "stem": "Find the integral of sin(x)",
  "options": ["-cos(x)+C", "cos(x)+C", "sin(x)+C", "-sin(x)+C"]
}
```

### Using from Python

```python
import requests

# Configure endpoint
MCP_ENDPOINT = "http://192.168.1.100:7001/mcp"
API_KEY = "your-api-key"  # Optional

# Prepare questions
questions = [
    {
        "qid": "Q1",
        "stem": "Solve 3x + 8 < 17",
        "options": ["x<1", "x<2", "x<3", "x<4"]
    }
]

# Make request
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"  # Include if API key is set
}

response = requests.post(
    MCP_ENDPOINT,
    json={"tool": "route_questions", "inputs": questions},
    headers=headers,
    timeout=60
)

results = response.json()
print(results)
```

### Using from KCET Solver

```bash
# Configure MCP endpoint in your environment or command line
python -m src.main \
  --stage p1+p2 \
  --paper data/paper.txt \
  --router mcp \
  --mcp-endpoint http://192.168.1.100:7001/mcp \
  --mcp-api-key "your-api-key"
```

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Optional API Key for authentication
MCP_API_KEY=your-secret-key-here

# Model configuration
ROUTER_MODEL_ID=Qwen/Qwen2.5-Math-7B-Instruct
MAX_NEW_TOKENS=32
TEMPERATURE=0.0

# GPU configuration
CUDA_VISIBLE_DEVICES=0

# Model cache (persistent across restarts)
TRANSFORMERS_CACHE=/app/models
HF_HOME=/app/models
```

### GPU Assignment

To use a specific GPU (if multiple GPUs available):

```bash
# In .env file
CUDA_VISIBLE_DEVICES=0  # Use first GPU

# Or in docker-compose.yml
environment:
  - CUDA_VISIBLE_DEVICES=1  # Use second GPU
```

### API Authentication

To enable API key authentication:

1. Set `MCP_API_KEY` in `.env` file
2. Restart service: `docker-compose restart`
3. Include API key in requests:
   ```
   Authorization: Bearer your-secret-key-here
   ```

## Management Commands

```bash
# View logs (follow mode)
docker-compose logs -f

# Stop service
docker-compose stop

# Start service
docker-compose start

# Restart service
docker-compose restart

# View resource usage
docker stats kcet-router-mcp

# Execute command in container
docker-compose exec router-mcp bash

# Remove service (keeps volumes)
docker-compose down

# Remove service and volumes
docker-compose down -v

# Rebuild image
docker-compose build --no-cache
```

## Monitoring

### Check GPU Usage

```bash
# From host
nvidia-smi

# From container
docker-compose exec router-mcp nvidia-smi
```

### View Model Cache

```bash
docker-compose exec router-mcp ls -lh /app/models
```

### Performance Metrics

The service logs inference time for each batch:

```bash
docker-compose logs | grep "Processing"
# 2025-10-16 13:50:01 - INFO - Processing 60 questions
# 2025-10-16 13:50:05 - INFO - Completed routing 60 questions
# Average: ~4 seconds for 60 questions
```

## Troubleshooting

### Service won't start

**Check Docker logs:**
```bash
docker-compose logs
```

**Common issues:**
- GPU not available: Check `nvidia-smi` and NVIDIA Docker runtime
- Model download failed: Check internet connection and disk space
- Port already in use: Change port in `docker-compose.yml`

### Out of memory (OOM)

**Symptoms:**
- Container exits with code 137
- Log shows "CUDA out of memory"

**Solutions:**
```bash
# 1. Use 8-bit quantization (already enabled)
# 2. Reduce batch size in client
# 3. Close other GPU applications
# 4. Use smaller model variant
```

### Slow inference

**Check:**
- GPU is being used: `docker-compose exec router-mcp nvidia-smi`
- Model loaded correctly: `curl http://localhost:7001/info`
- Temperature is 0.0 for greedy decoding

**Optimize:**
```bash
# In .env
TEMPERATURE=0.0  # Greedy (fastest)
MAX_NEW_TOKENS=32  # Lower for faster inference
```

### Connection refused

**Check:**
- Service is running: `docker-compose ps`
- Port is accessible: `netstat -an | grep 7001`
- Firewall rules allow traffic
- Use correct IP address (not 127.0.0.1 from remote)

## Performance

### Benchmarks

Hardware: RTX 3080 (10GB), 32GB RAM, Intel i7-10700K

| Batch Size | Time (seconds) | Questions/sec |
|-----------|----------------|---------------|
| 1         | 0.15           | 6.7           |
| 10        | 0.8            | 12.5          |
| 60        | 4.2            | 14.3          |
| 100       | 6.8            | 14.7          |

**Notes:**
- First request is slower (model warmup)
- Batching improves throughput significantly
- 8-bit quantization saves ~50% memory with minimal accuracy loss

## Security

### API Key Protection

Always set `MCP_API_KEY` in production:

```bash
# Generate secure key
openssl rand -hex 32

# Set in .env
MCP_API_KEY=your-generated-key
```

### Network Security

For production deployment:
- Use reverse proxy (nginx) with HTTPS
- Restrict access by IP/firewall
- Use Docker networks for service isolation
- Enable Docker content trust

## Advanced Configuration

### Custom Model

To use a different model:

```bash
# In .env
ROUTER_MODEL_ID=mistralai/Mistral-7B-Instruct-v0.2
```

### Multi-GPU

For multiple GPU support:

```yaml
# In docker-compose.yml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all  # Use all GPUs
          capabilities: [gpu]
```

### Production Deployment

For production on remote server:

1. **Set up server with GPU**
2. **Install prerequisites**
3. **Deploy service**
4. **Configure firewall:**
   ```bash
   sudo ufw allow 7001/tcp
   ```
5. **Set up systemd service (optional):**
   ```bash
   sudo systemctl enable docker
   # Service will auto-start with docker-compose restart policy
   ```

## API Documentation

Interactive API documentation available at:
- Swagger UI: `http://your-server-ip:7001/docs`
- ReDoc: `http://your-server-ip:7001/redoc`

## Support

For issues or questions:
- Check logs: `docker-compose logs`
- Review documentation: This README
- Test with curl: Examples provided above

## License

Part of the KCET Math Solver project.
