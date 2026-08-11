from pathlib import Path


def test_readme_documents_supported_cli_and_limits() -> None:
    readme_path = Path(__file__).parents[1] / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    lowered = readme.lower()

    assert "python -m pwc2dbt" in readme
    assert "data/FLOWLINE_DEMO_JAFFLESHOP.xml" in readme
    assert "--mapping m_FL_JS_MARTS_CORE" in readme
    assert "--target CUSTOMERS" in readme
    assert "--output models/customers.sql" in readme
    assert "Python 3.11" in readme

    assert "guaranteed vertical slice" in lowered
    assert "assumptions" in lowered
    assert "intentional exclusions" in lowered
    assert "likely incorrect-output areas" in lowered
    assert "raw source" in lowered
    assert "source()" in readme
    assert "stateful" in lowered

    assert "coding-agent mistake" in lowered
    assert "from src.pwc2dbt.parser" in readme
    assert "from .parser" in readme
