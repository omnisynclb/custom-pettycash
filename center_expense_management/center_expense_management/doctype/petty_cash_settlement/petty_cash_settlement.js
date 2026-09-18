frappe.ui.form.on('Petty Cash Settlement', {
    onload: function(frm) {
        if (frm.is_new() && (!frm.doc.month_name || !frm.doc.settlement_year)) {
            const today = frappe.datetime.get_today().split('-');
            const months = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ];
            frm.set_value('month_name', months[cint(today[1]) - 1]);
            frm.set_value('settlement_year', cint(today[0]));
        }
    },

    setup: function(frm) {
        frm.set_query('account', function() {
            return {
                filters: {
                    company: frm.doc.company,
                    root_type: 'Expense',
                    is_group: 0,
                    disabled: 0
                }
            };
        });
    },
    center_officer: function(frm) {
        load_petty_cash_configuration(frm);
    },

    month_name: function(frm) {
        sync_settlement_month(frm);
    },

    settlement_year: function(frm) {
        sync_settlement_month(frm);
    },

    petty_cash_limit: function(frm) {
        calculate_totals(frm);
    },

    refresh: function(frm) {
        calculate_totals(frm);
        configure_account_information(frm);
        configure_payment_information(frm);

        frm.set_df_property('amount', 'read_only', 1);
        frm.set_df_property('payment_date', 'read_only', 1);
    },

    expenses_add: function(frm) {
        calculate_totals(frm);
    },

    expenses_remove: function(frm) {
        calculate_totals(frm);
    },

    account: function(frm) {
        load_account_balance(frm);
    },

    payment_status: function(frm) {
        if (frm.doc.payment_status === "Paid") {
            frm.set_value("payment_date", frappe.datetime.get_today());
        }
    },

    before_workflow_action: function(frm) {

        const return_actions = [
         'Return to Center Officer',
         'Return to Accountant',
         'Return to Finance',
         'Return to Operations',
         'Return to Director',
         'Return to Treasurer'
        ];

       if (return_actions.includes(frm.selected_workflow_action)) {
          const action = frm.selected_workflow_action;

          frappe.dom.unfreeze();

          frappe.prompt(
             [
                  {
                      fieldname: 'return_reason',
                      fieldtype: 'Small Text',
                      label: __('Reason for Return'),
                      reqd: 1
                  }
             ],
             function(values) {
                frm.call('add_return_comment', {
                    reason: values.return_reason,
                    action: action
                }).then(function() {
                // Prevent this action from being intercepted again
                   frm.selected_workflow_action = null;

                // Execute the workflow action
                   frm.workflow_action(action);
                });
            },
            __('Return Settlement'),
            __('Return')
          );

          return false;
       }
        // Receipt required when Center Officer submits
        if (frm.selected_workflow_action === 'Submit for Accountant Review') {
            (frm.doc.expenses || []).forEach(function(row) {
                if (!row.receipt) {
                    frappe.throw(
                        __('Expense row {0}: Invoice/Receipt attachment is required before submission.', [row.idx])
                    );
                }
            });

            // One settlement per Center Officer per month
            if (frm.doc.center_officer && frm.doc.month) {
                let selected_date = frappe.datetime.str_to_obj(frm.doc.month);

                let month_start = frappe.datetime.obj_to_str(
                    new Date(
                        selected_date.getFullYear(),
                        selected_date.getMonth(),
                        1
                    )
                );

                let next_month = new Date(
                    selected_date.getFullYear(),
                    selected_date.getMonth() + 1,
                    1
                );

                let month_end = frappe.datetime.obj_to_str(next_month);

                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Petty Cash Settlement',
                        filters: [
                            ['center_officer', '=', frm.doc.center_officer],
                            ['month', '>=', month_start],
                            ['month', '<', month_end],
                            ['name', '!=', frm.doc.name]
                        ],
                        fields: ['name'],
                        limit_page_length: 1
                    },
                    async: false,
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            frappe.throw(
                                __('This Center Officer already has a Petty Cash Settlement for {0}. Only one settlement is allowed per month.', [
                                    frappe.datetime.str_to_user(frm.doc.month).substring(0, 7)
                                ])
                            );
                        }
                    }
                });
            }
        }
    },

    validate: function(frm) {
        let limit = flt(frm.doc.petty_cash_limit);
        let total = flt(frm.doc.total_expenses);

        // Check that every expense has a positive amount
        (frm.doc.expenses || []).forEach(function(row) {
            if (flt(row.amount) <= 0) {
                frappe.throw(
                    __('Expense row {0}: Amount must be greater than 0.', [row.idx])
                );
            }
        });

        // Check that total expenses do not exceed the petty cash limit
        if (total > limit) {
            frappe.throw(
                __('Total Expenses cannot exceed the Petty Cash Limit.')
            );
        }
    }
});

function configure_account_information(frm) {
    const state = frm.doc.workflow_state || 'Draft';
    const visible_states = [
        'Pending Finance Review',
        'Pending Operations Approval',
        'Pending Director Approval',
        'Pending Treasurer Approval',
        'Pending President Approval',
        'Completed'
    ];
    const finance_can_edit = state === 'Pending Finance Review';

    frm.toggle_display('expense_account_section', visible_states.includes(state));
    frm.set_df_property('account', 'read_only', !finance_can_edit);
}

function configure_payment_information(frm) {
    const state = frm.doc.workflow_state || 'Draft';
    const visible_states = [
        'Pending Finance Review',
        'Pending Operations Approval',
        'Pending Director Approval',
        'Pending Treasurer Approval',
        'Pending President Approval',
        'Completed'
    ];
    const finance_can_edit = state === 'Pending Finance Review';

    frm.toggle_display('payment_information_section', visible_states.includes(state));
    frm.set_df_property('payment_method', 'read_only', !finance_can_edit);
    frm.set_df_property('report_email', 'read_only', !finance_can_edit);
}

function sync_settlement_month(frm) {
    const months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    const month_number = months.indexOf(frm.doc.month_name) + 1;
    const year = cint(frm.doc.settlement_year);

    if (month_number > 0 && year >= 2000 && year <= 2100) {
        const value = `${year}-${String(month_number).padStart(2, '0')}`;
        frm.set_value('settlement_month', value);
        frm.set_value('month', `${value}-01`);
    }
}

frappe.ui.form.on('Petty Cash Expense', {
    amount: function(frm) {
        calculate_totals(frm);
    }
});

function load_petty_cash_configuration(frm) {
    if (!frm.doc.center_officer) {
        return;
    }

    frappe.db.get_list('Petty Cash Configuration', {
        filters: {
            center_officer: frm.doc.center_officer
        },
        fields: [
            'cost_center',
            'petty_cash_account',
            'petty_cash_limit'
        ],
        limit: 1
    }).then(function(records) {
        if (records.length === 0) {
            frappe.msgprint(
                __('No Petty Cash Configuration was found for this Center Officer.')
            );
            return;
        }

        let config = records[0];

        frm.set_value('cost_center', config.cost_center);
        frm.set_value('petty_cash_account', config.petty_cash_account);
        frm.set_value('petty_cash_limit', config.petty_cash_limit);

        calculate_totals(frm);
    });
}

function load_account_balance(frm) {
    if (!frm.doc.account) {
        frm.set_value('amount', 0);
        return;
    }

    frm.call('load_account_balance').then(function(r){
        if (r.message === undefined || r.message === null){
            return;
        }

        frm.set_value('amount',r.message);
   });
}

function calculate_totals(frm) {
    let total = 0;

    (frm.doc.expenses || []).forEach(function(row) {
        total += flt(row.amount);
    });

    frm.set_value('total_expenses', total);

    let limit = flt(frm.doc.petty_cash_limit);
    frm.set_value('remaining_balance', limit - total);
}
