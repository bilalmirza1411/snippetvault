from search.fuzzy_match import fuzzy_match


def test_exact():
    assert fuzzy_match("sort", "quicksort notes", 0) == 0

def test_one_typo():
    assert fuzzy_match("quiksort", "quicksort notes", 1) == 1

def test_case_insensitive():
    assert fuzzy_match("QUICKSORT", "quicksort notes", 0) == 0

def test_no_match():
    assert fuzzy_match("banana", "quicksort notes", 1) is None

def test_empty_query():
    assert fuzzy_match("", "anything", 1) is None