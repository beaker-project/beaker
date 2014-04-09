
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

/*
  Derived from: backgrid-paginator <http://github.com/wyuenho/backgrid-paginator>
  Adjusted to match Beaker's convention for grid pagination controls
*/

;(function () {

window.BeakerBackgridPaginator = Backbone.View.extend({
    tagName: 'div',
    className: 'pagination pagination-right',
    template: JST['backgrid-paginator'],
    events: {
        'click a': 'change_page',
    },
    initialize: function () {
        var collection = this.collection;
        this.listenTo(collection, 'add remove reset', this.render);
    },
    render: function () {
        this.$el.html(this.template(this.collection.state));
    },
    change_page: function (evt) {
        this.collection.getPage(parseInt($(evt.currentTarget).data('page')));
        evt.preventDefault();
    },
});

})();
