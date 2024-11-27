FROM node:20 AS client-builder

WORKDIR /app/src/neuron_client

COPY ["src/neuron_client/package*.json", "."]

RUN npm ci

COPY ["src/neuron_client/", "."]

RUN NODE_ENV=development npx vite build --mode development && \
  rm -rf src/ node_modules/

FROM python:3.11.10-slim-bookworm

# Install system dependencies
RUN apt-get update && \
  apt-get -y upgrade && \
  apt-get -y install \
  curl \
  git \
  ffmpeg && \
  rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy only the dependency files to leverage Docker cache
COPY pyproject.toml  ./

# Install dependencies
RUN mkdir -p src/neuron_server && touch src/neuron_server/__init__.py && pip install .

# Copy the rest of the application code
COPY . .

# Install the application
RUN pip install -e .

COPY --from=client-builder /app/src/neuron_client/dist /app/src/neuron_client/dist

ENV PORT=5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:$PORT/ || exit 1

ENTRYPOINT [ "python" ]

CMD ["-m", "neuron_server"]

