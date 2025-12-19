# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a production-ready Python CLI tool for searching scanned Bengali electoral roll PDFs using OCR (Optical Character Recognition). The tool has been hardened for security, includes comprehensive error handling, logging, and resource management.

## Development Setup

### Prerequisites

- Python 3.8+
- Tesseract OCR with Bengali language support (`tesseract-ocr-ben`)
- Poppler utilities (for pdf2image)
- Virtual environment at `.venv/`

### Install Dependencies

```bash
# Using Poetry (recommended)
poetry install

# Install with development dependencies
poetry install --with dev

# Alternative: Direct execution (no installation)
# Dependencies are specified in pyproject.toml
python run.py --help
```

### Running the Tool

```bash
# Using Poetry
poetry run electoral-search search <directory> --names-file <names.txt> [options]

# Or direct execution
python run.py search <directory> --names-file <names.txt> [options]
```

**Key Options:**
- `-n, --names-file`: Text file with Bengali names (UTF-8 encoded) [required]
- `-t, --threshold`: Fuzzy match threshold 0-100 (default: 82)
- `-v, --verbose`: Enable debug logging
- `-o, --output-json`: Save results to JSON file

### Running Tests

```bash
# Run all tests with Poetry
poetry run pytest

# With coverage
poetry run pytest --cov=electoral_search --cov-report=html

# Run specific test
poetry run pytest tests/test_text_processing.py -v
```

## Architecture

### Production Features

**Security Hardening:**
- Path validation prevents directory traversal attacks (validate_path_security)
- File size limits prevent DoS (MAX_PDF_SIZE_MB, MAX_NAMES_FILE_SIZE_MB)
- PDF magic number validation prevents processing of fake PDFs
- Bounded regex patterns prevent ReDoS attacks
- Resource cleanup prevents memory leaks

**Error Handling:**
- Comprehensive exception handling in process_pdf()
- Graceful degradation: single file failures don't stop batch processing
- Detailed error logging with ProcessingStats tracking
- OCR timeout protection (30s per page)
- Clear error messages for missing dependencies

**Logging and Monitoring:**
- Structured logging to both file (electoral_search.log) and console
- Processing statistics (files, pages, matches, errors)
- Progress bars for long-running operations
- Configurable log levels (INFO/DEBUG via -v flag)

### Core Components

**OCR Processing Flow** (process_pdf function):
1. PDF validation (size, magic number, accessibility)
2. PDFs converted to images at configurable DPI (default: 350)
3. OCR with Tesseract using Bengali language model + PSM 6
4. Voter information extraction via regex patterns
5. Fuzzy matching against search names
6. Resource cleanup (image objects closed)

**Text Normalization** (normalize_bn):
- Uses str.translate() for performance (faster than multiple .replace())
- Removes visarga (ঃ), danda (।), halant (্), and spaces
- Critical for handling OCR variations in Bengali text
- Applied before fuzzy matching

**Fuzzy Matching** (fuzzy_match):
- RapidFuzz token_set_ratio algorithm
- Normalized text comparison
- Configurable threshold (0-100)
- Default 82 balances precision/recall

**Pattern Matching** (extract_voter_blocks):
- Regex patterns with bounded quantifiers (prevents ReDoS)
- Matches "নাম :" (name) and "পিতার নাম :" / "স্বামীর নাম :" (father/husband)
- Handles both regular (:) and full-width (：) colons
- Returns typed VoterInfo dictionaries

### Configuration

**Environment Variables:**
- `OCR_DPI`: Image resolution (default: 350)
- `OCR_LANG`: Tesseract language (default: "ben")
- `MAX_PDF_SIZE_MB`: Max PDF file size (default: 50)
- `MAX_PDF_PAGES`: Max pages per PDF (default: 100)
- `MAX_NAMES_FILE_SIZE_MB`: Max names file size (default: 10)
- `MAX_SEARCH_NAMES`: Max search names (default: 1000)

**Constants:**
- `OCR_CONFIG = "--psm 6"`: Page segmentation mode (uniform text block)
- `FUZZY_THRESHOLD_DEFAULT = 82`: Default matching threshold
- All configurable at runtime via environment variables

### Type Safety

The codebase uses comprehensive type hints:
- `VoterInfo`: TypedDict for voter data structure
- `SearchResult`: TypedDict for match results
- `ProcessingStats`: dataclass for tracking statistics
- Proper typing on all function signatures

## Important Implementation Notes

### Bengali Text Processing
- **UTF-8 encoding required** for all text files
- Normalization is critical for OCR variation handling
- Regex patterns tuned for standard electoral roll format
- Both "পিতার নাম" (father) and "স্বামীর নাম" (husband) supported

### Performance Considerations
- **Sequential processing**: No parallelization (memory safety)
- **DPI tradeoff**: Higher DPI = better accuracy but slower/more memory
  - 200 DPI: Fast, lower accuracy
  - 350 DPI: Balanced (default)
  - 400+ DPI: Slow, highest accuracy
- **Memory usage**: ~100MB per page at 350 DPI
- **Processing speed**: ~5-10 seconds per page
- Images explicitly closed after processing to free memory

### Error Recovery
- File-level errors don't stop batch processing
- OCR timeouts skip page and continue
- All errors logged with context
- Statistics track successes and failures

### Testing Strategy
- Unit tests for text processing functions
- Mock-based tests for OCR operations
- Integration tests with temporary files
- Security tests for path validation
- Coverage target: >80%

## Common Development Tasks

### Adding New OCR Languages

1. Install Tesseract language pack
2. Set environment variable: `export OCR_LANG=<lang_code>`
3. Update regex patterns in extract_voter_blocks for language-specific formats
4. Update normalization in normalize_bn for language-specific characters

### Adjusting Performance

```bash
# Faster processing (lower quality)
export OCR_DPI=200
export MAX_PDF_PAGES=50

# Higher quality (slower)
export OCR_DPI=400
```

### Debugging OCR Issues

```bash
# Enable verbose logging
python electoral_search.py search ./pdfs -n names.txt -v

# Check logs
tail -f electoral_search.log
```

### Modifying Resource Limits

Edit environment variables or modify constants at top of electoral_search.py:
- MAX_PDF_SIZE_MB: PDF file size limit
- MAX_PDF_PAGES: Pages per PDF limit
- MAX_SEARCH_NAMES: Maximum names to search

## Security Considerations

- **Never disable path validation** - prevents directory traversal
- **Keep resource limits** - prevents DoS attacks
- **Validate file types** - magic number check prevents fake PDFs
- **Use timeouts** - prevents hanging on malformed files
- **Clean up resources** - prevents memory leaks
- **Pin dependencies** - ensures reproducible builds and security patches

## Troubleshooting

**Tesseract not found:**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-ben

# macOS
brew install tesseract tesseract-lang
```

**Poor OCR accuracy:**
- Increase DPI: `export OCR_DPI=400`
- Lower threshold: `-t 75`
- Check PDF quality and Bengali language pack

**Out of memory:**
- Reduce DPI: `export OCR_DPI=200`
- Limit pages: `export MAX_PDF_PAGES=50`
- Process fewer PDFs at once
