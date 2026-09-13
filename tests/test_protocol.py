from dataclasses import replace

import pytest

from healthcare_ner_replication.protocol import default_protocol, validate_protocol


def test_default_protocol_records_the_original_study_without_claiming_exact_data_access():
    protocol = default_protocol()

    assert protocol.article_title == (
        "An Analysis of Pre-trained Models to Identify Cybersecurity Incidents "
        "Entities in the Healthcare Industry"
    )
    assert protocol.models == ("SecureBERT-NER", "SecureBERT-APTNER")
    assert protocol.entity_types == ("IDTY", "ACT", "VUL", "LOC")
    assert protocol.evaluation_modes == ("strict", "partial")
    assert protocol.collection_date == "2023-10-30"
    assert protocol.manually_annotated_documents == 60
    assert protocol.max_tokens_per_document == 400
    assert protocol.corpus_stage_counts == {
        "collected": 24_108,
        "unique_links": 15_705,
        "selected_portals": 1_449,
        "final_corpus": 1_039,
    }
    assert protocol.original_corpus_available is False


def test_protocol_validation_rejects_an_empty_model_matrix():
    protocol = replace(default_protocol(), models=())

    with pytest.raises(ValueError, match="at least one model"):
        validate_protocol(protocol)


def test_protocol_validation_rejects_counts_that_grow_after_filtering():
    protocol = replace(
        default_protocol(),
        corpus_stage_counts={
            "collected": 10,
            "unique_links": 11,
            "selected_portals": 2,
            "final_corpus": 1,
        },
    )

    with pytest.raises(ValueError, match="cannot increase"):
        validate_protocol(protocol)
