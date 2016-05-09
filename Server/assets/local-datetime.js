
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

/**
 * Decorates all jQuery DOM manipulation methods in order to convert timestamps 
 * from UTC to local time.
 *
 * Because this is so expensive and hacky, this is not used on any new pages. 
 * Templates rendered client-side should ensure that they format timestamps in 
 * the user's local time explicitly. This script remains enabled on older 
 * TurboGears pages where the template is rendered server side and there is no 
 * straightforward way to localize timestamps.
 */

(function ($) {
    $.fn.localDatetime = function () {
        this.each(function (i, elem) {
            // Fast path: bail out if we have already seen this element
            // IMPORTANT: this fast path needs to be fast, because we will 
            // be repeating it so many times
            if (elem._localDatetime_done)
                return;
            elem._localDatetime_done = true;
            try {
                // datetime in text content
                var m = moment.utc(elem.textContent);
                if (m.isValid()) {
                    elem.textContent = m.local().format('YYYY-MM-DD HH:mm:ss Z');
                }
                // datetime in title attr
                if (elem.hasAttribute('title')) {
                    m = moment.utc(elem.getAttribute('title'));
                    if (m.isValid()) {
                        elem.setAttribute('title', m.local().format('YYYY-MM-DD HH:mm:ss Z'));
                    }
                }
            } catch (e) {
                if (typeof console != 'undefined' && typeof console.log != 'undefined') {
                    console.log(e); // and keep going
                }
            }
        });
    };
    var localise = function () {
        $('.datetime').localDatetime();
        $('time').localDatetime();
    };
    $(document).ready(function () {
        if ($(document.body).is('.with-localised-datetimes')) {
            localise();
            // decorate all jQuery DOM manipulation methods to
            // re-do datetime localisation
            $.each(['append', 'prepend', 'after', 'before', 'wrap', 'attr',
                    'removeAttr', 'addClass', 'removeClass', 'toggleClass',
                    'empty', 'remove', 'html'],
                function (i, method) {
                    var decorated = $.fn[method];
                    $.fn[method] = function () {
                        var retval = decorated.apply(this, arguments);
                        localise();
                        return retval;
                    };
                });
        }
    });
})(jQuery);
