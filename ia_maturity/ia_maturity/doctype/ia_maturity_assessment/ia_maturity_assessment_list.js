frappe.listview_settings["IA Maturity Assessment"] = {
	add_fields: ["maturity_level", "review_status", "docstatus", "overall_score"],
	get_indicator(doc) {
		if (doc.docstatus === 0) return [__("Draft"), "gray", "docstatus,=,0"];
		if (doc.docstatus === 2) return [__("Cancelled"), "red", "docstatus,=,2"];
		const c = { "Pending Review": "orange", Reviewed: "blue", Approved: "green", Returned: "red" };
		return [__(doc.review_status || "Submitted"), c[doc.review_status] || "blue", `review_status,=,${doc.review_status}`];
	},
};
