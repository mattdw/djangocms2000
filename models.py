from django.db import models
from django.conf import settings
from django.contrib.sites.models import Site
import re, os
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
#from custom_fields import RelativeFilePathField
from django.template.loader import get_template
from django import template
import markdown2, gfm, datetime
from django.utils.encoding import force_unicode
from django.utils.html import escape, strip_tags
from django.utils.text import truncate_words

#from custom_fields import TemplateChoiceField
from django.db.models.signals import class_prepared, post_save, pre_save
from django.utils.functional import curry
from django.test.client import Client

try:
    from audit import AuditTrail
except ImportError:
    class AuditTrail(object):
        def __init__(*args, **kwargs):
            pass

"""
from django.db.models.signals import post_init
from django.utils.functional import curry
"""

BLOCK_TYPE_CHOICES = (
    ('plain', 'Plain text'),
    ('markdown', 'Markdown'),
    ('html', 'HTML'),
)

class Block(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    
    #page = models.ForeignKey(Page)
    label = models.CharField(max_length=255)
    format = models.CharField(max_length=10, choices=BLOCK_TYPE_CHOICES, default='', blank=False)
    raw_content = models.TextField("Content", blank=True, )
    compiled_content = models.TextField(blank=True, editable=False)
    

    history = AuditTrail(show_in_admin=True)
    
    def label_display(self):
        return self.label.replace('-', ' ').replace('_', ' ').capitalize()
    
    def content_display(self):
        return truncate_words(strip_tags(self.compiled_content), 10)
    
    def __unicode__(self):
        return self.label
        #return "'%s' on %s" % (self.label, self.page.uri)
    
    def save(self, *args, **kwargs):
        if self.format == 'markdown':
            if self.raw_content.strip():
                self.compiled_content = markdown2.markdown(gfm.gfm(force_unicode((self.raw_content))))
            else:
                self.compiled_content = ''
        else:
            self.compiled_content = self.raw_content
        super(Block, self).save(*args, **kwargs)    
    
    class Meta:
       ordering = ['id',]
    

class Image(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    history = AuditTrail(show_in_admin=True)

    def label_display(self):
        return self.label.replace('-', ' ').replace('_', ' ').title()
    
    
    #page = models.ForeignKey(Page)
    label = models.CharField(max_length=255, editable=False)
    file = models.ImageField(upload_to=settings.UPLOAD_PATH, blank=True)
    description = models.CharField(max_length=255, blank=True)
    def __unicode__(self):
        return self.label
        #return "'%s' on %s" % (self.label, self.page.uri)
 
    #class Meta:
    #   ordering = ['label']




TEMPLATE_DIR = settings.TEMPLATE_DIRS[0]

def get_templates_from_dir(dir, exclude=None):
    TEMPLATE_REGEX = re.compile('\.html$')
    templates = []
    for root, dirs, files in os.walk("%s/%s" % (TEMPLATE_DIR, dir)):
        for file in files:
            path = ("%s/%s" % (root.replace(TEMPLATE_DIR, ''), file)).strip('/')
            filename = path.replace(dir, '').strip('/')
            if TEMPLATE_REGEX.search(path) and (not exclude or not exclude.search(filename)):
                templates.append((path, filename))
    
    return templates

def template_choices():
    CMS_EXCLUDE_REGEX = re.compile('base\.html$|^cms/|\.inc\.html$')
    OTHER_EXCLUDE_REGEX = re.compile('(?:^404\.html|^500\.html|^base\.html|^admin|^djangocms2000/|base\.html$)')
    return (
        ('Static Templates', get_templates_from_dir("djangocms2000", CMS_EXCLUDE_REGEX)),
        ('Other Templates', get_templates_from_dir("", OTHER_EXCLUDE_REGEX)),
    )
    

def get_child_pages(parent_uri, qs=None):
    return (qs or Page.objects).filter(uri__iregex=r'^' + parent_uri + '[\w_\-\.]+/$')


class _CMSAbstractBaseModel(models.Model):
    class Meta:
        abstract = True

    blocks = generic.GenericRelation(Block)
    images = generic.GenericRelation(Image)
        
    def get_title(self):
        try:
            return self.blocks.get(label="title").compiled_content
        except Block.DoesNotExist:
            try:
                return self.blocks.get(label="name").compiled_content
            except Block.DoesNotExist:
                return self

# add blocks on save via dummy render
def dummy_render(sender, **kwargs):
    if isinstance(kwargs['instance'], _CMSAbstractBaseModel):
        # dummy-render the object's absolute url to generate blocks
        c = Client()
        response = c.get(str(kwargs['instance'].get_absolute_url()), {}, HTTP_COOKIE='')   
post_save.connect(dummy_render)




class LivePageManager(models.Manager):
    def get_query_set(self):
        return super(LivePageManager, self).get_query_set().filter(is_live=True)



class Page(_CMSAbstractBaseModel):
    uri = models.CharField(max_length=255, unique=True)
    #template = TemplateChoiceField(path="%s/" % settings.TEMPLATE_DIRS[0], match="[^(?:404)(?:500)(?:base)(?:admin/base_site)].*\.html", recursive=True)
    template = models.CharField(max_length=255, default="djangocms2000/default.html", help_text="Choose from Static Templates unless you're sure of what you're doing.", choices=template_choices()) # help_text=("Example: djangocms2000/default.html")
    site = models.ForeignKey(Site, default=1)
    creation_date = models.DateTimeField(auto_now_add=True)
    is_live = models.BooleanField(default=True)
    
    objects = models.Manager()
    live = LivePageManager()
    
    class Meta:
        ordering = ('uri',)
    
    history = AuditTrail(show_in_admin=True)
    
    
    def get_children(self, qs=None):
        return get_child_pages(self.uri, qs)


    def __unicode__(self):
        return self.uri

    def get_absolute_url(self):
        return self.uri

    def page_title(self):
        return self.get_title()

# if no creation date exists, set one or the db will throw an error
def site_check(sender, **kwargs):
    if not kwargs['instance'].site:
        kwargs['instance'].site = Site.objects.all()[0]
pre_save.connect(site_check, sender=Page)



class MenuItem(models.Model):
    page = models.OneToOneField(Page)
    text = models.CharField(max_length=255, blank=True, default="", help_text="If left blank, will use page title")
    title = models.CharField(max_length=255, blank=True, default="")
    sort = models.IntegerField(blank=True, default=0)
    
    class Meta:
        ordering = ('sort','id',)
    
    def get_text(self):
        return self.text or self.page.page_title()
    
    def __unicode__(self):
        return self.get_text()
    






"""
Abstract model for other apps that want to have related Blocks and Images
"""
class CMSBaseModel(_CMSAbstractBaseModel):

    
    BLOCK_LABELS = [] # should be a tuple of the form ('name', 'format',), but will fall back if it's just a string
    IMAGE_LABELS = []
    
    
    def __unicode__(self):
        return self.get_title()
    
    def _block_LABEL(self, label):
        return self.blocks.get(label=label).compiled_content
    
    
    
    class Meta:
        abstract = True

# add extra blocks on save
def add_blocks(sender, **kwargs):
    if isinstance(kwargs['instance'], CMSBaseModel):
        # dummy-render the object's absolute url to generate blocks
        c = Client()
        #print kwargs['instance'].get_absolute_url()
        response = c.get(str(kwargs['instance'].get_absolute_url()), {}, HTTP_COOKIE='') 
        
        for label_tuple in kwargs['instance'].BLOCK_LABELS:
            if isinstance(label_tuple, str):
                label_tuple = (label_tuple, None,)
            block, created = Block.objects.get_or_create(
                label=label_tuple[0],
                content_type=ContentType.objects.get_for_model(kwargs['instance']),
                object_id=kwargs['instance'].id
            )
            # only set the format if the block was just created, or
            if (not block.format or created) and label_tuple[1]:
                block.format = label_tuple[1]
                block.save()
            
        for label in kwargs['instance'].IMAGE_LABELS:
            Image.objects.get_or_create(
                label=label,
                content_type=ContentType.objects.get_for_model(kwargs['instance']),
                object_id=kwargs['instance'].id
            )
post_save.connect(add_blocks)


"""
Possible todo: If the base model has a field named _block_LABEL, 
save the block's value there as well via post_save?
"""


# Set up the accessor method for block content
def add_methods(sender, **kwargs):
    if issubclass(sender, CMSBaseModel):
        for label_tuple in sender.BLOCK_LABELS:
            setattr(sender, 'block_%s' % label_tuple[0],
                curry(sender._block_LABEL, label=label_tuple[0]))

# connect the add_accessor_methods function to the post_init signal
class_prepared.connect(add_methods)

