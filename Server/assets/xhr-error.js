
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

/** Functions for displaying errors for failed XmlHttpRequests. */

;(function () {

var error_message = function (xhr) {
    if (xhr.status <= 0)
        return 'HTTP request aborted';
    var content_type = xhr.getResponseHeader('Content-Type');
    // In Firefox various network failures and security problems like invalid 
    // certs will result in status 404 with the unhelpful statusText 'error' 
    // and no response. So let's translate that to something a bit nicer.
    if (!content_type && xhr.statusText == 'error')
        return 'Unknown HTTP request failure';
    // Beaker will serve up text/plain error messages for API requests, but we 
    // might be seeing an Apache HTML error page instead. We only show the 
    // response to the user if it's plain text.
    if (content_type && content_type.substr(0, 'text/plain'.length) == 'text/plain')
        return xhr.statusText + ': ' + xhr.responseText;
    // This won't look great but it's the best we can do...
    return xhr.status + ' ' + xhr.statusText;
}

/** Returns a jQuery wrapped <div/> showing an error message based on the 
 * given failed XmlHttpRequest. Optionally prefix the message with an 
 * explanatory prefix. */
window.alert_for_xhr = function (xhr, prefix) {
    var msg = error_message(xhr);
    if (prefix)
        msg = prefix + ': ' + msg;
    return $('<div class="alert alert-error" />').text(msg);
};

/** Triggers a bootstrap-growl notification showing an error message based on 
 * the given failed XmlHttpRequest. */
window.growl_for_xhr = function (xhr, heading) {
    $.bootstrapGrowl('<h4>' + heading + '</h4>' + error_message(xhr), {type: 'error'});
};

})();
