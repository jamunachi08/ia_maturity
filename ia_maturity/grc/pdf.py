"""Self-contained report renderer with embedded Arabic fonts and no network fetches."""
import frappe
from ia_maturity.branding import get_brand
from ia_maturity.report_data import arabic_font_css
from ia_maturity.grc.report_fonts import report_font_css
from ia_maturity.grc.report_style import report_context
from ia_maturity.grc.color_policy import get_ranges


def embedded_only_fetcher():
    """URL fetcher that allows only embedded data: URLs, so reports never make network or file reads.

    WeasyPrint 68+ (pinned at 70.0 by current Frappe v15/v16) replaced default_url_fetcher with the
    URLFetcher class; older releases only have the function. Both paths enforce the same rule.
    """
    try:
        from weasyprint.urls import URLFetcher
    except ImportError:  # WeasyPrint < 68
        from weasyprint import default_url_fetcher

        def fetch(url, *args, **kwargs):
            if not url.startswith("data:"):
                raise ValueError("IA reports only allow embedded resources.")
            return default_url_fetcher(url, *args, **kwargs)

        return fetch
    return URLFetcher(allowed_protocols={"data"}, allow_redirects=False)


def render_html(html):
    from weasyprint import HTML

    return HTML(string=html, url_fetcher=embedded_only_fetcher()).write_pdf()


def render(context):
    html = frappe.render_template("ia_maturity/templates/grc_report.html",
        {"r": report_context(context,get_ranges()), "brand": get_brand(True), "font_css": report_font_css() + arabic_font_css()})
    return render_html(html)
