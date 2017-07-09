from django import template
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from forum.models import Tag, MarkedTag
from forum.templatetags import argument_parser
from forum import settings

register = template.Library()

class QuestionItemNode(template.Node):
    template = template.loader.get_template('question_list/item.html')

    def __init__(self, question, options):
        self.question = template.Variable(question)
        self.options = options

    def render(self, context):
        return self.template.render(template.Context({
            'question': self.question.resolve(context),
            'question_summary': self.options.get('question_summary', 'no' ) == 'yes',
            'favorite_count': self.options.get('favorite_count', 'no') == 'yes',
            'signature_type': self.options.get('signature_type', 'lite'),
        }))

class TermItemNode(template.Node):
    template = template.loader.get_template('term_list/item.html')

    def __init__(self, term, options):
        self.term = template.Variable(term)
        self.options = options

    def render(self, context):
        return self.template.render(template.Context({
            'term': self.term.resolve(context),
        }))

class CaseItemNode(template.Node):
    template = template.loader.get_template('case_list/item.html')
    
    def __init__(self, case, options):
        self.case = template.Variable(case)
        self.options = options
    
    def render(self, context):
        return self.template.render(template.Context({
            'case': self.case.resolve(context),
            'case_summary': self.options.get('case_summary', 'no' ) == 'yes',
            'favorite_count': self.options.get('favorite_count', 'no') == 'yes',
            'signature_type': self.options.get('signature_type', 'lite'),
        }))

class ArticleItemNode(template.Node):
    template = template.loader.get_template('article_list/item.html')
    
    def __init__(self, article, options):
        self.article = template.Variable(article)
        self.options = options
    
    def render(self, context):
        return self.template.render(template.Context({
                                                     'article': self.article.resolve(context),
                                                     'article_summary': self.options.get('article_summary', 'no' ) == 'yes',
                                                     'favorite_count': self.options.get('favorite_count', 'no') == 'yes',
                                                     'signature_type': self.options.get('signature_type', 'lite'),
                                                     }))


class DashItemNode(template.Node):
    template = template.loader.get_template('dash_list/item.html')
    
    def __init__(self, node, options):
        self.node = template.Variable(node)
        self.options = options
    
    def render(self, context):
        return self.template.render(template.Context({
                                                     'node': self.node.resolve(context),
                                                     'node_summary': self.options.get('node_summary', 'no' ) == 'yes',
                                                     'favorite_count': self.options.get('favorite_count', 'no') == 'yes',
                                                     'signature_type': self.options.get('signature_type', 'lite'),
                                                     }))



class SubscriptionItemNode(template.Node):
    template = template.loader.get_template('question_list/subscription_item.html')

    def __init__(self, subscription, question, options):
        self.question = template.Variable(question)
        self.subscription = template.Variable(subscription)
        self.options = options

    def render(self, context):
        return self.template.render(template.Context({
            'question': self.question.resolve(context),
            'subscription': self.subscription.resolve(context),
            'signature_type': self.options.get('signature_type', 'lite'),
        }))

@register.tag
def question_list_item(parser, token):
    tokens = token.split_contents()[1:]
    return QuestionItemNode(tokens[0], argument_parser(tokens[1:]))

@register.tag
def term_list_item(parser, token):
    tokens = token.split_contents()[1:]
    return TermItemNode(tokens[0], argument_parser(tokens[1:]))

@register.tag
def case_list_item(parser, token):
    tokens = token.split_contents()[1:]
    return CaseItemNode(tokens[0], argument_parser(tokens[1:]))

@register.tag
def article_list_item(parser, token):
    tokens = token.split_contents()[1:]
    return ArticleItemNode(tokens[0], argument_parser(tokens[1:]))

@register.tag
def dash_list_item(parser, token):
    tokens = token.split_contents()[1:]
    return DashItemNode(tokens[0], argument_parser(tokens[1:]))

@register.tag
def subscription_list_item(parser, token):
    tokens = token.split_contents()[1:]
    return SubscriptionItemNode(tokens[0], tokens[1], argument_parser(tokens[2:]))

@register.inclusion_tag('question_list/sort_tabs.html')
def question_sort_tabs(sort_context):
    return sort_context

@register.inclusion_tag('question_list/related_tags.html')
def question_list_related_tags(questions):
    if len(questions):
        tags = Tag.objects.filter(nodes__id__in=[q.id for q in questions]).distinct()

        if settings.LIMIT_RELATED_TAGS:
            tags = tags[:settings.LIMIT_RELATED_TAGS]

        return {'tags': tags}
    else:
        return {'tags': False}

@register.inclusion_tag('dash_list/related_tags.html')
def node_list_related_tags(nodes):
    if len(nodes):
        tags = Tag.objects.filter(nodes__id__in=[n.id for n in nodes]).distinct()
        
        if settings.LIMIT_RELATED_TAGS:
            tags = tags[:settings.LIMIT_RELATED_TAGS]
        
        return {'tags': tags}
    else:
        return {'tags': False}


@register.inclusion_tag('question_list/tag_selector.html', takes_context=True)
def tag_selector(context):
    request = context['request']
    show_interesting_tags = settings.SHOW_INTERESTING_TAGS_BOX

    if request.user.is_authenticated():
        pt = MarkedTag.objects.filter(user=request.user)
        return {
            'request' : request,
            "interesting_tag_names": pt.filter(reason='good').values_list('tag__name', flat=True),
            'ignored_tag_names': pt.filter(reason='bad').values_list('tag__name', flat=True),
            'user_authenticated': True,
            'show_interesting_tags' : show_interesting_tags,
        }
    else:
        return { 'request' : request, 'user_authenticated': False, 'show_interesting_tags' : show_interesting_tags }
