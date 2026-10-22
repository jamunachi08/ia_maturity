"""v1.3: Arabic text for the seed questionnaire, issue-register settings and benchmarking defaults."""

from ia_maturity.install import apply_arabic_seed, ensure_settings


def execute():
	ensure_settings()
	apply_arabic_seed()
