# Dashboard Viewer

A React-based dashboard image viewer with built-in proxy server that automatically polls for changes and smoothly transitions between images only when they update.

## Features

- **Built-in proxy server** - No CORS configuration needed
- **ETag-based change detection** - Only transitions when image actually changes
- **Smooth transitions** - Crossfade animation between images
- **Zero flicker** - Image updates are preloaded before transitioning
- **Docker ready** - Easy deployment with configurable image URL
- **Full-screen display** - Optimized for dashboard/kiosk displays
- **Debug mode** - Shows current configuration and polling status

## Quick Start

### Using Docker

```bash
# Using docker-compose
IMAGE_URL="https://your-image-url.com/image.png" docker-compose up

# Using docker run
docker run -p 8000:8000 -e IMAGE_URL="https://your-image-url.com/image.png" dashboard-viewer
```

### Local Development

```bash
# Install dependencies
npm install
poetry install

# Start frontend dev server (port 5174)
npm run dev

# In another terminal, start backend with your image URL
IMAGE_URL="https://your-image-url.com/image.png" poetry run python server.py

# Or use both together
IMAGE_URL="https://your-image-url.com/image.png" poetry run python server.py & npm run dev
```

### Building for Production

```bash
# Build frontend
npm run build

# Build Docker image
docker build -t dashboard-viewer .
```

## Configuration

### Backend Environment Variables

- `IMAGE_URL` - **Required**: The URL of the image to display (e.g., `https://ha.zaks.io/local/dashboard-art.png`)
- `PORT` - Port to run the server on (default: `8000`)
- `HOST` - Host to bind to (default: `0.0.0.0`)
- `DEV_MODE` - Enable auto-reload for development (default: `false`)

### Frontend Environment Variables (Build Time)

- `VITE_DASHBOARD_URL` - Override the image endpoint (default: `/image`)
- `VITE_POLL_INTERVAL` - How often to check for updates in milliseconds (default: `30000`)
- `VITE_FADE_DURATION` - Duration of the fade transition in milliseconds (default: `2000`)

## How it Works

1. **Proxy Server**: FastAPI server proxies image requests, eliminating CORS issues
2. **ETag Monitoring**: Frontend sends HEAD requests to check if image has changed
3. **Smart Loading**: Only downloads new image when ETag indicates a change
4. **Smooth Transitions**: Preloads new image before transitioning to prevent flicker
5. **Continuous Monitoring**: Polls at configured interval (default: 30 seconds)

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   Browser   │────▶│ FastAPI Proxy│────▶│ Image Server   │
│  (React App)│◀────│   (ETag OK)  │◀────│ (Home Assistant)│
└─────────────┘     └──────────────┘     └────────────────┘
```

The proxy server serves both the React frontend and proxies image requests, providing a seamless single-origin experience.

## Deployment on Same Server as Home Assistant

When deploying on the same server that hosts your Home Assistant instance, you need to configure the IMAGE_URL to use an internal address:

### Option 1: Using host.docker.internal (Recommended)
```bash
IMAGE_URL="http://host.docker.internal:8123/local/dashboard-art.png" docker-compose up -d
```

### Option 2: Using Docker Bridge IP
```bash
# Find Docker bridge IP (usually 172.17.0.1)
docker network inspect bridge | grep Gateway

# Use it in IMAGE_URL
IMAGE_URL="http://172.17.0.1:8123/local/dashboard-art.png" docker-compose up -d
```

### Option 3: Container-to-Container (if HA is in Docker)
```yaml
# In docker-compose.yml
services:
  dashboard-viewer:
    # ... other config ...
    networks:
      - homeassistant_default  # Join HA's network
    environment:
      - IMAGE_URL=http://homeassistant:8123/local/dashboard-art.png
```

### Common Issues

1. **Connection refused**: The container can't reach ha.zaks.io when running on the same host because Docker doesn't route external IPs back to the host.

2. **CORS errors**: Should not occur with the proxy setup, but if they do, ensure you're accessing the dashboard viewer through its served URL, not directly opening the HTML file.

3. **Image not loading**: Check Docker logs for connection errors:
   ```bash
   docker logs dashboard-viewer -f
   ```
