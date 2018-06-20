<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
  <title>${title}</title>
</head>
<body>
  <script type="text/javascript">
    var job = new Job(${tg.to_json(job)}, {parse: true, url: ${tg.to_json(tg.url(job.href))}});
    job.activity.reset({entries: ${tg.to_json(job.all_activity)}}, {parse: true});
    $(function () {
        // For backwards compatibility, replace an anchor like #RS_123 (from 
        // the old job page) with #set123.
        var old_anchor_match = /^#RS_(\d+)$/.exec(location.hash);
        if (old_anchor_match != null) {
            location.hash = '#set' + old_anchor_match[1];
        }
        $('#container')
            .append(new JobHeaderView({model: job}).el)
            .append(new JobInfoView({model: job}).el)
            .append(new JobRecipesView({model: job}).el);
        if (window.location.hash == '#activity')
            new JobActivityModal({model: job});
    });
    // auto-refresh while the job is not finished
    var autofetch = function () {
        if (!job.get('is_finished')) {
            job.fetch({
                timeout: 600000,
                success: () => {
                    _.delay(autofetch, 30000);
                },
                error: () => {
                    _.delay(autofetch, 30000);
                }
            });
        };
    };
    _.delay(autofetch, 30000);
  </script>
</body>
</html>
