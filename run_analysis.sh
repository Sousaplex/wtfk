#!/bin/bash

# WTFK (What The Foreign Key) - Schema Analysis Pipeline
# Comprehensive script to run the complete analysis workflow

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
INPUT_FILE=""
SKIP_EXTRACT=false
SKIP_COMPRESS=false
SKIP_CONTEXT=false
SKIP_ANALYSIS=false
SKIP_VISUALIZATIONS=false
SKIP_DIAGRAMS=false
SKIP_FINAL_REPORT=false
SKIP_HTML=false
SKIP_PDF=false
GENERATE_PDF=false
VERBOSE=false
SETTINGS_FILE="settings.json"
FRAMEWORKS=()

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

# Function to list available compliance frameworks
list_frameworks() {
    print_status "Available compliance frameworks:"
    local compliance_dir="compliance"
    if [[ -d "$compliance_dir" ]]; then
        for file in "$compliance_dir"/*.md; do
            if [[ -f "$file" ]]; then
                local framework_name=$(basename "$file" .md)
                echo "  - $framework_name"
            fi
        done
    else
        print_warning "Compliance directory not found at: $compliance_dir"
    fi
    exit 0
}

# Function to show usage
show_usage() {
    cat << EOF
WTFK (What The Foreign Key) - Schema Analysis Pipeline

Usage: $0 [OPTIONS] [input_schema_file]

Arguments:
    input_schema_file    Optional: Path to PostgreSQL schema dump file
                        (Default: auto-detects single .sql file in original/ directory)

Options:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -s, --settings FILE     Path to settings.json file (default: settings.json)
    
    Compliance Analysis:
    --frameworks f1 f2...   Space-separated list of compliance frameworks to analyze
    --list-frameworks       List available compliance frameworks and exit

    Pipeline Control:
    --skip-extract          Skip schema extraction (use existing schema_only.sql)
    --skip-compress         Skip schema compression (use existing schema_compressed.txt)
    --skip-context          Skip context generation (use existing context files)
    --skip-analysis         Skip AI analysis (use existing schema_analysis.md)
    --skip-visualizations   Skip visualization planning
    --skip-diagrams         Skip diagram generation
    --skip-final-report     Skip final report generation
    --skip-html             Skip HTML generation
    --pdf                   Generate PDF from HTML (requires HTML-to-PDF converter)
    --skip-pdf              Skip PDF generation (default: PDF is optional)
    
    Quick Options:
    --analysis-only         Run only AI analysis (skips extract, compress, context)
    --visuals-only          Run only visualization pipeline (skips analysis)
    --no-visuals            Run pipeline without visualizations

Examples:
    # Full pipeline with interactive framework selection
    $0
    
    # Run analysis with specific frameworks
    $0 --frameworks gdpr hipaa
    
    # List available frameworks
    $0 --list-frameworks

Requirements:
    - Exactly one .sql file must exist in original/ directory
    - File should be named schema.sql (recommended)

EOF
}

# Function to detect and validate schema file
detect_schema_file() {
    print_status "Detecting schema file in original/ directory..."
    
    # Check if original directory exists
    if [[ ! -d "original" ]]; then
        print_error "original/ directory not found"
        print_error "Please create original/ directory and place your schema.sql file there"
        exit 1
    fi
    
    # Find all .sql files in original directory
    local sql_files=($(find original -maxdepth 1 -name "*.sql" -type f))
    local file_count=${#sql_files[@]}
    
    # Validate exactly one SQL file
    if [[ $file_count -eq 0 ]]; then
        print_error "No .sql files found in original/ directory"
        print_error "Please place your PostgreSQL schema dump file in original/"
        print_error "Recommended: original/schema.sql"
        exit 1
    elif [[ $file_count -gt 1 ]]; then
        print_error "Multiple .sql files found in original/ directory:"
        for file in "${sql_files[@]}"; do
            echo "  - $file"
        done
        print_error "Please keep only one schema file in original/"
        print_error "Move or remove extra files to proceed"
        exit 1
    fi
    
    # Set the detected file
    INPUT_FILE="${sql_files[0]}"
    
    # Check file size and provide info
    local file_size=$(stat -f%z "$INPUT_FILE" 2>/dev/null || stat -c%s "$INPUT_FILE" 2>/dev/null || echo "unknown")
    local file_name=$(basename "$INPUT_FILE")
    
    print_success "Detected schema file: $INPUT_FILE"
    print_status "File name: $file_name"
    if [[ "$file_size" != "unknown" ]]; then
        local size_mb=$((file_size / 1024 / 1024))
        print_status "File size: ${size_mb}MB"
    fi
    
    # Recommend standard naming
    if [[ "$file_name" != "schema.sql" ]]; then
        print_warning "Consider renaming to 'schema.sql' for consistency"
    fi
    
    echo ""
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if ! command -v ./.venv/bin/python &> /dev/null; then
        print_error "python3 in .venv is required but not installed"
        exit 1
    fi
    
    # Check if we're in a virtual environment
    if [[ -n "$VIRTUAL_ENV" ]]; then
        print_status "Using virtual environment: $VIRTUAL_ENV"
    fi
    
    # Check required Python packages
    local required_packages=("langchain" "langchain_google_genai" "dotenv" "questionary")
    for package in "${required_packages[@]}"; do
        if ! ./.venv/bin/python -c "import $package" &> /dev/null; then
            print_error "Python package '$package' is required but not installed"
            print_error "Run: pip install -r requirements.txt"
            exit 1
        fi
    done
    
    # Check visualization packages if needed
    if [[ "$SKIP_VISUALIZATIONS" == false || "$SKIP_DIAGRAMS" == false ]]; then
        local viz_packages=("matplotlib" "seaborn" "networkx" "pandas" "numpy")
        for package in "${viz_packages[@]}"; do
            if ! ./.venv/bin/python -c "import $package" &> /dev/null; then
                print_error "Visualization package '$package' is required but not installed"
                print_error "Run: pip install -r requirements.txt"
                exit 1
            fi
        done
    fi
    
    # Check Google API key
    if [[ "$SKIP_ANALYSIS" == false || "$SKIP_VISUALIZATIONS" == false || "$SKIP_FINAL_REPORT" == false ]]; then
        if [[ -z "$GOOGLE_API_KEY" ]]; then
            if [[ ! -f ".env" ]]; then
                print_error "GOOGLE_API_KEY environment variable not set and no .env file found"
                print_error "Set the API key: export GOOGLE_API_KEY='your-api-key'"
                print_error "Or create .env file with: GOOGLE_API_KEY=your-api-key"
                exit 1
            fi
        fi
    fi
    
    # Validate input file exists (if not skipping extract)
    if [[ "$SKIP_EXTRACT" == false ]] && [[ ! -f "$INPUT_FILE" ]]; then
        print_error "Input file '$INPUT_FILE' not found"
        exit 1
    fi
    
    # Check settings file
    if [[ ! -f "$SETTINGS_FILE" ]]; then
        print_warning "Settings file '$SETTINGS_FILE' not found, using script defaults"
    fi
    
    print_success "Prerequisites check passed"
}

# Function to create directories
create_directories() {
    print_status "Creating directory structure..."
    
    mkdir -p schemas
    mkdir -p context
    mkdir -p output
    mkdir -p output/diagrams
    mkdir -p prompts

    
    print_success "Directory structure created"
}

# Function to run a script with error handling
run_script() {
    local script_name="$1"
    local description="$2"
    shift 2
    local args=("$@")
    
    echo ""
    print_status "=========================================="
    print_status "STEP: $description"
    print_status "=========================================="
    print_status "Script: scripts/$script_name"
    print_status "Arguments: ${args[*]}"
    
    if [[ "$VERBOSE" == true ]]; then
        print_status "Full command: ./.venv/bin/python scripts/$script_name ${args[*]}"
    fi
    
    print_status "Starting execution..."
    local start_time=$(date +%s)
    
    if ./.venv/bin/python "scripts/$script_name" "${args[@]}"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_success "$description completed successfully"
        print_status "Execution time: ${duration} seconds"
        
        # Show output file info if it exists
        case "$script_name" in
            "01_extract_schema.py")
                if [[ -f "schemas/schema_only.sql" ]]; then
                    local size=$(du -h schemas/schema_only.sql | cut -f1)
                    local lines=$(wc -l < schemas/schema_only.sql)
                    print_status "Generated: schemas/schema_only.sql ($size, $lines lines)"
                fi
                ;;
            "02_compress_schema.py")
                if [[ -f "schemas/schema_compressed.txt" ]]; then
                    local size=$(du -h schemas/schema_compressed.txt | cut -f1)
                    local lines=$(wc -l < schemas/schema_compressed.txt)
                    print_status "Generated: schemas/schema_compressed.txt ($size, $lines lines)"
                fi
                ;;
            "03_generate_context.py")
                if [[ -f "context/stats.json" ]]; then
                    local size=$(du -h context/stats.json | cut -f1)
                    print_status "Generated: context/stats.json ($size)"
                fi
                if [[ -f "context/context.json" ]]; then
                    local size=$(du -h context/context.json | cut -f1)
                    print_status "Generated: context/context.json ($size)"
                fi
                ;;
            "04_analyze_schema.py")
                # Find the analysis file (handles timestamped filenames)
                local analysis_file=$(ls output/schema_analysis*.md 2>/dev/null | head -1)
                if [[ -n "$analysis_file" ]]; then
                    local size=$(du -h "$analysis_file" | cut -f1)
                    local chars=$(wc -c < "$analysis_file")
                    print_status "Generated: $analysis_file ($size, $chars characters)"
                fi
                ;;
            "05_plan_visualizations.py")
                if [[ -f "output/visualization_plan.json" ]]; then
                    local size=$(du -h output/visualization_plan.json | cut -f1)
                    # Count planned graphs
                    local graph_count=$(grep -o '"graph_type"' output/visualization_plan.json | wc -l || echo "0")
                    print_status "Generated: output/visualization_plan.json ($size, $graph_count graphs planned)"
                fi
                # Check for prompt log
                local prompt_log=$(ls output/visualization_prompt_log_*.txt 2>/dev/null | head -1)
                if [[ -n "$prompt_log" ]]; then
                    print_status "Debug log: $prompt_log"
                fi
                ;;
            "06_generate_diagrams.py")
                local diagram_count=$(find output/diagrams -name "*.png" 2>/dev/null | wc -l)
                if [[ $diagram_count -gt 0 ]]; then
                    local total_size=$(du -sh output/diagrams 2>/dev/null | cut -f1)
                    print_status "Generated: $diagram_count diagrams in output/diagrams/ ($total_size total)"
                fi
                if [[ -f "output/generation_report.json" ]]; then
                    print_status "Generated: output/generation_report.json"
                fi
                ;;
            "07_generate_final_report.py")
                if [[ -f "output/final_report.md" ]]; then
                    local size=$(du -h output/final_report.md | cut -f1)
                    local chars=$(wc -c < output/final_report.md)
                    # Find the original analysis file for comparison
                    local original_analysis=$(ls output/schema_analysis*.md 2>/dev/null | head -1)
                    if [[ -n "$original_analysis" ]]; then
                        local original_size=$(wc -c < "$original_analysis")
                        local enhancement_pct=$(( (chars * 100) / original_size ))
                        print_status "Generated: output/final_report.md ($size, $chars characters, ${enhancement_pct}% of original)"
                    else
                        print_status "Generated: output/final_report.md ($size, $chars characters)"
                    fi
                fi
                ;;
            "08_generate_html.py")
                # Find the generated HTML file
                local html_file=$(ls output/final_report.html output/*_report.html 2>/dev/null | head -1)
                if [[ -n "$html_file" ]]; then
                    local size=$(du -h "$html_file" | cut -f1)
                    print_status "Generated: $html_file ($size)"
                    print_status "Interactive HTML report ready - open in browser!"
                fi
                ;;
            "09_html_to_pdf.py")
                # Find the generated PDF file (handles multiple naming patterns)
                local pdf_file=$(ls output/final_report.pdf output/*_report.pdf 2>/dev/null | head -1)
                if [[ -n "$pdf_file" ]]; then
                    local size=$(du -h "$pdf_file" | cut -f1)
                    print_status "Generated: $pdf_file ($size)"
                    print_status "PDF converted from HTML - perfect for printing!"
                fi
                ;;
        esac
        
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_error "$description failed after ${duration} seconds"
        print_error "Check the error output above for details"
        exit 1
    fi
}

# Function to show pipeline summary
show_pipeline_summary() {
    print_status "Pipeline Summary:"
    echo "  Input file: $INPUT_FILE"
    echo "  Settings file: $SETTINGS_FILE"
    if [[ ${#FRAMEWORKS[@]} -gt 0 ]]; then
        echo "  Compliance Frameworks: ${FRAMEWORKS[*]}"
    else
        echo "  Compliance Frameworks: Interactive selection"
    fi
    echo "  Steps to run:"
    
    [[ "$SKIP_EXTRACT" == false ]] && echo "    ✓ Extract schema structure"
    [[ "$SKIP_COMPRESS" == false ]] && echo "    ✓ Compress to hierarchical format"
    [[ "$SKIP_CONTEXT" == false ]] && echo "    ✓ Generate analysis context"
    [[ "$SKIP_ANALYSIS" == false ]] && echo "    ✓ AI-powered analysis"
    [[ "$SKIP_VISUALIZATIONS" == false ]] && echo "    ✓ Plan visualizations"
    [[ "$SKIP_DIAGRAMS" == false ]] && echo "    ✓ Generate diagrams"
    [[ "$SKIP_FINAL_REPORT" == false ]] && echo "    ✓ Generate final report with integrated diagrams"
    [[ "$SKIP_HTML" == false ]] && echo "    ✓ Generate HTML report (primary format)"
    [[ "$GENERATE_PDF" == true ]] && echo "    ✓ Convert HTML to PDF (optional)"
    
    echo ""
}

# Function to show results summary
show_results_summary() {
    print_success "Pipeline completed successfully!"
    echo ""
    print_status "Generated files:"
    
    [[ -f "schemas/schema_only.sql" ]] && echo "  📄 schemas/schema_only.sql"
    [[ -f "schemas/schema_compressed.txt" ]] && echo "  📄 schemas/schema_compressed.txt"
    [[ -f "context/context.json" ]] && echo "  📄 context/context.json"
    [[ -f "context/stats.json" ]] && echo "  📄 context/stats.json"
    # Show analysis file (handles timestamped filenames)
    local analysis_file=$(ls output/schema_analysis*.md 2>/dev/null | head -1)
    [[ -n "$analysis_file" ]] && echo "  📄 $analysis_file"
    [[ -f "output/visualization_plan.json" ]] && echo "  📄 output/visualization_plan.json"
    [[ -f "output/generation_report.json" ]] && echo "  📄 output/generation_report.json"
    [[ -f "output/final_report.md" ]] && echo "  📄 output/final_report.md"
    
    # Show PDF report if it exists
    local pdf_file=$(ls output/wtfk_report_*.pdf output/final_report.pdf output/*_report.pdf 2>/dev/null | head -1)
    if [[ -n "$pdf_file" ]]; then
        echo "  ���� $pdf_file"
    fi
    
    # Show HTML report if it exists
    local html_file=$(ls output/final_report.html output/*_report.html 2>/dev/null | head -1)
    if [[ -n "$html_file" ]]; then
        echo "  🌐 $html_file"
    fi
    
    # Count diagrams
    local diagram_count=$(find output/diagrams -name "*.png" 2>/dev/null | wc -l)
    if [[ $diagram_count -gt 0 ]]; then
        echo "  📊 output/diagrams/ ($diagram_count diagrams)"
    fi
    
    echo ""
    # Show main deliverable (prioritize HTML, then PDF, then final report, then analysis)
    local html_file=$(ls output/final_report.html output/*_report.html 2>/dev/null | head -1)
    local pdf_file=$(ls output/wtfk_report_*.pdf output/final_report.pdf output/*_report.pdf 2>/dev/null | head -1)
    
    if [[ -n "$html_file" ]]; then
        print_status "🌐 Main deliverable: $html_file (interactive HTML report)"
        if [[ -n "$pdf_file" ]]; then
            print_status "📚 Also available: $pdf_file (PDF for printing)"
        fi
        if [[ -f "output/final_report.md" ]]; then
            print_status "📄 Source: output/final_report.md (markdown)"
        fi
    elif [[ -n "$pdf_file" ]]; then
        print_status "📚 Main deliverable: $pdf_file (professional PDF report)"
        if [[ -f "output/final_report.md" ]]; then
            print_status "📄 Also available: output/final_report.md (markdown source)"
        fi
    elif [[ -f "output/final_report.md" ]]; then
        print_status "📄 Main deliverable: output/final_report.md (comprehensive report with diagrams)"
    else
        local analysis_file=$(ls output/schema_analysis*.md 2>/dev/null | head -1)
        if [[ -n "$analysis_file" ]]; then
            print_status "📄 Main deliverable: $analysis_file"
        else
            print_status "Main deliverable: Not generated"
        fi
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -s|--settings)
            SETTINGS_FILE="$2"
            shift 2
            ;;
        --frameworks)
            shift
            while [[ $# -gt 0 && ! $1 =~ ^-- ]]; do
                FRAMEWORKS+=("$1")
                shift
            done
            ;;
        --list-frameworks)
            list_frameworks
            ;;
        --skip-extract)
            SKIP_EXTRACT=true
            shift
            ;;
        --skip-compress)
            SKIP_COMPRESS=true
            shift
            ;;
        --skip-context)
            SKIP_CONTEXT=true
            shift
            ;;
        --skip-analysis)
            SKIP_ANALYSIS=true
            shift
            ;;
        --skip-visualizations)
            SKIP_VISUALIZATIONS=true
            shift
            ;;
        --skip-diagrams)
            SKIP_DIAGRAMS=true
            shift
            ;;
        --skip-final-report)
            SKIP_FINAL_REPORT=true
            shift
            ;;
        --skip-html)
            SKIP_HTML=true
            shift
            ;;
        --pdf)
            GENERATE_PDF=true
            shift
            ;;
        --skip-pdf)
            SKIP_PDF=true
            shift
            ;;
        --analysis-only)
            SKIP_EXTRACT=true
            SKIP_COMPRESS=true
            SKIP_CONTEXT=true
            SKIP_VISUALIZATIONS=true
            SKIP_DIAGRAMS=true
            SKIP_FINAL_REPORT=true
            shift
            ;;
        --visuals-only)
            SKIP_EXTRACT=true
            SKIP_COMPRESS=true
            SKIP_CONTEXT=true
            SKIP_ANALYSIS=true
            SKIP_FINAL_REPORT=true
            shift
            ;;
        --no-visuals)
            SKIP_VISUALIZATIONS=true
            SKIP_DIAGRAMS=true
            shift
            ;;
        --modern-web)
            SKIP_PDF=true
            SKIP_HTML=false
            shift
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$INPUT_FILE" ]]; then
                INPUT_FILE="$1"
            else
                print_error "Multiple input files specified"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Auto-detect schema file if not provided
if [[ -z "$INPUT_FILE" ]]; then
    detect_schema_file
fi

# Main execution
main() {
    print_status "WTFK (What The Foreign Key) - Schema Analysis Pipeline"
    print_status "========================================================"
    echo ""
    
    # Show pipeline summary
    show_pipeline_summary
    
    # Check prerequisites
    check_prerequisites
    
    # Create directories
    create_directories
    
    # Pipeline execution
    echo ""
    print_status "Starting pipeline execution..."
    echo ""
    
    # Step 1: Extract schema structure
    if [[ "$SKIP_EXTRACT" == false ]]; then
        run_script "01_extract_schema.py" "Schema extraction" "$INPUT_FILE"
    else
        print_status "Skipping schema extraction (using existing schema_only.sql)"
    fi
    
    # Step 2: Compress to hierarchical format
    if [[ "$SKIP_COMPRESS" == false ]]; then
        run_script "02_compress_schema.py" "Schema compression" "schemas/schema_only.sql"
    else
        print_status "Skipping schema compression (using existing schema_compressed.txt)"
    fi
    
    # Step 3: Generate analysis context
    if [[ "$SKIP_CONTEXT" == false ]]; then
        run_script "03_generate_context.py" "Context generation" "schemas/schema_compressed.txt" "-s" "$SETTINGS_FILE"
    else
        print_status "Skipping context generation (using existing context files)"
    fi
    
    # Step 4: AI-powered analysis
    if [[ "$SKIP_ANALYSIS" == false ]]; then
        # This step is now handled directly to allow for interactive input
        echo ""
        print_status "=========================================="
        print_status "STEP: AI analysis"
        print_status "=========================================="
        
        local analysis_args=("scripts/04_analyze_schema.py" "schemas/schema_compressed.txt" "-s" "$SETTINGS_FILE")
        if [[ ${#FRAMEWORKS[@]} -gt 0 ]]; then
            analysis_args+=("--frameworks" "${FRAMEWORKS[@]}")
        fi

        print_status "Starting execution..."
        local start_time=$(date +%s)

        # Execute python script directly to allow for interaction
        if ./.venv/bin/python "${analysis_args[@]}"; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            print_success "AI analysis completed successfully"
            print_status "Execution time: ${duration} seconds"
        else
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            print_error "AI analysis failed after ${duration} seconds"
            exit 1
        fi
    else
        print_status "Skipping AI analysis (using existing schema_analysis.md)"
    fi
    
    # Step 5: Plan visualizations
    if [[ "$SKIP_VISUALIZATIONS" == false ]]; then
        run_script "05_plan_visualizations.py" "Visualization planning" "schemas/schema_compressed.txt" "-s" "$SETTINGS_FILE" "-o" "output/visualization_plan.json"
    else
        print_status "Skipping visualization planning"
    fi
    
    # Step 6: Generate diagrams
    if [[ "$SKIP_DIAGRAMS" == false ]]; then
        if [[ -f "output/visualization_plan.json" ]]; then
            run_script "06_generate_diagrams.py" "Diagram generation" "--plan" "output/visualization_plan.json" "--schema" "schemas/schema_compressed.txt" "-s" "$SETTINGS_FILE"
        else
            print_warning "Skipping diagram generation (no visualization plan found)"
        fi
    else
        print_status "Skipping diagram generation"
    fi
    
    # Step 7: Generate final report with integrated diagrams
    if [[ "$SKIP_FINAL_REPORT" == false ]]; then
        # Check for any schema analysis file (handles timestamped filenames)
        if ls output/schema_analysis*.md 1> /dev/null 2>&1; then
            run_script "07_generate_final_report.py" "Final report generation" "--settings" "$SETTINGS_FILE"
        else
            print_warning "Skipping final report generation (no analysis report found)"
        fi
    else
        print_status "Skipping final report generation"
    fi
    
    # Step 8: Generate HTML report (primary format)
    if [[ "$SKIP_HTML" == false ]]; then
        # Check for final report first, then fallback to analysis report
        if [[ -f "output/final_report.md" ]]; then
            run_script "08_generate_html.py" "HTML generation" "output/final_report.md" "--settings" "$SETTINGS_FILE"
        elif ls output/schema_analysis*.md 1> /dev/null 2>&1; then
            local analysis_file=$(ls output/schema_analysis*.md 2>/dev/null | head -1)
            run_script "08_generate_html.py" "HTML generation" "$analysis_file" "--settings" "$SETTINGS_FILE"
        else
            print_warning "Skipping HTML generation (no markdown report found)"
        fi
    else
        print_status "Skipping HTML generation"
    fi
    
    # Step 9: Convert HTML to PDF (optional)
    if [[ "$GENERATE_PDF" == true && "$SKIP_PDF" == false ]]; then
        # Find the generated HTML file
        local html_file=$(ls output/final_report.html output/*_report.html 2>/dev/null | head -1)
        if [[ -n "$html_file" ]]; then
            run_script "09_html_to_pdf.py" "HTML to PDF conversion" "$html_file" "--settings" "$SETTINGS_FILE"
        else
            print_warning "Skipping PDF conversion (no HTML report found)"
        fi
    else
        print_status "Skipping PDF generation (use --pdf to enable)"
    fi
    
    echo ""
    show_results_summary
}

# Run main function
main 