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

    def _validate_type_verification_level(self, value) -> bool:
        return int(value) in (0, 1, 2, 3, 4)

    def _validate_type_msg_notifications(self, value) -> bool:
        return int(value) in (0, 1)

    def _validate_type_explicit_content(self, value) -> bool:
        return int(value) in (0, 1, 2)

    def _validate_type_image(self, value) -> bool:
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

GUILDADD_SCHEMA = {
    'name': {'type': 'string', 'minlength': 2, 'maxlength': 100},
    'region': {'type': 'voice_region'},

    'icon': {'type': 'image', 'nullable': True},
    'verification_level': {'type': 'verification_level', 'nullable': True},
    'default_message_notifications': {
        'type': 'msg_notifications',
        'nullable': True
    },
    'explicit_content_filter': {'type': 'explicit_content', 'nullable': True},

    # TODO: roles, channels
}
