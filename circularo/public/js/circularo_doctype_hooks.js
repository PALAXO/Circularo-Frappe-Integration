// Copyright (c) 2021, Circularo and contributors
// For license information, please see license.txt

/** Possible Circularo actions */
const CIRCULARO_ACTIONS = Object.freeze({
    SEND: 0,
    SIGN: 1,
    AUTOSIGN: 2
})

// Check for page changes
$(window).on('hashchange', loadCircularoInForm);
$(window).on('load', loadCircularoInForm);

/**
 * Page changed
 * Show Circularo button in form view, if enabled
 */
function loadCircularoInForm() {
    const route = frappe.get_route();
    const view = route[0];
    const doctype = route[1];

    // We are in Form view
    if (view === "Form") {
        const showCircularoButton = function (frm) {
            isEnabled(doctype, view, frm.docname).then(function () {
                //Circularo buttons enabled
                if (!frm.custom_buttons["Send to Circularo"]) {
                    frm.add_custom_button("Send to Circularo", function () {
                        circularoFormAction(frm, CIRCULARO_ACTIONS.SEND);
                    }, "Circularo");
                }

                if (!frm.custom_buttons["Sign in Circularo"]) {
                    frm.add_custom_button("Sign in Circularo", function () {
                        circularoFormAction(frm, CIRCULARO_ACTIONS.SIGN);
                    }, "Circularo");
                }

                if (!frm.custom_buttons["Auto-sign in Circularo"]) {
                    frm.add_custom_button("Auto-sign in Circularo", function () {
                        circularoFormAction(frm, CIRCULARO_ACTIONS.AUTOSIGN);
                    }, "Circularo");
                }
            }).catch(function (e) {
                //Not enabled
            });
        };

        // Waiting for page to load completely
        frappe.after_ajax(function () {
            frappe.ui.form.on(doctype, {
                refresh:showCircularoButton,
                onload_post_render: showCircularoButton
            });
        });
    }
}

// Use Proxy trap to always return "refresh" function in doctype listview settings
frappe.listview_settings = new Proxy(frappe.listview_settings, {
    get: function() {
        //Get original object
        const result = Reflect.get(...arguments) || {};
        //Add refresh function
        result.refresh = function(frm) {
            isEnabled(frm.doctype, "List").then(function() {
                //Circularo buttons enabled
                frm.page.add_action_item("Send to Circularo", function () {
                    circularoListAction(frm, CIRCULARO_ACTIONS.SEND);
                });
                frm.page.add_action_item("Sign in Circularo", function () {
                    circularoListAction(frm, CIRCULARO_ACTIONS.SIGN);
                });
                frm.page.add_action_item("Auto-sign in Circularo", function () {
                    circularoListAction(frm, CIRCULARO_ACTIONS.AUTOSIGN);
                });

                if (frm.get_checked_items().length === 0) {
                    frm.page.hide_actions_menu();
                }
            }).catch(function (e) {
                //Not enabled
            });
        }

        return result;
    }
});


/**
 * Form view action
 * @param frm {Object} Document details
 * @param actionType {number} Action type
 */
function circularoFormAction(frm, actionType) {
    const doctype = frm.doctype;
    const docname = frm.docname;

    sendToCircularo(doctype, docname, actionType, 0, 1).then(function ({ document, progressBar }) {
        progressBar.hide();

        showCreatedMessage([document], actionType);
    }).catch(function (e) {
        if (e.progressBar) {
            e.progressBar.hide();
        }
        showErrorMessage(e.err.message || e.err);
    });
}

/**
 * List view action
 * @param frm {Object} Info about checked documents
 * @param actionType {number} Action type
 */
function circularoListAction(frm, actionType) {
    const doctype = frm.doctype;

    const items = frm.get_checked_items();
    const createdDocuments = [];
    let myProgressBar = void 0;

    let p = Promise.resolve();
    // Go through all checked documents
    for (const [index, value] of Object.entries(items)) {
        p = p.then(function() {
            return sendToCircularo(doctype, value.name, actionType, index, items.length)
        }).then(function ({ document, progressBar }) {
            createdDocuments.push(document);
            myProgressBar = progressBar;
        });
    }

    p.then(function() {
        //All documents send
        myProgressBar.hide();
        showCreatedMessage(createdDocuments, actionType);
    }).catch(function (e) {
        //Error
        if (e.progressBar) {
            e.progressBar.hide();
        }
        showErrorMessage(e.err.message || e.err);
    });
}

/**
 * Sends document to Circularo
 * @param doctype {string} Frappe DocType
 * @param docname {string} Frappe DocName
 * @param actionType {number} Action type
 * @param index {number} Index of currently processed document
 * @param length {number} Count of processed documents
 * @returns {Promise<Object>}
 */
function sendToCircularo(doctype, docname, actionType, index, length) {
    //Check how many steps there will be
    let actualStep, totalSteps;
    if (length === 1) {
        actualStep = 0;
        totalSteps = 3;
    } else {
        actualStep = index * 3;
        totalSteps = length * 3;
    }

    const progressText = (length === 1) ? "" : "(" + (parseInt(index) + 1) + "/" + length + ") ";
    const doc = (length === 1) ? "document" : "documents";

    //Archive parameters
    let title = "Sending " + doc + " to Circularo";
    let text = progressText + "Archiving document '" + docname + "'...";
    let isSign = 0;
    let isAutosign = 0;

    if (actionType === CIRCULARO_ACTIONS.SIGN) {
        //Sign parameters
        title = "Preparing " + doc + " to be signed";
        text = progressText + "Preparing document '" + docname + "' to be signed...";
        isSign = 1;
        isAutosign = 0;

    } else if (actionType === CIRCULARO_ACTIONS.AUTOSIGN) {
        //Autosign parameters
        title = "Signing " + doc + " in Circularo";
        text = progressText + "Signing document '" + docname + "'...";
        isSign = 1;
        isAutosign = 1;
    }

    let progressBar = frappe.show_progress(title, actualStep++, totalSteps, text);
    progressBar.show();

    let myDocument;
    return new Promise(function(resolve, reject) {
        //Upload given file to Circularo
        uploadFile(doctype, docname).then(function (file) {
            progressBar = frappe.show_progress(title, actualStep++, totalSteps, text);
            //Create document in Circularo from uploaded file
            return createDocument(doctype, docname, file.file_id, file.num_pages, isSign, isAutosign);

        }).then(function (document) {
            progressBar = frappe.show_progress(title, actualStep++, totalSteps, text);
            myDocument = document;
            //Download (signed) file from Circularo
            return downloadFile(myDocument.history_name, 0)

        }).then(function() {
            resolve({ document: myDocument, progressBar });

        }).catch(function (err) {
            reject({ err, progressBar });
        });
    });
}

/**
 * Show message about created documents
 * @param createdDocuments {Array<Object>} Array of created documents
 * @param actionType {number} Action type performed on documents
 */
function showCreatedMessage(createdDocuments, actionType) {
    let title;
    if (actionType === CIRCULARO_ACTIONS.AUTOSIGN) {
        title = (createdDocuments.length === 1)
            ? "Document has been signed"
            : "Documents have been signed";

    } else if (actionType === CIRCULARO_ACTIONS.SIGN) {
        title = (createdDocuments.length === 1)
            ? "Document is ready to be signed"
            : "Documents are ready to be signed";

    } else {
        title = (createdDocuments.length === 1)
            ? "Document has been archived"
            : "Documents have been archived";
    }

    let fullText = "";
    //Go through all created documents
    for (let i = 0; i < createdDocuments.length; i++) {
        if (i !== 0) {
            fullText += "<hr>";
        }
        const myDocument = createdDocuments[i];

        //URL to original Frappe document
        const appLinkText = "<h4 style='display:inline;'>" +
            "<a style='text-decoration:none;' href='" + myDocument.history_url + "' target='_blank'>" + myDocument.docname + "</a>" +
            "</h4>";

        let circularoLinkText;
        if (actionType === CIRCULARO_ACTIONS.SIGN) {
            //Manual sign URL
            circularoLinkText = "<a href='" + myDocument.sign_url + "' target='_blank'>Sign in Circularo</a>";
        } else {
            //View document URL
            circularoLinkText = "<a href='" + myDocument.preview_url + "' target='_blank'>View in Circularo</a>";
        }

        fullText += appLinkText + "&nbsp;&nbsp;&nbsp;-&nbsp;&nbsp;&nbsp;" + circularoLinkText;
    }

    showSuccessMessage(fullText, title, true);
}

/**
 * Check if Circularo buttons are enabled
 * @param doctype {string} Frappe DocType
 * @param view {string} View type
 * @param docname {string | null} Frappe DocName (if not singleton)
 * @returns {Promise<Object>}
 */
function isEnabled(doctype, view, docname = null) {
    return new Promise(function(resolve, reject) {
        frappe.call({
            method: "circularo.circularo.doctype.circularo_integration.circularo_integration.is_enabled",
            args: {
                doctype: doctype,
                view: view,
                docname: docname
            },
            callback: function (value) {
                const args = value.message;
                if (args.status === 0) {
                    resolve(args.message);
                } else {
                    reject(args.message);
                }
            }
        });
    });
}

/**
 * Upload document as PDF to Circularo
 * @param doctype {string} Frappe DocType
 * @param docname {string} Frappe DocName
 * @returns {Promise<Object>} Object with file ID
 */
function uploadFile(doctype, docname) {
    return new Promise(function (resolve, reject) {
        frappe.call({
            method: "circularo.circularo.doctype.circularo_integration.circularo_integration.upload_file",
            args: {
                doctype: doctype,
                docname: docname
            },
            callback: function (value) {
                const args = value.message;
                if (args.status === 0) {
                    resolve(args.message);
                } else {
                    reject(args.message);
                }
            }
        });
    });
}

/**
 * Create document in Circularo
 * @param doctype {string} Frappe DocType
 * @param docname {string} Frappe DocName
 * @param fileHash {string} File ID of Circularo file
 * @param numPages {number} Count of file pages
 * @param isSign {number} 1 if is sign action, 0 otherwise
 * @param isAutosign {number} 1 if is autosign action, 0 otherwise
 * @returns {Promise<Object>} Object with document details
 */
function createDocument(doctype, docname, fileHash, numPages, isSign, isAutosign) {
    return new Promise(function (resolve, reject) {
        frappe.call({
            method: "circularo.circularo.doctype.circularo_integration.circularo_integration.create_document",
            args: {
                doctype: doctype,
                docname: docname,
                file_hash: fileHash,
                sign_page: numPages,
                is_sign: isSign,
                is_autosign: isAutosign
            },
            callback: function (value) {
                const args = value.message;
                if (args.status === 0) {
                    resolve(args.message);
                } else {
                    reject(args.message);
                }
            }
        });
    });
}

/**
 * Download PDF file from Circularo
 * @param historyName {string} History record DocName
 * @param downloadManualSign {number} 1 to try download manually signed PDF, 0 otherwise
 * @returns {Promise<Object>}
 */
function downloadFile(historyName, downloadManualSign) {
    return new Promise(function (resolve, reject) {
        frappe.call({
            method: "circularo.circularo.doctype.circularo_integration.circularo_integration.download_file",
            args: {
                history_name: historyName,
                download_manual_sign: downloadManualSign
            },
            callback: function (value) {
                const args = value.message;
                if (args.status === 0) {
                    resolve(args.message);
                } else {
                    reject(args.message);
                }
            }
        });
    });
}

