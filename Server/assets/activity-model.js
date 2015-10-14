
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.ActivityEntry = Backbone.Model.extend({
    parse: function (data) {
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user'], {parse: true}) : null;
        switch (data['type']) {
            case 'user_activity':
                data['object'] = !_.isEmpty(data['object']) ?
                        new User(data['object'], {parse: true}) : null;
                break;
            case 'group_activity':
                data['object'] = !_.isEmpty(data['group']) ?
                        new Group(data['group'], {parse: true}) : null;
                break;
            case 'system_activity':
                data['object'] = !_.isEmpty(data['system']) ?
                        new System(data['system'], {parse: true}) : null;
                break;
            case 'system_pool_activity':
                data['object'] = !_.isEmpty(data['pool']) ?
                        new SystemPool(data['pool'], {parse: true}) : null;
                break;
            case 'lab_controller_activity':
                data['object'] = !_.isEmpty(data['lab_controller']) ?
                        new LabController(data['lab_controller'], {parse: true}) : null;
                break;
            case 'job_activity':
                data['object'] = !_.isEmpty(data['job']) ?
                        new Job(data['job'], {parse: true}) : null;
                break;
            case 'recipeset_activity':
                data['object'] = !_.isEmpty(data['recipeset']) ?
                        new RecipeSet(data['recipeset'], {parse: true}) : null;
                break;
            case 'recipe_activity':
                data['object'] = !_.isEmpty(data['recipe']) ?
                        new Recipe(data['recipe'], {parse: true}) : null;
                break;
            case 'distro_activity':
                data['object'] = !_.isEmpty(data['distro']) ?
                        new Distro(data['distro'], {parse: true}) : null;
                break;
            case 'distro_tree_activity':
                data['object'] = !_.isEmpty(data['distro_tree']) ?
                        new DistroTree(data['distro_tree'], {parse: true}) : null;
                break;
            default:
                console.log('Unrecognised activity type when parsing', data);
                data['object'] = null;
        }
        return data;
    },
});

window.Activity = BeakerPageableCollection.extend({
    model: ActivityEntry,
    initialize: function (attributes, options) {
        this.url = options.url;
    },
});

})();
