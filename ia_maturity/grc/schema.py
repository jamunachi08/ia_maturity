"""Shared role and tenant schema constants."""
PORTAL_ROLES = ("GRC Customer", "GRC Organization Admin", "GRC Auditor", "GRC Reviewer", "GRC App Admin", "GRC Manager", "GRC Consultant")
CUSTOMER_ROLES = {"GRC Customer", "GRC Organization Admin", "IA Assessment Respondent"}
AUDITOR_ROLES = {"GRC Manager", "GRC Consultant", "GRC Auditor", "GRC Reviewer", "GRC App Admin", "IA Maturity Reviewer", "IA Maturity Manager"}
TENANT_DOCTYPES = ["Auditor Customer Assignment","GRC Organization Membership","GRC Organization Unit","GRC Invitation","GRC Assessment Assignment","GRC Activity","GRC Follow Up","GRC Report Release","GRC Reminder Delivery","IA Maturity Entity","IA Maturity Assessment","IA Maturity Action","IA Audit Issue"]
