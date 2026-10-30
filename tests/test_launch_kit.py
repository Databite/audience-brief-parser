"""Tests for the channel launch kit and the dated, measurable strategy plan.

Run with: python -m pytest tests/
"""
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import launch_kit  # noqa: E402
import strategy_report  # noqa: E402

KIT_FIXTURE = (ROOT / "tests" / "fixtures" / "advisor_linkedin_kit.json").read_text()
REPORT_FIXTURE = (ROOT / "tests" / "fixtures" / "advisor_report.json").read_text()


def test_parse_kit_is_complete():
    kit = launch_kit.parse_kit("```json\n" + KIT_FIXTURE + "\n```")
    assert launch_kit.validate_kit(kit) == []
    assert launch_kit.kit_title(kit) == "LinkedIn Launch Kit: Maple Advisory Group"


def test_validate_flags_ads_without_qualifying_questions():
    data = json.loads(KIT_FIXTURE)
    data["lead_form"] = {}
    data["success_measures"] = []
    issues = launch_kit.validate_kit(launch_kit.normalize_kit(data))
    assert any("no qualifying questions" in i for i in issues)
    assert "No success measures." in issues


def test_organic_kit_without_ads_is_valid():
    data = json.loads(KIT_FIXTURE)
    data["ads"], data["lead_form"], data["budget"] = [], None, None
    kit = launch_kit.normalize_kit(data)
    assert launch_kit.validate_kit(kit) == []
    assert "## Lead form" not in launch_kit.kit_to_markdown(kit)


def test_truncated_kit_is_salvaged():
    cut = KIT_FIXTURE[: KIT_FIXTURE.index("Create a LinkedIn Campaign Manager")]
    kit = launch_kit.parse_kit(cut, truncated=True)
    assert len(kit["posts"]) == 2
    assert "No success measures." in launch_kit.validate_kit(kit)


def test_kit_renders_and_escapes():
    data = json.loads(KIT_FIXTURE)
    data["posts"][0]["title"] = "<script>alert(1)</script>"
    kit = launch_kit.normalize_kit(data)
    page = launch_kit.kit_to_html(kit, month_label="December 2026")
    assert "<script>" not in page
    for text in ["Checklist", "Ready to paste", "Lead form", "Qualifies if: 10+ years", "Stop rule", "When someone responds"]:
        assert text in page
    md = launch_kit.kit_to_markdown(kit)
    assert "- [ ] **Dec 1:**" in md and "Qualifies if: Yes or planning to" in md


def test_kit_prompt_carries_channel_dates_and_budget():
    prompt = launch_kit.build_kit_prompt("Strategy text", "LinkedIn", "Maple Advisory Group", datetime.date(2026, 12, 1),
                                         "investment season Dec-Feb", "$300-500/month", "travelling in November")
    for text in ["LinkedIn", "Maple Advisory Group", "December 1, 2026", "investment season Dec-Feb", "$300-500/month", "travelling in November", "qualifies_if"]:
        assert text in prompt


def test_report_prompt_uses_dates_and_success_measures():
    prompt = strategy_report.build_report_prompt("notes", "", "free_text", datetime.date(2026, 11, 2), "Diwali Nov 8")
    assert "Monday, November 2, 2026" in prompt and "Diwali Nov 8" in prompt
    assert '"success_measure"' in prompt
    assert "do not assume customers will refer" in prompt
    assert "At least one insight should turn" not in prompt
    undated = strategy_report.build_report_prompt("notes")
    assert '"Week 1"' in undated


def test_report_flags_missing_success_measure():
    data = json.loads(REPORT_FIXTURE)
    del data["channel_plan"][0]["success_measure"]
    issues = strategy_report.validate_report(strategy_report.normalize_report(data))
    assert "Channel 'LinkedIn' has no success measure." in issues
    md = strategy_report.report_to_markdown(strategy_report.normalize_report(json.loads(REPORT_FIXTURE)))
    assert "| Success measure |" in md and "*Success: Headline updated" in md


def test_app_builds_kit_from_report_with_stubbed_claude():
    from streamlit.testing.v1 import AppTest

    # Stub Anthropic: the report prompt gets the report, the kit prompt the kit.
    at = AppTest.from_string(
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "import anthropic\n"
        f"RESPONSES = [{REPORT_FIXTURE!r}, {KIT_FIXTURE!r}]\n"
        "class _Msgs:\n"
        "    def create(self, **kw):\n"
        "        text = RESPONSES[1 if 'launch kit' in kw['messages'][0]['content'] else 0]\n"
        "        class U: input_tokens = 5000; output_tokens = 3000\n"
        "        class B: type = 'text'\n"
        "        B.text = text\n"
        "        class R: usage = U; content = [B]; stop_reason = 'end_turn'\n"
        "        return R\n"
        "class _Client:\n"
        "    def __init__(self, *a, **k): self.messages = _Msgs()\n"
        "anthropic.Anthropic = _Client\n"
        f"exec(compile(open({str(ROOT / 'app.py')!r}).read(), 'app.py', 'exec'))\n",
        default_timeout=30,
    )
    at.run()
    assert [t.label for t in at.tabs][:3] == ["Strategy report", "Launch kit", "For agencies"]
    at.text_area(key="report_text").input("A financial advisor in Ontario who gets clients by referral and wants LinkedIn leads.")
    next(b for b in at.button if b.label == "Build strategy report").click().run()
    assert not at.exception
    at.selectbox(key="kit_channel_pick").select("LinkedIn")
    at.text_input(key="kit_budget").input("$400 for December")
    next(b for b in at.button if b.label == "Build launch kit").click().run()
    assert not at.exception
    headers = [h.value for h in at.header] + [s.value for s in at.subheader]
    assert "LinkedIn Launch Kit: Maple Advisory Group" in headers
    for section in ["Checklist", "Posts", "Ads", "Lead form", "Targeting and budget", "Reply scripts"]:
        assert section in headers
