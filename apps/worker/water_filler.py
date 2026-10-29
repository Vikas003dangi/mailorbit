"""
Water-Filling Fair-Share Balancing Algorithm for MailOrbit Outreach Batches.

Distributes a sender account's daily email budget (default 30/day) fairly across
all active campaigns and sub-batches, ensuring:
1. Equal base shares are assigned to active batches.
2. Batches with fewer pending leads cap at their pending count.
3. Leftover budget is redistributed to larger pending batches.
4. Total dispatched across all batches never exceeds daily_budget.
"""
from typing import Any, Dict, List, Union
import uuid


class SubBatchLike:
    """Protocol-like helper for water-filling input objects."""
    def __init__(self, id: Union[uuid.UUID, str], pending_count: int, priority: int = 0):
        self.id = id
        self.pending_count = max(0, pending_count)
        self.priority = priority


def water_fill_fair_share(
    sub_batches: List[Any],
    daily_budget: int,
) -> Dict[Union[uuid.UUID, str], int]:
    """
    Executes water-filling fair share allocation.

    Args:
        sub_batches: List of objects with `.id` and `.pending_count` attributes,
                     or dicts with 'id' and 'pending_count'.
        daily_budget: Maximum emails allowable today (default 30).

    Returns:
        Dict mapping sub_batch.id -> integer allocated emails for today.
    """
    if daily_budget <= 0 or not sub_batches:
        return {
            (sb.id if hasattr(sb, "id") else sb["id"]): 0
            for sb in sub_batches
        }

    # Extract pending counts and initialize allocations
    allocations: Dict[Union[uuid.UUID, str], int] = {}
    pending: Dict[Union[uuid.UUID, str], int] = {}

    for sb in sub_batches:
        sb_id = sb.id if hasattr(sb, "id") else sb["id"]
        p_count = max(0, sb.pending_count if hasattr(sb, "pending_count") else sb.get("pending_count", 0))
        allocations[sb_id] = 0
        pending[sb_id] = p_count

    active_pool = [sb_id for sb_id, p_count in pending.items() if p_count > 0]
    remaining_budget = daily_budget

    while remaining_budget > 0 and active_pool:
        equal_share = remaining_budget // len(active_pool)
        if equal_share == 0:
            # Distribute remaining single units in order
            for sb_id in list(active_pool):
                if remaining_budget == 0:
                    break
                if pending[sb_id] > allocations[sb_id]:
                    allocations[sb_id] += 1
                    remaining_budget -= 1
                if allocations[sb_id] >= pending[sb_id]:
                    active_pool.remove(sb_id)
            break

        progress_made = False
        for sb_id in list(active_pool):
            needed = pending[sb_id] - allocations[sb_id]
            grant = min(needed, equal_share)
            if grant > 0:
                allocations[sb_id] += grant
                remaining_budget -= grant
                progress_made = True
            if allocations[sb_id] >= pending[sb_id]:
                active_pool.remove(sb_id)

        if not progress_made:
            break

    return allocations

