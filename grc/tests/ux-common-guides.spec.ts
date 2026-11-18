import {test,expect,type Page} from '@playwright/test';
const org={name:'UX-GUIDE',entity_name:'Guide company'};
const empty={assessments:[],counts:{},total:0,page:1,page_size:15,customer_count:0,overdue:0,overdue_actions_count:0,overdue_actions:[],recent_activity:[]};
function session(type:string,role:string){const customer=role==='Customer';return {enabled:true,user:'ux-guide@example.test',full_name:'Guide demo',kind:customer?'Customer':'Auditor',home:customer?'/grc/customer':'/grc/auditor',organizations:[org],memberships:customer?[{entity:org.name,membership_role:'Organization Admin'}]:[],assignments:[],allowed_assessment_types:[type],audit_type_access:{[org.name]:[type]},department_memberships:customer?[]:[{department:type,role}],staff_roles:customer?[]:['GRC '+role],can_manage_departments:role==='Manager',can_operations:role==='Manager',can_configure_scope:role==='Manager',can_invite_customers:!customer,workspace_preferences:{show_page_tour:false,show_help:true}}}
async function mock(page:Page,s:any,extra:Record<string,unknown>={}){
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.route('**/api/method/ia_maturity.grc.api.**',route=>{const name=route.request().url().split('.').pop()!.split('?')[0];return route.fulfill({json:{message:name==='bootstrap'?s:name==='dashboard'?empty:name in extra?extra[name]:name==='profile'?{name_repair_fields:[],email:s.user,full_name:s.full_name,kind:s.kind,modified:'1',values:{},fields:[],editable_fields:[],time_zones:[],workspace_preferences:s.workspace_preferences,authenticator:{policy:'Disabled',required:false,available:true,enrolled:false,can_enroll:false,method:'OTP App'}}:[]}})});
}
for(const type of ['Internal Audit','GRC'])for(const role of ['Customer','Consultant','Reviewer','Manager'])test(`${type} ${role} help explains current access and next steps`,async({page})=>{
 const s=session(type,role);await mock(page,s);await page.goto(s.home+'/guide');
 await expect(page.getByRole('heading',{name:role==='Customer'?'Customer guide':role==='Manager'?'Manager guide':'Auditor guide',exact:true})).toBeVisible();
 if(role==='Customer'){
  await expect(page.locator('.guide-sections')).toContainText('No password is needed.');
  await expect(page.getByRole('heading',{name:'Company profile and sections',exact:true})).toHaveCount(type==='GRC'?1:0);
  if(type==='Internal Audit')await expect(page.locator('.main-content')).not.toContainText('GRC');
 }else{
  await expect(page.locator('.guide-sections')).toContainText('Staff 2FA is off by default');
  await expect(page.locator('.guide-sections')).toContainText(role==='Manager'?'Pending Source Approval':'Consultant: prepare and monitor assigned work');
 }
 await page.getByRole('button',{name:'Start guided tour',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
 await page.goto(s.home+'/preferences');await expect(page.getByText('Verification codes, account security emails, invitations and clarification requests are mandatory and cannot be disabled.')).toBeVisible();await page.getByRole('button',{name:'Save changes',exact:true}).click();await expect(page.getByText('Saved',{exact:true})).toBeVisible();
 await page.goto(s.home+'/profile');await expect(page.getByText('Profile editing is currently managed by your platform administrator.')).toBeVisible();await page.getByRole('tab',{name:'Account security',exact:true}).click();
 if(role==='Customer'){await expect(page.getByText('Customers sign in with an email code every time. No password is needed.')).toBeVisible();await expect(page.locator('input[type="password"]')).toHaveCount(0)}
 else await expect(page.getByText(/Staff two-factor authentication is off for this account/)).toBeVisible();
 await page.getByRole('tab',{name:'Workspace preferences',exact:true}).click();await page.getByRole('button',{name:'Save workspace preferences',exact:true}).click();await expect(page.getByText('Saved',{exact:true})).toBeVisible();
});
test('a customer approved for both types still receives GRC profile and section guidance',async({page})=>{
 const s={...session('Internal Audit','Customer'),allowed_assessment_types:['Internal Audit','GRC'],audit_type_access:{[org.name]:['Internal Audit','GRC']}};
 await mock(page,s);await page.goto('/grc/customer/guide');await expect(page.getByRole('heading',{name:'Company profile and sections',exact:true})).toBeVisible();
});
test('optional questionnaire management has an explanatory empty state and a way back',async({page})=>{
 await mock(page,session('GRC','Manager'),{scope_configurations:{templates:[],configurations:[]}});await page.goto('/grc/auditor/audit-packages');
 await expect(page.getByRole('heading',{name:'No questionnaire versions available',exact:true})).toBeVisible();await expect(page.getByText(/This configuration is optional/)).toBeVisible();await expect(page.getByRole('combobox',{name:'Questionnaire version',exact:true})).toHaveCount(0);
 await page.getByRole('link',{name:'Return to workspace',exact:true}).click();await expect(page).toHaveURL(/\/grc\/auditor$/);
});
test('disabled staff 2FA explains password sign-in and never offers setup',async({page})=>{
 const s=session('Internal Audit','Reviewer');await mock(page,s,{profile:{name_repair_fields:[],email:s.user,full_name:s.full_name,kind:'Auditor',modified:'1',values:{},fields:[],editable_fields:[],time_zones:[],authenticator:{policy:'Disabled',required:false,available:true,enrolled:false,can_enroll:false,method:'OTP App'}}});await page.goto('/grc/auditor/profile');await page.getByRole('tab',{name:'Account security',exact:true}).click();
 await expect(page.getByText(/Staff two-factor authentication is off for this account/)).toBeVisible();await expect(page.getByRole('button',{name:'Set up authenticator',exact:true})).toHaveCount(0);
});
test('Arabic mobile manager help stays readable and its optional tour can close',async({page})=>{
 await mock(page,session('GRC','Manager'));await page.setViewportSize({width:390,height:844});await page.goto('/grc/auditor/guide');await page.getByRole('button',{name:'العربية',exact:true}).click();await expect(page.getByRole('heading',{name:'دليل المدير',exact:true})).toBeVisible();await page.getByRole('button',{name:'بدء الجولة الإرشادية',exact:true}).click();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
