
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.GroupRootPasswordView = Backbone.View.extend({
    template: JST['group-rootpassword'],
    events: {
        'submit form': 'save',
    },
    initialize: function (options) {
        this.listenTo(this.model, 'change:root_password change:can_view_rootpassword change:can_edit',
                this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    save: function (evt) {
        evt.preventDefault();
        var $form = this.$('form');
        $form.find('button').button('loading');
        $form.find('.alert-error').remove();
        var new_root_password = $form.find('[name=root_password]').val();
        this.model.save({root_password: new_root_password}, {patch: true, wait: true})
            .always(function () { $form.find('button').button('reset'); })
            .fail(function (xhr) {
                $form.append(alert_for_xhr(xhr));
            });
    },
});

})();
