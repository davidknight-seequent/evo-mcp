# Docker Setup & Deployment Guide for Evo MCP

## Overview

This guide explains how to run the Evo MCP server in Docker containers. Docker provides a clean, isolated environment for running the server with automatic dependency management and state persistence.

## Quick Start (2 Steps)

```bash
# 1. Navigate to the repository
cd /path/to/evo-mcp

# 2. Run the quick start script (creates .env and starts Docker)
./scripts/docker-quickstart.sh

# Or manually:
# - Copy template: cp .env.example .env
# - Edit credentials: nano .env
# - Start: docker-compose up -d
```

## File Structure

```
evo-mcp/
├── Dockerfile                 # Multi-stage build for production
├── docker-compose.yml         # Production configuration
├── docker-compose.dev.yml     # Development with live code reload
├── docker-compose.k8s.yml     # Kubernetes-ready configuration
├── .env                       # Your configuration (git-ignored)
├── .env.example               # Configuration template
├── .dockerignore              # Files to exclude from image
├── DOCKER-SETUP.md            # This guide
└── scripts/docker-quickstart.sh  # Automated setup
```

## Build & Run

### Option 1: Using Docker Compose (Recommended)

```bash
# Build the image
docker-compose build

# Start the server in background
docker-compose up -d

# View logs
docker-compose logs -f evo-mcp

# Stop the server
docker-compose down
```

### Option 2: Development Mode (with live code reload)

```bash
# Start with source code mounted for editing
docker-compose -f docker-compose.dev.yml up -d

# Changes to /src files apply immediately
```

### Option 3: Kubernetes

```bash
# Use K8s-ready compose file
docker-compose -f docker-compose.k8s.yml up -d

# Or deploy to Kubernetes cluster:
kubectl apply -f docker-compose.k8s.yml
```

## Transport Protocols

The MCP server supports multiple communication protocols:

### Stdio (Default)
Process-to-process communication via stdin/stdout pipes. Used by IDEs.

```bash
# Default - no environment variables needed
docker-compose up -d
```

### HTTP+SSE (Network-Based)
Run the server on a network port for remote clients or HTTP connections.

```bash
# Configure in .env
MCP_TRANSPORT=sse        # or http
MCP_PORT=8000

# Start the server
docker-compose up -d

# Access via HTTP
curl http://localhost:8000/sse
```

### Transport Options

| Transport | Use Case | Port Exposed | IDE Integration |
|-----------|----------|------------------|------------|
| **stdio** | Local IDE (VS Code, Cursor) | No | Direct connection |
| **sse** | Remote clients, HTTP clients | Yes (8000) | HTTP endpoint |
| **http** | HTTP streaming, proxies | Yes (8000) | HTTP endpoint |

## Configuration

### Environment Variables

All configuration happens through environment variables in `.env` (auto-loaded by docker-compose):

```bash
# Required
EVO_CLIENT_ID=your-client-id

# Optional: Evo Platform
EVO_REDIRECT_URL=http://localhost:3000/signin-oidc
EVO_DISCOVERY_URL=https://discover.api.seequent.com
ISSUER_URL=https://ims.bentley.com

# Optional: MCP Server
MCP_TOOL_FILTER=all              # all, admin, or data
EVO_MCP_LOG_LEVEL=ERROR          # DEBUG, INFO, WARNING, ERROR
EVO_AUTH_MODE=authorization_code # or client_credentials

# Optional: MCP Transport (default: stdio)
MCP_TRANSPORT=stdio              # stdio, sse, or http
MCP_HOST=0.0.0.0                # Bind address for sse/http
MCP_PORT=8000                    # Port for sse/http
MCP_PATH=/mcp                    # HTTP path (http transport only)
```

### State Directory

All state is stored in the Docker volume `evo-mcp-state`:

```
/app/state/
├── token_cache.json     # Cached OAuth tokens
├── variables.json       # Workspace cache
└── (server logs if configured)
```

This persists across container restarts and updates.

## Examples

### Run with Custom Log Level

```bash
export EVO_MCP_LOG_LEVEL=DEBUG
docker-compose up -d
```

### Run with Local Data Files

```bash
# Mount your data directory
export EVO_LOCAL_DATA_DIR=/path/to/data
docker-compose up -d
```

### Run with HTTP Transport (SSE)

```bash
# Configure for HTTP SSE transport
export MCP_TRANSPORT=sse
export MCP_PORT=8000

# Start server
docker-compose up -d

# Test the server via HTTP
curl http://localhost:8000/sse

# Access from your local IDE configured for HTTP transport
# See "Integration with IDE" section below
```

### Run with HTTP Transport (Streaming)

```bash
# Configure for HTTP streaming
export MCP_TRANSPORT=http
export MCP_PORT=8000

# Start server
docker-compose up -d

# The server will be available at http://localhost:8000/mcp
# (or your configured MCP_PATH)
```

### Clear Cached Tokens

```bash
docker volume rm evo-mcp-state
docker-compose up -d
```

### Stop and Clean Up

```bash
# Stop containers
docker-compose down

# Remove containers, networks, and volumes
docker-compose down -v

# Remove images
docker image rm evo-mcp
```

## Integration with IDE

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "mcp": {
    "servers": {
      "evo-mcp": {
        "type": "stdio",
        "command": "docker-compose",
        "args": ["exec", "-T", "evo-mcp", "python", "/app/src/mcp_tools.py"]
      }
    }
  }
}
```

### Cursor

Similar configuration in Cursor's MCP settings.

## Container Architecture

### Image Details

- **Base**: `python:3.11-slim` (efficient, secure)
- **Size**: ~200MB (after multi-stage build optimization)
- **User**: `mcpuser` (non-root, UID 1000)
- **Working Dir**: `/app`

### Multi-stage Build Benefits

1. **Smaller Image**: Build tools not included in final image
2. **Security**: Fewer packages = smaller attack surface
3. **Speed**: Faster deployments
4. **Layers**: Efficient caching for rebuilds

## Health Checks

The container includes a health check that validates:

```bash
# Check container health
docker-compose ps

# Should show: healthy or starting status
```

## Logging

### View Logs

```bash
# Tail logs
docker-compose logs -f

# View with timestamps
docker-compose logs --timestamps evo-mcp

# Show only last 50 lines
docker-compose logs --tail=50
```

### Log Configuration

Logs are directed to:
- **stdout/stderr**: Captured by Docker daemon
- **Docker**: Stored in `/var/lib/docker/containers/*/`
- **Retention**: Configured in `docker-compose.yml`

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs evo-mcp

# Verify credentials
grep EVO_CLIENT_ID .env

# Check file permissions
docker-compose run --rm evo-mcp ls -la /app/state
```

### Authentication failures

```bash
# Clear token cache
docker volume rm evo-mcp-state

# Restart with fresh authentication
docker-compose up -d
```

### Out of memory

```bash
# Increase memory limit in docker-compose.yml
# Then rebuild:
docker-compose up -d --force-recreate
```

### Port conflicts

If using default configuration, no ports are exposed. If you expose ports:

```yaml
ports:
  - "3000:3000"  # Change 3000:3000 if already in use
```

## Advanced

### Build for Different Architectures

```bash
# ARM64 (Apple Silicon, Raspberry Pi)
docker buildx build --platform linux/arm64 -t evo-mcp:arm64 .

# AMD64 (Intel/AMD)
docker buildx build --platform linux/amd64 -t evo-mcp:amd64 .
```

### Custom Base Image

Edit `Dockerfile` to use alternative base:

```dockerfile
# For smaller images
FROM python:3.11-alpine

# For specific needs
FROM python:3.11-bookworm
```

### Publish to Registry

```bash
docker tag evo-mcp:latest ghcr.io/seequentevo/evo-mcp:latest
docker push ghcr.io/seequentevo/evo-mcp:latest
```

## Security Best Practices

✅ **Implemented**:
- Non-root user execution
- Minimal base image
- No unnecessary packages
- Volume-based state isolation
- Resource limits

⚠️ **Still needed**:
- Secrets management (don't commit credentials)
- Network policies (limit container communication)
- Regular base image updates
- Image scanning for vulnerabilities

## Performance

### Optimization Tips

1. **Reuse volumes**: Don't delete `evo-mcp-state` between runs
2. **Cache tokens**: Speeds up subsequent startups
3. **Resource limits**: Set appropriate CPU/memory in docker-compose.yml
4. **Logging level**: Use `ERROR` for production (less I/O)

### Metrics

- **Startup time**: ~5-10 seconds (first run: 15-20s with auth)
- **Memory usage**: 100-200MB typical
- **CPU**: Minimal when idle (<5%)

## Next Steps

1. See [DOCKER.md](DOCKER.md) for detailed documentation
2. See [README.md](README.md) for general Evo MCP info
3. Explore [sample integrations](#integration-with-ide)
