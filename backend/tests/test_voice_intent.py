"""Tests for voice intent classification."""

from clarity_backend.voice.intent import (
    CHECK_STATUS,
    CREATE_ISSUE,
    DISMISS_ITEM,
    FIX_ITEM,
    MORNING_BRIEF,
    QUERY_ERRORS,
    QUERY_VULNS,
    SNOOZE_ITEM,
    UNKNOWN,
    classify,
)


class TestClassifyErrors:
    def test_what_errors_today(self):
        intent = classify("What errors came in today?")
        assert intent.type == QUERY_ERRORS
        assert intent.params.get("timeframe") == "24h"

    def test_any_bugs(self):
        intent = classify("Are there any bugs?")
        assert intent.type == QUERY_ERRORS

    def test_critical_errors(self):
        intent = classify("Show me critical errors")
        assert intent.type == QUERY_ERRORS
        assert intent.params.get("severity") == "critical"

    def test_failing_this_week(self):
        intent = classify("What's been failing this week?")
        assert intent.type == QUERY_ERRORS
        assert intent.params.get("timeframe") == "7d"


class TestClassifyVulns:
    def test_vulnerabilities(self):
        intent = classify("Any new vulnerabilities?")
        assert intent.type == QUERY_VULNS

    def test_security_issues(self):
        intent = classify("Are there security issues?")
        assert intent.type == QUERY_VULNS

    def test_cve(self):
        intent = classify("Any CVE reports?")
        assert intent.type == QUERY_VULNS


class TestClassifyStatus:
    def test_status(self):
        intent = classify("What's my status?")
        assert intent.type == CHECK_STATUS

    def test_overview(self):
        intent = classify("Give me an overview")
        assert intent.type == CHECK_STATUS

    def test_how_are_things(self):
        intent = classify("How are things going?")
        assert intent.type == CHECK_STATUS


class TestClassifyActions:
    def test_create_issue(self):
        intent = classify("Create an issue for item #42")
        assert intent.type == CREATE_ISSUE
        assert intent.params.get("item_id") == 42

    def test_snooze(self):
        intent = classify("Snooze item 5")
        assert intent.type == SNOOZE_ITEM
        assert intent.params.get("item_id") == 5

    def test_dismiss(self):
        intent = classify("Dismiss this one")
        assert intent.type == DISMISS_ITEM

    def test_morning_brief(self):
        intent = classify("Give me the morning brief")
        assert intent.type == MORNING_BRIEF


class TestClassifyFixItem:
    def test_fix_item_3(self):
        intent = classify("fix item 3")
        assert intent.type == FIX_ITEM
        assert intent.params.get("item_id") == 3

    def test_auto_fix_error_5(self):
        intent = classify("auto-fix error 5")
        assert intent.type == FIX_ITEM

    def test_patch_vulnerability(self):
        intent = classify("patch vulnerability #7")
        assert intent.type == FIX_ITEM
        assert intent.params.get("item_id") == 7

    def test_repair_issue(self):
        intent = classify("repair issue 12")
        assert intent.type == FIX_ITEM
        assert intent.params.get("item_id") == 12

    def test_resolve_item(self):
        intent = classify("resolve item 1")
        assert intent.type == FIX_ITEM
        assert intent.params.get("item_id") == 1


class TestClassifyEdgeCases:
    def test_empty_string(self):
        intent = classify("")
        assert intent.type == UNKNOWN
        assert intent.confidence == 0.0

    def test_unrecognized(self):
        intent = classify("Tell me a joke about cats")
        assert intent.type == UNKNOWN

    def test_confidence_for_match(self):
        intent = classify("Show errors")
        assert intent.confidence > 0.5

    def test_case_insensitive(self):
        intent = classify("SHOW ME ALL ERRORS")
        assert intent.type == QUERY_ERRORS
