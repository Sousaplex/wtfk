#!/usr/bin/env python3
"""
WTFK (What The Foreign Key) - Final Report Generator
Integrates diagrams with explanations into the comprehensive analysis report.
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
import argparse
from typing import Dict, List, Optional, Tuple

# Add the project root to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_settings(custom_path: Optional[str] = None) -> Dict:
    """Load settings from JSON file."""
    settings_path = custom_path or "settings.json"
    try:
        with open(settings_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Settings file '{settings_path}' not found. Using defaults.")
        return {
            "model": {
                "name": "gemini-2.5-pro",
                "temperature": 0.3,
                "max_output_tokens": 4000,
                "top_p": 0.95,
                "top_k": 40
            },
            "paths": {
                "output": "output",
                "diagrams": "output/diagrams",
                "context": "context"
            }
        }

def setup_gemini(api_key: str, model_params: Dict):
    """Initialize Gemini model with parameters."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        return ChatGoogleGenerativeAI(
            model=model_params.get("name", "gemini-2.5-pro"),
            google_api_key=api_key,
            temperature=model_params.get("temperature", 0.3),
            max_output_tokens=model_params.get("max_output_tokens", 4000),
            top_p=model_params.get("top_p", 0.95),
            top_k=model_params.get("top_k", 40)
        )
    except Exception as e:
        print(f"Error setting up Gemini: {e}")
        sys.exit(1)

def parse_markdown_sections(content: str) -> List[Dict]:
    """Parse markdown content to identify sections and their content."""
    sections = []
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        # Check if this is a header
        header_match = re.match(r'^(#{1,6})\s+(.+)', line)
        if header_match:
            # Save previous section if exists
            if current_section:
                sections.append({
                    'level': current_section['level'],
                    'title': current_section['title'],
                    'content': '\n'.join(current_content),
                    'line_number': current_section['line_number']
                })
            
            # Start new section
            current_section = {
                'level': len(header_match.group(1)),
                'title': header_match.group(2),
                'line_number': len(sections)
            }
            current_content = [line]
        else:
            if current_content:
                current_content.append(line)
    
    # Add the last section
    if current_section:
        sections.append({
            'level': current_section['level'],
            'title': current_section['title'],
            'content': '\n'.join(current_content),
            'line_number': current_section['line_number']
        })
    
    return sections

def match_diagrams_to_sections(sections: List[Dict], viz_plan: Dict, generation_report: Dict) -> Dict:
    """Match diagrams from visualization plan to analysis sections."""
    successful_diagrams = {}
    
    # Extract successful diagrams from generation report
    if generation_report.get('sections'):
        for section_name, diagrams in generation_report['sections'].items():
            for diagram in diagrams:
                file_path = diagram.get('file_path', '')
                filename = os.path.basename(file_path) if file_path else ''
                if filename:
                    successful_diagrams[filename] = {
                        'section': section_name,
                        'title': diagram.get('title', ''),
                        'graph_type': diagram.get('graph_type', ''),
                        'file_path': file_path
                    }
    
    section_diagrams = {}
    
    # Match successful diagrams to analysis sections
    for filename, diagram_info in successful_diagrams.items():
        target_section = diagram_info['section']
        
        # Find matching section by title similarity
        best_match = None
        best_score = 0
        
        for section in sections:
            section_title = section['title'].lower()
            target_lower = target_section.lower().replace('_', ' ')
            
            # Direct substring match or keyword overlap
            if target_lower in section_title or section_title in target_lower:
                score = min(len(target_lower), len(section_title))
                if score > best_score:
                    best_score = score
                    best_match = section
            
            # Check for keyword overlap (e.g., "executive" matches "Executive Summary")
            target_words = target_lower.split()
            section_words = section_title.split()
            overlap = len(set(target_words) & set(section_words))
            if overlap > 0 and overlap > best_score:
                best_score = overlap
                best_match = section
        
        if best_match:
            section_key = f"{best_match['level']}_{best_match['title']}"
            if section_key not in section_diagrams:
                section_diagrams[section_key] = []
            section_diagrams[section_key].append({
                'filename': filename,
                'title': diagram_info['title'],
                'graph_type': diagram_info['graph_type'],
                'target_section': target_section,
                'file_path': diagram_info['file_path']
            })
    
    return section_diagrams

def generate_diagram_explanation(llm, diagram: Dict, context: Dict) -> str:
    """Generate contextual explanation for a diagram using LLM."""
    prompt = f"""
As a database architect, provide a concise but insightful explanation for this visualization:

**Diagram Details:**
- Type: {diagram.get('graph_type', 'Unknown')}
- Title: {diagram.get('title', 'Untitled')}
- Description: {diagram.get('description', 'No description')}
- Section: {diagram.get('target_section', 'Unknown')}

**Schema Context:**
- Total Tables: {context.get('total_tables', 'Unknown')}
- Total Columns: {context.get('total_columns', 'Unknown')}
- Foreign Key Relationships: {context.get('total_foreign_keys', 'Unknown')}

**Instructions:**
1. Write 2-3 paragraphs explaining what this diagram reveals about the database schema
2. Focus on actionable insights and architectural implications
3. Highlight any patterns, risks, or opportunities the visualization exposes
4. Use professional, technical language appropriate for database architects
5. Do NOT repeat the diagram title or basic description
6. Start directly with insights, not "This diagram shows..."

**Key Insights:**
"""
    
    try:
        response = llm.invoke(prompt)
        # Handle LangChain AIMessage response
        if hasattr(response, 'content'):
            return response.content.strip()
        else:
            return str(response).strip()
    except Exception as e:
        print(f"Warning: Failed to generate explanation for {diagram.get('title', 'diagram')}: {e}")
        return f"This {diagram.get('graph_type', 'visualization')} provides insights into the {diagram.get('target_section', 'database schema')} structure and relationships."

def insert_diagrams_into_section(section_content: str, diagrams: List[Dict], explanations: Dict) -> str:
    """Insert diagrams and explanations into a section's content."""
    if not diagrams:
        return section_content
    
    # Insert diagrams at the end of the section, before any subsections
    lines = section_content.split('\n')
    insertion_point = len(lines)
    
    # Find the last content line before any subsections
    for i, line in enumerate(lines):
        if re.match(r'^#{2,6}\s+', line) and i > 0:  # Found a subsection
            insertion_point = i
            break
    
    # Build diagram insertions
    diagram_content = []
    for diagram in diagrams:
        filename = diagram.get('filename', '')
        title = diagram.get('title', 'Visualization')
        explanation = explanations.get(filename, '')
        
        diagram_content.extend([
            '',
            f'### {title}',
            '',
            f'![{title}](diagrams/{filename})',
            '',
            explanation,
            ''
        ])
    
    # Insert diagrams into the content
    result_lines = lines[:insertion_point] + diagram_content + lines[insertion_point:]
    return '\n'.join(result_lines)

def generate_final_report(settings: Dict, api_key: str, skip_explanations: bool = False):
    """Generate the final comprehensive report with integrated diagrams."""
    print("🔄 Starting final report generation...")
    
    # Load required files
    try:
        # Find the analysis file (handles timestamped filenames)
        import glob
        analysis_files = glob.glob('output/schema_analysis*.md')
        if not analysis_files:
            print("❌ Error: No schema analysis file found. Run analysis first.")
            return False
        
        # Use the most recent file if multiple exist
        analysis_file = max(analysis_files, key=os.path.getmtime)
        with open(analysis_file, 'r') as f:
            analysis_content = f.read()
        print(f"✓ Loaded analysis report: {analysis_file}")
    except Exception as e:
        print(f"❌ Error loading analysis report: {e}")
        return False
    
    try:
        with open('output/visualization_plan.json', 'r') as f:
            viz_plan = json.load(f)
        print("✓ Loaded visualization plan")
    except FileNotFoundError:
        print("❌ Error: visualization_plan.json not found. Run visualization planning first.")
        return False
    
    try:
        with open('output/generation_report.json', 'r') as f:
            generation_report = json.load(f)
        print("✓ Loaded generation report")
    except FileNotFoundError:
        print("❌ Error: generation_report.json not found. Run diagram generation first.")
        return False
    
    try:
        # Find the context file (handles timestamped filenames)
        import glob
        context_files = glob.glob('context/*_context.json')
        if not context_files:
            print("❌ Error: No context file found. Run context generation first.")
            return False
        
        # Use the most recent file if multiple exist
        context_file = max(context_files, key=os.path.getmtime)
        with open(context_file, 'r') as f:
            context = json.load(f)
        print(f"✓ Loaded context data: {context_file}")
    except Exception as e:
        print(f"❌ Error loading context data: {e}")
        return False
    
    # Setup LLM (only if not skipping explanations)
    if not skip_explanations:
        llm = setup_gemini(api_key, settings.get('model', {}))
        print("✓ Initialized Gemini model")
    else:
        llm = None
        print("✓ Skipping LLM initialization (explanations disabled)")
    
    # Parse markdown sections
    sections = parse_markdown_sections(analysis_content)
    print(f"✓ Parsed {len(sections)} sections from analysis")
    
    # Match diagrams to sections
    section_diagrams = match_diagrams_to_sections(sections, viz_plan, generation_report)
    total_diagrams = sum(len(diagrams) for diagrams in section_diagrams.values())
    print(f"✓ Matched {total_diagrams} diagrams to sections")
    
    # Generate explanations for all diagrams
    print("🔄 Generating diagram explanations...")
    explanations = {}
    
    if not skip_explanations and total_diagrams > 0:
        # Collect all diagrams for parallel processing
        all_diagrams = []
        for diagrams in section_diagrams.values():
            for diagram in diagrams:
                all_diagrams.append(diagram)
        
        # Generate explanations in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        def generate_single_explanation(diagram_info, diagram_index):
            """Generate explanation for a single diagram."""
            filename = diagram_info.get('filename', '')
            try:
                print(f"  📊 Generating explanation for {filename} ({diagram_index}/{len(all_diagrams)})")
                explanation = generate_diagram_explanation(llm, diagram_info, context)
                return filename, explanation
            except Exception as e:
                print(f"  ❌ Failed to generate explanation for {filename}: {e}")
                return filename, f"This {diagram_info.get('graph_type', 'visualization')} provides insights into the {diagram_info.get('target_section', 'database schema')} structure and relationships."
        
        # Use ThreadPoolExecutor for parallel processing
        max_workers = min(4, len(all_diagrams))  # Limit to 4 concurrent requests
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_diagram = {
                executor.submit(generate_single_explanation, diagram, i+1): diagram 
                for i, diagram in enumerate(all_diagrams)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_diagram):
                filename, explanation = future.result()
                explanations[filename] = explanation
    else:
        # Use placeholder explanations
        diagram_count = 0
        for diagrams in section_diagrams.values():
            for diagram in diagrams:
                diagram_count += 1
                filename = diagram.get('filename', '')
                print(f"  📊 Using placeholder explanation for {filename} ({diagram_count}/{total_diagrams})")
                explanations[filename] = f"This {diagram.get('graph_type', 'visualization')} provides insights into the {diagram.get('target_section', 'database schema')} structure and relationships."
    
    # Build the final report
    print("🔄 Building final report...")
    final_content = []
    
    for section in sections:
        section_key = f"{section['level']}_{section['title']}"
        diagrams = section_diagrams.get(section_key, [])
        
        if diagrams:
            print(f"  📋 Adding {len(diagrams)} diagrams to: {section['title']}")
            enhanced_content = insert_diagrams_into_section(section['content'], diagrams, explanations)
            final_content.append(enhanced_content)
        else:
            final_content.append(section['content'])
    
    # Add metadata header
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_by = settings.get('project', {}).get('generated_by', 'WTFK (What The Foreign Key)')
    header = f"""<!-- Generated by {generated_by} Pipeline -->
<!-- Timestamp: {timestamp} -->
<!-- Diagrams: {total_diagrams} visualizations integrated -->

"""
    
    final_report = header + '\n'.join(final_content)
    
    # Save the final report
    output_path = 'output/final_report.md'
    with open(output_path, 'w') as f:
        f.write(final_report)
    
    # Generate summary
    original_size = len(analysis_content)
    final_size = len(final_report)
    enhancement_ratio = (final_size / original_size) * 100
    
    print(f"✅ Final report generated successfully!")
    print(f"📄 Output: {output_path}")
    print(f"📈 Enhanced content: {enhancement_ratio:.1f}% of original ({final_size:,} chars)")
    print(f"🖼️  Integrated diagrams: {total_diagrams}")
    
    return True

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Generate final comprehensive report with integrated diagrams")
    parser.add_argument("--settings", help="Path to settings JSON file")
    parser.add_argument("--api-key", help="Google API key for Gemini")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--skip-explanations", action="store_true", help="Skip AI-generated explanations for faster testing")
    
    args = parser.parse_args()
    
    # Load settings
    settings = load_settings(args.settings)
    
    # Get API key (only if not skipping explanations)
    api_key = None
    if not args.skip_explanations:
        api_key = args.api_key or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            try:
                with open('.env', 'r') as f:
                    for line in f:
                        if line.startswith('GOOGLE_API_KEY='):
                            api_key = line.split('=', 1)[1].strip()
                            break
            except FileNotFoundError:
                pass
        
        if not api_key:
            print("❌ Error: Google API key not found.")
            print("Set GOOGLE_API_KEY environment variable, create .env file, or use --api-key parameter")
            print("Or use --skip-explanations for testing without AI-generated explanations")
            sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs('output', exist_ok=True)
    
    # Generate the final report
    success = generate_final_report(settings, api_key, skip_explanations=args.skip_explanations)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 