$(document).ready( function () {
        $("a[id^='add_admin_']").click(function () { 
            my_id = $(this).attr('id')
            group_id = my_id.replace(/^add_admin_(\d{1,})$/,"$1") 
            res = change_admin_status('add',group_id,$('#groups_id').val())
        }); 

        $("a[id ^= 'remove_admin_']").click(function () {
            my_id = $(this).attr('id')
            group_id = my_id.replace(/^remove_admin_(\d{1,})$/,"$1")
            res = change_admin_status('remove',group_id,$('#groups_id').val())
        });


    });

    change_admin_status = function(cmd,group_id,system_id) { 
        var params = { 'tg_format' : 'json',
                        'tg_random' : new Date().getTime(),
                        'system_id': system_id,
                        'group_id' : group_id,
                        'cmd' : cmd}
        var d = loadJSONDoc('/change_system_admin?' + queryString(params));
        d.addCallback(change_admin_result,group_id)                
    }

    change_admin_result = function(group_id,result) {
            $("#admin_group_"+group_id).toggle()
            $("#non_admin_group_"+group_id).toggle() 
    }
