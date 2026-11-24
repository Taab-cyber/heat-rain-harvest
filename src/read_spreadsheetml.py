"""Read an Excel-2003 XML ("SpreadsheetML") file, as delivered by LGD, into a DataFrame.

pandas cannot read this format directly, so we parse the XML: each <Row> holds
<Cell><Data>value</Data></Cell> items; ss:Index on a cell means earlier cells
in that row were empty (skipped), and ss:MergeAcross spans extra columns.
The raw file is never modified.
"""
from pathlib import Path

import pandas as pd
from lxml import etree

NS = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
SS = "{urn:schemas-microsoft-com:office:spreadsheet}"


def read_rows(path: Path) -> list[list[str | None]]:
    tree = etree.parse(str(path))
    rows = []
    for row in tree.iterfind(".//ss:Worksheet/ss:Table/ss:Row", NS):
        vals: list[str | None] = []
        for cell in row.iterfind("ss:Cell", NS):
            idx = cell.get(f"{SS}Index")
            if idx is not None:                       # 1-based column index after empty cells
                vals.extend([None] * (int(idx) - 1 - len(vals)))
            data = cell.find("ss:Data", NS)
            vals.append("".join(data.itertext()).strip() if data is not None else None)
            vals.extend([None] * int(cell.get(f"{SS}MergeAcross", 0)))
        rows.append(vals)
    return rows


def read_table(path: Path, header_contains: str) -> pd.DataFrame:
    """Use the first row containing `header_contains` as the header."""
    rows = read_rows(path)
    h = next(i for i, r in enumerate(rows) if any(v and header_contains in v for v in r))
    header = [v or f"col{j}" for j, v in enumerate(rows[h])]
    body = [r + [None] * (len(header) - len(r)) for r in rows[h + 1:]]
    return pd.DataFrame([r[: len(header)] for r in body], columns=header)
