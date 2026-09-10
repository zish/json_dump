# Example pseudocode templates

A template describes how one leaf of a nested structure is spelled as a line
of some language. It is a JSON (or TOML) file of literal strings — nothing in
it is imported, evaluated or executed.

```console
$ json-dump --list-templates          # what is built in, with an example of each
$ json-dump --help-template           # every field, placeholder and quoting style
$ json-dump --help-template go        # one notation, field by field
$ json-dump --dump-template go > mine.json   # a starting point to edit
```

## The three here

| File | Shows |
| --- | --- |
| [kotlin.json](kotlin.json) | `base`: inherit a built-in and state only the differences |
| [tsv.json](tsv.json) | a flat, unquoted notation written from scratch — `join`, `quote: raw` |
| [sql.json](sql.json) | `header`, a `path` with punctuation of its own, and a `line` that is a whole statement |

```console
$ json-dump --template ./sql.json hosts.json
CREATE TABLE IF NOT EXISTS leaf (path TEXT PRIMARY KEY, value TEXT);
BEGIN;
INSERT INTO leaf (path, value) VALUES ('hosts.0.name', 'web-01');
```

## Using them by name

Anything on the search path can be selected as `--template NAME`:

```console
$ mkdir -p ~/.config/json-dump/templates
$ cp *.json ~/.config/json-dump/templates/
$ json-dump --template tsv data.json
```

`JSON_DUMP_TEMPLATES` adds directories ahead of that one, which is how a
template travels with a project rather than with a person:

```console
$ JSON_DUMP_TEMPLATES=$PWD/contrib/templates json-dump --template sql data.json
```

Built-in names always resolve first, so no file can quietly redefine `perl`
for a script that expected it.
