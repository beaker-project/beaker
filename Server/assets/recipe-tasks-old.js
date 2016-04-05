
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipeTasksOldView = Backbone.View.extend({
    events: {
        'show .results-tabs a': 'tab_shown',
    },
    initialize: function (options) {
        this.recipe_id = options.recipe_id;
        // lazy load failed tab
        this.$('.failed-tab').one('show', _.bind(this.load_failed, this));

        if (window.location.hash) {
            // anchor might be in our results, need to load them immediately
            this.load_results().then(_.bind(this.activate_tab, this));
        } else {
            // lazy load results tab
            this.$('.results-tab').one('show', _.bind(this.load_results, this));
            this.activate_tab();
        }
    },
    activate_tab: function () {
        // 1. Is window.location.hash pointing at a task in our results?
        // 2. Is there a state saved in localStorage?
        // 3. Hide by default
        var cookie_value = this.get_saved_state();
        if (window.location.hash && this.$('.results-pane ' + window.location.hash).length) {
            this.$('.results-tab').tab('show').addClass('active');
            window.location.hash = window.location.hash;
        } else if (cookie_value) {
            this.$('.results-tabs a')
                .filter(function () { return $(this).data('cookieValue') == cookie_value; })
                .tab('show').addClass('active');
        } else {
            this.$('.hide-results-tab').tab('show').addClass('active');
        }
    },
    load_results: function () {
        var $pane = this.$('.results-pane');
        $pane.html('<i class="fa fa-spinner fa-spin"></i> Loading&hellip;');
        return $.ajax({
            url: '../tasks/do_search?tasks_tgp_order=id&tasks_tgp_limit=0&recipe_id=' + this.recipe_id,
            dataType: 'html',
            success: function (data) { $pane.html(data); },
            error: function (jqxhr, status, error) { $pane.addClass('alert alert-error').text(error); },
        });
    },
    load_failed: function () {
        var $pane = this.$('.failed-pane');
        $pane.html('<i class="fa fa-spinner fa-spin"></i> Loading&hellip;');
        return $.ajax({
            url: '../tasks/do_search?tasks_tgp_order=id&tasks_tgp_limit=0&is_failed=1&recipe_id=' + this.recipe_id,
            dataType: 'html',
            success: function (data) { $pane.html(data); },
            error: function (jqxhr, status, error) { $pane.addClass('alert alert-error').text(error); },
        });
    },
    get_saved_state: function () {
        try {
            return localStorage.getItem('beaker_recipe_' + this.recipe_id);
        } catch (e) {
            return undefined;
        }
    },
    set_saved_state: function (value) {
        try {
            localStorage.setItem('beaker_recipe_' + this.recipe_id, value);
        } catch (e) {
            // ignore
        }
    },
    tab_shown: function (evt) {
        this.set_saved_state($(evt.target).data('cookieValue'));
    },
});

})();
