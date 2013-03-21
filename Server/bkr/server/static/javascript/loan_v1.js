function loan_success(msg) {
    var msg =
        $('<div class="msg success" style="max-width: 15em;" />')
            .text(msg)
            .appendTo($('#update-loan'))
            .oneTime(2000, 'hide', function () {
                $(this).hide('slow').remove();
                $('#update-loan').dialog('destroy');
                });
}

function update_loan_callback() {
    function f(returned_user) {
        // Hardcoded id from loan_action.kid
        $('#loanee-name').text(returned_user);
        if (!returned_user){
            // Clear our comment field
            $('#update-loan .textarea').val("");
            $('#update-loan .textfield').val("");
            loan_success('Loan has been returned');
            $("[name='update-loan.return']").css('display', 'none');
            if (!$('#update-loan.update').length) {
                $('#loan-settings').css('display', 'none');
            }
        } else {
            loan_success('Loan has been updated');
            $("[name='update-loan.return']").css('display', 'block');
        }
    }
    return f;
}

function loan_action_remote_form_request(form, options, action, callback) {
    var query = formContents(form);
    /* Strip the form name from the options
     * otherwise it doesn't pass the args to the controller
     * in the correct format.
     */
    var stripped_query = [];
    var form_names = query[0];
    for (counter in form_names) {
        stripped_query.push(form_names[counter].replace(/.+?\.(.+)$/, "$1"));
    }
    query[0] = stripped_query;
    jQuery.ajax({
        type: "POST",
        url: action,
        data: queryString(query),
        beforeSend: function() {AjaxLoader.prototype.add_loader(form)},
        complete: function() {AjaxLoader.prototype.remove_loader(form)},
        error: function(e) { failure('Status ' + e['status'])},
        success: callback()});
}
