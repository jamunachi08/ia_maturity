frappe.listview_settings["IA Audit Issue"] = {
	add_fields: ["status", "due_date", "closed_on"],
	get_indicator(doc) {
		if (doc.status === "Closed") return [__("Closed"), "green", "status,=,Closed"];
		if (doc.status === "Risk Accepted") return [__("Risk Accepted"), "gray", "status,=,Risk Accepted"];
		if (doc.due_date && frappe.datetime.get_diff(doc.due_date, frappe.datetime.get_today()) < 0)
			return [__("Overdue"), "red", "status,!=,Closed"];
		return [__(doc.status), doc.status === "In Progress" ? "blue" : "orange", `status,=,${doc.status}`];
	},
};
