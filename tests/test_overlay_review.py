from scripts.validation.validate_overlay_review import apply_review

TEXT = "Acme Hospital in Ohio reported a ransomware attack by LockBit."


def _fixture():
    texts = {"doc-1": TEXT, "doc-2": "Rejected record."}
    base = {
        "doc-1": {
            "id": "doc-1",
            "keep": True,
            "entities": [
                {"start": 0, "end": 13, "label": "IDTY", "text": "Acme Hospital"},
                {"start": 17, "end": 21, "label": "IDTY", "text": "Ohio"},
                {"start": 33, "end": 43, "label": "ACT", "text": "ransomware"},
                {"start": 22, "end": 30, "label": "ACT", "text": "reported"},
            ],
        },
        "doc-2": {"id": "doc-2", "keep": False, "entities": []},
    }
    review = {
        "documents": [
            {
                "id": "doc-1",
                "reviewed": True,
                "decisions": [
                    {
                        "start": 17,
                        "end": 21,
                        "label": "IDTY",
                        "action": "relabel",
                        "new_label": "LOC",
                    },
                    {"start": 33, "end": 43, "label": "ACT", "action": "fix_span", "new_end": 50},
                    {"start": 22, "end": 30, "label": "ACT", "action": "reject"},
                ],
                "added_entities": [{"start": 54, "end": 61, "label": "IDTY", "text": "LockBit"}],
            }
        ]
    }
    return review, texts, base


def test_apply_review_applies_decisions_and_additions():
    review, texts, base = _fixture()

    errors, final, stats = apply_review(review, texts, base)

    assert errors == []
    assert [(e["text"], e["label"]) for e in final["doc-1"]["entities"]] == [
        ("Acme Hospital", "IDTY"),
        ("Ohio", "LOC"),
        ("ransomware attack", "ACT"),
        ("LockBit", "IDTY"),
    ]
    assert stats["decision_counts"] == {"relabel": 1, "fix_span": 1, "reject": 1}
    assert stats["added_label_counts"] == {"IDTY": 1}
    assert stats["base_entities"] == 4
    assert stats["final_entities"] == 4
    assert base["doc-1"]["entities"][1]["label"] == "IDTY"


def test_apply_review_rejects_decision_for_unknown_entity():
    review, texts, base = _fixture()
    review["documents"][0]["decisions"].append(
        {"start": 0, "end": 4, "label": "IDTY", "action": "reject"}
    )

    errors, _, _ = apply_review(review, texts, base)

    assert any("does not match an overlay entity" in error for error in errors)


def test_apply_review_rejects_overlap_and_text_mismatch():
    review, texts, base = _fixture()
    review["documents"][0]["added_entities"] = [
        {"start": 5, "end": 13, "label": "IDTY", "text": "Hospital"},
        {"start": 54, "end": 61, "label": "IDTY", "text": "wrong"},
    ]

    errors, _, _ = apply_review(review, texts, base)

    assert any("overlapping spans" in error for error in errors)
    assert any("text mismatch" in error for error in errors)


def test_apply_review_rejects_noop_and_invalid_actions():
    review, texts, base = _fixture()
    review["documents"][0]["decisions"] = [
        {"start": 0, "end": 13, "label": "IDTY", "action": "relabel", "new_label": "IDTY"},
        {"start": 17, "end": 21, "label": "IDTY", "action": "keep"},
    ]

    errors, _, _ = apply_review(review, texts, base)

    assert any("keeps the same label" in error for error in errors)
    assert any("invalid action" in error for error in errors)


def test_apply_review_keeps_rejected_records_empty():
    review, texts, base = _fixture()
    review["documents"].append(
        {
            "id": "doc-2",
            "reviewed": True,
            "added_entities": [{"start": 0, "end": 8, "label": "ACT", "text": "Rejected"}],
        }
    )

    errors, _, _ = apply_review(review, texts, base)

    assert any("keep=false" in error for error in errors)


def test_apply_review_leaves_unreviewed_documents_unchanged():
    _, texts, base = _fixture()

    errors, final, stats = apply_review({"documents": []}, texts, base)

    assert errors == []
    assert final["doc-1"]["entities"] == base["doc-1"]["entities"]
    assert stats["reviewed_documents"] == 0
