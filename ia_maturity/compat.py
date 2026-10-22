"""Small helpers that keep the app working on Frappe v15 and v16."""

import frappe


def frappe_major_version() -> int:
	try:
		return int(str(frappe.__version__).split(".")[0])
	except (ValueError, AttributeError):
		return 15


def desk_base() -> str:
	"""Desk URL prefix: /app on v15, /desk on v16+ (v16 redirects /app to /desk)."""
	return "/desk" if frappe_major_version() >= 16 else "/app"


def in_test() -> bool:
	"""v16 exposes frappe.in_test; v15 only has frappe.flags.in_test."""
	return bool(getattr(frappe, "in_test", False) or frappe.flags.in_test)
