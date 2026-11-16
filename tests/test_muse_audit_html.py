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


def test_muse_audit_supports_adding_reviewer_entities():
    html = AUDIT_HTML.read_text(encoding="utf-8")

    assert 'id="addEntityDialog"' in html
    assert 'id="btnAddEntity"' in html
    assert 'id="btnRemoveCustom"' in html
    assert 'id="addDocSelect"' in html
    assert 'id="addTextInput"' in html
    assert 'id="addOccurrenceSelect"' in html
    assert 'id="addLabelSelect"' in html
    assert 'value="custom">Adicionadas pelo revisor</option>' in html
    assert 'id="selectionHint"' in html
    assert "data-src-start=" in html
    for function in (
        "function openAddEntityDialog(",
        "function findOccurrences(",
        "function appendCustomEntity(",
        "function restoreCustomEntities(",
        "function removeCurrentCustomEntity(",
        "function confirmAddEntity(",
        "function getDocSelection(",
        "function addEntityFromSelection(",
    ):
        assert function in html
    assert "custom_entities: collectCustomEntities()" in html
    assert 'origin: custom ? "custom" : "muse"' in html
