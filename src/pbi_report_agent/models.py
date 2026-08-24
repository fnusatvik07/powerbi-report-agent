"""Typed spec for a Power BI report + semantic model.

A `ReportSpec` is a plain-data description of what you want. The generator turns it into
the on-disk PBIP project (PBIR report files + TMDL semantic model) that Power BI accepts.
Nothing here talks to the network - it is pure data.
"""

from dataclasses import dataclass, field


@dataclass
class Column:
    """One column of the fact table."""

    name: str
    # M / TMDL data type: "text" | "int64" | "double"
    dtype: str = "text"
    summarize_by: str = "none"


@dataclass
class Measure:
    """A DAX measure exposed by the model."""

    name: str
    dax: str
    format_string: str = "#,##0"


@dataclass
class Model:
    """A single-table import-mode semantic model backed by inline sample data.

    `rows` is a list of rows, each a list of values in the same order as `columns`.
    Inline data means the model refreshes in the service with no gateway or external source.
    """

    table: str
    columns: list[Column]
    rows: list[list[object]]
    measures: list[Measure] = field(default_factory=list)


@dataclass
class Visual:
    """One visual on a page.

    `vtype` is a PBIR visual type (e.g. "clusteredBarChart", "cardVisual", "slicer",
    "donutChart", "lineChart", "clusteredColumnChart", "pivotTable", "textbox", "shape",
    "pageNavigator").

    `roles` maps a role name to a list of field references. A field reference is either a
    column name (str) or a dict {"measure": "<name>"} to bind a measure. Common roles:
    Category/Y (charts), Data (card), Values (slicer), Rows/Values (matrix).

    `text` is used by textbox visuals. `color` tints shapes/card accent bars.
    """

    vtype: str
    x: int
    y: int
    width: int
    height: int
    roles: dict[str, list[object]] = field(default_factory=dict)
    text: str = ""
    color: str = ""
    title: str = ""


@dataclass
class Page:
    display_name: str
    visuals: list[Visual] = field(default_factory=list)


@dataclass
class ReportSpec:
    """The whole thing: a name, one semantic model, and one or more pages."""

    name: str
    model: Model
    pages: list[Page]
    base_theme: str = "CY24SU10"
