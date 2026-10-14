import sys
from collections import Counter
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import CSV_PATH, EMBEDDING_BACKEND, SAMPLE_DIR, UPLOAD_DIR, llm_enabled
from app.routers.query import field_details, screen
from app.routers.upload import ingest_path, save_upload
from core.classifier import experience_level
from core.embedder import get_embedder
from core.loader import guess_candidate_name, load_resume
from core.vector_store import clear_store, delete_by_candidate, delete_by_filename, find_existing, list_candidates, profile_for

st.set_page_config(page_title="Resume Analyser", page_icon="📄", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; max-width: 1100px;}
    .hero {border-bottom: 1px solid #d9e2ec; margin-bottom: 1rem; padding-bottom: 0.6rem;}
    .hero h1 {font-size: 1.8rem; margin-bottom: 0.15rem; color: #1f497d;}
    .muted {color: #5c6b7a; font-size: 0.95rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

LEVELS = ["Fresher", "Mid-level", "Senior"]


def _level_of(person: dict) -> str:
    return person.get("level") or experience_level(person.get("years", 0))


def _compact_table(people: list[dict], include_match: bool = False) -> list[dict]:
    rows = []
    for item in people:
        profile = item["profile"]
        row = {
            "Name": profile["candidate"],
            "Field": profile.get("field") or "Unspecified",
            "Level": _level_of(profile),
            "Years": profile.get("years", ""),
            "Skills": profile.get("skills_line", ""),
            "Education": profile.get("education", ""),
            "Certifications": profile.get("certifications", ""),
            "Projects": profile.get("projects", ""),
            "AI Score": profile.get("ai_score") or "",
        }
        if include_match:
            row["Match %"] = item.get("score", "")
        row["Current salary"] = profile.get("salary") or ""
        rows.append(row)
    return rows


def get_full_resume_text(profile: dict) -> str:
    filename = profile.get("filename")
    if filename:
        up_file = UPLOAD_DIR / filename
        if up_file.exists() and up_file.is_file():
            try:
                return load_resume(str(up_file))
            except Exception:
                pass
        sm_file = SAMPLE_DIR / filename
        if sm_file.exists() and sm_file.is_file():
            try:
                return load_resume(str(sm_file))
            except Exception:
                pass

    if profile.get("text"):
        return profile["text"]

    matched = profile_for(profile.get("candidate", ""))
    if matched and matched.get("text"):
        return matched["text"]

    return ""


def _show_selected(item: dict) -> None:
    profile = item["profile"]
    col_hdr, col_btn = st.columns([3, 1.2])
    with col_hdr:
        st.subheader(f"👤 {profile['candidate']}")
        if profile.get("filename"):
            st.caption(f"📁 Document: `{profile['filename']}`")
    with col_btn:
        if st.button("📄 View Full Resume", key=f"btn_full_resume_{profile['candidate']}", help="Open complete uploaded resume in a new popup window", use_container_width=True):
            st.session_state["show_full_resume_candidate"] = item
            st.rerun()

    cols = st.columns(4)
    cols[0].metric("Field", profile.get("field") or "Unspecified")
    cols[1].metric("Level", _level_of(profile))
    cols[2].metric("Years Exp.", profile.get("years") or "0")
    cols[3].metric("AI Score", profile.get("ai_score") or "—")
    st.write(f"**Current Salary:** {profile.get('salary') or '—'}")
    if item.get("interpretation"):
        st.write(item["interpretation"])
    st.write(f"**Title:** {profile.get('title') or '—'}")
    st.write(f"**Education:** {profile.get('education') or 'not listed'}")
    st.write(f"**Certifications:** {profile.get('certifications') or 'None'}")
    st.write(f"**Skills:** {profile.get('skills_line') or 'not listed'}")
    st.write(f"**Projects:** {profile.get('projects') or '0'}")
    if item.get("found"):
        st.caption("Matched on this query: " + ", ".join(map(str, item["found"])))
    if item.get("missing"):
        st.caption("Missing vs this query: " + ", ".join(map(str, item["missing"])))


@st.dialog("Candidate Profile", width="medium")
def popup_profile(item: dict) -> None:
    _show_selected(item)


def _on_full_resume_dismiss():
    st.session_state.pop("show_full_resume_candidate", None)


@st.dialog("📄 Full Resume Document", width="large", on_dismiss=_on_full_resume_dismiss)
def popup_full_resume(item: dict) -> None:
    profile = item["profile"]
    col_hdr, col_back = st.columns([3, 1.2])
    with col_hdr:
        st.subheader(f"📄 {profile['candidate']}")
        if profile.get("filename"):
            st.caption(f"File: `{profile['filename']}` · Field: **{profile.get('field', 'Unspecified')}**")
    with col_back:
        if st.button("← Back to Summary", key="btn_back_to_summary", use_container_width=True):
            st.session_state.pop("show_full_resume_candidate", None)
            st.session_state["field_selected"] = profile["candidate"]
            st.rerun()

    st.divider()

    resume_text = get_full_resume_text(profile)
    if resume_text:
        st.text_area("Full Resume Content", value=resume_text, height=450, disabled=True)
        filename = profile.get("filename")
        if filename and (UPLOAD_DIR / filename).exists():
            data_bytes = (UPLOAD_DIR / filename).read_bytes()
            st.download_button(
                f"📥 Download {filename}",
                data=data_bytes,
                file_name=filename,
                use_container_width=True,
            )
        else:
            st.download_button(
                "📥 Download Resume Text",
                data=resume_text,
                file_name=f"{profile['candidate']}_resume.txt",
                mime="text/plain",
                use_container_width=True,
            )
    else:
        st.info("No raw resume document text found on disk for this candidate.")


@st.dialog("If candidate name already exists:", width="medium")
def duplicate_dialog(duplicates: list[str]) -> None:
    names_str = ", ".join(f"**{n}**" for n in sorted(set(duplicates)))
    st.warning(f"Candidate {names_str} is already in the database.")
    choice = st.radio(
        "If candidate name already exists:",
        ["Update candidate profile (replace existing)", "Keep current selection (skip duplicate)"],
        index=0,
        key="duplicate_action_choice",
        label_visibility="collapsed",
    )
    cols = st.columns([1, 1])
    if cols[0].button("Confirm", type="primary", use_container_width=True):
        st.session_state["duplicate_action_chosen"] = choice
        st.rerun()
    if cols[1].button("Cancel", use_container_width=True):
        st.session_state["duplicate_action_chosen"] = "Keep current selection (skip duplicate)"
        st.rerun()



st.markdown(
    "<div class='hero'><h1>Resume Analyser</h1>"
    "<div class='muted'>Screen candidates by field and experience. Uploaded resumes are filed automatically.</div></div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Index")
    people = list_candidates()
    st.caption(f"{len(people)} candidate{'s' if len(people) != 1 else ''} indexed")
    embedder = get_embedder()
    st.caption(f"Embeddings: {embedder.name} ({EMBEDDING_BACKEND})")
    st.caption("LLM: Gemini" if llm_enabled() else "LLM: local retrieval")
    if people:
        counts = Counter(person.get("field") or "Unspecified" for person in people)
        with st.expander(f"Fields ({len(counts)})"):
            for field, count in counts.most_common():
                st.write(f"{field}: {count}")
    if st.button("Index screening CSV", use_container_width=True):
        from scripts.index_csv import main as index_csv

        with st.spinner("Indexing AI_Resume_Screening.csv..."):
            index_csv()
        st.rerun()
    if st.button("Clear index", use_container_width=True):
        clear_store()
        st.rerun()

if "redirect_nav" in st.session_state:
    st.session_state["nav"] = st.session_state.pop("redirect_nav")
if "redirect_field_pick" in st.session_state:
    st.session_state["field_pick"] = st.session_state.pop("redirect_field_pick")

nav = st.radio(
    "Section",
    ["Ask / Job match", "Fields", "Upload"],
    horizontal=True,
    key="nav",
    label_visibility="collapsed",
)

if nav == "Ask / Job match":
    st.write("Ask a question or paste a job description. Matching candidates from **all fields** are listed and sorted by relevance.")
    query = st.text_area(
        "Question or job description",
        height=140,
        placeholder="People who know Python  /  Fresher with Python  /  Data scientist with SQL",
        key="screen_query",
    )
    if st.button("Screen candidates", type="primary"):
        if not query.strip():
            st.warning("Enter a role, skill, or job description.")
        elif not people:
            st.warning("Index the screening CSV first.")
        else:
            with st.spinner("Scoring the dataset..."):
                result = screen(query.strip(), minimum=5)
            st.session_state["screen_result"] = result
            st.session_state["ask_selected"] = None   # reset selection on new search
    result = st.session_state.get("screen_result")
    if result:
        st.info(result["group"])
        if result["field"] and result["field"] != "All Fields":
            st.caption(f"Section: {result['field']}")
        shown = result["people"]
        if shown:
            event_ask = st.dataframe(
                _compact_table(shown, include_match=True),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="ask_screen_table",
            )
            selected_rows_ask = []
            if event_ask and hasattr(event_ask, "selection"):
                sel = event_ask.selection
                selected_rows_ask = sel.get("rows", []) if isinstance(sel, dict) else getattr(sel, "rows", [])

            prev_ask_key = "prev_ask_selected_row"
            if st.session_state.get("show_full_resume_candidate"):
                popup_full_resume(st.session_state["show_full_resume_candidate"])
            elif selected_rows_ask:
                row_idx = selected_rows_ask[0]
                if selected_rows_ask != st.session_state.get(prev_ask_key):
                    st.session_state[prev_ask_key] = selected_rows_ask
                    if 0 <= row_idx < len(shown):
                        popup_profile(shown[row_idx])
            else:
                st.session_state[prev_ask_key] = []

elif nav == "Fields":
    fields = sorted({person.get("field") or "Unspecified" for person in people})
    if not fields:
        st.info("Index the screening CSV to browse fields.")
    else:
        st.write("Choose a field and experience band, then **click any candidate row in the table** to view their full profile.")
        picked = st.radio("Field", fields, horizontal=True, key="field_pick")
        selected_levels = st.multiselect(
            "Experience level",
            LEVELS,
            default=LEVELS,
            key="field_levels",
            help="Fresher: 0–3 years. Mid-level: 3–6 years. Senior: 6+ years.",
        )
        details = field_details(picked) if picked else {"group": "", "people": []}
        filtered = [item for item in details["people"] if _level_of(item["profile"]) in (selected_levels or LEVELS)]
        level_counts = Counter(_level_of(item["profile"]) for item in details["people"])
        mix = ", ".join(f"{level_counts.get(name, 0)} {name}" for name in LEVELS)
        st.info(f"{picked} — showing {len(filtered)} of {len(details['people'])}. {mix}.")
        if not filtered:
            st.warning("No candidates in those experience levels. Change the filter.")
        else:
            # Summary table with interactive row selection
            event = st.dataframe(
                _compact_table(filtered),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=f"field_table_{picked}",
            )

            # Pop up candidate profile modal when a row is clicked
            selected_rows = []
            if event and hasattr(event, "selection"):
                sel = event.selection
                selected_rows = sel.get("rows", []) if isinstance(sel, dict) else getattr(sel, "rows", [])

            prev_field_key = f"prev_field_selected_{picked}"
            if st.session_state.get("show_full_resume_candidate"):
                popup_full_resume(st.session_state["show_full_resume_candidate"])
            elif selected_rows:
                row_idx = selected_rows[0]
                if selected_rows != st.session_state.get(prev_field_key):
                    st.session_state[prev_field_key] = selected_rows
                    if 0 <= row_idx < len(filtered):
                        popup_profile(filtered[row_idx])
            else:
                st.session_state[prev_field_key] = []

            # If redirected from upload with a target candidate, open popup
            if not st.session_state.get("show_full_resume_candidate") and st.session_state.get("field_selected"):
                target_name = st.session_state.pop("field_selected")
                matched = next((item for item in filtered if item["profile"]["candidate"] == target_name), None)
                if matched:
                    popup_profile(matched)

else:
    st.write("Upload a PDF, DOCX, or TXT resume. It is filed into a screening field, or **Unspecified** if nothing matches.")
    files = st.file_uploader("Resumes", type=["pdf", "docx", "txt"], accept_multiple_files=True)
    manual_name = st.text_input("Candidate name override (optional)")

    # Check for duplicate candidate uploads immediately
    upload_sig = (tuple(f"{f.name}_{f.size}" for f in files), (manual_name or "").strip()) if files else ()
    if files and upload_sig != st.session_state.get("last_scanned_upload_sig"):
        st.session_state["last_scanned_upload_sig"] = upload_sig
        st.session_state.pop("duplicate_action_chosen", None)
        found_duplicates = []
        for uploaded in files:
            path = save_upload(uploaded.name, uploaded.getvalue())
            text_preview = load_resume(str(path))
            candidate_name = (manual_name or "").strip() or guess_candidate_name(text_preview, path.name)
            if find_existing(candidate_name, filename=path.name):
                found_duplicates.append(candidate_name)
        if found_duplicates:
            st.session_state["detected_duplicates"] = found_duplicates
            duplicate_dialog(found_duplicates)
        else:
            st.session_state.pop("detected_duplicates", None)
    elif not files:
        st.session_state.pop("last_scanned_upload_sig", None)
        st.session_state.pop("detected_duplicates", None)
        st.session_state.pop("duplicate_action_chosen", None)

    if st.button("Index uploads", type="primary", disabled=not files):
        dups = st.session_state.get("detected_duplicates", [])
        if dups and "duplicate_action_chosen" not in st.session_state:
            duplicate_dialog(dups)
        else:
            action = st.session_state.get("duplicate_action_chosen", "Update candidate profile (replace existing)")
            update_flag = action.startswith("Update")
            ingested = []
            for uploaded in files:
                path = save_upload(uploaded.name, uploaded.getvalue())
                text_preview = load_resume(str(path))
                candidate_name = (manual_name or "").strip() or guess_candidate_name(text_preview, path.name)
                existing = find_existing(candidate_name, filename=path.name)

                if existing and not update_flag:
                    st.info(f"ℹ️ Kept existing profile for **{candidate_name}** (upload skipped as duplicate).")
                    continue

                with st.spinner(f"Scanning {uploaded.name}…"):
                    resume = ingest_path(
                        str(path),
                        candidate_name=manual_name or None,
                        update_existing=update_flag,
                    )
                ingested.append(resume)
                status_text = "Updated" if existing else "Filed"
                st.success(
                    f"✅ **{resume.name}** {status_text.lower()} under **{resume.field or 'Unspecified'}** "
                    f"({resume.title}). {resume.chunk_count} chunks indexed."
                )

            if ingested:
                st.session_state["upload_ingested"] = ingested
                last = ingested[-1]
                st.session_state["redirect_nav"] = "Fields"
                st.session_state["redirect_field_pick"] = last.field or "Unspecified"
                st.session_state["field_levels"] = LEVELS
                st.session_state["field_selected"] = last.name
                st.rerun()

    # Show details of the last batch of uploaded resumes (before redirect triggers)
    ingested_preview = st.session_state.get("upload_ingested", [])
    if ingested_preview:
        st.divider()
        st.subheader("📄 Last Uploaded Resume Details")
        for resume in ingested_preview:
            with st.expander(f"**{resume.name}** — {resume.field or 'Unspecified'}", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Field", resume.field or "Unspecified")
                c2.metric("Title", resume.title or "—")
                c3.metric("AI Score", resume.ai_score or "—")
                c4.metric("Current Salary", resume.salary or "—")
                if resume.skills:
                    st.write(f"**Skills:** {', '.join(resume.skills)}")
                st.caption(f"{resume.chunk_count} chunks indexed · filename: {resume.filename}")
        if st.button("Go to Fields →", type="primary"):
            st.session_state["upload_ingested"] = []
            st.rerun()

    st.caption(f"Dataset file: {CSV_PATH.name}" + (" found" if CSV_PATH.exists() else " missing"))
    if SAMPLE_DIR.exists() and st.button("Index sample txt resumes"):
        for sample in sorted(SAMPLE_DIR.glob("*.txt")):
            resume = ingest_path(str(sample))
            st.success(f"{resume.name}: filed under {resume.field or 'Unspecified'}")
        st.rerun()
