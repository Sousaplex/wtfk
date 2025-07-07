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

def generate_diagram_explanation(llm, diagram: Dict, context: Dict, settings: Dict) -> str:
    """Generate contextual explanation for a diagram using a template."""
    
    data_focus = diagram.get('data_focus', '')
    relevant_data = "No specific data sample provided."
    if data_focus and 'summary_stats' in context:
        stats = context['summary_stats']
        if data_focus in stats:
            data_sample = stats[data_focus]
            if isinstance(data_sample, list):
                relevant_data = ", ".join([f"{item[0]} ({item[1]})" for item in data_sample[:5]])
            elif isinstance(data_sample, dict):
                relevant_data = ", ".join([f"{k}: {v}" for k, v in list(data_sample.items())[:5]])

    try:
        prompts_dir = settings.get("paths", {}).get("prompts_dir", "prompts")
        prompt_path = Path(prompts_dir) / "diagram_explanation.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        prompt = template_content.format(
            current_date=datetime.now().strftime('%B %d, %Y'),
            diagram_title=diagram.get('title', 'Untitled'),
            diagram_type=diagram.get('graph_type', 'Unknown'),
            target_section=diagram.get('target_section', 'General Analysis'),
            relevant_data=relevant_data
        )
        
        response = llm.invoke(prompt)
        return response.content.strip() if hasattr(response, 'content') else str(response).strip()

    except Exception as e:
        print(f"Warning: Failed to generate explanation for {diagram.get('title', 'diagram')}: {e}")
        return f"This {diagram.get('graph_type', 'visualization')} provides insights into the {diagram.get('target_section', 'database schema')} structure and relationships."

def insert_diagrams_into_section(section_content: str, diagrams: List[Dict], explanations: Dict) -> str:
    """Insert interactive diagrams and explanations into a section's content."""
    if not diagrams:
        return section_content
    
    lines = section_content.split('\n')
    insertion_point = len(lines)
    
    for i, line in enumerate(lines):
        if re.match(r'^#{2,6}\s+', line) and i > 0:
            insertion_point = i
            break
    
    diagram_content = []
    for diagram in diagrams:
        # The file_path from the report now includes the .html extension
        filename = os.path.basename(diagram.get('file_path', ''))
        title = diagram.get('title', 'Visualization')
        explanation = explanations.get(filename, '')
        
        if filename:
            diagram_content.extend([
                '',
                f'### {title}',
                '',
                f'<iframe src="diagrams/{filename}" width="100%" height="500px" style="border:none; background: #f8f9fa; border-radius: 8px;"></iframe>',
                '',
                explanation,
                ''
            ])
    
    result_lines = lines[:insertion_point] + diagram_content + lines[insertion_point:]
    return '\n'.join(result_lines)

def generate_final_report_with_diagrams(settings_file=None, api_key=None, skip_explanations=False):
    """
    High-level function to generate the final comprehensive report with integrated diagrams.
    Returns True on success, False on failure.
    """
    print("🔄 Starting final report generation...")
    
    settings = load_settings(settings_file)
    
    # Load required files
    try:
        import glob
        analysis_files = glob.glob(f"{settings['paths']['output_dir']}/schema_analysis*.md")
        if not analysis_files:
            print("❌ Error: No schema analysis file found. Run analysis first.")
            return False
        
        analysis_file = max(analysis_files, key=os.path.getmtime)
        with open(analysis_file, 'r') as f:
            analysis_content = f.read()
        print(f"✓ Loaded analysis report: {analysis_file}")
    except Exception as e:
        print(f"❌ Error loading analysis report: {e}")
        return False
    
    try:
        plan_path = f"{settings['paths']['output_dir']}/visualization_plan.json"
        with open(plan_path, 'r') as f:
            viz_plan = json.load(f)
        print("✓ Loaded visualization plan")
    except FileNotFoundError:
        print(f"❌ Error: {plan_path} not found. Run visualization planning first.")
        return False
    
    try:
        report_path = f"{settings['paths']['output_dir']}/generation_report.json"
        with open(report_path, 'r') as f:
            generation_report = json.load(f)
        print("✓ Loaded generation report")
    except FileNotFoundError:
        print(f"❌ Error: {report_path} not found. Run diagram generation first.")
        return False
    
    try:
        context_files = glob.glob(f"{settings['paths']['context_dir']}/*_context.json")
        if not context_files:
            print("❌ Error: No context file found. Run context generation first.")
            return False
        
        context_file = max(context_files, key=os.path.getmtime)
        with open(context_file, 'r') as f:
            context = json.load(f)
        print(f"✓ Loaded context data: {context_file}")
    except Exception as e:
        print(f"❌ Error loading context data: {e}")
        return False
    
    llm = None
    if not skip_explanations:
        effective_api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not effective_api_key:
            print("Warning: No API key. Skipping diagram explanations.")
            skip_explanations = True
        else:
            llm = setup_gemini(effective_api_key, settings.get('model', {}))
            print("✓ Initialized Gemini model")
    else:
        print("✓ Skipping LLM initialization (explanations disabled)")

    sections = parse_markdown_sections(analysis_content)
    print(f"✓ Parsed {len(sections)} sections from analysis")
    
    section_diagrams = match_diagrams_to_sections(sections, viz_plan, generation_report)
    total_diagrams = sum(len(diagrams) for diagrams in section_diagrams.values())
    print(f"✓ Matched {total_diagrams} diagrams to sections")
    
    # Generate explanations for all diagrams in parallel
    print("🔄 Generating diagram explanations...")
    explanations = {}
    all_diagrams = [d for diagrams in section_diagrams.values() for d in diagrams]

    if not skip_explanations and total_diagrams > 0 and llm:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from tqdm import tqdm

        max_workers = settings.get("performance", {}).get("max_workers_explanations", 5)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_diagram = {executor.submit(generate_diagram_explanation, llm, diagram, context, settings): diagram for diagram in all_diagrams}
            
            for future in tqdm(as_completed(future_to_diagram), total=len(all_diagrams), desc="Generating Explanations"):
                diagram = future_to_diagram[future]
                try:
                    explanation = future.result()
                    explanations[diagram.get('filename')] = explanation
                except Exception as exc:
                    print(f"'{diagram.get('title')}' generated an exception: {exc}")
                    explanations[diagram.get('filename')] = "Error generating explanation."
    else:
        for diagram in all_diagrams:
            explanations[diagram.get('filename')] = "AI explanation generation was skipped."
    
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
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_by = settings.get('project', {}).get('generated_by', 'WTFK (What The Foreign Key)')
    header = f"<!-- Generated by {generated_by} Pipeline -->\n<!-- Timestamp: {timestamp} -->\n<!-- Diagrams: {total_diagrams} visualizations integrated -->\n\n"
    
    final_report = header + '\n'.join(final_content)
    
    output_path = Path(settings['paths']['output_dir']) / 'final_report.md'
    with open(output_path, 'w') as f:
        f.write(final_report)
    
    original_size = len(analysis_content)
    final_size = len(final_report)
    enhancement_ratio = (final_size / original_size) * 100 if original_size > 0 else 0
    
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
    
    api_key = args.api_key or os.getenv('GOOGLE_API_KEY')
    if not args.skip_explanations and not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv('GOOGLE_API_KEY')
        except ImportError:
            pass

    if not args.skip_explanations and not api_key:
        print("❌ Error: Google API key not found.")
        sys.exit(1)
    
    os.makedirs('output', exist_ok=True)
    
    if not generate_final_report_with_diagrams(args.settings, api_key, args.skip_explanations):
        sys.exit(1)

if __name__ == "__main__":
    main() 