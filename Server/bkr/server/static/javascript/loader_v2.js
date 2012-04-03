AjaxLoader = function () {}

AjaxLoader.prototype.initialize = function () { bindMethods(this) }

AjaxLoader.prototype.loading_suffix = '_loading'


AjaxLoader.prototype.remove_loader = function (target_dom) {
    $('#' + target_dom + '' + AjaxLoader.prototype.loading_suffix).remove()
}

AjaxLoader.prototype.add_loader = function (target_dom){
    var msg = $('<span id="' + target_dom +'' + this.loading_suffix + '"><img src="/static/images/ajax-loader.gif"></img> </span>')
        .insertAfter($('#'+ target_dom))
}

AjaxLoader2 = function (target) {
    bindMethods(this);
    this.target = target;
    this.msg = $('<span/>').attr('id', target.id + '_loading').html(
            '<img src="/static/images/ajax-loader.gif"/>');
    $(target).after(this.msg);
};
AjaxLoader2.prototype.remove = function () {
    this.msg.remove();
};
