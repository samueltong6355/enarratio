# Changelog

All notable changes to Enarratio are documented here. Each entry records what changed and
*why*, so the reasoning behind the build is recoverable later.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Project scaffold: repository layout, README stating the design principles, MIT licence for
  the code, and a `.gitignore` that keeps downloaded linguistic data out of version control
  (it is large and separately licensed).
- Python 3.12 virtual environment pinned via `uv`. The system Python is 3.14, which is ahead
  of the Latin NLP stack — spaCy, Stanza and the LatinCy pipelines have no 3.14 wheels yet.
- Research phase: an eleven-domain survey of the digital-classics landscape, each domain
  independently fact-checked against live sources (PyPI, the GitHub API, HuggingFace, and
  HTTP liveness checks) to eliminate invented package names and dead links. Notes land in
  `docs/research/`, consolidated into `docs/RESEARCH-DOSSIER.md`.
