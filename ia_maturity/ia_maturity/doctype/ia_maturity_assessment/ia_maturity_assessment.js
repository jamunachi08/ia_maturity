// Copyright (c) 2026, IRSAA Business Solutions (AlphaX)
// License: MIT

frappe.ui.form.on("IA Maturity Assessment", {
	setup(frm) {
		frm.set_query("template", () => ({ filters: { is_active: 1 } }));
		frm.set_query("entity", () => ({ filters: { is_active: 1 } }));
	},

	template(frm) {
		if (frm.doc.template && frm.doc.docstatus === 0) {
			frm.call({ doc: frm.doc, method: "load_questions" }).then(() => frm.refresh_field("answers"));
		}
	},

	refresh(frm) {
		render_results(frm);
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open in Portal"), () =>
				window.open(`/ia-assessment?name=${encodeURIComponent(frm.doc.name)}`, "_blank")
			);
		}
		if (frm.doc.docstatus === 1) {
			const pdf = (format) =>
				window.open(
					"/api/method/frappe.utils.print_format.download_pdf?" +
						new URLSearchParams({
							doctype: frm.doctype,
							name: frm.doc.name,
							format,
							no_letterhead: 1,
							language: frm.doc.language || "en",
						}),
					"_blank"
				);
			frm.add_custom_button(__("Internal Report (IRSAA)"), () => pdf("IA Maturity Internal Report"), __("PDF"));
			frm.add_custom_button(__("Client Report"), () => pdf("IA Maturity Report"), __("PDF"));
			frm.add_custom_button(
				__("Improvement Actions"),
				() => frappe.set_route("List", "IA Maturity Action", { assessment: frm.doc.name }),
				__("View")
			);
			if (frappe.user.has_role(["IA Maturity Reviewer", "IA Maturity Manager", "System Manager"])) {
				if (frappe.perm.has_perm(frm.doctype, 0, "cancel")) {
					frm.add_custom_button(
						__("Return to Respondent"),
						() =>
							frappe.prompt(
								[{ fieldname: "comments", fieldtype: "Small Text", label: __("What should the respondent correct?"), reqd: 1 }],
								(v) =>
									frappe
										.call("ia_maturity.ia_maturity.doctype.ia_maturity_assessment.ia_maturity_assessment.return_to_respondent", {
											name: frm.doc.name,
											comments: v.comments,
										})
										.then((r) => frappe.set_route("Form", frm.doctype, r.message)),
								__("Return to Respondent"),
								__("Return")
							),
						__("Review")
					);
				}
				["Reviewed", "Approved"].forEach((status) => {
					if (frm.doc.review_status !== status) {
						frm.add_custom_button(
							__(status),
							() =>
								frappe.prompt(
									[{ fieldname: "comments", fieldtype: "Small Text", label: __("Reviewer Comments"),
									   default: frm.doc.reviewer_comments || "" }],
									(v) =>
										frappe
											.call({
												method: "ia_maturity.ia_maturity.doctype.ia_maturity_assessment.ia_maturity_assessment.update_review",
												args: { name: frm.doc.name, status, comments: v.comments || "" },
												freeze: true,
											})
											.then(() => {
												frappe.show_alert({ message: __("Marked as {0}", [__(status)]), indicator: "green" });
												frm.reload_doc();
											}),
									__("Mark as {0}", [__(status)]),
									__(status)
								),
							__("Review")
						);
					}
				});
			}
		}
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(__("Reload Questions from Template"), () =>
				frm.call({ doc: frm.doc, method: "load_questions" }).then(() => frm.dirty() || frm.refresh_field("answers"))
			);
		}
	},
});

frappe.ui.form.on("IA Maturity Assessment Answer", {
	selected_option(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const map = { A: "option_a", B: "option_b", C: "option_c", D: "option_d" };
		const txt = map[row.selected_option] ? row[map[row.selected_option]] : row.selected_option === "N/A" ? "Not applicable" : "";
		frappe.model.set_value(cdt, cdn, "selected_description", txt);
	},
});

function render_results(frm) {
	const wrap = frm.get_field("results_html").$wrapper;
	const rows = frm.doc.section_scores || [];
	if (!rows.length || !frm.doc.answered_count) {
		wrap.html(`<div class="text-muted small">${__("Scores appear after answers are saved.")}</div>`);
		return;
	}
	const colours = { Critical: "#B42318", Low: "#BF530B", Medium: "#9A6F00", High: "#2D7A33", Leading: "#1C5CA3" };
	const bar = (pct, lvl) =>
		`<div class="iam-desk-track"><div class="iam-desk-bar" style="width:${Math.max(1, pct)}%;background:${colours[lvl] || "var(--gray-600)"}"></div></div>`;
	wrap.html(`
		<div class="iam-desk">
			<div class="iam-desk-brand"><img src="/assets/ia_maturity/images/alphax_mark.png" alt="">AlphaX · ${__("Maturity Results")}</div>
			<div class="iam-desk-head">
				<div class="iam-desk-big">${format_number(frm.doc.overall_score, null, 1)}<small>%</small></div>
				<div><span class="indicator-pill ${level_colour(frm.doc.maturity_level)}">${frappe.utils.escape_html(frm.doc.maturity_level || "")}</span>
				<div class="text-muted small" style="margin-top:4px">${frm.doc.answered_count} / ${frm.doc.question_count} ${__("answered")} · ${frm.doc.findings_count || 0} ${__("findings")}</div></div>
			</div>
			<table class="iam-desk-table">
				${rows
					.map(
						(r) => `<tr><td>${frappe.utils.escape_html(r.section_title)}</td><td style="width:45%">${bar(r.score_pct, r.maturity_level)}</td>
						<td class="text-right" style="width:60px">${format_number(r.score_pct, null, 1)}%</td><td style="width:90px">${frappe.utils.escape_html(r.maturity_level)}</td></tr>`
					)
					.join("")}
			</table>
		</div>`);
}

function level_colour(level) {
	return { Critical: "red", Low: "orange", Medium: "yellow", High: "green", Leading: "blue" }[level] || "gray";
}
