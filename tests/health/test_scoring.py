from __future__ import annotations

from netscanx.health.models import HealthCheck, HealthReport


def test_all_ok_keeps_score_at_100():
    report = HealthReport(target="local")
    report.add(HealthCheck(name="a", status="ok", message="fine", weight=50))
    report.add(HealthCheck(name="b", status="ok", message="fine", weight=50))
    assert report.score == 100
    assert report.summary_ok == 2


def test_error_deducts_full_weight():
    report = HealthReport(target="local")
    report.add(HealthCheck(name="a", status="error", message="bad", weight=20))
    assert report.score == 80
    assert report.summary_error == 1


def test_warning_deducts_half_weight():
    report = HealthReport(target="local")
    report.add(HealthCheck(name="a", status="warning", message="meh", weight=20))
    assert report.score == 90
    assert report.summary_warning == 1


def test_score_floors_at_zero():
    report = HealthReport(target="local")
    report.add(HealthCheck(name="a", status="error", message="bad", weight=80))
    report.add(HealthCheck(name="b", status="error", message="bad", weight=80))
    assert report.score == 0


def test_skipped_does_not_affect_score():
    report = HealthReport(target="local")
    report.add(HealthCheck(name="a", status="skipped", message="n/a", weight=20))
    assert report.score == 100
    assert report.summary_ok == 0
    assert report.summary_warning == 0
    assert report.summary_error == 0


def test_all_checks_failing_bottoms_out_local_weight_set():
    """The local check set's weights (20+15+15+20+15+15=100) are designed
    so that failing every check bottoms the score out at exactly 0."""
    report = HealthReport(target="local")
    weights = [20, 15, 15, 20, 15, 15]
    for i, w in enumerate(weights):
        report.add(HealthCheck(name=str(i), status="error", message="bad", weight=w))
    assert report.score == 0
