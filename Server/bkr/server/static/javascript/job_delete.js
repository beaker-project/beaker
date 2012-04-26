function do_job_delete_complete(result) {
    if (result['success']) {
        job_delete_success(result['t_id'])
    } else {
        var err_msg = 'There was a problem deleting your task ' + result['t_id'];
        if (result['err_msg']) {
            err_msg += "The error message returned was: '" + result['err_msg'] + "'";
         }
        failure(err_msg)
    }
}


function JobDelete(action, data, options) {
    do_and_confirm(action, data, do_job_delete_complete, undefined, 'delete')
}
