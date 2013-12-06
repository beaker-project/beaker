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
    $(document).ready(localise);
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
})(jQuery);
