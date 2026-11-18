import {test,expect,type Page} from '@playwright/test';

const user='ux-customer@example.test';
const company={name:'UX Company',entity_name:'UX Company'};
const dashboard={assessments:[],counts:{},total:0,page:1,page_size:15,customer_count:1,overdue:0,overdue_actions_count:0,overdue_actions:[],recent_activity:[],needs_reassignment:0};
function customer(type='GRC',extra:Record<string,unknown>={}){return {enabled:true,kind:'Customer',user,full_name:'UX Customer',home:'/grc/customer',organizations:[company],memberships:[{entity:company.name,membership_role:'Organization Admin'}],audit_type_access:{[company.name]:[type]},allowed_assessment_types:[type],workspace_preferences:{show_page_tour:false,show_help:false},...extra}}
function consultant(type='Internal Audit',extra:Record<string,unknown>={}){return {enabled:true,kind:'Auditor',user,full_name:'UX Consultant',home:'/grc/auditor',organizations:[company],assignments:[{entity:company.name,responsibility:'Consultant'}],can_invite_customers:true,staff_roles:['GRC Consultant'],department_memberships:[{department:type,role:'Consultant'}],workspace_preferences:{show_page_tour:false,show_help:false},...extra}}
async function mock(page:Page,session:Record<string,unknown>,responses:Record<string,unknown>={},language='en'){
 await page.addInitScript(language=>{localStorage.setItem('grc-language',language);localStorage.removeItem('grc-organization:ux-customer@example.test')},language);
 await page.route('**/api/method/**',route=>{
  const name=route.request().url().split('/api/method/')[1].split('?')[0].split('.').pop()!;
  return route.fulfill({json:{message:name==='bootstrap'?session:name==='dashboard'?responses.dashboard||dashboard:name in responses?responses[name]:[]}});
 });
}
function record(state:string){return {name:'UX-ASSESSMENT',entity:company.name,respondent:user,respondent_name:'UX Customer',state,editable:false,review_actions:[],question_count:20,answered_count:20}}

for(const type of ['Internal Audit','GRC'])test(`${type}: submitted customer sees results and waiting next step`,async({page})=>{
 await mock(page,customer(type),{dashboard:{...dashboard,assessments:[record('Submitted')],total:1}});
 await page.goto('/grc/customer');
 await expect(page.getByRole('heading',{name:'Your assessment is with the review team',exact:true})).toBeVisible();
 await expect(page.getByText('Your submitted answers are locked. Open the assessment for available results, or wait for the team to request clarification.')).toBeVisible();
 await expect(page.getByRole('link',{name:'View assessment and results',exact:true})).toHaveAttribute('href','/grc/customer/assessments/UX-ASSESSMENT');
});

for(const [state,title] of [['Approved','Your assessment is approved'],['Report Released','Your official report is ready']])test(`customer ${state} explains report availability`,async({page})=>{
 await mock(page,customer(),{dashboard:{...dashboard,assessments:[record(state)],total:1}});
 await page.goto('/grc/customer');
 await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'View assessment and results',exact:true})).toBeVisible();
});

test('GRC draft behind its mandatory profile gate has a resume action instead of another audit choice',async({page})=>{
 await mock(page,customer(),{dashboard:{...dashboard,assessments:[{...record('Draft'),current:true,profile_required:true,answered_count:0}],total:1}});
 await page.goto('/grc/customer');
 await expect(page.getByText('Complete your company profile to continue this assessment. Your existing draft is saved.')).toBeVisible();
 await expect(page.getByRole('link',{name:'Continue assessment',exact:true})).toHaveAttribute('href','/grc/customer/assessments/UX-ASSESSMENT');
 await expect(page.getByRole('heading',{name:'Choose your assessment',exact:true})).toHaveCount(0);
});

test('first assessment type is chosen once and later starts ask again',async({page})=>{
 await mock(page,customer('GRC',{allowed_assessment_types:['Internal Audit','GRC'],audit_type_access:{[company.name]:['Internal Audit','GRC']}}),{templates:[{name:'GRC1',template_name:'GRC template',assessment_type:'GRC',is_active:1,grc_published:1,is_default:1,version:1}]});
 await page.goto('/grc/customer');
 await page.locator('.assessment-types input[value="GRC"]').check();
 await page.getByRole('button',{name:'Continue',exact:true}).click();
 const modal=page.getByRole('dialog',{name:'Start assessment',exact:true});
 await expect(modal).toContainText('Assessment type: GRC');
 await expect(modal.locator('.assessment-types')).toHaveCount(0);
 await modal.getByRole('button',{name:'Cancel',exact:true}).click();
 await page.getByRole('button',{name:'Start assessment',exact:true}).click();
 await expect(modal.locator('.assessment-types input[value="GRC"]')).toBeVisible();
 await expect(modal.locator('.assessment-types input[value="GRC"]')).not.toBeChecked();
});

test('read-only customer empty state explains assignment without an unavailable Start action',async({page})=>{
 await mock(page,customer('Internal Audit',{memberships:[{entity:company.name,membership_role:'Viewer'}]}));
 await page.goto('/grc/customer');
 await expect(page.getByText('Your organization administrator or department team must assign an assessment before you can begin.')).toBeVisible();
 await expect(page.getByRole('button',{name:'Start assessment',exact:true})).toHaveCount(0);
});

test('department manager portfolio describes management scope rather than personal assignments',async({page})=>{
 await mock(page,consultant('Internal Audit',{organizations:[],assignments:[],can_manage_departments:true,can_operations:true,staff_roles:['GRC Manager'],department_memberships:[{department:'Internal Audit',role:'Manager'}]}),{dashboard:{...dashboard,customer_count:0}});
 await page.goto('/grc/auditor');
 await expect(page.getByText('Customers and assessments available within your department management scope.')).toBeVisible();
 await expect(page.getByText('No customer organizations are available in your management scope yet.')).toBeVisible();
 await expect(page.getByRole('heading',{name:'No customers in your management scope',exact:true})).toBeVisible();
 await expect(page.getByText('Invite a customer for your department, or review department access and customer assignments if an existing customer should appear.')).toBeVisible();
 await expect(page.getByRole('link',{name:'Available customers: 0',exact:true})).toBeVisible();
});

test('filtered empty customer list can clear its filters instead of starting a duplicate',async({page})=>{
 await mock(page,customer());
 await page.goto('/grc/customer/assessments?search=not-found&state=Submitted');
 await expect(page.getByRole('heading',{name:'No matching assessments',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Clear filters',exact:true}).click();
 await expect(page).toHaveURL(/\/grc\/customer\/assessments$/);
 await expect(page.getByRole('heading',{name:'No assessments yet',exact:true})).toBeVisible();
});

test('staff draft ignores a saved organization without creation rights and can cancel',async({page})=>{
 const readonly={name:'Read-only company',entity_name:'Read-only company'};
 await mock(page,consultant('Internal Audit',{organizations:[readonly,company]}),{templates:[{name:'IA20',template_name:'IA template',assessment_type:'Internal Audit',is_active:1,grc_published:1,is_default:1,version:1}]});
 await page.addInitScript(()=>localStorage.setItem('grc-organization:ux-customer@example.test','Read-only company'));
 let creates=0;
 await page.route('**/api/method/ia_maturity.grc.api.start_assessment',route=>{creates++;return route.fulfill({json:{message:{name:'UNEXPECTED'}}})});
 await page.goto('/grc/auditor');
 await page.getByRole('button',{name:'Start assessment',exact:true}).click();
 const modal=page.getByRole('dialog',{name:'Start assessment',exact:true});
 await expect(modal).toContainText(company.name);
 await expect(modal).not.toContainText(readonly.name);
 await modal.getByRole('button',{name:'Cancel',exact:true}).click();
 await expect(modal).toHaveCount(0);expect(creates).toBe(0);
});

test('unselected audit type is explained before an unavailable-template warning',async({page})=>{
 await mock(page,customer('GRC',{allowed_assessment_types:['Internal Audit','GRC'],audit_type_access:{[company.name]:['Internal Audit','GRC']}}));
 await page.goto('/grc/customer');
 await page.getByRole('button',{name:'Start assessment',exact:true}).click();
 const modal=page.getByRole('dialog',{name:'Start assessment',exact:true});
 await expect(modal).toContainText('Choose an audit type to see the available assessment.');
 await expect(modal).not.toContainText('No active published assessment templates are available.');
 await expect(modal.getByRole('button',{name:'Start assessment',exact:true})).toBeDisabled();
 await modal.getByRole('button',{name:'Cancel',exact:true}).click();
 await expect(modal).toHaveCount(0);
});

for(const type of ['Internal Audit','GRC'])test(`${type}: consultant filtered invitation list clears and draft cancels without sending`,async({page})=>{
 await mock(page,consultant(type));let sends=0;
 await page.route('**/api/method/ia_maturity.grc.api.create_onboarding_invitation',route=>{sends++;return route.fulfill({json:{message:{name:'UNEXPECTED'}}})});
 await page.goto('/grc/auditor/onboarding');
 await page.getByLabel('Search',{exact:true}).fill('missing');
 await expect(page.getByRole('heading',{name:'No matching invitations',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Clear filters',exact:true}).click();
 await expect(page.getByRole('heading',{name:'No onboarding invitations',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Invite customer',exact:true}).click();
 const modal=page.getByRole('dialog',{name:'Invite customer',exact:true});
 await expect(modal).toContainText('You can cancel this draft without sending anything.');
 await expect(modal.getByRole('combobox',{name:'Assessment type',exact:true})).toContainText(type);
 if(type==='GRC')await modal.getByRole('checkbox',{name:'Risk',exact:true}).check();
 await modal.getByRole('button',{name:'Cancel',exact:true}).click();
 await expect(modal).toHaveCount(0);expect(sends).toBe(0);
 if(type==='GRC'){
  await page.getByRole('button',{name:'Invite customer',exact:true}).click();
  await expect(modal.getByRole('checkbox',{name:'Risk',exact:true})).not.toBeChecked();
  await modal.getByRole('button',{name:'Cancel',exact:true}).click();
 }
});

test('closed, expired and pending customer invitations have safe next steps instead of Resume',async({page})=>{
 await mock(page,customer(),{customer_onboarding:['Revoked','Expired','Pending Invitation Approval'].map((status,i)=>({name:'INV'+i,email:user,status,next_action:'',blocker:''}))});
 await page.goto('/grc/customer/onboarding');
 await expect(page.getByText('This invitation is closed. Ask the inviting team for a new invitation.')).toBeVisible();
 await expect(page.getByText('Ask your inviting auditor to resend the invitation.')).toBeVisible();
 await expect(page.getByText('Your details have been submitted. An administrator will review the request.')).toBeVisible();
 await expect(page.getByRole('button',{name:'Resume onboarding',exact:true})).toHaveCount(0);
});

test('consultant pending approval detail explains waiting and preserves action restrictions',async({page})=>{
 await mock(page,consultant(),{onboarding_detail:{name:'INV-PENDING',email:user,company:company.name,assessment_type:'Internal Audit',status:'Pending Invitation Approval',next_action:'Administrator approves invitation',blocker:'',delivery_status:'Not sent',permitted_actions:[],events:[]}});
 await page.goto('/grc/auditor/onboarding/INV-PENDING');
 await expect(page.getByText('This request is waiting for an authorized manager. Do not send another invitation while approval is pending.')).toBeVisible();
 await expect(page.locator('.onboarding-meta')).toContainText('Internal Audit');
 await expect(page.getByRole('button',{name:'Resend invitation',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Send reminder',exact:true})).toHaveCount(0);
});

test('invalid public invitation gives a recovery path without signup fields',async({page})=>{
 await mock(page,{enabled:true,kind:'Guest',home:'/login'});
 await page.route('**/api/method/ia_maturity.grc.api.onboarding_link**',route=>route.fulfill({status:410,json:{message:'The invitation is expired.'}}));
 await page.goto('/onboarding?token=invalid-fixture');
 await expect(page.getByText('This invitation could not be opened. Use the latest invitation email, or ask the inviting team to resend it. You can still sign in to an existing account.')).toBeVisible();
 await expect(page.getByRole('link',{name:'Customer sign in',exact:true})).toHaveAttribute('href','/login');
 await expect(page.getByLabel('Full name',{exact:true})).toHaveCount(0);
});

test('invited OTP explains its inbox and cooldown and permits resend after the timer',async({page})=>{
 await page.clock.install();
 await mock(page,{enabled:true,kind:'Guest',home:'/login'},{onboarding_link:{email:user,company:'Invited company',assessment_type:'Internal Audit',language:'en'}});
 let sends=0;
 await page.route('**/api/method/ia_maturity.grc.auth.request_code',route=>{sends++;return route.fulfill({json:{message:{resend_after_seconds:60,expires_in_seconds:900}}})});
 await page.goto('/onboarding?token=otp-fixture');
 await page.getByLabel('Full name',{exact:true}).fill('Customer Name');
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Send verification code',exact:true}).click();
 const resend=page.getByRole('button',{name:/Resend verification code/});
 await expect(resend).toBeDisabled();
 await expect(page.getByText('Check your spam folder if it has not arrived. Use Resend code when the countdown ends.',{exact:false})).toBeVisible();
 expect(sends).toBe(1);
 await page.clock.fastForward(61000);
 await expect(resend).toBeEnabled();await resend.click();expect(sends).toBe(2);
 await expect(resend).toBeDisabled();
});

test('customer login explains OTP expiry and rejects an incomplete code on the frontend',async({page})=>{
 await page.clock.install();
 await mock(page,{enabled:true,kind:'Guest',home:'/login'});
 let verifies=0;
 await page.route('**/api/method/ia_maturity.grc.auth.request_code',route=>route.fulfill({json:{message:{resend_after_seconds:60,expires_in_seconds:120}}}));
 await page.route('**/api/method/ia_maturity.grc.auth.verify_code',route=>{verifies++;return route.fulfill({json:{message:{redirect:'/grc/customer'}}})});
 await page.goto('/login');await page.getByLabel('Email',{exact:true}).fill(user);
 await page.getByRole('button',{name:'Send code',exact:true}).click();
 await expect(page.getByText(user,{exact:true})).toBeVisible();
 await page.getByLabel('Verification code',{exact:true}).fill('12');
 await page.getByRole('button',{name:'Verify and continue',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('Enter the six-digit verification code to continue.');expect(verifies).toBe(0);
 await page.clock.fastForward(121000);
 await expect(page.getByText('This code has expired. Request a new code to continue.')).toBeVisible();
 await expect(page.getByRole('button',{name:'Verify and continue',exact:true})).toBeDisabled();
 await expect(page.getByRole('button',{name:'Resend code',exact:true})).toBeEnabled();
});

test('invitation first-send rate limit has a visible countdown and recovers',async({page})=>{
 await page.clock.install();
 await mock(page,{enabled:true,kind:'Guest',home:'/login'},{onboarding_link:{email:user,company:'Invited company',assessment_type:'GRC',language:'en'}});
 await page.route('**/api/method/ia_maturity.grc.auth.request_code',route=>route.fulfill({status:429,json:{message:'Please wait before requesting another code.',retry_after_seconds:60}}));
 await page.goto('/onboarding?token=cooldown-fixture');
 await page.getByLabel('Full name',{exact:true}).fill('Customer Name');await page.getByRole('checkbox').check();
 const send=page.getByRole('button',{name:'Send verification code',exact:true});
 await send.click();await expect(send).toBeDisabled();
 await expect(page.getByRole('status')).toContainText('You can request another verification email in');
 await page.clock.fastForward(61000);await expect(send).toBeEnabled();
});

test('Arabic mobile customer result guidance remains readable',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await mock(page,customer(),{dashboard:{...dashboard,assessments:[record('Submitted')],total:1}},'ar');
 await page.goto('/grc/customer');
 await expect(page.getByRole('heading',{name:'تقييمك لدى فريق المراجعة',exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'عرض التقييم والنتائج',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/ux-customer-results-arabic-mobile.png',fullPage:true,animations:'disabled'});
});
