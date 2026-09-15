"""Shared search index: baseline misses (S01/S02/S03) and documented matching semantics."""

from __future__ import annotations

from validators import loader, search


def _index():
    return search.build_search_index(loader.load_registry(), loader.load_receipts())


def _ids(result):
    return [r["document"]["id"] for r in result["results"]]


def test_s01_physically_constrained_finds_object_23_via_question():
    result = search.search(_index(), "physically constrained")
    assert "SR-OBJ-000023" in _ids(result)
    hit = next(r for r in result["results"] if r["document"]["id"] == "SR-OBJ-000023")
    assert "main_question" in hit["matched_fields"]


def test_s02_author_name_and_relation_id_resolve_through_shared_index():
    index = _index()
    by_name = search.search(index, "Clement")
    authored = {o["object_id"] for o in loader.load_registry()["objects"].values() if "AUTH-0001" in o["authors"]}
    assert authored <= set(_ids(by_name))
    by_relation = search.search(index, "REL-000006")
    assert {"SR-OBJ-000031", "SR-OBJ-000023"} <= set(_ids(by_relation))
    assert "identifier" in by_relation["results"][0]["matched_fields"]


def test_all_terms_must_match_and_quotes_are_phrases():
    index = _index()
    assert _ids(search.search(index, "associative memory")) == _ids(search.search(index, "memory associative"))
    assert set(_ids(search.search(index, '"associative memory"'))) <= set(_ids(search.search(index, "associative memory")))
    assert search.search(index, "associative zzzz-no-such-term")["total"] == 0


def test_doi_and_source_title_match_even_when_not_table_columns():
    index = _index()
    doi = search.search(index, "10.5281/zenodo.22739943")
    assert "SR-OBJ-000031" in _ids(doi)
    source_title = search.search(index, "Prospective Identifiable Return")
    assert "SR-OBJ-000031" in _ids(source_title)


def test_s03_filters_combine_predictably_and_report_matched_fields():
    index = _index()
    secondary = search.search(index, "", filters={"domain": {"cognitive-science"}})
    assert secondary["total"] >= 1
    for r in secondary["results"]:
        d = r["document"]["domain"]
        assert "cognitive-science" in {d["primary"], *d["secondary"]}
    combined = search.search(index, "", filters={"domain": {"cognitive-science"}, "maturity": {"prospectively-tested"}})
    assert set(_ids(combined)) <= set(_ids(secondary))
    assert combined["filters"] == {"domain": ["cognitive-science"], "maturity": ["prospectively-tested"]}


def test_ranking_is_relevance_only_and_deterministic():
    index = _index()
    a, b = search.search(index, "return"), search.search(index, "return")
    assert _ids(a) == _ids(b)
    scores = [r["score"] for r in a["results"]]
    assert scores == sorted(scores, reverse=True)
    doc_keys = set(index["documents"][0])
    assert not {"prestige", "quality", "importance", "score", "rank"} & doc_keys
