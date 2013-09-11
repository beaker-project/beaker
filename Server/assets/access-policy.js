;(function () {

var AccessPolicyRule = Backbone.Model.extend({
    // ensure the 'everybody' attribute is filled in
    initialize: function (attributes, options) {
        if (!_.has(attributes, 'everybody')) {
            this.set('everybody', (attributes['user'] == null && 
                    attributes['group'] == null));
        }
    },
});

window.AccessPolicy = Backbone.Model.extend({
    initialize: function () {
        this.rules = new Backbone.Collection([], {model: AccessPolicyRule});
    },
    parse: function (response) {
        // response will be undefined if the server gives back 204 for a save
        if (_.isUndefined(response)) return;
        this.rules.reset(response.rules);
        return {id: response.id,
                possible_permissions: response.possible_permissions};
    },
    toJSON: function () {
        return {rules: this.rules.toJSON()};
    },
});

var blur_on_enter = function (evt) {
    if (evt.which == 13) {
        $(evt.target).trigger('blur');
        return false;
    }
};

window.AccessPolicyView = Backbone.View.extend({
    template: JST['access-policy'],
    events: {
        'change   input[type=checkbox]': 'changed_checkbox',
        'blur     .group-rows input[type=text]': 'typed_group',
        'keypress .group-rows input[type=text]': blur_on_enter,
        'blur     .user-rows input[type=text]': 'typed_user',
        'keypress .user-rows input[type=text]': blur_on_enter,
        'submit   form': 'submit',
        'reset    form': 'reset',
    },
    initialize: function () {
        this.dirty = false;
        this.request_in_progress = false;
        this.listenTo(this.model, 'request', this.sync_started);
        this.listenTo(this.model, 'sync', this.sync_complete);
        this.listenTo(this.model, 'error', this.sync_error);
        this.listenTo(this.model, 'change:possible_permissions', this.render);
        this.listenTo(this.model.rules, 'reset', this.render);
        this.listenTo(this.model.rules, 'add', function (rule) {
            this.find_checkbox_for_rule(rule).checked = true;
        });
        this.listenTo(this.model.rules, 'remove', function (rule) {
            this.find_checkbox_for_rule(rule).checked = false;
        });
        this.render();
    },
    render: function () {
        this.$el.html(this.template(
                _.extend({readonly: this.options.readonly}, this.model.attributes)));
        // add initial rows
        _.chain(this.model.rules.pluck('group')).compact().uniq()
            .each(this.add_group_row, this);
        _.chain(this.model.rules.pluck('user')).compact().uniq()
            .each(this.add_user_row, this);
        this.add_everybody_row();
        this.model.rules.each(function (rule) {
            this.find_checkbox_for_rule(rule).checked = true;
        }, this);
        if (this.options.readonly) {
            this.$('input[type=checkbox]').prop('disabled', true);
        }
    },
    update_button_state: function () {
        this.$('button').prop('disabled',
                (!this.dirty || this.request_in_progress));
    },
    sync_started: function () {
        this.request_in_progress = true;
        this.update_button_state();
    },
    sync_complete: function () {
        this.dirty = false;
        this.request_in_progress = false;
        this.update_button_state();
        this.$('.dirty').removeClass('dirty');
        this.$('.sync-status').empty();
    },
    sync_error: function (model, xhr) {
        this.request_in_progress = false;
        this.update_button_state();
        this.$('.sync-status').empty().append(
            $('<span class="alert alert-error"/>')
            .text('Server request failed: ' + xhr.statusText));
    },
    submit: function () {
        if (this.request_in_progress) return false;
        this.$('.sync-status').html('<i class="icon-spinner icon-spin"></i> Saving&hellip;');
        this.model.save();
        return false;
    },
    reset: function () {
        if (this.request_in_progress) return false;
        this.$('.sync-status').html('<i class="icon-spinner icon-spin"></i> Loading&hellip;');
        this.model.fetch();
        return false;
    },
    typed_group: function () {
        var $input = this.$('.group-rows input[type=text]');
        var val = $input.val();
        if (!val) return;
        var $row = this.find_group_row(val);
        if (!$row.length) {
            var $row = this.add_group_row(val);
        }
        $row.find('input[type=checkbox]').first().focus();
        $input.val('');
    },
    typed_user: function () {
        var $input = this.$('.user-rows input[type=text]');
        var val = $input.val();
        if (!val) return;
        var $row = this.find_user_row(val);
        if (!$row.length) {
            var $row = this.add_user_row(val);
        }
        $row.find('input[type=checkbox]').first().focus();
        $input.val('');
    },
    find_group_row: function (group) {
        return $('.group-rows tr').filter(
                function () { return $.data(this, 'group') == group; });
    },
    add_group_row: function (group) {
        var row = $('<tr/>');
        row.data('group', group);
        $('<td/>').text(group).appendTo(row);
        _.each(this.model.get('possible_permissions'),
            function (permission) {
                var checkbox = $('<input type="checkbox"/>')
                    .data('user', null)
                    .data('group', group)
                    .data('permission', permission.value);
                $('<td/>').append(checkbox).appendTo(row);
            }, this);
        if (this.options.readonly)
            this.$('.group-rows').append(row);
        else
            this.$('.group-rows tr:last').before(row);
        return row;
    },
    find_user_row: function (user) {
        return $('.user-rows tr').filter(
                function () { return $.data(this, 'user') == user; });
    },
    add_user_row: function (user) {
        var row = $('<tr/>');
        row.data('user', user);
        $('<td/>').text(user).appendTo(row);
        _.each(this.model.get('possible_permissions'),
            function (permission) {
                var checkbox = $('<input type="checkbox"/>')
                    .data('user', user)
                    .data('group', null)
                    .data('permission', permission.value);
                $('<td/>').append(checkbox).appendTo(row);
            }, this);
        if (this.options.readonly)
            this.$('.user-rows').append(row);
        else
            this.$('.user-rows tr:last').before(row);
        return row;
    },
    add_everybody_row: function () {
        var row = $('<tr/>');
        $('<th/>').text('Everybody').appendTo(row);
        _.each(this.model.get('possible_permissions'),
            function (permission) {
                var checkbox = $('<input type="checkbox"/>')
                    .data('user', null)
                    .data('group', null)
                    .data('permission', permission.value);
                $('<td/>').append(checkbox).appendTo(row);
            }, this);
        this.$('.everybody-row').append(row);
        return row;
    },
    find_checkbox_for_rule: function (rule) {
        return this.$('input[type=checkbox]').filter(function () {
            return $.data(this, 'permission') == rule.get('permission') &&
                    $.data(this, 'group') == rule.get('group') &&
                    $.data(this, 'user') == rule.get('user');
        }).get(0);
    },
    changed_checkbox: function (evt) {
        var $elem = $(evt.target);
        var user = $elem.data('user');
        var group = $elem.data('group');
        // add or remove the matching rule
        var rule_attrs = {permission: $elem.data('permission'),
                group: group, user: user};
        if (evt.target.checked) {
            this.model.rules.add(rule_attrs);
        } else {
            var rule = this.model.rules.findWhere(rule_attrs);
            this.model.rules.remove(rule);
        }
        // show a dirtiness indicator in the row
        if (user) {
            this.find_user_row(user).addClass('dirty');
        } else if (group) {
            this.find_group_row(group).addClass('dirty');
        } else {
            this.$('.everybody-row tr').addClass('dirty');
        }
        this.dirty = true;
        this.update_button_state();
    },
})

})();
