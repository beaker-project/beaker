<div xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" class="btn-group">
  <a class="btn" href="${task.clone_link()}">Clone</a>
  <a py:if="task.can_cancel(tg.identity.user) and not task.is_finished()" class="btn" href="${task.cancel_link()}">Cancel</a>
</div>
