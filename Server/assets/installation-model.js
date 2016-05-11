
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.Installation = Backbone.Model.extend({
    parse: function (data) {
        if (!_.isEmpty(data['commands'])) {
            var commands = this.get('commands') || [];
            data['commands'] = _.map(data['commands'], function (commanddata, i) {
                var command = commands[i];
                if (command) {
                    command.set(command.parse(commanddata));
                } else {
                    command = new Command(commanddata, {parse: true});
                }
                return command;
            });
        }
        return data;
    },
});

})();
