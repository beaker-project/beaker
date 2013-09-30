(function ($) {
    var pad = function (n) { return n < 10 ? '0' + n : n; };
    var offset_hours = function (d) {
        var offset_mins = d.getTimezoneOffset();
        if (offset_mins == 0) return '+00:00';
        return (offset_mins > 0 ? '-' : '+') + pad(Math.abs(offset_mins) / 60)
                + ':' + pad(Math.abs(offset_mins) % 60);
    };
    var iso8601 = function (d) {
        // poor man's version, from
        // https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Date
        return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-'
                + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':'
                + pad(d.getMinutes()) + ':' + pad(d.getSeconds())
                + ' ' + offset_hours(d);
    };
    $.fn.localDatetime = function () {
        this.each(function (i, elem) {
            // Fast path: bail out if we have already seen this element
            // IMPORTANT: this fast path needs to be fast, because we will 
            // be repeating it so many times
            if (elem._localDatetime_done)
                return;
            elem._localDatetime_done = true;
            try {
                var d = new Date(elem.textContent.replace(/-/g, '/') + ' +00:00');
                if (isNaN(d.getTime()))
                    return; // skip it and keep going
                elem.textContent = iso8601(d);
            } catch (e) {
                if (typeof console != 'undefined' && typeof console.log != 'undefined') {
                    console.log(e); // and keep going
                }
            }
        });
    };
    $(document).ready(function () { $('.datetime').localDatetime(); });
    // decorate all jQuery DOM manipulation methods to
    // re-do datetime localisation
    $.each(['append', 'prepend', 'after', 'before', 'wrap', 'attr',
            'removeAttr', 'addClass', 'removeClass', 'toggleClass',
            'empty', 'remove', 'html'],
        function (i, method) {
            var decorated = $.fn[method];
            $.fn[method] = function () {
                var retval = decorated.apply(this, arguments);
                $('.datetime').localDatetime();
                return retval;
            };
        });
})(jQuery);
