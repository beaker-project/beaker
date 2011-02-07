function job_delete_success(t_id) {
    //remove the row from the list
    $("tr td a:contains('"+ t_id + "')").parents('tr').fadeOut(1000, function() { $(this).remove() });
}
