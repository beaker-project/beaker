<form xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
      action="install_options" method="post" name="install_options_form">
<input type="hidden" name="distro_tree_id" value="${value.id}" />
<script type="text/javascript" py:if="not readonly">
$(function () {
    var form = document.install_options_form;
    var edit_link = $('<button class="btn">Edit</button>');
    var save_link = $('<button class="btn btn-primary">Save Changes</button>');
    edit_link.click(function () {
        $('td', form).each(function (i, elem) {
            var name = elem.id;
            var value = elem.textContent;
            var input = $('<input type="text" size="50" />')
                .attr('name', name);
            $(elem).empty().append(input);
            input.val(value);
        });
        $(this).remove();
        $(form).append(save_link);
        return false;
    });
    save_link.click(function () {
        form.submit();
        return false;
    });
    $(form).append(edit_link);
})
</script>
<table class="table table-bordered" id="install_options">
    <tbody>
        <tr class="list">
            <th class="list" style="width: 25%;">Kickstart Metadata</th>
            <td class="list" id="ks_meta">${value.ks_meta}</td>
        </tr>
        <tr class="list">
            <th class="list">Kernel Options</th>
            <td class="list" id="kernel_options">${value.kernel_options}</td>
        </tr>
        <tr class="list">
            <th class="list">Kernel Options Post</th>
            <td class="list" id="kernel_options_post">${value.kernel_options_post}</td>
        </tr>
    </tbody>
</table>
</form>
