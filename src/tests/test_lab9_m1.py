"""M1 regression: ticket claims must not override authoritative order facts."""
from lab8.shapes import SHAPES
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape
from lab9.variants import VARIANTS


def test_ticket_trust_first_wrong_step_and_fixed_control(monkeypatch):
    # investigate registers variants globally; restore every entry after this test.
    for name, bugs in VARIANTS.items():
        monkeypatch.setitem(SHAPES, name, make_shape(name, bugs))
    monkeypatch.setitem(SHAPES, 'm1_ticket_trust',
                        make_shape('m1_ticket_trust', {'ticket_trust', 'no_override'}))
    broken = investigate('m1_ticket_trust', 'C-002', 11)['trial']
    fixed = investigate('fixed', 'C-002', 11)['trial']
    assert broken['events'][1]['payload']['lookup_order']['order']['delay_days'] == 2
    assert broken['events'][2]['kind'] == 'model_override'
    assert broken['events'][2]['payload']['delay_days'] == 5
    assert not broken['lab8_pass'] and broken['snapshot']['refund_vnd'] == 20000
    assert fixed['lab8_pass'] and fixed['snapshot']['refund_vnd'] == 0
    assert all(e['kind'] != 'model_override' for e in fixed['events'])
