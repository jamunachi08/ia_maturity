"""Audited bilingual public-site content and ordered role approvals."""
import json
import re
from pathlib import Path
import frappe
from frappe import _
from frappe.utils import now_datetime, cint
from ia_maturity.grc import security as sec

CATALOGUE = Path(__file__).resolve().parents[2] / 'grc' / 'src' / 'site-content-defaults.json'
LEGAL_KEYS = {'legal.privacy', 'legal.terms'}


def defaults():
    return json.loads(CATALOGUE.read_text(encoding='utf-8'))


def parse(raw, fallback):
    try:
        return json.loads(raw) if raw else fallback
    except (ValueError, TypeError):
        frappe.throw(_('Site content is invalid. Contact the platform administrator.'))


def config():
    return frappe.get_single('GRC Site Content')


def initialize():
    """Seed once, preserving the already published legacy legal notices."""
    existing = frappe.db.exists('Singles', {'doctype':'GRC Site Content','field':'editor_roles'})
    if existing:
        return
    settings = frappe.get_single('GRC Settings')
    initial = {key: {'en':settings.get(prefix+'_en') or '', 'ar':settings.get(prefix+'_ar') or ''}
               for key, prefix in [('legal.privacy','privacy'),('legal.terms','terms')]}
    frappe.db.set_single_value('GRC Site Content', {'published_content':json.dumps(initial,ensure_ascii=False),
        'editor_roles':json.dumps(['GRC App Admin']), 'approval_roles':json.dumps(['GRC App Admin'])})


def lock():
    frappe.db.sql('select value from `tabSingles` where doctype=%s and field=%s for update', ('GRC Site Content','editor_roles'))


def published():
    if not sec.enabled() or not frappe.db.exists('DocType','GRC Site Content'):
        return {}
    raw = frappe.db.get_single_value('GRC Site Content','published_content')
    return parse(raw,{})


def published_snapshot():
    base = {key: {'en':item['en'], 'ar':item['ar']} for key,item in defaults().items()}
    base.update({'legal.privacy':{'en':'','ar':''}, 'legal.terms':{'en':'','ar':''}})
    base.update({key:value for key,value in published().items() if key in base or key=='__layout' or re.fullmatch(r'custom\.[a-z0-9-]{1,50}\.(title|body)',key)})
    return base


def editors():
    return parse(frappe.db.get_single_value('GRC Site Content','editor_roles'),['GRC App Admin'])


def workflow():
    return parse(frappe.db.get_single_value('GRC Site Content','approval_roles'),['GRC App Admin'])


def can_edit():
    return bool(sec.is_admin() or sec.roles() & set(editors())) if frappe.session.user != 'Guest' else False


def can_access():
    if frappe.session.user == 'Guest':
        return False
    if can_edit() or bool(sec.roles() & set(workflow())):
        return True
    # A pending revision retains its submitted workflow even if settings change.
    if frappe.db.exists('DocType','GRC Site Revision'):
        for row in frappe.get_all('GRC Site Revision', filters={'status':'Pending'}, fields=['workflow','step']):
            stages=parse(row.workflow,[])
            if (row.step or 0)<len(stages) and stages[row.step or 0] in sec.roles():
                return True
    return False


def require_access():
    sec.require_login()
    if not can_access():
        sec.deny()


def require_editor():
    sec.require_login()
    if not can_edit():
        sec.deny()


def guard_document(doc, method=None):
    if sec.enabled() and not (frappe.flags.get('grc_site_service') or frappe.flags.get('in_migrate') or frappe.flags.get('in_install')):
        sec.deny()


def guard_delete(doc, method=None):
    if sec.enabled() and not (frappe.flags.get('in_migrate') or frappe.flags.get('in_install')):
        sec.deny()


from contextlib import contextmanager
@contextmanager
def service_write():
    previous=frappe.flags.get('grc_site_service')
    frappe.flags.grc_site_service=True
    try:
        yield
    finally:
        frappe.flags.grc_site_service=previous


def event(action, revision=None, details=None):
    with service_write():
        frappe.get_doc({'doctype':'GRC Site Event','revision':revision,'actor':frappe.session.user,
            'action':action,'details':frappe.as_json(details or {})}).insert(ignore_permissions=True)


def validate_content(value):
    if isinstance(value,str):
        value=parse(value,None)
    allowed=set(defaults()) | LEGAL_KEYS
    if not isinstance(value,dict) or not allowed.issubset(value) or len(value)>1000 or any(key not in allowed and key!='__layout' and not re.fullmatch(r'custom\.[a-z0-9-]{1,50}\.(title|body)',key) for key in value):
        frappe.throw(_('The site content catalogue changed or is incomplete. Reload before saving.'))
    for key, item in value.items():
        if not isinstance(item,dict) or set(item)!={'en','ar'} or any(not isinstance(item[lang],str) or len(item[lang])>12000 for lang in ('en','ar')):
            frappe.throw(_('Each content item must contain English and Arabic text.'))
    validate_layout(value)
    if len(json.dumps(value,ensure_ascii=False))>1000000:
        frappe.throw(_('Site content is too large.'))
    return value


def validate_layout(content):
    if '__layout' not in content:
        return
    if content['__layout']['en'] != content['__layout']['ar']:
        frappe.throw(_('Layout must be shared between both languages.'))
    layout=parse(content['__layout']['en'],None)
    if not isinstance(layout,dict) or set(layout)!={'hidden','removedCards','cards','sections'}:
        frappe.throw(_('Invalid site layout.'))
    pages={'home','services','catalogue','frameworks','about','resources','faq','contact','privacy','terms'}
    containers={p+'.main' for p in ('services','catalogue','frameworks','about','resources','faq')} | {'home.hero','home.facts','home.journey','home.assurance','home.readiness'}
    count=0
    all_ids=set()
    def card(item):
        nonlocal count
        count+=1
        if count>250 or not isinstance(item,dict) or not {'id','title','body'}.issubset(item) or not isinstance(item['id'],str) or not re.fullmatch(r'[a-z0-9-]{1,50}',item['id']):
            frappe.throw(_('Invalid card or section.'))
        if item['id'] in all_ids:frappe.throw(_('Duplicate content block identifier.'))
        all_ids.add(item['id'])
        for field in ('title','body'):
            if not isinstance(item[field],str) or not item[field].startswith('custom.') or item[field] not in content:
                frappe.throw(_('Card text is missing.'))
    if not isinstance(layout['sections'],dict) or not isinstance(layout['cards'],dict) or not isinstance(layout['removedCards'],dict) or not isinstance(layout['hidden'],list):
        frappe.throw(_('Invalid site layout.'))
    ids=set()
    for page,sections in layout['sections'].items():
        if page not in pages or not isinstance(sections,list) or len(sections)>30:
            frappe.throw(_('Invalid page sections.'))
        for section in sections:
            card(section)
            if set(section)!={'id','title','body','cards'} or section['id'] in ids or not isinstance(section['cards'],list):
                frappe.throw(_('Invalid section.'))
            ids.add(section['id']);containers.add(section['id'])
            for item in section['cards']:
                card(item)
                if set(item)!={'id','title','body'}:frappe.throw(_('Invalid card.'))
    for container,cards in layout['cards'].items():
        if container not in containers or not isinstance(cards,list):frappe.throw(_('Invalid card container.'))
        for item in cards:
            card(item)
            if set(item)!={'id','title','body'}:frappe.throw(_('Invalid card.'))
    if any(not isinstance(x,str) or x not in containers for x in layout['hidden']):frappe.throw(_('Invalid hidden section.'))
    for container,indices in layout['removedCards'].items():
        if container not in containers or not isinstance(indices,list) or len(indices)>100 or any(type(i)!=int or not 0<=i<100 for i in indices):
            frappe.throw(_('Invalid removed cards.'))


def get_revision(name, for_update=False):
    if for_update:
        frappe.db.sql('select name from `tabGRC Site Revision` where name=%s for update',name)
    return frappe.get_doc('GRC Site Revision',name)


def revision_data(doc):
    return {'name':doc.name,'status':doc.status,'content':parse(doc.content,{}),'base_revision':doc.base_revision,
        'workflow':parse(doc.workflow,[]),'step':doc.step or 0,'submitted_by':doc.submitted_by,
        'submitted_on':doc.submitted_on,'allow_submitter_approval':bool(doc.allow_submitter_approval),'published_by':doc.published_by,'published_on':doc.published_on,'modified':str(doc.modified)}


@frappe.whitelist()
def site_content_state(revision_page=1, event_page=1):
    require_access()
    revision_page=max(1,cint(revision_page));event_page=max(1,cint(event_page));size=50
    revisions=frappe.get_all('GRC Site Revision',fields=['name','status','owner','creation','modified','submitted_by','step','published_by','published_on'],order_by='creation desc',limit_start=(revision_page-1)*size,limit_page_length=size+1)
    draft=frappe.db.get_value('GRC Site Revision',{'status':'Draft'},'name',order_by='creation desc')
    events=frappe.get_all('GRC Site Event',fields=['name','revision','actor','action','details','creation'],order_by='creation desc',limit_start=(event_page-1)*size,limit_page_length=size+1)
    return {'revision_page':revision_page,'event_page':event_page,'revisions_more':len(revisions)>size,'events_more':len(events)>size,'can_edit':can_edit(),'is_admin':sec.is_admin(),'roles':sorted(sec.roles()),
        'editor_roles':editors(),'approval_roles':workflow(),'allow_submitter_approval':bool(cint(frappe.db.get_single_value('GRC Site Content','allow_submitter_approval'))),'available_roles':available_roles() if sec.is_admin() else [],
        'published':published(),'published_revision':frappe.db.get_single_value('GRC Site Content','published_revision'),
        'draft':revision_data(get_revision(draft)) if draft else None,'revisions':revisions[:size],'events':events[:size]}


@frappe.whitelist()
def site_content_revision(name):
    require_access()
    return revision_data(get_revision(name))


def available_roles():
    return [r for r in frappe.get_all('Role',filters={'disabled':0},pluck='name',order_by='name') if r not in {'All','Guest'}]


@frappe.whitelist(methods=['POST'])
def site_content_configure(editor_roles, approval_roles, allow_submitter_approval=0):
    sec.require_admin()
    editor_roles=parse(editor_roles,[]) if isinstance(editor_roles,str) else editor_roles
    approval_roles=parse(approval_roles,[]) if isinstance(approval_roles,str) else approval_roles
    valid_roles=set(available_roles())
    if not isinstance(editor_roles,list) or not isinstance(approval_roles,list) or not approval_roles or len(approval_roles)>10 or any(not isinstance(r,str) or r not in valid_roles for r in editor_roles+approval_roles):
        frappe.throw(_('Select valid active roles and at least one approval role.'))
    if len(set(editor_roles))!=len(editor_roles):
        frappe.throw(_('Editor roles must be unique.'))
    lock();before={'editor_roles':editors(),'approval_roles':workflow(),'allow_submitter_approval':bool(cint(frappe.db.get_single_value('GRC Site Content','allow_submitter_approval')))}
    frappe.db.set_single_value('GRC Site Content',{'editor_roles':json.dumps(editor_roles),'approval_roles':json.dumps(approval_roles),'allow_submitter_approval':int(bool(cint(allow_submitter_approval)))})
    event('Workflow configured',details={'before':before,'after':{'editor_roles':editor_roles,'approval_roles':approval_roles,'allow_submitter_approval':bool(cint(allow_submitter_approval))}})
    return {'ok':True}


@frappe.whitelist(methods=['POST'])
def site_content_save(content, name=None, modified=None):
    require_editor();value=validate_content(content);lock()
    existing=frappe.db.get_value('GRC Site Revision',{'status':'Draft'},'name',order_by='creation desc')
    if existing:
        if name != existing:
            frappe.throw(_('Another draft exists. Reload before editing.'))
        doc=get_revision(existing,True)
        if not modified or str(doc.modified)!=modified:
            frappe.throw(_('This draft was changed by another user. Reload before saving.'))
        before=parse(doc.content,{})
    else:
        if name:
            frappe.throw(_('The draft is no longer editable. Reload.'))
        doc=frappe.new_doc('GRC Site Revision');doc.status='Draft'
        doc.base_revision=frappe.db.get_single_value('GRC Site Content','published_revision');before=published_snapshot()
    changes={key:{'before':before.get(key),'after':value.get(key)} for key in set(before)|set(value) if before.get(key)!=value.get(key)}
    if not changes and existing:
        return revision_data(doc)
    doc.content=json.dumps(value,ensure_ascii=False,sort_keys=True)
    with service_write():doc.save(ignore_permissions=True)
    event('Draft saved',doc.name,{'changes':changes})
    return revision_data(doc)


@frappe.whitelist(methods=['POST'])
def site_content_submit(name, modified):
    require_editor();lock();doc=get_revision(name,True)
    if doc.status!='Draft' or str(doc.modified)!=modified:
        frappe.throw(_('This draft is no longer current. Reload.'))
    if (doc.base_revision or '') != (frappe.db.get_single_value('GRC Site Content','published_revision') or ''):
        frappe.throw(_('The live site changed since this draft started. Create a fresh draft.'))
    stages=workflow()
    if not stages:
        frappe.throw(_('Configure at least one approval role before submission.'))
    doc.workflow=json.dumps(stages);doc.allow_submitter_approval=cint(frappe.db.get_single_value('GRC Site Content','allow_submitter_approval'));doc.step=0;doc.status='Pending';doc.submitted_by=frappe.session.user;doc.submitted_on=now_datetime()
    with service_write():doc.save(ignore_permissions=True)
    event('Submitted',doc.name,{'workflow':stages,'allow_submitter_approval':bool(doc.allow_submitter_approval)})
    return revision_data(doc)


@frappe.whitelist(methods=['POST'])
def site_content_decide(name, decision, comment=''):
    require_access()
    if decision not in {'Approve','Reject'} or len(comment or '')>2000:
        frappe.throw(_('Choose a valid decision and comment.'))
    if decision=='Reject' and not (comment or '').strip():
        frappe.throw(_('Enter a reason for rejection.'))
    lock();doc=get_revision(name,True);stages=parse(doc.workflow,[]);index=doc.step or 0
    if doc.status!='Pending' or index>=len(stages):
        frappe.throw(_('This revision is no longer awaiting approval.'))
    if doc.submitted_by==frappe.session.user and not doc.allow_submitter_approval:
        frappe.throw(_('The submitter cannot approve or reject their own submission.'))
    if stages[index] not in sec.roles():
        sec.deny()
    if decision == 'Approve' and (doc.base_revision or '') != (frappe.db.get_single_value('GRC Site Content','published_revision') or ''):
        frappe.throw(_('The live site has changed. Reject this revision and submit a new draft.'))
    details={'decision':decision,'role':stages[index],'step':index+1,'comment':(comment or '').strip()}
    if decision=='Reject':doc.status='Rejected'
    else:
        doc.step=index+1
        if doc.step==len(stages):
            doc.status='Published';doc.published_by=frappe.session.user;doc.published_on=now_datetime()
            frappe.db.set_single_value('GRC Site Content',{'published_content':doc.content,'published_revision':doc.name})
    with service_write():doc.save(ignore_permissions=True)
    event('Decision',doc.name,details)
    if doc.status=='Published':event('Published',doc.name,{'base_revision':doc.base_revision})
    return revision_data(doc)


@frappe.whitelist(methods=['POST'])
def site_content_discard(name, modified):
    require_editor();lock();doc=get_revision(name,True)
    if doc.status!='Draft' or str(doc.modified)!=modified:
        frappe.throw(_('This draft is no longer current. Reload.'))
    doc.status='Discarded'
    with service_write():doc.save(ignore_permissions=True)
    event('Draft discarded',doc.name)
    return {'ok':True}


@frappe.whitelist(methods=['POST'])
def site_content_cancel(name, comment):
    sec.require_admin()
    if not isinstance(comment,str) or not comment.strip() or len(comment)>2000:
        frappe.throw(_('Enter a reason for cancelling the submission.'))
    lock();doc=get_revision(name,True)
    if doc.status!='Pending':
        frappe.throw(_('This revision is no longer awaiting approval.'))
    doc.status='Rejected'
    with service_write():doc.save(ignore_permissions=True)
    event('Submission cancelled',doc.name,{'reason':comment.strip(),'workflow':parse(doc.workflow,[]),'step':doc.step})
    return revision_data(doc)
