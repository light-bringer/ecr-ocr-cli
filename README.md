# Electoral Roll OCR Search

A production-ready Python CLI tool for searching scanned Bengali electoral roll PDFs using OCR (Optical Character Recognition).

## Features

- 🔍 **OCR-based search** using Tesseract with Bengali language support
- 🎯 **Fuzzy matching** to handle OCR variations and typos
- 🛡️ **Security hardened** with path validation and resource limits
- 📊 **Progress tracking** with rich terminal output
- 📝 **Comprehensive logging** for debugging and auditing
- 💾 **JSON export** capability for results
- ⚡ **Resource limits** to prevent DoS and memory exhaustion
- 🧪 **Full test coverage** with pytest

## Prerequisites

### System Dependencies

The following must be installed on your system:

1. **Tesseract OCR** with Bengali language support
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install tesseract-ocr tesseract-ocr-ben poppler-utils

   # macOS
   brew install tesseract tesseract-lang poppler

   # Verify installation
   tesseract --version
   tesseract --list-langs | grep ben
   ```

2. **Python 3.14+**
   ```bash
   python3 --version
   ```

## Installation

### Method 1: Docker (Easiest, Recommended for Production)

```bash
# Build the Docker image
docker build -t electoral-search .

# Run with Docker
docker run \
  -v $(pwd)/pdfs:/data:ro \
  -v $(pwd)/names.txt:/names.txt:ro \
  -v $(pwd)/output:/output \
  electoral-search search /data --names-file /names.txt -o /output/results.json

# Or use Docker Compose
docker-compose up

# See DOCKER.md for complete Docker guide
```

### Method 2: Using Poetry (For Development)

```bash
# Clone the repository
git clone <repository-url>
cd ecr-ocr-cli

# Install dependencies and create virtual environment
poetry install

# Verify installation
poetry run electoral-search --help

# Or activate the virtual environment
poetry shell
electoral-search --help
```

### Method 3: Install Globally

```bash
cd ecr-ocr-cli

# Install the package globally
poetry build
pip install dist/electoral_search-2.0.0-py3-none-any.whl

# Now use anywhere
electoral-search --help
```

### Method 4: Development Mode

```bash
# Install with development dependencies
poetry install --with dev

# Access development tools
poetry run pytest
poetry run black electoral_search/
poetry run mypy electoral_search/
```

## Usage

### Basic Usage

```bash
# Using Poetry (recommended)
poetry run electoral-search search /path/to/pdfs --names-file names.txt

# Or activate Poetry shell first
poetry shell
electoral-search search /path/to/pdfs --names-file names.txt

# Direct script (no installation needed)
python run.py search /path/to/pdfs --names-file names.txt

# As module
python -m electoral_search.cli search /path/to/pdfs --names-file names.txt
```

### Command Line Options

```
Arguments:
  DIRECTORY              Directory containing PDF files to process

Options:
  -n, --names-file PATH  File with Bengali names (UTF-8 encoded) [required]
  -t, --threshold INT    Fuzzy match threshold (0-100) [default: 82]
  -v, --verbose          Enable verbose logging
  -o, --output-json PATH Save results to JSON file
  --help                 Show this message and exit
```

### Examples

1. **Basic search**
   ```bash
   poetry run electoral-search search ./electoral_rolls --names-file search_names.txt
   # Or: python run.py search ./electoral_rolls --names-file search_names.txt
   ```

2. **Adjust matching sensitivity**
   ```bash
   # Lower threshold = more matches but more false positives
   poetry run electoral-search search ./pdfs -n names.txt -t 75

   # Higher threshold = fewer matches but more accurate
   poetry run electoral-search search ./pdfs -n names.txt -t 90
   ```

3. **Save results to JSON**
   ```bash
   poetry run electoral-search search ./pdfs -n names.txt -o results.json
   ```

4. **Verbose logging for debugging**
   ```bash
   poetry run electoral-search search ./pdfs -n names.txt -v
   ```

### Input File Format

**names.txt** (UTF-8 encoded, one name per line):
```
রহিম আলী
ফাতিমা খাতুন
আবদুল করিম
সালমা বেগম
```

### Output

The tool displays:
- Rich formatted table of matches
- Processing statistics (files, pages, matches)
- Error summary if any failures occurred
- Optional JSON export of all results

Example output:
```
Processing 5 PDFs...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                Electoral Roll Matches (3 found)
┏━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ PDF File     ┃ Page ┃ Name         ┃ Father / Guardian  ┃
┡━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ roll_001.pdf │    2 │ রহিম আলী     │ করিম আলী           │
│ roll_003.pdf │    5 │ ফাতিমা খাতুন │ রহিম আলী           │
│ roll_005.pdf │    1 │ সালমা বেগম   │ জাহিদ হাসান        │
└──────────────┴──────┴──────────────┴────────────────────┘

Processing Statistics:
  Files processed: 5
  Files failed: 0
  Pages processed: 87
  Matches found: 3
```

## Configuration

The tool can be configured via environment variables:

```bash
# OCR settings
export OCR_DPI=350              # Image resolution (default: 350)
export OCR_LANG=ben             # Tesseract language (default: ben)

# Resource limits
export MAX_PDF_SIZE_MB=50       # Max PDF file size (default: 50)
export MAX_PDF_PAGES=100        # Max pages per PDF (default: 100)
export MAX_NAMES_FILE_SIZE_MB=10  # Max names file size (default: 10)
export MAX_SEARCH_NAMES=1000    # Max number of names to search (default: 1000)
```

## Security Features

- **Path validation**: Prevents directory traversal attacks
- **File size limits**: Protects against resource exhaustion
- **PDF validation**: Verifies magic number before processing
- **Bounded regex**: ReDoS attack prevention
- **Timeout protection**: OCR operations timeout after 30 seconds per page
- **Resource cleanup**: Automatic image cleanup to prevent memory leaks

## Project Structure

The codebase is organized into a modular package structure:

```
electoral_search/
├── __init__.py          # Package initialization and exports
├── config.py            # Configuration and constants
├── types.py             # Type definitions (VoterInfo, SearchResult)
├── validation.py        # Input validation and security
├── text_processing.py   # Bengali text processing and fuzzy matching
├── ocr.py              # OCR and PDF processing
└── cli.py              # Command-line interface

tests/
├── __init__.py
├── test_config.py
├── test_validation.py
└── test_text_processing.py

run.py                   # Main entry point (direct execution)
pyproject.toml          # Poetry configuration and dependencies
poetry.lock             # Locked dependency versions (auto-generated)
Dockerfile              # Docker image definition
docker-compose.yml      # Docker Compose configuration
docker-entrypoint.sh    # Docker entrypoint script
.dockerignore           # Docker build exclusions
README.md               # This file
DOCKER.md               # Complete Docker guide
QUICKSTART.md           # 5-minute getting started guide
CLAUDE.md               # Development guide for Claude Code
PRODUCTION_IMPROVEMENTS.md  # Summary of all improvements made
```

## Development

### Running Tests

```bash
# Run all tests with coverage
poetry run pytest

# Run specific test module
poetry run pytest tests/test_text_processing.py -v

# Run with verbose output
poetry run pytest -v

# Generate HTML coverage report
poetry run pytest --cov-report=html
open htmlcov/index.html
```

### Code Quality

```bash
# Format code with Black
poetry run black electoral_search/ tests/

# Lint with Ruff (fast linter)
poetry run ruff check electoral_search/

# Type checking with mypy
poetry run mypy electoral_search/

# Security scanning with Bandit
poetry run bandit -r electoral_search/

# Run all quality checks
poetry run black --check electoral_search/ && \
poetry run ruff check electoral_search/ && \
poetry run mypy electoral_search/ && \
poetry run bandit -r electoral_search/
```

### Dependency Management

```bash
# Add a new dependency
poetry add package-name

# Add a development dependency
poetry add --group dev package-name

# Update all dependencies
poetry update

# Show dependency tree
poetry show --tree

# Export requirements.txt (if needed for legacy systems)
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

## Troubleshooting

### Tesseract Not Found

**Error**: `TesseractNotFoundError: tesseract is not installed`

**Solution**: Install Tesseract OCR (see Prerequisites section)

### Bengali Language Pack Missing

**Error**: `Error opening data file...ben.traineddata`

**Solution**: Install Bengali language pack
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr-ben

# macOS (included in tesseract-lang)
brew install tesseract-lang
```

### Out of Memory

**Error**: `MemoryError` or process killed

**Solution**: Reduce DPI or limit PDF pages
```bash
export OCR_DPI=200
export MAX_PDF_PAGES=50
```

### Poor OCR Accuracy

**Solutions**:
1. Increase DPI: `export OCR_DPI=400`
2. Lower fuzzy match threshold: `-t 75`
3. Ensure PDFs are high quality scans
4. Check Tesseract language pack is installed correctly

### No Matches Found

**Check**:
1. Names file is UTF-8 encoded
2. Names match the format in PDFs
3. Threshold isn't too high (try `-t 70`)
4. PDF text is extractable (not image-only without proper OCR)

## Performance Considerations

- **Processing time**: ~5-10 seconds per page at 350 DPI
- **Memory usage**: ~100MB per page being processed
- **Optimal DPI**: 300-350 (balance between accuracy and speed)
- **Large batches**: Process in smaller batches to manage memory

## Logging

Logs are written to both console and `electoral_search.log`:

- `INFO`: Processing progress and matches
- `WARNING`: Non-critical issues (timeouts, limits)
- `ERROR`: Processing failures
- `DEBUG`: Detailed OCR and matching information (use `-v` flag)

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues and questions:
- Check the Troubleshooting section
- Review logs in `electoral_search.log`
- Open an issue on GitHub with:
  - Error messages
  - Command used
  - System information
  - Log file excerpt
