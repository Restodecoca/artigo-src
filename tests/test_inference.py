from healthcare_ner_replication.inference import (
    MODEL_SPECS,
    canonicalize_entity_label,
    filter_model_entities,
)


def test_model_registry_points_to_the_two_public_checkpoints():
    assert MODEL_SPECS["SecureBERT-NER"].repository == "CyberPeace-Institute/SecureBERT-NER"
    assert MODEL_SPECS["SecureBERT-APTNER"].repository == "Cyber-ThreaD/SecureBERT-APTNER"
    assert MODEL_SPECS["SecureBERT-NER"].revision == "7f935a4f7db13697580c881e381bb2636dfa779a"
    assert MODEL_SPECS["SecureBERT-APTNER"].revision == "f220a5fbeb8ed9b60a516cf420fc816d9705ce7d"


def test_vulnerability_subtypes_are_explicitly_mapped_to_paper_label():
    assert canonicalize_entity_label("B-VULID") == "VUL"
    assert canonicalize_entity_label("VULNAME") == "VUL"
    assert canonicalize_entity_label("I-IDTY") == "IDTY"
    assert canonicalize_entity_label("B-MAL") is None


def test_filter_model_entities_keeps_offsets_and_discards_unselected_labels():
    raw_entities = [
        {"entity_group": "IDTY", "start": 2, "end": 10, "score": 0.9},
        {"entity_group": "VULNAME", "start": 20, "end": 31, "score": 0.8},
        {"entity_group": "MAL", "start": 40, "end": 49, "score": 0.99},
    ]

    result = filter_model_entities(raw_entities)

    assert [(span.start, span.end, span.label) for span in result] == [
        (2, 10, "IDTY"),
        (20, 31, "VUL"),
    ]
