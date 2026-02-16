# Docker Quick Start Guide for Evo MCP

## Prerequisites

- Docker & Docker Compose installed
- Evo Platform credentials (Client ID, etc.)

## Setup

### 1. Configure Environment Variables

```bash
# Copy the template and fill in your credentials
cp .env.example .env
# Edit with your actual credentials
nano .env
```

Required variables:
- `EVO_CLIENT_ID` - Your Evo application client ID
- `EVO_REDIRECT_URL` - OAuth redirect URL (default: http://localhost:3000/signin-oidc)

### 2. Build and Run

```bash
# Build the container
docker-compose build

# Start the server
docker-compose up -d

# View logs
docker-compose logs -f evo-mcp

# Stop the server
docker-compose down
```

## Usage with MCP Clients

### VS Code Integration

#### Option 1: SSE Transport (Recommended for Docker)

Start the server with SSE transport:
```bash
# In .env, set:
# MCP_TRANSPORT=sse
# MCP_PORT=8000

docker-compose up -d
```

Add to your VS Code settings (`.vscode/settings.json` or via UI):

```json
{
  "servers": {
    "evo-mcp-docker": {
      "type": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

#### Option 2: stdio via Docker

```json
{
  "servers": {
    "evo-mcp-docker": {
      "type": "stdio",
      "command": "docker",
      "args": ["run", "--rm", "-i", "--env-file", ".env", "--mount", "type=volume,source=evo-mcp-state,destination=/app/state", "evo-mcp-server"]
    }
  }
}
```

**Or** use docker-compose exec:

```json
{
  "servers": {
    "evo-mcp-docker": {
      "type": "stdio",
      "command": "docker-compose",
      "args": ["exec", "-T", "evo-mcp", "python", "/app/src/mcp_tools.py"]
    }
  }
}
```

### Cursor Integration

#### Option 1: SSE Transport (Recommended for Docker)

Start the server with SSE transport (see VS Code instructions above), then add to Cursor's MCP settings:

```json
{
  "mcpServers": {
    "evo-mcp-docker": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

#### Option 2: stdio via Docker

```json
{
  "mcpServers": {
    "evo-mcp-docker": {
      "command": "docker-compose",
      "args": ["exec", "-T", "evo-mcp", "python", "/app/src/mcp_tools.py"]
    }
  }
}
```

## Container Architecture

### Multi-stage Build
- **Stage 1 (builder)**: Uses `python:3.11-slim` + uv to build dependencies
- **Stage 2 (runtime)**: Lean runtime image with virtual environment only

Benefits:
- Smaller final image (no build tools)
- Faster deployments
- More secure (fewer attack surfaces)

### State Management
- **State Directory**: `/app/state` (persistent via Docker volume)
- **Contains**:
  - `token_cache.json` - Cached OAuth tokens
  - `variables.json` - Cached workspace variables
  - Server logs (if configured)

### Non-root User
- Runs as `mcpuser` (UID 1000) for security
- State directory permissions properly configured

## Environment Variables (docker-compose.yml)

All variables from `.env` are available. Key ones:

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `EVO_CLIENT_ID` | ✓ | - | Evo app client ID |
| `EVO_REDIRECT_URL` | | `http://localhost:3000/signin-oidc` | OAuth redirect |
| `EVO_DISCOVERY_URL` | | `https://discover.api.seequent.com` | Evo discovery service |
| `ISSUER_URL` | | `https://ims.bentley.com` | OAuth issuer |
| `MCP_TOOL_FILTER` | | `all` | Tool set: all, admin, data |
| `EVO_MCP_LOG_LEVEL` | | `ERROR` | Logging level |
| `EVO_AUTH_MODE` | | `authorization_code` | Auth flow type |

## Persisting Data

The `evo-mcp-state` volume persists across container restarts:

```bash
# View volume contents
docker inspect evo-mcp-state

# Back up state
docker run --rm -v evo-mcp-state:/data -v $(pwd):/backup alpine tar czf /backup/evo-mcp-state-backup.tar.gz -C /data .

# Restore state
docker run --rm -v evo-mcp-state:/data -v $(pwd):/backup alpine tar xzf /backup/evo-mcp-state-backup.tar.gz -C /data
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs evo-mcp

# Check exit code
docker-compose ps

# Debug inside container
docker-compose run --rm evo-mcp bash
```

### Authentication issues
```bash
# Clear token cache and retry
docker volume rm evo-mcp-state
docker-compose up evo-mcp
```

### Permission denied errors
```bash
# Verify volume permissions
docker exec evo-mcp ls -la /app/state
# Should show mcpuser:mcpuser ownership
```

## Production Deployment

### Recommendations

1. **Use secrets management**: Don't commit `.env` (it's git-ignored)
   ```bash
   # Use Docker secrets with swarm/Kubernetes
   # Or environment variable injection at deploy time
   ```

2. **Enable authentication**:
   - Use `client_credentials` auth mode for CI/production
   - Set `EVO_CLIENT_SECRET` via secrets

3. **Resource limits**: Already configured in docker-compose.yml
   - Adjust CPU/memory based on your workload

4. **Logging**: Configure centralized logging
   ```yaml
   logging:
     driver: splunk  # or other centralized logger
     options:
       splunk-token: "${SPLUNK_TOKEN}"
   ```

## Advanced: Custom Builds

### Build for specific architecture
```bash
# Build for ARM64 (Apple Silicon)
docker buildx build --platform linux/arm64 -t evo-mcp:arm64 .

# Build for AMD64
docker buildx build --platform linux/amd64 -t evo-mcp:amd64 .
```

### Build with custom base image
```dockerfile
# Edit Dockerfile to use alternative base:
FROM python:3.11-alpine  # Smallest possible image
```

## Security Considerations

✓ Non-root user execution  
✓ Read-only `/app/data` for input files  
✓ Separate state volume for token/cache  
✓ No sensitive data in image  
✓ Resource limits configured  

⚠️ Still needed:
- Secrets management (don't commit credentials)
- Network isolation (if running multiple containers)
- Regular base image updates
