"""Tests for triage engine pure functions."""

from clarity_backend.triage.engine import classify_severity, generate_fingerprint


class TestGenerateFingerprint:
    def test_same_input_same_fingerprint(self):
        fp1 = generate_fingerprint("TypeError", "msg", "posthog")
        fp2 = generate_fingerprint("TypeError", "msg", "posthog")
        assert fp1 == fp2

    def test_different_input_different_fingerprint(self):
        fp1 = generate_fingerprint("TypeError", "msg-a", "posthog")
        fp2 = generate_fingerprint("TypeError", "msg-b", "posthog")
        assert fp1 != fp2

    def test_different_source_different_fingerprint(self):
        fp1 = generate_fingerprint("TypeError", "msg", "posthog")
        fp2 = generate_fingerprint("TypeError", "msg", "aikido")
        assert fp1 != fp2

    def test_returns_hex_string(self):
        fp = generate_fingerprint("TypeError", "msg", "posthog")
        assert len(fp) == 64
        int(fp, 16)  # must be valid hex


class TestClassifySeverity:
    def test_low_occurrence(self):
        assert classify_severity(1, "TypeError") == "low"

    def test_medium_occurrence(self):
        assert classify_severity(4, "TypeError") == "medium"

    def test_high_occurrence(self):
        assert classify_severity(11, "TypeError") == "high"

    def test_critical_occurrence(self):
        assert classify_severity(101, "TypeError") == "critical"

    def test_fatal_exception_is_critical(self):
        assert classify_severity(1, "FatalError") == "critical"

    def test_fatal_case_insensitive(self):
        assert classify_severity(1, "FATAL_CRASH") == "critical"
