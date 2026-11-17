"""M2 boundary checks for binary judge calibration."""
import math
from pathlib import Path

import pytest

from lab9 import stats
from lab9.judge import calibrate


def test_binary_edge_cases():
    assert stats.confusion(['FAIL', 'PASS'], ['PASS', 'FAIL']) == dict(tp=0, fp=1, fn=1, tn=0)
    assert stats.precision_recall(['PASS'], ['PASS']) == (0.0, 0.0)
    assert stats.cohen_kappa(['FAIL', 'PASS'], ['FAIL', 'PASS']) == 1.0
    assert stats.cohen_kappa(['FAIL', 'PASS'], ['PASS', 'FAIL']) == -1.0
    assert stats.rogan_gladen(1.0, 0.8, 0.9) == 1.0


@pytest.mark.parametrize('human,judge', [([], []), (['PASS'], []), (['INVALID'], ['PASS'])])
def test_invalid_labels_rejected(human, judge):
    with pytest.raises(ValueError):
        stats.confusion(human, judge)


def test_undefined_correction_rejected():
    with pytest.raises(ValueError):
        stats.rogan_gladen(0.5, 0.5, 0.5)


def test_constant_judge_fails_calibration_without_crashing(tmp_path):
    path = tmp_path / 'constant.csv'
    path.write_text('item_id,reply,human,judge\nx,ok,PASS,PASS\n', encoding='utf-8')
    result = calibrate(path)
    assert not result['passed'] and math.isnan(result['kappa'])
    assert math.isnan(result['corrected_fail_rate'])


def test_public_judges_accept_tone_reject_helpful():
    tone = calibrate(Path('data/eval/judge_tone_public.csv'))
    helpful = calibrate(Path('data/eval/judge_helpful_public.csv'))
    assert tone['passed'] and tone['corrected_fail_rate'] == 0.3
    assert not helpful['passed'] and helpful['recall'] == 0.3
    assert helpful['confusion'] == dict(tp=9, fp=0, fn=21, tn=70)
