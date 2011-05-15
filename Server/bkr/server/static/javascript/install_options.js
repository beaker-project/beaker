InstallOptions = function (osmajorid, osversionid, controller) {
    this.osmajorid = osmajorid;
    this.osmajorfield = null;
    this.osversionid = osversionid;
    this.osversionfield = null;
    this.controller = controller;
    bindMethods(this);
};

InstallOptions.prototype.initialize = function() {
    this.osmajorfield = getElement(this.osmajorid);
    this.osversionfield = getElement(this.osversionid);
    updateNodeAttributes(this.osmajorfield, {
        "onchange": this.theOnChange
    });
    this.theOnChange()
}

InstallOptions.prototype.theOnChange = function(event) {
    var params = {"tg_format"        : "json",
                  "tg_random"        : new Date().getTime(),
                  "osmajor_id"       : this.osmajorfield.value};
    var d = loadJSONDoc(this.controller + "?" + queryString(params));
    d.addCallback(this.replaceFields);
}

InstallOptions.prototype.replaceFields = function(result) {
    osversions = result.osversions
    while ( this.osversionfield.options.length ) {
        this.osversionfield.options[0] = null;
    }
    for ( i = 0; i < osversions.length; i++ ) {
        $(this.osversionfield).append(
             $('<option></option>').val(osversions[i][0]).html(osversions[i][1])
                                  );
    }
}
