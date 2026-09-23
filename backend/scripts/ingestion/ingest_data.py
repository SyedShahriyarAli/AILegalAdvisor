"""
Complete Legal Data Ingestion Script
This script:
1. Creates constraints and indexes
2. Ingests all legal documents from file_paths.json
3. Creates similarity relationships between articles  (uses optimized sub-script)
4. Builds citation network / CITES relationships      (uses optimized sub-script)
5. Optionally updates concept relationships with enhanced extraction
"""

import sys
import os
import subprocess
import traceback
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

import json
from app.graph_rag.legal_graph_builder import LegalGraphBuilder
from dotenv import load_dotenv

load_dotenv()

# Resolve paths relative to THIS file so the script can be run from anywhere
_THIS_DIR = Path(__file__).resolve().parent
_FILE_PATHS_JSON = _THIS_DIR / "file_paths.json"
_SUB_SCRIPTS_DIR = _THIS_DIR / "sub_scripts"


def _run_sub_script(script_name: str, extra_args: list = None):
    """Run a sub-script in a subprocess, inheriting the current environment."""
    script_path = _SUB_SCRIPTS_DIR / script_name
    cmd = [sys.executable, str(script_path)] + (extra_args or [])
    print(f"  ▶ Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=os.environ.copy())
    if result.returncode != 0:
        print(f"  ⚠️  Sub-script exited with code {result.returncode}")
    return result.returncode == 0


def update_concepts(builder, update_existing=False):
    """
    Update concept relationships for existing articles.

    Args:
        builder: LegalGraphBuilder instance
        update_existing: If True, removes old concepts and creates new ones
                        If False, only adds new concepts (keeps old ones)
    """
    print("\n" + "=" * 60)
    print("Step 5: Updating Enhanced Concept Relationships")
    print("=" * 60)
    
    with builder.driver.session() as session:
        # Get all articles
        query = "MATCH (a:Article) WHERE a.content IS NOT NULL RETURN a.id as id, a.content as content"
        articles = list(session.run(query))
        
        print(f"Processing {len(articles)} articles...")
        
        updated_count = 0
        for i, article in enumerate(articles, 1):
            if i % 10 == 0:
                print(f"  Processed {i}/{len(articles)} articles...")
            
            concepts = builder.extract_concepts(article['content'])
            
            if update_existing:
                session.run("""
                    MATCH (a:Article {id: $article_id})-[r:RELATES_TO]->(:Concept)
                    DELETE r
                """, article_id=article['id'])
            
            # Batched: single round-trip per article rather than one per concept.
            if concepts:
                session.run(
                    """
                    MATCH (a:Article {id: $article_id})
                    UNWIND $concepts AS concept_name
                    MERGE (c:Concept {name: concept_name})
                    MERGE (a)-[:RELATES_TO]->(c)
                    """,
                    article_id=article['id'],
                    concepts=concepts,
                )

            updated_count += 1
        
        print(f"\n✓ Updated concepts for {updated_count} articles")
        
        # Show statistics
        result = session.run("MATCH (:Article)-[:RELATES_TO]->(c:Concept) RETURN count(DISTINCT c) as concept_count")
        concept_count = result.single()['concept_count']
        print(f"✓ Total unique concepts: {concept_count}")

def main():
    print("\n" + "=" * 60)
    print("Legal AI Advisor - Complete Data Ingestion Pipeline")
    print("=" * 60)
    
    builder = LegalGraphBuilder(
        uri=os.getenv('NEO4J_URI'),
        username=os.getenv('NEO4J_USER'),
        password=os.getenv('NEO4J_PASSWORD')
    )
    
    json_files = []
    # Track user concept choice so the final summary block can reference it
    # safely even if earlier steps fail.
    concept_choice = "1"

    try:
        # Step 1: Create constraints and indexes
        print("\n" + "=" * 60)
        print("Step 1: Creating Constraints and Indexes")
        print("=" * 60)
        builder.create_constraints_and_indexes()
        
        # Step 2: Ingest documents
        print("\n" + "=" * 60)
        print("Step 2: Ingesting Documents")
        print("=" * 60)

        if not _FILE_PATHS_JSON.exists():
            raise FileNotFoundError(
                f"file_paths.json not found at {_FILE_PATHS_JSON}. "
                "Make sure it exists next to ingest_data.py."
            )

        with open(_FILE_PATHS_JSON, 'r', encoding='utf-8') as file:
            json_files = json.load(file)
        
        success_count = 0
        error_count = 0
        
        for json_file in json_files:
            try:
                print(f"\n📄 Processing: {json_file}")
                builder.ingest_document(json_file)
                success_count += 1
                print(f"✅ Success")
            except Exception as e:
                error_count += 1
                print(f"❌ Error processing {json_file}: {type(e).__name__}: {str(e)}")
                # Print the full traceback so we can pinpoint which library /
                # call is raising (e.g. neo4j driver buffer, sentence-transformers,
                # spaCy, etc.). Swallowing the traceback hides the root cause.
                traceback.print_exc()
                continue
        
        print(f"\n📊 Ingestion Summary:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Failed: {error_count}")
        print(f"   📁 Total: {len(json_files)}")
        
        if success_count == 0:
            print("\n❌ No documents ingested successfully. Skipping remaining steps.")
            return
        
        # Step 3: Create similarity relationships (optimized sub-script)
        print("\n" + "=" * 60)
        print("Step 3: Creating Similarity Relationships (Optimized)")
        print("=" * 60)
        print("Delegating to create_similarities.py (parallel numpy computation)...")
        # Pass --recreate so fresh runs replace any stale data; use --threshold 0.7
        _run_sub_script("create_similarities.py", ["--recreate", "--threshold", "0.7"])
        
        # Step 4: Build citation network (optimized sub-script)
        print("\n" + "=" * 60)
        print("Step 4: Building Citation Network (Optimized)")
        print("=" * 60)
        print("Delegating to create_citations.py (batch + in-memory index)...")
        _run_sub_script("create_citations.py", ["--recreate"])
        
        # Step 5: Optional - Update concepts with enhanced extraction
        print("\n" + "=" * 60)
        print("Enhanced Concept Extraction (Optional)")
        print("=" * 60)
        print("This step uses NLP (spaCy) + 200+ legal terms for better concept extraction.")
        print("Options:")
        print("  1. Skip (keep basic concepts from ingestion)")
        print("  2. Add enhanced concepts (keeps existing + adds new)")
        print("  3. Replace all concepts (removes old + creates new)")
        
        concept_choice = input("\nEnter choice (1-3) [default: 2]: ").strip() or "2"
        
        if concept_choice in ["2", "3"]:
            update_existing = (concept_choice == "3")
            update_concepts(builder, update_existing=update_existing)
        else:
            print("Skipping enhanced concept extraction.")
        
        # Final summary
        print("\n" + "=" * 60)
        print("✅ Complete Ingestion Pipeline Finished Successfully!")
        print("=" * 60)
        
        with builder.driver.session() as session:
            # Get statistics
            stats = {
                'documents': session.run("MATCH (d:Document) RETURN count(d) as count").single()['count'],
                'articles': session.run("MATCH (a:Article) RETURN count(a) as count").single()['count'],
                'concepts': session.run("MATCH (c:Concept) RETURN count(c) as count").single()['count'],
                'cites': session.run("MATCH ()-[r:CITES]->() RETURN count(r) as count").single()['count'],
                'similar': session.run("MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) as count").single()['count'],
                'related_through': session.run("MATCH ()-[r:RELATED_THROUGH]->() RETURN count(r) as count").single()['count']
            }
            
            print("\n📊 Final Graph Statistics:")
            print(f"   📄 Documents: {stats['documents']}")
            print(f"   📰 Articles: {stats['articles']}")
            print(f"   🏷️  Concepts: {stats['concepts']}")
            print(f"   🔗 Citation Links (CITES): {stats['cites']}")
            print(f"   🔗 Similarity Links: {stats['similar']}")
            print(f"   🔗 Related Through Links: {stats['related_through']}")
            print(f"   📊 Total Relationships: {stats['cites'] + stats['similar'] + stats['related_through']}")
        
        print("\n✨ Your Graph RAG database is now ready for use!")
        print("   - Advanced retrieval features enabled")
        print("   - Citation network built")
        print("   - Similarity relationships created")
        if concept_choice in ["2", "3"]:
            print("   - Enhanced concepts extracted")
        
    except Exception as e:
        print(f"\n❌ Error during ingestion pipeline: {str(e)}")
        # Note: do NOT re-import traceback here. A function-local `import traceback`
        # would shadow the module-level import and cause UnboundLocalError when the
        # earlier per-file `except` block (above) tries to use traceback.print_exc().
        traceback.print_exc()
        
    finally:
        builder.close()
        print("\n🔌 Database connection closed.")

if __name__ == "__main__":
    main()
