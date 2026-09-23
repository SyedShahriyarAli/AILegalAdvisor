from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from datetime import datetime
import uuid
from pathlib import Path
import hashlib
import re
import threading
from io import BytesIO

import pdfplumber
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.graph_rag.legal_graph_rag import LegalGraphRAG
from app.graph_rag.graph import create_legal_graph

load_dotenv()

app = Flask(__name__)
CORS(app)


@app.after_request
def _allow_private_network_access(response):
    """Chromium private-network access preflight expects this on some localhost setups."""
    response.headers.setdefault("Access-Control-Allow-Private-Network", "true")
    return response

rag_system = LegalGraphRAG(
    neo4j_uri=os.getenv('NEO4J_URI'),
    neo4j_user=os.getenv('NEO4J_USER'),
    neo4j_password=os.getenv('NEO4J_PASSWORD'),
    ollama_url=os.getenv('OLLAMA_URL'),
    ollama_model=os.getenv('OLLAMA_MODEL')
)

# Initialize LangGraph directly
print("Initializing LangGraph Workflow...")
legal_graph_app = create_legal_graph()

conversation_history = {}

mongo_client = None
mongo_db = None
mongo_users = None
mongo_sessions = None
mongo_conversations = None
mongo_workspaces = None

mongo_uri = os.getenv("MONGO_URI")
mongo_db_name = os.getenv("MONGO_DB_NAME", "ai_legal_advisor")
if mongo_uri:
    try:
        mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command("ping")
        mongo_db = mongo_client[mongo_db_name]
        mongo_users = mongo_db["users"]
        mongo_sessions = mongo_db["sessions"]
        mongo_conversations = mongo_db["conversations"]
        mongo_workspaces = mongo_db["workspaces"]
        mongo_users.create_index("email", unique=True)
        mongo_sessions.create_index("token", unique=True)
        mongo_conversations.create_index("session_id", unique=True)
        mongo_workspaces.create_index("user_id", unique=True)
        print(f"MongoDB connected ({mongo_db_name})")
    except Exception as mongo_error:
        print(f"⚠️ MongoDB unavailable, falling back to in-memory sessions: {mongo_error}")
        mongo_client = None
        mongo_db = None
        mongo_users = None
        mongo_sessions = None
        mongo_conversations = None
        mongo_workspaces = None


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _save_conversation(session_id: str, payload: dict):
    conversation_history[session_id] = payload.get("history", [])
    if mongo_conversations is None:
        return
    try:
        mongo_conversations.update_one(
            {"session_id": session_id},
            {"$set": payload},
            upsert=True
        )
    except PyMongoError as e:
        print(f"Mongo conversation save failed: {e}")


def _get_conversation(session_id: str):
    if mongo_conversations is not None:
        try:
            doc = mongo_conversations.find_one({"session_id": session_id}, {"_id": 0})
            if doc:
                return doc
        except PyMongoError as e:
            print(f"Mongo conversation fetch failed: {e}")
    return {"session_id": session_id, "history": conversation_history.get(session_id, [])}


def _extract_pdf_text(uploaded_file) -> str:
    # BytesIO avoids Windows locking issues with NamedTemporaryFile(delete=True).
    data = uploaded_file.read()
    if not data:
        return ""
    text_parts = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages[:8]:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts).strip()


_easyocr_reader = None
_easyocr_lock = threading.Lock()


def _get_easyocr_reader():
    """Lazy-load EasyOCR (downloads models on first use). Thread-safe for Flask."""
    global _easyocr_reader
    if _easyocr_reader is not None:
        return _easyocr_reader
    with _easyocr_lock:
        if _easyocr_reader is not None:
            return _easyocr_reader
        import easyocr

        langs = [
            x.strip()
            for x in os.getenv("EASYOCR_LANGS", "en").split(",")
            if x.strip()
        ] or ["en"]
        gpu = os.getenv("EASYOCR_GPU", "").lower() in ("1", "true", "yes")
        _easyocr_reader = easyocr.Reader(langs, gpu=gpu)
        return _easyocr_reader


def _extract_image_text_easyocr(data: bytes) -> str:
    try:
        import numpy as np
        from PIL import Image

        image = Image.open(BytesIO(data)).convert("RGB")
        arr = np.asarray(image)
        reader = _get_easyocr_reader()
        lines = reader.readtext(arr, detail=0, paragraph=False)
        if not lines:
            return ""
        return "\n".join(str(t).strip() for t in lines if str(t).strip()).strip()
    except Exception as e:
        print(f"EasyOCR image extract failed: {e}")
        return ""


def _extract_image_text_tesseract(data: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(BytesIO(data))
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        print(f"Tesseract image extract failed: {e}")
        return ""


def _extract_image_text(uploaded_file) -> str:
    data = uploaded_file.read()
    if not data:
        return ""

    engine = (os.getenv("OCR_ENGINE") or "easyocr").strip().lower()
    if engine == "tesseract":
        return _extract_image_text_tesseract(data)

    text = _extract_image_text_easyocr(data)
    if text:
        return text
    if os.getenv("OCR_FALLBACK_TESSERACT", "").lower() in ("1", "true", "yes"):
        return _extract_image_text_tesseract(data)
    return ""


def _normalize_workspace_payload(payload: dict):
    data = payload or {}
    return {
        "sources": data.get("sources", []),
        "chatHistory": data.get("chatHistory", [])
    }


def _is_simple_greeting(text: str) -> bool:
    """Check if the text is a simple greeting without legal substance."""
    if not text:
        return False
        
    # Standard greetings and variants
    greetings = {
        "hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", 
        "assalam o alaikum", "aoa", "asalam o alaikum", "salam", "slm", "hi there", "hello there",
        "how are you", "how are you doing", "what's up", "whats up", "hey advisor", "hi advisor"
    }
    
    clean = text.lower().strip().rstrip('?!.')
    
    # Direct match
    if clean in greetings:
        return True
        
    # Short message containing a greeting (e.g., "Hi!")
    words = text.split()
    if len(words) <= 3:
        # Check if any word is a greeting or if the whole thing is
        for g in greetings:
            if g in clean:
                # If it contains a greeting and is very short, it's likely just a greeting
                # Unless it also contains a legal keyword
                legal_keywords = {"law", "crime", "bail", "peca", "ppc", "court", "judge", "police", "fir", "complaint"}
                if not any(k in clean for k in legal_keywords):
                    return True
                    
    return False


def _build_evidence_checklist(full_text: str, incident_date: str = ""):
    """Regex over merged text; `incident_date` from the client counts as Date of Incident when non-empty."""
    lowered = (full_text or "").lower()
    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
    ]
    has_structured_date = bool((incident_date or "").strip())
    date_in_text = any(re.search(p, lowered) for p in date_patterns)

    checks = [
        ("Date of Incident", None),
        ("Jurisdiction / Location", [r"\b(karachi|lahore|islamabad|peshawar|quetta|pakistan)\b"]),
        ("CNIC / Identity of Respondent", [r"\b\d{5}-\d{7}-\d\b", r"\bcnic\b"]),
        ("Proof of Harm / Defamation", [r"\bdefamation\b", r"\bharm\b", r"\bdamage\b", r"\blibel\b"]),
        ("Witness Statements", [r"\bwitness\b", r"\bstatement\b"]),
        ("Formal Notice Proof", [r"\blegal notice\b", r"\bformal notice\b", r"\bnotice served\b"]),
    ]
    result = []
    for label, patterns in checks:
        if label == "Date of Incident":
            found = has_structured_date or date_in_text
        else:
            found = any(re.search(pattern, lowered) for pattern in patterns)
        result.append({
            "label": label,
            "status": "found" if found else "missing",
        })
    return result


def _compute_probability(case_count: int, source_count: int, checklist):
    checklist_found = len([x for x in checklist if x["status"] == "found"])
    completeness = checklist_found / max(len(checklist), 1)
    similarity = min(case_count / 5.0, 1.0)
    legal_grounding = min(source_count / 6.0, 1.0)

    score = int(((0.45 * completeness) + (0.35 * similarity) + (0.20 * legal_grounding)) * 100)
    score = max(25, min(92, score))

    def _band(value):
        if value >= 0.75:
            return "Strong"
        if value >= 0.45:
            return "Moderate"
        return "Weak"

    return {
        "score": score,
        "label": "High Merit" if score >= 70 else "Moderate Merit" if score >= 50 else "Low Merit",
        "factors": {
            "legal_grounds": _band(legal_grounding),
            "evidence_weight": _band(completeness),
            "precedent_similarity": _band(similarity),
        }
    }

# Explicit title -> on-disk PDF filename map (used when Document.source_file
# is missing in Neo4j, which is currently the case for every ingested doc).
# Keep keys identical to the `document.title` value in the source JSONs.
TITLE_TO_FILENAME = {
    "Constitution of the Islamic Republic of Pakistan": "Constitution, 1973.pdf",
    "Pakistan Penal Code": "Pakistan Penal Code.pdf",
    "The Electronic Transactions Ordinance, 2002": "The Electronic Transactions Ordinance, 2002.pdf",
    "Pakistan Telecommunication Rules, 2000": "Pakistan Telecom Rules.pdf",
    "The Prevention of Electronic Crimes Act, 2016": "PECA Act, 2016.pdf",
    "Prevention of Electronic Crimes (Amendment) Act, 2025": "PECA Amendment, 2025.pdf",
}

# Tokens that carry no signal when matching titles against filenames.
_PDF_MATCH_STOPWORDS = {
    "the", "of", "and", "a", "an", "for", "to", "in", "on",
    "act", "rules", "ordinance", "code",
}


def _tokenize_for_match(text: str) -> set:
    """Lowercase + alphanumeric tokens, minus stopwords, for fuzzy filename matching."""
    if not text:
        return set()
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in tokens if t and t not in _PDF_MATCH_STOPWORDS and len(t) > 1}


def _scan_pdf_directory_for_title(base_path: Path, title: str):
    """
    Last-resort: find the PDF in `base_path` whose filename has the highest
    token overlap with `title`. Returns the filename or None if nothing
    meaningfully matches. Tolerates future PDF renames as long as the new
    filename still contains identifying words from the document title.
    """
    if not title or not base_path.exists():
        return None

    title_tokens = _tokenize_for_match(title)
    if not title_tokens:
        return None

    best_filename = None
    best_score = 0
    for pdf_path in base_path.glob("*.pdf"):
        file_tokens = _tokenize_for_match(pdf_path.stem)
        if not file_tokens:
            continue
        score = len(title_tokens & file_tokens)
        if score > best_score:
            best_score = score
            best_filename = pdf_path.name

    # Require at least 2 overlapping signal tokens to avoid spurious matches
    # (e.g. matching every "Pakistan ..." PDF to any title containing "Pakistan").
    if best_score >= 2:
        return best_filename
    return None


def get_pdf_path(filename, title=None):
    """
    Resolve a PDF filename relative to backend/data/pdfs.

    Resolution order:
      1. `filename` from the DB (Document.source_file), if present on disk
         (preferring a `-Cleaned.pdf` variant).
      2. `TITLE_TO_FILENAME[title]` mapping, with the same -Cleaned/original
         lookup.
      3. Auto-discovery: scan `backend/data/pdfs` and pick the PDF whose
         filename shares the most identifying tokens with `title`.
    """
    base_path = Path(__file__).parent.parent.parent / 'data' / 'pdfs'

    def _resolve(name):
        """Return cleaned variant if it exists, else original if it exists, else None."""
        if not name:
            return None
        cleaned = name.replace('.pdf', '-Cleaned.pdf')
        if (base_path / cleaned).exists():
            return cleaned
        if (base_path / name).exists():
            return name
        return None

    # 1. Filename from the graph database.
    resolved = _resolve(filename)
    if resolved:
        return resolved

    # 2. Explicit title -> filename mapping.
    if title:
        for key, val in TITLE_TO_FILENAME.items():
            if key.lower() in title.lower() or title.lower() in key.lower():
                resolved = _resolve(val)
                if resolved:
                    return resolved
                break

    # 3. Token-overlap scan of the PDF directory (auto-heals on rename).
    discovered = _scan_pdf_directory_for_title(base_path, title)
    if discovered:
        return _resolve(discovered) or discovered

    return None

def format_graph_response(final_state):
    """Helper to format graph state into API response"""
    # Map output to API format
    statutes = final_state.get("statutes", [])
    cases = final_state.get("cases", [])
    
    # Format statutes as sources
    formatted_sources = []
    for doc in statutes:
        # Resolve best PDF file (cleaned vs original)
        source_file = doc.get("source_file")
        document_title = doc.get("document_title")
        page_number = doc.get("page_number", 1)

        # Pass title for fallback resolution
        pdf_file = get_pdf_path(source_file, document_title)
        
        pdf_link = None
        if pdf_file:
            # Use fragment #page=N&search=Term for browser PDF viewer navigation and highlighting
            article_num = doc.get("article_number", "")
            pdf_link = f"/api/pdf?file={pdf_file}#page={page_number}"
            
            if article_num and str(article_num).lower() != "n/a":
                # Add search parameter to highlight the article number
                pdf_link += f"&search={article_num}"

        source = {
            "document": doc.get("document_title", "Unknown"),
            "title": doc.get("title", ""),
            "article": str(doc.get("article_number", "N/A")),
            "relevance_score": doc.get("final_score", 0),
            "type": "article",
            "pdf_link": pdf_link,
            "page_number": page_number,
            "source_file": source_file,
            "chapter": doc.get("chapter"),
            "part": doc.get("part"),
        }
        formatted_sources.append(source)
        
    # Format cases separately
    formatted_cases = []
    for doc in cases:
        case_item = {
            "citation": doc.get("citation", "N/A"),
            "title": doc.get("title", doc.get("citation", "Unknown Case")),
            "court": doc.get("court", "Unknown Court"),
            "date": doc.get("date", ""),
            "summary": doc.get("summary", "")[:150] + "...",
            "pdf_link": doc.get("pdf_link", None),
            "relevance_score": doc.get("final_score", 0),
            "type": "case",
            "cyber_law_reason": doc.get("cyber_law_reason"),
            "cyber_law_triggers_json": doc.get("cyber_law_triggers_json"),
        }
        formatted_cases.append(case_item)
    
    result = {
        'answer': final_state.get('answer', 'No answer generated'),
        'sources': formatted_sources,
        'cases': formatted_cases,
        'complexity': final_state.get('complexity', 'unknown'),
        'orchestrator': {
            'steps': final_state.get('steps', []),
            'strategy_used': 'LangGraph Parallel Retrieval',
            'query_type': final_state.get('complexity', 'general')
        },
        'metadata': {
            'statute_count': len(formatted_sources),
            'case_count': len(formatted_cases)
        }
    }
    return result


@app.route("/api/ping", methods=["GET"])
def api_ping():
    """Lightweight reachability check from the browser (via Vite proxy or direct)."""
    return jsonify({"ok": True, "service": "ailegaladvisor-api"})


@app.route('/health', methods=['GET'])
def health_check():
    generation_status = rag_system.check_generation_health()
    
    return jsonify({
        'status': 'healthy' if generation_status.get("healthy") else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'generation_backend': generation_status.get("backend"),
            'generation': 'connected' if generation_status.get("healthy") else 'disconnected',
            'generation_error': generation_status.get("error"),
            'neo4j': 'connected',  # If we got here, Neo4j is working
            'mongodb': 'connected' if mongo_db is not None else 'disconnected',
            'model': generation_status.get("model")
        }
    })


@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json or {}
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()
        organization = data.get("organization", "").strip()

        if not name or not email or not password:
            return jsonify({"success": False, "error": "Name, email and password are required"}), 400

        if mongo_users is not None:
            if mongo_users.find_one({"email": email}):
                return jsonify({"success": False, "error": "Account already exists"}), 409
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "name": name,
                "email": email,
                "password_hash": _hash_password(password),
                "organization": organization,
                "created_at": datetime.now().isoformat()
            }
            mongo_users.insert_one(user)
        else:
            user_id = str(uuid.uuid4())

        return jsonify({
            "success": True,
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "organization": organization,
                "createdAt": datetime.now().isoformat()
            }
        }), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "").strip()
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password are required"}), 400

        if mongo_users is None:
            return jsonify({"success": False, "error": "MongoDB is required for login"}), 500

        user = mongo_users.find_one({"email": email})
        if not user or user.get("password_hash") != _hash_password(password):
            return jsonify({"success": False, "error": "Invalid email or password"}), 401

        token = str(uuid.uuid4())
        mongo_sessions.update_one(
            {"token": token},
            {"$set": {"token": token, "user_id": user["id"], "created_at": datetime.now().isoformat()}},
            upsert=True
        )

        return jsonify({
            "success": True,
            "token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "organization": user.get("organization", ""),
                "createdAt": user.get("created_at")
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    try:
        token = (request.json or {}).get("token")
        if mongo_sessions is not None and token:
            mongo_sessions.delete_one({"token": token})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        new_password = data.get("newPassword", "").strip()
        if not email or not new_password:
            return jsonify({"success": False, "error": "Email and new password are required"}), 400
        if mongo_users is None:
            return jsonify({"success": False, "error": "MongoDB is required"}), 500
        result = mongo_users.update_one({"email": email}, {"$set": {"password_hash": _hash_password(new_password)}})
        if result.matched_count == 0:
            return jsonify({"success": False, "error": "User not found"}), 404
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/auth/update-email', methods=['POST'])
def update_email():
    try:
        data = request.json or {}
        old_email = data.get("oldEmail", "").strip().lower()
        new_email = data.get("newEmail", "").strip().lower()
        if not old_email or not new_email:
            return jsonify({"success": False, "error": "Both old and new emails are required"}), 400
        if mongo_users is None:
            return jsonify({"success": False, "error": "MongoDB is required"}), 500
        if mongo_users.find_one({"email": new_email}):
            return jsonify({"success": False, "error": "New email is already in use"}), 409
        result = mongo_users.update_one({"email": old_email}, {"$set": {"email": new_email}})
        if result.matched_count == 0:
            return jsonify({"success": False, "error": "User not found"}), 404
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/user-data/<user_id>', methods=['GET'])
def get_user_data(user_id):
    try:
        if mongo_workspaces is None:
            return jsonify({"success": True, "user_id": user_id, "data": {"sources": [], "chatHistory": []}})
        doc = mongo_workspaces.find_one({"user_id": user_id}, {"_id": 0, "data": 1})
        data = _normalize_workspace_payload(doc.get("data") if doc else {})
        return jsonify({"success": True, "user_id": user_id, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/user-data/<user_id>', methods=['PUT'])
def save_user_data(user_id):
    try:
        payload = request.json or {}
        data = _normalize_workspace_payload(payload.get("data", {}))
        if mongo_workspaces is None:
            return jsonify({"success": True, "user_id": user_id, "data": data})
        mongo_workspaces.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "data": data, "updated_at": datetime.now().isoformat()}},
            upsert=True
        )
        return jsonify({"success": True, "user_id": user_id, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/query', methods=['POST'])
def query():
    """
    Main query endpoint for legal questions
    
    Request body:
    {
        "question": "What is bail?",
        "session_id": "optional-session-id",
        "use_orchestrator": true  # Optional: use advanced orchestration (default: true)
    }
    """
    try:
        data = request.json
        question = data.get('question', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))
        use_orchestrator_flag = data.get('use_orchestrator', True)  # Default to orchestrator
        
        if not question:
            return jsonify({
                'error': 'Question is required'
            }), 400
        
        # Check for simple greetings
        if _is_simple_greeting(question):
            return jsonify({
                'success': True,
                'answer': "Hello! I am your AI Legal Advisor. How can I assist you today with Pakistani cybercrime law?",
                'sources': [],
                'cases': [],
                'session_id': session_id,
                'duration': 0,
                'complexity': 'simple',
                'retrieval_strategy': 'greeting'
            })
        
        start_time = datetime.now()
        
        # Use LangGraph directly
        if use_orchestrator_flag:
            print(f"\n{'='*70}")
            print(f"LangGraph Processing Query: {question}")
            print(f"{'='*70}\n")
            
            # Initial State
            initial_state = {
                "question": question,
                "steps": [],
                "statutes": [],
                "cases": [],
                "documents": []
            }
            
            # Config to pass RAG instance
            config = {"configurable": {"rag": rag_system}}
            
            # Invoke Graph
            try:
                final_state = legal_graph_app.invoke(initial_state, config=config)
                result = format_graph_response(final_state)
                print(f"\nGraph Execution Complete (Steps: {result['orchestrator']['steps']})")
                
            except Exception as graph_error:
                print(f"Graph Execution Failed: {str(graph_error)}")
                import traceback
                traceback.print_exc()
                
                # Fallback response for user
                result = {
                    'answer': "I apologize, but I could not find any relevant legal documents to answer your question. Please try asking a specific legal question related to Pakistani law.",
                    'sources': [],
                    'cases': [],
                    'complexity': 'unknown',
                    'orchestrator': {
                        'steps': ['error_fallback'],
                        'strategy_used': 'Error Recovery',
                        'query_type': 'error'
                    },
                    'metadata': {'statute_count': 0, 'case_count': 0}
                }
            
            print(f"{'='*70}\n")
            
        else:
            # Fallback to direct RAG with multi-stage
            result = rag_system.query(question, use_multi_stage=True)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        session_doc = _get_conversation(session_id)
        history = session_doc.get("history", [])

        history.append({
            'question': question,
            'answer': result['answer'],
            'sources': result['sources'],
            'cases': result.get('cases', []),
            'timestamp': datetime.now().isoformat(),
            'duration': duration
        })
        _save_conversation(session_id, {"session_id": session_id, "history": history, "updated_at": datetime.now().isoformat()})
        
        return jsonify({
            'success': True,
            'answer': result['answer'],
            'sources': result['sources'],
            'cases': result.get('cases', []),
            'session_id': session_id,
            'duration': duration,
            'complexity': result.get('complexity', 'unknown'),
            'retrieval_strategy': result.get('retrieval_strategy', 'standard'),
            'orchestrator': result.get('orchestrator', None),
            'metadata': result.get('metadata', None)  # Include filtering metadata
        })
        
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """Get conversation history for a session"""
    history = _get_conversation(session_id).get("history", [])
    return jsonify({
        'session_id': session_id,
        'history': history,
        'count': len(history)
    })

@app.route('/api/history/<session_id>', methods=['DELETE'])
def clear_history(session_id):
    """Clear conversation history for a session"""
    if session_id in conversation_history:
        del conversation_history[session_id]
    if mongo_conversations is not None:
        mongo_conversations.delete_one({"session_id": session_id})
    return jsonify({
        'success': True,
        'message': 'History cleared'
    })


@app.route('/api/ingest/ocr', methods=['POST'])
def ingest_ocr():
    try:
        uploaded_file = request.files.get("file")
        if not uploaded_file:
            return jsonify({"success": False, "error": "File is required"}), 400

        filename = uploaded_file.filename or "uploaded_file"
        lowered = filename.lower()
        if lowered.endswith(".pdf"):
            extracted_text = _extract_pdf_text(uploaded_file)
        else:
            extracted_text = _extract_image_text(uploaded_file)

        if not extracted_text:
            return jsonify({
                "success": True,
                "extracted_facts": [],
                "detected_entities": [],
                "document_confidence": 0.2,
                "raw_text": "",
                "warning": (
                    "Could not extract meaningful text. Image OCR defaults to EasyOCR (first run downloads models). "
                    "Set OCR_ENGINE=tesseract and install Tesseract on the host, or OCR_FALLBACK_TESSERACT=true to try Tesseract after EasyOCR."
                )
            })

        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
        facts = lines[:8]
        entities = []
        seen = set()
        for token in re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", extracted_text):
            if token not in seen:
                seen.add(token)
                entities.append(token)
            if len(entities) >= 12:
                break

        return jsonify({
            "success": True,
            "extracted_facts": facts,
            "detected_entities": entities,
            "document_confidence": 0.75 if len(extracted_text) > 250 else 0.55,
            "raw_text": extracted_text[:5000]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/workspace/analyze', methods=['POST'])
def workspace_analyze():
    try:
        data = request.json or {}
        narrative = data.get("narrative", "").strip()
        extracted_text = data.get("ocr_text", "").strip()
        session_id = data.get("session_id", str(uuid.uuid4()))
        incident_date = data.get("incident_date", "").strip()
        if not narrative:
            return jsonify({"success": False, "error": "Narrative is required"}), 400

        # Check for simple greetings
        if _is_simple_greeting(narrative):
            return jsonify({
                "success": True,
                "session_id": session_id,
                "summary": "Hello! I am your AI Legal Advisor. I can help you analyze legal documents, draft petitions, or research case law. How can I assist you with Pakistani cybercrime law today?",
                "applicable_laws": [],
                "related_cases": [],
                "evidence_checklist": [],
                "win_probability": {"score": 0, "label": "N/A", "factors": {"legal_grounds": "N/A", "evidence_weight": "N/A", "precedent_similarity": "N/A"}},
                "sources": []
            })

        initial_state = {
            "question": narrative,
            "steps": [],
            "statutes": [],
            "cases": [],
            "documents": []
        }
        config = {"configurable": {"rag": rag_system}}
        final_state = legal_graph_app.invoke(initial_state, config=config)
        formatted = format_graph_response(final_state)

        merged_text = f"{incident_date}\n{narrative}\n{extracted_text}".strip()
        checklist = _build_evidence_checklist(merged_text, incident_date=incident_date)
        probability = _compute_probability(
            case_count=len(formatted.get("cases", [])),
            source_count=len(formatted.get("sources", [])),
            checklist=checklist
        )

        applicable_laws = []
        for source in formatted.get("sources", [])[:5]:
            applicable_laws.append({
                "document": source.get("document"),
                "article": source.get("article"),
                "title": source.get("title"),
                "relevance_score": source.get("relevance_score", 0),
                "pdf_link": source.get("pdf_link"),
                "chapter": source.get("chapter"),
                "part": source.get("part"),
            })

        return jsonify({
            "success": True,
            "session_id": session_id,
            "summary": formatted.get("answer", ""),
            "applicable_laws": applicable_laws,
            "related_cases": formatted.get("cases", []),
            "evidence_checklist": checklist,
            "win_probability": probability,
            "sources": formatted.get("sources", []),
            "reasons": [
                f"Matched {len(formatted.get('cases', []))} related precedents",
                f"Detected {len([x for x in checklist if x['status'] == 'found'])} checklist items as present",
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _draft_document(prompt: str, narrative: str, sources: list, related_cases: list):
    context_lines = [f"Narrative:\n{narrative}\n"]
    if sources:
        context_lines.append("Relevant Laws:")
        for src in sources[:5]:
            context_lines.append(f"- {src.get('document')} Article {src.get('article')}: {src.get('title', '')}")
    if related_cases:
        context_lines.append("Related Cases:")
        for case in related_cases[:4]:
            context_lines.append(f"- {case.get('title')} ({case.get('citation')})")
    context = "\n".join(context_lines)
    return rag_system.generate_answer_ollama(prompt, context, response_format="text")


@app.route('/api/draft/petition', methods=['POST'])
def draft_petition():
    try:
        data = request.json or {}
        narrative = data.get("narrative", "").strip()
        template_id = data.get("template_id", "default")
        sources = data.get("sources", [])
        related_cases = data.get("related_cases", [])
        if not narrative:
            return jsonify({"success": False, "error": "Narrative is required"}), 400
        
        prompts = {
            "writ": "Draft a formal Writ Petition for High Court under Article 199. Include Title, Facts, Grounds, and Prayer.",
            "bail": "Draft a Bail Application (497/498 CrPC) for cybercrime case. Focus on bailability and lack of evidence.",
            "quashment": "Draft a Quashment Petition for FIR under section 561-A CrPC. Argument: no offense made out.",
            "default": "Draft a formal legal petition in Pakistani legal style with sections: Title, Facts, Legal Grounds, Prayer, Verification. Keep it court-ready."
        }
        prompt = prompts.get(template_id, prompts["default"])
        
        body = _draft_document(prompt, narrative, sources, related_cases)
        return jsonify({
            "success": True, 
            "title": f"Draft {template_id.title()} Petition", 
            "body_markdown": body, 
            "citations": sources[:5]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/draft/nccia', methods=['POST'])
def draft_nccia():
    try:
        data = request.json or {}
        narrative = data.get("narrative", "").strip()
        template_id = data.get("template_id", "nccia")
        sources = data.get("sources", [])
        related_cases = data.get("related_cases", [])
        if not narrative:
            return jsonify({"success": False, "error": "Narrative is required"}), 400
            
        prompts = {
            "nccia": "Draft an NCCIA cybercrime complaint with sections: Complainant Details, Incident Description, Evidence Summary, Applicable Law, Relief Requested.",
            "harassment": "Draft a specific cyber-harassment complaint to NCCIA. Focus on Section 21/24 of PECA. Include evidence of non-consensual sharing or stalking.",
            "fraud": "Draft a financial cyber-fraud complaint to NCCIA. Focus on Section 13/14 of PECA. Include transaction details and unauthorized access."
        }
        prompt = prompts.get(template_id, prompts["nccia"])
        
        body = _draft_document(prompt, narrative, sources, related_cases)
        return jsonify({
            "success": True,
            "title": f"Draft {template_id.title()} Complaint",
            "body_markdown": body,
            "sections": ["Complainant Details", "Incident Description", "Evidence Summary", "Applicable Law", "Relief Requested"]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/search/semantic', methods=['POST'])
def semantic_search():
    """
    Semantic search for articles
    
    Request body:
    {
        "query": "search term",
        "top_k": 10
    }
    """
    try:
        data = request.json
        query = data.get('query', '').strip()
        top_k = data.get('top_k', 10)
        
        if not query:
            return jsonify({
                'error': 'Query is required'
            }), 400
        
        results = rag_system.semantic_search(query, top_k=top_k)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search/keyword', methods=['POST'])
def keyword_search():
    """
    Keyword-based full-text search
    
    Request body:
    {
        "query": "search term",
        "top_k": 10
    }
    """
    try:
        data = request.json
        query = data.get('query', '').strip()
        top_k = data.get('top_k', 10)
        
        if not query:
            return jsonify({
                'error': 'Query is required'
            }), 400
        
        results = rag_system.keyword_search(query, top_k=top_k)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/article/<path:article_id>/related', methods=['GET'])
def get_related(article_id):
    """Get related articles for a given article"""
    try:
        depth = request.args.get('depth', 2, type=int)
        
        results = rag_system.get_related_articles(article_id, depth=depth)
        
        return jsonify({
            'success': True,
            'article_id': article_id,
            'related_articles': results,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about the knowledge graph"""
    try:
        with rag_system.driver.session() as session:
            doc_count = session.run("MATCH (d:Document) RETURN count(d) as count").single()['count']
            
            article_count = session.run("MATCH (a:Article) RETURN count(a) as count").single()['count']
            
            concept_count = session.run("MATCH (c:Concept) RETURN count(c) as count").single()['count']
            
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()['count']
            
            return jsonify({
                'success': True,
                'stats': {
                    'documents': doc_count,
                    'articles': article_count,
                    'concepts': concept_count,
                    'relationships': rel_count,
                    'total_sessions': len(conversation_history)
                }
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/documents', methods=['GET'])
def list_documents():
    """List all documents in the knowledge graph"""
    try:
        with rag_system.driver.session() as session:
            query = """
            MATCH (d:Document)
            OPTIONAL MATCH (d)-[:CONTAINS]->(a:Article)
            RETURN d.title as title, 
                   d.year as year, 
                   d.type as type,
                   count(a) as article_count
            ORDER BY d.title
            """
            
            results = session.run(query)
            documents = [dict(record) for record in results]
            
            return jsonify({
                'success': True,
                'documents': documents,
                'count': len(documents)
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cases', methods=['GET'])
def list_cases():
    """List all court cases in the knowledge graph"""
    try:
        limit = request.args.get('limit', 100, type=int)
        cases = rag_system.get_all_cases(limit=limit)
        
        # If graph is empty, try to load from JSON as fallback
        if not cases:
            try:
                generated_json_path = Path(__file__).parent.parent.parent / 'data' / 'generated' / 'all_courts_cyber_cases_enriched.json'
                canonical_json_path = Path(__file__).parent.parent.parent / 'data' / 'jsons' / 'all_courts_cyber_cases_enriched.json'
                json_path = generated_json_path if generated_json_path.exists() else canonical_json_path
                if json_path.exists():
                    import json
                    with open(json_path, 'r', encoding='utf-8') as f:
                        all_cases = json.load(f)
                        # Transform to match expected structure
                        cases = []
                        for c in all_cases[:limit]:
                            cases.append({
                                'id': c.get('citation', str(uuid.uuid4())),
                                'citation': c.get('citation'),
                                'title': c.get('parties'),
                                'summary': c.get('excerpt'),
                                'court': c.get('court'),
                                'date': c.get('date'),
                                'judge': c.get('judge'),
                                'pdf_link': c.get('pdf_link'),
                                'type': 'case'
                            })
            except Exception as json_err:
                print(f"JSON fallback error: {json_err}")

        return jsonify({
            'success': True,
            'cases': cases,
            'count': len(cases)
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/concepts', methods=['GET'])
def list_concepts():
    """List all legal concepts with article counts"""
    try:
        with rag_system.driver.session() as session:
            query = """
            MATCH (c:Concept)<-[:RELATES_TO]-(a:Article)
            RETURN c.name as concept, count(a) as article_count
            ORDER BY article_count DESC
            LIMIT 50
            """
            
            results = session.run(query)
            concepts = [dict(record) for record in results]
            
            return jsonify({
                'success': True,
                'concepts': concepts,
                'count': len(concepts)
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/pdf', methods=['GET'])
def serve_pdf():
    """
    Serve PDF files with optional page parameter
    
    Query parameters:
    - file: Path to PDF file (relative to data/pdfs/)
    - page: Page number to open (optional)
    
    Example: /api/pdf?file=constitution.pdf&page=10
    """
    try:
        file_param = request.args.get('file', '').strip()
        page = request.args.get('page', '1')
        
        if not file_param:
            return jsonify({
                'error': 'File parameter is required'
            }), 400
        
        # Security: Prevent directory traversal
        if '..' in file_param or file_param.startswith('/'):
            return jsonify({
                'error': 'Invalid file path'
            }), 400
        
        # Construct full path to PDF
        # Correct path: backend/data/pdfs
        base_path = Path(__file__).parent.parent.parent / 'data' / 'pdfs'
        pdf_path = base_path / file_param
        
        # Check if file exists
        if not pdf_path.exists() or not pdf_path.is_file():
            return jsonify({
                'error': 'PDF file not found',
                'requested_file': file_param,
                'search_path': str(base_path)
            }), 404
        
        # Send file with page fragment
        response = send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=False,  # Display in browser
            download_name=pdf_path.name
        )
        
        # Add header for PDF page navigation (browsers support #page=N)
        response.headers['Content-Disposition'] = f'inline; filename="{pdf_path.name}"'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/pdf/info', methods=['GET'])
def pdf_info():
    """
    Get information about a PDF file
    
    Query parameters:
    - file: Path to PDF file
    """
    try:
        file_param = request.args.get('file', '').strip()
        
        if not file_param:
            return jsonify({
                'error': 'File parameter is required'
            }), 400
        
        # Security check
        if '..' in file_param or file_param.startswith('/'):
            return jsonify({
                'error': 'Invalid file path'
            }), 400
        
        base_path = Path(__file__).parent.parent.parent / 'data' / 'pdfs'
        pdf_path = base_path / file_param
        
        if not pdf_path.exists():
            return jsonify({
                'error': 'PDF file not found'
            }), 404
        
        # Get file info
        file_stat = pdf_path.stat()

        
        return jsonify({
            'success': True,
            'file_info': {
                'filename': pdf_path.name,
                'size_bytes': file_stat.st_size,
                'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'path': file_param
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Starting Legal AI Advisor API...")
    print("="*60)
    print(f"Neo4j connection: {os.getenv('NEO4J_URI')}")
    print(f"Ollama URL: {os.getenv('OLLAMA_URL')}")
    print(f"Model: {os.getenv('OLLAMA_MODEL')}")
    print("="*60 + "\n")
    
    # RAG system initialization already checked Ollama in __init__
    print("Server initialization complete!")
    print("Starting Flask server on http://0.0.0.0:5000\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)