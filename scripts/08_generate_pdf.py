#!/usr/bin/env python3
"""
WTFK (What The Foreign Key) - Step 8: PDF Generation
Convert markdown reports to professional PDF format using pandoc.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import shutil
import os


class PDFGenerator:
    def __init__(self, settings_file="settings.json"):
        """Initialize PDF generator with settings."""
        self.settings = self.load_settings(settings_file)
        self.pdf_config = self.settings.get('pdf_generation', {})
        
        # Validate pandoc availability
        if not self._check_pandoc():
            raise RuntimeError("Pandoc is required for PDF generation. Please install pandoc.")
    
    def load_settings(self, settings_file):
        """Load configuration from JSON file."""
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Settings file '{settings_file}' not found. Using defaults.")
            return self._default_settings()
        except json.JSONDecodeError as e:
            print(f"Error parsing settings file: {e}")
            return self._default_settings()
    
    def _default_settings(self):
        """Return default settings if file not found."""
        return {
            "pdf_generation": {
                "enable_generation": True,
                "engine": "pandoc",
                "style": "business",
                "include_toc": True,
                "toc_depth": 3,
                "number_sections": True,
                "highlight_style": "pygments",
                "page_break_before": ["# Executive Summary", "# Domain Analysis", "# Performance Analysis", "# Security Analysis"],
                "styles": {
                    "business": {
                        "description": "Professional business report style",
                        "geometry": "margin=0.75in",
                        "fontsize": "12pt",
                        "documentclass": "report",
                        "classoption": "oneside",
                        "mainfont": "Arial",
                        "colorlinks": True,
                        "linkcolor": "blue",
                        "urlcolor": "blue"
                    }
                }
            }
        }
    
    def _check_pandoc(self):
        """Check if pandoc is available."""
        try:
            subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _preprocess_markdown(self, markdown_content, output_dir):
        """Preprocess markdown for better PDF conversion."""
        # Convert relative image paths to absolute paths
        lines = markdown_content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Handle image references
            if line.strip().startswith('![') and '](' in line:
                # Extract image path
                start = line.find('](') + 2
                end = line.find(')', start)
                if start > 1 and end > start:
                    image_path = line[start:end]
                    # Convert relative path to absolute
                    if not image_path.startswith('/') and not image_path.startswith('http'):
                        # Handle different path formats
                        if image_path.startswith('output/diagrams/'):
                            # Already has full path from project root
                            abs_path = os.path.abspath(image_path)
                        elif image_path.startswith('diagrams/'):
                            # Missing 'output/' prefix, add it
                            abs_path = os.path.abspath(os.path.join('output', image_path))
                        elif image_path.startswith('output/'):
                            # Has output prefix but maybe missing diagrams
                            abs_path = os.path.abspath(image_path)
                        else:
                            # Default handling for other relative paths
                            abs_path = os.path.abspath(os.path.join(output_dir, '..', image_path))
                        
                        # Verify file exists and warn if not
                        if not os.path.exists(abs_path):
                            print(f"⚠️  Warning: Image not found: {abs_path}")
                            print(f"   Original path: {image_path}")
                        
                        line = line[:start] + abs_path + line[end:]
            
            # Add page breaks before specified sections
            if line.strip() in self.pdf_config.get('page_break_before', []):
                processed_lines.append('\\newpage')
                processed_lines.append('')
            
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _create_metadata_block(self, title, author=None):
        """Create YAML metadata block for pandoc."""
        # Get the selected style configuration
        style_name = self.pdf_config.get('style', 'business')
        style_config = self.pdf_config.get('styles', {}).get(style_name, {})
        
        # Get author from settings if not provided
        if author is None:
            author = self.settings.get('project', {}).get('generated_by', 'Database Schema Analysis')
        
        metadata = {
            'title': title,
            'author': author,
            'date': datetime.now().strftime('%B %d, %Y'),
            'geometry': style_config.get('geometry', 'margin=1in'),
            'fontsize': style_config.get('fontsize', '11pt'),
            'documentclass': style_config.get('documentclass', 'article'),
            'classoption': style_config.get('classoption', 'onecolumn'),
            'toc': self.pdf_config.get('include_toc', True),
            'toc-depth': self.pdf_config.get('toc_depth', 3),
            'numbersections': self.pdf_config.get('number_sections', True),
            'highlight-style': self.pdf_config.get('highlight_style', 'pygments'),
            'colorlinks': style_config.get('colorlinks', True),
            'linkcolor': style_config.get('linkcolor', 'blue'),
            'urlcolor': style_config.get('urlcolor', 'blue'),
            'citecolor': style_config.get('toccolor', 'blue')
        }
        
        # Add font configuration if specified
        if 'mainfont' in style_config:
            metadata['mainfont'] = style_config['mainfont']
        if 'sansfont' in style_config:
            metadata['sansfont'] = style_config['sansfont']
        if 'monofont' in style_config:
            metadata['monofont'] = style_config['monofont']
        
        # Add header includes for custom LaTeX
        if 'header_includes' in style_config:
            metadata['header-includes'] = style_config['header_includes']
        
        # Create YAML front matter
        yaml_lines = ['---']
        for key, value in metadata.items():
            if isinstance(value, bool):
                yaml_lines.append(f'{key}: {str(value).lower()}')
            else:
                yaml_lines.append(f'{key}: {value}')
        yaml_lines.append('---')
        yaml_lines.append('')
        
        return '\n'.join(yaml_lines)
    
    def generate_pdf(self, markdown_file, output_file=None, title=None):
        """Generate PDF from markdown file."""
        if not self.pdf_config.get('enable_generation', True):
            print("PDF generation is disabled in settings.")
            return None
        
        # Validate input file
        markdown_path = Path(markdown_file)
        if not markdown_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_file}")
        
        # Determine output file
        if output_file is None:
            output_file = markdown_path.with_suffix('.pdf')
        else:
            output_file = Path(output_file)
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Read markdown content
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Determine title
        if title is None:
            title = markdown_path.stem.replace('_', ' ').title()
        
        # Preprocess markdown
        output_dir = str(output_file.parent)
        processed_content = self._preprocess_markdown(markdown_content, output_dir)
        
        # Add metadata block
        metadata_block = self._create_metadata_block(title)
        final_content = metadata_block + processed_content
        
        # Create temporary file with processed content
        temp_file = output_file.with_suffix('.tmp.md')
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        try:
            # Get the selected style configuration
            style_name = self.pdf_config.get('style', 'business')
            style_config = self.pdf_config.get('styles', {}).get(style_name, {})
            
            # Build pandoc command
            cmd = [
                'pandoc',
                str(temp_file),
                '-o', str(output_file),
                '--pdf-engine=xelatex',
                '--standalone',
                '--embed-resources'
            ]
            
            # Add table of contents if enabled
            if self.pdf_config.get('include_toc', True):
                cmd.extend(['--table-of-contents', '--toc-depth', str(self.pdf_config.get('toc_depth', 3))])
            
            # Add section numbering if enabled
            if self.pdf_config.get('number_sections', True):
                cmd.append('--number-sections')
            
            # Add syntax highlighting
            if self.pdf_config.get('highlight_style'):
                cmd.extend(['--highlight-style', self.pdf_config.get('highlight_style')])
            
            # Execute pandoc
            print(f"🔄 Converting {markdown_path.name} to PDF...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ PDF generation failed:")
                print(f"stdout: {result.stdout}")
                print(f"stderr: {result.stderr}")
                return None
            
            print(f"✅ PDF generated successfully: {output_file}")
            print(f"📄 File size: {output_file.stat().st_size / 1024:.1f} KB")
            
            return output_file
            
        finally:
            # Clean up temporary file
            if temp_file.exists():
                temp_file.unlink()
    
    def generate_pdf_from_report(self, report_file, output_dir=None):
        """Generate PDF from a WTFK analysis report with smart naming."""
        report_path = Path(report_file)
        
        if output_dir is None:
            output_dir = report_path.parent
        else:
            output_dir = Path(output_dir)
        
        # Extract info from filename for better title
        filename = report_path.stem
        project_name = self.settings.get('project', {}).get('name', 'Database Schema Analysis')
        
        if 'final_report' in filename.lower():
            title = f"{project_name} Report"
        elif 'schema_analysis' in filename.lower():
            title = project_name
        else:
            title = filename.replace('_', ' ').title()
        
        # Generate timestamp-based filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"wtfk_report_{timestamp}.pdf"
        output_file = output_dir / pdf_filename
        
        return self.generate_pdf(report_file, output_file, title)


def main():
    parser = argparse.ArgumentParser(
        description="Generate PDF from WTFK markdown reports"
    )
    parser.add_argument(
        "markdown_file",
        nargs="?",  # Make optional
        help="Path to markdown file to convert"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output PDF file path (default: same name as markdown with .pdf extension)"
    )
    parser.add_argument(
        "-t", "--title",
        help="PDF title (default: derived from filename)"
    )
    parser.add_argument(
        "-s", "--settings",
        help="Path to settings.json file",
        default="settings.json"
    )
    parser.add_argument(
        "--style",
        help="PDF style to use (business, executive, technical, modern, minimal)",
        choices=["business", "executive", "technical", "modern", "minimal"],
        default=None
    )
    parser.add_argument(
        "--list-styles",
        help="List available PDF styles",
        action="store_true"
    )
    parser.add_argument(
        "--check-pandoc",
        help="Check if pandoc is available",
        action="store_true"
    )
    
    args = parser.parse_args()
    
    # Check pandoc availability
    if args.check_pandoc:
        try:
            subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
            print("✅ Pandoc is available and ready for PDF generation.")
            sys.exit(0)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Pandoc is not available. Please install pandoc to generate PDFs.")
            print("Visit: https://pandoc.org/installing.html")
            sys.exit(1)
    
    # List available styles
    if args.list_styles:
        try:
            generator = PDFGenerator(settings_file=args.settings)
            styles = generator.pdf_config.get('styles', {})
            print("📋 Available PDF Styles:")
            print("=" * 50)
            for style_name, style_config in styles.items():
                print(f"🎨 {style_name.upper()}")
                print(f"   Description: {style_config.get('description', 'No description')}")
                print(f"   Font: {style_config.get('mainfont', 'Default')} ({style_config.get('fontsize', '11pt')})")
                print(f"   Layout: {style_config.get('documentclass', 'article')} with {style_config.get('geometry', 'default margins')}")
                print()
            sys.exit(0)
        except Exception as e:
            print(f"❌ Error listing styles: {e}")
            sys.exit(1)
    
    # Validate markdown file is provided if not checking pandoc
    if not args.markdown_file:
        print("❌ Error: markdown_file argument is required when not using --check-pandoc")
        parser.print_help()
        sys.exit(1)
    
    try:
        # Initialize PDF generator
        generator = PDFGenerator(settings_file=args.settings)
        
        # Override style if specified
        if args.style:
            generator.pdf_config['style'] = args.style
            print(f"🎨 Using style: {args.style}")
        
        # Generate PDF
        output_file = generator.generate_pdf(
            markdown_file=args.markdown_file,
            output_file=args.output,
            title=args.title
        )
        
        if output_file:
            print(f"\n📚 PDF Report Ready: {output_file}")
            print("Share this professional report with stakeholders!")
        else:
            print("❌ PDF generation failed. Check error messages above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 