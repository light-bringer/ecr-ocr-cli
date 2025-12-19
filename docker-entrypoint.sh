#!/bin/bash
# Docker entrypoint script for electoral-search
# Provides helper functions and validation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored message
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate Tesseract installation
validate_tesseract() {
    log_info "Validating Tesseract OCR installation..."

    if ! command -v tesseract &> /dev/null; then
        log_error "Tesseract OCR not found!"
        exit 1
    fi

    if ! tesseract --list-langs 2>/dev/null | grep -q "ben"; then
        log_error "Bengali language pack not installed!"
        log_info "Available languages: $(tesseract --list-langs 2>&1 | tail -n +2)"
        exit 1
    fi

    log_info "Tesseract version: $(tesseract --version 2>&1 | head -n 1)"
    log_info "Bengali language pack: ✓"
}

# Show usage
show_usage() {
    cat << EOF
Electoral Search Docker Container

Usage:
    docker run electoral-search [OPTIONS] COMMAND

Commands:
    search DIR --names-file FILE    Search PDFs for names
    --help                          Show help
    bash                           Open interactive shell

Examples:
    # Search PDFs in mounted /data directory
    docker run -v \$(pwd)/pdfs:/data -v \$(pwd)/names.txt:/names.txt \\
        electoral-search search /data --names-file /names.txt

    # With output to file
    docker run -v \$(pwd)/pdfs:/data -v \$(pwd)/output:/output \\
        electoral-search search /data --names-file /names.txt -o /output/results.json

    # Interactive shell
    docker run -it electoral-search bash

Environment Variables:
    OCR_DPI                 Image resolution (default: 350)
    OCR_LANG               Tesseract language (default: ben)
    MAX_PDF_SIZE_MB        Max PDF size (default: 50)
    MAX_PDF_PAGES          Max pages per PDF (default: 100)
    MAX_SEARCH_NAMES       Max search names (default: 1000)

EOF
}

# Main entrypoint logic
main() {
    # Validate system
    validate_tesseract

    # Handle special commands
    case "$1" in
        bash|sh|shell)
            log_info "Starting interactive shell..."
            exec /bin/bash
            ;;
        help|--help|-h)
            show_usage
            exit 0
            ;;
        validate)
            log_info "System validation complete!"
            python -c "import electoral_search; print('Electoral search module: ✓')"
            exit 0
            ;;
        *)
            # Run the electoral search command
            log_info "Starting electoral search..."
            log_info "Configuration:"
            log_info "  OCR_DPI: ${OCR_DPI:-350}"
            log_info "  OCR_LANG: ${OCR_LANG:-ben}"
            log_info "  MAX_PDF_SIZE_MB: ${MAX_PDF_SIZE_MB:-50}"

            exec python /app/run.py "$@"
            ;;
    esac
}

# Run main
main "$@"
