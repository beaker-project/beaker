<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
      py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>${title} ${value.id}: ${value}</title>
    <style type="text/css">
        table.install_options {
            margin-top: 2em;
        }
    </style>
</head>
<body class="flora">

<h2>OS Major</h2>
<table class="list">
    <tbody>
        <tr class="list">
            <th class="list" style="width: 25%;">ID</th>
            <td class="list">${value.id}</td>
        </tr>
        <tr class="list">
            <th class="list">Name</th>
            <td class="list">${value.osmajor}</td>
        </tr>
    </tbody>
</table>

<h2>Details</h2>
${form.display(action=action)}

<h2>Install Options</h2>
<form action="save_osmajor_installopts" method="post">
    <input type="hidden" name="osmajor_id" value="${value.id}" />
    <table py:for="arch in [None] + list(value.arches())"
           class="list install_options"
           id="install_options_${arch or 'all'}">
        <?python
        io = value.install_options_by_arch.get(arch, None)
        ?>
        <tbody>
            <tr class="list">
                <th class="list">Arch</th>
                <td class="list">${arch or '(all)'}</td>
            </tr>
            <tr class="list">
                <th class="list" style="width: 25%;">Kickstart Metadata</th>
                <td class="list">
                    <input type="text" size="50"
                        name="installopts.${arch or ''}.ks_meta"
                        value="${io and io.ks_meta}"
                        />
                </td>
            </tr>
            <tr class="list">
                <th class="list">Kernel Options</th>
                <td class="list">
                    <input type="text" size="50"
                        name="installopts.${arch or ''}.kernel_options"
                        value="${io and io.kernel_options}"
                        />
                </td>
            </tr>
            <tr class="list">
                <th class="list">Kernel Options Post</th>
                <td class="list">
                    <input type="text" size="50"
                        name="installopts.${arch or ''}.kernel_options_post"
                        value="${io and io.kernel_options_post}"
                        />
                </td>
            </tr>
        </tbody>
    </table>
    <a href="#" onclick="this.parentNode.submit(); return false;">Save Changes</a>
</form>

</body>
</html>
