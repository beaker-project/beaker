// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

/**
 * Global access policy view that can be extented
**/

;(function () {

window.AccessPolicyView = Backbone.View.extend({
    template: JST['access-policy'],
    events: {
        'change   input[type=checkbox]': 'changed_checkbox',
        'click    .group-rows button.add': 'add_group',
        'keypress .group-rows input[type=text]': 'add_group_on_enter',
        'click    .user-rows button.add': 'add_user',
        'keypress .user-rows input[type=text]': 'add_user_on_enter',
    },
    initialize: function (options) {
        this.readonly = options.readonly;
        this.render();
    },
    render: function () {
        var readonly = this.readonly;
        var rules = this.model.get('rules');
        this.$el.html(this.template({
            readonly: readonly,
            rules: rules,
            possible_permissions: this.model.get('possible_permissions'),
        }));
        // add initial rows
        _.chain(rules.pluck('group')).compact().uniq()
            .each(this.add_group_row, this);
        _.chain(rules.pluck('user')).compact().uniq()
            .each(this.add_user_row, this);
        this.add_everybody_row();
        rules.each(function (rule) {
            this.find_checkbox_for_rule(rule).checked = true;
        }, this);
        if (readonly) {
            this.$('input[type=checkbox]').prop('disabled', true);
        }
        // set up typeaheads
        this.$('.group-rows input[type=text]').beaker_typeahead('group-name');
        this.$('.user-rows input[type=text]').beaker_typeahead('user-name');
    },
    add_group: function () {
        var $input = this.$('#access-policy-group-input');
        var val = $input.val();
        if (val) {
            var $row = this.find_group_row(val);
            if (!$row.length) {
                var $row = this.add_group_row(val);
            }
            $row.find('input[type=checkbox]').first().focus();
            $input.typeahead('setQuery', '');
        }
    },
    add_group_on_enter: function (evt) {
        if (evt.which == 13) {
            evt.preventDefault();
            this.add_group();
        }
    },
    add_user: function () {
        var $input = this.$('#access-policy-user-input');
        var val = $input.val();
        if (val) {
            var $row = this.find_user_row(val);
            if (!$row.length) {
                var $row = this.add_user_row(val);
            }
            $row.find('input[type=checkbox]').first().focus();
            $input.typeahead('setQuery', '');
        }
    },
    add_user_on_enter: function (evt) {
        if (evt.which == 13) {
            evt.preventDefault();
            this.add_user();
        }
    },
    find_group_row: function (group) {
        return $('.group-rows tr').filter(
                function () { return $.data(this, 'group') == group; });
    },
    add_group_row: function (group) {
        var row = $('<tr/>');
        row.data('group', group);
        var td = $('<td/>');
        td.appendTo(row);
        $('<a>',{
            text: group,
            href: beaker_url_prefix + 'groups/edit?group_name=' + encodeURIComponent(group)
        }).appendTo(td);
        _.each(this.model.get('possible_permissions'),
            function (permission) {
                var checkbox = $('<input type="checkbox"/>')
                    .data('user', null)
                    .data('group', group)
                    .data('permission', permission.value);
                $('<td/>').append(checkbox).appendTo(row);
            }, this);
        if (this.readonly)
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
        if (this.readonly)
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
        var rules = this.model.get('rules');
        if (evt.target.checked) {
            rules.add(rule_attrs);
        } else {
            var rule = rules.findWhere(rule_attrs);
            rules.remove(rule);
        }
        // show a dirtiness indicator in the row
        if (user) {
            this.find_user_row(user).addClass('dirty');
        } else if (group) {
            this.find_group_row(group).addClass('dirty');
        } else {
            this.$('.everybody-row tr').addClass('dirty');
        }
        this.trigger('changed_access_policy_rules');
    },
})

})();
