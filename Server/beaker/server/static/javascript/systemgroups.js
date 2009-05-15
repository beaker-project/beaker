SystemGroupManager = function(ajaxgridid, systemid, removecontroller) {
    this.ajaxgridid = ajaxgridid;
    this.systemid = systemid;
    this.removecontroller = removecontroller;
    bindMethods(this)
}

SystemGroupManager.prototype.retrieveRemove = function(id) {
    if(!confirm('Are you shure you want to remove group id='+ id)) return;
    var params = {"tg_format"                   : "json",
                  "tg_random"                   : new Date().getTime(),
                  "system_id"                   : this.systemid,
                  "group_id"                    : id};
    var d = loadJSONDoc(this.removecontroller + "?" + queryString(params));
    d.addCallback(this.updateStatus)
}

SystemGroupManager.prototype.updateStatus = function() {
    eval(this.ajaxgridid + "({\"system_id\":" + this.systemid +"});");
}
