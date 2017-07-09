# encoding:utf-8
import os.path

import datetime

from django.core.urlresolvers import reverse
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.utils.html import *
from django.utils.translation import ugettext as _

from django.contrib import messages

from forum.actions import AskAction, AnswerAction, ReviseAction, RollbackAction, RetagAction, AnswerToQuestionAction, CommentToQuestionAction, AddCaseAction
from forum.forms import *
from forum.models import *
from forum.utils import html
from forum.http_responses import HttpResponseUnauthorized
import base64

from vars import PENDING_SUBMISSION_SESSION_ATTR

@csrf_exempt
def upload(request):#ajax upload file to a question or answer
    class FileTypeNotAllow(Exception):
        pass
    class FileSizeNotAllow(Exception):
        pass
    class UploadPermissionNotAuthorized(Exception):
        pass

    xml_template = "<result><msg><![CDATA[%s]]></msg><error><![CDATA[%s]]></error><file_url>%s</file_url></result>"

    try:
        f = request.FILES['file-upload']
        # check upload permission
        if not request.user.can_upload_files():
            raise UploadPermissionNotAuthorized()

        # check file type
        try:
            file_name_suffix = os.path.splitext(f.name)[1].lower()
        except KeyError:
            raise FileTypeNotAllow()

        if not file_name_suffix in ('.jpg', '.jpeg', '.gif', '.png', '.bmp', '.tiff', '.ico'):
            raise FileTypeNotAllow()

        storage = FileSystemStorage(str(settings.UPFILES_FOLDER), str(settings.UPFILES_ALIAS))
        new_file_name = storage.save("_".join(f.name.split()), f)
        # check file size
        # byte
        size = storage.size(new_file_name)

        if size > float(settings.ALLOW_MAX_FILE_SIZE) * 1024 * 1024:
            storage.delete(new_file_name)
            raise FileSizeNotAllow()

        result = xml_template % ('Good', '', str(settings.UPFILES_ALIAS) + new_file_name)
    except UploadPermissionNotAuthorized:
        result = xml_template % ('', _('uploading images is limited to users with >60 reputation points'), '')
    except FileTypeNotAllow:
        result = xml_template % ('', _("allowed file types are 'jpg', 'jpeg', 'gif', 'bmp', 'png', 'tiff'"), '')
    except FileSizeNotAllow:
        result = xml_template % ('', _("maximum upload file size is %sM") % settings.ALLOW_MAX_FILE_SIZE, '')
    except Exception, e:
        result = xml_template % ('', _('Error uploading file. Please contact the site administrator. Thank you. %s' % e), '')

    return HttpResponse(result, mimetype="application/xml")

def ask(request):
    form = None

    if request.POST:
        if request.session.pop('reviewing_pending_data', False):
            form = AskForm(initial=request.POST, user=request.user)
        elif "text" in request.POST:
            form = AskForm(request.POST, user=request.user)
            if form.is_valid():
                if request.user.is_authenticated() and request.user.email_valid_and_can_ask():
                    ask_action = AskAction(user=request.user, ip=request.META['REMOTE_ADDR']).save(data=form.cleaned_data)
                    question = ask_action.node

                    if settings.WIKI_ON and request.POST.get('wiki', False):
                        question.nstate.wiki = ask_action

                    return HttpResponseRedirect(question.get_absolute_url())
                else:
                    request.session[PENDING_SUBMISSION_SESSION_ATTR] = {
                        'POST': request.POST,
                        'data_name': _("question"),
                        'type': 'ask',
                        'submission_url': reverse('ask'),
                        'time': datetime.datetime.now()
                    }

                    if request.user.is_authenticated():
                        messages.info(request, _("Your question is pending until you %s.") % html.hyperlink(
                            django_settings.APP_URL + reverse('send_validation_email', prefix='/'), _("validate your email")
                        ))
                        return HttpResponseRedirect(reverse('index'))
                    else:
                        return HttpResponseRedirect(reverse('auth_signin'))
        elif "go" in request.POST:
            form = AskForm({'title': request.POST['q']}, user=request.user)
            
    if not form:
        form = AskForm(user=request.user)

    return render_to_response('ask.html', {
        'form' : form,
        'tab' : 'ask'
        }, context_instance=RequestContext(request))

def add_case(request):
    form = None
    
    if request.POST:
        if request.session.pop('reviewing_pending_data', False):
            form = AddCaseForm(initial=request.POST, user=request.user)
        elif "text" in request.POST:
            form = AddCaseForm(request.POST, user=request.user)
            if form.is_valid():
                if request.user.is_authenticated() and request.user.email_valid_and_can_ask():
                    add_case_action = AddCaseAction(user=request.user, ip=request.META['REMOTE_ADDR']).save(data=form.cleaned_data)
                    case = add_case_action.node
                    
                    return HttpResponseRedirect(case.get_absolute_url())
                else:
                    request.session[PENDING_SUBMISSION_SESSION_ATTR] = {
                        'POST': request.POST,
                        'data_name': _("case"),
                        'type': 'add_case',
                        'submission_url': reverse('add_case'),
                        'time': datetime.datetime.now()
                    }
                    
                    if request.user.is_authenticated():
                        messages.info(request, _("Your case study is pending until you %s.") % html.hyperlink(
                                                                                                              django_settings.APP_URL + reverse('send_validation_email', prefix='/'), _("validate your email")
                                                                                                            ))
                        return HttpResponseRedirect(reverse('index'))
                    else:
                        return HttpResponseRedirect(reverse('auth_signin'))
        elif "go" in request.POST:
            form = AddCaseForm({'title': request.POST['q']}, user=request.user)
    
    if not form:
        form = AddCaseForm(user=request.user)

    return render_to_response('add_case.html', {
            'form' : form,
            'tab' : 'add_case'
            }, context_instance=RequestContext(request))

def add_article(request):
    form = None
    
    if request.POST:
        if request.session.pop('reviewing_pending_data', False):
            form = AddArticleForm(initial=request.POST, user=request.user)
        elif "text" in request.POST:
            form = AddArticleForm(request.POST, user=request.user)
            if form.is_valid():
                if request.user.is_authenticated() and request.user.email_valid_and_can_ask():
                    add_article_action = AddArticleAction(user=request.user, ip=request.META['REMOTE_ADDR']).save(data=form.cleaned_data)
                    article = add_article_action.node
                    
                    return HttpResponseRedirect(article.get_absolute_url())
                else:
                    request.session[PENDING_SUBMISSION_SESSION_ATTR] = {
                        'POST': request.POST,
                        'data_name': _("case"),
                        'type': 'add_article',
                        'submission_url': reverse('add_article'),
                        'time': datetime.datetime.now()
                    }
                    
                    if request.user.is_authenticated():
                        messages.info(request, _("Your case study is pending until you %s.") % html.hyperlink(
                                                                                                              django_settings.APP_URL + reverse('send_validation_email', prefix='/'), _("validate your email")
                                                                                                              ))
                        return HttpResponseRedirect(reverse('index'))
                    else:
                        return HttpResponseRedirect(reverse('auth_signin'))
        elif "go" in request.POST:
                            form = AddArticleForm({'title': request.POST['q']}, user=request.user)
    
    if not form:
        form = AddArticleForm(user=request.user)

    return render_to_response('add_article.html', {
                          'form' : form,
                          'tab' : 'add_article'
                          }, context_instance=RequestContext(request))

def convert_to_question(request, id):
    user = request.user

    node_type = request.GET.get('node_type', 'answer')
    if node_type == 'comment':
        node = get_object_or_404(Comment, id=id)
        action_class = CommentToQuestionAction
    else:
        node = get_object_or_404(Answer, id=id)
        action_class = AnswerToQuestionAction

    if not user.can_convert_to_question(node):
        return HttpResponseUnauthorized(request)

    return _edit_question(request, node, template='node/convert_to_question.html', summary=_("Converted to question"),
                           action_class =action_class, allow_rollback=False, url_getter=lambda a: Question.objects.get(id=a.id).get_absolute_url())

def is_correct_key(k):
    return k == '17112008';

def add_book(request):
    if is_correct_key(request.POST['key']):
        Book.objects.create(title=request.POST['title'], url=request.POST['url'],parent=request.POST['parent'])
    else:
        raise Http404
    return HttpResponse('Ok')

def add_term(request):
    if is_correct_key(request.POST['key']):
        data = dict( body=request.POST['body'])
        data['title'] = strip_tags(request.POST['title'].strip())
        data['tagnames'] = request.POST['tagnames'].strip().lower()
        term = Term(author=User.objects.get(id=2), **data)
        term.body = request.POST['body']
        term.approved = True
        term.nis.approved = True
        term.save(handle_revision = False, handle_activity = False)
    else:
        raise Http404
    return HttpResponse('Ok')

def clean_terms(request, k):
    terms_to_delete=[]
    terms=Term.objects.all()
    if is_correct_key(k):
        for i in range(0,len(terms)-1):
            for j in range(i+1,len(terms)-1):
                if terms[i].title == terms[j].title and terms[i].body == terms[j].body:
                    terms_to_delete.append(terms[i].id)
                    print(str(terms[i].id) + " " + terms[i].title)
        t = set(terms_to_delete)
        for term in Term.objects.all():
            if term.id in t:
                term.delete()
    else:
        raise Http404
    return HttpResponse('Ok')

def clear_books(request, k):
    if is_correct_key(k):
        for item in Book.objects.all():
            item.delete()
    else:
        raise Http404
    return HttpResponse('Ok')

def edit_question(request, id):
    question = get_object_or_404(Question, id=id)
    if question.nis.deleted and not request.user.can_view_deleted_post(question):
        raise Http404
    if request.user.can_edit_post(question):
        return _edit_question(request, question)
    elif request.user.can_retag_questions():
        return _retag_question(request, question)
    else:
        raise Http404

def edit_case(request, id):
    case = get_object_or_404(Case, id=id)
    if case.nis.deleted and not request.user.can_view_deleted_post(case):
        raise Http404
    if request.user.can_edit_post(case):
        return _edit_case(request, case)
    elif request.user.can_retag_questions():
        return _retag_case(request, case)
    else:
        raise Http404

def _retag_question(request, question):
    if request.method == 'POST':
        form = RetagQuestionForm(question, request.POST)
        if form.is_valid():
            if form.has_changed():
                RetagAction(user=request.user, node=question, ip=request.META['REMOTE_ADDR']).save(data=dict(tagnames=form.cleaned_data['tags']))

            return HttpResponseRedirect(question.get_absolute_url())
    else:
        form = RetagQuestionForm(question)
    return render_to_response('question_retag.html', {
        'question': question,
        'form' : form,
        #'tags' : _get_tags_cache_json(),
    }, context_instance=RequestContext(request))

def _retag_case(request, case):
    if request.method == 'POST':
        form = RetagCaseForm(case, request.POST)
        if form.is_valid():
            if form.has_changed():
                RetagAction(user=request.user, node=case, ip=request.META['REMOTE_ADDR']).save(data=dict(tagnames=form.cleaned_data['tags']))
            
            return HttpResponseRedirect(case.get_absolute_url())
    else:
        form = RetagCaseForm(case)
    return render_to_response('case_retag.html', {
        'case': case,
        'form' : form,
        #'tags' : _get_tags_cache_json(),
        }, context_instance=RequestContext(request))

def _edit_question(request, question, template='question_edit.html', summary='', action_class=ReviseAction,
                   allow_rollback=True, url_getter=lambda q: q.get_absolute_url(), additional_context=None):
    if request.method == 'POST':
        revision_form = RevisionForm(question, data=request.POST)
        revision_form.is_valid()
        revision = question.revisions.get(revision=revision_form.cleaned_data['revision'])

        if 'select_revision' in request.POST:
            form = EditQuestionForm(question, request.user, revision)
        else:
            form = EditQuestionForm(question, request.user, revision, data=request.POST)

        if not 'select_revision' in request.POST and form.is_valid():
            if form.has_changed():
                action = action_class(user=request.user, node=question, ip=request.META['REMOTE_ADDR']).save(data=form.cleaned_data)

                if settings.WIKI_ON:
                    if request.POST.get('wiki', False) and not question.nis.wiki:
                        question.nstate.wiki = action
                    elif question.nis.wiki and (not request.POST.get('wiki', False)) and request.user.can_cancel_wiki(question):
                        question.nstate.wiki = None
            else:
                if not revision == question.active_revision:
                    if allow_rollback:
                        RollbackAction(user=request.user, node=question).save(data=dict(activate=revision))
                    else:
                        pass

            return HttpResponseRedirect(url_getter(question))
    else:
        revision_form = RevisionForm(question)
        form = EditQuestionForm(question, request.user, initial={'summary': summary})

    context = {
        'question': question,
        'revision_form': revision_form,
        'form' : form,
    }

    if not (additional_context is None):
        context.update(additional_context)

    return render_to_response(template, context, context_instance=RequestContext(request))

def _edit_case(request, case, template='case_edit.html', summary='', action_class=ReviseAction,
                   allow_rollback=True, url_getter=lambda q: q.get_absolute_url(), additional_context=None):
    if request.method == 'POST':
        revision_form = RevisionForm(case, data=request.POST)
        revision_form.is_valid()
        revision = case.revisions.get(revision=revision_form.cleaned_data['revision'])
        
        if 'select_revision' in request.POST:
            form = EditCaseForm(case, request.user, revision)
        else:
            form = EditCaseForm(case, request.user, revision, data=request.POST)
    
        if not 'select_revision' in request.POST and form.is_valid():
            if form.has_changed():
                action = action_class(user=request.user, node=case, ip=request.META['REMOTE_ADDR']).save(data=form.cleaned_data)
                

        else:
            if not revision == case.active_revision:
                if allow_rollback:
                    RollbackAction(user=request.user, node=case).save(data=dict(activate=revision))
                else:
                    pass
        
        return HttpResponseRedirect(url_getter(question))
    else:
        revision_form = RevisionForm(case)
        form = EditCaseForm(case, request.user, initial={'summary': summary})
    
    context = {
        'case': case,
        'revision_form': revision_form,
        'form' : form,
    }
    
    if not (additional_context is None):
        context.update(additional_context)
    
    return render_to_response(template, context, context_instance=RequestContext(request))

def _edit_article(request, article, template='case_article.html', summary='', action_class=ReviseAction,
               allow_rollback=True, url_getter=lambda q: q.get_absolute_url(), additional_context=None):
    if request.method == 'POST':
        revision_form = RevisionForm(case, data=request.POST)
        revision_form.is_valid()
        revision = article.revisions.get(revision=revision_form.cleaned_data['revision'])
        
        if 'select_revision' in request.POST:
            form = EditArticleForm(article, request.user, revision)
        else:
            form = EditArticleForm(case, request.user, revision, data=request.POST)
        
        if not 'select_revision' in request.POST and form.is_valid():
            if form.has_changed():
                action = action_class(user=request.user, node=case, ip=request.META['REMOTE_ADDR']).save(data=form.cleaned_data)
    
    
        else:
            if not revision == case.active_revision:
                if allow_rollback:
                    RollbackAction(user=request.user, node=case).save(data=dict(activate=revision))
                else:
                    pass

        return HttpResponseRedirect(url_getter(question))
    else:
        revision_form = RevisionForm(case)
        form = EditArticleForm(article, request.user, initial={'summary': summary})
    
    context = {
        'article': article,
        'revision_form': revision_form,
        'form' : form,
    }
    
    if not (additional_context is None):
        context.update(additional_context)

    return render_to_response(template, context, context_instance=RequestContext(request))

def edit_answer(request, id):
    answer = get_object_or_404(Answer, id=id)
    if answer.deleted and not request.user.can_view_deleted_post(answer):
        raise Http404
    elif not request.user.can_edit_post(answer):
        raise Http404

    if request.method == "POST":
        revision_form = RevisionForm(answer, data=request.POST)
        revision_form.is_valid()
        revision = answer.revisions.get(revision=revision_form.cleaned_data['revision'])

        if 'select_revision' in request.POST:
            form = EditAnswerForm(answer, request.user, revision)
        else:
            form = EditAnswerForm(answer, request.user, revision, data=request.POST)

        if not 'select_revision' in request.POST and form.is_valid():
            if form.has_changed():
                action = ReviseAction(user=request.user, node=answer, ip=request.META['REMOTE_ADDR']).save(data=form.cleaned_data)

                if settings.WIKI_ON:
                    if request.POST.get('wiki', False) and not answer.nis.wiki:
                        answer.nstate.wiki = action
                    elif answer.nis.wiki and (not request.POST.get('wiki', False)) and request.user.can_cancel_wiki(answer):
                        answer.nstate.wiki = None
            else:
                if not revision == answer.active_revision:
                    RollbackAction(user=request.user, node=answer, ip=request.META['REMOTE_ADDR']).save(data=dict(activate=revision))

            return HttpResponseRedirect(answer.get_absolute_url())

    else:
        revision_form = RevisionForm(answer)
        form = EditAnswerForm(answer, request.user)
    return render_to_response('answer_edit.html', {
                              'answer': answer,
                              'revision_form': revision_form,
                              'form': form,
                              }, context_instance=RequestContext(request))

def answer(request, id):
    question = get_object_or_404(Question, id=id)

    if request.POST:
        form = AnswerForm(request.POST, request.user)

        if request.session.pop('reviewing_pending_data', False) or not form.is_valid():
            request.session['redirect_POST_data'] = request.POST
            return HttpResponseRedirect(question.get_absolute_url() + '#fmanswer')

        if request.user.is_authenticated() and request.user.email_valid_and_can_answer():
            answer_action = AnswerAction(user=request.user, ip=request.META['REMOTE_ADDR']).save(dict(question=question, **form.cleaned_data))
            answer = answer_action.node

            if settings.WIKI_ON and request.POST.get('wiki', False):
                answer.nstate.wiki = answer_action

            return HttpResponseRedirect(answer.get_absolute_url())
        else:
            request.session[PENDING_SUBMISSION_SESSION_ATTR] = {
                'POST': request.POST,
                'data_name': _("answer"),
                'type': 'answer',
                'submission_url': reverse('answer', kwargs={'id': id}),
                'time': datetime.datetime.now()
            }

            if request.user.is_authenticated():
                messages.info(request, _("Your answer is pending until you %s.") % html.hyperlink(
                    django_settings.APP_URL + reverse('send_validation_email', prefix='/'), _("validate your email")
                ))
                return HttpResponseRedirect(question.get_absolute_url())
            else:
                return HttpResponseRedirect(reverse('auth_signin'))

    return HttpResponseRedirect(question.get_absolute_url())


def manage_pending_data(request, action, forward=None):
    pending_data = request.session.pop(PENDING_SUBMISSION_SESSION_ATTR, None)

    if not pending_data:
        raise Http404

    if action == _("cancel"):
        return HttpResponseRedirect(forward or request.META.get('HTTP_REFERER', '/'))
    else:
        if action == _("review"):
            request.session['reviewing_pending_data'] = True

        request.session['redirect_POST_data'] = pending_data['POST']
        return HttpResponseRedirect(pending_data['submission_url'])


