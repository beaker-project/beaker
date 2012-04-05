Provision = function (systemid, distroid, ksmetaid, koptionsid, koptionspostid, controller) {
    this.distroid = distroid;
    this.distrofield = null;
    this.systemid = systemid;
    this.systemfield = null;
    this.ksmetaid = ksmetaid;
    this.ksmetafield = null;
    this.koptionsid = koptionsid;
    this.koptionsfield = null;
    this.koptionspostid = koptionspostid;
    this.koptionspostfield = null;
    this.controller = controller;
    bindMethods(this);
};

Provision.prototype.initialize = function() {
    this.distrofield = getElement(this.distroid);
    this.systemfield = getElement(this.systemid);
    this.ksmetafield = getElement(this.ksmetaid);
    this.koptionsfield = getElement(this.koptionsid);
    this.koptionspostfield = getElement(this.koptionspostid);
    updateNodeAttributes(this.distrofield, {
        "onchange": this.theOnChange
    });
    this.theOnChange()
}

Provision.prototype.theOnChange = function(event) {
    var params = {"tg_format"        : "json",
                  "tg_random"        : new Date().getTime(),
                  "system_id"        : this.systemfield.value,
                  "distro_tree_id"   : this.distrofield.value};
    var d = loadJSONDoc(this.controller + "?" + queryString(params));
    d.addCallback(this.replaceFields);
}

Provision.prototype.replaceFields = function(result) {
    this.ksmetafield.value = result.ks_meta;
    this.koptionsfield.value = result.kernel_options;
    this.koptionspostfield.value = result.kernel_options_post;
}
