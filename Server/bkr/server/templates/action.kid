<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<div xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
  <a class='list' href="${task.clone_link()}">Clone</a><br/>
  <a py:if="task.can_cancel(tg.identity.user) and not task.is_finished()" class='list' href="${task.cancel_link()}">Cancel</a><br/>
</div>
