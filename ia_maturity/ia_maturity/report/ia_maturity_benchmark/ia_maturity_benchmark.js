frappe.query_reports["IA Maturity Benchmark"] = {
	filters: [
		{ fieldname: "template", label: __("Template"), fieldtype: "Link", options: "IA Maturity Template" },
		{
			fieldname: "sector", label: __("Sector"), fieldtype: "Select",
			options: "\nBanking & Financial Services\nInsurance\nCapital Markets\nGovernment / Semi-Government\nEnergy & Utilities\nHealthcare\nRetail & Consumer\nReal Estate & Construction\nTelecom & Technology\nManufacturing\nNon-Profit\nOther",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		return data && data.bold ? `<b>${value}</b>` : value;
	},
};
