
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

bootbox.setDefaults({
    animate: false,
});

/*
 * Wrappers which return a Promise using jQuery.Deferred.
 *
 *      bootbox.confirm_as_promise('Sure?')
 *          .done(function () { console.log('confirmed'); })
 *          .fail(function () { console.log('not confirmed'); });
 */
bootbox.alert_as_promise = function (msg) {
    var d = new jQuery.Deferred();
    var cb = function () { d.resolve(); };
    bootbox.alert(msg, cb);
    return d.promise();
};
bootbox.confirm_as_promise = function (msg) {
    var d = new jQuery.Deferred();
    var cb = function (confirmed) { confirmed ? d.resolve() : d.reject(); };
    bootbox.confirm(msg, cb);
    return d.promise();
};

})();
