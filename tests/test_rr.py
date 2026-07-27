"""Unit tests for the pure parsing helpers in `bin/rr`.

These cover the fragile bits — French money parsing, secret masking, platform
mapping, and the reservation table row/detail parsing — against the exact
strings the live RentalReady owner portal renders. Network and cookie access
are out of scope here (covered manually against the live session).
"""

import importlib.util
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

# The CLI lives at bin/rr (no .py extension); load it as a module by path.
_SPEC = importlib.util.spec_from_loader(
    "rr", importlib.machinery.SourceFileLoader("rr", str(Path(__file__).parent.parent / "bin" / "rr"))
)
rr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rr)


# --------------------------- parse_money --------------------------- #
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("401,00 €", 401.00),
        ("2 457,02 €", 2457.02),
        ("-99,00 €", -99.00),
        ("-946,34", -946.34),
        ("2457,02€", 2457.02),
        ("0,00 €", 0.0),
    ],
)
def test_parse_money_values(raw, expected):
    assert rr.parse_money(raw) == expected


@pytest.mark.parametrize("raw", ["—", "-", "", "n/a", None, "   "])
def test_parse_money_nulls(raw):
    assert rr.parse_money(raw) is None


def test_parse_money_handles_narrow_no_break_space():
    # The totals row uses U+202F narrow no-break space as the thousands sep.
    assert rr.parse_money("4 254,20 €") == 4254.20


# ------------------------------ mask ------------------------------- #
def test_mask_reveals_last_n():
    assert rr.mask("FR7600000000000000000005678", keep=4) == "•" * 23 + "5678"


def test_mask_keep_zero_hides_everything():
    # Regression: v[-0:] is the whole string, so keep=0 must special-case.
    assert rr.mask("BANKFRPP123", keep=0) == "•" * 11


def test_mask_empty_is_empty():
    assert rr.mask("", keep=4) == ""


def test_mask_strips_spaces_before_masking():
    assert rr.mask("+33 6 00 00 00 89", keep=2) == "•" * 10 + "89"


# --------------------------- platforms ----------------------------- #
@pytest.mark.parametrize(
    "name,code", [("airbnb", "1"), ("booking", "4"), ("hoststay", "2"), ("host_stay", "2")]
)
def test_platform_codes(name, code):
    assert rr.PLATFORMS[name] == code


# ----------------------- reservation columns ----------------------- #
def test_reservation_column_count_matches_live_table():
    # The live table renders exactly 17 columns; the parser keys off this count.
    assert len(rr._RES_COLS) == 17


def test_money_columns_are_a_subset_of_all_columns():
    assert rr._MONEY_COLS.issubset(set(rr._RES_COLS))


# --------------------------- cells() ------------------------------- #
def test_cells_extracts_row_text():
    tr = BeautifulSoup("<tr><td>2468984</td><td>02/07/2026</td></tr>", "lxml").find("tr")
    assert rr.cells(tr) == ["2468984", "02/07/2026"]


# -------------------- _parse_reservations_page --------------------- #
def _res_page_html(rows_html: str, nav_html: str = "") -> "BeautifulSoup":
    # The live header's first cell is "ID"; the parser skips rows on that.
    ths = ["ID"] + rr._RES_COLS[1:]
    header = "<tr>" + "".join(f"<th>{c}</th>" for c in ths) + "</tr>"
    return BeautifulSoup(f"<table>{header}{rows_html}</table>{nav_html}", "lxml")


def _data_row(res_id: str) -> str:
    tds = [res_id, "02/07/2026", "05/07/2026", "401,00 €", "80,20 €", "99,00 €",
           "-99,00 €", "-93,00 €", "0,00 €", "—", "227,80 €", "Inconnu",
           "1 facture", "—", "227,80 €", "227,80 €", "PAYÉ"]
    detail = "Seaside Cottage Réservation : Jane Doe 2 adultes, 1 enfant 3 nuits Plateforme : Airbnb"
    return ("<tr>" + "".join(f"<td>{v}</td>" for v in tds) + "</tr>"
            + f'<tr><td colspan="17">{detail}</td></tr>')


def test_parse_page_counts_data_rows():
    items, _, _ = rr._parse_reservations_page(_res_page_html(_data_row("111") + _data_row("222")))
    assert len(items) == 2


def test_parse_page_extracts_guest_detail():
    items, _, _ = rr._parse_reservations_page(_res_page_html(_data_row("111")))
    assert items[0]["guest"] == "Jane Doe"


def test_parse_page_parses_detail_nights():
    items, _, _ = rr._parse_reservations_page(_res_page_html(_data_row("111")))
    assert items[0]["nights"] == 3


def test_parse_page_money_column_is_float():
    items, _, _ = rr._parse_reservations_page(_res_page_html(_data_row("111")))
    assert items[0]["net_revenue"] == 227.80


def test_parse_page_last_page_from_windowed_nav():
    nav = '<div class="pagination"><a href="?start_date=x&page=4">4</a></div>'
    _, _, last = rr._parse_reservations_page(_res_page_html(_data_row("111"), nav))
    assert last == 4


def test_parse_page_last_page_defaults_to_one_when_unpaginated():
    _, _, last = rr._parse_reservations_page(_res_page_html(_data_row("111")))
    assert last == 1


# --------------------------- _fmt_eur ------------------------------ #
def test_fmt_eur_none_is_dash():
    assert rr._fmt_eur(None) == "—"


def test_fmt_eur_formats_thousands():
    assert rr._fmt_eur(2457.02) == "2 457.02 €"
