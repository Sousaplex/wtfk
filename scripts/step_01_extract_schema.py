#!/usr/bin/env python3
"""
SQL Schema Extractor

This script extracts only the schema definitions from a SQL file,
removing all INSERT statements and data while preserving:
- CREATE statements (TABLE, SEQUENCE, INDEX, VIEW, etc.)
- ALTER statements
- COMMENT statements
- Database configuration statements
- TOC entries and comments
"""

import re
import argparse
import sys
from pathlib import Path


def is_schema_statement(line):
    """
    Determine if a line contains a schema definition statement.
    Returns True for statements that should be kept in the schema-only file.
    """
    line_stripped = line.strip().upper()
    
    # Skip empty lines and comments - we'll handle these separately
    if not line_stripped or line_stripped.startswith('--'):
        return True
    
    # Schema-related statements to keep
    schema_keywords = [
        'CREATE TABLE',
        'CREATE SEQUENCE',
        'CREATE INDEX',
        'CREATE UNIQUE INDEX',
        'CREATE VIEW',
        'CREATE SCHEMA',
        'CREATE FUNCTION',
        'CREATE TRIGGER',
        'CREATE TYPE',
        'CREATE DOMAIN',
        'CREATE EXTENSION',
        'ALTER TABLE',
        'ALTER SEQUENCE',
        'ALTER INDEX',
        'ALTER VIEW',
        'ALTER SCHEMA',
        'ALTER FUNCTION',
        'ALTER TRIGGER',
        'ALTER TYPE',
        'ALTER DOMAIN',
        'COMMENT ON',
        'SET ',
        'SELECT PG_CATALOG.SET_CONFIG',
        'DROP TABLE',
        'DROP SEQUENCE',
        'DROP INDEX',
        'DROP VIEW',
        'DROP SCHEMA',
        'DROP FUNCTION',
        'DROP TRIGGER',
        'DROP TYPE',
        'DROP DOMAIN',
        'DROP EXTENSION',
    ]
    
    # Check if line starts with any schema keyword
    for keyword in schema_keywords:
        if line_stripped.startswith(keyword):
            return True
    
    # Keep TOC entries (PostgreSQL dump specific)
    if line_stripped.startswith('-- TOC ENTRY'):
        return True
    
    # Keep dependency comments
    if line_stripped.startswith('-- DEPENDENCIES:'):
        return True
    
    # Keep name/type/schema comments
    if line_stripped.startswith('-- NAME:'):
        return True
    
    return False


def is_insert_statement(line):
    """
    Determine if a line is part of an INSERT statement or data loading.
    """
    line_stripped = line.strip().upper()
    
    # INSERT statements
    if line_stripped.startswith('INSERT INTO'):
        return True
    
    # COPY statements (PostgreSQL bulk data loading)
    if line_stripped.startswith('COPY ') and ' FROM ' in line_stripped:
        return True
    
    return False


def extract_schema(input_file, output_file):
    """
    Extract schema from input SQL file and write to output file.
    """
    print(f"Reading from: {input_file}")
    print(f"Writing to: {output_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return False
    except UnicodeDecodeError:
        print(f"Error: Could not decode '{input_file}'. Trying with latin-1 encoding.")
        try:
            with open(input_file, 'r', encoding='latin-1') as infile:
                lines = infile.readlines()
        except Exception as e:
            print(f"Error reading file: {e}")
            return False
    
    schema_lines = []
    in_copy_block = False
    in_insert_block = False
    total_lines = len(lines)
    
    print(f"Processing {total_lines} lines...")
    
    for i, line in enumerate(lines):
        line_stripped = line.strip().upper()
        
        if line_stripped.startswith('COPY '):
            in_copy_block = True
            continue
        
        if in_copy_block:
            if line_stripped == '\\.':
                in_copy_block = False
            continue
        
        if line_stripped.startswith('INSERT INTO'):
            in_insert_block = True
            continue
        
        if in_insert_block:
            if line_stripped.endswith(';'):
                in_insert_block = False
            continue
        
        if is_insert_statement(line):
            continue
        
        schema_lines.append(line)
        
        if i > 0 and i % 5000 == 0:
            print(f"Processed {i}/{total_lines} lines...")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.writelines(schema_lines)
        
        # Count tables in the output
        table_count = sum(1 for line in schema_lines if line.strip().upper().startswith('CREATE TABLE'))
        
        print(f"Schema extraction complete!")
        print(f"  - Original file: {total_lines} lines")
        print(f"  - Schema file: {len(schema_lines)} lines")
        print(f"  - Reduction: {((total_lines - len(schema_lines)) / total_lines * 100):.1f}%")
        print(f"  - Tables Found: {table_count}")
        
        return True
        
    except Exception as e:
        print(f"Error writing output file: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Extract schema definitions from SQL files, removing INSERT statements and data"
    )
    parser.add_argument(
        "input_file",
        help="Input SQL file path"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: input_file_schema.sql)",
        default=None
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_file}' does not exist.")
        sys.exit(1)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("schemas") / "schema_only.sql"
        # Ensure schemas directory exists
        output_path.parent.mkdir(exist_ok=True)
    
    success = extract_schema(input_path, output_path)
    
    if success:
        print(f"\nSchema successfully extracted to: {output_path}")
    else:
        print("\nSchema extraction failed.")
        sys.exit(1)


if __name__ == "__main__":
    main() 