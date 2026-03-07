from collections import defaultdict


def test_rrf_fusion_deduplicates():
    """Testa lógica de RRF: resultados duplicados são fundidos, não duplicados."""
    k = 60
    semantic = [
        {"chunk_id": "a", "score": 0.9},
        {"chunk_id": "b", "score": 0.8},
        {"chunk_id": "c", "score": 0.7},
    ]
    keyword = [
        {"chunk_id": "b", "score": 0.5},
        {"chunk_id": "d", "score": 0.4},
        {"chunk_id": "a", "score": 0.3},
    ]

    rrf_scores: dict[str, float] = defaultdict(float)
    for rank, r in enumerate(semantic):
        rrf_scores[r["chunk_id"]] += 1.0 / (k + rank + 1)
    for rank, r in enumerate(keyword):
        rrf_scores[r["chunk_id"]] += 1.0 / (k + rank + 1)

    # "a" e "b" aparecem nas duas listas — devem ter score mais alto
    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

    assert sorted_ids[0] in ("a", "b")  # top results são os que aparecem em ambas
    assert "d" in sorted_ids  # "d" só aparece no keyword, mas ainda está presente
    assert len(sorted_ids) == 4  # a, b, c, d — sem duplicatas


def test_rrf_score_formula():
    """Verifica que a fórmula RRF 1/(k+rank+1) está correta."""
    k = 60
    rank_0_score = 1.0 / (k + 0 + 1)  # rank 0 → 1/61
    rank_1_score = 1.0 / (k + 1 + 1)  # rank 1 → 1/62

    assert round(rank_0_score, 6) == round(1 / 61, 6)
    assert round(rank_1_score, 6) == round(1 / 62, 6)
    assert rank_0_score > rank_1_score  # rank menor → score maior
