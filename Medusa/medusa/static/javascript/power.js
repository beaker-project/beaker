PowerManager = function (id, keyid, controllerid, searchController, systemid) {
	this.id = id;
	this.keyid = keyid;
	this.name = null;
	this.controllerid = controllerid;
	this.systemid = systemid;
	this.powerField = null;
	this.controllerField = null;
	this.systemField = null;
	this.searchController = searchController;
	bindMethods(this);
};

PowerManager.prototype.initialize = function() {
	this.controllerField = getElement(this.controllerid);
	this.systemField = getElement(this.systemid);
	// Use hidden keyid to find out what name space we should be 
	// in.  Then remove the element after.
	this.name = getElement(this.keyid).name;
        removeElement(this.keyid);

	this.powerField = getElement(this.controllerid);
	updateNodeAttributes(this.powerField, {
            "onchange": this.theOnChange
        });
        this.theOnChange()
}

PowerControllerManager = function (id, keyid, controllerid, searchController, powertypeid) {
	this.id = id;
	this.keyid = keyid;
	this.name = null;
	this.powertypeid = powertypeid;
	this.controllerid = controllerid;
	this.powerField = null;
	this.controllerField = null;
	this.searchController = searchController;
	bindMethods(this);
};

PowerControllerManager.prototype.initialize = function() {
	this.controllerField = getElement(this.controllerid);
	// Use hidden keyid to find out what name space we should be 
	// in.  Then remove the element after.
	this.name = getElement(this.keyid).name;
        removeElement(this.keyid);

	this.powerField = getElement(this.powertypeid);
	updateNodeAttributes(this.powerField, {
            "onchange": this.theOnChange
        });
        this.theOnChange()
}

PowerManager.prototype.rowDisplay = function(power_args) {
    desc = power_args["description"]
    key = this.name + "." + power_args["id"]
    input = INPUT({type: "textbox",
                   name: key,
                   value: power_args["value"]})
    return TR(null, TH(null,desc), TD(null,input));
}

PowerControllerManager.prototype.rowDisplay = PowerManager.prototype.rowDisplay

PowerManager.prototype.replaceFields = function(result) {
   new_contents = TABLE(null, TBODY(null, map(this.rowDisplay, result.keys)));
   replaceChildNodes("powerControlArgs" + this.id, new_contents);
}

PowerControllerManager.prototype.replaceFields = PowerManager.prototype.replaceFields

PowerManager.prototype.theOnChange = function(event) {
    if (!this.powerField.value || this.powerField.value == 0) {
        empty_contents = TABLE(null, TBODY(null, TR(null, TD(null,null))));
        replaceChildNodes("powerControlArgs" + this.id, empty_contents);
        return false;
    }
    var params = {"tg_format"          : "json",
                  "tg_random"          : new Date().getTime(),
                  "powercontroller_id" : this.controllerField.value,
                  "system_id"           : this.systemField.value};

    var d = loadJSONDoc(this.searchController + "?" + queryString(params));
    d.addCallback(this.replaceFields);
}

PowerControllerManager.prototype.theOnChange = function(event) {
    if (!this.powerField.value || this.powerField.value == 0) {
        empty_contents = TABLE(null, TBODY(null, TR(null, TD(null,null))));
        replaceChildNodes("powerControlArgs" + this.id, empty_contents);
        return false;
    }
    var params = {"tg_format"          : "json",
                  "tg_random"          : new Date().getTime(),
                  "powercontroller_id" : this.controllerField.value,
                  "powertype_id"       : this.powerField.value};

    var d = loadJSONDoc(this.searchController + "?" + queryString(params));
    d.addCallback(this.replaceFields);
}
