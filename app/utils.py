"""Short code generation and fraud check simulation."""
import asyncio
import random
import string


def generate_short_code(length: int = 6) -> str:
    """Generate a random alphanumeric lowercase short code (a-z, 0-9)."""
    characters = string.ascii_lowercase + string.digits
    return "".join(random.choice(characters) for _ in range(length))


async def simulate_fraud_check() -> bool:
    """Simulate fraud validation with 100ms delay. Always returns True."""
    await asyncio.sleep(0.1)
    return True
