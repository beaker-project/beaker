
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.Job = Backbone.Model.extend({
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>jobs/<%- id %>"><%- t_id %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
});

window.RecipeSet = Backbone.Model.extend({
    parse: function (data) {
        data['job'] = !_.isEmpty(data['job']) ? new Job(data['job']) : null;
        return data;
    },
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>jobs/<%- job.get("id") %>"><%- t_id %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
});

window.Recipe = Backbone.Model.extend({
    initialize: function (attributes, options) {
        options = options || {};
        if (options.url)
            this.url = options.url;
    },
    parse: function (data) {
        var recipe = this;
        if (!_.isEmpty(data['recipeset'])) {
            if (this.get('recipeset')) {
                var recipeset = this.get('recipeset');
                recipeset.set(recipeset.parse(data['recipeset']));
                data['recipeset'] = recipeset;
            } else {
                data['recipeset'] = new RecipeSet(data['recipeset'], {parse: true});
            }
        }
        if (!_.isEmpty(data['guest_recipes'])) {
            var recipes = this.get('guest_recipes') || [];
            data['guest_recipes'] = _.map(data['guest_recipes'], function (recipedata, i) {
                var recipe = recipes[i];
                if (recipe) {
                    recipe.set(recipe.parse(recipedata));
                } else {
                    recipe = new Recipe(recipedata, {parse: true});
                }
                recipe.set({hostrecipe: recipe}, {silent: true});
                return recipe;
            });
        }
        return data;
    },
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>recipes/<%- id %>"><%- t_id %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
});


})();
