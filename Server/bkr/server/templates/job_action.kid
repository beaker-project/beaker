<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<div xmlns="http://www.w3.org/1999/xhtml"
 xmlns:py="http://purl.org/kid/ns#"
 class='job-action-container'>
  <a class='list' href="${value.clone_link()}">Clone</a>
  <span py:if="value.can_cancel(tg.identity.user) and
   not value.is_finished()"
   py:strip='1'>
    <a class='list job-action' href="${value.cancel_link()}">Cancel</a>
  </span>
  <span py:if="value.can_delete(tg.identity.user) and
   value.is_finished()"
   py:strip='1'>
    ${delete_link.display(**job_delete_attrs)}
  </span>
  <a py:if="export" class='list job-action' href="${export}" >Export</a>
</div>
