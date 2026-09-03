import html
import re
import urllib.parse
from html.parser import HTMLParser

ALLOWED_TAGS = {
    "p",
    "br",
    "hr",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "strike",
    "del",
    "ins",
    "mark",
    "small",
    "sub",
    "sup",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "blockquote",
    "pre",
    "code",
    "a",
    "img",
    "span",
    "div",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "figure",
    "figcaption",
}

VOID_TAGS = {"br", "hr", "img"}

ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "rel", "class"},
    "img": {"src", "alt", "title", "width", "height", "class"},
    "p": {"class"},
    "span": {"class"},
    "div": {"class"},
    "code": {"class"},
    "pre": {"class"},
    "blockquote": {"class"},
    "table": {"class"},
    "thead": {"class"},
    "tbody": {"class"},
    "tfoot": {"class"},
    "tr": {"class"},
    "th": {"class", "colspan", "rowspan", "scope"},
    "td": {"class", "colspan", "rowspan"},
    "h1": {"class"},
    "h2": {"class"},
    "h3": {"class"},
    "h4": {"class"},
    "h5": {"class"},
    "h6": {"class"},
    "ul": {"class"},
    "ol": {"class", "type", "start"},
    "li": {"class"},
    "figure": {"class"},
    "figcaption": {"class"},
}

DISALLOWED_CONTAINER_TAGS = {
    "script",
    "style",
    "iframe",
    "object",
    "applet",
    "noscript",
    "noembed",
    "noframes",
    "template",
    "svg",
    "math",
    "form",
    "button",
    "textarea",
    "select",
}

DISALLOWED_VOID_TAGS = {
    "embed",
    "input",
    "meta",
    "link",
    "base",
    "param",
    "source",
    "track",
}

SAFE_SCHEMES = {"http", "https", "mailto", "tel"}


def is_safe_url(url: str) -> bool:
    if not url:
        return False
    # Strip whitespace, control characters, and newlines
    clean_url = re.sub(r"[\x00-\x20\x7f-\x9f]+", "", url)
    if clean_url.startswith(("/", "./", "../", "#")):
        return True
    try:
        parsed = urllib.parse.urlparse(clean_url)
        return parsed.scheme.lower() in SAFE_SCHEMES
    except Exception:
        return False


class HTMLSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.result: list[str] = []
        self.disallowed_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in DISALLOWED_CONTAINER_TAGS:
            self.disallowed_depth += 1
            return
        if tag_lower in DISALLOWED_VOID_TAGS:
            return
        if self.disallowed_depth > 0:
            return
        if tag_lower not in ALLOWED_TAGS:
            return

        allowed_for_tag = ALLOWED_ATTRS.get(tag_lower, set())
        clean_attrs: list[str] = []
        is_link_blank = False

        for attr, val in attrs:
            attr_lower = attr.lower()
            if attr_lower.startswith("on"):
                continue
            if attr_lower not in allowed_for_tag:
                continue

            if val is None:
                clean_attrs.append(attr_lower)
                continue

            if attr_lower in ("href", "src"):
                if not is_safe_url(val):
                    continue

            if tag_lower == "a" and attr_lower == "target" and val.lower() == "_blank":
                is_link_blank = True

            clean_attrs.append(f'{attr_lower}="{html.escape(val, quote=True)}"')

        if is_link_blank and not any(a.startswith("rel=") for a in clean_attrs):
            clean_attrs.append('rel="noopener noreferrer"')

        attrs_str = (" " + " ".join(clean_attrs)) if clean_attrs else ""
        if tag_lower in VOID_TAGS:
            self.result.append(f"<{tag_lower}{attrs_str} />")
        else:
            self.result.append(f"<{tag_lower}{attrs_str}>")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in DISALLOWED_CONTAINER_TAGS:
            if self.disallowed_depth > 0:
                self.disallowed_depth -= 1
            return
        if self.disallowed_depth > 0:
            return
        if tag_lower in ALLOWED_TAGS and tag_lower not in VOID_TAGS:
            self.result.append(f"</{tag_lower}>")

    def handle_data(self, data: str) -> None:
        if self.disallowed_depth == 0:
            self.result.append(html.escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if self.disallowed_depth == 0:
            self.result.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self.disallowed_depth == 0:
            self.result.append(f"&#{name};")


def sanitize_html(raw_html: str | None) -> str:
    """
    Sanitize raw HTML by removing unsafe tags, attributes, event handlers,
    and dangerous URL schemes while preserving legitimate article formatting.
    """
    if not raw_html:
        return ""
    sanitizer = HTMLSanitizer()
    sanitizer.feed(raw_html)
    sanitizer.close()
    return "".join(sanitizer.result)
