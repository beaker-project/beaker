// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.ReservationDurationSelection = Backbone.View.extend({
    tagName: 'div',
    className: 'control-group reservation-duration-widget',
    template: JST['reservation-duration-selection'],
    events: {
        'click button': 'update_maximum_field',
    },
    initialize: function(options) {
        this.reserve_duration = options.reserve_duration || 1;
        this.maximum = moment.duration(99 * 60 * 60, 'seconds');
    },
    render: function () {
        this.$el.html(this.template(this));
    },
    update_maximum_field: function (evt) {
        var elm = evt.currentTarget;
        var unit = $(elm).attr('data-duration-unit');
        this.$('#reserve_duration').attr('max', this.maximum.as(unit));
    },
    get_reservation_duration: function () {
        var unit = this.$('.duration-unit button.active').attr('data-duration-unit');
        var value = parseInt(this.$('[name=reserve_duration]').val());
        if (isNaN(value)) {
            // Should never happen, since the browser validation should have
            // caught invalid values.
            throw new Error('Parsing given reservation duration to int returned NaN.');
        }
        var duration = moment.duration(value, unit);
        return duration;
    },
});

})();
