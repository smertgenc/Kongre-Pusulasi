"""Bounded retries for failures known to be transient; never change recipients."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import random

MAX_ATTEMPTS=3
MAX_ELAPSED=240
MAX_RETRY_AFTER=30
TRANSIENT_STATUS={408,500,502,503,504}

def retry_delay(response, attempt, *, max_retry_after=MAX_RETRY_AFTER):
    status=response.status_code
    header=response.headers.get('retry-after')
    if status not in TRANSIENT_STATUS and not (status==429 and header):return None
    server_delay=None
    if header:
        try:server_delay=float(header)
        except ValueError:
            try:server_delay=(parsedate_to_datetime(header)-datetime.now(timezone.utc)).total_seconds()
            except (ValueError,TypeError,OverflowError):pass
        if server_delay is not None and (server_delay!=server_delay or server_delay>max_retry_after):return None
    if status==429 and server_delay is None:return None
    # Wait at least as long as the server requested, and stagger concurrent calls.
    return max(2**attempt+random.uniform(0,.5),max(0,server_delay or 0))
