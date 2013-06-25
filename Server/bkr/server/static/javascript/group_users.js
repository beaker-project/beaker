//Script for handling group owners addition/removal

$(document).ready(function() {

    function create_status_element(this_link, msg){

        var status_id = "change_ownership_status";

        //Remove if this already exists
        $("#"+status_id).remove();

        $(this_link).after(function() {
            var status_msg = document.createElement("div");
            status_msg.setAttribute("id", status_id);
            status_msg.setAttribute("class", "flash");
            return status_msg;
        });

        $("#"+status_id).text(msg).delay(5000).fadeOut(1000);

    }

    // Handle add owner operation
    $(".change_ownership_add").live("click", function(event) {

        event.preventDefault();
        var post_url = this.href;
        var this_link = this;

        var jqxhr = $.post(post_url,{}, function() {
            $(this_link).text("Remove (-)");
            $(this_link).attr("class", "change_ownership_remove");
            $(this_link).attr("href", post_url.replace("grant_owner","revoke_owner"));
            create_status_element(this_link, 'Ownership granted');
        })
                .fail(function() {
                    create_status_element(this_link, jqxhr.responseText);
                });
    });

    // Handle remove owner operation
    $(".change_ownership_remove").live("click", function(event) {

        event.preventDefault();
        var post_url = this.href;
        var this_link = this;

        var jqxhr = $.post(post_url,{}, function() {
            var to_remove_uid = post_url.split("&")[1].split("=")[1];
            if (to_remove_uid == jqxhr.responseText){
                window.location.replace("mine");
            }
            else
            {
                $(this_link).text("Add (+)");
                $(this_link).attr("class", "change_ownership_add");
                $(this_link).attr("href", post_url.replace("revoke_owner","grant_owner"));
                create_status_element(this_link, 'Ownership revoked');
            }})
                .fail(function() {
                    create_status_element(this_link, jqxhr.responseText);
                });
    });
});
