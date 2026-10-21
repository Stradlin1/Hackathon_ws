import pytest

from evaluate import summarize


def test_summarize_counts_top1_top5_and_mrr():
    results = [{"rank": 1}, {"rank": 2}, {"rank": None}, {"rank": 5}]
    summary = summarize(results)
    assert summary["pairs"] == 4
    assert summary["top1"] == 1
    assert summary["top5"] == 3
    assert summary["mrr"] == pytest.approx(0.425)
    assert summary["missed"] == 3


def test_summarize_empty_results():
    assert summarize([]) == {"pairs": 0, "top1": 0, "top5": 0, "mrr": 0.0, "missed": 0}
