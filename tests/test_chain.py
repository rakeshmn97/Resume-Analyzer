from core.chunker import chunk_text
from core.embedder import HashEmbedder
from core.llm_chain import analyse, answer_question, rank_against_job
from core.vector_store import add_chunks, clear_store


def _index_pair():
    clear_store()
    embedder = HashEmbedder()
    priya = (
        "Priya Sharma\n\nSkills:\nPython, AWS, Docker, SQL, machine learning, PyTorch.\n\n"
        "Experience:\nMachine learning engineer deploying models on AWS with Docker."
    )
    arjun = (
        "Arjun Mehta\n\nSkills:\nReact, TypeScript, JavaScript, communication.\n\n"
        "Experience:\nFrontend engineer at a startup building React products."
    )
    add_chunks(chunk_text(priya, "priya.txt", "Priya Sharma"), embedder)
    add_chunks(chunk_text(arjun, "arjun.txt", "Arjun Mehta"), embedder)


def test_local_answer_stays_on_retrieved_candidate():
    _index_pair()
    result = analyse("Who knows Python and AWS?", n_results=4)
    assert result.mode == "local"
    assert result.sources
    assert result.sources[0].candidate == "Priya Sharma"
    assert "react" not in result.skills_found
    assert "python" in result.skills_found


def test_job_match_score_and_gaps():
    _index_pair()
    job = "Need Python, AWS, Docker, SQL, and React."
    ranked = rank_against_job(job, limit=4)
    assert [row.candidate for row in ranked][0] == "Priya Sharma"
    assert ranked[0].match_score > ranked[1].match_score
    priya = next(row for row in ranked if row.candidate == "Priya Sharma")
    assert "react" in priya.missing_skills
    assert "python" in priya.skills_found


def _with_role(text: str, filename: str, name: str, field: str, title: str):
    chunks = chunk_text(text, filename, name)
    for chunk in chunks:
        chunk["metadata"]["field"] = field
        chunk["metadata"]["title"] = title
    return chunks


def test_rank_keeps_unrelated_fields_below_the_matching_field():
    clear_store()
    embedder = HashEmbedder()
    nurse = (
        "Amina Khan\nField: Nursing\nTitle: ICU Nurse\n\nSkills:\n"
        "Patient care, ICU, medication administration, ward rounds.\n\n"
        "Experience:\nICU nurse responsible for patient care and medication administration."
    )
    engineer = (
        "Arjun Mehta\nField: Software\nTitle: Frontend Engineer\n\nSkills:\n"
        "React, TypeScript, JavaScript.\n\n"
        "Experience:\nFrontend engineer building React products."
    )
    add_chunks(_with_role(nurse, "amina.txt", "Amina Khan", "Nursing", "ICU Nurse"), embedder)
    add_chunks(_with_role(engineer, "arjun.txt", "Arjun Mehta", "Software", "Frontend Engineer"), embedder)
    ranked = rank_against_job(
        "Hiring an ICU nurse for patient care and medication administration.",
        limit=5,
    )
    assert ranked[0].candidate == "Amina Khan"
    assert ranked[0].field == "Nursing"
    assert ranked[0].match_score > ranked[1].match_score


def test_rank_teacher_query_returns_teachers_first():
    clear_store()
    embedder = HashEmbedder()
    teacher = (
        "Meera Iyer\nField: Teaching\nTitle: Secondary School Teacher\n\nSkills:\n"
        "Lesson planning, classroom management, curriculum.\n"
    )
    nurse = (
        "Amina Khan\nField: Nursing\nTitle: ICU Nurse\n\nSkills:\n"
        "Patient care, ICU, medication administration.\n"
    )
    add_chunks(_with_role(teacher, "meera.txt", "Meera Iyer", "Teaching", "Secondary School Teacher"), embedder)
    add_chunks(_with_role(nurse, "amina.txt", "Amina Khan", "Nursing", "ICU Nurse"), embedder)
    ranked = rank_against_job("teacher", limit=5)
    assert ranked[0].candidate == "Meera Iyer"
    assert ranked[0].match_score == 100
    assert ranked[1].match_score == 0


def test_ask_returns_five_teachers():
    clear_store()
    embedder = HashEmbedder()
    for index in range(6):
        name = f"Teacher {index}"
        text = (
            f"{name}\nField: Teaching\nTitle: Secondary School Teacher\n\n"
            "Skills:\nLesson planning, classroom management, curriculum.\n"
        )
        add_chunks(
            _with_role(text, f"t{index}.txt", name, "Teaching", "Secondary School Teacher"),
            embedder,
        )
    answers = answer_question("teacher", minimum=5)
    assert len(answers) >= 5
    assert all("Teacher" in answer.sources[0].candidate for answer in answers[:5])
