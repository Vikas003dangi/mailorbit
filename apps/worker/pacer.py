import logging
import random
import time

logger = logging.getLogger("mailorbit.pacer")


class Pacer:
    """
    Randomized delay pacer enforcing human-like email dispatch intervals.
    TRD Requirement: 25-40s randomized delay between dispatches.
    Can be configured to 0 delay in test suites.
    """

    def __init__(self, min_seconds: float = 25.0, max_seconds: float = 40.0, enabled: bool = True):
        self.min_seconds = min_seconds
        self.max_seconds = max_seconds
        self.enabled = enabled

    def pace(self) -> float:
        """Applies configured randomized delay. Returns actual elapsed seconds."""
        if not self.enabled or (self.min_seconds <= 0 and self.max_seconds <= 0):
            return 0.0

        delay = random.uniform(self.min_seconds, self.max_seconds)
        logger.debug("Pacing dispatch with %.2f second delay", delay)
        time.sleep(delay)
        return delay
