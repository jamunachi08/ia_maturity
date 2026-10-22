frappe.listview_settings["IA Maturity Action"] = {
	add_fields: ["status", "priority", "due_date"],
	get_indicator(doc) {
		if (doc.status === "Completed") return [__("Completed"), "green", "status,=,Completed"];
		if (doc.status === "Cancelled") return [__("Cancelled"), "gray", "status,=,Cancelled"];
		if (doc.due_date && frappe.datetime.get_diff(doc.due_date, frappe.datetime.get_today()) < 0)
			return [__("Overdue"), "red", "status,!=,Completed"];
		return [__(doc.status), doc.status === "In Progress" ? "blue" : "orange", `status,=,${doc.status}`];
	},
};
