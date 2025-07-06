#!/usr/bin/env python3
"""
PostgreSQL Schema Context Generator

This script analyzes a compressed database schema and generates deterministic 
statistics and metadata that can be used as context for LLM analysis.

LLMs are great at interpretation but poor at precise counting and analysis,
so this script pre-computes all the numerical and structural data.
"""

import argparse
import sys
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime


class SchemaContextGenerator:
    def __init__(self, settings_file="settings.json"):
        self.tables = {}
        self.relationships = []
        self.statistics = {}
        self.settings = self.load_settings(settings_file)
    
    def load_settings(self, settings_file):
        """Load settings from JSON file with fallback to defaults."""
        default_settings = {
            "context_generation": {
                "max_displayed_items": 10,
                "enable_ai_categorization": True,
                "fallback_categorization": {
                    "auth_security": ["auth", "user", "permission", "role", "token", "session"],
                    "audit_logging": ["log", "audit", "change", "history", "event"],
                    "configuration": ["config", "setting", "param", "lookup", "type", "status", "category"],
                    "integration": ["api", "webhook", "external", "import", "export", "sync"],
                    "temporary_cache": ["temp", "cache", "queue", "pending"]
                }
            }
        }
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
            
            # Deep merge user settings with defaults
            if 'context_generation' in user_settings:
                for key, value in user_settings['context_generation'].items():
                    default_settings['context_generation'][key] = value
            
            print(f"Loaded context settings from: {settings_file}")
            return default_settings
            
        except FileNotFoundError:
            print(f"Settings file '{settings_file}' not found. Using defaults.")
            return default_settings
        except json.JSONDecodeError as e:
            print(f"Error parsing settings file '{settings_file}': {e}")
            print("Using default settings.")
            return default_settings
        except Exception as e:
            print(f"Error loading settings file '{settings_file}': {e}")
            print("Using default settings.")
            return default_settings
        
    def parse_compressed_schema(self, schema_content):
        """Parse the compressed schema format and extract metadata."""
        
        lines = schema_content.strip().split('\n')
        current_table = None
        
        for line in lines:
            original_line = line  # Keep original line with indentation
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('--'):
                continue
            
            # New table definition
            if line.endswith(':') and not original_line.startswith(' '):
                current_table = line[:-1]
                self.tables[current_table] = {
                    'columns': [],
                    'primary_keys': [],
                    'foreign_keys': [],
                    'unique_constraints': [],
                    'indexes': [],
                    'column_types': Counter(),
                    'nullable_columns': 0,
                    'required_columns': 0
                }
                continue
            
            if current_table is None:
                continue
            
            # Column definitions (including quoted column names)
            if (original_line.startswith('  ') and ':' in line and 
                not original_line.startswith('  FK') and 
                not original_line.startswith('  UNIQUE') and 
                not original_line.startswith('  IDX') and 
                not original_line.startswith('  PRIMARY')):
                self._parse_column(line, current_table)
            
            # Foreign key relationships
            elif original_line.startswith('  FK ('):
                self._parse_foreign_key(line, current_table)
            
            # Unique constraints
            elif original_line.startswith('  UNIQUE ('):
                self._parse_unique_constraint(line, current_table)
            
            # Primary key constraints
            elif original_line.startswith('  PRIMARY KEY ('):
                self._parse_primary_key(line, current_table)
            
            # Indexes
            elif original_line.startswith('  IDX ('):
                self._parse_index(line, current_table)
    
    def _parse_column(self, line, table_name):
        """Parse a column definition."""
        # Format: "  column_name: type [NOT NULL] [DEFAULT value]"
        line = line.strip()
        
        if ': PK' in line:
            # Auto-incrementing primary key
            col_name = line.split(':')[0].strip().strip('"')  # Remove quotes if present
            self.tables[table_name]['columns'].append(col_name)
            self.tables[table_name]['primary_keys'].append(col_name)
            self.tables[table_name]['column_types']['integer'] += 1
            self.tables[table_name]['required_columns'] += 1
        else:
            # Regular column
            parts = line.split(':', 1)  # Split only on first colon
            if len(parts) >= 2:
                col_name = parts[0].strip().strip('"')  # Remove quotes if present
                col_def = parts[1].strip()
                
                self.tables[table_name]['columns'].append(col_name)
                
                # Extract data type (first word)
                if col_def:
                    data_type = col_def.split()[0].lower()
                    self.tables[table_name]['column_types'][data_type] += 1
                    
                    # Check if nullable
                    if 'NOT NULL' in col_def.upper():
                        self.tables[table_name]['required_columns'] += 1
                    else:
                        self.tables[table_name]['nullable_columns'] += 1
    
    def _parse_foreign_key(self, line, table_name):
        """Parse a foreign key relationship."""
        # Format: "  FK (local_col) > ref_table(ref_col) [DEFERRABLE]"
        import re
        
        match = re.search(r'FK \(([^)]+)\) > (\w+)\(([^)]+)\)', line)
        if match:
            local_col = match.group(1).strip()
            ref_table = match.group(2).strip()
            ref_col = match.group(3).strip()
            
            fk_info = {
                'from_table': table_name,
                'from_column': local_col,
                'to_table': ref_table,
                'to_column': ref_col,
                'deferrable': 'DEFERRABLE' in line.upper()
            }
            
            self.tables[table_name]['foreign_keys'].append(fk_info)
            self.relationships.append(fk_info)
    
    def _parse_unique_constraint(self, line, table_name):
        """Parse a unique constraint."""
        # Format: "  UNIQUE (col1, col2, ...)"
        import re
        
        match = re.search(r'UNIQUE \(([^)]+)\)', line)
        if match:
            columns = [col.strip() for col in match.group(1).split(',')]
            self.tables[table_name]['unique_constraints'].append(columns)
    
    def _parse_primary_key(self, line, table_name):
        """Parse a primary key constraint."""
        # Format: "  PRIMARY KEY (col1, col2, ...)"
        import re
        
        match = re.search(r'PRIMARY KEY \(([^)]+)\)', line)
        if match:
            columns = [col.strip() for col in match.group(1).split(',')]
            self.tables[table_name]['primary_keys'].extend(columns)
    
    def _parse_index(self, line, table_name):
        """Parse an index definition."""
        # Format: "  IDX (col1, col2, ...) [UNIQUE] [(LIKE)]"
        import re
        
        match = re.search(r'IDX \(([^)]+)\)', line)
        if match:
            columns = [col.strip() for col in match.group(1).split(',')]
            index_info = {
                'columns': columns,
                'unique': 'UNIQUE' in line.upper(),
                'like_ops': '(LIKE)' in line.upper()
            }
            self.tables[table_name]['indexes'].append(index_info)
    
    def generate_statistics(self):
        """Generate comprehensive statistics from the parsed schema."""
        
        # Basic counts
        self.statistics['table_count'] = len(self.tables)
        self.statistics['total_columns'] = sum(len(table['columns']) for table in self.tables.values())
        self.statistics['total_foreign_keys'] = len(self.relationships)
        
        # Column statistics
        self.statistics['total_required_columns'] = sum(table['required_columns'] for table in self.tables.values())
        self.statistics['total_nullable_columns'] = sum(table['nullable_columns'] for table in self.tables.values())
        
        # Data type distribution
        all_types = Counter()
        for table in self.tables.values():
            all_types.update(table['column_types'])
        self.statistics['data_type_distribution'] = dict(all_types.most_common())
        
        # Table size analysis
        table_sizes = [(name, len(table['columns'])) for name, table in self.tables.items()]
        table_sizes.sort(key=lambda x: x[1], reverse=True)
        
        max_items = self.settings['context_generation']['max_displayed_items']
        self.statistics['largest_tables'] = table_sizes[:max_items]
        self.statistics['smallest_tables'] = table_sizes[-max_items:] if len(table_sizes) > max_items else []
        
        # Foreign key analysis
        fk_counts = defaultdict(int)
        incoming_fk_counts = defaultdict(int)
        
        for fk in self.relationships:
            fk_counts[fk['from_table']] += 1
            incoming_fk_counts[fk['to_table']] += 1
        
        # Tables with most outgoing FKs
        most_connected_out = sorted(fk_counts.items(), key=lambda x: x[1], reverse=True)
        self.statistics['most_outgoing_fks'] = most_connected_out[:max_items]
        
        # Tables with most incoming FKs (most referenced)
        most_referenced = sorted(incoming_fk_counts.items(), key=lambda x: x[1], reverse=True)
        self.statistics['most_referenced_tables'] = most_referenced[:max_items]
        
        # Tables with no FKs (potential root entities)
        tables_without_fks = [name for name in self.tables.keys() if fk_counts[name] == 0]
        self.statistics['tables_without_outgoing_fks'] = tables_without_fks
        
        # Tables never referenced (potential leaf entities)
        never_referenced = [name for name in self.tables.keys() if incoming_fk_counts[name] == 0]
        self.statistics['never_referenced_tables'] = never_referenced
        
        # Constraint analysis
        total_unique_constraints = sum(len(table['unique_constraints']) for table in self.tables.values())
        total_indexes = sum(len(table['indexes']) for table in self.tables.values())
        
        self.statistics['total_unique_constraints'] = total_unique_constraints
        self.statistics['total_indexes'] = total_indexes
        
        # Primary key analysis
        tables_with_composite_pk = []
        tables_without_pk = []
        
        for name, table in self.tables.items():
            if len(table['primary_keys']) > 1:
                tables_with_composite_pk.append(name)
            elif len(table['primary_keys']) == 0:
                tables_without_pk.append(name)
        
        self.statistics['tables_with_composite_pk'] = tables_with_composite_pk
        self.statistics['tables_without_pk'] = tables_without_pk
        
        # Relationship patterns
        self.statistics['self_referencing_tables'] = []
        table_connections = defaultdict(set)
        
        for fk in self.relationships:
            if fk['from_table'] == fk['to_table']:
                self.statistics['self_referencing_tables'].append(fk['from_table'])
            table_connections[fk['from_table']].add(fk['to_table'])
        
        # Calculate average columns per table
        if self.statistics['table_count'] > 0:
            self.statistics['avg_columns_per_table'] = round(
                self.statistics['total_columns'] / self.statistics['table_count'], 2
            )
            self.statistics['avg_fks_per_table'] = round(
                self.statistics['total_foreign_keys'] / self.statistics['table_count'], 2
            )
        
        # Domain analysis based on table name patterns
        self.statistics['table_categories'] = self._categorize_tables()
    
    def _categorize_tables(self):
        """Categorize tables using AI-based analysis or fallback to generic patterns."""
        
        # Check if AI categorization is enabled
        if self.settings['context_generation'].get('enable_ai_categorization', False):
            return self._ai_categorize_tables()
        else:
            return self._fallback_categorize_tables()
    
    def _ai_categorize_tables(self):
        """Use AI to intelligently categorize tables based on their structure and names."""
        try:
            # Import LangChain components
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain.prompts import PromptTemplate
            from langchain.schema import StrOutputParser
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            api_key = os.getenv('GOOGLE_API_KEY')
            
            if not api_key:
                print("Warning: No Google API key found. Using fallback categorization.")
                return self._fallback_categorize_tables()
            
            # Initialize LLM
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-pro",
                google_api_key=api_key,
                temperature=0.1,
                max_output_tokens=4000
            )
            
            # Prepare table information for AI analysis
            table_info = []
            for name, table in self.tables.items():
                # Get a sample of column names to understand table purpose
                column_sample = table['columns'][:10]  # First 10 columns
                fk_count = len(table['foreign_keys'])
                
                table_info.append({
                    'name': name,
                    'columns': column_sample,
                    'column_count': len(table['columns']),
                    'foreign_key_count': fk_count
                })
            
            # Load prompt from file
            prompt_file = self.settings['context_generation']['table_categorization_prompt']
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_template = f.read()
            except FileNotFoundError:
                print(f"Warning: Prompt file '{prompt_file}' not found. Using fallback categorization.")
                return self._fallback_categorize_tables()
            except Exception as e:
                print(f"Warning: Failed to load prompt file '{prompt_file}': {e}. Using fallback categorization.")
                return self._fallback_categorize_tables()
            
            # Create prompt for AI categorization
            prompt = PromptTemplate(
                input_variables=["table_info"],
                template=prompt_template
            )
            
            # Get AI categorization
            chain = prompt | llm | StrOutputParser()
            
            print("🤖 Using AI to categorize tables by domain...")
            table_info_str = "\n".join([
                f"- {t['name']}: {t['column_count']} columns, {t['foreign_key_count']} FKs, sample columns: {', '.join(t['columns'][:5])}"
                for t in table_info[:50]  # Limit to first 50 tables to avoid token limits
            ])
            
            result = chain.invoke({"table_info": table_info_str})
            
            # Parse AI result
            import json
            try:
                # Extract JSON from the result
                if '```json' in result:
                    json_str = result.split('```json')[1].split('```')[0].strip()
                elif '{' in result and '}' in result:
                    # Find the JSON object in the response
                    start = result.find('{')
                    end = result.rfind('}') + 1
                    json_str = result[start:end]
                else:
                    raise ValueError("No JSON found in AI response")
                
                ai_categories = json.loads(json_str)
                
                # Organize by category
                categories = {}
                available_categories = [
                    'business_core', 'auth_security', 'audit_logging', 'integration',
                    'configuration', 'user_management', 'content_media', 'financial_commerce',
                    'communication', 'analytics_reporting', 'workflow_process'
                ]
                
                for category in available_categories:
                    categories[category] = []
                
                # Assign tables to categories
                for table_name in self.tables.keys():
                    if table_name in ai_categories:
                        category = ai_categories[table_name]
                        if category in categories:
                            categories[category].append(table_name)
                        else:
                            categories['business_core'].append(table_name)
                    else:
                        categories['business_core'].append(table_name)
                
                print(f"✅ AI categorized {len(self.tables)} tables into {len([c for c in categories.values() if c])} domain categories")
                return categories
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"Warning: Failed to parse AI categorization result: {e}")
                print("Falling back to pattern-based categorization.")
                return self._fallback_categorize_tables()
            
        except ImportError:
            print("Warning: LangChain not available. Using fallback categorization.")
            return self._fallback_categorize_tables()
        except Exception as e:
            print(f"Warning: AI categorization failed: {e}")
            print("Using fallback categorization.")
            return self._fallback_categorize_tables()
    
    def _fallback_categorize_tables(self):
        """Fallback categorization using generic keyword patterns."""
        # Get fallback category keywords from settings
        category_keywords = self.settings['context_generation']['fallback_categorization']
        
        # Initialize categories
        categories = {category: [] for category in category_keywords.keys()}
        categories['business_core'] = []  # Always have business_core as fallback
        
        for table_name in self.tables.keys():
            name_lower = table_name.lower()
            categorized = False
            
            # Check each category against its keywords
            for category, keywords in category_keywords.items():
                if any(keyword in name_lower for keyword in keywords):
                    categories[category].append(table_name)
                    categorized = True
                    break
            
            # If not categorized, put in business_core
            if not categorized:
                categories['business_core'].append(table_name)
        
        return categories
    
    def save_context(self, output_dir, schema_file_name):
        """Save all context data to JSON files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Generate base name from schema file
        base_name = Path(schema_file_name).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        context_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'source_schema': schema_file_name,
                'generator_version': '1.0.0'
            },
            'statistics': self.statistics,
            'tables': self.tables,
            'relationships': self.relationships
        }
        
        # Save main context file
        context_file = output_path / f"{base_name}_context.json"
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, indent=2, ensure_ascii=False)
        
        # Save statistics summary (for easy prompt injection)
        stats_file = output_path / f"{base_name}_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.statistics, f, indent=2, ensure_ascii=False)
        
        return context_file, stats_file
    
    def generate_summary_text(self):
        """Generate a human-readable summary for prompt injection."""
        summary = []
        max_items = self.settings['context_generation']['max_displayed_items']
        
        # For summary, use half the max_items for a more concise display
        summary_limit = max(3, max_items // 2)
        
        summary.append("## Schema Statistics Summary")
        summary.append(f"- **Total Tables**: {self.statistics['table_count']}")
        summary.append(f"- **Total Columns**: {self.statistics['total_columns']}")
        summary.append(f"- **Total Foreign Key Relationships**: {self.statistics['total_foreign_keys']}")
        summary.append(f"- **Average Columns per Table**: {self.statistics.get('avg_columns_per_table', 0)}")
        summary.append(f"- **Average Foreign Keys per Table**: {self.statistics.get('avg_fks_per_table', 0)}")
        summary.append("")
        
        summary.append("## Table Size Distribution")
        if self.statistics['largest_tables']:
            summary.append("**Largest Tables (by column count):**")
            for table, count in self.statistics['largest_tables'][:summary_limit]:
                summary.append(f"- {table}: {count} columns")
        summary.append("")
        
        summary.append("## Most Connected Tables")
        if self.statistics['most_referenced_tables']:
            summary.append("**Most Referenced Tables (incoming FKs):**")
            for table, count in self.statistics['most_referenced_tables'][:summary_limit]:
                summary.append(f"- {table}: {count} incoming foreign keys")
        summary.append("")
        
        summary.append("## Data Type Distribution")
        for data_type, count in list(self.statistics['data_type_distribution'].items())[:max_items]:
            summary.append(f"- {data_type}: {count} columns")
        summary.append("")
        
        summary.append("## Table Categories")
        for category, tables in self.statistics['table_categories'].items():
            if tables:
                summary.append(f"- **{category.replace('_', ' ').title()}**: {len(tables)} tables")
        
        return '\n'.join(summary)


def main():
    parser = argparse.ArgumentParser(
        description="Generate context and statistics from compressed PostgreSQL schema"
    )
    parser.add_argument(
        "schema_file",
        help="Path to compressed schema file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory for context files",
        default="context"
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Print detailed statistics",
        action="store_true"
    )
    parser.add_argument(
        "-s", "--settings",
        help="Path to settings.json file",
        default="settings.json"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    schema_path = Path(args.schema_file)
    if not schema_path.exists():
        print(f"Error: Schema file '{args.schema_file}' not found.")
        sys.exit(1)
    
    print(f"Generating context from: {schema_path}")
    print(f"Output directory: {args.output}")
    print()
    
    # Load and parse schema
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_content = f.read()
    except Exception as e:
        print(f"Error reading schema file: {e}")
        sys.exit(1)
    
    # Generate context
    generator = SchemaContextGenerator(settings_file=args.settings)
    generator.parse_compressed_schema(schema_content)
    generator.generate_statistics()
    
    # Save context files
    context_file, stats_file = generator.save_context(args.output, args.schema_file)
    
    print(f"Context generated successfully!")
    print(f"- Main context: {context_file}")
    print(f"- Statistics: {stats_file}")
    print()
    
    # Display summary
    if args.verbose:
        print("=== SCHEMA STATISTICS ===")
        print(generator.generate_summary_text())
        print()
    else:
        stats = generator.statistics
        print(f"Summary: {stats['table_count']} tables, {stats['total_columns']} columns, {stats['total_foreign_keys']} relationships")
    
    print("Context files ready for AI analysis!")


if __name__ == "__main__":
    main() 