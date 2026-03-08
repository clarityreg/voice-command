"""Tests for the ProjectResolver — fuzzy project name matching."""

from clarity_backend.voice.project_resolver import ProjectResolver, ResolveResult


SAMPLE_PROJECTS = {
    "acme": {"id": "proj-1", "name": "Acme Corp", "identifier": "ACME"},
    "clarity": {"id": "proj-2", "name": "Clarity Regulatory", "identifier": "CLR"},
    "widgets": {"id": "proj-3", "name": "Widgets Inc", "identifier": "WDG"},
    "internal": {"id": "proj-4", "name": "Internal Tools", "identifier": "INT"},
}


class TestExactMatch:
    def test_exact_alias(self):
        r = ProjectResolver(SAMPLE_PROJECTS)
        result = r.resolve("acme")
        assert result.project_id == "proj-1"
        assert result.method == "exact"
        assert result.confidence == 1.0

    def test_exact_alias_case_insensitive(self):
        r = ProjectResolver(SAMPLE_PROJECTS)
        result = r.resolve("ACME")
        assert result.project_id == "proj-1"

    def test_exact_full_name(self):
        r = ProjectResolver(SAMPLE_PROJECTS)
        result = r.resolve("Acme Corp")
        assert result.project_id == "proj-1"
        assert result.method == "exact"

    def test_exact_full_name_case_insensitive(self):
        r = ProjectResolver(SAMPLE_PROJECTS)
        result = r.resolve("clarity regulatory")
        assert result.project_id == "proj-2"


class TestSubstringMatch:
    def test_partial_name(self):
        r = ProjectResolver(SAMPLE_PROJECTS)
        result = r.resolve("widget")
        assert result.project_id == "proj-3"
        assert result.method in ("substring", "fuzzy")

    def test_partial_name_longer(self):
        r = ProjectResolver(SAMPLE_PROJECTS)
        result = r.resolve("internal tools project")
        assert result.project_id == "proj-4"
        assert result.method in ("substring", "fuzzy")


class TestFuzzyMatch:
    def test_typo_in_name(self):
        r = ProjectResolver(SAMPLE_PROJECTS)
        result = r.resolve("widgts")
        assert result.project_id == "proj-3"
        assert result.method == "fuzzy"
        assert result.confidence >= 0.6

    def test_close_spoken_name(self):
        r = ProjectResolver(SAMPLE_PROJECTS)
        result = r.resolve("acme corp")
        assert result.project_id == "proj-1"


class TestNoMatch:
    def test_unrelated_name(self):
        r = ProjectResolver(SAMPLE_PROJECTS)
        result = r.resolve("banana factory")
        assert result.project_id is None
        assert result.method == "none"

    def test_empty_string(self):
        r = ProjectResolver(SAMPLE_PROJECTS)
        result = r.resolve("")
        assert result.project_id is None

    def test_empty_projects(self):
        r = ProjectResolver({})
        result = r.resolve("acme")
        assert result.project_id is None


class TestResolveResult:
    def test_default_values(self):
        r = ResolveResult()
        assert r.project_id is None
        assert r.project_name is None
        assert r.confidence == 0.0
        assert r.alternatives == []
        assert r.method == "none"
