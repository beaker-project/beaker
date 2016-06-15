
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {
    $(document).ready(function() {
        $('html').on('keydown', 'textarea', function(evt) {
            if (evt.ctrlKey && evt.which == 13) {
                var $containing_form = $(evt.currentTarget).closest('form');
                if ($containing_form.find(':input[type=submit]').is(':enabled')) {
                    evt.preventDefault();
                    $containing_form.submit();
                }
            }
        });
    });
})();
