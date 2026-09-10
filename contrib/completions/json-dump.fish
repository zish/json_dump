# fish completion for json-dump
#
# Format lists come from `json-dump -L --porcelain`, filtered to formats whose
# optional Python dependencies are installed, so uninstallable choices are
# never offered.

function __json_dump_formats --argument-names direction
    json-dump -L --porcelain --direction $direction 2>/dev/null | while read -l line
        set -l f (string split \t -- $line)
        test (count $f) -ge 6; or continue
        test "$f[4]" = yes; or continue
        printf '%s\t%s\n' $f[1] $f[6]
        for a in (string split , -- $f[5])
            test -n "$a"; and printf '%s\t%s\n' $a "alias for $f[1]"
        end
    end
end

function __json_dump_templates
    json-dump --list-templates --porcelain 2>/dev/null | while read -l line
        set -l f (string split \t -- $line)
        test (count $f) -ge 5; or continue
        printf '%s\t%s\n' $f[1] $f[5]
        for a in (string split , -- $f[3])
            test -n "$a"; and printf '%s\t%s\n' $a "alias for $f[1]"
        end
    end
end

complete -c json-dump -f -a '(__fish_complete_path)'

# input
complete -c json-dump -s i -s f -l input-format -l from -r -f \
    -a "auto\t'detect from extension, then content' (__json_dump_formats in)" \
    -d 'Format of the input'
complete -c json-dump -s m -l multipacket -d 'Treat each input line as a separate document'
complete -c json-dump -s r -l reverse      -d 'Process documents newest-first (implies -m)'
complete -c json-dump -l input-encoding -r -f -a 'utf-8 utf-8-sig utf-16 latin-1 ascii cp1252' \
    -d 'Character encoding for text input'

# output
complete -c json-dump -s o -s t -l output-format -l to -r -f \
    -a '(__json_dump_formats out)' -d 'Format to emit'
complete -c json-dump -s O -l output -r -d 'Write to FILE instead of stdout'
complete -c json-dump -l indent  -r -f -d 'Indentation width for structured output'
complete -c json-dump -l compact       -d 'Single-line structured output'
complete -c json-dump -s s -l sort-keys -d 'Sort mapping keys'
complete -c json-dump -l ascii         -d 'Escape non-ASCII characters'
complete -c json-dump -l null-policy -r -f -a 'keep drop empty' \
    -d 'Handling of null in formats that lack it'
complete -c json-dump -l avro-schema -r -d 'Avro writer schema (JSON) instead of inference'

# path dump
complete -c json-dump -s T -l template -r -a '(__json_dump_templates)' \
    -d 'Pseudocode notation, by name or template file'
complete -c json-dump -s e -l escape-special -d 'Escape CR, LF and TAB in leaf values'
complete -c json-dump -l perl-compat -d 'Reproduce json_dump.pl byte-for-byte'
complete -c json-dump -l root -r -f -d 'Name of the root node in dumped paths'

# merging
complete -c json-dump -l no-merge -d 'Emit each document separately'
complete -c json-dump -l merge-strategy -r -f -d 'How to combine mappings' -a "\
deep\t'recurse, later wins at the leaves'
shallow\t'later document replaces the whole value'
last\t'later document wins outright'
first\t'earlier document wins outright'
collect\t'gather conflicting values into a list'"
complete -c json-dump -l list-merge -r -f -d 'How to combine arrays' -a "\
concat\t'append'
union\t'append, dropping structural duplicates'
replace\t'later wins'
keep\t'earlier wins'
index\t'merge element-wise by position'"
complete -c json-dump -s d -l dedup -d 'Drop structurally duplicate array elements'
complete -c json-dump -l wrap-key -r -f -d 'Key each document by its source' -a "\
none\t'merge instead'
basename\t'file name'
stem\t'file name without extension'
path\t'path as given'
index\t'position on the command line'"

# information
complete -c json-dump -s h -l help    -d 'Show help and exit'
complete -c json-dump -s L -l list-formats -d 'List every format and its availability'
complete -c json-dump -l help-format -r -f -a '(__json_dump_formats any)' \
    -d 'Explain one format in detail'
complete -c json-dump -l list-templates -d 'List every pseudocode template'
complete -c json-dump -l help-template -r -f -a '(__json_dump_templates)' \
    -d 'Explain one template, or how to write one'
complete -c json-dump -l dump-template -r -f -a '(__json_dump_templates)' \
    -d 'Print a template as JSON, ready to edit'
complete -c json-dump -l porcelain -d 'Machine-readable --list-formats output'
complete -c json-dump -l direction -r -f -a 'any in out' -d 'Restrict --list-formats'
complete -c json-dump -s V -l version -d 'Show version and exit'
