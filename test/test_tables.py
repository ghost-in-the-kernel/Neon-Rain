from scripts.checks import tables


def test_cells_are_trimmed_and_the_outer_bars_dropped() -> None:
    assert tables.cells("  | a |  b c |  |\n") == ["a", "b c", ""]


def test_a_table_is_the_run_of_lines_that_start_with_a_bar() -> None:
    assert tables.TABLE.findall("x\n| a |\n| b |\n\ny\n| c |") == ["| a |\n| b |\n", "| c |"]
