# MCP Router Service - Deployment Guide

Complete step-by-step guide for deploying the MCP Router Service on a GPU-enabled server.

## Server Requirements

### Minimum Specifications
- **CPU**: 4 cores (8 threads recommended)
- **RAM**: 16GB minimum, 32GB recommended
- **GPU**: NVIDIA GPU with 8GB+ VRAM
  - Examples: GTX 1080 Ti, RTX 2060, RTX 3060, RTX 3080, RTX 4070
- **Storage**: 20GB free space (15GB for model cache)
- **OS**: Ubuntu 20.04/22.04 LTS (recommended)

### Network
- **Bandwidth**: 100 Mbps+ for model download
- **Firewall**: Allow incoming TCP port 7001
- **Static IP**: Recommended for consistent client configuration

## Installation Steps

### Step 1: Prepare the Server

#### 1.1 Update System
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

#### 1.2 Install NVIDIA Drivers (if not installed)
```bash
# Check if drivers are installed
nvidia-smi

# If not installed, install drivers
sudo apt-get install -y nvidia-driver-535  # or latest version
sudo reboot

# Verify after reboot
nvidia-smi
```

Expected output:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xx.xx    Driver Version: 535.xx.xx    CUDA Version: 12.2   |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
...
```

### Step 2: Install Docker

#### 2.1 Install Docker Engine
```bash
# Remove old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify installation
sudo docker run hello-world
```

#### 2.2 Configure Docker for Non-Root User
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Verify
docker ps
```

### Step 3: Install NVIDIA Container Toolkit

```bash
# Add NVIDIA package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
    && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install NVIDIA Container Toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test GPU access
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

If successful, you should see the nvidia-smi output from within the container.

### Step 4: Deploy MCP Router Service

#### 4.1 Clone/Copy Project Files
```bash
# If using git
cd ~
git clone <your-repo-url>
cd numerical_problem_solving_v2/services/router-mcp

# Or if copying files
mkdir -p ~/kcet-router-mcp
cd ~/kcet-router-mcp
# Copy: Dockerfile, docker-compose.yml, requirements.txt, server.py, deploy.sh
```

#### 4.2 Configure Environment
```bash
# Create .env file
cp .env.example .env

# Edit configuration (optional)
nano .env

# Set API key for security (recommended)
# Generate secure key:
openssl rand -hex 32

# Add to .env:
# MCP_API_KEY=<your-generated-key>
```

#### 4.3 Make Deploy Script Executable
```bash
chmod +x deploy.sh
```

#### 4.4 Run Deployment
```bash
./deploy.sh
```

The deployment will:
1. Check prerequisites ✓
2. Build Docker image (~10 minutes)
3. Download model (~14GB, first time only)
4. Start service
5. Wait for health check
6. Display service information

### Step 5: Verify Deployment

#### 5.1 Check Service Status
```bash
docker-compose ps
```

Expected output:
```
NAME                COMMAND                  SERVICE       STATUS        PORTS
kcet-router-mcp     "uvicorn server:app …"   router-mcp    Up (healthy)  0.0.0.0:7001->7001/tcp
```

#### 5.2 Test Health Endpoint
```bash
curl http://localhost:7001/health
```

Expected response:
```json
{
  "status": "healthy",
  "model": "Qwen/Qwen2.5-Math-7B-Instruct",
  "device": "cuda",
  "model_loaded": true
}
```

#### 5.3 Get Server Information
```bash
curl http://localhost:7001/info
```

#### 5.4 Test Classification
```bash
curl -X POST http://localhost:7001/classify \
  -H "Content-Type: application/json" \
  -d '{
    "qid": "Q1",
    "stem": "Solve the equation 3x + 8 = 17",
    "options": ["x=1", "x=2", "x=3", "x=4"]
  }'
```

### Step 6: Configure Firewall

#### 6.1 Allow Port 7001
```bash
# Using UFW
sudo ufw allow 7001/tcp
sudo ufw reload

# Using iptables
sudo iptables -A INPUT -p tcp --dport 7001 -j ACCEPT
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

#### 6.2 Verify Port is Open
```bash
# From server
netstat -tuln | grep 7001

# From client machine
telnet <server-ip> 7001
# or
curl http://<server-ip>:7001/health
```

### Step 7: Configure Client Application

On your main KCET solver machine, update the configuration:

```bash
# Test MCP connection
export MCP_ENDPOINT="http://<server-ip>:7001/mcp"
export MCP_API_KEY="your-api-key"  # If you set one

# Run P2 routing with MCP
python -m src.main \
  --stage p1+p2 \
  --paper data/paper.txt \
  --router mcp \
  --mcp-endpoint "$MCP_ENDPOINT" \
  --mcp-api-key "$MCP_API_KEY"
```

## Post-Deployment Configuration

### Enable Auto-Start on Boot

Docker service will auto-start due to `restart: unless-stopped` policy in docker-compose.yml.

To verify:
```bash
sudo systemctl enable docker
sudo systemctl status docker
```

### Set Up Log Rotation

Create `/etc/docker/daemon.json`:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker:
```bash
sudo systemctl restart docker
docker-compose restart
```

### Monitor Resource Usage

```bash
# Real-time GPU monitoring
watch -n 1 nvidia-smi

# Docker stats
docker stats kcet-router-mcp

# Service logs
docker-compose logs -f --tail=100
```

### Set Up Monitoring (Optional)

For production deployments, consider:
- **Prometheus + Grafana**: Metrics and dashboards
- **ELK Stack**: Log aggregation and analysis
- **Uptime Kuma**: Uptime monitoring

## Maintenance

### View Logs
```bash
# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Search logs
docker-compose logs | grep "ERROR"
```

### Update Service
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Or use deploy script
./deploy.sh
```

### Clear Model Cache
```bash
# Remove volume (will re-download model)
docker-compose down -v
docker volume rm router-mcp_router-models

# Restart
./deploy.sh
```

### Backup Configuration
```bash
# Backup important files
tar -czf router-mcp-backup-$(date +%Y%m%d).tar.gz \
  .env \
  docker-compose.yml \
  logs/

# Store backup in safe location
```

## Troubleshooting

### Issue: Service won't start

**Check logs:**
```bash
docker-compose logs
```

**Common causes:**
- GPU not available: Run `nvidia-smi` and check NVIDIA Docker runtime
- Port conflict: Change port in docker-compose.yml
- Insufficient disk space: Check `df -h`

### Issue: Model download fails

**Symptoms:**
- Service starts but never becomes healthy
- Logs show "Connection timeout" or "Download failed"

**Solutions:**
```bash
# 1. Check internet connection
ping huggingface.co

# 2. Use HF_TOKEN if model is gated
# Add to .env:
# HF_TOKEN=your_huggingface_token

# 3. Pre-download model
docker-compose run --rm router-mcp python -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
model_id = 'Qwen/Qwen2.5-Math-7B-Instruct'
tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir='/app/models')
model = AutoModelForCausalLM.from_pretrained(model_id, cache_dir='/app/models')
"
```

### Issue: CUDA Out of Memory

**Solutions:**
```bash
# 1. Ensure 8-bit quantization is enabled (already in Dockerfile)
# 2. Close other GPU applications
# 3. Restart container
docker-compose restart

# 4. Check GPU memory
nvidia-smi
```

### Issue: Slow inference

**Diagnosis:**
```bash
# Check if GPU is being used
docker-compose exec router-mcp nvidia-smi

# View detailed logs
docker-compose logs -f
```

**Optimize:**
- Ensure TEMPERATURE=0.0 in .env
- Verify model is on GPU (check logs)
- Use batch requests (more efficient)

### Issue: Can't connect from client

**Check:**
```bash
# 1. Service is running
docker-compose ps

# 2. Port is open
sudo netstat -tuln | grep 7001

# 3. Firewall allows traffic
sudo ufw status

# 4. Test from server first
curl http://localhost:7001/health

# 5. Then test from client
curl http://<server-ip>:7001/health
```

## Performance Optimization

### Batch Size
- Larger batches = better GPU utilization
- Optimal: 32-128 questions per request

### Temperature
- Set to 0.0 for deterministic, fastest results
- Non-zero enables sampling (slower)

### Quantization
- 8-bit: Already enabled, ~50% memory savings
- 4-bit: Possible but lower accuracy

### Multiple Workers
Not recommended for GPU inference (serialization overhead).

## Security Best Practices

1. **Always set API key in production**
   ```bash
   MCP_API_KEY=$(openssl rand -hex 32)
   ```

2. **Use HTTPS in production**
   - Deploy nginx reverse proxy
   - Configure SSL certificates

3. **Restrict network access**
   - Use firewall rules
   - Consider VPN for sensitive deployments

4. **Keep system updated**
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   docker-compose pull  # Update base images
   ```

5. **Monitor logs for suspicious activity**
   ```bash
   docker-compose logs | grep "401\|403\|500"
   ```

## Cost Estimation

For cloud deployment (AWS/GCP/Azure):

**GPU Instance Examples:**
- AWS g4dn.xlarge (T4, 16GB): ~$0.50/hr
- AWS g5.xlarge (A10G, 24GB): ~$1.00/hr
- GCP n1-standard-4 + T4: ~$0.45/hr

**Monthly costs (24/7):**
- ~$360/month for basic T4 instance
- ~$720/month for A10G instance

**Cost optimization:**
- Use spot/preemptible instances (~70% savings)
- Auto-shutdown during off-hours
- Regional pricing differences

## Scaling Considerations

### Horizontal Scaling
Deploy multiple instances with load balancer:
```
                    ┌─> Router Instance 1 (GPU 1)
Client → Load Balancer ─┼─> Router Instance 2 (GPU 2)
                    └─> Router Instance 3 (GPU 3)
```

### Vertical Scaling
Use larger GPU with multiple workers (limited benefit).

## Support and Resources

- **Documentation**: See [README.md](README.md)
- **API Docs**: http://your-server:7001/docs
- **Model Info**: https://huggingface.co/Qwen/Qwen2.5-Math-7B-Instruct
- **NVIDIA Docs**: https://docs.nvidia.com/datacenter/cloud-native/

## Appendix: Remote Server Setup Example

Complete example for fresh Ubuntu server:

```bash
# === On Server ===
# 1. Update and install drivers
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y nvidia-driver-535
sudo reboot

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# 3. Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 4. Get project files
cd ~
git clone <your-repo>
cd numerical_problem_solving_v2/services/router-mcp

# 5. Configure
cp .env.example .env
nano .env  # Set MCP_API_KEY

# 6. Deploy
chmod +x deploy.sh
./deploy.sh

# 7. Configure firewall
sudo ufw allow 7001/tcp
sudo ufw enable

# 8. Get server IP
hostname -I | awk '{print $1}'

# === On Client ===
# Test connection
SERVER_IP="<server-ip-from-above>"
curl http://$SERVER_IP:7001/health

# Run KCET solver with MCP
python -m src.main \
  --stage p1+p2 \
  --paper data/paper.txt \
  --router mcp \
  --mcp-endpoint "http://$SERVER_IP:7001/mcp" \
  --mcp-api-key "<your-api-key>"
```

Done! Your MCP Router Service is now deployed and ready to use.
