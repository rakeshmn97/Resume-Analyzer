from core.classifier import classify_field, profile_from_text
from core.loader import load_resume


def test_rakesh_style_resume_maps_to_data_scientist():
    text = (
        "RAKESH M N\n"
        "PROFESSIONAL SUMMARY\n"
        "Results-driven Data Analyst and AI/ML Engineer with an MSc in Business Analytics. "
        "Python, SQL, Scikit-Learn, Pandas, NumPy, Tableau, Power BI, Django, FastAPI, React.\n"
        "EDUCATION\nDublin Business School — MSc in Business Analytics\n"
    )
    field, title, score = classify_field(text)
    assert field == "Data Scientist"
    assert score >= 8
    profile = profile_from_text(text, "rakesh.docx", "RAKESH M N")
    assert profile["field"] == "Data Scientist"
    assert "python" in profile["skills_line"].lower()
    assert "Bengaluru" not in profile["education"]
    assert "MSc" in profile["education"] or "Business Analytics" in profile["education"]
    assert profile["level"] == "Fresher"


def test_experience_bands():
    from core.classifier import experience_level

    assert experience_level(0) == "Fresher"
    assert experience_level(3) == "Fresher"
    assert experience_level(4) == "Mid-level"
    assert experience_level(6) == "Mid-level"
    assert experience_level(7) == "Senior"


def test_real_rakesh_cv_if_present():
    path = r"C:\Users\User\Desktop\vs aiml\Antigravity\Rakesh_MN_Professional_CV.docx"
    from pathlib import Path

    if not Path(path).exists():
        return
    text = load_resume(path)
    field, _title, _score = classify_field(text)
    assert field == "Data Scientist"
    assert "Python" in text or "python" in text.lower()
