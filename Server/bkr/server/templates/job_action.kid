<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
<div>
<a class='list' href="${task.clone_link()}">Clone</a><br/>
<span py:if="('admin' in tg.identity.groups or task.is_owner(tg.identity.user)) and not task.is_finished()">
<a class='list' href="${task.cancel_link()}">Cancel</a><br/>
</span>
<span py:if="'admin' not in tg.identity.groups and task.is_owner(tg.identity.user) and task.is_finished()">
<a class='list' style='cursor:pointer;color: #22437f;' py:attrs='job_details'>Delete</a><br/>
</span>
<a py:if="export" class='list' href="${export}">Export</a><br/>
</div>

</html>
