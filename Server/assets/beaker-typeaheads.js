;(function ($) {

// Top-level JSON arrays are a security risk and Flask does not allow us to 
// return them:
// http://flask.pocoo.org/docs/security/#json-security
// so we need to give typeahead a filter function to extract the array.
var results_filter = function (response) {
    return response.data;
};

// window.beaker_url_prefix is set by master.kid
$.fn.beaker_typeahead = function (type) {
    var options = ({
        'group-name': {
            name: 'beaker-group-name',
            prefetch: {
                url: beaker_url_prefix + 'groups/+typeahead',
                filter: results_filter,
            },
            valueKey: 'group_name',
            limit: 8,
            template: JST['beaker-typeaheads/group-name'],
        },
        'user-name': {
            name: 'beaker-user-name',
            prefetch: {
                url: beaker_url_prefix + 'users/+typeahead',
                filter: results_filter,
            },
            remote: {
                url: beaker_url_prefix + 'users/+typeahead?q=%QUERY',
                filter: results_filter,
            },
            valueKey: 'user_name',
            limit: 10,
            template: JST['beaker-typeaheads/user-name'],
        },
    })[type];
    this.typeahead(options);

    // Store a data attribute indicating whether the current value of the input 
    // is from the typeahead suggestions or not. Specifically, we store true if:
    //   - the user selected a suggestion, using the mouse or the arrow keys and enter;
    //   - the user autocompleted a suggestion by hitting tab; or
    //   - the user typed out a suggestion explicitly.
    // Widgets can use this to decide how to treat the input's value (as a kind 
    // of validation).
    // Inspired by https://github.com/twitter/typeahead.js/issues/267#issuecomment-20792039
    this.data('typeahead_match', false);
    this.on('typeahead:selected typeahead:autocompleted', function () {
        $(this).data('typeahead_match', true);
    });
    this.on('change', function (evt) {
        var $input = $(this);
        // does what they typed match a suggestion?
        var available = $input.data('ttView').datasets[0].itemHash;
        var matching = _.findWhere(available, {value: $input.val()});
        $input.data('typeahead_match', !!matching);
    });

    return this;
};

})(jQuery);
