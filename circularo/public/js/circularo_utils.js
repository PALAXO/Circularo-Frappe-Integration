// Copyright (c) 2021, Circularo and contributors
// For license information, please see license.txt

/**
 * Shows success message window
 * @param message {string} Window text
 * @param title {string} Window title
 * @param wide {boolean} Use wide window
 */
function showSuccessMessage(message, title = "Success", wide = false) {
    frappe.msgprint({
        title: title,
        indicator: "green",
        message: message,
        wide: wide
    });
}

/**
 * Shows error message
 * @param message {string} Window text
 * @param title {string} Window title
 */
function showErrorMessage(message, title = "Error") {
    frappe.msgprint({
        title: title,
        indicator: "red",
        message: message
    });
}

/**
 * Opens new tab with given URL
 * @param url {string} URL to be opened
 */
function openNewTab(url) {
    Object.assign(document.createElement('a'), {
        target: '_blank',
        href: url,
    }).click();
}