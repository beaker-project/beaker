-- Query for all CEE users in Beaker and total up the number of provisions they have done
SELECT tg_user.user_name, COUNT(tg_user.user_name) AS count
FROM tg_user
INNER JOIN user_group ON user_group.user_id = tg_user.user_id
INNER JOIN activity ON activity.user_id = tg_user.user_id
WHERE activity.action = 'Provision'
    AND group_id = (SELECT group_id FROM tg_group WHERE group_name = 'cee-users')
GROUP BY tg_user.user_name
ORDER BY count DESC
