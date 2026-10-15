"""Source checks for the Altium timer pump; native lifecycle is tested manually."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1] / "scripts" / "altium"


def source(name: str) -> str:
    text = (ROOT / name).read_text(encoding="utf-8-sig")
    return re.sub(r"\{.*?\}|//[^\n]*", "", text, flags=re.S)


def routine(text: str, name: str) -> str:
    match = re.search(
        rf"(?:Procedure|Function) {name}\b.*?(?=\n(?:Procedure|Function) |\Z)",
        text, re.S,
    )
    assert match, f"Missing routine: {name}"
    return match.group(0)


def test_entry_point_returns_to_altium_message_loop():
    dispatcher = source("Dispatcher.pas")
    start = routine(dispatcher, "StartMCPServer")
    assert "StartMCPPump(0);" in start
    assert "While Running" not in dispatcher
    assert "Application.ProcessMessages" not in dispatcher


def test_timer_event_is_bound_to_its_own_form():
    form = source("StatusForm.pas")
    dfm = (ROOT / "StatusForm.dfm").read_text(encoding="utf-8-sig")
    assert "object tmr_Poll: TTimer" in dfm
    assert "OnTimer = tmr_PollTimer" in dfm
    assert "Procedure tmr_PollTimer(Sender : TObject);" in form
    assert "tmr_MCP" not in dfm


def test_tick_prevents_reentry_and_observes_shutdown():
    tick = routine(source("StatusForm.pas"), "tmr_PollTimer")
    assert "If PumpInTick Then Exit;" in tick
    assert "PumpInTick := True;" in tick
    assert "PumpInTick := False;" in tick
    assert "If Client.IsQuitting Then" in tick
    assert "PumpQuitting := True;" in tick
    assert "If FileExists(PumpStopPath) Then" in tick
    assert "If Not Running Then" in tick
    assert "Sleep(" not in tick


def test_finalise_disables_timer_and_skips_ui_on_host_exit():
    finalise = routine(source("StatusForm.pas"), "FinalisePump")
    assert finalise.index("tmr_Poll.Enabled := False") < finalise.index("HideStatusForm(0)")
    assert finalise.index("If PumpQuitting Then Exit;") < finalise.index("HideStatusForm(0)")
    assert "CleanupMCPServer(0)" not in finalise
    assert "Application.ProcessMessages" not in finalise


def test_close_finalises_even_if_hidden_form_stops_ticking():
    form = source("StatusForm.pas")
    assert "FinalisePump(0);" in routine(form, "StatusFormClose")
    assert "Running := False;" in routine(form, "btn_DetachClick")


def test_script_revision_is_pinned_for_cache_detection():
    assert "SCRIPT_VERSION = '2026.10.14.5';" in source("Main.pas")
