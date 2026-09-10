# bash completion for json-dump
#
# Format names are queried from the binary itself
# (`json-dump -L --porcelain --direction in|out`) so the completion list
# tracks whichever optional Python packages are actually installed --
# there is no hard-coded format list to drift out of date.
#
# Install:  cp json-dump.bash /usr/share/bash-completion/completions/json-dump
#      or:  source json-dump.bash

_json_dump_formats() {
    local direction=$1
    "${_json_dump_cmd:-json-dump}" -L --porcelain --direction "$direction" 2>/dev/null \
        | awk -F'\t' '$4 == "yes" { print $1; if ($5 != "") { n = split($5, a, ","); for (i = 1; i <= n; i++) print a[i] } }'
}

# Template names come from the same place, and include whatever custom
# templates are on the user's search path -- which is the whole point of
# asking the binary rather than hard-coding a list.
_json_dump_templates() {
    "${_json_dump_cmd:-json-dump}" --list-templates --porcelain 2>/dev/null \
        | awk -F'\t' '{ print $1; if ($3 != "") { n = split($3, a, ","); for (i = 1; i <= n; i++) print a[i] } }'
}

_json_dump() {
    local cur prev words cword
    if declare -F _init_completion >/dev/null 2>&1; then
        _init_completion -n : || return
    else
        cur=${COMP_WORDS[COMP_CWORD]}
        prev=${COMP_WORDS[COMP_CWORD-1]}
    fi

    local _json_dump_cmd=${COMP_WORDS[0]}

    case $prev in
        -i|-f|--input-format|--from)
            COMPREPLY=($(compgen -W "auto $(_json_dump_formats in)" -- "$cur")); return ;;
        -o|-t|--output-format|--to|--help-format)
            COMPREPLY=($(compgen -W "$(_json_dump_formats out)" -- "$cur")); return ;;
        -O|--output|--avro-schema)
            COMPREPLY=($(compgen -f -- "$cur")); return ;;
        -T|--template)
            # A template is a name or a file, so offer both.
            COMPREPLY=($(compgen -W "$(_json_dump_templates)" -- "$cur"))
            COMPREPLY+=($(compgen -f -- "$cur")); return ;;
        --help-template|--dump-template)
            COMPREPLY=($(compgen -W "$(_json_dump_templates)" -- "$cur")); return ;;
        --merge-strategy)
            COMPREPLY=($(compgen -W "deep shallow last first collect" -- "$cur")); return ;;
        --list-merge)
            COMPREPLY=($(compgen -W "concat union replace keep index" -- "$cur")); return ;;
        --wrap-key)
            COMPREPLY=($(compgen -W "none basename stem path index" -- "$cur")); return ;;
        --null-policy)
            COMPREPLY=($(compgen -W "keep drop empty" -- "$cur")); return ;;
        --direction)
            COMPREPLY=($(compgen -W "any in out" -- "$cur")); return ;;
        --input-encoding)
            COMPREPLY=($(compgen -W "utf-8 utf-8-sig utf-16 latin-1 ascii cp1252" -- "$cur")); return ;;
        --indent|--root)
            return ;;
    esac

    if [[ $cur == -* ]]; then
        COMPREPLY=($(compgen -W "
            -i -f --input-format --from -m --multipacket -r --reverse --input-encoding
            -o -t --output-format --to -O --output --indent --compact -s --sort-keys
            --ascii --null-policy --avro-schema
            -T --template -e --escape-special --perl-compat --root
            --no-merge --merge-strategy --list-merge -d --dedup --wrap-key
            -h --help -L --list-formats --help-format --porcelain --direction -V --version
            --list-templates --help-template --dump-template
        " -- "$cur"))
        return
    fi

    COMPREPLY=($(compgen -f -- "$cur"))
}

complete -F _json_dump json-dump json_dump
