"""Static checks for Filevine document-assembly templates (Liquid syntax).

Catches the errors that otherwise surface only when a paralegal generates the
document: unbalanced block tags, typo'd filters, malformed delimiters, and
tokens that reference a section/field selector the project type doesn't have.
"""

import re

OUTPUT_RE = re.compile(r"\{\{-?(.*?)-?\}\}", re.S)
TAG_RE = re.compile(r"\{%-?\s*(\w+)(.*?)-?%\}", re.S)
PATH_RE = re.compile(r"^[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*|\[\d+\])*$")

BLOCK_TAGS = {
    "if": "endif",
    "unless": "endunless",
    "for": "endfor",
    "case": "endcase",
    "capture": "endcapture",
    "comment": "endcomment",
    "raw": "endraw",
    "tablerow": "endtablerow",
}
MIDDLE_TAGS = {"else", "elsif", "when", "break", "continue"}
INLINE_TAGS = {"assign", "increment", "decrement", "cycle", "echo", "include", "render", "liquid"}

STANDARD_FILTERS = {
    "abs", "append", "at_least", "at_most", "capitalize", "ceil", "compact", "concat",
    "date", "default", "divided_by", "downcase", "escape", "escape_once", "first",
    "floor", "join", "last", "lstrip", "map", "minus", "modulo", "newline_to_br",
    "plus", "prepend", "remove", "remove_first", "replace", "replace_first",
    "reverse", "round", "rstrip", "size", "slice", "sort", "sort_natural", "split",
    "strip", "strip_html", "strip_newlines", "sum", "times", "truncate",
    "truncatewords", "uniq", "upcase", "url_decode", "url_encode", "where",
}

# Roots that are always valid regardless of project-type schema.
BUILTIN_ROOTS = {"project", "client", "today", "now", "user", "org", "forloop"}


def _split_filters(expr):
    parts, buf, quote = [], "", None
    for ch in expr:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == "|":
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    return [p.strip() for p in parts]


def lint(template, schema=None, extra_filters=None):
    """Lint a template.

    schema: optional {section_selector: [field_selector, ...]} from the project
    type. When given, `section.field` tokens are checked against it.
    """
    errors, warnings = [], []
    filters_ok = STANDARD_FILTERS | set(extra_filters or [])
    schema = {k: set(v) for k, v in (schema or {}).items()}
    local_vars = set()
    tokens = []

    def line_of(pos):
        return template.count("\n", 0, pos) + 1

    # Stray / malformed delimiters
    opens = len(re.findall(r"\{\{", template)) + len(re.findall(r"\{%", template))
    closes = len(re.findall(r"\}\}", template)) + len(re.findall(r"%\}", template))
    if opens != closes:
        errors.append(f"Unbalanced delimiters: {opens} opening vs {closes} closing.")
    for m in re.finditer(r"\{\s+\{|\}\s+\}", template):
        errors.append(f"Line {line_of(m.start())}: split delimiter '{m.group(0)}' "
                      "(often caused by Word autocorrect or a line break).")
    for m in re.finditer(r"[“”‘’]", template):
        inside = any(a.start() < m.start() < a.end()
                     for a in list(OUTPUT_RE.finditer(template)) + list(TAG_RE.finditer(template)))
        if inside:
            errors.append(f"Line {line_of(m.start())}: smart quote inside a Liquid "
                          "expression. Replace with straight quotes.")

    # Block balance
    stack = []
    for m in TAG_RE.finditer(template):
        name, rest, ln = m.group(1), m.group(2).strip(), line_of(m.start())
        if name in BLOCK_TAGS:
            stack.append((name, ln))
            if name == "for":
                fm = re.match(r"(\w+)\s+in\s+", rest)
                if fm:
                    local_vars.add(fm.group(1))
            if name == "capture" and rest:
                local_vars.add(rest.split()[0])
        elif name.startswith("end"):
            opener = name[3:]
            if not stack:
                errors.append(f"Line {ln}: '{name}' with no open '{opener}'.")
            elif stack[-1][0] != opener:
                errors.append(f"Line {ln}: '{name}' closes '{stack[-1][0]}' opened on line "
                              f"{stack[-1][1]}.")
                stack.pop()
            else:
                stack.pop()
        elif name == "assign":
            am = re.match(r"(\w+)\s*=", rest)
            if am:
                local_vars.add(am.group(1))
        elif name not in MIDDLE_TAGS and name not in INLINE_TAGS:
            warnings.append(f"Line {ln}: unrecognized tag '{name}'.")
    for name, ln in stack:
        errors.append(f"Line {ln}: '{name}' is never closed with '{BLOCK_TAGS[name]}'.")

    # Outputs
    for m in OUTPUT_RE.finditer(template):
        ln = line_of(m.start())
        parts = _split_filters(m.group(1).strip())
        base, filters = parts[0], parts[1:]
        if not base:
            errors.append(f"Line {ln}: empty output tag.")
            continue
        for f in filters:
            fname = f.split(":")[0].strip()
            if fname not in filters_ok:
                hint = ""
                low = fname.lower()
                if low in filters_ok:
                    hint = f" (filters are case-sensitive: use '{low}')"
                errors.append(f"Line {ln}: unknown filter '{fname}'{hint}.")
        if base.startswith(("\"", "'")) or re.match(r"^-?\d", base):
            continue
        if not PATH_RE.match(base):
            errors.append(f"Line {ln}: malformed token '{base}'.")
            continue
        tokens.append(base)
        root = base.split(".")[0].split("[")[0]
        if root in local_vars or root in BUILTIN_ROOTS:
            continue
        if schema:
            if root not in schema:
                errors.append(f"Line {ln}: section '{root}' not in project type "
                              f"(token '{base}').")
            else:
                segs = base.split(".")
                if len(segs) > 1:
                    field = segs[1].split("[")[0]
                    if field not in schema[root]:
                        errors.append(f"Line {ln}: field '{field}' not in section "
                                      f"'{root}' (token '{base}').")
        else:
            warnings.append(f"Line {ln}: '{base}' not verified (no schema supplied).")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": sorted(set(warnings)),
        "tokens": sorted(set(tokens)),
    }
