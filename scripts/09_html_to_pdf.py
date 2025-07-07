#!/usr/bin/env python3
"""
WTFK (What The Foreign Key) - Step 9: HTML to PDF Conversion
Convert HTML reports to PDF for printing and sharing.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


class HTMLToPDFConverter:
    def __init__(self, settings_file="settings.json"):
        """Initialize HTML to PDF converter with settings."""
        self.settings = self.load_settings(settings_file)
        self.pdf_config = self.settings.get('pdf_generation', {})
        
    def load_settings(self, settings_file):
        """Load configuration from JSON file."""
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._default_settings()
    
    def _default_settings(self):
        """Return default settings if file not found."""
        return {
            "pdf_generation": {
                "enable_generation": True,
                "method": "weasyprint",  # or "playwright", "wkhtmltopdf"
                "style": "business"
            }
        }
    
    def _check_dependencies(self):
        """Check if required dependencies are available."""
        method = self.pdf_config.get('method', 'weasyprint')
        
        if method == 'weasyprint':
            try:
                import weasyprint
                return True, "weasyprint"
            except ImportError:
                pass
        
        if method == 'playwright':
            try:
                from playwright.sync_api import sync_playwright
                return True, "playwright"
            except ImportError:
                pass
        
        if method == 'wkhtmltopdf':
            try:
                subprocess.run(['wkhtmltopdf', '--version'], capture_output=True, check=True)
                return True, "wkhtmltopdf"
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        return False, None
    
    def _convert_with_weasyprint(self, html_file, pdf_file):
        """Convert HTML to PDF using WeasyPrint."""
        try:
            import weasyprint
            
            # Read HTML content
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Convert to PDF
            html_doc = weasyprint.HTML(string=html_content, base_url=str(html_file.parent))
            html_doc.write_pdf(pdf_file)
            
            return True
        except Exception as e:
            print(f"Error with WeasyPrint: {e}")
            return False
    
    def _convert_with_playwright(self, html_file, pdf_file):
        """Convert HTML to PDF using Playwright."""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                
                # Load HTML file
                page.goto(f'file://{html_file.absolute()}')
                
                # Generate PDF
                page.pdf(
                    path=pdf_file,
                    format='A4',
                    margin={
                        'top': '1in',
                        'right': '0.75in',
                        'bottom': '1in',
                        'left': '0.75in'
                    },
                    print_background=True
                )
                
                browser.close()
            
            return True
        except Exception as e:
            print(f"Error with Playwright: {e}")
            return False
    
    def _convert_with_wkhtmltopdf(self, html_file, pdf_file):
        """Convert HTML to PDF using wkhtmltopdf."""
        try:
            cmd = [
                'wkhtmltopdf',
                '--page-size', 'A4',
                '--margin-top', '1in',
                '--margin-right', '0.75in',
                '--margin-bottom', '1in',
                '--margin-left', '0.75in',
                '--print-media-type',
                '--enable-local-file-access',
                str(html_file),
                str(pdf_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True
            else:
                print(f"wkhtmltopdf error: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error with wkhtmltopdf: {e}")
            return False
    
    def convert_to_pdf(self, html_file, output_file=None):
        """Convert HTML file to PDF."""
        if not self.pdf_config.get('enable_generation', True):
            print("PDF generation is disabled in settings.")
            return None
        
        # Validate input file
        html_path = Path(html_file)
        if not html_path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_file}")
        
        # Determine output file
        if output_file is None:
            output_file = html_path.with_suffix('.pdf')
        else:
            output_file = Path(output_file)
        
        # Check dependencies
        available, method = self._check_dependencies()
        if not available:
            print("❌ No PDF conversion method available.")
            print("Install one of the following:")
            print("  pip install weasyprint")
            print("  pip install playwright && playwright install chromium")
            print("  brew install wkhtmltopdf  # or apt-get install wkhtmltopdf")
            return None
        
        print(f"🔄 Converting {html_path.name} to PDF using {method}...")
        
        # Convert based on available method
        success = False
        if method == 'weasyprint':
            success = self._convert_with_weasyprint(html_path, output_file)
        elif method == 'playwright':
            success = self._convert_with_playwright(html_path, output_file)
        elif method == 'wkhtmltopdf':
            success = self._convert_with_wkhtmltopdf(html_path, output_file)
        
        if success:
            print(f"✅ PDF generated successfully: {output_file}")
            print(f"📄 File size: {output_file.stat().st_size / 1024:.1f} KB")
            return output_file
        else:
            print(f"❌ PDF conversion failed")
            return None


def main():
    parser = argparse.ArgumentParser(
        description="Convert HTML reports to PDF for printing and sharing"
    )
    parser.add_argument(
        "html_file",
        help="Path to HTML file to convert",
        nargs="?"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output PDF file path (default: same name as HTML with .pdf extension)"
    )
    parser.add_argument(
        "-s", "--settings",
        help="Path to settings.json file",
        default="settings.json"
    )
    parser.add_argument(
        "--check-deps",
        help="Check available PDF conversion methods",
        action="store_true"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    if args.check_deps:
        converter = HTMLToPDFConverter(settings_file=args.settings)
        available, method = converter._check_dependencies()
        
        print("📋 PDF Conversion Methods:")
        print("=" * 40)
        
        methods = [
            ('weasyprint', 'WeasyPrint (Pure Python, good for simple layouts)'),
            ('playwright', 'Playwright (Chrome-based, best quality)'),
            ('wkhtmltopdf', 'wkhtmltopdf (External binary, reliable)')
        ]
        
        for method_name, description in methods:
            converter.pdf_config['method'] = method_name
            avail, _ = converter._check_dependencies()
            status = "✅ Available" if avail else "❌ Not installed"
            print(f"{method_name}: {status}")
            print(f"   {description}")
            print()
        
        if available:
            print(f"🎯 Currently using: {method}")
        else:
            print("⚠️  No PDF conversion methods available")
            print("Install at least one method to enable PDF generation")
        
        sys.exit(0)
    
    try:
        # Check if html_file is provided when not using --check-deps
        if not args.html_file:
            print("❌ Error: html_file is required when not using --check-deps")
            parser.print_help()
            sys.exit(1)
        
        # Initialize converter
        converter = HTMLToPDFConverter(settings_file=args.settings)
        
        # Convert to PDF
        output_file = converter.convert_to_pdf(
            html_file=args.html_file,
            output_file=args.output
        )
        
        if output_file:
            print(f"\n📚 PDF Report Ready: {output_file}")
            print("Perfect for printing and sharing!")
        else:
            print("❌ PDF conversion failed. Check error messages above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 