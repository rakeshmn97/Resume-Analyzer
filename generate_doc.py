"""
Generate a comprehensive Word document for the RAG-based Resume Analyser project.
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import datetime

# ─────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────

def set_cell_bg(cell, hex_color: str):
    """Set background colour of a table cell."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)

def set_cell_border(cell, **kwargs):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        tag = OxmlElement(f'w:{edge}')
        tag.set(qn('w:val'), kwargs.get(edge, 'single'))
        tag.set(qn('w:sz'), '4')
        tag.set(qn('w:space'), '0')
        tag.set(qn('w:color'), kwargs.get('color', '4F81BD'))
        tcBorders.append(tag)
    tcPr.append(tcBorders)

def add_heading(doc, text, level=1, color=None):
    heading = doc.add_heading(text, level=level)
    run = heading.runs[0] if heading.runs else heading.add_run(text)
    if color:
        run.font.color.rgb = RGBColor(*color)
    return heading

def add_para(doc, text, bold=False, italic=False, size=11, color=None, indent=0):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(indent)
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor(*color)
    return p

def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.left_indent = Cm(level * 0.5)
    run = p.add_run(text)
    run.font.size = Pt(11)
    return p

def add_numbered(doc, text):
    p = doc.add_paragraph(style='List Number')
    run = p.add_run(text)
    run.font.size = Pt(11)
    return p

def add_code_block(doc, code: str):
    """Add a shaded code block paragraph."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.right_indent = Cm(0.5)
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), 'F2F2F2')
    pPr.append(shd)
    run = p.add_run(code)
    run.font.name = 'Courier New'
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x1F, 0x69, 0x7C)
    return p

def add_info_box(doc, label: str, text: str, bg='EBF3FB', label_color=(31, 73, 125)):
    """Add a 1-row table acting as an info / note box."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    cell = table.cell(0, 0)
    set_cell_bg(cell, bg)
    p = cell.paragraphs[0]
    r1 = p.add_run(f'{label}  ')
    r1.bold = True
    r1.font.color.rgb = RGBColor(*label_color)
    r1.font.size = Pt(10)
    r2 = p.add_run(text)
    r2.font.size = Pt(10)
    doc.add_paragraph()   # spacing

def add_divider(doc):
    p = doc.add_paragraph('─' * 90)
    p.runs[0].font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    p.runs[0].font.size = Pt(8)

def make_header_row(table, headers, bg='1F497D'):
    row = table.rows[0]
    for i, h in enumerate(headers):
        cell = row.cells[i]
        set_cell_bg(cell, bg)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.size = Pt(10)

def add_table_row(table, values, row_idx, alt=False):
    row = table.add_row()
    bg = 'EBF3FB' if alt else 'FFFFFF'
    for i, val in enumerate(values):
        cell = row.cells[i]
        set_cell_bg(cell, bg)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(str(val))
        run.font.size = Pt(10)

# ─────────────────────────────────────────────
# Build Document
# ─────────────────────────────────────────────

doc = Document()

# Page margins
section = doc.sections[0]
section.top_margin    = Cm(2.0)
section.bottom_margin = Cm(2.0)
section.left_margin   = Cm(2.5)
section.right_margin  = Cm(2.5)

# ── COVER PAGE ────────────────────────────────
cover = doc.add_paragraph()
cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph()
doc.add_paragraph()

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title.add_run('RESUME ANALYSER')
r.bold = True
r.font.size = Pt(32)
r.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = sub.add_run('RAG-Based Intelligent Recruitment System')
r2.font.size = Pt(18)
r2.font.color.rgb = RGBColor(0x4F, 0x81, 0xBD)

doc.add_paragraph()
doc.add_paragraph()

tagline = doc.add_paragraph()
tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
r3 = tagline.add_run('Complete Project Documentation — Concepts · Architecture · Implementation')
r3.italic = True
r3.font.size = Pt(12)
r3.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

doc.add_paragraph()
doc.add_paragraph()

date_p = doc.add_paragraph()
date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r4 = date_p.add_run(f'Generated: {datetime.date.today().strftime("%B %d, %Y")}')
r4.font.size = Pt(11)
r4.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

doc.add_page_break()

# ── TABLE OF CONTENTS ─────────────────────────
add_heading(doc, 'Table of Contents', level=1, color=(31, 73, 125))
toc_items = [
    ('1', 'Project Overview'),
    ('2', 'What is RAG? — Core Concept'),
    ('3', 'How RAG Works — Step by Step'),
    ('4', 'Core Technical Concepts'),
    ('5', 'Project vs Normal LLMs — Comparison'),
    ('6', 'System Architecture'),
    ('7', 'Project Folder Structure'),
    ('8', 'Tech Stack'),
    ('9', 'Implementation Phases (Roadmap)'),
    ('10', 'Core Code Logic'),
    ('11', 'Key Design Decisions'),
    ('12', 'Evaluation Strategy'),
    ('13', 'Getting Started'),
    ('14', 'Future Enhancements'),
]
for num, title_text in toc_items:
    p = doc.add_paragraph()
    r_num = p.add_run(f'{num}.  ')
    r_num.bold = True
    r_num.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    r_num.font.size = Pt(11)
    r_txt = p.add_run(title_text)
    r_txt.font.size = Pt(11)

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 1 — PROJECT OVERVIEW
# ════════════════════════════════════════════
add_heading(doc, '1. Project Overview', level=1, color=(31, 73, 125))

add_para(doc,
    'The Resume Analyser is an intelligent recruitment assistance system built on '
    'Retrieval-Augmented Generation (RAG). It allows HR teams and recruiters to upload '
    'a pool of resumes (PDF / DOCX) and ask natural language questions across all of them — '
    'without ever manually reading each file.',
    size=11)

doc.add_paragraph()
add_para(doc, 'Key Capabilities', bold=True, size=12)
capabilities = [
    'Multi-resume semantic search — "Who knows Python and AWS?"',
    'Job Description matching — score every candidate against a JD (0–100%)',
    'Automated skills extraction — list all technical & soft skills per candidate',
    'Candidate ranking — rank a pool of 50 applicants for any role in seconds',
    'Gap analysis — identify missing skills vs. a target job description',
    'Auto-generated candidate summaries — 3–5 bullet executive profile',
    'Full source traceability — see which exact resume passage the answer came from',
]
for cap in capabilities:
    add_bullet(doc, cap)

doc.add_paragraph()
add_info_box(doc, '💡 Problem Solved:',
    'Recruiters spend 6–8 seconds per resume on average. With 500 applicants, '
    'that is 50+ minutes of manual skimming. This system reduces that to a '
    'natural language query answered in under 5 seconds.',
    bg='EBF3FB')

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 2 — WHAT IS RAG
# ════════════════════════════════════════════
add_heading(doc, '2. What is RAG? — Core Concept', level=1, color=(31, 73, 125))

add_para(doc,
    'RAG stands for Retrieval-Augmented Generation. It is an AI architecture pattern '
    'that enhances a Large Language Model (LLM) by connecting it to an external knowledge '
    'source — in this case, your private resume database — rather than relying solely on '
    'the LLM\'s training data.',
    size=11)

doc.add_paragraph()
add_para(doc, 'The Problem with Plain LLMs', bold=True, size=12)
add_bullet(doc, 'LLMs have a fixed training knowledge cutoff — they know nothing about your specific candidates.')
add_bullet(doc, 'You cannot paste 500 resumes into a single prompt — context windows are limited (~128K tokens).')
add_bullet(doc, 'LLMs can hallucinate — fabricate skills or experience that were never in the resume.')
add_bullet(doc, 'Every query re-reads the whole document set — expensive and slow at scale.')

doc.add_paragraph()
add_para(doc, 'The RAG Solution', bold=True, size=12)
add_bullet(doc, 'Store all resumes as searchable vectors (embeddings) in a vector database — done once.')
add_bullet(doc, 'For each query, retrieve only the 5–10 most relevant resume chunks.')
add_bullet(doc, 'Pass only those chunks to the LLM as context — fast, cheap, and grounded.')
add_bullet(doc, 'The LLM generates an answer based strictly on the retrieved real data — no hallucination.')

doc.add_paragraph()
add_para(doc, 'The Librarian Analogy', bold=True, size=12)
add_para(doc,
    'Imagine a brilliant librarian (the RAG retriever) and a professor (the LLM). A recruiter '
    'asks: "Who among our applicants has machine learning experience?" The librarian does not '
    'read all 500 CVs aloud — they instantly search the index, pull the 5 most relevant CVs, '
    'and hand them to the professor. The professor reads just those 5 and gives a precise answer. '
    'That\'s RAG.',
    italic=True, size=11)

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 3 — HOW RAG WORKS
# ════════════════════════════════════════════
add_heading(doc, '3. How RAG Works — Step by Step', level=1, color=(31, 73, 125))

add_para(doc, 'Phase 1 — Indexing (Runs Once per Resume)', bold=True, size=12,
         color=(31, 73, 125))

steps_index = [
    ('Step 1 — Load',     'Upload PDF or DOCX resume. Use PyMuPDF (fitz) or python-docx to extract raw text.'),
    ('Step 2 — Chunk',    'Split text into overlapping segments (~500 tokens each, 50-token overlap). Prevents context loss at section boundaries.'),
    ('Step 3 — Embed',    'Convert each chunk into a numerical vector using an embedding model (e.g., Google text-embedding-004). Semantically similar text produces similar vectors.'),
    ('Step 4 — Store',    'Save each chunk, its vector, and metadata (filename, candidate name, section) in ChromaDB — a persistent vector database.'),
]
for title_s, desc in steps_index:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    r1 = p.add_run(f'{title_s}: ')
    r1.bold = True
    r1.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    r2 = p.add_run(desc)
    r2.font.size = Pt(11)

doc.add_paragraph()
add_para(doc, 'Phase 2 — Querying (Runs on Every User Question)', bold=True, size=12,
         color=(31, 73, 125))

steps_query = [
    ('Step 1 — Receive Query', 'User types a natural language question: "Which candidates know React and have startup experience?"'),
    ('Step 2 — Embed Query',   'The question is converted to a vector using the same embedding model used during indexing.'),
    ('Step 3 — Semantic Search','ChromaDB performs a similarity search — finds the top-K (5–10) resume chunks whose vectors are closest to the query vector.'),
    ('Step 4 — Build Context', 'Retrieved chunks are combined into a context window, along with their metadata.'),
    ('Step 5 — LLM Generation','The context + question are sent to the LLM (Gemini / GPT-4o) with a structured prompt. The LLM answers using only the retrieved content.'),
    ('Step 6 — Response',      'A structured JSON response is returned: answer, matched skills, match score, and summary.'),
]
for title_s, desc in steps_query:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    r1 = p.add_run(f'{title_s}: ')
    r1.bold = True
    r1.font.color.rgb = RGBColor(0x1F, 0x97, 0x5A)
    r2 = p.add_run(desc)
    r2.font.size = Pt(11)

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 4 — CORE CONCEPTS
# ════════════════════════════════════════════
add_heading(doc, '4. Core Technical Concepts', level=1, color=(31, 73, 125))

concepts = [
    ('Embeddings',
     'An embedding is a list of floating-point numbers (a vector) that captures the semantic '
     'meaning of a piece of text. The model "text-embedding-004" converts a sentence into a '
     'vector of 768 dimensions. Texts with similar meanings produce vectors that are close '
     'together in this high-dimensional space — even if they use different words.\n\n'
     'Example: "machine learning engineer" → [0.23, -0.87, 0.45, ...]\n'
     '"AI developer" → [0.21, -0.85, 0.47, ...]   ← Very close vectors'),

    ('Vector Store (ChromaDB)',
     'A vector store is a specialized database designed to store and search embeddings at speed. '
     'Unlike a SQL database that matches exact values, ChromaDB finds documents by semantic '
     'similarity using Approximate Nearest Neighbour (ANN) algorithms.\n\n'
     'Each stored record in ChromaDB contains:\n'
     '  • The original text chunk\n'
     '  • Its embedding vector\n'
     '  • Metadata: filename, candidate name, section (Skills / Experience / Education)'),

    ('Text Chunking',
     'A full resume (1–2 pages) is split into smaller, overlapping text segments before embedding. '
     'This is necessary because:\n'
     '  1. Large text blobs produce poor-quality embeddings (too much signal is lost)\n'
     '  2. Smaller chunks allow precise retrieval of just the relevant section\n\n'
     'Strategy: chunk_size=500 tokens, chunk_overlap=50 tokens\n'
     'Overlap ensures no important information is cut off at a boundary.'),

    ('Semantic Search / Cosine Similarity',
     'Once both the query and the stored chunks are embedded, the retriever computes cosine '
     'similarity between the query vector and every stored vector. Cosine similarity ranges from '
     '0.0 (completely different) to 1.0 (identical meaning).\n\n'
     'The top-K chunks with the highest similarity scores are returned as the most relevant '
     'context for the query — regardless of whether the exact words match.'),

    ('LLM + Prompt Engineering',
     'The retrieved chunks are injected into a carefully designed prompt template before being '
     'sent to the LLM. The prompt instructs the LLM to:\n'
     '  • Answer ONLY from the provided context\n'
     '  • Return a structured JSON response\n'
     '  • Say "Not found in resume" if information is absent\n\n'
     'This eliminates hallucination and produces verifiable, structured outputs.'),
]

for concept_title, concept_desc in concepts:
    add_heading(doc, concept_title, level=2, color=(79, 129, 189))
    add_para(doc, concept_desc, size=11)
    doc.add_paragraph()

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 5 — PROJECT VS NORMAL LLM
# ════════════════════════════════════════════
add_heading(doc, '5. Project vs Normal LLMs — Comparison', level=1, color=(31, 73, 125))

add_para(doc,
    'The table below shows how the RAG-based Resume Analyser differs from simply using '
    'ChatGPT or Gemini directly for resume analysis.',
    size=11)
doc.add_paragraph()

headers = ['Feature', 'Normal LLM (ChatGPT/Gemini)', 'RAG Resume Analyser']
table = doc.add_table(rows=1, cols=3)
table.style = 'Table Grid'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
make_header_row(table, headers)

rows_data = [
    ('Knowledge Source',     'Training data only (fixed cutoff)',     'Your uploaded resumes (always current)'),
    ('Private Data Access',  '❌ Cannot access private resumes',       '✅ Full access to your resume pool'),
    ('Hallucination Risk',   '⚠️ High — may fabricate skills',        '✅ Low — grounded in real resume text'),
    ('Handling 100 Resumes', '❌ Context limit exceeded',              '✅ Scales effortlessly via vector DB'),
    ('Search Type',          'Keyword (finds "Python" only)',          'Semantic (finds "ML" for "AI skills")'),
    ('Source Traceability',  '❌ Black box — no proof',                '✅ Shows exact resume chunk used'),
    ('Session Memory',       '❌ Lost after each session',             '✅ Persistent vector store'),
    ('Cost per Query',       'High — entire resume in every prompt',  'Low — only 5–10 small chunks'),
    ('Scalability',          '🔴 Poor — degrades with more docs',     '🟢 Excellent — O(log n) search'),
    ('Setup Required',       'None — just paste and ask',             'One-time indexing of resumes'),
]
for i, (feat, llm, rag) in enumerate(rows_data):
    add_table_row(table, [feat, llm, rag], i, alt=(i % 2 == 0))

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 6 — ARCHITECTURE
# ════════════════════════════════════════════
add_heading(doc, '6. System Architecture', level=1, color=(31, 73, 125))

add_para(doc,
    'The system is divided into two pipelines: the Ingestion Pipeline (offline) '
    'and the Query Pipeline (real-time).',
    size=11)

doc.add_paragraph()
add_para(doc, 'Ingestion Pipeline (runs once per resume upload)', bold=True, size=12)
ingestion = [
    'Resume Upload (PDF/DOCX)',
    '→  Document Loader (PyMuPDF / python-docx)',
    '→  Text Extractor',
    '→  Text Chunker (RecursiveCharacterTextSplitter)',
    '→  Embedding Model (text-embedding-004)',
    '→  ChromaDB (Vector Store with Metadata)',
]
for step in ingestion:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8)
    run = p.add_run(step)
    run.font.name = 'Courier New'
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x1F, 0x69, 0x7C)

doc.add_paragraph()
add_para(doc, 'Query Pipeline (runs per user question)', bold=True, size=12)
query_pipe = [
    'User Natural Language Query',
    '→  Query Embedder (same model as indexing)',
    '→  ChromaDB Semantic Search (Top-K retrieval)',
    '→  Context Builder (retrieved chunks + metadata)',
    '→  Prompt Template Engine',
    '→  LLM (Gemini 1.5 Flash / GPT-4o-mini)',
    '→  Structured JSON Response (answer, skills, score, summary)',
    '→  Streamlit UI Output',
]
for step in query_pipe:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8)
    run = p.add_run(step)
    run.font.name = 'Courier New'
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x1F, 0x7A, 0x40)

doc.add_paragraph()
add_info_box(doc, '📌 Key Design Principle:',
    'The embedding model used during INDEXING must be identical to the one used during '
    'QUERYING. Mixing models (e.g., indexing with MiniLM but querying with text-embedding-004) '
    'will produce incorrect similarity scores and broken retrieval.',
    bg='FFF3CD', label_color=(124, 77, 0))

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 7 — FOLDER STRUCTURE
# ════════════════════════════════════════════
add_heading(doc, '7. Project Folder Structure', level=1, color=(31, 73, 125))

structure = """Resume Analyser/
├── app/
│   ├── main.py                  # Streamlit entry point
│   ├── config.py                # API keys, model config
│   └── routers/
│       ├── upload.py            # Resume ingestion logic
│       └── query.py             # Query/chat endpoints
├── core/
│   ├── loader.py                # PDF/DOCX loading
│   ├── chunker.py               # Text splitting strategy
│   ├── embedder.py              # Embedding model wrapper
│   ├── vector_store.py          # ChromaDB abstraction
│   ├── retriever.py             # Semantic search + reranking
│   └── llm_chain.py             # RAG chain (LangChain)
├── models/
│   ├── resume.py                # Resume metadata (Pydantic)
│   └── query.py                 # Query/response schemas
├── prompts/
│   └── analyse_prompt.txt       # LLM prompt templates
├── data/
│   └── uploads/                 # Raw uploaded resumes
├── tests/
│   ├── test_loader.py
│   ├── test_retriever.py
│   └── test_chain.py
├── .env                         # API keys (never commit!)
├── requirements.txt
└── README.md"""

add_code_block(doc, structure)

doc.add_paragraph()
add_para(doc, 'Module Responsibilities', bold=True, size=12)
modules = [
    ('app/main.py',          'Streamlit frontend — file uploader, chat interface, results display'),
    ('core/loader.py',       'Detects file type (PDF/DOCX), extracts clean text, returns Document objects'),
    ('core/chunker.py',      'Splits documents into overlapping chunks using LangChain text splitters'),
    ('core/embedder.py',     'Wraps the embedding model — converts text to vectors'),
    ('core/vector_store.py', 'Abstracts ChromaDB operations: add, search, delete, filter by metadata'),
    ('core/retriever.py',    'Performs top-K semantic search, optionally re-ranks with a cross-encoder'),
    ('core/llm_chain.py',    'Builds and runs the RAG chain: retrieval → context → prompt → LLM → parse'),
    ('models/resume.py',     'Pydantic schema: Resume(id, name, filename, upload_date, chunks)'),
    ('prompts/',             'Stores prompt templates for different analysis modes (match, gap, summary)'),
]
for mod, desc in modules:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    r1 = p.add_run(f'{mod}')
    r1.bold = True
    r1.font.name = 'Courier New'
    r1.font.size = Pt(10)
    r1.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    r2 = p.add_run(f'  —  {desc}')
    r2.font.size = Pt(10)

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 8 — TECH STACK
# ════════════════════════════════════════════
add_heading(doc, '8. Tech Stack', level=1, color=(31, 73, 125))

stack_headers = ['Layer', 'Tool / Library', 'Purpose']
stack_table = doc.add_table(rows=1, cols=3)
stack_table.style = 'Table Grid'
stack_table.alignment = WD_TABLE_ALIGNMENT.CENTER
make_header_row(stack_table, stack_headers)

stack_rows = [
    ('Frontend UI',      'Streamlit',                  'Web interface — file upload, chat, results'),
    ('Backend API',      'FastAPI (optional)',          'REST API layer for production deployment'),
    ('PDF Parsing',      'PyMuPDF (fitz)',              'Extract text from PDF resumes'),
    ('DOCX Parsing',     'python-docx',                'Extract text from Word resumes'),
    ('Text Splitting',   'LangChain TextSplitter',     'Chunk text with configurable overlap'),
    ('Embeddings',       'Google text-embedding-004',  'Convert text → semantic vectors'),
    ('Embeddings (alt)', 'all-MiniLM-L6-v2',           'Local/offline alternative embedding'),
    ('Vector Database',  'ChromaDB',                   'Persistent vector storage & search'),
    ('RAG Framework',    'LangChain',                  'Orchestrate retrieval + LLM chain'),
    ('LLM',             'Gemini 1.5 Flash',            'Language generation & analysis'),
    ('LLM (alt)',        'GPT-4o-mini',                'OpenAI alternative'),
    ('Schema Validation','Pydantic',                   'Structured data models & JSON parsing'),
    ('Evaluation',       'RAGAS',                      'RAG quality metrics (faithfulness, recall)'),
    ('Config',           'python-dotenv',              'Manage API keys from .env file'),
]
for i, row in enumerate(stack_rows):
    add_table_row(stack_table, list(row), i, alt=(i % 2 == 0))

doc.add_paragraph()
add_para(doc, 'requirements.txt', bold=True, size=11)
req = (
    "streamlit\n"
    "langchain\n"
    "langchain-google-genai\n"
    "langchain-community\n"
    "chromadb\n"
    "pymupdf\n"
    "python-docx\n"
    "sentence-transformers\n"
    "pydantic\n"
    "python-dotenv\n"
    "fastapi\n"
    "uvicorn\n"
    "ragas"
)
add_code_block(doc, req)

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 9 — IMPLEMENTATION PHASES
# ════════════════════════════════════════════
add_heading(doc, '9. Implementation Phases (Roadmap)', level=1, color=(31, 73, 125))

phases = [
    ('Phase 1 — Document Ingestion Pipeline', [
        'Set up project structure and install dependencies',
        'Implement PDF loader using PyMuPDF (fitz)',
        'Implement DOCX loader using python-docx',
        'Extract and clean raw text from both formats',
        'Implement RecursiveCharacterTextSplitter with 500-token chunks and 50-token overlap',
        'Integrate Google text-embedding-004 or sentence-transformers',
        'Set up ChromaDB with persistent storage',
        'Store chunks with metadata: filename, candidate name, upload date, section type',
        'Write unit tests for loader and chunker',
    ]),
    ('Phase 2 — RAG Query Engine', [
        'Build the query embedding function (same model as indexing)',
        'Implement semantic search in ChromaDB with top-K retrieval',
        'Add metadata filtering (e.g., filter by specific candidate)',
        'Build context assembly from retrieved chunks',
        'Design structured prompt templates for different query types',
        'Integrate LangChain RAG chain with Gemini LLM',
        'Parse LLM output into structured Pydantic models (JSON mode)',
        'Write integration tests for end-to-end RAG pipeline',
    ]),
    ('Phase 3 — Analysis Features', [
        'Skills Extractor: parse and list all technical + soft skills from a resume',
        'JD Matcher: score a resume against a Job Description (0–100%)',
        'Gap Analyser: identify missing skills vs. the target JD',
        'Candidate Summary: generate 3–5 bullet executive summary',
        'Multi-Resume Ranking: rank all candidates in the pool for a given JD',
        'Side-by-side comparison of two candidates',
    ]),
    ('Phase 4 — Streamlit Frontend', [
        'Build multi-file upload widget for PDF/DOCX resumes',
        'Add processing spinner and progress indicator during indexing',
        'Build chat interface for natural language queries',
        'Display answer with source resume chunks (traceability)',
        'Add JD matching panel with score visualisation',
        'Build candidate ranking leaderboard view',
        'Add downloadable analysis report (PDF export)',
    ]),
    ('Phase 5 — Enhancements & Production', [
        'Add cross-encoder re-ranking (ms-marco-MiniLM) for better retrieval precision',
        'Implement query caching to speed up repeated questions',
        'Add RAGAS evaluation pipeline for continuous quality monitoring',
        'Integrate user authentication for multi-tenant deployment',
        'Containerise with Docker for production deployment',
        'Add FastAPI backend for REST API access',
        'Performance tuning: latency target < 3 seconds per query',
    ]),
]

for phase_title, tasks in phases:
    add_heading(doc, phase_title, level=2, color=(79, 129, 189))
    for task in tasks:
        add_bullet(doc, task)
    doc.add_paragraph()

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 10 — CORE CODE LOGIC
# ════════════════════════════════════════════
add_heading(doc, '10. Core Code Logic', level=1, color=(31, 73, 125))

add_heading(doc, 'Document Loader (core/loader.py)', level=2, color=(79, 129, 189))
add_code_block(doc,
"""import fitz          # PyMuPDF
from docx import Document

def load_pdf(path: str) -> str:
    doc = fitz.open(path)
    return "\\n".join(page.get_text() for page in doc)

def load_docx(path: str) -> str:
    doc = Document(path)
    return "\\n".join(p.text for p in doc.paragraphs)

def load_resume(path: str) -> str:
    if path.endswith(".pdf"):
        return load_pdf(path)
    elif path.endswith(".docx"):
        return load_docx(path)
    raise ValueError(f"Unsupported file type: {path}")
""")

doc.add_paragraph()
add_heading(doc, 'Chunker (core/chunker.py)', level=2, color=(79, 129, 189))
add_code_block(doc,
"""from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_text(text: str, filename: str, candidate_name: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\\n\\n", "\\n", ". ", " "]
    )
    chunks = splitter.split_text(text)
    return [
        {
            "text": chunk,
            "metadata": {
                "filename": filename,
                "candidate": candidate_name,
                "chunk_index": i
            }
        }
        for i, chunk in enumerate(chunks)
    ]
""")

doc.add_paragraph()
add_heading(doc, 'Vector Store (core/vector_store.py)', level=2, color=(79, 129, 189))
add_code_block(doc,
"""import chromadb
from chromadb.utils import embedding_functions

EMBED_FN = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key="YOUR_API_KEY",
    model_name="models/text-embedding-004"
)

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="resumes",
    embedding_function=EMBED_FN
)

def add_chunks(chunks: list[dict]):
    collection.add(
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
        ids=[f'{c["metadata"]["filename"]}_{c["metadata"]["chunk_index"]}'
             for c in chunks]
    )

def search(query: str, n_results: int = 5, where: dict = None):
    return collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where  # e.g., {"candidate": "John"}
    )
""")

doc.add_paragraph()
add_heading(doc, 'RAG Chain (core/llm_chain.py)', level=2, color=(79, 129, 189))
add_code_block(doc,
"""import json
from core.vector_store import search

PROMPT_TEMPLATE = \"\"\"
You are an expert HR analyst. Using ONLY the resume content below, answer the query.
If information is not present, respond with "Not found in resume."

Resume Context:
{context}

Query: {query}

Respond ONLY in JSON format:
{{
    "answer": "...",
    "skills_found": ["skill1", "skill2"],
    "match_score": 0-100,
    "summary": "..."
}}
\"\"\"

def analyse_resume(query: str, llm, candidate: str = None) -> dict:
    # 1. Retrieve relevant chunks
    where_filter = {"candidate": candidate} if candidate else None
    results = search(query, n_results=5, where=where_filter)
    
    # 2. Build context from retrieved chunks
    context = "\\n\\n".join(results["documents"][0])
    
    # 3. Fill prompt template
    prompt = PROMPT_TEMPLATE.format(context=context, query=query)
    
    # 4. Call LLM
    response = llm.invoke(prompt)
    
    # 5. Parse structured response
    return json.loads(response.content)
""")

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 11 — DESIGN DECISIONS
# ════════════════════════════════════════════
add_heading(doc, '11. Key Design Decisions', level=1, color=(31, 73, 125))

decisions = [
    ('Chunking Strategy',
     'Overlapping chunks (500 tokens, 50-token overlap) are used to ensure resume sections are '
     'not arbitrarily cut. Key info appearing near a section boundary (e.g., a skill listed at '
     'the end of a Work Experience paragraph) will appear in two adjacent chunks, guaranteeing '
     'retrieval. Consideration: for structured resumes, section-aware splitting (splitting on '
     '"Experience:", "Education:", "Skills:") is even better.'),

    ('Embedding Model Choice',
     'Two options are provided:\n'
     '  • Google text-embedding-004: Best quality, requires API key, cloud-based\n'
     '  • all-MiniLM-L6-v2 (Sentence Transformers): Runs 100% locally, no API key, '
     'slightly lower quality but faster for offline use.\n'
     'The model must be consistent between indexing and querying.'),

    ('ChromaDB over FAISS',
     'ChromaDB is chosen over FAISS for three reasons:\n'
     '  1. Persistent storage — survives application restarts\n'
     '  2. Metadata filtering — query by candidate name, date, section\n'
     '  3. Simpler API — no manual index serialisation required\n'
     'FAISS is faster for massive scale (millions of vectors) but requires '
     'more engineering overhead.'),

    ('Hallucination Guard',
     'The LLM prompt explicitly instructs the model to answer ONLY from the provided context '
     'and to respond "Not found in resume" if the information is absent. This "closed-book" '
     'prompting is the primary defence against hallucination. Additionally, source chunks are '
     'always displayed alongside the answer for human verification.'),

    ('Structured Output (JSON Mode)',
     'The LLM is prompted to always return valid JSON. This makes downstream parsing '
     'deterministic. Pydantic models validate the schema, raising errors if the LLM returns '
     'malformed output. Retry logic can re-invoke the LLM if parsing fails.'),
]

for title_d, explanation in decisions:
    add_heading(doc, title_d, level=2, color=(79, 129, 189))
    add_para(doc, explanation, size=11)
    doc.add_paragraph()

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 12 — EVALUATION
# ════════════════════════════════════════════
add_heading(doc, '12. Evaluation Strategy', level=1, color=(31, 73, 125))

add_para(doc,
    'The system is evaluated using RAGAS — a framework specifically designed for measuring '
    'RAG pipeline quality. Four metrics are tracked:',
    size=11)
doc.add_paragraph()

eval_headers = ['Metric', 'Tool', 'Description', 'Target']
eval_table = doc.add_table(rows=1, cols=4)
eval_table.style = 'Table Grid'
eval_table.alignment = WD_TABLE_ALIGNMENT.CENTER
make_header_row(eval_table, eval_headers)

eval_rows = [
    ('Context Precision',   'RAGAS', 'Are the retrieved chunks actually relevant to the query?',         '> 0.80'),
    ('Context Recall',      'RAGAS', 'Were all relevant resume sections retrieved?',                      '> 0.75'),
    ('Faithfulness',        'RAGAS', 'Is the answer fully supported by the retrieved context?',           '> 0.85'),
    ('Answer Relevance',    'RAGAS', 'Does the answer actually address what was asked?',                  '> 0.80'),
    ('End-to-End Latency',  'Custom','Total time from query to response',                                 '< 5 sec'),
    ('Retrieval Latency',   'Custom','Time for ChromaDB semantic search',                                 '< 200 ms'),
]
for i, row in enumerate(eval_rows):
    add_table_row(eval_table, list(row), i, alt=(i % 2 == 0))

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 13 — GETTING STARTED
# ════════════════════════════════════════════
add_heading(doc, '13. Getting Started', level=1, color=(31, 73, 125))

add_numbered(doc, 'Clone or create the project directory structure as shown in Section 7.')
add_numbered(doc, 'Create and activate a Python virtual environment.')
add_numbered(doc, 'Install all dependencies from requirements.txt.')
add_numbered(doc, 'Create a .env file with your API keys.')
add_numbered(doc, 'Run the Streamlit app.')

doc.add_paragraph()
add_code_block(doc,
"""# Step 1 — Navigate to project folder
cd "Resume Analyser"

# Step 2 — Create virtual environment
python -m venv venv

# Step 3 — Activate (Windows)
venv\\Scripts\\activate

# Step 4 — Install dependencies
pip install -r requirements.txt

# Step 5 — Create .env file
echo GOOGLE_API_KEY=your_key_here > .env

# Step 6 — Run the app
streamlit run app/main.py
""")

add_info_box(doc, '🔒 Security Note:',
    'Never commit your .env file to version control. Add it to .gitignore immediately. '
    'Your GOOGLE_API_KEY or OPENAI_API_KEY should never appear in any source file.',
    bg='FFF3CD', label_color=(124, 77, 0))

doc.add_page_break()

# ════════════════════════════════════════════
# SECTION 14 — FUTURE ENHANCEMENTS
# ════════════════════════════════════════════
add_heading(doc, '14. Future Enhancements', level=1, color=(31, 73, 125))

enhancements = [
    ('Cross-Encoder Re-ranking',
     'After the initial top-K retrieval (bi-encoder), a cross-encoder (e.g., ms-marco-MiniLM-L-6-v2) '
     're-scores each chunk against the query with higher accuracy. This two-stage approach '
     '(retrieve then rerank) significantly improves precision at the cost of small latency.'),

    ('Hybrid Search',
     'Combine dense (semantic) retrieval with sparse (BM25 keyword) search. This handles '
     'exact-match queries (e.g., specific certification names, exact job titles) better '
     'than pure semantic search alone.'),

    ('Agentic Resume Analysis',
     'Implement a LangChain Agent that can autonomously:\n'
     '  • Search across resumes\n'
     '  • Look up skill definitions online\n'
     '  • Calculate years of experience from dates\n'
     '  • Generate a full shortlist report without step-by-step user guidance'),

    ('Multimodal Support',
     'Extend the loader to handle resumes with tables, images, and charts using '
     'vision-capable models (e.g., Gemini 1.5 Pro Vision) to extract skills from '
     'graphical skill bars and infographic-style CVs.'),

    ('Analytics Dashboard',
     'A recruiter dashboard showing:\n'
     '  • Skills frequency heatmap across all candidates\n'
     '  • Experience distribution charts\n'
     '  • Educational background breakdown\n'
     '  • JD coverage gap analysis across the full pipeline'),
]

for title_e, desc in enhancements:
    add_heading(doc, title_e, level=2, color=(79, 129, 189))
    add_para(doc, desc, size=11)
    doc.add_paragraph()

# ── BACK COVER ────────────────────────────────
doc.add_page_break()
end = doc.add_paragraph()
end.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph()
doc.add_paragraph()
doc.add_paragraph()
r_end = end.add_run('— End of Document —')
r_end.font.size = Pt(14)
r_end.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
r_end.italic = True

footer_p = doc.add_paragraph()
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_footer = footer_p.add_run('Resume Analyser | RAG-Based Intelligent Recruitment System')
r_footer.font.size = Pt(11)
r_footer.font.color.rgb = RGBColor(0x4F, 0x81, 0xBD)

# ─────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────
output_path = 'Resume_Analyser_Project_Documentation.docx'
doc.save(output_path)
print(f"[OK] Document saved: {output_path}")
