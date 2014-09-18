
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemAddModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['system-add'],
    events: {
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('input[name="fqdn"]').focus();
    },
    render: function () {
        this.$el.html(this.template({}));
    },
});

})();
