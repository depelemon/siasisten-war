from src.scraper import Position


def find_new_openings(
    current: dict[str, Position],
    previous: dict[str, Position],
) -> dict[str, Position]:
    """
    Returns positions that are newly open since the previous run:
    - Brand-new IDs that have can_apply=True
    - Existing IDs that flipped from can_apply=False to can_apply=True
    """
    new: dict[str, Position] = {}
    for pos_id, pos in current.items():
        if not pos.can_apply:
            continue
        prev = previous.get(pos_id)
        if prev is None or not prev.can_apply:
            new[pos_id] = pos
    return new
