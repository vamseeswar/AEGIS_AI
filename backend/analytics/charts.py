"""AEGIS AI — Data Visualization Generator
Analyzes structured tabular data / SQL result sets and generates
Recharts-compatible JSON specifications with curated palettes and auto-detected chart types.
"""

from typing import Any

from pydantic import BaseModel, Field

CURATED_PALETTE = [
    "#14b8a6",  # Teal
    "#8b5cf6",  # Violet
    "#38bdf8",  # Sky Blue
    "#f59e0b",  # Amber
    "#ec4899",  # Pink
    "#10b981",  # Emerald
    "#6366f1",  # Indigo
]


class ChartSeriesConfig(BaseModel):
    key: str
    label: str
    color: str


class ChartConfig(BaseModel):
    chart_type: str = Field(description="Recharts type: 'bar', 'line', 'area', or 'pie'")
    title: str
    x_axis_key: str
    y_axis_keys: list[str]
    series: list[ChartSeriesConfig]
    data: list[dict[str, Any]]


def generate_chart_config(
    rows: list[dict[str, Any]],
    title_hint: str = "Query Results Analytics",
) -> ChartConfig | None:
    """Inspects rows and column types to build a Recharts configuration.

    Returns None if data cannot be meaningfully plotted (e.g. no numeric columns or < 2 rows).
    """
    if not rows or len(rows) < 1:
        return None

    first_row = rows[0]
    keys = list(first_row.keys())

    # Classify keys into numeric and non-numeric
    numeric_keys = []
    text_keys = []

    for key in keys:
        # Check values across up to 10 rows
        is_num = True
        sample_vals = [r.get(key) for r in rows[:10] if r.get(key) is not None]
        if not sample_vals:
            continue
        for v in sample_vals:
            if not isinstance(v, int | float):
                is_num = False
                break
        if is_num:
            numeric_keys.append(key)
        else:
            text_keys.append(key)

    if not numeric_keys:
        return None

    # Determine X-axis key
    # Prefer keys matching date/time/period/month/day/name/label
    x_key = keys[0]
    if text_keys:
        time_matches = [k for k in text_keys if any(term in k.lower() for term in ["time", "date", "month", "day", "year", "period"])]
        if time_matches:
            x_key = time_matches[0]
        else:
            x_key = text_keys[0]
    else:
        # All numeric, take first as X
        x_key = numeric_keys[0]
        numeric_keys = numeric_keys[1:]
        if not numeric_keys:
            numeric_keys = [x_key]

    # Decide chart type
    is_time_series = any(term in x_key.lower() for term in ["time", "date", "month", "day", "year", "hour", "created_at"])

    if is_time_series:
        chart_type = "area" if len(numeric_keys) == 1 else "line"
    elif len(rows) <= 6 and len(numeric_keys) == 1:
        chart_type = "bar"
    else:
        chart_type = "bar"

    # Build series
    series = []
    for idx, num_k in enumerate(numeric_keys[:4]):  # Cap at 4 series
        color = CURATED_PALETTE[idx % len(CURATED_PALETTE)]
        label = num_k.replace("_", " ").title()
        series.append(ChartSeriesConfig(key=num_k, label=label, color=color))

    return ChartConfig(
        chart_type=chart_type,
        title=title_hint,
        x_axis_key=x_key,
        y_axis_keys=[s.key for s in series],
        series=series,
        data=rows,
    )
