frappe.ui.form.on('Petty Cash Settings', {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Send Reminders Now'), () => {
                frappe.call({
                    method: 'center_expense_management.tasks.send_monthly_reminders',
                    args: { force: 1 },
                    freeze: true,
                    freeze_message: __('Sending petty cash reminders...')
                }).then((r) => {
                    frappe.msgprint(__('Sent {0} reminder(s).', [r.message || 0]));
                });
            });
        }
    }
});
