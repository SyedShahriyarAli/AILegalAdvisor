"""
Court Case Ingestion System
Ingests court judgments from all courts and links them to statutory provisions.

Supports:
  - LHC  (lahore-high-court-cyber-cases.json)        {"judgments": [...]}
  - IHC  (islamabad-high-court-cyber-cases.json)     [...]  bare array
  - PHC  (peshawar-high-court-cyber-cases.json)      [...]  bare array
  - SHC  (sindh-high-court-cyber-cases-*.json)       [...]  bare array

Usage:
  python ingest_cases.py                          # scans cyber_cases/, deletes old cases first
  python ingest_cases.py --keep-cases             # add to existing cases instead of wiping
  python ingest_cases.py --dir path/to/jsons      # custom directory
  python ingest_cases.py --file path/to/file.json --court "Lahore High Court"
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Add backend dir to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.graph_rag.legal_graph_builder import LegalGraphBuilder
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Court detection from filename
# ---------------------------------------------------------------------------

_COURT_MAP = {
    "lhc": "Lahore High Court",
    "ihc": "Islamabad High Court",
    "phc": "Peshawar High Court",
    "shc": "Sindh High Court",
}

def _detect_court(filename: str) -> str:
    stem = Path(filename).stem.lower()
    for prefix, name in _COURT_MAP.items():
        if stem.startswith(prefix):
            return name
    # Support descriptive filenames like lahore-high-court-cyber-cases.json
    if "lahore-high-court" in stem:
        return "Lahore High Court"
    if "islamabad-high-court" in stem:
        return "Islamabad High Court"
    if "peshawar-high-court" in stem:
        return "Peshawar High Court"
    if "sindh-high-court" in stem:
        return "Sindh High Court"
    return "Unknown Court"


# ---------------------------------------------------------------------------
# Per-court field normalizers → common dict
# ---------------------------------------------------------------------------

def _make_id(raw: str) -> str:
    """Sanitise a string into a safe node ID."""
    return re.sub(r'[^A-Za-z0-9_\-]', '_', raw.strip())[:120]


def _norm_lhc(case: Dict) -> Dict:
    title       = (case.get('case_title') or '').strip()
    case_no     = (case.get('writ_petition') or case.get('case_number') or '').strip()
    date        = (case.get('date_of_judgment') or case.get('order_date') or '').strip()
    judge       = (case.get('hon_judge') or case.get('judges') or '').strip()
    citation    = (case.get('lhc_citation') or '').strip()
    pdf         = (case.get('pdf_link') or '').strip()
    summary     = (case.get('matter') or '').strip()
    sr          = (case.get('sr_no') or '').strip()
    pdf_data    = (case.get('pdf_data') or '').strip()
    winner      = (case.get('winner') or '').strip() or None

    cyber_reason   = case.get('cyber_law_reason')
    cyber_match    = case.get('cyber_law_match') or {}
    cyber_profile  = cyber_match.get('filter_profile')
    cyber_triggers = json.dumps(cyber_match.get('triggers')) if cyber_match.get('triggers') else None
    cyber_keywords = [t.get('matched', '') for t in cyber_match.get('triggers', []) if isinstance(t, dict)]

    raw_id = citation or f"LHC_{case_no or sr or title[:40]}"
    return dict(
        case_id=_make_id(raw_id), citation=citation, title=title,
        case_no=case_no, date=date, judge=judge, pdf_link=pdf,
        summary=summary or f"{title}. {case_no}".strip('. '),
        discussed_laws='', cyber_keywords=cyber_keywords,
        cyber_law_reason=cyber_reason, cyber_law_filter_profile=cyber_profile,
        cyber_law_triggers_json=cyber_triggers, pdf_data=pdf_data,
        winner=winner,
    )


def _norm_ihc(case: Dict) -> Dict:
    title    = (case.get('case_title') or '').strip()
    case_no  = (case.get('case_no') or '').strip()
    date     = (case.get('order_date') or '').strip()
    judge    = (case.get('before') or case.get('author') or '').strip()
    pdf      = (case.get('download_link') or case.get('judgment_link') or '').strip()
    desc     = (case.get('description') or '').strip()
    laws     = (case.get('discussed_laws') or '').strip()
    s_no     = (case.get('s_no') or '').strip()
    pdf_data = (case.get('pdf_data') or '').strip()
    winner   = (case.get('winner') or '').strip() or None

    raw_id = f"IHC_{case_no or s_no or title[:40]}"
    return dict(
        case_id=_make_id(raw_id), citation='', title=title,
        case_no=case_no, date=date, judge=judge, pdf_link=pdf,
        summary=f"{desc} {laws}".strip() or title,
        discussed_laws=laws, cyber_keywords=[],
        cyber_law_reason=None, cyber_law_filter_profile=None,
        cyber_law_triggers_json=None, pdf_data=pdf_data,
        winner=winner,
    )


def _norm_phc(case: Dict) -> Dict:
    title    = (case.get('case_title') or '').strip()
    date     = (case.get('decision_date') or '').strip()
    pdf      = (case.get('judgment_link') or '').strip()
    remarks  = (case.get('remarks') or '').strip()
    neutral  = (case.get('phc_neutral_citation') or '').strip()
    other    = (case.get('other_citation') or '').strip()
    citation = neutral or other or ''
    s_no     = (case.get('s_no') or '').strip()
    pdf_data = (case.get('pdf_data') or '').strip()
    winner   = (case.get('winner') or '').strip() or None

    raw_id = f"PHC_{neutral or other or s_no or title[:40]}"
    return dict(
        case_id=_make_id(raw_id), citation=citation, title=title,
        case_no='', date=date, judge='', pdf_link=pdf,
        summary=remarks[:500] if remarks else title,
        discussed_laws='', cyber_keywords=[],
        cyber_law_reason=None, cyber_law_filter_profile=None,
        cyber_law_triggers_json=None, pdf_data=pdf_data,
        winner=winner,
    )


def _norm_shc(case: Dict) -> Dict:
    parties   = (case.get('parties') or '').strip()
    case_no   = (case.get('case_no') or '').strip()
    date      = (case.get('date') or '').strip()
    citation  = (case.get('citation') or '').strip()
    pdf       = (case.get('pdf_link') or '').strip()
    excerpt   = (case.get('excerpt') or '').strip()
    keywords  = case.get('cyber_keywords_matched') or []
    record_id = (case.get('record_id') or '').strip()
    sr_no     = (case.get('sr_no') or '').strip()
    pdf_data  = (case.get('pdf_data') or '').strip()
    winner    = (case.get('winner') or '').strip() or None

    raw_id = f"SHC_{record_id or citation or case_no or sr_no}"
    return dict(
        case_id=_make_id(raw_id), citation=citation, title=parties,
        case_no=case_no, date=date, judge='', pdf_link=pdf,
        summary=excerpt[:500] if excerpt else parties,
        discussed_laws='', cyber_keywords=keywords if isinstance(keywords, list) else [],
        cyber_law_reason=None, cyber_law_filter_profile=None,
        cyber_law_triggers_json=None, pdf_data=pdf_data,
        winner=winner,
    )


_NORMALIZERS = {
    "Lahore High Court":     _norm_lhc,
    "Islamabad High Court":  _norm_ihc,
    "Peshawar High Court":   _norm_phc,
    "Sindh High Court":      _norm_shc,
}


# ---------------------------------------------------------------------------
# Module-level multiprocessing function (must be top-level for pickle)
# ---------------------------------------------------------------------------

def compute_case_similarities_batch(args):
    case_ids, embeddings_dict, threshold, start_idx, end_idx = args
    results = []
    n = len(case_ids)
    for i in range(start_idx, min(end_idx, n)):
        id1  = case_ids[i]
        emb1 = embeddings_dict[id1]
        norm1 = np.linalg.norm(emb1)
        for j in range(i + 1, n):
            id2  = case_ids[j]
            emb2 = embeddings_dict[id2]
            sim  = float(np.dot(emb1, emb2) / (norm1 * np.linalg.norm(emb2)))
            if sim >= threshold:
                results.append((id1, id2, sim))
    return results


# ---------------------------------------------------------------------------
# Main ingester class
# ---------------------------------------------------------------------------

class CourtCaseIngester:

    def __init__(self, builder: LegalGraphBuilder):
        self.builder = builder
        self.citation_patterns = [
            r'\bSection\s+(\d+[A-Z]*)\b',
            r'\bSec\.\s+(\d+[A-Z]*)\b',
            r'\bS\.\s+(\d+[A-Z]*)\b',
            r'\bArticle\s+(\d+[A-Z]*)\b',
            r'\bArt\.\s+(\d+[A-Z]*)\b',
            r'\b(\d+)\s+PPC\b',
            r'\bPPC\s+(\d+)\b',
            r'\b(\d+)\s+Cr\.?P\.?C\.?\b',
            r'\bCr\.?P\.?C\.?\s+(\d+)\b',
            r'\bPECA\s+(\d+[A-Z]*)\b',
        ]

    # ------------------------------------------------------------------
    def create_case_schema(self):
        print("\n" + "="*70)
        print("Creating Court Case Schema")
        print("="*70)

        with self.builder.driver.session() as session:
            # Drop any stale uniqueness constraint on Case.citation.
            # The constraint name varies by Neo4j version so we inspect the schema.
            try:
                rows = list(session.run(
                    "SHOW CONSTRAINTS YIELD name, labelsOrTypes, properties, type "
                    "WHERE 'Case' IN labelsOrTypes "
                    "  AND 'citation' IN properties "
                    "  AND type = 'UNIQUENESS'"
                ))
                for row in rows:
                    cname = row['name']
                    session.run(f"DROP CONSTRAINT {cname} IF EXISTS")
                    print(f"  [DROPPED] Stale constraint: {cname}")
            except Exception as e:
                print(f"  [SKIP] Could not inspect constraints: {e}")

            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE",
            ]
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.date)",
                "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.court)",
                "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.citation)",
                "CREATE FULLTEXT INDEX case_title IF NOT EXISTS FOR (c:Case) ON EACH [c.title, c.summary]",
                """CREATE VECTOR INDEX case_embeddings IF NOT EXISTS FOR (c:Case) ON (c.embedding)
                    OPTIONS {
                        indexConfig: {
                        `vector.dimensions`: 384,
                        `vector.similarity_function`: 'cosine'
                        }
                    }""",
            ]
            for q in constraints + indexes:
                try:
                    session.run(q)
                    print(f"  [OK] {q[:60]}...")
                except Exception as e:
                    print(f"  [EXISTS] {str(e)[:60]}")

        print("[SUCCESS] Schema ready\n")

    # ------------------------------------------------------------------
    def extract_citations(self, text: str) -> List[str]:
        citations = set()
        if not text:
            return []
        for pattern in self.citation_patterns:
            for m in re.finditer(pattern, text[:10000], re.IGNORECASE):
                citations.add(m.group(1) if m.lastindex else m.group(0))
        return list(citations)[:25]

    # ------------------------------------------------------------------
    def _load_cases(self, json_file: str) -> List[Dict]:
        """Load cases from file, handling both bare-array and wrapped formats."""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Try common wrapper keys
            for key in ('judgments', 'cases', 'data', 'results'):
                if key in data and isinstance(data[key], list):
                    return data[key]
        raise ValueError(f"Unrecognised JSON structure in {json_file}: "
                         f"expected array or {{\"judgments\": [...]}}")

    # ------------------------------------------------------------------
    def ingest_case(self, norm: Dict, court: str) -> bool:
        """Ingest a single normalised case record."""
        try:
            case_id  = norm['case_id']
            if not case_id.strip('_'):
                case_id = f"case_{abs(hash(norm['title'] + norm['case_no'])) % 10**10}"

            pdf_data = norm.get('pdf_data') or ''
            has_pdf  = bool(pdf_data) and not pdf_data.startswith('[ERROR')

            # Use full PDF text for embedding when available; fall back to summary
            embedding_text = (
                f"{norm['title']} {pdf_data[:3000]}"
                if has_pdf
                else f"{norm['title']} {norm['summary']}"
            )
            embedding = self.builder.generate_embedding(embedding_text)

            cyber_keywords_json = (
                json.dumps(norm['cyber_keywords']) if norm['cyber_keywords'] else None
            )

            with self.builder.driver.session() as session:
                session.run("""
                    MERGE (c:Case {id: $case_id})
                    SET c.citation                  = $citation,
                        c.title                     = $title,
                        c.case_no                   = $case_no,
                        c.date                      = $date,
                        c.judge                     = $judge,
                        c.court                     = $court,
                        c.pdf_link                  = $pdf_link,
                        c.summary                   = $summary,
                        c.pdf_data                  = $pdf_data,
                        c.discussed_laws            = $discussed_laws,
                        c.cyber_keywords_json       = $cyber_keywords_json,
                        c.cyber_law_reason          = $cyber_law_reason,
                        c.cyber_law_filter_profile  = $cyber_law_filter_profile,
                        c.cyber_law_triggers_json   = $cyber_law_triggers_json,
                        c.embedding                 = $embedding,
                        c.ingested_at               = datetime(),
                        c.winner                    = $winner
                """,
                    case_id=case_id, citation=norm['citation'],
                    title=norm['title'], case_no=norm['case_no'],
                    date=norm['date'], judge=norm['judge'], court=court,
                    pdf_link=norm['pdf_link'], summary=norm['summary'],
                    pdf_data=pdf_data if has_pdf else None,
                    discussed_laws=norm['discussed_laws'],
                    cyber_keywords_json=cyber_keywords_json,
                    cyber_law_reason=norm['cyber_law_reason'],
                    cyber_law_filter_profile=norm['cyber_law_filter_profile'],
                    cyber_law_triggers_json=norm['cyber_law_triggers_json'],
                    embedding=embedding,
                    winner=norm.get('winner'),
                )

                # Citation extraction: prefer full PDF text over short summary
                citation_text = " ".join(filter(None, [
                    norm['title'], norm['case_no'],
                    pdf_data[:5000] if has_pdf else norm['summary'],
                    norm['discussed_laws'],
                ]))
                cited = self.extract_citations(citation_text)
                if cited:
                    session.run("""
                        UNWIND $provisions as prov
                        OPTIONAL MATCH (a:Article)
                        WHERE a.article_number = prov
                           OR a.article_number CONTAINS prov
                        WITH prov, collect(a)[0] AS a
                        WHERE a IS NOT NULL
                        MATCH (c:Case {id: $case_id})
                        MERGE (c)-[r:CITES]->(a)
                        SET r.provision = prov, r.source = 'extracted'
                    """, provisions=cited, case_id=case_id)

            return True

        except Exception as e:
            print(f"  [WARN] Error ingesting case '{norm.get('title','?')[:50]}': {e}")
            return False

    # ------------------------------------------------------------------
    def ingest_from_file(self, json_file: str, court: str) -> Tuple[int, int]:
        print(f"\n{'='*70}")
        print(f"File  : {json_file}")
        print(f"Court : {court}")
        print(f"{'='*70}")

        normalizer = _NORMALIZERS.get(court)
        if normalizer is None:
            print(f"  [WARN] No normalizer for court '{court}'. Using generic LHC normalizer.")
            normalizer = _norm_lhc

        try:
            raw_cases = self._load_cases(json_file)
        except Exception as e:
            print(f"  [ERROR] Failed to load file: {e}")
            return 0, 0

        total = len(raw_cases)
        print(f"Found {total} cases\n")

        success, errors = 0, 0
        for i, raw in enumerate(raw_cases, 1):
            if i % 100 == 0:
                print(f"  Progress: {i}/{total} ({i/total*100:.1f}%)")
            try:
                norm = normalizer(raw)
            except Exception as e:
                print(f"  [WARN] Normalisation error (row {i}): {e}")
                errors += 1
                continue

            if self.ingest_case(norm, court):
                success += 1
            else:
                errors += 1

        print(f"\n  [DONE] Success: {success}/{total}  Errors: {errors}")
        return success, errors

    # ------------------------------------------------------------------
    def create_case_similarity_relationships(self, threshold: float = 0.7,
                                              batch_size: int = 1000):
        from multiprocessing import Pool, cpu_count
        import time

        print(f"\n{'='*70}\nCreating Case Similarity Relationships\n{'='*70}")
        start = time.time()

        with self.builder.driver.session() as session:
            rows = list(session.run(
                "MATCH (c:Case) WHERE c.embedding IS NOT NULL "
                "RETURN c.id as id, c.embedding as embedding"
            ))

        total = len(rows)
        if total < 2:
            print("Need at least 2 cases.")
            return

        print(f"Processing {total} cases  ({total*(total-1)//2:,} pairs)...")
        case_ids   = [r['id'] for r in rows]
        embeddings = {r['id']: np.array(r['embedding']) for r in rows}

        num_workers = min(cpu_count(), 8)
        chunk = max(1, total // num_workers)
        work  = [
            (case_ids, embeddings, threshold, i, min(i + chunk, total))
            for i in range(0, total, chunk)
        ]

        all_sims = []
        if num_workers > 1 and len(work) > 1:
            with Pool(processes=num_workers) as pool:
                for result in pool.map(compute_case_similarities_batch, work):
                    all_sims.extend(result)
        else:
            all_sims = compute_case_similarities_batch(work[0])

        print(f"Found {len(all_sims):,} similar pairs above threshold {threshold}")
        if not all_sims:
            return

        with self.builder.driver.session() as session:
            for i in range(0, len(all_sims), batch_size):
                batch = all_sims[i:i + batch_size]
                session.run("""
                    UNWIND $rels as rel
                    MATCH (c1:Case {id: rel.id1})
                    MATCH (c2:Case {id: rel.id2})
                    MERGE (c1)-[r:SIMILAR_TO]-(c2)
                    SET r.score = rel.similarity
                """, rels=[{'id1': a, 'id2': b, 'similarity': s} for a, b, s in batch])

        print(f"[DONE] Created {len(all_sims):,} similarity relationships in {time.time()-start:.1f}s")

    # ------------------------------------------------------------------
    def link_cases_to_articles_advanced(self):
        """Extra pass: link cases via title+summary that weren't caught during ingest."""
        print(f"\n{'='*70}\nAdvanced Case-to-Article Linking\n{'='*70}")

        with self.builder.driver.session() as session:
            cases = list(session.run(
                "MATCH (c:Case) RETURN c.id as id, c.title as title, "
                "c.case_no as case_no, c.summary as summary, "
                "c.discussed_laws as discussed_laws"
            ))
            print(f"Scanning {len(cases)} cases for additional citations...")

            new_links = 0
            for i, c in enumerate(cases):
                if i % 200 == 0 and i:
                    print(f"  {i}/{len(cases)} done...")

                text = " ".join(filter(None, [
                    c['title'], c['case_no'], c['summary'], c['discussed_laws']
                ]))
                citations = self.extract_citations(text)
                if not citations:
                    continue

                result = session.run("""
                    UNWIND $provisions as prov
                    OPTIONAL MATCH (a:Article)
                    WHERE a.article_number = prov
                       OR a.article_number CONTAINS prov
                    WITH prov, collect(a)[0] AS a
                    WHERE a IS NOT NULL
                    MATCH (cas:Case {id: $case_id})
                    WHERE NOT (cas)-[:CITES]->(a)
                    MERGE (cas)-[r:CITES]->(a)
                    SET r.provision = prov, r.source = 'advanced'
                    RETURN count(r) as cnt
                """, provisions=citations, case_id=c['id'])
                row = result.single()
                if row:
                    new_links += row['cnt']

        print(f"[DONE] Created {new_links} additional case-to-article links")


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingest court cases into Neo4j")
    src = parser.add_mutually_exclusive_group()
    src.add_argument(
        "--dir", type=Path,
        default=None,
        help="Directory of case JSON files",
    )
    src.add_argument(
        "--file", type=Path,
        default=None,
        help="Single JSON file to ingest",
    )
    parser.add_argument(
        "--court",
        type=str,
        default=None,
        help="Court name override when using --file",
    )
    parser.add_argument(
        "--keep-cases",
        action="store_true",
        help="Keep existing Case nodes instead of wiping them",
    )
    parser.add_argument(
        "--skip-similarities",
        action="store_true",
        help="Skip case similarity computation",
    )
    args = parser.parse_args()

    # Resolve target files
    if args.file:
        json_files = [args.file]
    else:
        cases_dir = args.dir or (
            Path(__file__).resolve().parent.parent.parent
            / "data" / "jsons" / "cyber_cases"
        )
        if not cases_dir.is_dir():
            print(f"[ERROR] Directory not found: {cases_dir}")
            sys.exit(1)
        json_files = sorted(cases_dir.glob("*.json"))
        if not json_files:
            print(f"[ERROR] No JSON files found in {cases_dir}")
            sys.exit(1)

    print("\n" + "="*70)
    print("COURT CASE INGESTION")
    print("="*70)
    print(f"Files to process: {len(json_files)}")
    for f in json_files:
        print(f"  - {f.name}")

    builder  = LegalGraphBuilder(
        uri=os.getenv('NEO4J_URI'),
        username=os.getenv('NEO4J_USER'),
        password=os.getenv('NEO4J_PASSWORD'),
    )
    ingester = CourtCaseIngester(builder)

    try:
        ingester.create_case_schema()

        if not args.keep_cases:
            print("\n[REPLACE] Removing existing Case nodes...")
            with builder.driver.session() as session:
                deleted = session.run(
                    "MATCH (c:Case) DETACH DELETE c RETURN count(*) as n"
                ).single()
                n = deleted['n'] if deleted else 0
            print(f"[REPLACE] Deleted {n} existing Case nodes. Use --keep-cases to skip.")

        total_success, total_errors = 0, 0

        for json_file in json_files:
            court = args.court or _detect_court(str(json_file))
            ok, err = ingester.ingest_from_file(str(json_file), court)
            total_success += ok
            total_errors  += err

        print(f"\n[GRAND TOTAL] OK: {total_success}  Errors: {total_errors}")

        # Advanced linking
        ingester.link_cases_to_articles_advanced()

        # Similarity relationships
        if args.skip_similarities:
            print("\n[SKIP] Skipping similarity relationships (--skip-similarities)")
        else:
            print("\nCase similarity helps find related precedents.")
            resp = input("Create case similarity relationships? (y/n) [y]: ").strip().lower()
            if resp != 'n':
                ingester.create_case_similarity_relationships(threshold=0.7)
            else:
                print("Skipping -- run again without --skip-similarities to add later.")

        print("\n" + "="*70)
        print("[DONE] CASE INGESTION COMPLETE")
        print("="*70)
        with builder.driver.session() as session:
            cases    = session.run("MATCH (c:Case) RETURN count(c) as n").single()['n']
            articles = session.run("MATCH (a:Article) RETURN count(a) as n").single()['n']
            links    = session.run("MATCH (:Case)-[:CITES]->(:Article) RETURN count(*) as n").single()['n']
            sims     = session.run("MATCH (:Case)-[:SIMILAR_TO]-(:Case) RETURN count(*) as n").single()['n']

        print(f"\n   Court Cases:          {cases}")
        print(f"   Statutory Articles:   {articles}")
        print(f"   Case->Article Links:  {links}")
        print(f"   Case Similarities:    {sims}")
        print(f"   Avg Links/Case:       {links/cases if cases else 0:.1f}")

    except Exception as e:
        import traceback
        print(f"\n[FATAL ERROR] {e}")
        traceback.print_exc()
    finally:
        builder.close()
        print("\n[DONE] Connection closed.")


if __name__ == "__main__":
    main()
