import hashlib
import os
import base64

import sha3
from random import randint


async def random_digits(n: int) -> str:
    """Returns `n` random digits"""
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return str(randint(range_start, range_end))


def get_random_salt(size: int=64) -> str:
    """Generate a random salt for passwords"""
    return base64.b64encode(os.urandom(size)).decode()


def pwd_hash(plain: str, salt: str) -> str:
    """Generate a hash for a password using SHA3-512."""
    return hashlib.sha3_512(f'{plain}{salt}'.encode()).hexdigest()
