# encoding:utf-8
import datetime
import logging
from urllib import unquote
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404, HttpResponsePermanentRedirect,  HttpResponse
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.template import RequestContext
from django import template
from django.utils.html import *
from django.utils.http import urlquote
from django.db.models import Q, Count
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe

from forum import settings as django_settings
from forum.utils.html import hyperlink
from forum.utils.diff import textDiff as htmldiff
from forum.utils import pagination
from forum.forms import *
from forum.models import *
from forum.actions import QuestionViewAction
from forum.http_responses import HttpResponseUnauthorized
from forum.feed import RssQuestionFeed, RssAnswerFeed
from forum.utils.pagination import generate_uri

import decorators

class HottestQuestionsSort(pagination.SortBase):
    def apply(self, questions):
        return questions.extra(select={'new_child_count': '''
            SELECT COUNT(1)
                FROM forum_node fn1
                WHERE fn1.abs_parent_id = forum_node.id
                    AND fn1.id != forum_node.id
                    AND NOT(fn1.state_string LIKE '%%(deleted)%%')
                    AND added_at > %s'''
            },
            select_params=[ (datetime.datetime.now() - datetime.timedelta(days=2))
                .strftime('%Y-%m-%d')]
        ).order_by('-new_child_count', 'last_activity_at')

class UnansweredQuestionsSort(pagination.SortBase):
    def apply(self, questions):
        return questions.extra(select={'answer_count': '''
            SELECT COUNT(1)
                FROM forum_node fn1
                WHERE fn1.abs_parent_id = forum_node.id
                    AND fn1.id != forum_node.id
                    AND fn1.node_type='answer'
                    AND NOT(fn1.state_string LIKE '%%(deleted)%%')'''
            }).order_by('answer_count', 'last_activity_at')

class QuestionListPaginatorContext(pagination.PaginatorContext):
    def __init__(self, id='QUESTIONS_LIST', prefix='', pagesizes=(15, 30, 50), default_pagesize=30):
        super (QuestionListPaginatorContext, self).__init__(id, sort_methods=(
            (_('active'), pagination.SimpleSort(_('active'), '-last_activity_at', _("Most <strong>recently updated</strong> questions"))),
            (_('newest'), pagination.SimpleSort(_('newest'), '-added_at', _("most <strong>recently asked</strong> questions"))),
            (_('hottest'), HottestQuestionsSort(_('hottest'), _("most <strong>active</strong> questions in the last 24 hours</strong>"))),
            (_('mostvoted'), pagination.SimpleSort(_('most voted'), '-score', _("most <strong>voted</strong> questions"))),
            (_('unanswered'), UnansweredQuestionsSort('unanswered', "questions with no answers")),
        ), pagesizes=pagesizes, default_pagesize=default_pagesize, prefix=prefix)

class TermListPaginatorContext(pagination.PaginatorContext):
    def __init__(self, id='TERMS_LIST', prefix='', pagesizes=(15, 30, 50), default_pagesize=30):
        super (TermListPaginatorContext, self).__init__(id, pagesizes=pagesizes, default_pagesize=default_pagesize, prefix=prefix)

class CaseListPaginatorContext(pagination.PaginatorContext):
    def __init__(self, id='CASES_LIST', prefix='', pagesizes=(15, 30, 50), default_pagesize=30):
        super (CaseListPaginatorContext, self).__init__(id, pagesizes=pagesizes, default_pagesize=default_pagesize, prefix=prefix)

class NodeListPaginatorContext(pagination.PaginatorContext):
    def __init__(self, id='QUESTIONS_LIST', prefix='', pagesizes=(15, 30, 50), default_pagesize=30):
        super (NodeListPaginatorContext, self).__init__(id, sort_methods=(
                (_('newest'), pagination.SimpleSort(_('newest'), '-added_at', _("most <strong>recently added</strong> topics"))),
                (_('mostviewed'), pagination.SimpleSort(_('most viewed'), '-extra_count', _("most <strong>viewed</strong> topics"))),
            ), pagesizes=pagesizes, default_pagesize=default_pagesize, prefix=prefix)


class AnswerSort(pagination.SimpleSort):
    def apply(self, answers):
        if not settings.DISABLE_ACCEPTING_FEATURE:
            return answers.order_by(*(['-marked'] + list(self._get_order_by())))
        else:
            return super(AnswerSort, self).apply(answers)

class AnswerPaginatorContext(pagination.PaginatorContext):
    def __init__(self, id='ANSWER_LIST', prefix='', default_pagesize=10):
        super (AnswerPaginatorContext, self).__init__(id, sort_methods=(
            (_('active'), AnswerSort(_('active answers'), '-last_activity_at', _("most recently updated answers/comments will be shown first"))),
            (_('oldest'), AnswerSort(_('oldest answers'), 'added_at', _("oldest answers will be shown first"))),
            (_('newest'), AnswerSort(_('newest answers'), '-added_at', _("newest answers will be shown first"))),
            (_('votes'), AnswerSort(_('popular answers'), ('-score', 'added_at'), _("most voted answers will be shown first"))),
        ), default_sort=_('votes'), pagesizes=(5, 10, 20), default_pagesize=default_pagesize, prefix=prefix)

class TagPaginatorContext(pagination.PaginatorContext):
    def __init__(self):
        super (TagPaginatorContext, self).__init__('TAG_LIST', sort_methods=(
            (_('name'), pagination.SimpleSort(_('by name'), 'name', _("sorted alphabetically"))),
            (_('used'), pagination.SimpleSort(_('by popularity'), '-used_count', _("sorted by frequency of tag use"))),
        ), default_sort=_('used'), pagesizes=(30, 60, 120))
    

def feed(request):
    return RssQuestionFeed(
                request,
                Question.objects.filter_state(deleted=False).order_by('-last_activity_at'),
                settings.APP_TITLE + _(' - ')+ _('latest questions'),
                settings.APP_DESCRIPTION)(request)


def apply_moderation(request,questions):
    if request.user.is_authenticated():
        if request.user.is_superuser or request.user.is_staff:
            return questions
        else:
            return questions.exclude(approved=False)

    else:
        return questions.exclude(approved=False)

@decorators.render('index.html')
def index(request):
    paginator_context = QuestionListPaginatorContext()
    paginator_context.base_path = reverse('questions')

    return question_list(request,
                         apply_moderation(request,Question.objects.all()),
                         base_path=reverse('questions'),
                         feed_url=reverse('latest_questions_feed'),
                         paginator_context=paginator_context)


#@decorators.render('questions.html', 'unanswered', _('unanswered'), weight=400)
def unanswered(request):
    return question_list(request,
                         apply_moderation(request,Question.objects.exclude(id__in=Question.objects.filter(children__marked=True).distinct()).exclude(marked=True)),
                         _('open questions without an accepted answer'),
                         None,
                         _("Unanswered Questions"))

@decorators.render('dashboard.html', 'dashboard', _('dashboard'), weight=0)
def dashboard(request):
    return dashboard_list(request,
                     Node.objects.all().exclude(node_type='term'),
                     _('questions and cases'),
                     None,
                     _("Questions and Cases"))

@decorators.render('questions.html', 'questions', _('questions'), weight=0)
def questions(request,type=''):
    return question_list(request,
                         apply_moderation(request,Question.objects.all()),
                         _('questions'),type=type)

@decorators.render('terms.html', 'terms', _('terms'), weight=0)
def terms(request):
    return term_list(request,
                     Term.objects.all(),
                     _('terms'))

@decorators.render('cases.html', 'cases', _('cases'), weight=0)
def cases(request):
    return case_list(request,
                         Case.objects.all(),
                         _('cases'))

@decorators.render('articles.html', 'articles', _('articles'), weight=0)
def articles(request):
    return articles_list(request,
                     Article.objects.all(),
                     _('articles'))

@decorators.render('dashboard.html')
def tag(request, tag):
    try:
        tag = Tag.active.get(name=unquote(tag))
    except Tag.DoesNotExist:
        raise Http404

    # Getting the questions QuerySet
    #questions = apply_moderation(request,Question.objects.filter(tags__id=tag.id))
    
    questions =Node.objects.filter(tags__id=tag.id)
    

    if request.method == "GET":
        user = request.GET.get('user', None)

        if user is not None:
            try:
                questions = apply_moderation(request,questions.filter(author=User.objects.get(username=user)))
            except User.DoesNotExist:
                raise Http404

    # The extra tag context we need to pass
    tag_context = {
        'tag' : tag,
    }

    # The context returned by the question_list function, contains info about the questions
    question_context = dashboard_list(request,
                         questions,
                         mark_safe(_(u'topics tagged <span class="tag">%(tag)s</span>') % {'tag': tag}),
                         None,
                         mark_safe(_(u'topics Tagged With %(tag)s') % {'tag': tag}),
                         False)

    # If the return data type is not a dict just return it
    if not isinstance(question_context, dict):
        return question_context

    question_context = dict(question_context)

    # Create the combined context
    context = dict(question_context.items() + tag_context.items())

    return context


@decorators.render('questions.html', 'questions', tabbed=False)
def user_questions(request, mode, user, slug):
    user = get_object_or_404(User, id=user)

    if mode == _('asked-by'):
        questions = Question.objects.filter(author=user)
        description = _("Questions asked by %s")
    elif mode == _('answered-by'):
        questions = Question.objects.filter(children__author=user, children__node_type='answer').distinct()
        description = _("Questions answered by %s")
    elif mode == _('subscribed-by'):
        if not (request.user.is_superuser or request.user == user):
            return HttpResponseUnauthorized(request)
        questions = user.subscriptions

        if request.user == user:
            description = _("Questions you subscribed %s")
        else:
            description = _("Questions subscribed by %s")
    else:
        raise Http404


    return question_list(request, questions,
                         mark_safe(description % hyperlink(user.get_profile_url(), user.username)),
                         page_title=description % user.username)

def question_list(request, initial,
                  list_description=_('questions'),
                  base_path=None,
                  page_title=_("All Questions"),
                  allowIgnoreTags=True,
                  feed_url=None,
                  paginator_context=None,
                  show_summary=None,
                  feed_sort=('-added_at',),
                  feed_req_params_exclude=(_('page'), _('pagesize'), _('sort')),
                  extra_context={},
                  type=''):

    if show_summary is None:
        show_summary = bool(settings.SHOW_SUMMARY_ON_QUESTIONS_LIST)

    questions = initial.filter_state(deleted=False)

    if request.user.is_authenticated() and allowIgnoreTags:
        questions = questions.filter(~Q(tags__id__in = request.user.marked_tags.filter(user_selections__reason = 'bad')))

    if page_title is None:
        page_title = _("Questions")

    if request.GET.get('type', None) == 'rss':
        if feed_sort:
            questions = questions.order_by(*feed_sort)
        return RssQuestionFeed(request, questions, page_title, list_description)(request)

    keywords =  ""
    if request.GET.get("q"):
        keywords = request.GET.get("q").strip()

    #answer_count = Answer.objects.filter_state(deleted=False).filter(parent__in=questions).count()
    #answer_description = _("answers")

    if not feed_url:
        req_params = generate_uri(request.GET, feed_req_params_exclude)

        if req_params:
            req_params = '&' + req_params

        feed_url = request.path + "?type=rss" + req_params
    tags =  ""
    for q in questions:
        tags = tags + q.tagnames + " "
    uniq_tags = set( tag for tag in tags.split())
    if len(uniq_tags) > 0:
        tags = reduce(lambda a,b:a + " " + b , uniq_tags)
    context = {
        'questions' : questions.distinct(),
        'questions_count' : questions.count(),
        'cases_count' : Case.objects.count(),
        'keywords' : keywords,
        'list_description': list_description,
        'base_path' : base_path,
        'page_title' : page_title,
        'tab' : 'questions',
        'feed_url': feed_url,
        'show_summary' : show_summary,
        'amp': type == 'amp',
        'meta' : {'description' : "List of questions related to Bridge, Engine Room and whole ship equipment, navigation, engineering, repair, maintenance and safety on board the ship.", 
                  'keywords' : tags}
    }
    context.update(extra_context)

    return pagination.paginated(request,
                               ('questions', paginator_context or QuestionListPaginatorContext()), context)

def term_list(request, initial,
                  list_description=_('terms'),
                  base_path=None,
                  page_title=_("Terms"),
                  allowIgnoreTags=True,
                  feed_url=None,
                  paginator_context=None,
                  show_summary=None,
                  feed_sort=None,
                  feed_req_params_exclude=(_('page'), _('pagesize'), _('sort')),
                  extra_context={}):
    
    if show_summary is None:
        show_summary = bool(settings.SHOW_SUMMARY_ON_QUESTIONS_LIST)

    terms = initial.order_by('title')

    if request.user.is_authenticated() and allowIgnoreTags:
        terms = terms.filter(~Q(tags__id__in = request.user.marked_tags.filter(user_selections__reason = 'bad')))
    
    if page_title is None:
        page_title = _("Terms")

    keywords =  ""
    if request.GET.get("q"):
        keywords = request.GET.get("q").strip()

    tags =  ""
    for t in terms:
        print(t.tagnames)
        tags = tags + t.tagnames + " "
    uniq_tags = set( tag for tag in tags.split())
    tags = {}
    if len(uniq_tags) > 0:
        tags = reduce(lambda a,b:a + " " + b , uniq_tags)
    context = {
        'terms' : terms.distinct(),
        'terms_count' : terms.count(),
        'keywords' : keywords,
        'list_description': list_description,
        'base_path' : base_path,
        'page_title' : page_title,
        'tab' : 'terms',
        'feed_url': feed_url,
        'show_summary' : show_summary,
        'meta' : {'description' : "List of terms related to Bridge, Engine Room and whole ship equipment, navigation, engineering, repair, maintenance and safety on board the ship.",
            'keywords' : tags}
    }
    context.update(extra_context)

    return pagination.paginated(request,
                            ('terms', paginator_context or TermListPaginatorContext()), context)

def case_list(request, initial,
                  list_description=_('cases'),
                  base_path=None,
                  page_title=_("All Cases"),
                  allowIgnoreTags=True,
                  feed_url=None,
                  paginator_context=None,
                  show_summary=None,
                  feed_sort=('-added_at',),
                  feed_req_params_exclude=(_('page'), _('pagesize'), _('sort')),
                  extra_context={}):
    
    if show_summary is None:
        show_summary = bool(settings.SHOW_SUMMARY_ON_QUESTIONS_LIST)
    
    cases = initial.filter_state(deleted=False)

    if request.user.is_authenticated() and allowIgnoreTags:
        cases = cases.filter(~Q(tags__id__in = request.user.marked_tags.filter(user_selections__reason = 'bad')))
    
    if page_title is None:
        page_title = _("Cases")


    keywords =  ""
    if request.GET.get("q"):
        keywords = request.GET.get("q").strip()


    tags =  ""
    for c in cases:
        print(c.tagnames)
        tags = tags + c.tagnames + " "
    uniq_tags = set( tag for tag in tags.split())
    tags = reduce(lambda a,b:a + " " + b , uniq_tags)
    context = {
        'cases' : cases.distinct(),
        'cases_count' : cases.count(),
        'keywords' : keywords,
        'list_description': list_description,
        'base_path' : base_path,
        'page_title' : page_title,
        'tab' : 'cases',
        'feed_url': feed_url,
        'show_summary' : show_summary,
        'meta' : {'description' : "List of case studies related to Bridge, Engine Room and whole ship equipment, navigation, engineering, repair, maintenance and safety on board the ship.",
            'keywords' : tags}
    }
    context.update(extra_context)

    return pagination.paginated(request,
                            ('cases', paginator_context or CaseListPaginatorContext()), context)

def dashboard_list(request, initial,
                  list_description=_('nodes'),
                  base_path=None,
                  page_title=_("Dashboard"),
                  allowIgnoreTags=True,
                  feed_url=None,
                  paginator_context=None,
                  show_summary=None,
                  feed_sort=('-added_at',),
                  feed_req_params_exclude=(_('page'), _('pagesize'), _('sort')),
                  extra_context={}):
    
    if show_summary is None:
        show_summary = bool(settings.SHOW_SUMMARY_ON_QUESTIONS_LIST)
    
    nodes = initial.filter_state(deleted=False)

    if request.user.is_authenticated() and allowIgnoreTags:
        nodes = nodes.filter(~Q(tags__id__in = request.user.marked_tags.filter(user_selections__reason = 'bad')))
    
    if page_title is None:
        page_title = _("Dashboard")

    keywords =  ""
    if request.GET.get("q"):
        keywords = request.GET.get("q").strip()

    #answer_count = Answer.objects.filter_state(deleted=False).filter(parent__in=questions).count()
    #answer_description = _("answers")


    tags =  ""
    for n in nodes:
        tags = tags + n.tagnames + " "
    uniq_tags = set( tag for tag in tags.split())
    if len(uniq_tags) > 0:
        tags = reduce(lambda a,b:a + " " + b , uniq_tags)
    context = {
        'nodes' : nodes.distinct(),
        'nodes_count' : nodes.count(),
        'keywords' : keywords,
        'list_description': list_description,
        'base_path' : base_path,
        'page_title' : page_title,
        'tab' : 'dashboard',
        'feed_url': feed_url,
        'show_summary' : show_summary,
        'meta' : {'description' : "Dashboard with all data available related to Bridge, Engine Room and whole ship equipment, navigation, engineering, repair, maintenance and safety on board the ship.",
            'keywords' : tags}
    }
    context.update(extra_context)

    return pagination.paginated(request,
                            ('nodes', paginator_context or NodeListPaginatorContext()), context)


def search(request):
    if request.method == "GET" and "q" in request.GET:
        keywords = request.GET.get("q")
        search_type = request.GET.get("t")

        if not keywords:
            return HttpResponseRedirect(reverse(index))
        if search_type == 'tag':
            return HttpResponseRedirect(reverse('tags') + '?q=%s' % urlquote(keywords.strip()))
        elif search_type == "user":
            return HttpResponseRedirect(reverse('users') + '?q=%s' % urlquote(keywords.strip()))
        else:
            return question_search(request, keywords)
    else:
        return render_to_response("search.html", context_instance=RequestContext(request))

@decorators.render('dashboard.html')
def question_search(request, keywords):
    rank_feed = False
    can_rank, initial = Node.objects.search(keywords)

    if can_rank:
        sort_order = None

        if isinstance(can_rank, basestring):
            sort_order = can_rank
            rank_feed = True

        paginator_context = QuestionListPaginatorContext()
        paginator_context.sort_methods[_('ranking')] = pagination.SimpleSort(_('relevance'), sort_order, _("most relevant questions"))
        paginator_context.force_sort = _('ranking')
    else:
        paginator_context = None

    feed_url = mark_safe(escape(request.path + "?type=rss&q=" + keywords))

    return dashboard_list(request, initial,
                         _("topics matching '%(keywords)s'") % {'keywords': keywords},
                         None,
                         _("topics matching '%(keywords)s'") % {'keywords': keywords},
                         paginator_context=paginator_context,
                         feed_url=feed_url, feed_sort=rank_feed and (can_rank,) or '-added_at')


@decorators.render('tags.html', 'tags', _('tags'), weight=100)
def tags(request):
    stag = ""
    tags = Tag.active.all()

    if request.method == "GET":
        stag = request.GET.get("q", "").strip()
        if stag:
            tags = tags.filter(name__icontains=stag)

    return pagination.paginated(request, ('tags', TagPaginatorContext()), {
        "tags" : tags,
        "stag" : stag,
        "keywords" : stag
    })

def update_question_view_times(request, question):
    last_seen_in_question = request.session.get('last_seen_in_question', {})

    last_seen = last_seen_in_question.get(question.id, None)

    if (not last_seen) or (last_seen < question.last_activity_at):
        QuestionViewAction(question, request.user, ip=request.META['REMOTE_ADDR']).save()
        last_seen_in_question[question.id] = datetime.datetime.now()
        request.session['last_seen_in_question'] = last_seen_in_question

def update_case_view_times(request, case):
    last_seen_in_case = request.session.get('last_seen_in_case', {})
    
    last_seen = last_seen_in_case.get(case.id, None)
    
    if (not last_seen) or (last_seen < case.last_activity_at):
        QuestionViewAction(case, request.user, ip=request.META['REMOTE_ADDR']).save()
        last_seen_in_case[case.id] = datetime.datetime.now()
        request.session['last_seen_in_case'] = last_seen_in_case

def update_node_view_times(request, n):
    last_seen_in_case = request.session.get('last_seen_in_case', {})
    
    last_seen = last_seen_in_case.get(n.id, None)
    
    if (not last_seen) or (last_seen < n.last_activity_at):
        NodeViewAction(n, request.user, ip=request.META['REMOTE_ADDR']).save()
        last_seen_in_case[n.id] = datetime.datetime.now()
        request.session['last_seen_in_case'] = last_seen_in_case

def match_question_slug(id, slug):
    slug_words = slug.split('-')
    qs = Question.objects.filter(title__istartswith=slug_words[0])

    for q in qs:
        if slug == urlquote(slugify(q.title)):
            return q

    return None

def answer_redirect(request, answer):
    pc = AnswerPaginatorContext()

    sort = pc.sort(request)

    if sort == _('oldest'):
        filter = Q(added_at__lt=answer.added_at)
    elif sort == _('newest'):
        filter = Q(added_at__gt=answer.added_at)
    elif sort == _('votes'):
        filter = Q(score__gt=answer.score) | Q(score=answer.score, added_at__lt=answer.added_at)
    else:
        raise Http404()

    count = answer.question.answers.filter(Q(marked=True) | filter).exclude(state_string="(deleted)").count()
    pagesize = pc.pagesize(request)

    page = count / pagesize
    
    if count % pagesize:
        page += 1
        
    if page == 0:
        page = 1

    return HttpResponseRedirect("%s?%s=%s&focusedAnswerId=%s#%s" % (
        answer.question.get_absolute_url(), _('page'), page, answer.id, answer.id))

@decorators.render("question.html", 'questions')
def question(request, id, slug='', answer=None):
    try:
        question = Question.objects.get(id=id)
    except:
        if slug:
            question = match_question_slug(id, slug)
            if question is not None:
                return HttpResponseRedirect(question.get_absolute_url())

        raise Http404()

    if question.nis.deleted and not request.user.can_view_deleted_post(question):
        raise Http404

    if request.GET.get('type', None) == 'rss':
        return RssAnswerFeed(request, question, include_comments=request.GET.get('comments', None) == 'yes')(request)

    if answer:
        answer = get_object_or_404(Answer, id=answer)

        if (question.nis.deleted and not request.user.can_view_deleted_post(question)) or answer.question != question:
            raise Http404

        if answer.marked:
            return HttpResponsePermanentRedirect(question.get_absolute_url())

        return answer_redirect(request, answer)

    if settings.FORCE_SINGLE_URL and (slug != slugify(question.title)):
        return HttpResponsePermanentRedirect(question.get_absolute_url())

    if request.POST:
        answer_form = AnswerForm(request.POST, user=request.user)
    else:
        answer_form = AnswerForm(user=request.user)

    question.body = question.body.replace('test','hello')
    answers = request.user.get_visible_answers(question)

    for ans in answers:
        ans.body = ans.body.replace('wesw','hello')
        print ans.body

    update_question_view_times(request, question)

    if request.user.is_authenticated():
        try:
            subscription = QuestionSubscription.objects.get(question=question, user=request.user)
        except:
            subscription = False
    else:
        subscription = False
    try:
        focused_answer_id = int(request.GET.get("focusedAnswerId", None))
    except TypeError, ValueError:
        focused_answer_id = None
    
    return pagination.paginated(request, ('answers', AnswerPaginatorContext()), {
    "question" : question,
    "answer" : answer_form,
    "answers" : answers,
    "similar_questions" : question.get_related_questions(),
    "subscription": subscription,
    "embed_youtube_videos" : settings.EMBED_YOUTUBE_VIDEOS,
    "focused_answer_id" : focused_answer_id,
    "meta" : {'description': question.title, 'keywords' : question.tagnames}
    })

@decorators.render("term.html", 'terms')
def term(request, id, slug=''):
    try:
        term = Term.objects.get(id=id)
    except:
        if slug:
            term = match_question_slug(id, slug)
            if term is not None:
                return HttpResponseRedirect(term.get_absolute_url())
        raise Http404()


    if settings.FORCE_SINGLE_URL and (slug != slugify(term.title)):
        return HttpResponsePermanentRedirect(term.get_absolute_url())

    return pagination.paginated(request, [], {
                            "term" : term,
                            "embed_youtube_videos" : settings.EMBED_YOUTUBE_VIDEOS,
                            "similar_terms" : term.get_related(),
                            "meta" : {'description': term.title, 'keywords' : term.tagnames}
                            })

@decorators.render("case.html", 'cases')
def case(request, id, slug=''):
    try:
        case = Case.objects.get(id=id)
    except:
        if slug:
            case = match_question_slug(id, slug)
            if tcase is not None:
                return HttpResponseRedirect(case.get_absolute_url())

        raise Http404()
    
    if case.nis.deleted and not request.user.can_view_deleted_post(case):
        raise Http404
    

    if settings.FORCE_SINGLE_URL and (slug != slugify(case.title)):
        return HttpResponsePermanentRedirect(case.get_absolute_url())

    update_case_view_times(request, case)
    

    return pagination.paginated(request, [], {
                            "case" : case,
                            "similar_questions" : case.get_related_questions(),
                            "embed_youtube_videos" : settings.EMBED_YOUTUBE_VIDEOS,
                            "meta" : {'description': case.title, 'keywords' : case.tagnames}
                            })

@decorators.render("article.html", 'articles')
def article(request, id, slug=''):
    try:
        article = Article.objects.get(id=id)
    except:
        if slug:
            article = match_question_slug(id, slug)
            if tcase is not None:
                return HttpResponseRedirect(article.get_absolute_url())

        raise Http404()
    
    if article.nis.deleted and not request.user.can_view_deleted_post(article):
        raise Http404


    if settings.FORCE_SINGLE_URL and (slug != slugify(article.title)):
        return HttpResponsePermanentRedirect(articlee.get_absolute_url())
    
    update_case_view_times(request, article)
    
    
    return pagination.paginated(request, [], {
                                "article" : article,
                                "similar_questions" : article.get_related_questions(),
                                "embed_youtube_videos" : settings.EMBED_YOUTUBE_VIDEOS,
                                "meta" : {'description': article.title, 'keywords' : article.tagnames}
                                })

REVISION_TEMPLATE = template.loader.get_template('node/revision.html')

def revisions(request, id):
    post = get_object_or_404(Node, id=id).leaf
    revisions = list(post.revisions.order_by('revised_at'))
    rev_ctx = []

    for i, revision in enumerate(revisions):
        rev_ctx.append(dict(inst=revision, html=template.loader.get_template('node/revision.html').render(template.Context({
        'title': revision.title,
        'html': revision.html,
        'tags': revision.tagname_list(),
        }))))

        if i > 0:
            rev_ctx[i]['diff'] = mark_safe(htmldiff(rev_ctx[i-1]['html'], rev_ctx[i]['html']))
        else:
            rev_ctx[i]['diff'] = mark_safe(rev_ctx[i]['html'])

        if not (revision.summary):
            rev_ctx[i]['summary'] = _('Revision n. %(rev_number)d') % {'rev_number': revision.revision}
        else:
            rev_ctx[i]['summary'] = revision.summary

    rev_ctx.reverse()

    return render_to_response('revisions.html', {
    'post': post,
    'revisions': rev_ctx,
    }, context_instance=RequestContext(request))

def is_correct_key(k):
    return k == '17112008';


def get_questions(request, key):
    import json
    if is_correct_key(key):
        response = '['
        for q in Question.objects.all():
            response = response + '{' + '"id":' + str(q.id) + ', "title":"'+q.title+'", "body":"'+q.body+'", "type":"'+q.node_type+'"},'
        if response.endswith(','):
            response = response[:-1]
        response = response + ']'
        return HttpResponse(response)
    else:
        raise Http404
    return HttpResponse('Ok')

def get_terms(request, key):
    import json
    if is_correct_key(key):
        response = '['
        for q in Term.objects.all():
            response = response + '{' + '"id":' + str(q.id) + ', "title":"'+q.title+'", "body":"'+q.body+'", "type":"'+q.node_type+'"},'
        if response.endswith(','):
            response = response[:-1]
        response = response + ']'
        return HttpResponse(response)
    else:
        raise Http404
    return HttpResponse('Ok')


def similar(a, b):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def search_terms(request):
    import json
    if request.method == "GET" and "q" in request.GET:
        keywords = request.GET.get("q").strip()
        search_type = request.GET.get("t")
        _, terms = Term.objects.search(request.GET.get("q").strip())
        response = '['
        
        for q in terms:
            response = response + '{"title":"'+q.title+'", "body":"'+q.body+'", "similar":"'+str(similar(q.title,keywords))+'"},'
        if response.endswith(','):
                response = response[:-1]
        response = response + ']'
        return HttpResponse(response)
    return HttpResponse('Empty request')
