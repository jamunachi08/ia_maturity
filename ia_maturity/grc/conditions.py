from ia_maturity.grc.security import query_condition

def query_auditor_customer_assignment(user=None):
    return query_condition(user, "Auditor Customer Assignment")

def query_grc_organization_membership(user=None):
    return query_condition(user, "GRC Organization Membership")

def query_grc_organization_unit(user=None):
    return query_condition(user, "GRC Organization Unit")

def query_grc_invitation(user=None):
    return query_condition(user, "GRC Invitation")

def query_grc_assessment_assignment(user=None):
    return query_condition(user, "GRC Assessment Assignment")

def query_grc_activity(user=None):
    return query_condition(user, "GRC Activity")

def query_grc_follow_up(user=None):
    return query_condition(user, "GRC Follow Up")

def query_grc_report_release(user=None):
    return query_condition(user, "GRC Report Release")

def query_grc_reminder_delivery(user=None):
    return query_condition(user, "GRC Reminder Delivery")

def query_ia_maturity_entity(user=None):
    return query_condition(user, "IA Maturity Entity")

def query_ia_maturity_assessment(user=None):
    return query_condition(user, "IA Maturity Assessment")

def query_ia_maturity_action(user=None):
    return query_condition(user, "IA Maturity Action")

def query_ia_audit_issue(user=None):
    return query_condition(user, "IA Audit Issue")
