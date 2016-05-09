<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
      py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>${value}</title>
</head>
<body class="with-localised-datetimes">

<div class="page-header">
  <h1>${value}</h1>
</div>

${form.display(value=value, action=action)}

<h2>Install Options</h2>
<form action="save_osmajor_installopts" method="post" class="form-horizontal">
    <input type="hidden" name="osmajor_id" value="${value.id}" />
    <fieldset py:for="arch in [None] + list(value.arches())"
           id="install_options_${arch or 'all'}">
        <?python
        io = value.install_options_by_arch.get(arch, None)
        ?>
      <legend>${arch or 'All arches'}</legend>
      <div class="control-group">
        <label class="control-label" for="installopts.${arch or ''}.ks_meta">
          Kickstart Metadata
        </label>
        <div class="controls">
                    <input type="text" size="50"
                        name="installopts.${arch or ''}.ks_meta"
                        value="${io and io.ks_meta}"
                        />
        </div>
      </div>
      <div class="control-group">
        <label class="control-label" for="installopts.${arch or ''}.kernel_options">
          Kernel Options
        </label>
        <div class="controls">
                    <input type="text" size="50"
                        name="installopts.${arch or ''}.kernel_options"
                        value="${io and io.kernel_options}"
                        />
        </div>
      </div>
      <div class="control-group">
        <label class="control-label" for="installopts.${arch or ''}.kernel_options_post">
          Kernel Options Post
        </label>
        <div class="controls">
                    <input type="text" size="50"
                        name="installopts.${arch or ''}.kernel_options_post"
                        value="${io and io.kernel_options_post}"
                        />
        </div>
      </div>
    </fieldset>
    <div class="form-actions">
      <button class="btn btn-primary" type="submit">Save Changes</button>
    </div>
</form>

</body>
</html>
