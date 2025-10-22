# MCP Router Service - Quick Start

Get the MCP Router Service running in 5 minutes!

## Prerequisites Checklist

- [ ] Ubuntu 20.04/22.04 server (or similar Linux)
- [ ] NVIDIA GPU with 8GB+ VRAM
- [ ] 20GB free disk space
- [ ] Internet connection

## Installation (One-Command)

```bash
# Copy-paste this entire block:
cd ~ && \
curl -fsSL https://get.docker.com -o get-docker.sh && \
sudo sh get-docker.sh && \
sudo usermod -aG docker $USER && \
newgrp docker && \
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) && \
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg && \
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list && \
sudo apt-get update && \
sudo apt-get install -y nvidia-container-toolkit && \
sudo nvidia-ctk runtime configure --runtime=docker && \
sudo systemctl restart docker && \
echo "✓ Docker and NVIDIA runtime installed!"
```

## Deploy Service

```bash
# 1. Navigate to service directory
cd /path/to/numerical_problem_solving_v2/services/router-mcp

# 2. Configure (optional)
cp .env.example .env
# nano .env  # Edit if you want to set API key

# 3. Deploy!
chmod +x deploy.sh
./deploy.sh
```

That's it! The service will:
- Build the Docker image (~10 min)
- Download the 7B model (~5 min, 14GB)
- Start the service
- Show you the URL

## Verify It's Working

```bash
# Get your server IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Service URL: http://$SERVER_IP:7001"

# Test it
curl http://localhost:7001/health
```

Expected response:
```json
{"status":"healthy","model":"Qwen/Qwen2.5-Math-7B-Instruct","device":"cuda","model_loaded":true}
```

## Use from Client

On your main machine:

```bash
python -m src.main \
  --stage p1+p2 \
  --paper data/paper.txt \
  --router mcp \
  --mcp-endpoint "http://YOUR_SERVER_IP:7001/mcp"
```

Replace `YOUR_SERVER_IP` with the IP from above.

## Troubleshooting

### "nvidia-smi: command not found"

Install NVIDIA drivers first:
```bash
sudo apt-get install -y nvidia-driver-535
sudo reboot
```

### "Cannot connect to the Docker daemon"

Start Docker:
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### Service won't become healthy

Check logs:
```bash
docker-compose logs -f
```

Common issues:
- Downloading model (wait 5-10 minutes)
- No internet (check `ping google.com`)
- GPU not available (check `nvidia-smi`)

### Can't connect from client

1. Check firewall:
```bash
sudo ufw allow 7001/tcp
```

2. Test from server first:
```bash
curl http://localhost:7001/health
```

3. Then from client:
```bash
curl http://YOUR_SERVER_IP:7001/health
```

## What Next?

- **See full docs**: [README.md](README.md)
- **Deployment guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Run tests**: `python test_mcp.py --url http://localhost:7001`
- **View API docs**: Open http://YOUR_SERVER_IP:7001/docs in browser

## Common Commands

```bash
# View logs
docker-compose logs -f

# Restart service
docker-compose restart

# Stop service
docker-compose stop

# Check GPU usage
docker-compose exec router-mcp nvidia-smi

# Run test suite
python test_mcp.py
```

## Performance Expectations

- **Startup time**: 2-3 minutes (model loading)
- **Single question**: ~0.15 seconds
- **Batch of 60**: ~4 seconds
- **Memory usage**: ~7GB GPU RAM

## Security Note

For production, **always set an API key**:

```bash
# In .env file
MCP_API_KEY=$(openssl rand -hex 32)
```

Then use it in requests:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:7001/health
```

---

**Need help?** Check the full documentation in [README.md](README.md) or [DEPLOYMENT.md](DEPLOYMENT.md).
