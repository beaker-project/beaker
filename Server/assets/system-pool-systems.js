
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemPoolSystemsView = Backbone.View.extend({
    template: JST['system-pool-systems'],
    events: {
        'click .system-remove': 'remove_system',
    },
    initialize: function() {
        this.render();
        this.listenTo(this.model, 'change', this.render);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        if (this.model.get('can_edit')) {
            this.$('.pool-systems-list').after(
                new SystemPoolAddSystemForm({model: this.model}).el);
        }
    },
    remove_system: function (evt) {
        $(evt.currentTarget).button('loading');
        this.model.remove_system($(evt.currentTarget).data('system-remove'),
                                    {success: _.bind(this.render, this),
                                     error: _.bind(this.remove_system_error, this)});
        evt.preventDefault();
    },
    remove_system_error: function (model, xhr) {
        this.$('button').button('reset');
        this.$el.append(alert_for_xhr(xhr));
    },
});

var SystemPoolAddSystemForm = Backbone.View.extend({
    template: JST['system-pool-add-system'],
    events: {
        'submit form': 'submit',
    },
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('input[name="system"]').beaker_typeahead('system-fqdn');
    },
    submit: function (evt) {
        if (evt.currentTarget.checkValidity()) {
            this.$('.alert').remove();
            var new_system = this.$('input[name=system]').val();
            if (_.contains(this.model.get('systems'), new_system)) {
                // nothing to do
                this.$('input[name=system]').typeahead('setQuery', '');
                return false;
            }
            this.$('button').button('loading');
            var model = this.model;
            this.model.add_system(new_system, {success: _.bind(this.success, this),
                                               error: _.bind(this.error, this)});
        }
        evt.preventDefault();
    },
    success: function () {
        this.$('button').button('reset');
        // calling .focus directy is not working, seems a known issue
        // http://stackoverflow.com/questions/7046798/jquery-focus-fails-on-firefox
        setTimeout(function(){
            this.$('input[name=system]').focus();
        }, 0);
    },
    error: function (model, xhr) {
        this.$('button').button('reset');
        this.$el.append(alert_for_xhr(xhr));
    },
});

})();
