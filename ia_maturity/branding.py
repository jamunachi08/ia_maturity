"""AlphaX brand constants (product: AlphaX, company: IRSAA Business Solutions).

Every branded surface (portal, PDF report, e-mail, desk) reads from here, so a
re-brand is a one-file change plus the images in public/images/.
"""

import base64
import os
from functools import lru_cache

import frappe

PRODUCT = "AlphaX"
PRODUCT_TITLE = "AlphaX IA Maturity"
MODULE_TITLE = "Internal Audit Maturity Assessment"
COMPANY = "IRSAA Business Solutions"
SUPPORT_EMAIL = "erpsupport@irsaa.com"
WEBSITE = "https://irsaa.com"

# Colours sampled from the supplied logos
INK = "#181818"  # AlphaX black
PRIMARY = "#12506E"  # IRSAA blue
PRIMARY_DARK = "#0C3A50"
PRIMARY_SOFT = "#E3EEF3"
SLATE = "#5A6562"  # IRSAA "Business Solutions" grey

ASSET_BASE = "/assets/ia_maturity/images/"
IMAGES = {
	"logo": "alphax_logo.png",
	"logo_white": "alphax_logo_white.png",
	"mark": "alphax_mark.png",
	"mark_white": "alphax_mark_white.png",
	"wordmark": "alphax_wordmark.png",
	"wordmark_white": "alphax_wordmark_white.png",
	"icon": "alphax_icon.png",
	"company_logo": "irsaa_logo.png",
}


def asset_url(key):
	return ASSET_BASE + IMAGES[key]


@lru_cache(maxsize=16)
def data_uri(key):
	"""Base64 data URI: used in the PDF so wkhtmltopdf never needs network access."""
	path = os.path.join(os.path.dirname(__file__), "public", "images", IMAGES[key])
	with open(path, "rb") as fh:
		return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def get_brand(embed=False):
	"""Brand dict for Jinja (print format) and Python callers.

	embed=True returns images as data URIs (PDF); otherwise absolute asset URLs (web / e-mail).
	"""
	if embed:
		images = {k: data_uri(k) for k in IMAGES}
	else:
		images = {k: frappe.utils.get_url(asset_url(k)) for k in IMAGES}
	return frappe._dict(
		product=PRODUCT,
		product_title=PRODUCT_TITLE,
		module_title=MODULE_TITLE,
		company=COMPANY,
		support_email=SUPPORT_EMAIL,
		website=WEBSITE,
		ink=INK,
		primary=PRIMARY,
		primary_dark=PRIMARY_DARK,
		primary_soft=PRIMARY_SOFT,
		slate=SLATE,
		images=frappe._dict(images),
	)
