<div xmlns:py="http://purl.org/kid/ns#" style="vertical-align: top;">
    <form py:if="not readonly"
          action="${tg.url(action)}" method="post"
          id="job_whiteboard_form"
          py:attrs="form_attrs">
        <script type="text/javascript">
            function job_whiteboard_save_success() {
                var msg = $('<div class="msg success" style="max-width: 20em;">Whiteboard has been updated</div>')
                        .hide()
                        .appendTo($('#job_whiteboard_form'))
                        .show('slow')
                        .oneTime(2000, 'hide', function () { $(this).hide('slow').remove(); });
            }
            function job_whiteboard_save_failure() {
                var msg = $('<div class="msg warn" style="max-width: 20em;">Unable to update whiteboard</div>')
                        .hide()
                        .appendTo($('#job_whiteboard_form'))
                        .show('slow');
            }
            function job_whiteboard_before() {
                AjaxLoader.prototype.add_loader('job_whiteboard_form')
            }

            function job_whiteboard_complete() {
                AjaxLoader.prototype.remove_loader('job_whiteboard_form') 
            }
        </script>
        ${hidden_id.display(value=job_id)}
        <span py:replace="field.display(value=value, attrs={'style': 'width: 20em;'})" />
        <button type="submit">Save</button>
    </form>
    <span py:if="readonly">${value}</span>
</div>
