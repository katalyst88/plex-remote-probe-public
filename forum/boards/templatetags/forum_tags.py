import bleach
import markdown as md
from bleach.linkifier import LinkifyFilter
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = {
    "p", "br", "hr", "strong", "em", "b", "i", "code", "pre", "blockquote",
    "ul", "ol", "li", "a", "h3", "h4", "h5", "h6", "del",
}
ALLOWED_ATTRS = {"a": ["href", "title", "rel"]}


def _nofollow(attrs, new=False):
    attrs[(None, "rel")] = "nofollow noopener ugc"
    return attrs


_cleaner = bleach.Cleaner(
    tags=ALLOWED_TAGS,
    attributes=ALLOWED_ATTRS,
    protocols={"http", "https", "mailto"},
    strip=True,
    filters=[lambda source: LinkifyFilter(source, callbacks=[_nofollow], skip_tags={"pre", "code"})],
)


@register.filter(name="markdown")
def render_markdown(text):
    """Render user Markdown to sanitised HTML. Raw HTML in the input is stripped."""
    html = md.markdown(text or "", extensions=["fenced_code", "nl2br", "sane_lists"])
    return mark_safe(_cleaner.clean(html))
