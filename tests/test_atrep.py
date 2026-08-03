"""Binding-surface tests: signatures, return types, exception
mapping. Format semantics live in the spec repo's conformance
tree, run by atrep-rs — not here.

The samples are lifted from atrep-rs's own test suite
(tests/outline.rs, tests/metagraphe.rs), not invented."""

import pytest

import atrep

DOC = (
    '@@@!litogramma\n\n'
    '@# The Charges\n'
    '@("steph:17a")How you have been affected@^!(n1).\n\n'
    '@^!\nThe famous opening.\n!^@(n1)\n\n'
    '@## First Accusers\nMore prose here.\n##@\n'
    '#@\n\n'
    '@# The Defence\n'
    '@("steph:18a")From the beginning.\n#@\n'
)

DIA = (
    '@@@!atrep\n\n'
    '@=== section\n@= [lemma]\ngrammata\n=@\n===@\n\n'
    '@=== emphasis\n@/ grammata /@\n===@\n\n'
    '@=== verse\n@|(n)\n===@\n'
)


def test_version():
    assert atrep.version() == "0.3.0"


def test_check_document():
    assert atrep.check(DOC) == "document"


def test_check_definition():
    assert atrep.check(DIA) == "dialektos"


def test_check_error_locates():
    with pytest.raises(atrep.AtrepError) as e:
        atrep.check("@@@!litogramma\n\n@# Unclosed\nProse.\n")
    assert "doc.atd" in str(e.value)


def test_brachy_is_idempotent():
    b = atrep.brachy(DOC)
    assert atrep.brachy(b) == b
    assert "@#" in b


def test_plero_round_trips():
    p = atrep.plero(DOC)
    assert "@{" in p
    assert atrep.brachy(p) == atrep.brachy(DOC)


def test_plero_rejects_definition():
    with pytest.raises(atrep.AtrepError):
        atrep.plero(DIA)


def test_outline_shape():
    o = atrep.outline(DOC)
    assert o["dialektos"] == "litogramma"
    assert set(o) == {"dialektos", "blocks", "milestones", "onyms", "deixes"}
    first = o["blocks"][0]
    assert first["name"] == "section"
    assert first["depth"] == 0
    assert first["start"] == 3
    keys = {m["key"] for m in o["milestones"]}
    assert "steph:17a" in keys and "steph:18a" in keys
    assert any(p["key"] == "n1" for p in o["onyms"])


def test_endo_markdown():
    a = atrep.endo("markdown", "# Title\n\nSome prose.\n")
    assert atrep.check(a) == "document"
    assert "Title" in a


def test_endo_unknown_format():
    with pytest.raises(atrep.AtrepError):
        atrep.endo("latex", "\\section{x}")


def test_endo_scheme_misuse():
    with pytest.raises(atrep.AtrepError):
        atrep.endo("markdown", "# Title\n", scheme="steph")


def test_dialektos_std():
    lekt = atrep.dialektos("koine")
    assert atrep.check(lekt) == "dialektos"


def test_dialektos_sources():
    lekt = atrep.dialektos("demo", sources={"demo.lektos": DIA})
    assert "section" in lekt


def test_dialektos_params_exclusive():
    with pytest.raises(atrep.AtrepError):
        atrep.dialektos("demo", dir=".", sources={"demo.lektos": DIA})


def test_std_dialektoi():
    ids = atrep.std_dialektoi()
    assert "litogramma" in ids
    assert "koine" in ids
    assert len(ids) >= 14


def test_errors_are_atrep_error():
    assert issubclass(atrep.AtrepError, Exception)
    with pytest.raises(atrep.AtrepError):
        atrep.check("@@@!no-such-dialektos\n\ntext\n")
