// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemPoolAccessPolicyView = Backbone.View.extend({
    initialize: function (options) {
        this.render();
        this.listenTo(this.model, 'change:can_edit_policy', this.render);
    },
    render: function () {
        this.$el.empty();
        var readonly = this.model.get('can_edit_policy') ? false : true;
        new AccessPolicyView({model: this.model.get('access_policy'), readonly: readonly})
                           .$el
                           .appendTo(this.$el);
    },
});

})();
