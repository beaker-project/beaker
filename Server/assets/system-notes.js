
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemNotesView = Backbone.View.extend({
    template: JST['system-notes'],
    events: {
        'click .show-deleted': 'show_deleted',
        'submit form.add-system-note': 'add_note',
        'click .delete-system-note': 'delete_note',
    },
    initialize: function () {
        this.listenTo(this.model, 'change:can_change_notes', this.render);
        this.listenTo(this.model.get('notes'), 'add remove reset change', this.render);
        this.showing_deleted = false;
        this.render();
    },
    render: function () {
        var display_notes = this.model.get('notes').sortBy('created');
        display_notes.reverse();
        var deleted_notes = [];
        if (!this.showing_deleted) {
            var is_deleted = function (note) { return !!note.get('deleted'); };
            deleted_notes = _.filter(display_notes, is_deleted);
            display_notes = _.reject(display_notes, is_deleted);
        }
        this.$el.html(this.template({
            can_change_notes: this.model.get('can_change_notes'),
            display_notes: display_notes,
            deleted_notes: deleted_notes,
        }));
    },
    show_deleted: function () {
        this.showing_deleted = true;
        this.render();
    },
    add_note: function (evt) {
        evt.preventDefault();
        var $form = $(evt.currentTarget);
        $form.find('button').button('loading');
        $form.find('.alert-error').remove();
        var text = $form.find('[name=text]').val();
        this.model.get('notes').create({text: text}, {wait: true,
            error: function (model, xhr) {
                $form.find('button').button('reset');
                $form.append(alert_for_xhr(xhr));
            }});
    },
    delete_note: function (evt) {
        evt.preventDefault();
        var $button = $(evt.currentTarget);
        $button.button('loading');
        var note_id = $button.data('note-id');
        var note = this.model.get('notes').get(note_id);
        bootbox.confirm_as_promise('<p>Are you sure you want to delete this note?</p>')
            .always(function () { $button.button('reset'); })
            .then(function () { return note.save({deleted: 'now'}, {patch: true, wait: true}); })
            .fail(function (xhr) {
                console.log('it is', xhr);
                if (!_.isEmpty(xhr)) {
                    growl_for_xhr(xhr, 'Failed to delete note');
                }
            });
    },
});

})();
