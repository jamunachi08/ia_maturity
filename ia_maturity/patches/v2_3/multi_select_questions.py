"""v2.3: multi-select question provision.

Excel/HTML 20Q remains single A–D. Backfill selection_mode=Single and
multi_score_method=Highest on template questions and answer snapshots so
legacy rows stay single-select after the schema change.
"""
import frappe


def execute():
	_backfill_template_questions()
	_backfill_answer_snapshots()


def _backfill_template_questions():
	if not frappe.db.has_column("IA Maturity Template Question", "selection_mode"):
		return
	frappe.db.sql(
		"""update `tabIA Maturity Template Question`
		set selection_mode = ifnull(nullif(selection_mode, ''), 'Single'),
			multi_score_method = ifnull(nullif(multi_score_method, ''), 'Highest')"""
	)


def _backfill_answer_snapshots():
	if not frappe.db.has_column("IA Maturity Assessment Answer", "selection_mode"):
		return
	frappe.db.sql(
		"""update `tabIA Maturity Assessment Answer`
		set selection_mode = ifnull(nullif(selection_mode, ''), 'Single'),
			multi_score_method = ifnull(nullif(multi_score_method, ''), 'Highest')"""
	)
