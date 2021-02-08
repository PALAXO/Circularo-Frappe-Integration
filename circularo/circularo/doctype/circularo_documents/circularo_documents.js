// Copyright (c) 2021, Circularo and contributors
// For license information, please see license.txt

/**
 * Circularo Documents doctype frontend
 */
frappe.ui.form.on('Circularo Documents', {
    /**
     * Opens document
     * @param frm {Object}
     */
    open_in_app: function(frm) {
        frappe.call({
            method: "circularo.circularo.doctype.circularo_documents.circularo_documents.get_app_url",
            args: {
                doctype: frm.doctype,
                docname: frm.docname
            },
            callback: function(val) {
                const args = val.message;
                openNewTab(args.message);
            }
        });
    },

    /**
     * Opens document in Circularo
     * @param frm {Object}
     */
    open_in_circularo: function(frm) {
        frappe.call({
            method: "circularo.circularo.doctype.circularo_documents.circularo_documents.get_circularo_url",
            args: {
                doctype: frm.doctype,
                docname: frm.docname
            },
            callback: function(val) {
                const args = val.message;
                openNewTab(args.message);
            }
        });
    },

    /**
     * Opens downloaded PDF file
     * @param frm {Object}
     */
    view_file: function(frm) {
        frappe.call({
            method: "circularo.circularo.doctype.circularo_documents.circularo_documents.view_file",
            args: {
                doctype: frm.doctype,
                docname: frm.docname
            },
            callback: function(val) {
                const args = val.message;
                openNewTab(args.message);
            }
        });
    },

    /**
     * Downloads signed file or shows link to sign
     * @param frm {Object}
     */
    download_file: function(frm) {
        const progressBar = frappe.show_progress("Downloading", 1, 3, "Downloading signed PDF file.");

        frappe.call({
            method: "circularo.circularo.doctype.circularo_integration.circularo_integration.download_file",
            args: {
                history_name: frm.docname,
                download_manual_sign: 1
            },
            callback: function(val) {
                const args = val.message;
                progressBar.hide();

                if (args.status !== 0) {
                    showErrorMessage(args.message);
                } else {
                    const messageObject = args.message;
                    if (messageObject.downloaded) {
                        //Successfully downloaded signed file
                        showSuccessMessage("Signed file has been successfully downloaded.", "Successfully downloaded");
                    } else {
                        //Not signed yet -> show link to sign
                        let opened = false;
                        const msg = frappe.msgprint({
                            title: "Not signed",
                            message: "Document has not been signet yet.",
                            primary_action: {
                                label: "Sign now",
                                action: function () {
                                    if (!opened) {
                                        openNewTab(messageObject.sign_url);
                                        msg.hide();
                                        opened = true;
                                    }
                                }
                            }
                        });
                    }
                }
            }
        });
    }
});
