
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipeInstallationView = Backbone.View.extend({
    className: 'tab-pane recipe-installation',
    template: JST['recipe-installation'],
    initialize: function() {
        this.listenTo(this.model, 'change:status', this.render);
        this.listenTo(this.model, 'change:installation', function () {
            this.render();
            this.listenTo(this.model.get('installation'), 'change', this.render);
        });
        if (!_.isEmpty(this.model.get('installation'))) {
            this.listenTo(this.model.get('installation'), 'change', this.render);
        }
        this.render();
    },
    render: function () {
        this.$el.html(this.template( this.model.attributes));
        new LogsLink({model: this.model}).$el.appendTo(this.$('div.recipe-installation-logs'));
        var recipe_installation_details = new RecipeInstallationDetails({model: this.model});
        this.$('.recipe-installation-details').append(recipe_installation_details.el);
    },
});

var RecipeInstallationDetails = Backbone.View.extend({
    tagName: 'div',
    template: JST['recipe-installation-details'],
    events: {
        'click .toggle-progress-settings button': 'toggle_progress_settings',
    },
    toggle_progress_settings: function (evt) {
        var selected_side;
        if (!_.isEmpty(evt)) {
            evt.preventDefault();
            selected_side = $(evt.currentTarget).text() ;
        } else {
            selected_side = 'Progress';
        }
        switch (selected_side) {
            case 'Progress':
                this.$('.recipe-installation-progress').show();
                this.$('.recipe-installation-settings').hide();
                break;
            case 'Settings':
                this.$('.recipe-installation-progress').hide();
                this.$('.recipe-installation-settings').show();
                break;
        }
    },
    initialize: function (options) {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        var progress = new RecipeInstallationProgress({model: this.model}).el;
        var settings = new RecipeInstallationSettings({model: this.model}).el;
        this.$('.recipe-installation-progress-settings').empty().append(progress).append(settings);
        this.toggle_progress_settings();
        return this;
    },
});
/**
 * Gets the difference in milliseconds between two dates.
 */
window.get_time_difference = function(date_one, date_two) {
    var diff, date_format='hh:mm:ss';
    if (!date_one)
        return '';
    diff = date_one.diff(date_two || moment());
    if (diff >= 0) {
        date_format = '+' + date_format;
        return moment.duration(diff).format("+hh:mm:ss", { trim: false });
    }
    return moment.duration(diff).format(date_format, { trim: false });
};

var RecipeInstallationProgress = Backbone.View.extend({
    className: 'recipe-installation-progress',
    template: JST['recipe-installation-progress'],
    initialize: function (options) {
        this.render();
    },
    render: function () {
        var netboot_configured = null;
        var openstack_instance_created = null;
        var rebooted = null;
        var install_started = null;
        var install_finished = null;
        var postinstall_finished = null;
        // If the recipe is still queued there will be no associated 
        // installation, so we have to handle the possibility that it's null 
        // here.
        var installation = this.model.get('installation');
        if (!_.isEmpty(installation)) {
            var configure_netboot_cmd = _.find(installation.get('commands'),
                    function (command) { return command.get('action') == 'configure_netboot'; });
            if (!_.isEmpty(configure_netboot_cmd) &&
                    configure_netboot_cmd.get('status') == 'Completed') {
                netboot_configured = configure_netboot_cmd.get('finish_time');
            }
            var resource = this.model.get('resource');
            if(resource && !_.isEmpty(resource.get('instance_id'))) {
                openstack_instance_created = resource.get('instance_created');
            }
            rebooted = installation.get('rebooted');
            install_started = installation.get('install_started');
            install_finished = installation.get('install_finished');
            postinstall_finished = installation.get('postinstall_finished');
        }
        if (!_.any([netboot_configured, openstack_instance_created, rebooted, install_started,
                    install_finished, postinstall_finished])) {
            this.$el.text('No installation progress reported.');
        } else {
            this.$el.html(this.template({
                netboot_configured: netboot_configured,
                openstack_instance_created: openstack_instance_created,
                rebooted: rebooted,
                install_started: install_started,
                install_finished: install_finished,
                postinstall_finished: postinstall_finished,
                start_time: this.model.get('start_time'),
                get_time_difference: get_time_difference,
                kernel_options: installation.get('kernel_options'),
            }));
            this.linkify_ks();
        }
        return this;
    },
    linkify_ks: function () {
        var $kopts = this.$('.recipe-installation-kernel-options code');
        var kopts = $kopts.text();
        kopts = kopts.replace(/ks=([^ ]+)/, function (match, url) {
                return 'ks=<a href="' + _.escape(url) + '">' + _.escape(url) + '</a>'; });
        $kopts.html(kopts);
    },
});

var RecipeInstallationSettings = Backbone.View.extend({
    className: 'recipe-installation-settings',
    template: JST['recipe-installation-settings'],
    initialize: function (options) {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        return this;
    },
});

})();
