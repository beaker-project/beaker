
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipePageLayout = Backbone.View.extend({
    template: JST['recipe-page'],
    initialize: function (options) {
        this.cookie_name = 'beaker_recipe_' + this.model.get('id') + '_viewstate';

        // If the page is loaded with no anchor in the URL, but we remember 
        // a previous anchor from localStorage, put that in.
        if (!location.hash && localStorage.getItem(this.cookie_name)) {
            window.history.replaceState(undefined, undefined, localStorage.getItem(this.cookie_name));
        }
        // If we still have no anchor, just pick something sensible to show.
        if (!location.hash) {
            window.history.replaceState(undefined, undefined, this.initial_hash());
        }

        this.header_view = new RecipePageHeaderView({model: this.model});
        this.quick_info_view = new RecipeQuickInfoView({model: this.model});
        this.installation_view = new RecipeInstallationView({model: this.model, id: 'installation'});
        this.tasks_view = new RecipeTasksView({model: this.model, id: 'tasks'});
        this.reservation_view = new RecipeReservationView({model: this.model, id: 'reservation'});
        this.render();

        // Register event handlers for all the different view changes which we 
        // want to reflect in the anchor.
        var layout = this;
        $(window).on('hashchange', function (evt) {
            evt.preventDefault();
            layout.update_viewstate_from_hash();
        });
        this.$('.recipe-nav').on('shown', 'a', _.bind(this.update_hash_from_viewstate, this));
        this.listenTo(this.tasks_view, 'expand:task', this.update_hash_from_viewstate);
    },
    render: function () {
        this.$el.html(this.template());
        this.header_view.setElement(this.$('.recipe-page-header')).render();
        this.quick_info_view.setElement(this.$('.recipe-quick-info')).render();
        this.installation_view.$el.appendTo(this.$('.tab-content'));
        this.tasks_view.$el.appendTo(this.$('.tab-content'));
        this.reservation_view.$el.appendTo(this.$('.tab-content'));
        return this;
    },
    initial_hash: function () {
        // Pick something sensible to show the user initially.
        if (this.model.get('status') == 'Reserved') {
            return '#reservation';
        } else if (this.model.get('status') == 'Running' || this.model.get('is_finished')) {
            var running_task = _.find(this.model.get('tasks'),
                    function (task) { return task.get('status') == 'Running'; });
            if (running_task) {
                return '#task' + running_task.get('id');
            }
            var first_failed_task = _.find(this.model.get('tasks'),
                    function (task) { return task.get('result') != 'New' && task.get('result') != 'Pass'; });
            if (first_failed_task) {
                return '#task' + first_failed_task.get('id');
            }
            return '#tasks';
        } else {
            return '#installation';
        }
    },
    update_viewstate_from_hash: function () {
        var hash = location.hash;
        if (hash == '#installation') {
            this.activate_tab('installation');
        } else if (hash == '#reservation') {
            this.activate_tab('reservation');
        } else if (hash.startsWith('#task')) {
            this.activate_tab('tasks');
            // You might think this would be easier using a regexp, but you 
            // would be wrong :-) mainly because JS RegExp lacks lookbehind 
            // assertions.
            var task_ids = _.compact(_.map(hash.substr(1).split(','), function (item) {
                var match = item.match(/task(\d+)/);
                if (match) return match[1];
            }));
            this.tasks_view.expand_task_ids(task_ids);
        } else {
            // The user has somehow ended up at anchor that we don't recognise, 
            // maybe because they produced the URL themselves. We need to show 
            // *something* so just pick the default.
            window.history.replaceState(undefined, undefined, this.initial_hash());
            this.update_viewstate_from_hash();
        }
    },
    activate_tab: function (name) {
        // This is for displaying a tab programmatically, not something that is 
        // triggered by a user action. We set the classes directly, instead of 
        // calling .tab('show'), in order to avoid triggering events.
        this.$('.recipe-nav > li.active').removeClass('active');
        this.$('.recipe-nav > li').has('> a[href="#' + name + '"]').addClass('active');
        this.$('.tab-pane.active').removeClass('active');
        this.$('#' + name).addClass('active');
    },
    update_hash_from_viewstate: function () {
        var hash;
        if (this.$('#installation').is('.active')) {
            hash = '#installation';
        } else if (this.$('#reservation').is('.active')) {
            hash = '#reservation';
        } else if (this.$('#tasks').is('.active')) {
            var task_ids = this.tasks_view.expanded_task_ids();
            if (!_.isEmpty(task_ids)) {
                hash = '#' + _.map(task_ids, function (task_id) { return 'task' + task_id; }).join(',');
            } else {
                hash = '#tasks';
            }
        }
        window.history.replaceState(undefined, undefined, hash);
        // Also save to localStorage for the next time this page is loaded.
        localStorage.setItem(this.cookie_name, hash);
    },
});

})();
