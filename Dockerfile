FROM python:3.12-slim-bookworm AS server-builder

ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
  apt-get -y upgrade && \
  apt-get -y install \
  curl \
  git && \
  rm -rf /var/lib/apt/lists/*


# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
  && mv ~/.local/bin/poetry /usr/local/bin/

ENV POETRY_NO_INTERACTION=true
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Set working directory
WORKDIR /app

# Copy only the dependency files to leverage Docker cache
COPY ["pyproject.toml", "poetry.lock", "./"]

# Install dependencies
RUN poetry install --no-root --no-interaction --no-ansi

FROM python:3.12-slim-bookworm

ENV PATH="/app/.venv/bin:$PATH"
ENV PORT=5000

RUN apt-get update && \
  apt-get install -qy ca-certificates curl ffmpeg unzip && \
  install -m 0755 -d /etc/apt/keyrings && \
  curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
  chmod a+r /etc/apt/keyrings/docker.asc && \
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
  apt-get update && \
  apt-get -qy upgrade && \
  apt-get -qy install docker-ce docker-ce-cli containerd.io && \
  rm -rf /var/lib/apt/lists/*

# Install Deno
RUN curl -fsSL https://deno.land/install.sh | sh && \
  mv ~/.deno/bin/deno /usr/local/bin/

# Set working directory
WORKDIR /app

COPY --from=server-builder /app/.venv /app/.venv
COPY src/neuron_server /app/src/neuron_server
COPY pyproject.toml /app/pyproject.toml

RUN pip install -e .

RUN useradd -m neuron -d /app -G systemd-journal && \
  chown neuron /app

USER neuron

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:$PORT/status || exit 1

ENTRYPOINT [ "python" ]

CMD ["-m", "neuron_server"]
