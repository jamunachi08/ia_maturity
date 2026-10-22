"""v1.5: landing page sign-up – defaults for the new settings on existing sites."""

from ia_maturity.install import ensure_settings


def execute():
	ensure_settings()
