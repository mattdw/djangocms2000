from django import forms
#from models import Block, Page, Image
#from tinymce.widgets import TinyMCE
from models import Page, template_choices
import re
from django.conf import settings


class BlockForm(forms.Form):
	block_id = forms.CharField(widget=forms.HiddenInput)
	format = forms.CharField(widget=forms.HiddenInput)
	
	raw_content = forms.CharField(widget=forms.Textarea)


class ImageForm(forms.Form):
	image_id = forms.CharField(widget=forms.HiddenInput)
	redirect_to = forms.CharField(widget=forms.HiddenInput)
	
	description = forms.CharField(widget=forms.TextInput)
	file = forms.FileField()




URL_STRIP_REGEX = re.compile('[^A-z0-9\-_\/\.]')
URL_DASH_REGEX = re.compile('--+')
class PageForm(forms.ModelForm):
    template = forms.CharField(
        widget=forms.Select(choices=template_choices()),
        help_text="Choose from Static Templates unless you're sure of what you're doing."
    )
    def __init__(self, *args, **kwargs):
        super(PageForm, self).__init__(*args, **kwargs)
        # just in case a template has been added/changed since last server restart
        self.fields['template'].widget.choices = template_choices()
     
    class Meta:
        model = Page
    
    def clean_uri(self):
        uri = URL_STRIP_REGEX.sub('', self.cleaned_data['uri'].replace(' ', '-')).lower()
        uri = URL_DASH_REGEX.sub('-', uri).strip('-')
        
        uri = ("/%s" % (uri.lstrip('/'))).replace('//', '/')
        
        if settings.APPEND_SLASH and uri[-1] != '/':
            uri = "%s/" % uri
        
        if Page.objects.exclude(pk=self.instance and self.instance.pk).filter(uri__in=[uri.rstrip('/'), "%s/" % uri.rstrip('/')]):
            raise forms.ValidationError('A page with this uri already exists')
        
        return uri



class PublicPageForm(PageForm):
    class Meta(PageForm.Meta):
        exclude = ['site',]
    
    
    