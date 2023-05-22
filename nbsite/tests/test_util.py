import pytest

from nbsite.util import base_version


@pytest.mark.parametrize(
    "version,expected",
    [
        ("0.3.0", "0.3.0"),
        ("0.13.0a19", "0.13.0a19"),
        ("0.13.0rc1", "0.13.0rc1"),
        ("0.13.0b1", "0.13.0b1"),
        ("no.match", "no.match"),
        ("0.13.0a19.post4+g0695e214", "0.13.0a19"),
        ("1.14.4", "1.14.4"),
        ("1.14.4.post82+g46ba8bbf2", "1.14.4"),
        # Only 3 component versions are matched.
        ("0.13.post4+g0695e214", "0.13.post4+g0695e214"),
        ("v0.3.0", "v0.3.0"),
    ]
)
def test_base_version(version, expected):
    assert base_version(version) == expected
