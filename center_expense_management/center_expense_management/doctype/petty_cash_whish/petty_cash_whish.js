// Copyright (c) 2026, OmniSync and contributors
// For license information, please see license.txt

frappe.ui.form.on('Petty Cash Whish', {
    refresh: function(frm) {
        const can_send = ['LSA Finance Approver', 'System Manager']
            .some(role => frappe.user_roles.includes(role));

        if (!frm.is_new() && can_send) {
            frm.add_custom_button(__('Send Whish Excel Now'), function() {
                frappe.call({
                    method: 'center_expense_management.tasks.send_whish_excel_now',
                    args: { whish_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __('Generating and sending Whish Excel...')
                }).then(function() {
                    frm.reload_doc();
                    frappe.show_alert({message: __('Whish Excel sent.'), indicator: 'green'});
                });
            });
        }

        if (!frm.is_new() && frm.doc.excel_file) {
            frm.add_custom_button(__('Download Latest Excel'), function() {
                const separator = frm.doc.excel_file.includes('?') ? '&' : '?';
                const version = encodeURIComponent(frm.doc.modified || Date.now());
                window.open(`${frm.doc.excel_file}${separator}v=${version}`, '_blank');
            });
        }
    }
});
