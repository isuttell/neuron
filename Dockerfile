FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
  apt-get -y upgrade && \
  apt-get -y install \
  curl \
  git

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy only the dependency files to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-root

# Copy the rest of the application code
COPY . .

# Install the application
RUN poetry install

ENTRYPOINT [ "python" ]

CMD ["-m", "neuron_server"]

