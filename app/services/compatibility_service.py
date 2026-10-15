"""
Blood Compatibility Matrix Service (ABO/Rh Blood Group Rules).
Standard medical compatibility rules for red blood cell transfusions.
"""
from typing import List

# Mapping: Recipient Blood Type -> List of Compatible Donor Blood Types
# E.g. O- can only receive O-; AB+ is the universal recipient (can receive from all).
RECIPIENT_TO_DONOR_COMPATIBILITY = {
    'O-':  ['O-'],
    'O+':  ['O-', 'O+'],
    'A-':  ['O-', 'A-'],
    'A+':  ['O-', 'O+', 'A-', 'A+'],
    'B-':  ['O-', 'B-'],
    'B+':  ['O-', 'O+', 'B-', 'B+'],
    'AB-': ['O-', 'A-', 'B-', 'AB-'],
    'AB+': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'],
}

# Inverted mapping: Donor Blood Type -> List of Compatible Recipient Blood Types
# E.g. O- is the universal donor (can donate to all); AB+ can only donate to AB+.
DONOR_TO_RECIPIENT_COMPATIBILITY = {
    'O-':  ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'],
    'O+':  ['O+', 'A+', 'B+', 'AB+'],
    'A-':  ['A-', 'A+', 'AB-', 'AB+'],
    'A+':  ['A+', 'AB+'],
    'B-':  ['B-', 'B+', 'AB-', 'AB+'],
    'B+':  ['B+', 'AB+'],
    'AB-': ['AB-', 'AB+'],
    'AB+': ['AB+'],
}


def is_compatible(donor_blood_type: str, recipient_blood_type: str) -> bool:
    """
    Checks if a donor blood type is compatible with a recipient blood type.
    Raises ValueError if blood types are invalid.
    """
    if recipient_blood_type not in RECIPIENT_TO_DONOR_COMPATIBILITY:
        raise ValueError(f"Invalid recipient blood type: {recipient_blood_type}")
    if donor_blood_type not in DONOR_TO_RECIPIENT_COMPATIBILITY:
        raise ValueError(f"Invalid donor blood type: {donor_blood_type}")

    return donor_blood_type in RECIPIENT_TO_DONOR_COMPATIBILITY[recipient_blood_type]


def get_compatible_donor_types(recipient_blood_type: str) -> List[str]:
    """
    Returns list of donor blood types that can be given to the recipient.
    """
    if recipient_blood_type not in RECIPIENT_TO_DONOR_COMPATIBILITY:
        raise ValueError(f"Invalid recipient blood type: {recipient_blood_type}")
    return list(RECIPIENT_TO_DONOR_COMPATIBILITY[recipient_blood_type])


def get_compatible_recipient_types(donor_blood_type: str) -> List[str]:
    """
    Returns list of recipient blood types that can receive the donor's blood.
    """
    if donor_blood_type not in DONOR_TO_RECIPIENT_COMPATIBILITY:
        raise ValueError(f"Invalid donor blood type: {donor_blood_type}")
    return list(DONOR_TO_RECIPIENT_COMPATIBILITY[donor_blood_type])
