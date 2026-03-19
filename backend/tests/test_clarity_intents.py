"""Tests for Clarity App intent classification patterns."""

import os

os.environ.setdefault("DOTENV_CONFIG", "1")

import pytest  # noqa: E402

from clarity_backend.voice.intent import (  # noqa: E402
    CHECK_STATUS,
    CLARITY_COMPLIANCE,
    CLARITY_INGREDIENT_CHECK,
    CLARITY_PARKING_LOT_ADD,
    CLARITY_RAG_QUERY,
    CLARITY_RUN_EMAIL_REVIEW,
    CLARITY_SCHEDULE_STATUS,
    CLARITY_START_BLITZ,
    CLARITY_UNIFIED_INBOX,
    CLARITY_UPCOMING_ACTIONS,
    CLARITY_XP_STATUS,
    PLANE_CREATE_TASK,
    PLANE_LIST_TASKS,
    QUERY_ERRORS,
    QUERY_VULNS,
    READ_EMAILS,
    UNKNOWN,
    classify,
)


class TestClarityScheduleStatus:
    def test_schedule_status(self):
        intent = classify("What's the schedule status?")
        assert intent.type == CLARITY_SCHEDULE_STATUS

    def test_schedule_dashboard(self):
        intent = classify("Show me the schedule dashboard")
        assert intent.type == CLARITY_SCHEDULE_STATUS

    def test_product_status(self):
        intent = classify("Check product status")
        assert intent.type == CLARITY_SCHEDULE_STATUS

    def test_schedule_status_for_client_extracts_client_id(self):
        intent = classify("schedule status for novachem")
        assert intent.type == CLARITY_SCHEDULE_STATUS
        assert intent.params.get("client_id") == "novachem"

    def test_schedule_dashboard_of_client_extracts_client_id(self):
        intent = classify("schedule dashboard of acme-corp")
        assert intent.type == CLARITY_SCHEDULE_STATUS
        assert intent.params.get("client_id") == "acme-corp"


class TestClarityCompliance:
    def test_compliance_for_client(self):
        intent = classify("compliance for novachem")
        assert intent.type == CLARITY_COMPLIANCE
        assert intent.params["client_id"] == "novachem"

    def test_compliance_summary(self):
        intent = classify("Show compliance summary")
        assert intent.type == CLARITY_COMPLIANCE

    def test_show_compliance(self):
        intent = classify("show compliance")
        assert intent.type == CLARITY_COMPLIANCE

    def test_compliance_check(self):
        intent = classify("compliance check for loreal")
        assert intent.type == CLARITY_COMPLIANCE
        assert intent.params.get("client_id") == "loreal"


class TestClarityParkingLotAdd:
    def test_parking_lot_with_colon(self):
        intent = classify("parking lot: buy milk")
        assert intent.type == CLARITY_PARKING_LOT_ADD
        assert intent.params["content"] == "buy milk"

    def test_quick_note(self):
        intent = classify("quick note fix the api")
        assert intent.type == CLARITY_PARKING_LOT_ADD
        assert "fix the api" in intent.params.get("content", "")

    def test_remember_this(self):
        intent = classify("remember this: call the client")
        assert intent.type == CLARITY_PARKING_LOT_ADD
        assert intent.params["content"] == "call the client"

    def test_parking_lot_no_colon(self):
        intent = classify("add to parking lot buy milk")
        assert intent.type == CLARITY_PARKING_LOT_ADD


class TestClarityStartBlitz:
    def test_start_blitz(self):
        intent = classify("start a blitz")
        assert intent.type == CLARITY_START_BLITZ

    def test_begin_blitz(self):
        intent = classify("begin blitz session")
        assert intent.type == CLARITY_START_BLITZ

    def test_focus_session(self):
        intent = classify("start a focus session")
        assert intent.type == CLARITY_START_BLITZ

    def test_sprint_session(self):
        intent = classify("let's do a sprint session")
        assert intent.type == CLARITY_START_BLITZ


class TestClarityRunEmailReview:
    def test_review_emails(self):
        intent = classify("review my emails")
        assert intent.type == CLARITY_RUN_EMAIL_REVIEW

    def test_email_review(self):
        intent = classify("start email review")
        assert intent.type == CLARITY_RUN_EMAIL_REVIEW

    def test_triage_emails(self):
        intent = classify("triage emails")
        assert intent.type == CLARITY_RUN_EMAIL_REVIEW


class TestClarityUpcomingActions:
    def test_upcoming(self):
        intent = classify("What's upcoming?")
        assert intent.type == CLARITY_UPCOMING_ACTIONS

    def test_due_soon(self):
        intent = classify("What's due soon?")
        assert intent.type == CLARITY_UPCOMING_ACTIONS

    def test_action_points(self):
        intent = classify("Show me my action points")
        assert intent.type == CLARITY_UPCOMING_ACTIONS

    def test_action_point_singular(self):
        intent = classify("Any action point for today?")
        assert intent.type == CLARITY_UPCOMING_ACTIONS


class TestClarityRagQuery:
    def test_regulation_query(self):
        intent = classify("What are the regulations on preservatives?")
        assert intent.type == CLARITY_RAG_QUERY

    def test_regulatory_question(self):
        intent = classify("Ask about regulatory requirements for novel food")
        assert intent.type == CLARITY_RAG_QUERY

    def test_novel_food_query(self):
        intent = classify("Tell me about novel food regulations")
        assert intent.type == CLARITY_RAG_QUERY

    def test_is_allowed_query(self):
        intent = classify("is retinol allowed in germany")
        assert intent.type == CLARITY_RAG_QUERY
        assert "retinol" in intent.params.get("query", "")

    def test_query_extracts_topic(self):
        intent = classify("regulation on preservatives")
        assert intent.type == CLARITY_RAG_QUERY
        # regex captures "on preservatives" — the preposition is part of the match group
        assert "preservatives" in intent.params.get("query", "")


class TestClarityIngredientCheck:
    def test_ingredient_keyword(self):
        intent = classify("ingredient retinol")
        assert intent.type == CLARITY_INGREDIENT_CHECK
        assert intent.params["ingredient"] == "retinol"

    def test_substance_keyword(self):
        intent = classify("substance vitamin-c")
        assert intent.type == CLARITY_INGREDIENT_CHECK
        assert intent.params["ingredient"] == "vitamin-c"

    def test_allowed_in_market_via_ingredient_keyword(self):
        # "is X allowed in Y" matches the RAG pattern first (is \w+ allowed).
        # Use the "ingredient" keyword to specifically target CLARITY_INGREDIENT_CHECK.
        intent = classify("ingredient niacinamide allowed in france")
        assert intent.type == CLARITY_INGREDIENT_CHECK
        assert intent.params.get("ingredient") == "niacinamide"

    def test_allowed_in_triggers_rag_query(self):
        # Phrase "is X allowed in Y" hits CLARITY_RAG_QUERY before ingredient check.
        intent = classify("is niacinamide allowed in france")
        assert intent.type == CLARITY_RAG_QUERY

    def test_compliant_in_market_via_ingredient_keyword(self):
        # "compliant" is not in the RAG pattern, but also not in the ingredient pattern.
        # The ingredient pattern requires "allowed|compliant|permitted" plus "ingredient/substance".
        # Use the ingredient keyword form to guarantee CLARITY_INGREDIENT_CHECK.
        intent = classify("ingredient retinol compliant in germany")
        assert intent.type == CLARITY_INGREDIENT_CHECK
        assert intent.params.get("ingredient") == "retinol"


class TestClarityUnifiedInbox:
    def test_unified_inbox(self):
        intent = classify("Show unified inbox")
        assert intent.type == CLARITY_UNIFIED_INBOX

    def test_whats_urgent(self):
        intent = classify("what's urgent right now")
        assert intent.type == CLARITY_UNIFIED_INBOX

    def test_urgent_keyword(self):
        intent = classify("urgent")
        assert intent.type == CLARITY_UNIFIED_INBOX

    def test_priority_items(self):
        intent = classify("Show priority items")
        assert intent.type == CLARITY_UNIFIED_INBOX


class TestClarityXpStatus:
    def test_xp_keyword(self):
        intent = classify("How much XP do I have?")
        assert intent.type == CLARITY_XP_STATUS

    def test_streak_keyword(self):
        intent = classify("What's my streak?")
        assert intent.type == CLARITY_XP_STATUS

    def test_gamification(self):
        intent = classify("Show gamification stats")
        assert intent.type == CLARITY_XP_STATUS

    def test_how_much_xp(self):
        intent = classify("how much xp today")
        assert intent.type == CLARITY_XP_STATUS


class TestExistingIntentsUnaffected:
    def test_query_errors(self):
        intent = classify("What errors came in today?")
        assert intent.type == QUERY_ERRORS

    def test_query_vulns(self):
        intent = classify("Any new vulnerabilities?")
        assert intent.type == QUERY_VULNS

    def test_check_status(self):
        intent = classify("What's my status?")
        assert intent.type == CHECK_STATUS

    def test_plane_list_tasks(self):
        intent = classify("show my tasks")
        assert intent.type == PLANE_LIST_TASKS

    def test_plane_create_task(self):
        intent = classify("create task in acme: fix bug")
        assert intent.type == PLANE_CREATE_TASK

    def test_read_emails_does_not_capture_email_review(self):
        """'review my emails' is CLARITY_RUN_EMAIL_REVIEW, not READ_EMAILS."""
        review_intent = classify("review my emails")
        assert review_intent.type == CLARITY_RUN_EMAIL_REVIEW

    def test_read_emails_plain(self):
        intent = classify("check my inbox")
        assert intent.type == READ_EMAILS


class TestEdgeCases:
    def test_empty_string_returns_unknown(self):
        intent = classify("")
        assert intent.type == UNKNOWN
        assert intent.confidence == 0.0

    def test_whitespace_only_returns_unknown(self):
        intent = classify("   ")
        assert intent.type == UNKNOWN

    def test_unrelated_phrase_returns_unknown(self):
        intent = classify("What's the weather like today?")
        assert intent.type == UNKNOWN

    def test_confidence_on_clarity_match(self):
        intent = classify("compliance for novachem")
        assert intent.confidence == pytest.approx(0.85)

    def test_case_insensitive_classification(self):
        intent = classify("COMPLIANCE FOR NOVACHEM")
        assert intent.type == CLARITY_COMPLIANCE

    def test_parking_lot_content_extraction_colon_separator(self):
        intent = classify("add to parking lot: buy milk")
        assert intent.type == CLARITY_PARKING_LOT_ADD
        assert intent.params.get("content") == "buy milk"
