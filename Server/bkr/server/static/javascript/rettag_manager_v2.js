RetentionTagManager = function () {
    this.field_type = {}
    this.controllers = {
                        'secondary' : function(t) { return function(x,y,z) { t.RecipeSetChanged(x,y,z) } },
                        'primary' : function (t) { return function(x,y,z) { t.ChangeAll(x,y,z) } }
                       }
    this.my_regex = /^.+?(\d{1,})$/

}

RetentionTagManager.prototype = new PrimarySecondary()

RetentionTagManager.prototype.RecipeSetChanged = function(new_retentiontag_id,recipeset_id,callback) { 
    var params = {"tg_format" : "json",
                  "tg_random" : new Date().getTime(),
                  "retentiontag_id" : new_retentiontag_id,
                  "recipeset_id" : recipeset_id }
    AjaxLoader.prototype.add_loader('retentiontag_recipeset_' + recipeset_id) 
    var d = loadJSONDoc('/jobs/change_retentiontag_recipeset' + "?" + queryString(params))
    // I wish we could just pass the callback var to priorityChanged
    // Reason we can't is because it each call uses the same pointer value it seems! 
    d.addCallback(RetentionTagManager.prototype.valueChanged,callback['function'],callback['args']['element_id'],callback['args']['value']) //mochikit's built in currying...
}

