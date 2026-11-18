import {test,expect,type Page} from '@playwright/test';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

// These browser checks isolate the real React UI from the shared mutable demo site.
// Unmocked API/database journeys are separately required before acceptance.
const org={name:'DEMO',entity_name:'Demo Company'};
const customer={enabled:true,kind:'Customer',user:'demo-customer@example.test',full_name:'Demo Customer',home:'/grc/customer',organizations:[org],memberships:[{entity:org.name,membership_role:'Organization Admin'}],workspace_preferences:{show_page_tour:false,show_help:false},allowed_assessment_types:['GRC'],audit_type_access:{DEMO:['GRC']}};
const emptyDashboard={counts:{},assessments:[],total:0,overdue:0,overdue_actions_count:0,recent_activity:[]};
const sections=[{code:'Awareness',title:'GRC General Maturity Awareness',question_count:3},{code:'Risk',title:'Risk',question_count:13},{code:'Compliance',title:'Compliance',question_count:12},{code:'Governance',title:'Governance',question_count:18}];
const packages=['Risk','Compliance','Governance'].map(code=>({code:code.toLowerCase(),label:code,label_ar:({Risk:'المخاطر',Compliance:'الامتثال',Governance:'الحوكمة'} as Record<string,string>)[code],description:'',description_ar:'',sections:[code]}));
function assessment(){return {name:'DEMO-GRC',assessment_type:'GRC',entity:'DEMO',respondent:customer.user,docstatus:0,modified:'v1',state:'Draft',current:true,editable:true,review_actions:[],released:false,results_visible:false,question_count:46,answered_count:0,scope_editable:true,scope:{configuration:'demo',version:1,required_sections:['Awareness'],minimum_optional_sections:1,packages,sections,selected_packages:[],selected_sections:['Awareness'],confirmed:false,acknowledgement_required:false,can_correct:false}};}
async function setup(page:Page,session:any=customer){
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.route('**/assets/ia_maturity/images/*',route=>route.fulfill({path:path.join(path.dirname(fileURLToPath(import.meta.url)),'../../ia_maturity/public/images',path.basename(new URL(route.request().url()).pathname))}));
 await page.route('**/api/method/**',route=>{
  const method=route.request().url().split('/api/method/')[1].split('?')[0].split('.').pop();
  const message=method==='bootstrap'?session:method==='dashboard'?emptyDashboard:method==='templates'?[{name:'GRC46',template_name:'GRC Questionnaire',assessment_type:'GRC',version:1,is_default:1,is_active:1,grc_published:1},{name:'IA20',template_name:'IA Questionnaire',assessment_type:'Internal Audit',version:1,is_default:1,is_active:1,grc_published:1}]:[];
  return route.fulfill({json:{message}});
 });
}

test('customer login uses OTP only while staff retains password sign in',async({page})=>{
 await setup(page,{enabled:true,kind:'Guest',home:'/login'});
 await page.goto('/login');
 await expect(page.getByLabel('Email',{exact:true})).toBeVisible();
 await expect(page.getByLabel('Password',{exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Forgot password?',exact:true})).toHaveCount(0);
 await expect(page.getByText('Customers sign in with an email code every time. No password is needed.')).toBeVisible();
 await page.getByRole('link',{name:'Staff sign in',exact:true}).click();
 await expect(page.getByLabel('Password',{exact:true})).toBeVisible();
 await expect(page.getByLabel('Email or username',{exact:true})).toBeVisible();
});

test('signup collects company without sector or password and sends verification fields',async({page})=>{
 await setup(page,{enabled:true,kind:'Guest',home:'/login'});
 let payload:any;
 await page.route('**/api/method/ia_maturity.grc.auth.request_code',route=>{payload=route.request().postDataJSON();return route.fulfill({json:{message:{resend_after_seconds:60,expires_in_seconds:900}}})});
 await page.goto('/signup');
 await page.getByLabel('Email',{exact:true}).fill('signup@example.test');
 await page.getByLabel('Full name',{exact:true}).fill('Demo Customer');
 await page.getByLabel('Company',{exact:true}).fill('Demo Company');
 await expect(page.getByRole('combobox',{name:'Sector',exact:true})).toHaveCount(0);
 await expect(page.getByLabel('Password',{exact:true})).toHaveCount(0);
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Send verification email',exact:true}).click();
 await expect(page.getByLabel('Verification code',{exact:true})).toBeVisible();
 expect(payload).toMatchObject({email:'signup@example.test',full_name:'Demo Customer',organization_name:'Demo Company',purpose:'Start'});
 expect(payload).not.toHaveProperty('organization_sector');
});

test('IA invitation locks email and company and never offers another audit type',async({page})=>{
 await setup(page,{enabled:true,kind:'Guest',home:'/login'});
 await page.route('**/api/method/ia_maturity.grc.api.onboarding_link**',r=>r.fulfill({json:{message:{email:'invited@example.test',company:'Invited Company',assessment_type:'Internal Audit',team_label:'Internal Audit',language:'en',auditor:'Inviting Auditor'}}}));
 await page.goto('/onboarding?token=demo');
 await expect(page.getByText('Invited by the Internal Audit team',{exact:true})).toBeVisible();
 await expect(page.getByLabel('Email',{exact:true})).toHaveAttribute('readonly','');
 await expect(page.getByLabel('Company',{exact:true})).toHaveValue('Invited Company');
 await expect(page.getByLabel('Company',{exact:true})).toHaveAttribute('readonly','');
 await expect(page.getByRole('radio')).toHaveCount(0);
 await expect(page.locator('body')).not.toContainText('Governance, Risk and Compliance');
 await expect(page.locator('body')).not.toContainText('GRC');
});

test('IA customer workspace and guide contain only the granted audit type',async({page})=>{
 await setup(page,{...customer,allowed_assessment_types:['Internal Audit'],audit_type_access:{DEMO:['Internal Audit']}});
 await page.goto('/grc/customer');
 await expect(page.getByRole('radio',{name:/Internal Audit/})).toBeVisible();
 await expect(page.locator('body')).not.toContainText('GRC');
 await page.goto('/grc/customer/guide');
 await expect(page.getByRole('heading',{name:'Customer guide',exact:true})).toBeVisible();
 await expect(page.locator('body')).not.toContainText('GRC');
 await expect(page.getByRole('link',{name:'Download bilingual PDF',exact:true})).toHaveCount(0);
});

test('customer dashboard and start dialog show only the granted type',async({page})=>{
 await setup(page);
 await page.goto('/grc/customer');
 await expect(page.getByRole('radio',{name:/Governance, Risk and Compliance/})).toBeVisible();
 await expect(page.getByRole('radio',{name:/Internal Audit/})).toHaveCount(0);
 await page.getByRole('button',{name:'Continue',exact:true}).click();
 await expect(page.getByRole('dialog')).toBeVisible();
 await expect(page.getByRole('dialog').getByRole('radio')).toHaveCount(0);
 await expect(page.getByRole('dialog').getByRole('combobox',{name:'Template',exact:true})).toHaveCount(0);
 await expect(page.getByRole('dialog').getByRole('button',{name:'Start assessment',exact:true})).toBeEnabled();
});

test('GRC requires another section and protects invitation minimum sections',async({page})=>{
 await setup(page);
 const doc:any=assessment();
 await page.route('**/api/method/ia_maturity.grc.api.assessment**',r=>r.fulfill({json:{message:doc}}));
 await page.goto('/grc/customer/assessments/DEMO-GRC');
 const confirm=page.getByRole('button',{name:'Confirm scope and continue',exact:true});
 await expect(confirm).toBeDisabled();
 await expect(page.getByRole('checkbox',{name:/GRC General Maturity Awareness/})).toBeDisabled();
 await page.getByRole('checkbox',{name:/Risk/}).check();
 await expect(confirm).toBeEnabled();
 doc.scope.minimum_packages=['risk'];doc.scope.invited_sections=['Awareness','Risk'];doc.scope.selected_packages=['risk'];
 await page.reload();
 await expect(page.getByRole('checkbox',{name:/Risk/})).toBeChecked();
 await expect(page.getByRole('checkbox',{name:/Risk/})).toBeDisabled();
 await page.getByRole('checkbox',{name:/Compliance/}).check();
 await expect(confirm).toBeEnabled();
});

test('report emails a PDF to the registered customer with no editable recipient',async({page})=>{
 await setup(page);
 const doc:any={...assessment(),scope:undefined,docstatus:1,scope_editable:false,editable:false,state:'Submitted',questions:[],can_email_report:true,allow_report_email:1,report_recipient:customer.user,expand_report:true};
 await page.route('**/api/method/ia_maturity.grc.api.assessment**',r=>r.fulfill({json:{message:doc}}));
 await page.goto('/grc/customer/assessments/DEMO-GRC');
 await expect(page.getByRole('heading',{name:'GRC Maturity Assessment',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Email report',exact:true}).click();
 await expect(page.getByRole('dialog').getByLabel('Recipient',{exact:true})).toHaveValue(customer.user);
 await expect(page.getByRole('dialog').getByLabel('Recipient',{exact:true})).toHaveAttribute('readonly','');
 await expect(page.getByRole('button',{name:'Send PDF',exact:true})).toBeVisible();
});

test('mobile report retains PDF actions without an empty embedded preview',async({page})=>{
 await setup(page);
 const doc:any={...assessment(),scope:undefined,docstatus:1,editable:false,state:'Report Released',released:true,questions:[],can_download_report:true,can_email_report:true,pdf_url:'/api/method/ia_maturity.grc.api.download_report?name=DEMO-GRC',expand_report:true};
 await page.route('**/api/method/ia_maturity.grc.api.assessment**',r=>r.fulfill({json:{message:doc}}));
 await page.goto('/grc/customer/assessments/DEMO-GRC');
 await expect(page.getByTitle('Report preview',{exact:true})).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 await expect(page.getByTitle('Report preview',{exact:true})).toBeHidden();
 await expect(page.getByRole('link',{name:'Download PDF',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Email report',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
});

test('second audit access remains pending until manager approval',async({page})=>{
 await setup(page);
 let sent:any;
 await page.route('**/api/method/ia_maturity.grc.api.request_audit_type',r=>{sent=r.request().postDataJSON();return r.fulfill({json:{message:{name:'REQUEST',status:'Pending'}}})});
 await page.goto('/grc/customer/audit-access');
 await page.getByRole('button',{name:'Request another audit type',exact:true}).click();
 await page.getByRole('button',{name:'Send request',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('Both department approvals are required before access changes.');
 expect(sent).toMatchObject({entity:'DEMO',assessment_type:'Internal Audit'});
 await expect(page.getByRole('button',{name:'Request pending',exact:true})).toBeDisabled();
});

test('department manager can review a request without exposing other departments',async({page})=>{
 await setup(page,{...customer,kind:'Auditor',home:'/grc/auditor',department_memberships:[{department:'GRC',role:'Manager'}],can_manage_departments:true});
 await page.route('**/api/method/ia_maturity.grc.api.audit_type_requests**',r=>r.fulfill({json:{message:[{name:'REQUEST',entity:'Demo Company',assessment_type:'GRC',requested_by:customer.user,status:'Pending Target Approval',can_decide:true}]}}));
 await page.goto('/grc/auditor/audit-access');
 await page.getByRole('button',{name:'Approve',exact:true}).click();
 await expect(page.getByRole('dialog',{name:'Approve audit access',exact:true})).toBeVisible();
 await page.getByRole('dialog').getByRole('button',{name:'Close',exact:true}).click();
 await page.getByRole('button',{name:'Add department staff',exact:true}).click();
 await page.getByRole('dialog').getByRole('combobox',{name:'Department',exact:true}).click();
 await expect(page.getByRole('option',{name:'GRC',exact:true})).toBeVisible();
 await expect(page.getByRole('option',{name:'Internal Audit',exact:true})).toHaveCount(0);
 await page.keyboard.press('Escape');
 await page.getByRole('dialog').getByRole('combobox',{name:'Role',exact:true}).click();
 await expect(page.getByRole('option',{name:'Consultant',exact:true})).toBeVisible();
 await expect(page.getByRole('option',{name:'Manager',exact:true})).toHaveCount(0);
});

test('invited verified customer proceeds directly to the pinned assessment',async({page})=>{
 const session={...customer,access_version:'before-activation'};
 await setup(page,session);
 await page.route('**/api/method/ia_maturity.grc.api.customer_onboarding**',r=>r.fulfill({json:{message:[{name:'INVITE',email:customer.user,company:'Demo Company',assessment_type:'GRC',status:'Email Verified'}]}}));
 await page.route('**/api/method/ia_maturity.grc.api.complete_onboarding',r=>{session.access_version='after-activation';return r.fulfill({json:{message:{assessment:'DEMO-GRC',status:'Completed'}}})});
 await page.route('**/api/method/ia_maturity.grc.api.assessment**',r=>r.fulfill({json:{message:assessment()}}));
 await page.goto('/grc/customer/onboarding');
 await expect(page).toHaveURL(/assessments\/DEMO-GRC\/scope$/);
 await expect(page.getByRole('heading',{name:'What would you like assessed?',exact:true})).toBeVisible();
});

test('GRC auditor invitation fixes department and captures minimum sections',async({page})=>{
 await setup(page,{...customer,kind:'Auditor',home:'/grc/auditor',can_invite_customers:true,department_memberships:[{department:'GRC',role:'Consultant'}]});
 let sent:any;
 await page.route('**/api/method/ia_maturity.grc.api.create_onboarding_invitation',r=>{sent=r.request().postDataJSON();return r.fulfill({json:{message:{name:'INVITE'}}})});
 await page.goto('/grc/auditor/onboarding');
 await page.getByRole('button',{name:'Invite customer',exact:true}).click();
 const modal=page.getByRole('dialog');
 await modal.getByLabel('Customer email',{exact:true}).fill('invited@example.test');
 await modal.getByLabel('Company',{exact:true}).fill('Invited Company');
 await modal.getByRole('checkbox',{name:'Risk',exact:true}).check();
 await modal.getByRole('button',{name:'Send invitation',exact:true}).click();
 await expect(modal).toHaveCount(0);
 expect(sent).toMatchObject({email:'invited@example.test',company:'Invited Company',assessment_type:'GRC',minimum_sections:['Awareness','Risk']});
});

test('existing-customer invitation approval response shows neutral manager feedback',async({page})=>{
 await setup(page,{...customer,kind:'Auditor',home:'/grc/auditor',can_invite_customers:true,department_memberships:[{department:'GRC',role:'Consultant'}]});
 await page.route('**/api/method/ia_maturity.grc.api.create_onboarding_invitation',r=>r.fulfill({json:{message:{name:'REQUEST',status:'Pending manager approval',pending_approval:true}}}));
 await page.goto('/grc/auditor/onboarding');
 await page.getByRole('button',{name:'Invite customer',exact:true}).click();
 const dialog=page.getByRole('dialog');
 await dialog.getByLabel('Customer email',{exact:true}).fill('existing@example.test');
 await dialog.getByLabel('Company',{exact:true}).fill('Requested Company');
 await dialog.getByRole('button',{name:'Send invitation',exact:true}).click();
 await expect(dialog).toHaveCount(0);
 await expect(page.getByText('Pending manager approval',{exact:true})).toBeVisible();
 await expect(page.locator('[data-tour="onboarding-tracker"]')).not.toContainText('Requested Company');
 await expect(page.locator('[data-tour="onboarding-tracker"]')).not.toContainText('existing@example.test');
});

test('Arabic mobile signup keeps OTP fields readable without horizontal overflow',async({page})=>{
 await setup(page,{enabled:true,kind:'Guest',home:'/login'});
 await page.setViewportSize({width:390,height:844});
 await page.goto('/signup');
 await page.getByRole('button',{name:'العربية',exact:true}).click();
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await expect(page.getByLabel('المنشأة',{exact:true})).toBeVisible();
 await expect(page.getByLabel('كلمة المرور',{exact:true})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.screenshot({path:'test-results/demo-signup-ar-mobile.png',fullPage:true});
});

for(const width of [320,390])test(`Arabic GRC scope preserves mandatory and invited sections at ${width}px`,async({page})=>{
 await setup(page);
 const doc:any=assessment();doc.scope.minimum_packages=['risk'];doc.scope.selected_packages=['risk'];
 await page.route('**/api/method/ia_maturity.grc.api.assessment**',r=>r.fulfill({json:{message:doc}}));
 await page.setViewportSize({width,height:844});
 await page.goto('/grc/customer/assessments/DEMO-GRC');
 await page.getByRole('button',{name:'العربية',exact:true}).click();
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await expect(page.getByRole('checkbox',{name:/المخاطر/})).toBeDisabled();
 await expect(page.getByRole('button',{name:'تأكيد النطاق والمتابعة',exact:true})).toBeEnabled();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.screenshot({path:`test-results/demo-scope-ar-${width}.png`,fullPage:true});
});
