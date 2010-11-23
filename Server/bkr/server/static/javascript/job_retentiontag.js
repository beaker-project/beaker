
function job_retentiontag_save_success() {
    jquery_obj = $("#job_retentiontag")

    var msg = $('<div class="msg success" style="max-width: 20em;">Whiteboard has been updated</div>')
                .hide()
                .appendTo(jquery_obj)
                .show('slow')
                .fadeIn(1000)
                .oneTime(2000, 'hide', function () { $(this).fadeOut(1000).remove(); });
}

function job_retentiontag_before() {
                AjaxLoader.prototype.add_loader('job_retentiontag')
}


function job_retentiontag_complete() {
                AjaxLoader.prototype.remove_loader('job_retentiontag') 
}


function job_retentiontag_save_failure() {
                var msg = $('<div class="msg warn" style="max-width: 20em;">Unable to update Tag</div>')
                        .hide()
                        .appendTo($('#job_retentiontag'))
                        .fadeIn(1000);
            }
