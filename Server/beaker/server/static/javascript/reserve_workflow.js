ReserveWorkflow = function (arch,distro_family,method,tag,distro,submit,arch_val,distro_family_val,tag_val,method_val,
                            all_arches,all_distro_familys,all_tags,all_methods) {
    this.arch_id = arch
    this.distro_family_id = distro_family
    this.method_id = method
    this.tag_id = tag
    this.distro_id = distro 
    this.submit_id = submit

    this.arch_val = arch_val
    this.distro_family_val = distro_family_val
    this.method_val = method_val
    this.tag_val = tag_val

    this.all_arches = all_arches
    this.all_distro_familys = all_distro_familys
    this.all_tags = all_tags
    this.all_methods = all_methods
    bindMethods(this)
};

ReserveWorkflow.prototype.initialize = function() {  
    getElement(this.submit_id).setAttribute('disabled',1)
    this.replace_fields() 
}

ReserveWorkflow.prototype.replace_fields = function() {  
    // For some stupid reason I can't get a closure to work in JS...so I'm writing all this redundant code
    // what a pita
    replaceChildNodes(this.arch_id, map(this.replaceArch ,this.all_arches))
    replaceChildNodes(this.distro_family_id, map(this.replaceDistroFamily ,this.all_distro_familys))
    replaceChildNodes(this.tag_id, map(this.replaceTag ,this.all_tags))
    replaceChildNodes(this.method_id, map(this.replaceMethod ,this.all_methods))
}


ReserveWorkflow.prototype.replaceMethod = function(arg) { 
        if ( arg == this.method_val ) {
            option = OPTION({"value": arg,
                             "selected": true}, arg);
        } else {
            option = OPTION({"value": arg}, arg);
        }
        return option;
}
ReserveWorkflow.prototype.replaceDistroFamily = function(arg) { 
        if ( arg == this.distro_family_val ) {
            option = OPTION({"value": arg,
                             "selected": true}, arg);
        } else {
            option = OPTION({"value": arg}, arg);
        }
        return option;
}

ReserveWorkflow.prototype.replaceTag = function(arg) { 
        if ( arg == this.tag_val ) {
            option = OPTION({"value": arg,
                             "selected": true}, arg);
        } else {
            option = OPTION({"value": arg}, arg);
        }
        return option;
}

ReserveWorkflow.prototype.replaceArch = function(arg) { 
        if ( arg == this.arch_val ) {
            option = OPTION({"value": arg,
                             "selected": true}, arg);
        } else {
            option = OPTION({"value": arg}, arg);
        }
        return option;
}

ReserveWorkflow.prototype.get_distros = function() {
    var arch_value = getElement(this.arch_id).value
    var distro_family_value = getElement(this.distro_family_id).value
    var method_value = getElement(this.method_id).value
    var tag_value = getElement(this.tag_id).value

    var params = { 'tg_format' : 'json',
                   'tg_random' : new Date().getTime(),
                   'arch' : arch_value,
                   'distro_family' : distro_family_value,
                   'method' : method_value,
                   'tag' : tag_value }
    var d = loadJSONDoc('/reserveworkflow/get_distro_options?' + queryString(params)); 
    d.addCallback(this.replaceDistros)
};


ReserveWorkflow.prototype.replaceDistros = function(result) {  
    if (result.options.length > 0) {
        getElement(this.submit_id).removeAttribute('disabled')
    } else {
        result.options.unshift('None selected')
        getElement(this.submit_id).setAttribute('disabled',1)
    }

    replaceChildNodes(this.distro_id, map(this.replaceOptions, result.options));
}

ReserveWorkflow.prototype.replaceOptions = function(arg) {
    option = OPTION({"value": arg}, arg)
    return option
}
