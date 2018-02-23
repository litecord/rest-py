"""common litecord data validation schemas.
"""

import re
from cerberus import Validator

EMAIL_REGEX = r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)'


class LitecordValidator(Validator):
    """Main litecord validator which implements
    more types for the schemas."""

    def _validate_type_email(self, value) -> bool:
        """Validate emails."""
        if re.match(EMAIL_REGEX, value):
            return True

v = LitecordValidator()

USERADD_SCHEMA = {
    'email': {'type': 'email'},
    'password': {'type': 'string'},
    'username': {'type': 'string', 'maxlength': 100},
}

LOGIN_SCHEMA = {
    'email': {'type': 'email'},
    'password': {'type': 'string'},
}

USERMOD_SCHEMA = {
    # TODO: discriminator
    'username': {'type': 'string', 'nullable': True},
    'avatar': {'type': 'string', 'nullable': True},

    # to change your email, you need your password.
    'email': {'type': 'email', 'depedencies': 'password'},
    'password': {'type': 'string'}
}

