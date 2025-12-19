# Quick Start Guide

Get started with electoral search in 5 minutes.

## Prerequisites

Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-ben poppler-utils

# macOS
brew install tesseract tesseract-lang poppler
```

## Installation

### Option 1: Using Docker (Easiest)

```bash
# Build Docker image
docker build -t electoral-search .

# Verify installation
docker run electoral-search --help

# See DOCKER.md for complete guide
```

### Option 2: Using Poetry (For Development)

```bash
# Install Poetry first
curl -sSL https://install.python-poetry.org | python3 -

# Clone and setup
git clone <repository-url>
cd ecr-ocr-cli
poetry install

# Verify
poetry run electoral-search --help
```

### Option 3: Direct Execution (No Poetry)

```bash
# Clone repository
git clone <repository-url>
cd ecr-ocr-cli

# Run directly (dependencies auto-detected from pyproject.toml)
python run.py --help
```

## Basic Usage

### 1. Prepare Your Files

Create a names file (UTF-8, one name per line):

```text
রহিম আলী
ফাতিমা খাতুন
আবদুল করিম
```

Save as `names.txt`

### 2. Run Search

```bash
# Using Poetry
poetry run electoral-search search /path/to/pdfs --names-file names.txt

# Or activate shell first
poetry shell
electoral-search search /path/to/pdfs --names-file names.txt

# Direct execution (no Poetry needed)
python run.py search /path/to/pdfs --names-file names.txt
```

### 3. View Results

Results display in a formatted table:
```
Electoral Roll Matches (3 found)
┏━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ PDF File     ┃ Page ┃ Name         ┃ Father / Guardian  ┃
┡━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ roll_001.pdf │    2 │ রহিম আলী     │ করিম আলী           │
...
```

## Common Options

```bash
# Lower threshold for more matches
poetry run electoral-search search ./pdfs -n names.txt -t 75

# Save to JSON
poetry run electoral-search search ./pdfs -n names.txt -o results.json

# Save to CSV
poetry run electoral-search search ./pdfs -n names.txt -o results.csv

# Enable box-level OCR with bounding boxes
poetry run electoral-search search ./pdfs -n names.txt --box-level -o results.json

# Filter by confidence threshold
poetry run electoral-search search ./pdfs -n names.txt --box-level --min-confidence 80

# Verbose mode for debugging
poetry run electoral-search search ./pdfs -n names.txt -v

# Combine options for high-quality results
poetry run electoral-search search ./pdfs -n names.txt \
  --box-level \
  --min-confidence 85 \
  -o results.json \
  -v
```

## Configuration (Optional)

Set environment variables to customize:

```bash
export OCR_DPI=300              # Faster processing
export MAX_PDF_SIZE_MB=100      # Larger file limit
export MAX_PDF_PAGES=200        # More pages per PDF
```

## Troubleshooting

**Tesseract not found?**
```bash
tesseract --version
tesseract --list-langs | grep ben
```

**Poor OCR accuracy?**
```bash
# Increase DPI
export OCR_DPI=400
electoral-search search ./pdfs -n names.txt -t 75
```

**Need help?**
```bash
poetry run electoral-search search --help
# Or: python run.py search --help
```

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [CLAUDE.md](CLAUDE.md) for development guide
- See [PRODUCTION_IMPROVEMENTS.md](PRODUCTION_IMPROVEMENTS.md) for features

## Support

- Check logs: `tail -f electoral_search.log`
- Enable verbose mode: `-v` flag
- Review error messages in statistics summary
