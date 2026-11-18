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


DESK_PREFIXES = ("/app", "/desk")


def desk_url(route: str = "") -> str:
	"""Version-correct Desk URL, e.g. desk_url("home") -> /app/home (v15) or /desk/home (v16)."""
	route = (route or "").strip("/")
	return f"{desk_base()}/{route}" if route else desk_base()


def is_desk_path(path: str, route: str) -> bool:
	"""True when path is the given Desk route under either the v15 or v16 prefix."""
	route = (route or "").strip("/")
	return any(path == f"{prefix}/{route}" for prefix in DESK_PREFIXES)


def permission_hook_passthrough() -> bool | None:
	"""Continue native/specific permission checks on both supported hook contracts.

	v15 stops on True and skips None; v16 continues on True and denies None.
	An unconditional True on v15 would skip tenant and private-file hooks.
	"""
	return True if frappe_major_version() >= 16 else None


def in_test() -> bool:
	"""v16 exposes frappe.in_test; v15 only has frappe.flags.in_test."""
	return bool(getattr(frappe, "in_test", False) or frappe.flags.in_test)
