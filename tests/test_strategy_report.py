"""Tests for the strategy report: parsing, validation, rendering, and the
Streamlit tab end to end with the Claude call stubbed out.

Run with: python -m pytest tests/
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import strategy_report  # noqa: E402

FIXTURE = (ROOT / "tests" / "fixtures" / "rush_me_report.json").read_text()


def test_parse_normalizes_loose_fields():
    report = strategy_report.parse_report("```json\n" + FIXTURE + "\n```")
    assert report["channel_plan"][2]["priority"] == "primary"
    community = report["hashtags"]["groups"][3]["tags"]
    assert community[0] == "#NewToCanada"
    assert "#BuildingWealth" in community
    assert strategy_report.validate_report(report) == []


def test_truncated_response_is_salvaged():
    # Cut the fixture off mid-string inside actions_30_day, like a max_tokens stop.
    cut = FIXTURE[: FIXTURE.index("Publish your second content series") + 10]
    report = strategy_report.parse_report(cut, truncated=True)
    assert report["business_name"] == "Rush Me Financial"
    assert len(report["insights"]) == 4
    # The step being written when the cut happened keeps its complete fields.
    assert len(report["actions_30_day"]) == 4
    assert "detail" not in report["actions_30_day"][3]
    assert report["validation_questions"] == []
    assert "No validation questions." in strategy_report.validate_report(report)


def test_untruncated_garbage_still_raises():
    import pytest
    with pytest.raises(json.JSONDecodeError):
        strategy_report.parse_report('{"business_name": "x", ', truncated=False)


def test_validate_flags_missing_sections():
    report = strategy_report.normalize_report({"insights": [{"title": "x"}]})
    issues = strategy_report.validate_report(report)
    assert any("Expected 4 strategic insights" in i for i in issues)
    assert any("Channel plan is empty" in i for i in issues)
    assert any("Core profile" in i for i in issues)


def test_validate_flags_bad_priority_and_tag_stuffing():
    data = json.loads(FIXTURE)
    data["channel_plan"][0]["priority"] = "urgent"
    data["hashtags"]["combos"][0]["tags"] += ["#A", "#B"]
    issues = strategy_report.validate_report(strategy_report.normalize_report(data))
    assert any("priority 'urgent'" in i for i in issues)
    assert any("more than 5" in i for i in issues)


def test_html_has_all_six_sections_and_escapes():
    data = json.loads(FIXTURE)
    data["audience_tags"].append("<script>alert(1)</script>")
    page = strategy_report.report_to_html(strategy_report.normalize_report(data), month_label="October 2026")
    for heading in ["01 &mdash; Target audience", "02 &mdash; Strategic insights", "03 &mdash; Channel plan",
                    "04 &mdash; LinkedIn hashtags", "05 &mdash; Immediate actions", "06 &mdash; To sharpen this further"]:
        assert heading in page
    assert "Four things that change your approach" in page
    assert "Built from your brief &middot; Rush Me Financial" in page
    transcript_page = strategy_report.report_to_html(strategy_report.normalize_report(data), source_type="transcript")
    assert "Built from your discovery call &middot; Rush Me Financial" in transcript_page
    assert "<script>" not in page


def test_markdown_lists_every_channel():
    report = strategy_report.parse_report(FIXTURE)
    md = strategy_report.report_to_markdown(report)
    for row in report["channel_plan"]:
        assert row["channel"] in md


def test_prompt_contains_source_and_business():
    prompt = strategy_report.build_report_prompt("Some transcript text", "Rush Me Financial")
    assert "Rush Me Financial" in prompt and "Some transcript text" in prompt
    assert '"validation_questions"' in prompt
    assert "free text" in prompt
    transcript_prompt = strategy_report.build_report_prompt("Some transcript text", "", "transcript")
    assert "discovery call transcript" in transcript_prompt


def test_short_free_text_is_accepted():
    text = "Accounting firm in Toronto serving incorporated trades businesses; clients come by word of mouth."
    assert strategy_report.validate_source_input(text)[0]


def test_source_length_limits():
    assert not strategy_report.validate_source_input("too short")[0]
    assert strategy_report.validate_source_input("x" * 18000)[0]
    assert not strategy_report.validate_source_input("x" * (strategy_report.MAX_SOURCE_LENGTH + 1))[0]


def test_app_tab_renders_report_with_stubbed_claude():
    from streamlit.testing.v1 import AppTest

    # Stub the Anthropic client before app.py runs, so the real script
    # renders top to bottom without network access or an API key.
    at = AppTest.from_string(
        "import sys, json\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "import strategy_report, anthropic\n"
        f"FIXTURE = {FIXTURE!r}\n"
        "class _Msgs:\n"
        "    def create(self, **kw):\n"
        "        class U: input_tokens = 5000; output_tokens = 3000\n"
        "        class B: type = 'text'; text = FIXTURE\n"
        "        class R: usage = U; content = [B]; stop_reason = 'end_turn'\n"
        "        return R\n"
        "class _Client:\n"
        "    def __init__(self, *a, **k): self.messages = _Msgs()\n"
        "anthropic.Anthropic = _Client\n"
        f"exec(compile(open({str(ROOT / 'app.py')!r}).read(), 'app.py', 'exec'))\n",
        default_timeout=30,
    )
    at.run()
    transcript = "We are a two-person bookkeeping firm for incorporated contractors in Ontario."
    at.text_input(key="report_business").input("Rush Me Financial")
    at.text_area(key="report_text").input(transcript)
    next(b for b in at.button if b.label == "Build strategy report").click().run()
    assert not at.exception
    headers = [h.value for h in at.header] + [s.value for s in at.subheader]
    assert "Audience & Channel Strategy: Rush Me Financial" in headers
    for section in ["01 Target audience", "02 Strategic insights", "03 Channel plan", "04 LinkedIn hashtags", "05 Next 30 days", "06 To sharpen this further"]:
        assert section in headers
    assert not at.warning or all("Expected" not in w.value for w in at.warning)
