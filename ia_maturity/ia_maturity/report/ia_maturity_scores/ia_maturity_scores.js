frappe.query_reports["IA Maturity Scores"] = {
	filters: [
		{ fieldname: "entity", label: __("Entity"), fieldtype: "Link", options: "IA Maturity Entity" },
		{ fieldname: "template", label: __("Template"), fieldtype: "Link", options: "IA Maturity Template" },
		{ fieldname: "respondent_role", label: __("Perspective"), fieldtype: "Select",
		  options: "\nChief Audit Executive\nAudit Committee Member\nBoard Member\nExecutive Management\nInternal Audit Staff\nSecond Line (Risk / Compliance)\nExternal Consultant\nOther" },
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date" },
		{ fieldname: "group_by", label: __("Group By"), fieldtype: "Select", options: "\nEntity\nRespondent Perspective" },
		{ fieldname: "include_drafts", label: __("Include Drafts"), fieldtype: "Check" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "maturity_level" && data) {
			const c = { Critical: "red", Low: "orange", Medium: "#9A6F00", High: "green", Leading: "blue" }[data.maturity_level];
			if (c) value = `<span style="color:${c};font-weight:600">${value}</span>`;
		}
		return value;
	},
};
