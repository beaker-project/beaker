;(function () {

window.BackgridUserCell = Backgrid.Cell.extend({
    template: JST['backgrid-user-cell'],
    className: 'user-cell',
    formatter: {
        fromRaw: function (value) {
            if (_.isEmpty(value))
                return '';
            return value.get('user_name');
        },
        toRaw: function (value) {
            if (_.isEmpty(value))
                return null;
            return new User({user_name: value});
        },
    },
    render: function () {
        this.$el.empty();
        var user = this.model.get(this.column.get('name'));
        if (!_.isEmpty(user)) {
            this.$el.html(this.template(user.attributes));
        }
        return this;
    },
});

// Based on https://github.com/wyuenho/backgrid-moment-cell/blob/master/backgrid-moment-cell.js
// but simplified for Beaker's specific needs
window.BackgridDateTimeCell = Backgrid.Cell.extend({
    className: 'datetime-cell',
    formatter: {
        fromRaw: function (value) {
            if (!value)
                return '';
            return moment.utc(value).local().format('YYYY-MM-DD HH:mm:ss Z');
        },
        toRaw: function (value) {
            return value;
        },
    },
});

})();
