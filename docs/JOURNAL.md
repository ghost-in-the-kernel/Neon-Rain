# Journal: every event in the work, as a record a researcher can count

One entry per event: a contradiction found, a decision taken, a failure caught or missed, a change
of direction, a measurement. Not a restatement of the commit log and not a status list and not the
design: the journal records *what happened while the work was done*. Fixed fields, the same as
Katana's and Suite Builder's, so entries can be counted across projects. Newest last. Written by
whoever was there, in the same commit as the event when possible; an agent writes its own entries.

Fields: **Who**, **Intent**, **Found**, **Options**, **Resolved**, **Touched**, **Caught by** (for a
failure), **Cost**, **Class** (`contradiction`, `ambiguity`, `failure-caught`, `failure-missed`,
`decision`, `measurement`, `direction`, `trial`, `deferred`, `conflict`). A `conflict` also has
**Mine** and **Theirs** (each objective, plainly, no guess at intent) and stays listed in HANDOFF.md's
"For Ghost" until its **Resolved** names Ghost (J-023; `conflict` is Neon Rain's addition to the
shared classes). `test/test_journal.py` holds this.

## Where the entries live

The entries are in `docs/journal/`, ten ids to a file: `J-001-010.md`, `J-011-020.md`, and so on, each
under 300 lines so a file is read whole (AGT-04 asks for sections past 400). An entry is a heading
`### J-nnn Title` and the fields above, one `- **Field:** text` each, newest last. Take the id from
`python3 -I scripts/next_id.py journal`, and append the entry to the end of the newest file; when
that file holds its tenth id, start the next one, `J-nnn-mmm.md`, headed
`# Journal, J-nnn to J-mmm`. `docs/journal/INDEX.md` has one line per entry (id, title, class, file); it
is written by `python3 -I scripts/journal_index.py`, and `test/test_journal.py` fails, naming that
command, when it is stale. Run it after adding an entry.
