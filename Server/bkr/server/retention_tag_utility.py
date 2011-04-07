from bkr.server.model import RetentionTag

class RetentionTagUtility:
    """
    Utility class for RetentionTag controller 
    """
    @classmethod
    def save_tag(cls, **kw):
        tag = kw.get('tag')  
        is_default = bool(int(kw.get('default')))
        needs_product = bool(kw.get('needs_product',None))
        new_tag = RetentionTag(tag, is_default, needs_product)
        return new_tag

    @classmethod
    def edit_default(cls, **kw):
        is_default =  bool(int(kw.get('default')))
        id = kw.get('id')
        needs_product = bool(kw.get('needs_product', None))
        tag = RetentionTag.by_id(id)
        tag.default = is_default 
        tag.needs_product = needs_product 
