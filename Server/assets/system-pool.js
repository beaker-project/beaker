
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

    window.SystemPoolView = Backbone.View.extend({
        template: JST['system-pool'],
        events: {
            'click .pool-remove': 'remove_pool',
        },

        initialize: function() {
            this.render();
            this.listenTo(this.model, 'change', this.render);
        },
        render: function () {
            this.$el.html(this.template(this.model.attributes));
            if (this.model.get('can_add_to_pool')) {
                this.$('#system-pool-add').append(
                    new SystemAddPoolForm({model: this.model}).el);
            }
        },

        remove_pool: function (evt) {
            $(evt.currentTarget).button('loading');
            this.model.remove_from_pool($(evt.currentTarget).data('pool-remove'),
                                        {success: _.bind(this.render, this),
                                         error: _.bind(this.remove_pool_error, this)});
            evt.preventDefault();
        },
        remove_pool_error: function (model, xhr) {
            this.$('button').button('reset');
            this.$el.append(
                $('<div class="alert alert-error"/>')
                    .text(xhr.statusText + ': ' + xhr.responseText));
        },

    });

    var SystemAddPoolForm = Backbone.View.extend({
        template: JST['system-add-pool'],
        events: {
            'change input[name=pool]': 'update_button_state',
            'input input[name=pool]': 'update_button_state',
            'keyup input[name=pool]': 'update_button_state',
            'submit form': 'submit',
        },
        initialize: function () {
            this.render();
        },
        render: function () {
            this.$el.html(this.template(this.model.attributes));
            this.$('input[name="pool"]').beaker_typeahead('pool-name');
            this.$('button[type=submit]').prop('disabled', true);
        },
        update_button_state: function () {
            this.$('.alert').remove();
            var $input = this.$('input[name=pool]');
            var allow_submission = ($input.val() && $input.get(0).checkValidity());
            this.$('button[type=submit]').prop('disabled', this.saving || !allow_submission);
        },

        submit: function (evt) {
            if (evt.currentTarget.checkValidity()) {
                var new_pool = this.$('input[name=pool]').val();
                if (_.contains(this.model.get('pools'), new_pool)) {
                    // nothing to do
                    this.$('input[name=pool]').typeahead('setQuery', '');
                    return false;
                } else {
                    // If the pool does not exist, create it after confirming
                    if (!(_.contains(this.model.get('all_pools'), new_pool))) {
                        bootbox.confirm_as_promise('Pool does not exist. Create it?').done(_.bind(this.add_to_pool, this, new_pool));
                    } else {
                        this.add_to_pool(new_pool);
                    }
                }
            }
            evt.preventDefault();
        },

        add_to_pool: function(new_pool) {
            this.saving = true;
            this.$('btn').button('loading');
            this.model.add_to_pool(new_pool,
                                   {success: _.bind(this.render, this),
                                    error: _.bind(this.error, this)});
        },

        error: function (model, xhr) {
            this.$('btn').button('reset');
            this.$el.append(
                $('<div class="alert alert-error"/>')
                    .text(xhr.statusText + ': ' + xhr.responseText));
        },
    });

})();
