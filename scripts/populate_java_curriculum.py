#!/usr/bin/env python3
"""
Seed script to populate Java curricula concepts and relationships from JSON.
"""

import argparse
import json
import os
import sys
import psycopg2

# Calculate the default JSON path relative to the script location
DEFAULT_JSON_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../backend/curricula/programming/java.json"
    )
)

def main():
    parser = argparse.ArgumentParser(description="Populate domain, concepts, and concept relationships from a curriculum JSON file.")
    parser.add_argument(
        "--file", "-f",
        default=DEFAULT_JSON_PATH,
        help=f"Path to the curriculum JSON file (default: {DEFAULT_JSON_PATH})"
    )
    parser.add_argument(
        "--db-url", "-d",
        default=os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"),
        help="PostgreSQL connection URL (default: DATABASE_URL env var or postgresql://postgres:postgres@localhost:5432/postgres)"
    )
    parser.add_argument(
        "--domain-name",
        default="Java Interview Preparation",
        help="Name of the new domain to create (default: 'Java Interview Preparation')"
    )
    parser.add_argument(
        "--domain-version",
        default="1.0",
        help="Version of the new domain to create (default: '1.0')"
    )
    
    args = parser.parse_args()
    
    # Resolve relative paths relative to current working directory if not absolute
    json_path = os.path.abspath(args.file)
    
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at '{json_path}'", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error parsing JSON file: {e}", file=sys.stderr)
        sys.exit(1)
        
    concepts = data.get("concepts", [])
    relationships = data.get("relationships", [])
    
    if not concepts:
        print("Warning: No concepts found in the JSON file. Nothing to do.")
        sys.exit(0)
        
    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(args.db_url)
    except Exception as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)
        
    try:
        with conn:
            with conn.cursor() as cur:
                # 1. Create the new domain
                print(f"Creating new domain: '{args.domain_name}' (Version: {args.domain_version})...")
                cur.execute(
                    "INSERT INTO domains (name, version) VALUES (%s, %s) RETURNING id",
                    (args.domain_name, args.domain_version)
                )
                domain_id = cur.fetchone()[0]
                print(f"Domain created with ID: {domain_id}")
                
                # 2. Insert concepts
                print(f"Inserting {len(concepts)} concepts...")
                concept_name_to_id = {}
                
                for idx, concept in enumerate(concepts):
                    name = concept.get("name")
                    path = concept.get("path")
                    difficulty = concept.get("difficulty", 0.0)
                    metadata = concept.get("metadata", {})
                    
                    if not name or not path:
                        print(f"Warning: Concept at index {idx} is missing name or path. Skipping.")
                        continue
                        
                    cur.execute(
                        """
                        INSERT INTO concepts (domain_id, name, path, difficulty, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (domain_id, name, path, difficulty, json.dumps(metadata))
                    )
                    concept_id = cur.fetchone()[0]
                    concept_name_to_id[name] = concept_id
                
                print("All concepts inserted successfully.")
                
                # 3. Insert relationships
                print(f"Inserting {len(relationships)} concept relationships...")
                inserted_relationships_count = 0
                for idx, rel in enumerate(relationships):
                    source_name = rel.get("source")
                    target_name = rel.get("target")
                    relation_type = rel.get("relation_type", "prerequisite")
                    
                    if not source_name or not target_name:
                        print(f"Warning: Relationship at index {idx} is missing source or target. Skipping.")
                        continue
                        
                    source_id = concept_name_to_id.get(source_name)
                    target_id = concept_name_to_id.get(target_name)
                    
                    if not source_id:
                        print(f"Warning: Source concept '{source_name}' not found. Skipping relationship.")
                        continue
                    if not target_id:
                        print(f"Warning: Target concept '{target_name}' not found. Skipping relationship.")
                        continue
                        
                    cur.execute(
                        """
                        INSERT INTO concept_relationships (source_id, target_id, relation_type)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (source_id, target_id, relation_type) DO NOTHING
                        """,
                        (source_id, target_id, relation_type)
                    )
                    inserted_relationships_count += 1
                
                print(f"Successfully inserted {inserted_relationships_count} relationships.")
                
        print(f"Database population completed successfully!")
        
    except Exception as e:
        print(f"Error during database operation: {e}", file=sys.stderr)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
