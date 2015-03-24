// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemCockpitView = Backbone.View.extend({
    events : {
        'click .retry': 'retry',
    },
    initialize: function (options) {
        this.url = 'https://' + this.model.get('fqdn') + ':9090/';
        this.render();
    },
    render: function () {
        this.$el.empty();
        this.ping();
    },
    ping: function() {
        var view = this;
        $.ajax({
            url: this.url + 'ping',
            success: function (data, status, jqxhr) {
                view.embed();
            },
            error: function () {
                view.error();
            },
        });
    },
    retry: function(evt) {
        this.render();
        evt.preventDefault();
    },
    embed: function () {
        $('<iframe width="800px" height="600px" src=' + this.url + '/>')
                    .appendTo(this.$el);
    },
    error: function() {
        $('<div class="alert"/>').text(
            'Cockpit is not installed, or the system is powered off. ' +
            '(Ping request failed.)')
                .appendTo(this.$el);
        $('<div><button type="button" class="retry">Retry</button></div></div>')
            .appendTo(this.$el);
    },
});

})();
