"""Scoped customer/staff oversight and approval of onboarding and allocations."""
import json
from contextlib import contextmanager
import frappe
from frappe import _
from frappe.utils import cint,now_datetime
from ia_maturity.grc import security as sec
KINDS={'Auditor Customer Invitation','Invited Customer Onboarding','Customer Onboarding','Auditor Onboarding','Customer Assignment','Assessment Assignment','Customer Invitation','Customer Membership'}
DEFAULT={'onboarding':False,'assignments':False,'stages':['GRC App Admin'],'allow_self':False}


def managed():
    sec.require_login()
    if sec.is_admin():return sec.entities()
    if sec.account_type()!='Auditor':sec.deny()
    return [e for e in sec.entities() if sec.is_organization_manager(e)]


def require_manager(entity=None):
    scope=managed()
    if not sec.is_admin() and (entity not in scope if entity else not scope):sec.deny()
    return scope


def policies():
    if not frappe.db.exists('DocType','GRC Operations Policy'):return {}
    return frappe.parse_json(frappe.db.get_single_value('GRC Operations Policy','policies') or '{}')


def policy(entity=None):
    values=policies();return {**DEFAULT,**values.get('*',{}),**values.get(entity or '',{})}


def guard(doc,method=None):
    if sec.enabled() and not (frappe.flags.get('grc_operations_service') or frappe.flags.get('in_migrate') or frappe.flags.get('in_install')):sec.deny()


def no_delete(doc,method=None):
    if sec.enabled() and not frappe.flags.get('in_uninstall'):sec.deny()


@contextmanager
def writing(apply=False):
    old=frappe.flags.get('grc_operations_service');old_apply=frappe.flags.get('grc_operations_apply')
    frappe.flags.grc_operations_service=True
    if apply:frappe.flags.grc_operations_apply=True
    try:yield
    finally:frappe.flags.grc_operations_service=old;frappe.flags.grc_operations_apply=old_apply


def maybe_queue(kind,payload,entity=None,actor=None):
    if frappe.flags.get('grc_operations_apply') or not sec.enabled() or not frappe.db.exists('DocType','GRC Operations Request'):return None
    config=policy(entity)
    if not config['onboarding' if 'Onboarding' in kind or kind in {'Customer Invitation','Auditor Customer Invitation'} else 'assignments']:return None
    if kind not in KINDS:sec.deny()
    frappe.db.sql('select value from tabSingles where doctype=%s and field=%s for update',('GRC Settings','results_visibility'))
    actor=actor or frappe.session.user
    if actor=='Guest':sec.deny()
    text=frappe.as_json(payload)
    existing=frappe.db.get_value('GRC Operations Request',{'status':'Pending','kind':kind,'entity':entity or '', 'requested_by':actor,'payload':text},'name')
    if existing:return {'name':existing,'pending_approval':True}
    with writing():
        doc=frappe.get_doc({'doctype':'GRC Operations Request','kind':kind,'entity':entity,'status':'Pending','payload':text,'workflow':frappe.as_json(config),'requested_by':actor,'step':0,'decisions':'[]'}).insert(ignore_permissions=True)
    sec.log('Operational approval requested',entity,details={'request':doc.name,'kind':kind,'requested_by':actor})
    return {'name':doc.name,'pending_approval':True}


def pending_onboarding(user=None):
    if not frappe.db.exists('DocType','GRC Operations Request'):return []
    return frappe.get_all('GRC Operations Request',filters={'requested_by':user or frappe.session.user,'kind':'Customer Onboarding','status':'Pending'},fields=['name','kind','creation'])



@frappe.whitelist(methods=['POST'])
def operations_onboard_auditor(entity,email,full_name,role='GRC Auditor'):
    require_manager(entity)
    if role not in {'GRC Auditor','GRC Consultant','GRC Reviewer'}:sec.deny()
    from ia_maturity.grc.identity import validate_name
    from frappe.utils import validate_email_address
    email=email.strip().lower();validate_name(full_name.strip(),required=True)
    if not validate_email_address(email) or frappe.db.exists('User',email):frappe.throw(_('Enter a valid email for a new staff account.'))
    payload={'email':email,'full_name':full_name.strip(),'role':role,'enabled':1}
    # Manager requests always require approval, even if general onboarding is disabled.
    config=policy(entity);config['onboarding']=True
    with writing():
        doc=frappe.get_doc({'doctype':'GRC Operations Request','kind':'Auditor Onboarding','entity':entity,'status':'Pending','payload':frappe.as_json(payload),'workflow':frappe.as_json(config),'requested_by':frappe.session.user,'step':0,'decisions':'[]'}).insert(ignore_permissions=True)
    sec.log('Operational approval requested',entity,details={'request':doc.name,'kind':doc.kind})
    return {'name':doc.name,'pending_approval':True}

@frappe.whitelist(methods=['POST'])
def operations_configure(config,entity=None):
    require_manager(entity)
    if not entity and not sec.is_admin():sec.deny()
    value=frappe.parse_json(config) if isinstance(config,str) else config
    if not isinstance(value,dict) or set(value)!=set(DEFAULT) or not isinstance(value['stages'],list) or not 1<=len(value['stages'])<=5 or any(r not in {'GRC Manager','GRC App Admin'} for r in value['stages']):frappe.throw(_('Choose a valid operations workflow.'))
    if not entity and 'GRC Manager' in value['stages']:frappe.throw(_('Unassigned onboarding requires an app administrator approval step. Use manager stages in a customer-specific workflow.'))
    for k in ('onboarding','assignments','allow_self'):value[k]=bool(cint(value[k]))
    # Serialize policy writes using an existing singleton row.
    frappe.db.sql('select value from `tabSingles` where doctype=%s and field=%s for update',('GRC Settings','results_visibility'))
    values=policies();before=values.get(entity or '*',{});values[entity or '*']=value
    frappe.db.set_single_value('GRC Operations Policy','policies',json.dumps(values))
    sec.log('Operations workflow configured',entity,details={'before':before,'after':value})
    return {'ok':True}


def visible_request(doc):
    require_manager()
    if sec.is_admin():return
    if doc.kind in {'Auditor Customer Invitation','Invited Customer Onboarding'}:sec.deny()
    if not department_request_allowed(doc):sec.deny()
    if not doc.entity:
        if doc.requested_by!=frappe.session.user:sec.deny()
        return
    require_manager(doc.entity)
    if doc.kind=='Auditor Onboarding' and frappe.parse_json(doc.payload).get('role') not in {'GRC Auditor','GRC Consultant','GRC Reviewer'}:sec.deny()


def department_request_allowed(doc):
    if sec.is_admin():return True
    from ia_maturity.grc import departments as dept
    payload=frappe.parse_json(doc.payload or '{}')
    if sec.account_type(doc.requested_by)=='Auditor' and not (dept.staff_types(doc.requested_by)&dept.staff_types()):return False
    if doc.kind=='Assessment Assignment' and payload.get('name'):
        return dept.can_read(frappe.get_doc('GRC Assessment Assignment',payload['name']))
    if doc.kind=='Customer Assignment' and payload.get('auditor'):
        return bool(dept.staff_types(payload['auditor'])&dept.staff_types())
    return True


def apply_request(doc):
    from ia_maturity.grc.administration import save_staff,assign_customer,assign_assessment
    from ia_maturity.grc.organizations import save_organization,invite_member,update_membership
    payload=frappe.parse_json(doc.payload)
    if doc.kind in {'Auditor Customer Invitation', 'Invited Customer Onboarding'}:
        from ia_maturity.grc.onboarding import apply_approval
        return apply_approval(doc)
    if not frappe.db.get_value('User',doc.requested_by,'enabled'):frappe.throw(_('The requesting account is no longer active.'))
    actor=frappe.session.user
    try:
        frappe.set_user('Administrator')
        with writing(True):
            if doc.kind=='Customer Onboarding':
                result=save_organization(payload['data'])
                requester=doc.requested_by
                if sec.account_type(requester)=='Customer':
                    with sec.service_write():frappe.get_doc({'doctype':'GRC Organization Membership','entity':result['name'],'user':requester,'membership_role':'Organization Admin','active':1}).insert(ignore_permissions=True)
                elif sec.account_type(requester)=='Auditor':
                    # Mirror direct creation: the new customer joins the requester's single department.
                    from ia_maturity.grc.departments import grant, staff_types
                    if not sec.is_admin(requester):
                        departments=staff_types(requester)
                        if len(departments)!=1:frappe.throw(_('Create the customer through a department invitation.'))
                        grant(result['name'],next(iter(departments)),'Approved customer onboarding')
                    assign_customer(result['name'],requester,'Manager' if sec.roles(requester)&{'GRC Manager','IA Maturity Manager'} else 'Consultant')
                return {'name':result['name']}
            if doc.kind=='Auditor Onboarding':
                if frappe.db.exists('User',payload['email']):frappe.throw(_('This account already exists. Submit a new request for the current account.'))
                responsibility='Reviewer' if payload['role']=='GRC Reviewer' else 'Consultant'
                shared=set()
                if doc.entity:
                    # Since v3.0 assignment needs a shared department: the new staff member joins only
                    # the departments the requesting manager shares with this customer.
                    from ia_maturity.grc.departments import entity_types, staff_types
                    shared=staff_types(doc.requested_by)&entity_types(doc.entity)
                    if not shared:frappe.throw(_('The requesting manager no longer shares a department with this customer.'))
                result=save_staff(**payload)
                if doc.entity:
                    from ia_maturity.grc.departments import save_department_staff
                    for department in sorted(shared):save_department_staff(result['name'],department,responsibility)
                    assign_customer(doc.entity,result['name'],responsibility)
                return result
            if doc.kind=='Customer Assignment':
                expected=payload.pop('_before',None)
                current=frappe.db.get_value('Auditor Customer Assignment',{'entity':payload['entity'],'auditor':payload['auditor'],'responsibility':payload['responsibility']},['name','active'],as_dict=True)
                if (dict(current) if current else None)!=expected:frappe.throw(_('The customer assignment changed after submission. Submit a new request.'))
                return assign_customer(**payload)
            if doc.kind=='Customer Invitation':
                return invite_member(**payload)
            if doc.kind=='Customer Membership':
                expected=payload.pop('_before')
                current=frappe.db.get_value('GRC Organization Membership',payload['name'],['membership_role','active'],as_dict=True)
                if dict(current or {})!=expected:frappe.throw(_('The membership changed after submission. Submit a new request.'))
                return update_membership(**payload)
            if doc.kind=='Assessment Assignment':
                expected=payload.pop('_before',{})
                current=frappe.db.get_value('GRC Assessment Assignment',payload['name'],list(expected),as_dict=True)
                if not current or any((str(current.get(k) or '') != str(v or '')) for k,v in expected.items()):frappe.throw(_('The allocation changed after this request. Reject it and submit a new request.'))
                return assign_assessment(**payload)
    finally:frappe.set_user(actor)


@frappe.whitelist(methods=['POST'])
def operations_decide(name,decision,comment=''):
    require_manager()
    if decision not in {'Approve','Reject','Cancel'} or not isinstance(comment,str) or len(comment)>2000:frappe.throw(_('Choose a valid decision.'))
    frappe.db.sql('select name from `tabGRC Operations Request` where name=%s for update',name)
    doc=frappe.get_doc('GRC Operations Request',name);visible_request(doc)
    if doc.status!='Pending':frappe.throw(_('This request is no longer pending.'))
    config=frappe.parse_json(doc.workflow);stage=(config['stages'])[doc.step or 0]
    if decision=='Cancel':
        if not sec.is_admin() and doc.requested_by!=frappe.session.user:sec.deny()
    else:
        if doc.requested_by==frappe.session.user and not config.get('allow_self'):frappe.throw(_('A different authorized reviewer must decide this request.'))
        if stage=='GRC App Admin' and not sec.is_admin():sec.deny()
        if stage=='GRC Manager' and not (sec.is_admin() or sec.is_organization_manager(doc.entity)):sec.deny()
    if decision!='Approve' and not comment.strip():frappe.throw(_('Enter a decision reason.'))
    decisions=frappe.parse_json(doc.decisions or '[]');decisions.append({'actor':frappe.session.user,'decision':decision,'stage':stage,'time':str(now_datetime()),'comment':comment.strip()})
    if decision=='Approve':
        doc.step=(doc.step or 0)+1
        if doc.step==len(config['stages']):
            result=apply_request(doc);doc.result=frappe.as_json(result);doc.status='Approved'
            if doc.kind=='Customer Onboarding':doc.entity=result['name']
    else:
        doc.status='Rejected' if decision=='Reject' else 'Cancelled'
        from ia_maturity.grc.onboarding import approval_rejected
        approval_rejected(doc)
    doc.decisions=frappe.as_json(decisions);doc.decision_by=frappe.session.user;doc.decision_on=now_datetime()
    with writing():doc.save(ignore_permissions=True)
    sec.log('Operational approval decision',doc.entity,details={'request':doc.name,'kind':doc.kind,'decision':decision,'status':doc.status,'comment':comment.strip()})
    return {'name':doc.name,'status':doc.status}


@frappe.whitelist()
def operations_overview():
    scope=managed()
    from ia_maturity.grc import departments as dept
    # An active department manager may have no customer assignments yet. The
    # overview can explain that empty state; all record actions stay scoped.
    if not sec.is_admin() and not scope and not any(dept.manager(d) for d in dept.types()):
        sec.deny()
    entities=frappe.get_all('IA Maturity Entity',filters={'name':['in',scope or ['__none__']]},fields=['name','entity_name','sector','contact_email','is_active','grc_ownership_locked'],order_by='entity_name')
    for entity in entities:
        entity['ownership_locked']=bool(entity.pop('grc_ownership_locked',0))
    assignments=frappe.get_all('Auditor Customer Assignment',filters={'entity':['in',scope or ['__none__']],'active':1},fields=['name','entity','auditor','responsibility'])
    if not sec.is_admin():assignments=[a for a in assignments if dept.staff_types(a.auditor)&dept.staff_types()]
    staff_ids=sorted({a.auditor for a in assignments})
    if sec.is_admin():staff_ids=frappe.get_all('User',filters={'grc_account_type':'Auditor'},pluck='name')
    people=[]
    from ia_maturity.grc.identity import display_name
    for user in staff_ids:
        record=frappe.db.get_value('User',user,['name','enabled','mobile_no','language','creation','last_login'],as_dict=True)
        if record:record['full_name']=display_name(user);record['roles']=sorted(sec.roles(user)&sec.AUDITOR_ROLES);people.append(record)
    filters={} if sec.is_admin() else {'entity':['in',scope or ['__none__']]}
    requests=frappe.get_all('GRC Operations Request',filters=filters,fields=['name','kind','entity','status','payload','workflow','step','requested_by','creation','decisions','result'],order_by='creation desc',limit_page_length=0)
    if not sec.is_admin():
        own=frappe.get_all('GRC Operations Request',filters={'requested_by':frappe.session.user},fields=['name','kind','entity','status','payload','workflow','step','requested_by','creation','decisions','result'],order_by='creation desc',limit_page_length=0)
        requests+= [r for r in own if not r.entity]
    if not sec.is_admin():requests=[r for r in requests if r.kind not in {'Auditor Customer Invitation','Invited Customer Onboarding'} and department_request_allowed(r)]
    for row in requests:row.payload=frappe.parse_json(row.payload);row.workflow=frappe.parse_json(row.workflow);row.decisions=frappe.parse_json(row.decisions or '[]')
    return {'customers':entities,'auditors':people,'assignments':assignments,'requests':requests,'is_admin':sec.is_admin(),'policy':policy(),'customer_policies':{e:policy(e) for e in scope}}


@frappe.whitelist()
def operations_detail(kind,name):
    scope=require_manager()
    from ia_maturity.grc import departments as dept
    if kind=='customer':
        require_manager(name);selected=[name]
        from ia_maturity.grc.organizations import organization_detail
        profile=organization_detail(name)
    elif kind=='auditor':
        if not sec.is_admin() and not (dept.staff_types(name)&dept.staff_types()):sec.deny()
        assigned=frappe.get_all('Auditor Customer Assignment',filters={'auditor':name,'active':1,'entity':['in',scope or ['__none__']]},pluck='entity')
        if not sec.is_admin() and not assigned:sec.deny()
        if sec.account_type(name)!='Auditor':sec.deny()
        selected=scope if sec.is_admin() else assigned
        from ia_maturity.grc.identity import display_name
        profile=frappe.db.get_value('User',name,['name','email','mobile_no','phone','language','time_zone','enabled','last_login','creation'],as_dict=True);profile['full_name']=display_name(name);profile['roles']=sorted(sec.roles(name)&sec.AUDITOR_ROLES)
    else:sec.deny()
    query={'entity':['in',selected or ['__none__']]}
    assessments=frappe.get_all('GRC Assessment Assignment',filters=query,fields=['name','entity','assessment','respondent','consultant','reviewer','workflow_state','due_date','review_due_date'],order_by='modified desc',limit_page_length=0)
    actions=frappe.get_all('IA Maturity Action',filters=query,fields=['name','entity','assessment','finding_title','status','assigned_to','due_date'],order_by='modified desc',limit_page_length=0)
    followups=frappe.get_all('GRC Follow Up',filters=query,fields=['name','entity','note','status','assigned_to','due_date','grc_department'],order_by='modified desc',limit_page_length=0)
    activity_query={'actor':name} if kind=='auditor' and sec.is_admin() else query
    activity=frappe.get_all('GRC Activity',filters=activity_query,fields=['name','entity','actor','action','creation','assessment','details','grc_department'],order_by='creation desc',limit_page_length=0)
    assessments=[a for a in assessments if dept.can_read(a)]
    actions=[a for a in actions if dept.can_read(a)]
    followups=[a for a in followups if dept.can_read(a)]
    activity=[a for a in activity if dept.can_read(a)]
    if kind=='auditor':
        assessments=[a for a in assessments if name in {a.consultant,a.reviewer}]
        actions=[a for a in actions if a.assigned_to==name];followups=[a for a in followups if a.assigned_to==name];activity=[a for a in activity if a.actor==name]
    counts={}
    for row in activity:counts[row.action]=counts.get(row.action,0)+1
    return {'profile':profile,'assessments':assessments,'actions':actions,'followups':followups,'activity':activity,'activity_summary':counts}
