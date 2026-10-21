// Copyright (c) 2026, OmniSync and contributors
// For license information, please see license.txt

frappe.ui.form.on('Petty Cash Whish', {
    refresh: function(frm) {
        const can_send = ['LSA Finance Approver', 'System Manager']
            .some(role => frappe.user_roles.includes(role));

        if (!frm.is_new()) {
            frm.add_custom_button(__('View Whish Excel'), function() {
                if (frm.is_dirty()) {
                    frappe.msgprint(__('Save the Whish Payment Batch before viewing its Excel preview.'));
                    return;
                }
                show_whish_excel_preview(frm);
            });
        }

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
    }
});

function show_whish_excel_preview(frm) {
    const escape = value => frappe.utils.escape_html(String(value == null ? '' : value));
    const rows = (frm.doc.employees || []).map(function(row, index) {
        const amount = format_currency(
            flt(row.salary_received_net),
            row.currency || undefined,
            2
        );
        return `
            <tr>
                <td class="text-center">${index + 1}</td>
                <td>${escape(row.employee_name)}</td>
                <td>${escape(row.phone_number)}</td>
                <td>${escape(row.whish_id)}</td>
                <td class="text-right">${escape(amount)}</td>
                <td class="text-center">${escape(row.currency)}</td>
            </tr>`;
    }).join('');

    const body = rows || `
        <tr>
            <td colspan="6" class="text-center text-muted">
                ${__('No employees are included in this payment batch.')}
            </td>
        </tr>`;

    const dialog = new frappe.ui.Dialog({
        title: __('Whish Excel Preview - {0}', [frm.doc.name]),
        size: 'extra-large',
        fields: [{
            fieldname: 'preview',
            fieldtype: 'HTML'
        }],
        primary_action_label: __('Close'),
        primary_action: function() {
            dialog.hide();
        }
    });

    dialog.fields_dict.preview.$wrapper.html(`
        <div class="whish-excel-preview">
            <div class="text-muted small mb-3">
                ${__('Preview of the saved data used to generate the private Excel attachment.')}
            </div>
            <div class="whish-excel-scroll">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>${__('Number')}</th>
                            <th>${__('NAME')}</th>
                            <th>${__('Phone Number')}</th>
                            <th>${__('Whish ID')}</th>
                            <th>${__('Salary received by the employee ( NET)')}</th>
                            <th>${__('Currency')}</th>
                        </tr>
                    </thead>
                    <tbody>${body}</tbody>
                </table>
            </div>
        </div>
        <style>
            .whish-excel-scroll {
                max-height: 65vh;
                overflow: auto;
            }
            .whish-excel-preview table {
                min-width: 980px;
                margin-bottom: 0;
                background: var(--card-bg);
            }
            .whish-excel-preview thead th {
                position: sticky;
                top: 0;
                z-index: 1;
                padding: 10px;
                border-color: #1f2937;
                background: #9dc3e6;
                color: #111827;
                font-weight: 700;
                text-align: center;
                white-space: nowrap;
            }
            .whish-excel-preview tbody td {
                padding: 9px 10px;
                border-color: #1f2937;
                vertical-align: middle;
            }
        </style>`);

    dialog.show();
}
