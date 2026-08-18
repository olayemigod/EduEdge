const EDGEDGE_BRANCH_COST_CENTERS = [
	"cost_center",
	"default_income_cost_center",
	"default_expense_cost_center",
];

const EDGEDGE_BRANCH_ACCOUNT_QUERIES = {
	school_fees_income_account: { root_type: "Income" },
	cbt_exam_fees_income_account: { root_type: "Income" },
	admission_registration_income_account: { root_type: "Income" },
	transport_fees_income_account: { root_type: "Income" },
	hostel_boarding_income_account: { root_type: "Income" },
	books_materials_income_account: { root_type: "Income" },
	uniform_sales_income_account: { root_type: "Income" },
	other_income_account: { root_type: "Income" },
	default_receivable_account: { account_type: "Receivable" },
	default_cash_account: { account_type: "Cash" },
	default_bank_account: { account_type: "Bank" },
	default_payment_gateway_account: { account_type: ["in", ["Bank", "Cash"]] },
	default_discount_account: { root_type: "Expense" },
	default_scholarship_bursary_account: { root_type: "Expense" },
	default_write_off_account: { root_type: "Expense" },
	default_inventory_account: { account_type: "Stock" },
	default_cost_of_goods_sold_account: { root_type: "Expense" },
	default_stock_adjustment_account: { root_type: "Expense" },
};

frappe.ui.form.on("EduEdge School Branch", {
	setup(frm) {
		frm.set_query("institution", () => ({
			filters: { company: frm.doc.company || undefined, enabled: 1 },
		}));
		for (const fieldname of EDGEDGE_BRANCH_COST_CENTERS) {
			frm.set_query(fieldname, () => ({
				filters: { company: frm.doc.company, is_group: 0, disabled: 0 },
			}));
		}
		for (const [fieldname, accountFilters] of Object.entries(EDGEDGE_BRANCH_ACCOUNT_QUERIES)) {
			frm.set_query(fieldname, () => ({
				filters: { company: frm.doc.company, is_group: 0, disabled: 0, ...accountFilters },
			}));
		}
		frm.set_query("default_warehouse", () => ({
			filters: { company: frm.doc.company, is_group: 0, disabled: 0 },
		}));
	},

	async institution(frm) {
		if (!frm.doc.institution) {
			await frm.set_value("institution_type", null);
			return;
		}
		const response = await frappe.db.get_value(
			"EduEdge Institution",
			frm.doc.institution,
			["company", "institution_type"]
		);
		const values = response?.message || {};
		if (values.company && frm.doc.company !== values.company) {
			await frm.set_value("institution", null);
			frappe.msgprint(__("Select an Institution that belongs to the chosen Company."));
			return;
		}
		if (values.institution_type) await frm.set_value("institution_type", values.institution_type);
	},

	company(frm) {
		if (frm.doc.institution) frm.set_value("institution", null);
		const dependentFields = [
			...EDGEDGE_BRANCH_COST_CENTERS,
			...Object.keys(EDGEDGE_BRANCH_ACCOUNT_QUERIES),
			"default_warehouse",
		];
		for (const fieldname of dependentFields) {
			if (frm.doc[fieldname]) frm.set_value(fieldname, null);
		}
	},
});
