"""
Single File Ingestion Script for Legal Documents

This script allows you to ingest a single JSON file into the Neo4j database
without re-running the entire ingestion pipeline.

Usage:
    python ingest_single_file.py <path_to_json_file>
    
    OR
    
    python ingest_single_file.py --interactive
    
Example:
    python ingest_single_file.py ../../data/legal_data/constitution_1973.json
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.graph_rag.legal_graph_builder import LegalGraphBuilder
from dotenv import load_dotenv
import argparse

load_dotenv()

def check_file_exists_in_db(builder, json_file_path):
    """
    Check if a document from this JSON file already exists in the database
    
    Returns:
        tuple: (exists: bool, doc_title: str)
    """
    try:
        import json
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        doc_title = data['document']['title']
        
        with builder.driver.session() as session:
            result = session.run(
                "MATCH (d:Document {title: $title}) RETURN d.title as title, count(d) as count",
                title=doc_title
            )
            record = result.single()
            exists = record['count'] > 0 if record else False
            
            return exists, doc_title
    except Exception as e:
        print(f"Error checking database: {e}")
        return False, None

def delete_document(builder, doc_title):
    """
    Delete a document and all its relationships from the database
    """
    print(f"\n🗑️  Deleting existing document: {doc_title}")
    
    with builder.driver.session() as session:
        # Delete all related nodes and relationships
        delete_query = """
        MATCH (d:Document {title: $title})
        OPTIONAL MATCH (d)-[:CONTAINS]->(a:Article)
        OPTIONAL MATCH (a)-[:CONTAINS]->(c:Clause)
        OPTIONAL MATCH (c)-[:CONTAINS]->(s:SubClause)
        OPTIONAL MATCH (a)-[r]-()
        DETACH DELETE d, a, c, s
        """
        session.run(delete_query, title=doc_title)
    
    print(f"✅ Deleted successfully")

def ingest_single_file(json_file_path, force_overwrite=False):
    """
    Ingest a single JSON file into the database
    
    Args:
        json_file_path: Path to the JSON file
        force_overwrite: If True, overwrites existing document without asking
    """
    # Validate file exists
    if not os.path.exists(json_file_path):
        print(f"❌ Error: File not found: {json_file_path}")
        return False
    
    if not json_file_path.endswith('.json'):
        print(f"❌ Error: File must be a JSON file: {json_file_path}")
        return False
    
    print("\n" + "=" * 70)
    print("Single File Ingestion - Legal AI Advisor")
    print("=" * 70)
    print(f"📄 File: {json_file_path}")
    
    # Initialize builder
    builder = LegalGraphBuilder(
        uri=os.getenv('NEO4J_URI'),
        username=os.getenv('NEO4J_USER'),
        password=os.getenv('NEO4J_PASSWORD')
    )
    
    try:
        # Check if document already exists
        exists, doc_title = check_file_exists_in_db(builder, json_file_path)
        
        if exists:
            print(f"\n⚠️  WARNING: Document '{doc_title}' already exists in database!")
            
            if not force_overwrite:
                choice = input("Do you want to (O)verwrite, (S)kip, or (C)ancel? [O/S/C]: ").strip().upper()
                
                if choice == 'C':
                    print("❌ Cancelled by user")
                    return False
                elif choice == 'S':
                    print("⏭️  Skipping ingestion")
                    return True
                elif choice == 'O':
                    delete_document(builder, doc_title)
                else:
                    print("❌ Invalid choice. Cancelling.")
                    return False
            else:
                delete_document(builder, doc_title)
        
        # Ensure indexes exist
        print("\n📊 Checking indexes...")
        builder.create_constraints_and_indexes()
        
        # Ingest the document
        print(f"\n📥 Ingesting document...")
        builder.ingest_document(json_file_path)
        
        print(f"\n✅ Document ingested successfully!")
        
        # Show statistics for this document
        with builder.driver.session() as session:
            if doc_title:
                stats_query = """
                MATCH (d:Document {title: $title})-[:CONTAINS]->(a:Article)
                OPTIONAL MATCH (a)-[:CONTAINS]->(c:Clause)
                OPTIONAL MATCH (c)-[:CONTAINS]->(s:SubClause)
                RETURN count(DISTINCT a) as articles,
                       count(DISTINCT c) as clauses,
                       count(DISTINCT s) as subclauses
                """
                result = session.run(stats_query, title=doc_title)
                stats = result.single()
                
                print("\n📊 Document Statistics:")
                print(f"   📄 Document: {doc_title}")
                print(f"   📰 Articles: {stats['articles']}")
                print(f"   📝 Clauses: {stats['clauses']}")
                print(f"   📋 Sub-clauses: {stats['subclauses']}")
        
        # Ask about similarity and citation relationships
        print("\n" + "=" * 70)
        print("Additional Processing Options")
        print("=" * 70)
        print("Would you like to:")
        print("  1. Create similarity relationships for this document")
        print("  2. Build citation network for this document")
        print("  3. Both (1 & 2)")
        print("  4. Skip")
        
        choice = input("\nEnter choice (1-4) [default: 4]: ").strip() or "4"
        
        if choice in ["1", "3"]:
            print("\n🔗 Creating similarity relationships...")
            builder.create_similarity_relationships(threshold=0.7)
            print("✅ Similarity relationships created")
        
        if choice in ["2", "3"]:
            print("\n🔗 Building citation network...")
            builder.build_citation_network()
            print("✅ Citation network built")
        
        print("\n" + "=" * 70)
        print("✅ Single File Ingestion Complete!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during ingestion: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        builder.close()
        print("\n🔌 Database connection closed.")

def interactive_mode():
    """
    Interactive mode for selecting and ingesting files
    """
    print("\n" + "=" * 70)
    print("Interactive Mode - Single File Ingestion")
    print("=" * 70)
    
    # Common data directories to search
    data_dirs = [
        Path("../../data/jsons"),
        Path("./data/jsons"),
        Path("../data/jsons"),
    ]
    
    json_files = []
    for data_dir in data_dirs:
        if data_dir.exists():
            json_files = list(data_dir.glob("*.json"))
            if json_files:
                print(f"\n📁 Found {len(json_files)} JSON files in {data_dir}")
                break
    
    if not json_files:
        print("\n❌ No JSON files found in common data directories.")
        file_path = input("Enter the full path to your JSON file: ").strip()
        if file_path:
            ingest_single_file(file_path)
        return
    
    # Display files
    print("\nAvailable files:")
    for i, file in enumerate(json_files, 1):
        print(f"  {i}. {file.name}")
    
    # Get user selection
    try:
        choice = input(f"\nSelect file number (1-{len(json_files)}) or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            print("Exiting...")
            return
        
        file_index = int(choice) - 1
        if 0 <= file_index < len(json_files):
            selected_file = json_files[file_index]
            ingest_single_file(str(selected_file))
        else:
            print("❌ Invalid selection")
            
    except ValueError:
        print("❌ Invalid input")
    except KeyboardInterrupt:
        print("\n\nCancelled by user")

def main():
    parser = argparse.ArgumentParser(
        description="Ingest a single legal document JSON file into Neo4j database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest specific file
  python ingest_single_file.py ../../data/legal_data/constitution_1973.json
  
  # Ingest with force overwrite (no prompts)
  python ingest_single_file.py constitution.json --force
  
  # Interactive mode
  python ingest_single_file.py --interactive
        """
    )
    
    parser.add_argument(
        'json_file',
        nargs='?',
        help='Path to the JSON file to ingest'
    )
    
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode to select file'
    )
    
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Force overwrite without prompting if document exists'
    )
    
    args = parser.parse_args()
    
    # Check if interactive mode
    if args.interactive:
        interactive_mode()
    elif args.json_file:
        ingest_single_file(args.json_file, force_overwrite=args.force)
    else:
        parser.print_help()
        print("\n❌ Error: Please provide a JSON file path or use --interactive mode")
        sys.exit(1)

if __name__ == "__main__":
    main()
