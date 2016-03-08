
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
            this.$el.append(alert_for_xhr(xhr));
        },

    });

    var SystemAddPoolForm = Backbone.View.extend({
        template: JST['system-add-pool'],
        events: {
            'submit form': 'submit',
        },
        initialize: function () {
            this.render();
        },
        render: function () {
            this.$el.html(this.template(this.model.attributes));
            this.$('input[name="pool"]').beaker_typeahead('pool-name');
        },
        submit: function (evt) {
            if (evt.currentTarget.checkValidity()) {
                this.$('.alert').remove();
                var new_pool = this.$('input[name=pool]').val();
                if (_.contains(this.model.get('pools'), new_pool)) {
                    // nothing to do
                    this.$('input[name=pool]').typeahead('setQuery', '');
                    return false;
                }
                this.$('button').button('loading');
                var model = this.model;
                model.add_to_pool(new_pool)
                    // if it fails with a 404, offer to create the pool
                    .then(function () { }, function (xhr, status, error) {
                        if (xhr.status == 404) {
                            return bootbox.confirm_as_promise('<p>Pool does not exist. Create it?</p>')
                                .then(null, function () { return xhr; })
                                // confirmation received, create it
                                .then(function () {
                                    return $.ajax({
                                        url: beaker_url_prefix + 'pools/',
                                        type: 'POST',
                                        contentType: 'application/json',
                                        data: JSON.stringify({'name': new_pool}),
                                        dataType: 'text',
                                    });
                                })
                                // creation succeeded, add it again
                                .then(function () { return model.add_to_pool(new_pool); });
                        } else {
                            return xhr;
                        }
                    })
                    // on success, re-render
                    .done(_.bind(this.render, this))
                    // any other failure, we display
                    .fail(_.bind(this.error, this))
            }
            evt.preventDefault();
        },
        error: function (xhr) {
            this.$('button').button('reset');
            this.$el.append(alert_for_xhr(xhr));
        },
    });

})();
