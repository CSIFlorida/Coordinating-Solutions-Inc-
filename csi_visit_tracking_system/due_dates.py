"""
Shared visit-cadence engine. Pure functions, no I/O — used by the web app,
the PDF generator, and the monthly scheduler so all three always agree.

Rules:
  - anchor = Support Plan effective date shifted back 2 months.
  - Support Plan (SP) visit: due annually on the anchor's month.
  - Quarterly visit: due every 3 months from the anchor, UNLESS the
    consumer is due for an SP visit that same month (SP takes precedence,
    no double-listing that month).
  - Monthly visit: due every month, for consumers flagged GroupHome (GH)
    or Ind. Living (IL, treated as Supported Living / SL).
"""
from datetime import date

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]


def month_index(year, month0):
    """month0 is 0-based (0=Jan)."""
    return year * 12 + month0


def anchor_index(effective_date_str):
    y, m, _d = (int(x) for x in effective_date_str.split("-"))
    return month_index(y, m - 1) - 2


def anchor_month_day(effective_date_str):
    """Fixed month(0-11)/day characteristics of the SP anniversary."""
    y, m, d = (int(x) for x in effective_date_str.split("-"))
    a = date(y, 1, 1)
    # shift month by (m - 1 - 2) using plain arithmetic (avoids dateutil dep)
    total_month0 = (m - 1 - 2)
    yy = y + total_month0 // 12
    mm0 = total_month0 % 12
    # clamp day for short months (e.g. day 31 shifted into a 30-day month)
    days_in_month = [31, 29 if (yy % 4 == 0 and (yy % 100 != 0 or yy % 400 == 0)) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    dd = min(d, days_in_month[mm0])
    return mm0, dd


def due_flags(effective_date_str, gh, il, target_year, target_month0):
    """Returns {"sp": bool, "quarterly": bool, "monthly": bool} for one consumer
    in one target calendar month (target_month0 is 0-based)."""
    a = anchor_index(effective_date_str)
    target = month_index(target_year, target_month0)
    diff = target - a
    is_monthly_group = bool(gh) or bool(il)
    sp_due = diff % 12 == 0
    quarterly_due = (not is_monthly_group) and (not sp_due) and (diff % 3 == 0)
    return {"sp": sp_due, "quarterly": quarterly_due, "monthly": is_monthly_group}


def sp_due_date_label(effective_date_str, target_year, target_month0):
    """Upcoming SP anniversary date (as of the given target month), formatted
    'Mon D, YYYY'. Mirrors the logic used in the live report artifact."""
    mm0, dd = anchor_month_day(effective_date_str)
    year = target_year if mm0 >= target_month0 else target_year + 1
    return f"{MONTH_NAMES[mm0][:3]} {dd}, {year}"


def format_effective_date(date_str):
    if not date_str:
        return "—"
    y, m, d = (int(x) for x in date_str.split("-"))
    return f"{m}/{d}/{y}"
