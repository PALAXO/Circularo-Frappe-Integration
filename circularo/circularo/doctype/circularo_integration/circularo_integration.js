// Copyright (c) 2021, Circularo and contributors
// For license information, please see license.txt

/**
 * Circularo Integration doctype frontend
 */
frappe.ui.form.on('Circularo Integration', {
    /**
     * Creates Circularo API token
     * @param frm {Object}
     */
    create_circularo_api_token: function(frm) {
        const dialog = new frappe.ui.Dialog({
            title: "Set credentials",
            fields: [
                {fieldname: "url", label: "Server URL", fieldtype: "Data", default: "https://dev.circularo.com/"},
                {fieldname: "tenant", label: "Tenant", fieldtype: "Data", default: "default"},
                {fieldname: "email", label: "E-Mail", fieldtype: "Data"},
                {fieldname: "password", label: "Password", fieldtype: "Password"}
            ],
            primary_action_label: "Create API Token",
            primary_action: function () {
                dialog.set_message("Checking parameters...");
                let args = dialog.get_values();
                frappe.call({
                    method: "circularo.circularo.doctype.circularo_integration.circularo_integration.create_api_token",
                    args: {
                        url: args.url || "",
                        tenant: args.tenant || "",
                        email: args.email || "",
                        password: args.password || ""
                    },
                    callback: function(val) {
                        const args = val.message;
                        if (args.status === 0) {
                            //Success
                            showSuccessMessage(args.message, "API token created");
                            dialog.hide();
                        } else {
                            //Failed
                            showErrorMessage(args.message, "Failed to create API token");
                            dialog.clear_message()
                        }
                    }
                });
            }
        });

        frm.save().then(function() {
            dialog.show();
        })
    },

    /**
     * Removes Circularo API token
     */
    remove_circularo_api_token: function() {
        frappe.call({
            method: "circularo.circularo.doctype.circularo_integration.circularo_integration.remove_api_token",
            callback: function(val) {
                const args = val.message;
                showSuccessMessage(args.message, "API token removed");
            }
        });
    },

    /**
     * Restores Circularo settings
     */
    restore_settings: function() {
        frappe.call({
            method: "circularo.circularo.doctype.circularo_integration.circularo_integration.restore_settings",
            callback: function() {
                showSuccessMessage("Settings restored");
            }
        });
    }
});
