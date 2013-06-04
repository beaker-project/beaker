<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>${value.display_name}</title>
</head>

<body class="flora">
    <h1>${value.display_name}</h1>
    <div py:if="tg.identity.user and value.can_edit(tg.identity.user)"
         py:content="form(method='POST', action=action, value=value, options=options, disabled_fields=disabled_fields)" />
    &nbsp;
    <div>
       ${usergrid.display(value.users)}
       <div py:if="tg.identity.user and value.can_modify_membership(tg.identity.user)"
            py:content="user_form(method='POST', action=user_action, value=value)" />
    </div>
    &nbsp;
    <div>
       ${systemgrid.display(value.systems)}
       <div py:if="tg.identity.user and value.can_edit(tg.identity.user)"
            py:content="system_form(method='POST', action=system_action, value=value)" />
    </div>
    <div>
       <br/>
       ${group_permissions.display(value, form=group_form, grid=group_permissions_grid)}
    </div>
</body>
</html>
