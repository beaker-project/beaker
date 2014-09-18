<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<title>$title</title>
</head>
<body>
<div class="page-header">
  <h1>$title</h1>
</div>
<p py:if="tg.config('beaker.reservation_policy_url')">
  Please ensure that you adhere to the
  <a href="${tg.config('beaker.reservation_policy_url')}">reservation
  policy for Beaker systems</a>.
</p>
<div class="reserveworkflow"></div>
<script type="text/javascript">
$(function () {
    new ReserveWorkflow({
        el: '.reserveworkflow',
        options: ${tg.to_json(options)},
        selection: ${tg.to_json(selection)},
    });
});
</script>
</body>
</html>
