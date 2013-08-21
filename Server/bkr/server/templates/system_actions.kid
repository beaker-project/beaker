<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<a href="#" onclick="show_system_actions()" class='link'>(Contact Owner)</a>
<script type='text/javascript'>
    function show_system_actions() {
       $('#system_action').attr('title', 'System Action').dialog({
            buttons : {
                "${problem.desc}" : function () {
                    $(this).dialog("close");
                    show_field("${report_problem_options['name']}", "${problem.desc}");
                },
                "${loan.desc}" : function () {
                    $(this).dialog("close");
                    show_field("${loan_options['name']}", "${loan.desc}");
                }
            },
            resizable: false,
            height: 300,
            width:400,
            autoOpen: true,
            modal: true,});
    }

        function show_field (id, title) {
            $('#'+id).attr('title', title).dialog({
                resizable: false,
                height: 300,
                width: 700,
                modal: true,});
        }
</script>
<span id='system_action' style='display:none' >
        <div id="${report_problem_options['name']}" style='display:none'>
            ${problem.display(
                options=report_problem_options,
                name=report_problem_options['name'],
                action=report_problem_options['action'])}
        </div>
        <div id="${loan_options['name']}" style='display:none;'>
            ${loan.display(options=loan_options,
                name=loan_options['name'], action=loan_options['action'])}
        </div>
</span>
</html>
