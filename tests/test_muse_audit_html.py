from pathlib import Path

AUDIT_HTML = Path(__file__).parents[1] / "scripts" / "validation" / "muse_audit.html"


def test_muse_audit_is_offline_and_exposes_the_protocol_labels():
    html = AUDIT_HTML.read_text(encoding="utf-8")

    assert "muse-annotation-audit" in html
    assert "<script src=" not in html
    assert "<link " not in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "WebSocket" not in html
    assert "sendBeacon" not in html
    assert "EventSource" not in html
    assert "http://" not in html
    assert "https://" not in html
    for label in ("IDTY", "ACT", "VUL", "LOC", "NONE"):
        assert f'data-label="{label}"' in html
