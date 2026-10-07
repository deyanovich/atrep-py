//! Python bindings for Atrep — the same core crate the CLI wraps,
//! surfaced pythonically: strings in, strings out, exceptions
//! instead of exit codes. Resolution is offline: the std dialektoi
//! are embedded, non-std ones resolve from the path's directory
//! (no `net`, no `bundle`).

use std::collections::HashMap;
use std::path::Path;

use pyo3::create_exception;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use unicode_normalization::UnicodeNormalization;

create_exception!(atrep, AtrepError, PyException, "An atrep error.");

fn aerr(e: impl std::fmt::Display) -> PyErr {
    AtrepError::new_err(e.to_string())
}

/// The parsed document behind `text`, or an error for definition
/// sources — the document operations (brachy, plero, outline) do
/// not apply to dialektos definitions.
fn parse_doc(text: &str, path: &str) -> PyResult<::atrep::Document> {
    match ::atrep::check_source(text, Path::new(path)).map_err(aerr)? {
        ::atrep::Checked::Document(doc) => Ok(doc),
        ::atrep::Checked::Dialektos(_) => Err(aerr(
            "definition source: this operation applies to documents",
        )),
    }
}

/// The dialektos a document declares, resolved from the path's
/// directory with the embedded std dialektoi as fallback.
fn resolve_dial(doc: &::atrep::Document, path: &str) -> PyResult<::atrep::dialektos::Dialektos> {
    let dir = Path::new(path).parent().unwrap_or(Path::new("."));
    ::atrep::dialektos::resolve(dir, &doc.dialect_id).map_err(aerr)
}

/// The bindings (and wrapped core) version.
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Parse and validate a document or dialektos definition, routed
/// on the declaration; returns "document" or "dialektos". `path`
/// is where the source nominally lives: non-std dialektoi and
/// imports resolve from its directory and errors locate there.
#[pyfunction]
#[pyo3(signature = (text, path="doc.atd"))]
fn check(text: &str, path: &str) -> PyResult<&'static str> {
    match ::atrep::check_source(text, Path::new(path)).map_err(aerr)? {
        ::atrep::Checked::Document(_) => Ok("document"),
        ::atrep::Checked::Dialektos(_) => Ok("dialektos"),
    }
}

/// Rewrite a document in the brachygraphic spelling (sim symbols;
/// the canonical spelling).
#[pyfunction]
#[pyo3(signature = (text, path="doc.atd"))]
fn brachy(text: &str, path: &str) -> PyResult<String> {
    let doc = parse_doc(text, path)?;
    Ok(::atrep::dendron::serialize(&doc))
}

/// Rewrite a document in the plerographic spelling (sim names in
/// braces). `lang` spells sim names from that language's glossa
/// (`<dialektos>.<lang>.glossa`), falling back to primary names
/// where the glossa is silent.
#[pyfunction]
#[pyo3(signature = (text, lang=None, path="doc.atd"))]
fn plero(text: &str, lang: Option<&str>, path: &str) -> PyResult<String> {
    let doc = parse_doc(text, path)?;
    let dial = resolve_dial(&doc, path)?;
    ::atrep::dendron::serialize_plerographic_in(&doc, &dial, lang).map_err(aerr)
}

/// The document's structural outline as plain dicts and lists:
/// blocks with line spans, and located milestones, onyms, and
/// deixes (`{"key": ..., "line": ...}` each).
#[pyfunction]
#[pyo3(signature = (text, path="doc.atd"))]
fn outline(py: Python<'_>, text: &str, path: &str) -> PyResult<Py<PyDict>> {
    let normalized: String = text.nfc().collect();
    let (doc, blocks, dial) =
        ::atrep::parser::parse_document_outline(&normalized, Path::new(path)).map_err(aerr)?;
    let o = ::atrep::outline::assemble(&doc, blocks, &normalized, &dial);

    let points = |pts: &[::atrep::outline::OutlinePoint]| -> PyResult<Py<PyList>> {
        let list = PyList::empty(py);
        for p in pts {
            let d = PyDict::new(py);
            d.set_item("key", &p.key)?;
            d.set_item("line", p.line)?;
            list.append(d)?;
        }
        Ok(list.unbind())
    };

    let blocks_list = PyList::empty(py);
    for b in &o.blocks {
        let d = PyDict::new(py);
        d.set_item("kind", b.kind)?;
        d.set_item("symbol", b.symbol.as_deref())?;
        d.set_item("name", b.name.as_deref())?;
        d.set_item("depth", b.depth)?;
        d.set_item("start", b.start)?;
        d.set_item("end", b.end)?;
        d.set_item("lemma", &b.lemma)?;
        d.set_item("onym", b.onym.as_deref())?;
        d.set_item("genoses", &b.genoses)?;
        blocks_list.append(d)?;
    }

    let out = PyDict::new(py);
    out.set_item("dialektos", &o.dialektos)?;
    out.set_item("blocks", blocks_list)?;
    out.set_item("milestones", points(&o.milestones)?)?;
    out.set_item("onyms", points(&o.onyms)?)?;
    out.set_item("deixes", points(&o.deixes)?)?;
    Ok(out.unbind())
}

/// Foreign format -> canonical atrep (brachygraphic spelling).
/// Formats: markdown | html | rst | org | djot | docbook | bibtex
/// | jats | tei | usfm | usx | osis | fb2 | rnc | opencorpora |
/// proiel | conllu | dsl. `scheme` applies a versification milestone
/// scheme (usfm/usx/osis only). FB2 binaries are not returned:
/// the document references them as media/<id>.
#[pyfunction]
#[pyo3(signature = (format, text, scheme=None))]
fn endo(format: &str, text: &str, scheme: Option<&str>) -> PyResult<String> {
    use ::atrep::endo as e;
    let mut doc = match format {
        "markdown" => e::markdown_to_document(text),
        "html" => e::html_to_document(text),
        "rst" => e::rst_to_document(text),
        "org" => e::org_to_document(text),
        "djot" => e::djot_to_document(text),
        "docbook" => e::docbook_to_document(text),
        "bibtex" => e::bibtex_to_document(text),
        "jats" => e::jats_to_document(text),
        "tei" => e::tei_to_document(text),
        "usfm" => e::usfm_to_document(text),
        "usx" => e::usx_to_document(text),
        "osis" => e::osis_to_document(text),
        "fb2" => ::atrep::fb2::fb2_to_document(text),
        "rnc" => ::atrep::epimerismos::rnc_to_document(text),
        "opencorpora" => ::atrep::epimerismos::opencorpora_to_document(text),
        "proiel" => ::atrep::epimerismos::proiel_to_document(text),
        "conllu" => ::atrep::epimerismos::conllu_to_document(text),
        // ABBYY Lingvo DSL, decoded by the caller: a file is
        // UTF-16 or a code page, so read it as bytes and decode
        // (atrep's `dsl` module does) before passing the text.
        "dsl" => ::atrep::dsl::dsl_text_to_document(text, None),
        other => return Err(aerr(format!("unsupported endo format: {other}"))),
    }
    .map_err(aerr)?;
    if let Some(s) = scheme {
        match format {
            "usfm" | "usx" | "osis" => e::usfm_apply_scheme(&mut doc, s),
            _ => return Err(aerr("scheme applies to usfm/usx/osis only")),
        }
    }
    Ok(::atrep::dendron::serialize(&doc))
}

/// Resolve a dialektos by id and return its canonical
/// serialization. `dir` resolves from a directory on disk;
/// `sources` resolves from a dict of in-memory artifacts keyed by
/// file name (e.g. `{"demo.lektos": "..."}`). The two are
/// mutually exclusive; with neither, only the embedded std
/// dialektoi resolve.
#[pyfunction]
#[pyo3(signature = (id, dir=None, sources=None))]
fn dialektos(id: &str, dir: Option<&str>, sources: Option<HashMap<String, String>>) -> PyResult<String> {
    let d = match (dir, sources) {
        (Some(_), Some(_)) => {
            return Err(aerr("dir and sources are mutually exclusive"));
        }
        (Some(dir), None) => ::atrep::dialektos::resolve(Path::new(dir), id),
        (None, sources) => {
            let mut ms = ::atrep::source::MemorySource::new();
            for (name, text) in sources.unwrap_or_default() {
                ms.insert(name, text);
            }
            ::atrep::dialektos::resolve_from(&ms, id)
        }
    }
    .map_err(aerr)?;
    Ok(::atrep::dialektos::serialize(&d))
}

/// The ids of the embedded std dialektoi.
#[pyfunction]
fn std_dialektoi() -> Vec<&'static str> {
    ::atrep::dialektos::std_ids()
}

#[pymodule]
fn atrep(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(check, m)?)?;
    m.add_function(wrap_pyfunction!(brachy, m)?)?;
    m.add_function(wrap_pyfunction!(plero, m)?)?;
    m.add_function(wrap_pyfunction!(outline, m)?)?;
    m.add_function(wrap_pyfunction!(endo, m)?)?;
    m.add_function(wrap_pyfunction!(dialektos, m)?)?;
    m.add_function(wrap_pyfunction!(std_dialektoi, m)?)?;
    m.add("AtrepError", py.get_type::<AtrepError>())?;
    Ok(())
}
