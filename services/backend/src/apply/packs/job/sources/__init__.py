"""
Where job postings come from: the public APIs and feeds job boards publish for exactly this. No scraping, no
logging in, no getting round limits: each adapter asks no more often than its terms allow
(``min_interval_hours``), and names the board where its terms ask (``attribution``).

Not here, on purpose: job sites that have no public listings API, or whose terms forbid collecting them. The
extension tracks a posting from the page the person has open instead.

Adding one: CONTRIBUTING.md, "Adding a platform" (``uv run apply-dev new-source <kind>`` writes the stubs).
"""

from .board01 import Board01Source
from .board02 import Board02Source
from .board03 import Board03Source
from .board04 import Board04Source
from .board05 import Board05Source
from .board06 import Board06Source
from .board07 import Board07Source
from .board08 import Board08Source
from .board09 import Board09Source

# Company boards (an employer's own), then job sites (many employers').
SOURCES = (
    Board01Source(),
    Board02Source(),
    Board03Source(),
    Board04Source(),
    Board05Source(),
    Board06Source(),
    Board07Source(),
    Board08Source(),
    Board09Source(),
)

__all__ = ["SOURCES"]
