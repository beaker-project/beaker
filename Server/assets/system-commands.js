
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

var SystemCommandsToolbar = Backbone.View.extend({
    tagName: 'div',
    template: JST['system-commands-toolbar'],
    events: {
        'click button': 'click',
    },
    initialize: function () {
        this.listenTo(this.model,
                'change:can_power change:has_power change:lab_controller_id',
                this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        return this;
    },
    click: function (evt) {
        var $button = $(evt.target);
        var msg = '<p>Are you sure you want to ' + $button.data('confirmationText') + '?</p>';
        if (this.model.get('current_reservation') &&
                this.model.get('current_reservation').get('user').get('user_name')
                != window.beaker_current_user.get('user_name')) {
            msg += ('<p><strong>You are not the current user of the system. '
                   + 'This action may interfere with another user.</strong></p>');
        }
        var command = $button.data('command');
        bootbox.confirm_as_promise(msg).done(_.bind(this.confirmed, this, command));
    },
    confirmed: function (command) {
        this.$('.sync-status').html(
                '<i class="fa fa-spinner fa-spin"></i> Submitting command&hellip;');
        this.model.command(command,
                {success: _.bind(this.enqueued, this),
                 error: _.bind(this.error, this)});
    },
    enqueued: function () {
        this.$('.sync-status').empty();
    },
    error: function (model, xhr) {
        this.$('.sync-status').empty();
        this.$el.append(alert_for_xhr(xhr));
    },
});

var SystemCommandQueueView = BeakerGrid.extend({
    initialize: function (options) {
        options.collection = this.model.command_queue;
        options.columns = [
            {name: 'user', label: 'User', cell: BackgridUserCell, editable: false},
            {name: 'service', label: 'Service', cell: 'string', editable: false},
            // this is queue_time in Python land, but the JSON API has submitted for compatibility reasons:
            {name: 'submitted', label: 'Queued', cell: BackgridDateTimeCell, editable: false},
            {name: 'start_time', label: 'Started', cell: BackgridDateTimeCell, editable: false},
            {name: 'finish_time', label: 'Finished', cell: BackgridDateTimeCell, editable: false},
            {name: 'action', label: 'Action', cell: 'string', editable: false},
            {name: 'status', label: 'Status', cell: 'string', editable: false},
            {name: 'message', label: 'Message', cell: 'string', editable: false},
        ];
        options.name = 'command queue';
        BeakerGrid.prototype.initialize.apply(this, arguments);
    },
});

window.SystemCommandsView = Backbone.View.extend({
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.empty()
            .append(new SystemCommandsToolbar({model: this.model}).el)
            .append('<h3>Command queue</h3>')
            .append(new SystemCommandQueueView({model: this.model}).el);
    },
});

})();
