"""Tests for the CLARITY_REGULATION_LIMIT intent classification and command handler."""

import os

os.environ.setdefault("DOTENV_CONFIG", "1")

from unittest.mock import AsyncMock, patch  # noqa: E402

import pytest  # noqa: E402

from clarity_backend.voice.intent import (  # noqa: E402
    CLARITY_INGREDIENT_CHECK,
    CLARITY_REGULATION_LIMIT,
    classify,
)


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


class TestRegulationLimitClassification:
    """Verify that regulation-limit phrases resolve to CLARITY_REGULATION_LIMIT."""

    def test_whats_the_limit_for_vitamin_d_in_france(self):
        intent = classify("what's the limit for vitamin D in France")
        assert intent.type == CLARITY_REGULATION_LIMIT

    def test_what_is_the_limit_of_calcium_in_uk(self):
        intent = classify("what is the limit of calcium in the UK")
        assert intent.type == CLARITY_REGULATION_LIMIT

    def test_limit_for_glucosamine_in_germany(self):
        intent = classify("limit for glucosamine in Germany")
        assert intent.type == CLARITY_REGULATION_LIMIT

    def test_limit_of_iron_in_spain(self):
        intent = classify("limit of iron in Spain")
        assert intent.type == CLARITY_REGULATION_LIMIT

    def test_confidence_is_set(self):
        intent = classify("limit for magnesium in France")
        assert intent.confidence == pytest.approx(0.85)


class TestRegulationLimitParamExtraction:
    """Verify that substance and country are extracted correctly."""

    def test_extracts_substance_vitamin_d(self):
        intent = classify("what's the limit for vitamin D in France")
        assert intent.params.get("substance") == "vitamin d"

    def test_extracts_country_france(self):
        intent = classify("what's the limit for vitamin D in France")
        assert intent.params.get("country") == "france"

    def test_extracts_substance_calcium(self):
        intent = classify("what is the limit of calcium in the UK")
        assert intent.params.get("substance") == "calcium"

    def test_extracts_country_uk(self):
        # "the UK" — the leading article is part of what the regex captures
        # after "in "; we assert "uk" is present regardless of article.
        intent = classify("what is the limit of calcium in the UK")
        assert "uk" in intent.params.get("country", "")

    def test_extracts_substance_glucosamine(self):
        intent = classify("limit for glucosamine in Germany")
        assert intent.params.get("substance") == "glucosamine"

    def test_extracts_country_germany(self):
        intent = classify("limit for glucosamine in Germany")
        assert intent.params.get("country") == "germany"

    def test_multi_word_substance(self):
        # Ensure multi-word substances like "vitamin D" are captured in full.
        intent = classify("what's the limit for omega 3 in France")
        assert intent.params.get("substance") == "omega 3"
        assert intent.params.get("country") == "france"


class TestRegulationLimitDoesNotOverreachOtherIntents:
    """Confirm that similar-but-distinct phrases still route to the correct intent."""

    def test_is_glucosamine_allowed_in_france_is_rag_query(self):
        # "is X allowed" should still hit CLARITY_RAG_QUERY (existing behaviour).
        from clarity_backend.voice.intent import CLARITY_RAG_QUERY

        intent = classify("is glucosamine allowed in France")
        assert intent.type == CLARITY_RAG_QUERY

    def test_ingredient_keyword_still_routes_to_ingredient_check(self):
        # Plain ingredient lookups without "limit" should stay on CLARITY_INGREDIENT_CHECK.
        intent = classify("ingredient retinol")
        assert intent.type == CLARITY_INGREDIENT_CHECK

    def test_substance_keyword_still_routes_to_ingredient_check(self):
        intent = classify("substance vitamin-c")
        assert intent.type == CLARITY_INGREDIENT_CHECK


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------


class TestHandleClarityRegulationLimit:
    """Unit tests for _handle_clarity_regulation_limit."""

    @pytest.fixture()
    def mock_session(self):
        """A minimal AsyncSession stand-in — the handler never touches the DB."""
        return AsyncMock()

    @pytest.fixture()
    def intent_factory(self):
        """Return a helper that builds a pre-classified Intent."""
        from clarity_backend.voice.intent import Intent

        def _make(substance: str = "vitamin D", country: str = "France") -> Intent:
            return Intent(
                type=CLARITY_REGULATION_LIMIT,
                confidence=0.85,
                params={"substance": substance, "country": country},
            )

        return _make

    @pytest.mark.asyncio
    async def test_returns_formatted_response(self, mock_session, intent_factory):
        from clarity_backend.voice.commands import _handle_clarity_regulation_limit

        mock_client = AsyncMock()
        mock_client.check_compliance = AsyncMock(return_value={"limit": "800 IU/day"})

        with patch(
            "clarity_backend.voice.commands._get_clarity_client", return_value=mock_client
        ):
            result = await _handle_clarity_regulation_limit(intent_factory(), mock_session)

        assert "vitamin D" in result["response"]
        assert "France" in result["response"]
        assert "800 IU/day" in result["response"]

    @pytest.mark.asyncio
    async def test_calls_check_compliance_with_correct_args(self, mock_session, intent_factory):
        from clarity_backend.voice.commands import _handle_clarity_regulation_limit

        mock_client = AsyncMock()
        mock_client.check_compliance = AsyncMock(return_value={"limit": "500 mg"})

        with patch(
            "clarity_backend.voice.commands._get_clarity_client", return_value=mock_client
        ):
            await _handle_clarity_regulation_limit(
                intent_factory(substance="calcium", country="Germany"), mock_session
            )

        mock_client.check_compliance.assert_awaited_once_with(
            ingredient="calcium", market="Germany"
        )

    @pytest.mark.asyncio
    async def test_falls_back_to_result_key(self, mock_session, intent_factory):
        """Handler should accept 'result' as the API key when 'limit' is absent."""
        from clarity_backend.voice.commands import _handle_clarity_regulation_limit

        mock_client = AsyncMock()
        mock_client.check_compliance = AsyncMock(return_value={"result": "Not established"})

        with patch(
            "clarity_backend.voice.commands._get_clarity_client", return_value=mock_client
        ):
            result = await _handle_clarity_regulation_limit(intent_factory(), mock_session)

        assert "Not established" in result["response"]

    @pytest.mark.asyncio
    async def test_falls_back_to_detail_key(self, mock_session, intent_factory):
        """Handler should accept 'detail' as the API key when neither 'limit' nor 'result' exist."""
        from clarity_backend.voice.commands import _handle_clarity_regulation_limit

        mock_client = AsyncMock()
        mock_client.check_compliance = AsyncMock(
            return_value={"detail": "Max 200 mcg/day"}
        )

        with patch(
            "clarity_backend.voice.commands._get_clarity_client", return_value=mock_client
        ):
            result = await _handle_clarity_regulation_limit(intent_factory(), mock_session)

        assert "Max 200 mcg/day" in result["response"]

    @pytest.mark.asyncio
    async def test_offline_fallback(self, mock_session, intent_factory):
        from clarity_backend.integrations.clarity import ClarityOfflineError
        from clarity_backend.voice.commands import _handle_clarity_regulation_limit

        mock_client = AsyncMock()
        mock_client.check_compliance = AsyncMock(side_effect=ClarityOfflineError("timeout"))

        with patch(
            "clarity_backend.voice.commands._get_clarity_client", return_value=mock_client
        ):
            result = await _handle_clarity_regulation_limit(intent_factory(), mock_session)

        assert "not available" in result["response"].lower() or "offline" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_missing_substance_prompts_user(self, mock_session):
        from clarity_backend.voice.commands import _handle_clarity_regulation_limit
        from clarity_backend.voice.intent import Intent

        intent = Intent(
            type=CLARITY_REGULATION_LIMIT,
            confidence=0.85,
            params={"substance": "", "country": "France"},
        )
        result = await _handle_clarity_regulation_limit(intent, mock_session)
        assert "substance" in result["response"].lower() or "which" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_missing_country_prompts_user(self, mock_session):
        from clarity_backend.voice.commands import _handle_clarity_regulation_limit
        from clarity_backend.voice.intent import Intent

        intent = Intent(
            type=CLARITY_REGULATION_LIMIT,
            confidence=0.85,
            params={"substance": "vitamin D", "country": ""},
        )
        result = await _handle_clarity_regulation_limit(intent, mock_session)
        assert "country" in result["response"].lower() or "market" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_data_payload_is_forwarded(self, mock_session, intent_factory):
        """The raw API response should be passed through in the 'data' key."""
        from clarity_backend.voice.commands import _handle_clarity_regulation_limit

        api_response = {"limit": "50 mg", "source": "EFSA", "updated": "2025-01"}
        mock_client = AsyncMock()
        mock_client.check_compliance = AsyncMock(return_value=api_response)

        with patch(
            "clarity_backend.voice.commands._get_clarity_client", return_value=mock_client
        ):
            result = await _handle_clarity_regulation_limit(intent_factory(), mock_session)

        assert result["data"] == api_response
