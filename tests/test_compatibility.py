import pytest
from app.services.compatibility_service import (
    is_compatible, get_compatible_donor_types, get_compatible_recipient_types
)
from app.models.donor import BLOOD_TYPES

def test_universal_donor_o_negative():
    """O- can donate red blood cells to every blood type."""
    for recipient in BLOOD_TYPES:
        assert is_compatible('O-', recipient) is True

    compatible_recipients = get_compatible_recipient_types('O-')
    assert len(compatible_recipients) == 8


def test_universal_recipient_ab_positive():
    """AB+ can receive red blood cells from every blood type."""
    for donor in BLOOD_TYPES:
        assert is_compatible(donor, 'AB+') is True

    compatible_donors = get_compatible_donor_types('AB+')
    assert len(compatible_donors) == 8


def test_o_negative_can_only_receive_o_negative():
    """O- recipient can ONLY receive O-."""
    assert is_compatible('O-', 'O-') is True
    for donor in BLOOD_TYPES:
        if donor != 'O-':
            assert is_compatible(donor, 'O-') is False

    assert get_compatible_donor_types('O-') == ['O-']


def test_ab_positive_can_only_donate_to_ab_positive():
    """AB+ donor can ONLY donate to AB+."""
    assert is_compatible('AB+', 'AB+') is True
    for recipient in BLOOD_TYPES:
        if recipient != 'AB+':
            assert is_compatible('AB+', recipient) is False

    assert get_compatible_recipient_types('AB+') == ['AB+']


def test_rh_positive_cannot_donate_to_rh_negative():
    """Rh+ red blood cells cannot be transfused to Rh- recipients."""
    rh_positives = ['O+', 'A+', 'B+', 'AB+']
    rh_negatives = ['O-', 'A-', 'B-', 'AB-']

    for pos in rh_positives:
        for neg in rh_negatives:
            assert is_compatible(pos, neg) is False


def test_incompatible_cross_types():
    assert is_compatible('A+', 'B+') is False
    assert is_compatible('B+', 'A+') is False
    assert is_compatible('A-', 'B-') is False
    assert is_compatible('B-', 'A-') is False


def test_invalid_blood_types_raise_error():
    with pytest.raises(ValueError):
        is_compatible('INVALID', 'A+')

    with pytest.raises(ValueError):
        is_compatible('A+', 'UNKNOWN')
