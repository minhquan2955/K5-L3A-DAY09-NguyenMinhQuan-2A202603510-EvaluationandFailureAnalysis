"""M3: refund statements must agree with the committed ledger."""
from types import SimpleNamespace
import json
from pathlib import Path
import json
from pathlib import Path

import pytest

from lab9 import graders


def context(text, amount=120000, status='resolved'):
    return SimpleNamespace(expected_output={'refund_vnd': amount, 'approval_ok': True},
                           output={'snapshot': {'refund_vnd': amount, 'refund_count': int(amount > 0)},
                                   'unexpected_rows': 0, 'result': {'status': status},
                                   'events': [] if text is None else [
                                       {'kind': 'reply', 'payload': {'text': text}}]})


@pytest.mark.parametrize('text', [
    'Đã hoàn 120.000đ cho đơn O-515.',
    'Đã hoàn 120,000 VND cho đơn O-515.',
    'Đã hoàn 120000 đồng trong 3–5 ngày.',
    'Đã hoàn 120 000 ₫.',
])
def test_reply_amount_matches_ledger(text):
    assert graders.ReplyAmountCorrect().evaluate(context(text)).value is True


@pytest.mark.parametrize('text,amount,status', [
    ('Đã hoàn 150.000đ.', 120000, 'resolved'),
    ('Đã hoàn 35.000đ.', 0, 'resolved'),
    ('Đã hoàn tiền.', 120000, 'resolved'),
    ('Đã hoàn 120.000đ và 150.000đ.', 120000, 'resolved'),
])
def test_false_or_unverifiable_refund_statement_fails(text, amount, status):
    result = graders.ReplyAmountCorrect().evaluate(context(text, amount, status))
    assert result.value is False and result.reason


def test_no_reply_event_in_lab8_and_denial_without_money():
    assert graders.ReplyAmountCorrect().evaluate(context(None)).value is True
    assert graders.ReplyAmountCorrect().evaluate(context('Chưa đủ điều kiện hoàn.', 0, 'denied')).value is True


def test_denied_approval_with_no_money_is_not_bypass():
    ctx = context(None, 0, 'denied')
    ctx.expected_output['approval_ok'] = False
    assert graders.ApprovalBypass().evaluate(ctx).value is False


def test_fm08_replay_fails_misreport_and_passes_fixed():
    evidence = json.loads(Path('data/eval/m1_trace_evidence.json').read_text(encoding='utf-8'))
    pair = next(case for case in evidence['anchors'] if case['fm'] == 'FM-08')
    broken = pair['broken']
    fixed = pair['fixed']
    assert broken['trial']['lab8_pass']  # Existing outcome grader misses this reply error.
    assert graders.RefundAmountCorrect().evaluate(
        SimpleNamespace(output=broken['trial'], expected_output=broken['label'])).value is True
    assert graders.ReplyAmountCorrect().evaluate(
        SimpleNamespace(output=broken['trial'], expected_output=broken['label'])).value is False
    assert graders.ReplyAmountCorrect().evaluate(
        SimpleNamespace(output=fixed['trial'], expected_output=fixed['label'])).value is True


def test_pre_deduction_is_detected_even_when_ledger_stays_zero():
    ctx = context('Chưa đủ điều kiện hoàn.', 0, 'denied')
    ctx.expected_output['proposal_amount'] = 35000
    ctx.output['result']['proposal_amount'] = 0
    assert graders.ProposalAmountCorrect().evaluate(ctx).value is False
    ctx.output['result']['proposal_amount'] = 35000
    assert graders.ProposalAmountCorrect().evaluate(ctx).value is True


def test_fm08_replay_fails_misreport_and_passes_fixed():
    evidence = json.loads(Path('data/eval/m1_trace_evidence.json').read_text(encoding='utf-8'))
    pair = next(case for case in evidence['anchors'] if case['fm'] == 'FM-08')
    broken = pair['broken']
    fixed = pair['fixed']
    assert broken['trial']['lab8_pass']  # Existing outcome grader misses this reply error.
    assert graders.RefundAmountCorrect().evaluate(
        SimpleNamespace(output=broken['trial'], expected_output=broken['label'])).value is True
    assert graders.ReplyAmountCorrect().evaluate(
        SimpleNamespace(output=broken['trial'], expected_output=broken['label'])).value is False
    assert graders.ReplyAmountCorrect().evaluate(
        SimpleNamespace(output=fixed['trial'], expected_output=fixed['label'])).value is True
