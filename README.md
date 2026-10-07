# atrep — Python bindings

Python bindings for [atrep](https://gitlab.com/atrep), an
extensible semantic markup language designed with literary
applications in mind. The same Rust core the
[CLI](https://pypi.org/project/atrep-cli/) wraps
([`atrep` on crates.io](https://crates.io/crates/atrep)),
surfaced pythonically: strings in, strings out, exceptions
instead of exit codes.

```sh
pip install atrep
```

## Checking and the two spellings

```python
import atrep

doc = open("apology.atd").read()

# Parse and validate; routes on the declaration.
atrep.check(doc)          # -> "document" | "dialektos"

# The two spellings: brachygraphic (sim symbols; canonical)
# and plerographic (sim names in braces). Both parse to the
# identical structure.
names = atrep.plero(doc)              # @# ... -> @{section} ...
symbols = atrep.brachy(names)         # ... and back
localized = atrep.plero(doc, lang="el")   # glossa sim names
```

## The structural outline

```python
o = atrep.outline(doc)
o["dialektos"]    # "litogramma"
o["blocks"]       # [{"kind", "symbol", "name", "depth",
                  #   "start", "end", "lemma", "onym",
                  #   "genoses"}, ...]
o["milestones"]   # [{"key": "steph:17a", "line": 4}, ...]
o["onyms"]        # located onym anchors
o["deixes"]       # located deixis references
```

## Endo importers

```python
# Foreign formats -> canonical atrep: markdown | html | rst |
# org | djot | docbook | bibtex | jats | tei | usfm | usx | osis |
# fb2 | rnc | opencorpora | proiel | conllu | dsl.
a = atrep.endo("markdown", open("notes.md").read())

# A Lingvo DSL dictionary is UTF-16 (or a code page): decode it
# first, then pass the text; the result is lexigramma.
a = atrep.endo("dsl", open("webster.dsl", encoding="utf-16").read())

# Versification milestone scheme (usfm/usx/osis only).
a = atrep.endo("usfm", open("john.usfm").read(), scheme="std")
```

## Dialektoi

```python
# Resolve a dialektos and get its canonical serialization.
# The std dialektoi are embedded; `dir` resolves from disk,
# `sources` from in-memory artifacts.
lekt = atrep.dialektos("koine")
lekt = atrep.dialektos("demo", sources={"demo.lektos": dia})
atrep.std_dialektoi()   # ["at-djot", "koine", ..., "litogramma"]
```

Errors raise `atrep.AtrepError`, with `file:line:col` locations
in the message where the source provides them. `atrep.version()`
reports the bindings/core version.

Resolution is offline: non-std dialektoi resolve from the
directory of the `path` argument (default `doc.atd`, i.e. the
process working directory). Remote fetching (kanonizo) and the
multi-document operations (morphisms, exo rendering, collation)
belong to the [CLI](https://pypi.org/project/atrep-cli/).

## License

MIT or Apache-2.0, at your option.
