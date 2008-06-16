from kid import Element

def make_link(url, text):
    # make an <a> element
    a = Element('a', {'class': 'list'}, href=url)
    a.text = text
    return a

