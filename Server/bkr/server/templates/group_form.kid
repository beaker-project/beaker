<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>${value.display_name}</title>
</head>


<body>
    <div class="page-header">
        <h1>${value.display_name}</h1>
    </div>
    <div py:if="tg.identity.user and value.can_edit(tg.identity.user)"
         py:content="form(method='POST', action=action, value=value, options=options, disabled_fields=disabled_fields)" />
    <div py:if="tg.identity.user and tg.identity.user in value.users" id="root_pw_display">
         <h2>Root password</h2>
         <p py:if="group_pw">The group root password is: <code>${group_pw}</code></p>
         <p py:if="not group_pw">No group root password set. Group jobs will use the root password preferences of the submitting user.</p>
    </div>
    <div>
        <h2>Group members</h2>
       ${usergrid.display(sorted(value.user_group_assocs, key=lambda ug: not ug.is_owner))}
       <div py:if="tg.identity.user and value.can_modify_membership(tg.identity.user)"
            py:content="user_form(method='POST', action=user_action, value=value)" />
    </div>
      <div py:if="value.ldap">
	<br/>
      <i>Members populated from LDAP</i>
    </div>
    <div>
        <h2>Systems</h2>
        <div py:if="value.systems"
             py:content="systemgrid.display(value.systems)" />
       <div py:if="tg.identity.user and tg.identity.user.is_admin()"
            py:content="system_form(method='POST', action=system_action, value=value)" />
    </div>
    <div>
        <h2>Permissions</h2>
       ${group_permissions.display(value, form=group_form, grid=group_permissions_grid)}
    </div>
</body>
</html>
