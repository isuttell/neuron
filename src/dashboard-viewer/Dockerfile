# Build stage for frontend
FROM node:22-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source files
COPY . .

# Build the frontend
RUN npm run build

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry==2.1.3

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main --no-root

# Copy the module and test files
COPY dashboard_viewer/ ./dashboard_viewer/
COPY test-ws.html .

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/dist ./dist

# Environment variables with defaults
ENV IMAGE_URL="https://ha.zaks.io/local/dashboard-art.png" \
    PORT=8000 \
    HOST=0.0.0.0

EXPOSE 8000

CMD ["poetry", "run", "dashboard-viewer"]
