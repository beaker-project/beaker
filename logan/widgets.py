from turbogears import validators, url, config
import model
from turbogears.widgets import (Form, TextField, SubmitButton, TextArea,
                                AutoCompleteField, SingleSelectField, CheckBox,
                                HiddenField, RemoteForm, CheckBoxList, JSLink,
                                Widget, TableForm, FormField, CompoundFormField,
                                static, PaginateDataGrid, RepeatingFormField)

class myPaginateDataGrid(PaginateDataGrid):
    template = "logan.templates.my_paginate_datagrid"
