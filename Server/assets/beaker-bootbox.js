;(function () {

bootbox.animate(false);

/*
 * Wrappers which return a Promise using jQuery.Deferred.
 *
 *      bootbox.confirm_as_promise('Sure?')
 *          .done(function () { console.log('confirmed'); })
 *          .fail(function () { console.log('not confirmed'); });
 */
bootbox.alert_as_promise = function (msg, button_text) {
    var d = new jQuery.Deferred();
    var cb = function () { d.resolve(); };
    bootbox.alert.apply(null, _.toArray(arguments).concat([cb]));
    return d.promise();
};
bootbox.confirm_as_promise = function (msg, cancel_text, confirm_text) {
    var d = new jQuery.Deferred();
    var cb = function (confirmed) { confirmed ? d.resolve() : d.reject(); };
    bootbox.confirm.apply(null, _.toArray(arguments).concat([cb]));
    return d.promise();
};

})();
