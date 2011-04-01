from bkr.server.model import RetentionTag

class RetentionTagUtility:
    """
    Utility class for RetentionTag controller 
    """
    @classmethod
    def save_tag(cls, **kw):
        tag = kw.get('tag')  
        is_default = bool(int(kw.get('default')))
        new_tag = RetentionTag(tag, is_default)
        return new_tag

    @classmethod
    def edit_default(cls, **kw):
        is_default =  bool(int(kw.get('default')))
        id = kw.get('id')
        tag = RetentionTag.by_id(id)
        tag.default = is_default 
