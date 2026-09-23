import json
import re
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any
import spacy

# ---------------------------------------------------------------------------
# Document type mapping — derived from known document titles, NOT the first
# word (which was the previous broken behaviour).
# ---------------------------------------------------------------------------
_DOCUMENT_TYPE_MAP = {
    "constitution": "Constitution",
    "penal code": "Penal Code",
    "pakistan penal code": "Penal Code",
    "prevention of electronic crimes": "Cyber Law",
    "electronic transactions ordinance": "Ordinance",
    "telecommunication rules": "Rules",
    "pakistan telecommunication": "Rules",
}

def _derive_doc_type(title: str) -> str:
    """Derive a meaningful document type from a known title mapping."""
    title_lower = title.lower()
    for key, doc_type in _DOCUMENT_TYPE_MAP.items():
        if key in title_lower:
            return doc_type
    # Fallback: first meaningful word
    words = [w for w in title.split() if len(w) > 3]
    return words[0].title() if words else "Unknown"


class LegalGraphBuilder:
    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Warning: spaCy model 'en_core_web_sm' not found. Falling back to basic concept extraction.")
            self.nlp = None
        
    def close(self):
        self.driver.close()
    
    def create_constraints_and_indexes(self):
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.title IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Article) REQUIRE a.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Clause) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:SubClause) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (co:Concept) REQUIRE co.name IS UNIQUE"
            ]
            
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (a:Article) ON (a.article_number)",
                "CREATE INDEX IF NOT EXISTS FOR (a:Article) ON (a.document_title)",
                "CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.year)",
                "CREATE FULLTEXT INDEX article_content IF NOT EXISTS FOR (a:Article) ON EACH [a.content]",
                "CREATE FULLTEXT INDEX clause_content IF NOT EXISTS FOR (c:Clause) ON EACH [c.text]",
                """CREATE VECTOR INDEX article_embeddings IF NOT EXISTS FOR (a:Article) ON (a.embedding)
                    OPTIONS {
                        indexConfig: {
                        `vector.dimensions`: 384,
                        `vector.similarity_function`: 'cosine'
                        }
                    }"""
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"✓ Created constraint")
                except Exception as e:
                    print(f"Constraint already exists or error: {e}")
            
            for index in indexes:
                try:
                    session.run(index)
                    print(f"✓ Created index")
                except Exception as e:
                    print(f"Index already exists or error: {e}")
    
    def extract_concepts(self, text: str) -> List[str]:
        """Enhanced concept extraction using NLP + expanded legal taxonomy.
        
        Priority: taxonomy keyword matches > NER entities > noun phrases.
        Noun phrases are only added if the taxonomy list doesn't already cover
        the concept, and they are filtered to reduce noise.
        """
        taxonomy_matches = set()
        ner_entities = set()
        noun_phrase_candidates = set()

        # --- 1. Taxonomy keyword matching (highest quality) ---
        legal_keywords = self._get_legal_taxonomy()
        text_lower = text.lower()
        for keyword in legal_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                taxonomy_matches.add(keyword)

        if self.nlp:
            doc = self.nlp(text[:100000])  # Limit text length for performance

            # --- 2. NER entities ---
            for ent in doc.ents:
                if ent.label_ in ['LAW', 'ORG', 'GPE', 'EVENT']:
                    ner_entities.add(ent.text.lower().strip())

            # --- 3. Noun phrases (only 2-3 words, filtered to reduce noise) ---
            _STOP_NOUN_PHRASES = {
                'the president', 'any person', 'such order', 'the state',
                'the court', 'any law', 'the government', 'the authority',
                'the act', 'the ordinance', 'the federal government',
                'the provincial government', 'any offence', 'the chairman',
            }
            for chunk in doc.noun_chunks:
                phrase = chunk.text.lower().strip()
                words = phrase.split()
                if 2 <= len(words) <= 3 and phrase not in _STOP_NOUN_PHRASES:
                    noun_phrase_candidates.add(phrase)

        # Merge: taxonomy first, then NER, then filtered noun phrases
        combined = taxonomy_matches | ner_entities
        # Only add noun phrases that bring something new (not already covered by taxonomy)
        combined |= noun_phrase_candidates

        # Filter by length
        filtered = [c for c in combined if 3 <= len(c) <= 50]

        # Rank: taxonomy matches come first, then NER, then noun phrases
        ranked = (
            [c for c in filtered if c in taxonomy_matches] +
            [c for c in filtered if c in ner_entities and c not in taxonomy_matches] +
            [c for c in filtered if c not in taxonomy_matches and c not in ner_entities]
        )

        return ranked[:50]
    
    def _get_legal_taxonomy(self) -> List[str]:
        """Expanded legal taxonomy with 200+ Pakistani legal terms"""
        return [
            # Criminal Procedure
            'jurisdiction', 'bail', 'custody', 'warrant', 'summon', 'trial',
            'prosecution', 'defence', 'evidence', 'witness', 'accused', 'court',
            'anticipatory bail', 'bail before arrest', 'pre-arrest bail',
            'cognizable offense', 'non-cognizable offense', 'bailable offense',
            'non-bailable offense', 'first information report', 'fir',
            
            # Court & Judicial System
            'judge', 'magistrate', 'high court', 'supreme court', 'session court',
            'district court', 'civil court', 'criminal court', 'appellate court',
            'tribunal', 'commission', 'inquiry', 'investigation',
            
            # Legal Procedures
            'punishment', 'sentence', 'appeal', 'revision', 'review',
            'acquittal', 'conviction', 'complaint', 'investigation', 'arrest',
            'detention', 'remand', 'charge', 'judgement', 'decree', 'order',
            'notification', 'ordinance', 'amendment', 'repeal',
            
            # Criminal Law
            'murder', 'culpable homicide', 'qatl', 'hurt', 'grievous hurt',
            'theft', 'robbery', 'dacoity', 'extortion', 'kidnapping',
            'abduction', 'rape', 'assault', 'criminal breach of trust',
            'cheating', 'forgery', 'defamation', 'mischief', 'trespass',
            'rioting', 'unlawful assembly', 'terrorism', 'conspiracy',
            
            # Evidence & Proof
            'burden of proof', 'standard of proof', 'admissible evidence',
            'circumstantial evidence', 'documentary evidence', 'oral evidence',
            'expert testimony', 'dying declaration', 'confession',
            'admission', 'presumption', 'corroboration',
            
            # Rights & Freedoms
            'fundamental rights', 'human rights', 'right to life',
            'right to liberty', 'freedom of speech', 'freedom of assembly',
            'right to property', 'due process', 'fair trial', 'natural justice',
            
            # Civil Law
            'contract', 'agreement', 'breach', 'damages', 'specific performance',
            'injunction', 'tort', 'negligence', 'liability', 'compensation',
            'restitution', 'rescission', 'void', 'voidable', 'consideration',
            'offer', 'acceptance', 'capacity', 'consent', 'fraud', 'misrepresentation',
            
            # Property Law
            'property', 'ownership', 'possession', 'title', 'lease',
            'mortgage', 'easement', 'transfer', 'sale', 'gift',
            'inheritance', 'succession', 'will', 'intestate', 'estate',
            
            # Family Law
            'marriage', 'divorce', 'talaq', 'khula', 'maintenance',
            'custody', 'guardianship', 'adoption', 'legitimacy', 'dower',
            'mehr', 'nikah', 'iddat', 'polygamy',
            
            # Constitutional Law
            'constitution', 'federal', 'provincial', 'parliament',
            'national assembly', 'senate', 'president', 'prime minister',
            'governor', 'chief minister', 'legislation', 'executive',
            'judiciary', 'separation of powers', 'federation',
            
            # Legal Doctrines
            'mens rea', 'actus reus', 'res judicata', 'stare decisis',
            'habeas corpus', 'certiorari', 'mandamus', 'quo warranto',
            'prohibition', 'ultra vires', 'locus standi', 'cause of action',
            
            # Procedural Terms
            'plaintiff', 'defendant', 'petitioner', 'respondent',
            'appellant', 'complainant', 'informant', 'informer',
            'prosecution witness', 'defence witness', 'expert witness',
            'summons', 'subpoena', 'interrogation', 'cross-examination',
            'examination-in-chief', 're-examination', 'deposition',
            
            # Remedies & Relief
            'compensation', 'damages', 'punitive damages', 'exemplary damages',
            'restitution', 'rescission', 'specific performance', 'injunction',
            'declaratory relief', 'stay order', 'interim relief',
            
            # Offenses & Penalties
            'imprisonment', 'fine', 'rigorous imprisonment', 'simple imprisonment',
            'life imprisonment', 'death penalty', 'capital punishment',
            'community service', 'probation', 'parole', 'suspended sentence',
            
            # Pakistani Specific Terms
            'pakistan penal code', 'ppc', 'criminal procedure code', 'crpc',
            'constitution of pakistan', 'qanun-e-shahadat', 'hudood ordinance',
            'anti-terrorism act', 'prevention of corruption act',
            'national accountability bureau', 'nab', 'federal shariat court',

            # Cyber / Telecom (relevant to PECA & ETO)
            'electronic crime', 'cyber crime', 'data protection', 'information system',
            'electronic signature', 'digital evidence', 'unauthorized access',
            'service provider', 'telecommunication', 'internet', 'social media',
        ]
    
    def extract_references(self, text: str) -> List[Dict[str, str]]:
        """Extract legal references with context"""
        patterns = [
            (r'section\s+(\d+[A-Z]*)', 'section'),
            (r'article\s+(\d+[A-Z]*)', 'article'),
            (r'clause\s+\(([a-z0-9]+)\)', 'clause'),
            (r'order\s+([IVXLCDM]+)', 'order')
        ]
        
        references = []
        for pattern, ref_type in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract context around the reference
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                references.append({
                    'reference': match.group(0),
                    'number': match.group(1),
                    'type': ref_type,
                    'context': context
                })
        
        return references
    
    def generate_embedding(self, text: str) -> List[float]:
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()
    
    # -----------------------------------------------------------------------
    # Schema-aware ingestion helpers
    # -----------------------------------------------------------------------

    def _get_articles(self, doc_data: Dict) -> List[Dict]:
        """Return the list of articles/sections regardless of JSON schema variant.

        Supported schemas:
          - {"articles": [{"article_number": ..., "clauses": [...]}]}   (Constitution, PPC)
          - {"sections": [{"section_number": ..., "clauses": [...]}]}   (PECA, ETO, Telecom)
        """
        if 'articles' in doc_data:
            return doc_data['articles']
        if 'sections' in doc_data:
            # Normalise section dicts to use article_number key so the rest of
            # the code can treat them uniformly.
            normalised = []
            for sec in doc_data['sections']:
                normalised.append({
                    'article_number': sec.get('section_number', sec.get('article_number', '')),
                    'title': sec.get('title', ''),
                    'content': sec.get('content', ''),
                    'page_number': sec.get('page_number'),
                    'part': sec.get('part'),
                    'chapter': sec.get('chapter'),
                    'clauses': sec.get('clauses', []),
                })
            return normalised
        return []

    def ingest_document(self, json_file_path: str):
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        doc_data = data['document']
        
        # Extract source file path (PDF) from metadata
        source_file = doc_data.get('source_file', '')
        
        with self.driver.session() as session:
            # Create Document node
            doc_id = self._create_document_node(session, doc_data, source_file)
            print(f"✓ Created document: {doc_data['title']}")
            
            # Process each article — schema-aware
            articles = self._get_articles(doc_data)
            if not articles:
                print(f"  ⚠️  No articles/sections found in {json_file_path}. Check JSON schema.")
            
            for article in articles:
                self._process_article(session, doc_id, article, doc_data['title'])
            
            print(f"✓ Completed ingestion of {doc_data['title']} ({len(articles)} articles/sections)")
    
    def _create_document_node(self, session, doc_data: Dict, source_file: str = "") -> str:
        query = """
        MERGE (d:Document {title: $title})
        SET d.year = $year,
            d.type = $doc_type,
            d.source_file = $source_file,
            d.created_at = datetime()
        RETURN d.title as id
        """
        
        result = session.run(query, 
            title=doc_data['title'],
            year=doc_data.get('year'),
            doc_type=_derive_doc_type(doc_data.get('title', '')),
            source_file=source_file
        )
        return result.single()['id']
    
    def _process_article(self, session, doc_id: str, article: Dict, doc_title: str):
        content = article.get('content', '')
        embedding = self.generate_embedding(content)
        
        concepts = self.extract_concepts(content)
        references = self.extract_references(content)
        
        article_query = """
        MATCH (d:Document {title: $doc_title})
        MERGE (a:Article {id: $article_id})
        SET a.article_number = $article_number,
            a.title = $title,
            a.content = $content,
            a.page_number = $page_number,
            a.part = $part,
            a.chapter = $chapter,
            a.document_title = $doc_title,
            a.embedding = $embedding
        MERGE (d)-[:CONTAINS]->(a)
        RETURN a.id as article_id
        """
        
        article_id = f"{doc_title}:Article:{article['article_number']}"
        
        session.run(article_query,
            doc_title=doc_id,
            article_id=article_id,
            article_number=article['article_number'],
            title=article.get('title', ''),
            content=content,
            page_number=article.get('page_number'),
            part=article.get('part'),
            chapter=article.get('chapter'),
            embedding=embedding
        )
        
        # Batched concept insert: one round-trip per article instead of one per
        # concept. The previous per-concept loop issued ~50 queries/article on
        # the constitution (~15k round-trips total), which makes ingestion
        # against any non-local Neo4j painfully slow and prone to user-cancel
        # (which in turn triggers a follow-on BufferError in the pure-Python
        # neo4j driver during inbox cleanup).
        if concepts:
            session.run(
                """
                MATCH (a:Article {id: $article_id})
                UNWIND $concepts AS concept_name
                MERGE (c:Concept {name: concept_name})
                MERGE (a)-[:RELATES_TO]->(c)
                """,
                article_id=article_id,
                concepts=concepts,
            )

        for clause in article.get('clauses', []):
            self._process_clause(session, article_id, clause)
    
    def _process_clause(self, session, article_id: str, clause: Dict):
        clause_id = f"{article_id}:Clause:{clause['id']}"
        
        clause_query = """
        MATCH (a:Article {id: $article_id})
        MERGE (c:Clause {id: $clause_id})
        SET c.clause_number = $clause_number,
            c.text = $text
        MERGE (a)-[:CONTAINS]->(c)
        """
        
        session.run(clause_query,
            article_id=article_id,
            clause_id=clause_id,
            clause_number=clause['id'],
            text=clause.get('text', '')
        )
        
        # Sub-clauses: the JSON uses nested "clauses" inside a clause object
        # (not "sub_clauses"). Support both key names defensively.
        sub_clauses = clause.get('clauses', clause.get('sub_clauses', []))
        for sub_clause in sub_clauses:
            self._process_sub_clause(session, clause_id, sub_clause)
    
    def _process_sub_clause(self, session, clause_id: str, sub_clause: Dict):
        """Process and create SubClause node"""
        sub_clause_id = f"{clause_id}:SubClause:{sub_clause['id']}"
        
        query = """
        MATCH (c:Clause {id: $clause_id})
        MERGE (sc:SubClause {id: $sub_clause_id})
        SET sc.sub_clause_number = $sub_clause_number,
            sc.text = $text
        MERGE (c)-[:CONTAINS]->(sc)
        """
        
        session.run(query,
            clause_id=clause_id,
            sub_clause_id=sub_clause_id,
            sub_clause_number=sub_clause['id'],
            text=sub_clause.get('text', '')
        )
    
    def create_similarity_relationships(self, threshold: float = 0.7):
        """
        DEPRECATED inline version — kept for backward-compat but calls the
        optimized sub-script logic instead of the old O(n²) DB round-trip loop.

        For full pipeline use, prefer running create_similarities.py directly or
        calling it from ingest_data.py via subprocess.
        """
        with self.driver.session() as session:
            query = "MATCH (a:Article) WHERE a.embedding IS NOT NULL RETURN a.id as id, a.embedding as embedding"
            results = list(session.run(query))
            
            if len(results) < 2:
                print("Need at least 2 articles to create similarities.")
                return

            article_ids = [r['id'] for r in results]
            embeddings = {r['id']: np.array(r['embedding']) for r in results}

            print(f"Computing similarities for {len(article_ids)} articles (in-memory numpy)...")

            similar_pairs = []
            n = len(article_ids)
            for i in range(n):
                emb1 = embeddings[article_ids[i]]
                norm1 = np.linalg.norm(emb1)
                for j in range(i + 1, n):
                    emb2 = embeddings[article_ids[j]]
                    similarity = float(np.dot(emb1, emb2) / (norm1 * np.linalg.norm(emb2)))
                    if similarity >= threshold:
                        similar_pairs.append((article_ids[i], article_ids[j], similarity))

            print(f"Inserting {len(similar_pairs)} similarity relationships...")

            # Batch insert
            batch_size = 1000
            for i in range(0, len(similar_pairs), batch_size):
                batch = similar_pairs[i:i + batch_size]
                batch_data = [{'id1': id1, 'id2': id2, 'similarity': sim} for id1, id2, sim in batch]
                session.run("""
                    UNWIND $relationships as rel
                    MATCH (a1:Article {id: rel.id1})
                    MATCH (a2:Article {id: rel.id2})
                    MERGE (a1)-[r:SIMILAR_TO]->(a2)
                    SET r.similarity = rel.similarity
                """, relationships=batch_data)

            print(f"✓ Created {len(similar_pairs)} similarity relationships")
    
    def build_citation_network(self):
        """Build CITES relationships between articles that reference each other.

        Uses an in-memory lookup index keyed by (document_title, article_number)
        to avoid cross-document citation ambiguity.  Falls back to any-document
        match only when no same-document target exists.
        """
        print("Building citation network...")
        
        with self.driver.session() as session:
            # Fetch all articles with document context
            query = """
            MATCH (d:Document)-[:CONTAINS]->(a:Article)
            RETURN a.id as id,
                   a.content as content,
                   a.article_number as number,
                   a.title as title,
                   d.title as doc_title
            """
            articles = list(session.run(query))

            # Build lookup: (doc_title, number) -> article_id  AND  number -> [article_ids]
            same_doc_lookup: Dict[tuple, str] = {}
            cross_doc_lookup: Dict[str, List[str]] = {}
            for a in articles:
                key = (a['doc_title'], a['number'])
                same_doc_lookup[key] = a['id']
                cross_doc_lookup.setdefault(a['number'], []).append(a['id'])
            
            all_citations = []
            for article in articles:
                if not article['content']:
                    continue
                
                references = self.extract_references(article['content'])
                source_doc = article['doc_title']
                
                for ref in references:
                    ref_number = ref['number']
                    
                    # 1. Same-document match (preferred)
                    target_id = same_doc_lookup.get((source_doc, ref_number))
                    
                    # 2. Cross-document fallback (first match)
                    if not target_id:
                        candidates = cross_doc_lookup.get(ref_number, [])
                        target_id = candidates[0] if candidates else None
                    
                    if target_id and target_id != article['id']:
                        all_citations.append({
                            'source_id': article['id'],
                            'target_id': target_id,
                            'context': ref['context'][:200],
                            'ref_type': ref['type']
                        })

            # Batch insert
            batch_size = 100
            citation_count = 0
            for i in range(0, len(all_citations), batch_size):
                batch = all_citations[i:i + batch_size]
                session.run("""
                    UNWIND $citations as cit
                    MATCH (source:Article {id: cit.source_id})
                    MATCH (target:Article {id: cit.target_id})
                    MERGE (source)-[r:CITES]->(target)
                    SET r.context = cit.context,
                        r.reference_type = cit.ref_type
                """, citations=batch)
                citation_count += len(batch)
            
            print(f"✓ Created {citation_count} citation relationships")
            
            # Create indirect relationships
            print("Creating related-through relationships...")
            session.run("""
            MATCH (a1:Article)-[:CITES]->(common:Article)<-[:CITES]-(a2:Article)
            WHERE a1 <> a2 AND id(a1) < id(a2)
            WITH a1, a2, count(common) as shared_refs
            WHERE shared_refs >= 2
            MERGE (a1)-[r:RELATED_THROUGH]->(a2)
            SET r.shared_citations = shared_refs
            """)
            print("✓ Created related-through relationships")
