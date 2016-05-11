
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function ($) {

// An extension of the Bootstrap Popover plugin which uses Backbone views for 
// its content, and which behaves more reasonably based on how we use it on the 
// page.

// Bootstrap Popover is designed around having a button as a kind of toggle, to 
// show and hide the popover, but in Beaker we instead use a small icon link to 
// trigger the popover. Because the link can't have activated/deactived states 
// like a button, it doesn't make sense to use the link as a toggle. Instead, 
// the link shows the popover and then clicking anywhere outside the popover 
// hides it. In order to manage this, and to fit better with Beaker's existing 
// conventions around Backbone, the popover content is a Backbone.View newly 
// created each time the popover is shown.

var BeakerPopover = function(element, options) {
    // Set trigger to 'manual' so that bootstrap popover's init() doesn't 
    // register any click handlers. We do that ourselves here instead.
    options.trigger = 'manual';
    this.init('beaker_popover', element, options);
    // Register our own click handler but always only show, never hide (or 
    // toggle). The popover view will take care of removing itself when the 
    // user clicks outside of it.
    var popover = this;
    this.$element.on('click.' + this.type, this.options.selector, function (evt) {
        // Don't try to navigate to href="#" or whatever on links
        evt.preventDefault();
        popover.show(evt);
        // If the popover content has an input or textarea, focus it
        // so that the user can start typing straight away.
        popover.tip().find('input,textarea:first').focus();
    });
};

BeakerPopover.prototype = $.extend({}, $.fn.popover.Constructor.prototype, {
    constructor: BeakerPopover,
    hasContent: function () {
        return true;
    },
    tip: function () {
        return this.$tip = this.view.$el;
    },
    show: function (evt) {
        // When this event bubbles up to 'html' it will trigger the newly 
        // created popover's event handler for detecting clicks outside itself, 
        // which means the popover will immediately close itself. So we have to 
        // pass this event down to the popover view so it knows to ignore it.
        this.view = new this.options.view_type({
            model: this.options.model,
            creation_event: evt,
        });
        $.fn.popover.Constructor.prototype.show.apply(this);
    },
    hide: function () {
        throw 'should never be called';
    },
});

$.fn.beaker_popover = function(option) {
    return this.each(function() {
        var $this = $(this), data = $this.data('beaker_popover'),
            options = typeof option == 'object' && option;
        if(!data) $this.data('beaker_popover', (data = new BeakerPopover(this, options)));
        if(typeof option == 'string') data[option]();
    });
};

$.fn.beaker_popover.Constructor = BeakerPopover;

$.fn.beaker_popover.defaults = $.extend({} , $.fn.popover.defaults, {
    placement: 'bottom',
    container: 'body',
});

/**
 * This is just an empty popover, each place where a popover is used should 
 * extend this view to display whatever is desired inside the popover.
 * Pass the extended view type as the *view_type* option when applying the popover plugin.
 *
 * Note that render() is defined here to add the necessary markup for the 
 * popover, the extending view should chain up to render() here and then insert 
 * its content into .popover-content. Messy, but that's what it is.
 */
window.BeakerPopoverView = Backbone.View.extend({
    className: 'popover',
    initialize: function (options) {
        var view = this;
        $('html').on('click.closePopover' + this.cid, function (evt) {
            if (view.$el.has(evt.target).length == 0 &&
                    evt.timeStamp != options.creation_event.timeStamp) {
                // Click was outside of this popover, and was *not* the same 
                // click which created us.
                view.remove();
            }
        });
        this.render();
    },
    render: function () {
        this.$el.html('<div class="arrow"></div><div class="popover-content"></div>');
        return this;
    },
    remove: function () {
        $('html').off('click.closePopover' + this.cid);
        Backbone.View.prototype.remove.apply(this, arguments);
    },
});


})(jQuery);
