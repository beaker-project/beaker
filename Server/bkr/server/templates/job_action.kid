<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
<script type='text/javascript' src='/static/javascript/job_delete.js' />
<script type='text/javascript' py:if="type_ == 'joblist'">
 
function job_delete_success(t_id) {
    //remove the row from the list
    $("tr td a:contains('"+ t_id + "')").parents('tr').fadeOut(1000, function() { $(this).remove() });
}
</script>

<script type='text/javascript' py:if="type_ == 'jobpage'">
 function job_delete_success(t_id) {
    var newpara = $('<p></p>').text('Succesfully deleted '+ t_id)
    var dialog_div = $('<div></div>').attr('title','Success').append(newpara)
    jQuery.fx.speeds._default = 2000;
    dialog_div.dialog({
        autoOpen: true,
        hide: "explode",
        resizable: false,
        height:200,
        modal: true,
        open: function(event, ui) { 
            $(this).oneTime(1000, function() {$(this).dialog("close");$(location).attr('href','${redirect_to}')}); 
            }
    });
 }
</script>

<div>
<a class='list' href="${task.clone_link()}">Clone</a><br/>
<span py:if="('admin' in tg.identity.groups or task.is_owner(tg.identity.user)) and not task.is_finished()">
<a class='list' href="${task.cancel_link()}">Cancel</a><br/>
</span>
<span py:if="('admin' in tg.identity.groups or task.is_owner(tg.identity.user)) and task.is_finished()">
<a class='list' style='cursor:pointer;color: #22437f;' py:attrs='job_details'>Delete</a><br/>
</span>
</div>

</html>
