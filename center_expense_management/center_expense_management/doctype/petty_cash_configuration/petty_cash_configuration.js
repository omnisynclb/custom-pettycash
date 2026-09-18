// Copyright (c) 2026, OmniSync and contributors
// For license information, please see license.txt

frappe.ui.form.on('Petty Cash Configuration', {
    setup: function(frm) {
        frm.set_query('cost_center', function() {
            return {
                filters: {
                    is_group: 0,
                    disabled: 0
                }
            };
        });
    }
});
