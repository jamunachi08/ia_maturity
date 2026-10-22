frappe.ui.form.on("IA Maturity Template", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("New Version"), () => {
				frappe.prompt(
					[{ fieldname: "template_name", fieldtype: "Data", label: __("New Template Name"), reqd: 1,
					   default: frm.doc.template_name + " v" + (flt(frm.doc.version || 1) + 1).toFixed(1) }],
					(v) => {
						const doc = frappe.model.copy_doc(frm.doc);
						doc.template_name = v.template_name;
						doc.version = (flt(frm.doc.version || 1) + 1).toFixed(1);
						frappe.set_route("Form", doc.doctype, doc.name);
					},
					__("Create New Version")
				);
			});
			frm.add_custom_button(__("Assessments"), () =>
				frappe.set_route("List", "IA Maturity Assessment", { template: frm.doc.name })
			);
		}
		frm.set_intro(
			__("Answers keep a snapshot of the question text, so editing this template never changes submitted assessments. For substantive changes, create a new version."),
			"blue"
		);
	},
});
