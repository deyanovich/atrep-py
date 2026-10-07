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
    assert atrep.version() == "0.3.6"


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


def test_endo_conllu_parsing_pack():
    conllu = (
        "# sent_id = 1\n# text = Arma virumque cano.\n"
        "1\tArma\tarma\tNOUN\t_\tCase=Acc|Number=Plur\t3\tobj\t_\t_\n"
        "2\tvirumque\tvir\tNOUN\t_\tCase=Acc|Number=Sing\t1\tconj\t_\t_\n"
        "3\tcano\tcano\tVERB\t_\tMood=Ind|Person=1\t0\troot\t_\tSpaceAfter=No\n"
        "4\t.\t.\tPUNCT\t_\t_\t3\tpunct\t_\t_\n\n"
    )
    a = atrep.endo("conllu", conllu)
    assert atrep.check(a) == "document"
    assert "@!=(arma)" in a and "@!/(NOUN)" in a


def test_endo_tei_cast_and_choice():
    tei = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc>'
        "<titleStmt><title>Tom Sawyer</title></titleStmt></fileDesc>"
        "<profileDesc><particDesc><listPerson>"
        '<person xml:id="polly"><persName>Aunt Polly</persName></person>'
        "</listPerson></particDesc></profileDesc></teiHeader><text><body>"
        '<p><said who="#polly">Tom!</said> <choice><orig>ye olde</orig>'
        "<reg>the old</reg></choice> fence.</p></body></text></TEI>"
    )
    a = atrep.endo("tei", tei)
    assert atrep.check(a) == "document"
    assert "@:!Aunt Polly!:@(polly)" in a
    assert "@@.@?~(ye\\ olde)the old.@@" in a


def test_endo_tei_bibliography_and_cite_span():
    tei = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc>'
        "<titleStmt><title>On Empires</title></titleStmt></fileDesc>"
        "</teiHeader><text><body>"
        '<p>Rome fell slowly <ref target="#gibbon1776">ch. 15</ref> and '
        'Persia was vast <ptr target="#herodotus"/>.</p>'
        '<listBibl><bibl xml:id="gibbon1776"><author>Gibbon, Edward</author>'
        '<title level="m">The Decline and Fall of the Roman Empire</title>'
        "<date>1776</date></bibl>"
        '<bibl xml:id="herodotus"><author>Herodotus</author>'
        "<title>The Histories</title></bibl></listBibl>"
        "</body></text></TEI>"
    )
    a = atrep.endo("tei", tei)
    assert atrep.check(a) == "document"
    assert "@@.@>[(gibbon1776)ch. 15.@@" in a
    assert "vast @>[(herodotus)." in a
    assert "@@@!(bibliogramma)" in a
    assert "@& gibbon1776\n@: author\nGibbon, Edward\n:@" in a
    assert "@: year\n1776\n:@\n&@.book" in a


def test_endo_dsl():
    dsl = (
        '#NAME "Webster"\n#INDEX_LANGUAGE "English"\n#CONTENTS_LANGUAGE "English"\n\n'
        "Liberal\n\t[m1][p]a.[/p][/m]\n"
        "\t[m1]1) Free by birth; noble. [ex]a liberal ancestry[/ex][/m]\n"
        "\t[m1]2) Generous; bounteous. See <<Liberalism>>.[/m]\n\n"
        "Liberalism\n\t[m1]Liberal principles.[/m]\n"
    )
    a = atrep.endo("dsl", dsl)
    assert atrep.check(a) == "document"
    assert a.startswith("@@@!lexigramma\n")
    assert "@=/en en/=@" in a
    assert "@! Liberal\n@=&a.&=@\n\n@:(1)\nFree by birth; noble. @~a liberal ancestry~@\n:@" in a
    assert "See @>(Liberalism)." in a
    assert "@! Liberalism\n@:(1)\nLiberal principles.\n:@" in a


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
