# Docker Guide for Electoral Search

Complete guide for running Electoral Search in Docker.

## Quick Start

### 1. Build the Image

```bash
# Build the Docker image
docker build -t electoral-search .

# Or using docker-compose
docker-compose build
```

### 2. Run with Docker

```bash
# Basic usage - show help
docker run electoral-search

# Search PDFs (mount volumes)
docker run \
  -v $(pwd)/pdfs:/data:ro \
  -v $(pwd)/names.txt:/names.txt:ro \
  -v $(pwd)/output:/output \
  electoral-search search /data --names-file /names.txt -o /output/results.json
```

### 3. Run with Docker Compose

```bash
# Update docker-compose.yml with your paths, then:
docker-compose run electoral-search

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Detailed Usage

### Building the Image

```bash
# Standard build
docker build -t electoral-search:latest .

# Build with custom tag
docker build -t electoral-search:2.0.0 .

# Build with build args (if needed)
docker build --build-arg POETRY_VERSION=1.7.1 -t electoral-search .

# Check image size
docker images electoral-search
```

### Running Searches

#### Basic Search

```bash
docker run \
  -v /path/to/pdfs:/data:ro \
  -v /path/to/names.txt:/names.txt:ro \
  electoral-search search /data --names-file /names.txt
```

#### With Output File

```bash
docker run \
  -v $(pwd)/pdfs:/data:ro \
  -v $(pwd)/names.txt:/names.txt:ro \
  -v $(pwd)/output:/output \
  electoral-search search /data --names-file /names.txt -o /output/results.json -v
```

#### Custom Configuration

```bash
docker run \
  -e OCR_DPI=400 \
  -e MAX_PDF_SIZE_MB=100 \
  -v $(pwd)/pdfs:/data:ro \
  -v $(pwd)/names.txt:/names.txt:ro \
  electoral-search search /data --names-file /names.txt -t 85
```

### Interactive Shell

```bash
# Start interactive shell
docker run -it electoral-search bash

# Or with docker-compose
docker-compose run electoral-search bash

# Inside container, run commands
electoral-search search /data --names-file /names.txt
```

### Validation

```bash
# Validate Tesseract and system
docker run electoral-search validate
```

## Docker Compose Usage

### Basic Setup

1. **Update `docker-compose.yml`** with your paths:

```yaml
volumes:
  - ./your-pdfs:/data:ro
  - ./your-names.txt:/data/names.txt:ro
  - ./your-output:/output
```

2. **Run the search**:

```bash
docker-compose run electoral-search
```

### Common Commands

```bash
# Build
docker-compose build

# Run search (one-time)
docker-compose run electoral-search search /data --names-file /data/names.txt

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f electoral-search

# Stop
docker-compose down

# Rebuild and run
docker-compose up --build

# Clean up
docker-compose down -v
```

### Debug Mode

```bash
# Start debug shell (defined in docker-compose.yml)
docker-compose --profile debug run electoral-search-shell
```

## Volume Mapping

The Docker container uses three main mount points:

| Mount Point | Purpose | Recommended Mapping |
|-------------|---------|-------------------|
| `/data` | PDF files directory | `-v $(pwd)/pdfs:/data:ro` |
| `/output` | Results output | `-v $(pwd)/output:/output` |
| `/data/names.txt` | Search names file | `-v $(pwd)/names.txt:/data/names.txt:ro` |

### Example Directory Structure

```
project/
├── pdfs/              # Your PDF files
│   ├── roll_001.pdf
│   └── roll_002.pdf
├── names.txt          # Search names (UTF-8)
└── output/            # Results go here
    └── results.json
```

### Volume Mapping Command

```bash
docker run \
  -v $(pwd)/pdfs:/data:ro \
  -v $(pwd)/names.txt:/data/names.txt:ro \
  -v $(pwd)/output:/output \
  electoral-search search /data --names-file /data/names.txt -o /output/results.json
```

## Environment Variables

Configure the container using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OCR_DPI` | 350 | Image resolution for OCR |
| `OCR_LANG` | ben | Tesseract language |
| `MAX_PDF_SIZE_MB` | 50 | Maximum PDF file size |
| `MAX_PDF_PAGES` | 100 | Maximum pages per PDF |
| `MAX_NAMES_FILE_SIZE_MB` | 10 | Maximum names file size |
| `MAX_SEARCH_NAMES` | 1000 | Maximum search names |

### Using Environment Variables

```bash
# Via command line
docker run \
  -e OCR_DPI=400 \
  -e MAX_PDF_SIZE_MB=100 \
  -v $(pwd)/pdfs:/data:ro \
  electoral-search search /data --names-file /names.txt

# Via .env file
docker-compose --env-file .env up

# In docker-compose.yml
environment:
  - OCR_DPI=400
  - MAX_PDF_SIZE_MB=100
```

## Resource Limits

### CPU and Memory Limits

```bash
# Docker run
docker run \
  --cpus=2 \
  --memory=4g \
  -v $(pwd)/pdfs:/data:ro \
  electoral-search search /data --names-file /names.txt

# Docker compose (already configured in docker-compose.yml)
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

## Troubleshooting

### Check Container Logs

```bash
# Docker
docker logs <container-id>

# Docker Compose
docker-compose logs electoral-search
```

### Validate Installation

```bash
# Check Tesseract
docker run electoral-search validate

# Interactive check
docker run -it electoral-search bash
tesseract --version
tesseract --list-langs
```

### Common Issues

**Issue: "Tesseract not found"**
```bash
# Rebuild image to ensure Tesseract is installed
docker build --no-cache -t electoral-search .
```

**Issue: "Permission denied" on volumes**
```bash
# Fix permissions on host
chmod -R 755 pdfs/
chmod 644 names.txt

# Or run as root (not recommended)
docker run --user root ...
```

**Issue: "Bengali language pack not installed"**
```bash
# Verify in container
docker run electoral-search tesseract --list-langs
```

**Issue: "Out of memory"**
```bash
# Increase memory limit
docker run --memory=8g ...

# Or reduce DPI
docker run -e OCR_DPI=250 ...
```

## Production Deployment

### Best Practices

1. **Use specific version tags**
   ```bash
   docker build -t electoral-search:2.0.0 .
   docker tag electoral-search:2.0.0 electoral-search:latest
   ```

2. **Health checks** (already configured in Dockerfile)
   ```bash
   docker inspect --format='{{json .State.Health}}' <container-id>
   ```

3. **Resource monitoring**
   ```bash
   docker stats electoral-search
   ```

4. **Log rotation**
   ```bash
   docker run --log-opt max-size=10m --log-opt max-file=3 ...
   ```

### Docker Registry

```bash
# Tag for registry
docker tag electoral-search:latest your-registry.com/electoral-search:2.0.0

# Push to registry
docker push your-registry.com/electoral-search:2.0.0

# Pull on another machine
docker pull your-registry.com/electoral-search:2.0.0
```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests (if available), or create:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: electoral-search
spec:
  containers:
  - name: electoral-search
    image: electoral-search:2.0.0
    volumeMounts:
    - name: data
      mountPath: /data
    - name: output
      mountPath: /output
    env:
    - name: OCR_DPI
      value: "350"
  volumes:
  - name: data
    hostPath:
      path: /path/to/pdfs
  - name: output
    hostPath:
      path: /path/to/output
```

## Performance Tips

1. **Optimize DPI**: Lower DPI = faster processing
   ```bash
   docker run -e OCR_DPI=250 ...
   ```

2. **Limit resources**: Prevent OOM
   ```bash
   docker run --memory=4g --cpus=2 ...
   ```

3. **Use volumes**: Don't copy large files into image
   ```bash
   -v $(pwd)/large-dataset:/data:ro
   ```

4. **Batch processing**: Process multiple PDFs in one run
   ```bash
   # Put all PDFs in one directory
   docker run -v $(pwd)/all-pdfs:/data ...
   ```

## Security Considerations

1. **Non-root user**: Container runs as user `electoral` (UID 1000)
2. **Read-only volumes**: Use `:ro` flag for input data
3. **Resource limits**: Prevent DoS attacks
4. **No secrets in image**: Use environment variables or secrets
5. **Minimal base image**: Uses slim Python image
6. **Health checks**: Automatic container health monitoring

## Examples

### Example 1: Single PDF

```bash
docker run \
  -v $(pwd)/sample.pdf:/data/sample.pdf:ro \
  -v $(pwd)/names.txt:/names.txt:ro \
  electoral-search search /data --names-file /names.txt
```

### Example 2: Batch Processing

```bash
docker run \
  -v $(pwd)/electoral-rolls:/data:ro \
  -v $(pwd)/names.txt:/names.txt:ro \
  -v $(pwd)/results:/output \
  electoral-search search /data --names-file /names.txt -o /output/batch-results.json -v
```

### Example 3: High Quality OCR

```bash
docker run \
  -e OCR_DPI=400 \
  --memory=8g \
  -v $(pwd)/pdfs:/data:ro \
  -v $(pwd)/names.txt:/names.txt:ro \
  electoral-search search /data --names-file /names.txt -t 90
```

### Example 4: CI/CD Pipeline

```bash
# In CI/CD script
docker build -t electoral-search:$CI_COMMIT_SHA .
docker run \
  -v $CI_PROJECT_DIR/test-data:/data:ro \
  -v $CI_PROJECT_DIR/test-names.txt:/names.txt:ro \
  electoral-search search /data --names-file /names.txt
```

## Support

For issues and questions:
- Check container logs: `docker logs <container>`
- Validate installation: `docker run electoral-search validate`
- Interactive debug: `docker run -it electoral-search bash`
- See main README.md for application-specific help
