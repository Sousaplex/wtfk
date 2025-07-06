#!/bin/bash

# PostgreSQL Schema Analysis Archive Script
# Archives completed analysis results and cleans working files

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
PostgreSQL Schema Analysis Archive Script

Usage: $0 [OPTIONS] [archive_name]

Arguments:
    archive_name    Optional name for the archive (default: auto-generated timestamp)

Options:
    -h, --help      Show this help message
    -l, --list      List existing archives
    -k, --keep      Keep working files (don't clean)
    -f, --force     Force archive even if output directory is incomplete

Examples:
    # Archive with auto-generated name
    $0
    
    # Archive with custom name
    $0 ecommerce_analysis_v1
    
    # Archive but keep working files
    $0 --keep my_analysis
    
    # List existing archives
    $0 --list

Description:
    This script archives a completed analysis by:
    1. Creating a timestamped subdirectory in archive/
    2. Moving all results from output/ to the archive
    3. Moving processed schemas and context files
    4. Cleaning working directories (unless --keep specified)
    5. Preserving original/schema.sql

EOF
}

# Function to list existing archives
list_archives() {
    print_status "Existing archives:"
    
    if [[ ! -d "archive" ]]; then
        echo "  No archives found (archive/ directory doesn't exist)"
        return
    fi
    
    local count=0
    for archive_dir in archive/*/; do
        if [[ -d "$archive_dir" ]]; then
            local dir_name=$(basename "$archive_dir")
            local file_count=$(find "$archive_dir" -type f | wc -l)
            local size=$(du -sh "$archive_dir" 2>/dev/null | cut -f1)
            echo "  📁 $dir_name ($file_count files, $size)"
            count=$((count + 1))
        fi
    done
    
    if [[ $count -eq 0 ]]; then
        echo "  No archives found"
    else
        echo ""
        echo "Total archives: $count"
    fi
}

# Function to validate output directory
validate_output() {
    print_status "Checking for analysis results..."
    
    # Check if any working directories have content
    local has_output=false
    local content_summary=()
    
    # Check output directory for any analysis files
    if [[ -d "output" ]]; then
        local analysis_files=$(find output -name "schema_analysis*.md" 2>/dev/null | wc -l)
        local report_files=$(find output -name "*report*.md" 2>/dev/null | wc -l)
        local diagram_files=$(find output/diagrams -name "*.png" 2>/dev/null | wc -l)
        local json_files=$(find output -name "*.json" 2>/dev/null | wc -l)
        local pdf_files=$(find output -name "*.pdf" 2>/dev/null | wc -l)
        
        if [[ $analysis_files -gt 0 ]]; then
            has_output=true
            content_summary+=("Analysis reports: $analysis_files")
        fi
        if [[ $report_files -gt 0 ]]; then
            has_output=true
            content_summary+=("Final reports: $report_files")
        fi
        if [[ $diagram_files -gt 0 ]]; then
            has_output=true
            content_summary+=("Diagrams: $diagram_files")
        fi
        if [[ $json_files -gt 0 ]]; then
            has_output=true
            content_summary+=("JSON files: $json_files")
        fi
        if [[ $pdf_files -gt 0 ]]; then
            has_output=true
            content_summary+=("PDF reports: $pdf_files")
        fi
    fi
    
    # Check schemas directory
    if [[ -d "schemas" ]]; then
        local schema_files=$(find schemas -name "*.sql" -o -name "*.txt" 2>/dev/null | wc -l)
        if [[ $schema_files -gt 0 ]]; then
            has_output=true
            content_summary+=("Processed schemas: $schema_files")
        fi
    fi
    
    # Check context directory
    if [[ -d "context" ]]; then
        local context_files=$(find context -name "*.json" 2>/dev/null | wc -l)
        if [[ $context_files -gt 0 ]]; then
            has_output=true
            content_summary+=("Context files: $context_files")
        fi
    fi
    
    if [[ "$has_output" == false ]]; then
        print_error "No analysis results found in working directories"
        print_error "Working directories appear empty:"
        echo "  - output/ - No analysis reports, diagrams, or JSON files found"
        echo "  - schemas/ - No processed schema files found"
        echo "  - context/ - No context files found"
        echo ""
        print_error "Run the analysis pipeline first: ./run_analysis.sh"
        return 1
    fi
    
    # Show what was found
    print_success "Found analysis results:"
    for item in "${content_summary[@]}"; do
        echo "  ✓ $item"
    done
    echo ""
    
    return 0
}

# Function to create archive
create_archive() {
    local archive_name="$1"
    local keep_files="$2"
    
    # Generate archive name if not provided
    if [[ -z "$archive_name" ]]; then
        archive_name="analysis_$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Clean archive name (remove invalid characters)
    archive_name=$(echo "$archive_name" | sed 's/[^a-zA-Z0-9_-]/_/g')
    
    local archive_dir="archive/$archive_name"
    
    print_status "Creating archive: $archive_name"
    
    # Create archive directory
    mkdir -p "$archive_dir"
    
    # Archive main results
    if [[ -d "output" ]]; then
        print_status "Archiving output files..."
        cp -r output/* "$archive_dir/"
        
        # Count files archived
        local output_files=$(find output -type f | wc -l)
        print_success "Archived $output_files output files"
    fi
    
    # Archive processed schemas
    if [[ -d "schemas" ]]; then
        print_status "Archiving processed schemas..."
        mkdir -p "$archive_dir/schemas"
        cp schemas/* "$archive_dir/schemas/" 2>/dev/null || true
        
        local schema_files=$(find schemas -type f 2>/dev/null | wc -l)
        if [[ $schema_files -gt 0 ]]; then
            print_success "Archived $schema_files schema files"
        fi
    fi
    
    # Archive context data
    if [[ -d "context" ]]; then
        print_status "Archiving context data..."
        mkdir -p "$archive_dir/context"
        cp context/* "$archive_dir/context/" 2>/dev/null || true
        
        local context_files=$(find context -type f 2>/dev/null | wc -l)
        if [[ $context_files -gt 0 ]]; then
            print_success "Archived $context_files context files"
        fi
    fi
    
    # Archive configuration used
    if [[ -f "settings.json" ]]; then
        print_status "Archiving configuration..."
        cp settings.json "$archive_dir/"
        print_success "Archived settings.json"
    fi
    
    # Archive prompt logs if they exist
    if [[ -f output/visualization_prompt_log_*.txt ]]; then
        print_status "Archiving prompt logs..."
        # Already copied with output directory
        local log_count=$(find output -name "visualization_prompt_log_*.txt" 2>/dev/null | wc -l)
        if [[ $log_count -gt 0 ]]; then
            print_success "Archived $log_count prompt log files"
        fi
    fi
    
    # Create archive metadata
    print_status "Creating archive metadata..."
    
    # Generate dynamic content listing
    local content_sections=""
    
    # Analysis Results section
    if [[ -d "$archive_dir" ]]; then
        local analysis_files=$(find "$archive_dir" -name "schema_analysis*.md" 2>/dev/null)
        local report_files=$(find "$archive_dir" -name "*report*.md" 2>/dev/null)
        local pdf_files=$(find "$archive_dir" -name "*.pdf" 2>/dev/null)
        local json_files=$(find "$archive_dir" -name "*.json" 2>/dev/null)
        
        if [[ -n "$analysis_files" || -n "$report_files" || -n "$pdf_files" ]]; then
            content_sections+="### Analysis Results"$'\n'
            if [[ -n "$analysis_files" ]]; then
                while IFS= read -r file; do
                    local basename=$(basename "$file")
                    content_sections+="- \`$basename\` - AI analysis report"$'\n'
                done <<< "$analysis_files"
            fi
            if [[ -n "$report_files" ]]; then
                while IFS= read -r file; do
                    local basename=$(basename "$file")
                    content_sections+="- \`$basename\` - Final comprehensive report"$'\n'
                done <<< "$report_files"
            fi
            if [[ -n "$pdf_files" ]]; then
                while IFS= read -r file; do
                    local basename=$(basename "$file")
                    content_sections+="- \`$basename\` - Professional PDF report"$'\n'
                done <<< "$pdf_files"
            fi
            if [[ -d "$archive_dir/diagrams" ]]; then
                local diagram_count=$(find "$archive_dir/diagrams" -name "*.png" 2>/dev/null | wc -l)
                if [[ $diagram_count -gt 0 ]]; then
                    content_sections+="- \`diagrams/\` - Generated visualizations ($diagram_count images)"$'\n'
                fi
            fi
            if [[ -n "$json_files" ]]; then
                content_sections+="- \`*.json\` - Configuration and planning files"$'\n'
            fi
            content_sections+=$'\n'
        fi
        
        # Processed Data section
        if [[ -d "$archive_dir/schemas" || -d "$archive_dir/context" ]]; then
            content_sections+="### Processed Data"$'\n'
            if [[ -d "$archive_dir/schemas" ]]; then
                local schema_count=$(find "$archive_dir/schemas" -type f 2>/dev/null | wc -l)
                content_sections+="- \`schemas/\` - Extracted and compressed schema files ($schema_count files)"$'\n'
            fi
            if [[ -d "$archive_dir/context" ]]; then
                local context_count=$(find "$archive_dir/context" -type f 2>/dev/null | wc -l)
                content_sections+="- \`context/\` - Statistical analysis and context data ($context_count files)"$'\n'
            fi
            content_sections+=$'\n'
        fi
        
        # Configuration section
        if [[ -f "$archive_dir/settings.json" ]]; then
            content_sections+="### Configuration"$'\n'
            content_sections+="- \`settings.json\` - Analysis configuration used"$'\n'
            content_sections+=$'\n'
        fi
    fi
    
    cat > "$archive_dir/ARCHIVE_INFO.md" << EOF
# Schema Analysis Archive

**Archive Name:** $archive_name  
**Created:** $(date)  
**Original Schema:** $(ls original/*.sql 2>/dev/null | head -1 || echo "Not found")

## Contents

$content_sections

## Archive Statistics
- Total files: $(find "$archive_dir" -type f | wc -l)
- Archive size: $(du -sh "$archive_dir" | cut -f1)

## Regeneration
To regenerate this analysis:
1. Place the original schema in \`original/schema.sql\`
2. Copy \`settings.json\` to project root
3. Run: \`./run_analysis.sh\`

Generated by WTFK (What The Foreign Key) pipeline
EOF
    
    # Calculate archive size
    local archive_size=$(du -sh "$archive_dir" | cut -f1)
    local total_files=$(find "$archive_dir" -type f | wc -l)
    
    print_success "Archive created successfully!"
    echo "  📁 Location: $archive_dir"
    echo "  📊 Size: $archive_size"
    echo "  📄 Files: $total_files"
    
    # Clean working files if requested
    if [[ "$keep_files" == false ]]; then
        print_status "Cleaning working files..."
        
        # Clean output directory (but keep the directory structure)
        if [[ -d "output" ]]; then
            rm -rf output/*
            print_success "Cleaned output/"
        fi
        
        # Clean schemas directory
        if [[ -d "schemas" ]]; then
            rm -rf schemas/*
            print_success "Cleaned schemas/"
        fi
        
        # Clean context directory
        if [[ -d "context" ]]; then
            rm -rf context/*
            print_success "Cleaned context/"
        fi
        
        print_success "Working files cleaned"
        print_status "Original schema preserved in original/"
    else
        print_status "Working files preserved (--keep specified)"
    fi
    
    echo ""
    print_success "Archive complete: $archive_name"
}

# Parse command line arguments
ARCHIVE_NAME=""
KEEP_FILES=false
LIST_ONLY=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -l|--list)
            LIST_ONLY=true
            shift
            ;;
        -k|--keep)
            KEEP_FILES=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$ARCHIVE_NAME" ]]; then
                ARCHIVE_NAME="$1"
            else
                print_error "Multiple archive names specified"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Main execution
main() {
    print_status "PostgreSQL Schema Analysis Archive Tool"
    print_status "======================================"
    echo ""
    
    # Handle list option
    if [[ "$LIST_ONLY" == true ]]; then
        list_archives
        exit 0
    fi
    
    # Validate output directory unless forced
    if [[ "$FORCE" == false ]]; then
        if ! validate_output; then
            print_error "Use --force to archive incomplete results"
            exit 1
        fi
    else
        print_warning "Forcing archive of potentially incomplete results"
    fi
    
    # Create archive
    create_archive "$ARCHIVE_NAME" "$KEEP_FILES"
    
    echo ""
    print_status "You can now run a new analysis with: ./run_analysis.sh"
}

# Run main function
main 