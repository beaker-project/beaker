;(function () {

window.Task = Backbone.Model.extend({
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>tasks/<%- id %>"><%- name %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
    initialize: function (attributes, options) {
        if (options && options.url) {
            this.url = options.url;
        }
    },
    parse: function(data) {
        if (!_.isEmpty(data['uploading_user'])) {
            if (this.get('uploading_user')) {
                var uploading_user = this.get('uploading_user');
                uploading_user.set(uploading_user.parse(data['uploading_user']));
                data['uploading_user'] = uploading_user;
            } else {
                data['uploading_user'] = new User(data['uploading_user'], {parse: true});
            }
        }
        return data;
    }
});


window.TaskLibrary = BeakerPageableCollection.extend({
    model: Task,
    initialize: function (attributes, options) {
        this.url = options.url;
    },
});

})();
