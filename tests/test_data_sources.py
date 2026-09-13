from healthcare_ner_replication.data_sources import (
    normalize_reference_entities,
    public_reference_candidates,
)


def test_public_huggingface_candidates_are_reference_only():
    candidates = public_reference_candidates()

    assert {candidate.repository for candidate in candidates} == {
        "zefang-liu/cyberbench",
        "chairulridjal/arcspan-cyber-ner",
        "mrmoor/cyber-threat-intelligence",
        "priamai/AnnoCTR",
        "vinitvek/cybersecurityattacks",
        "ScortonAI/Cyber-Security-Breaches",
    }
    assert all(not candidate.is_original_corpus for candidate in candidates)
    assert all(candidate.role == "reference_only" for candidate in candidates)
    revisions = {candidate.repository: candidate.revision for candidate in candidates}
    assert revisions["mrmoor/cyber-threat-intelligence"] == (
        "d8783e04f46039f3624df6958dd4d34405d8c72a"
    )
    assert revisions["vinitvek/cybersecurityattacks"] == (
        "92ed82a32fcd6d1bcfae16722e9ff5a7ab50d46b"
    )
    assert revisions["ScortonAI/Cyber-Security-Breaches"] == (
        "1da6a89a887067a29fa536441d3f32dce0a5879c"
    )


def test_normalize_reference_entities_maps_mrmoor_labels_and_offsets():
    entities = normalize_reference_entities(
        [
            {"label": "identity", "start_offset": 0, "end_offset": 5},
            {"label": "attack-pattern", "start_offset": 6, "end_offset": 12},
            {"label": "vulnerability", "start_offset": 13, "end_offset": 20},
            {"label": "location", "start_offset": 21, "end_offset": 27},
            {"label": "malware", "start_offset": 28, "end_offset": 35},
        ]
    )

    assert [(span.start, span.end, span.label) for span in entities] == [
        (0, 5, "IDTY"),
        (6, 12, "ACT"),
        (13, 20, "VUL"),
        (21, 27, "LOC"),
    ]
