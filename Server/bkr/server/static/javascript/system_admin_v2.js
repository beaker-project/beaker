var allowed_action = { 'add': 1, 'remove': 1}
function add_system_admin (controller, group_id) {
    _change_admin_system(controller, 'add', group_id)
}

function remove_system_admin (controller, group_id) {
    _change_admin_system(controller, 'remove', group_id)
}

function change_admin_status(cmd, group_id, system_id, controller) {
    var params = {'tg_format': 'json',
                  'tg_random': new Date().getTime(),
                  'system_id': system_id,
                  'group_id': group_id,
                  'cmd': cmd}
    var d = loadJSONDoc(controller + '?' + queryString(params));
    d.addCallback(change_admin_result,group_id)
}

function change_admin_result(group_id,result) {
    $("#admin_group_"+group_id).toggle()
    $("#non_admin_group_"+group_id).toggle()
}

function _change_admin_system(controller, action, group_id) {
    if (allowed_action[action]) {
        change_admin_status(action, group_id, $('#groups_id').val(), controller);
    }
}
