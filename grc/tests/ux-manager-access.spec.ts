import {test,expect,type Page} from '@playwright/test';

test.use({trace:'off',video:'off'});
const entity='UX Company',manager='manager@ux.example.test';
const policy={onboarding:true,assignments:true,stages:['GRC Manager','GRC App Admin'],allow_self:false};
const org={name:entity,entity_name:entity,sector:'Other',contact_email:'customer@ux.example.test',is_active:1};
function session(overrides:any={}){return {enabled:true,kind:'Auditor',user:manager,full_name:'UX Manager',home:'/grc/auditor',is_admin:false,can_operations:true,can_manage_departments:true,can_invite_customers:true,organizations:[org],department_memberships:[{department:'Internal Audit',role:'Manager'}],staff_roles:['GRC Manager'],assignments:[{entity,responsibility:'Manager'}],managed_entities:[entity],audit_type_access:{[entity]:['Internal Audit']},workspace_preferences:{show_page_tour:false,show_help:false},...overrides};}
function overview(overrides:any={}){return {is_admin:false,policy,customer_policies:{[entity]:policy},customers:[org],auditors:[{name:manager,full_name:'UX Manager',enabled:1,roles:['GRC Manager']}],assignments:[{entity,auditor:manager,responsibility:'Manager'}],requests:[],...overrides};}
function request(overrides:any={}){return {name:'REQ-1',entity,assessment_type:'GRC',source_department:'Internal Audit',department:'GRC',requested_by:'customer@ux.example.test',status:'Pending Source Approval',can_decide:true,...overrides};}
function detail(overrides:any={}){return {...org,can_manage:false,can_assign_staff:false,read_only:false,can_view_company_profile:false,ownership_locked:false,members:[],units:[],invitations:[],auditors:[],...overrides};}
async function mock(page:Page,state:any,data:Record<string,any>={}){
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.route('**/api/method/ia_maturity.grc.api.**',route=>{
  const method=new URL(route.request().url()).pathname.split('.').pop()!;
  const message=method==='bootstrap'?state:method in data?data[method]:[];
  return route.fulfill({json:{message}});
 });
}

for(const kind of ['Internal Audit','GRC'])test(`${kind} customer audit access explains both approvals and optional cancellation`,async({page})=>{
 const state=session({kind:'Customer',home:'/grc/customer',user:'customer@ux.example.test',can_operations:false,can_manage_departments:false,staff_roles:[],department_memberships:[],assignments:[],memberships:[{entity,membership_role:'Organization Admin'}],audit_type_access:{[entity]:[kind]},allowed_assessment_types:[kind]});
 await mock(page,state,{audit_type_requests:[]});
 let writes=0;await page.route('**/api/method/ia_maturity.grc.api.request_audit_type',route=>{writes++;return route.fulfill({json:{message:{name:'REQ-NEW'}}})});
 await page.goto('/grc/customer/audit-access');
 await expect(page.getByText('Additional audit access needs two decisions:',{exact:false})).toBeVisible();
 await expect(page.getByText('No request is required to continue your current assessment.',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Request another audit type',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Request another audit type',exact:true});
 await expect(dialog).toContainText('You may cancel and continue your existing work.');
 await dialog.getByRole('button',{name:'Cancel',exact:true}).click();
 await expect(dialog).toHaveCount(0);expect(writes).toBe(0);
});

test('customer contributor sees administrator guidance instead of a failing request action',async({page})=>{
 await mock(page,session({kind:'Customer',home:'/grc/customer',memberships:[{entity,membership_role:'Contributor'}],allowed_assessment_types:['GRC'],audit_type_access:{[entity]:['GRC']}}),{audit_type_requests:[]});
 await page.goto('/grc/customer/audit-access');
 await expect(page.getByRole('button',{name:'Request another audit type',exact:true})).toHaveCount(0);
 await expect(page.getByText('Only an organization administrator can request another audit type.',{exact:false})).toBeVisible();
});

test('source manager approval makes the receiving decision explicit without claiming access is active',async({page})=>{
 const rows=[request()];await mock(page,session(),{audit_type_requests:rows,department_staff:[]});
 let sent:any;await page.route('**/api/method/ia_maturity.grc.api.decide_audit_type_request',route=>{sent=route.request().postDataJSON();rows[0].status='Pending Target Approval';rows[0].can_decide=false;return route.fulfill({json:{message:{status:'Pending Target Approval'}}})});
 await page.goto('/grc/auditor/audit-access');await page.getByRole('button',{name:'Approve',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Approve audit access',exact:true});
 await expect(dialog).toContainText('It does not activate access yet.');
 await dialog.getByLabel('Reason',{exact:true}).fill('Source department reviewed this request');
 await dialog.getByRole('button',{name:'Confirm',exact:true}).click();
 expect(sent).toMatchObject({name:'REQ-1',approve:true});
 await expect(page.getByText('Current department approved. Waiting for the receiving department manager; access is not active yet.')).toBeVisible();
 await expect(page.getByRole('button',{name:'Approve',exact:true})).toHaveCount(0);
});

test('receiving manager sees final access activation and can cancel a decision without writing',async({page})=>{
 await mock(page,session({department_memberships:[{department:'GRC',role:'Manager'}]}),{audit_type_requests:[request({status:'Pending Target Approval'})],department_staff:[]});
 await page.goto('/grc/auditor/audit-access');await page.getByRole('button',{name:'Approve',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Approve audit access',exact:true});
 await expect(dialog).toContainText('Approval activates the additional audit access.');
 await dialog.getByRole('button',{name:'Cancel',exact:true}).click();await expect(dialog).toHaveCount(0);
});

test('staff without the explicit decision capability cannot approve a visible request',async({page})=>{
 await mock(page,session(),{audit_type_requests:[request({can_decide:false})],department_staff:[]});
 await page.goto('/grc/auditor/audit-access');
 await expect(page.getByRole('button',{name:'Approve',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Reject',exact:true})).toHaveCount(0);
});

test('department manager cannot deactivate self or another manager and sees who can change those memberships',async({page})=>{
 await mock(page,session(),{audit_type_requests:[],department_staff:[{name:'DM-SELF',user:manager,department:'Internal Audit',role:'Manager',active:1},{name:'DM-OTHER',user:'other-manager@ux.example.test',department:'Internal Audit',role:'Manager',active:1},{name:'DM-REVIEW',user:'reviewer@ux.example.test',department:'Internal Audit',role:'Reviewer',active:1}]});
 await page.goto('/grc/auditor/audit-access');
 await expect(page.getByText('Only app administrators can change manager memberships.',{exact:false})).toBeVisible();
 const rows=page.getByRole('row');
 await expect(rows.filter({has:page.getByRole('cell',{name:manager,exact:true})}).getByRole('button',{name:'Deactivate',exact:true})).toBeDisabled();
 await expect(rows.filter({has:page.getByRole('cell',{name:'other-manager@ux.example.test',exact:true})}).getByRole('button',{name:'Deactivate',exact:true})).toBeDisabled();
 await expect(rows.filter({has:page.getByRole('cell',{name:'reviewer@ux.example.test',exact:true})}).getByRole('button',{name:'Deactivate',exact:true})).toBeEnabled();
});

test('manager with no customers gets next-step guidance and no empty onboarding form',async({page})=>{
 await mock(page,session({organizations:[],assignments:[],managed_entities:[]}),{operations_overview:overview({customers:[],auditors:[],assignments:[],customer_policies:{}})});
 await page.goto('/grc/auditor/oversight');
 await expect(page.getByText('Only customers in your authorized department management scope appear here.')).toBeVisible();
 await expect(page.getByRole('heading',{name:'No managed customers',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Request auditor onboarding',exact:true})).toBeDisabled();
 await expect(page.getByRole('link',{name:'Customer onboarding',exact:true}).last()).toHaveAttribute('href','/grc/auditor/onboarding');
 await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('manager assigns a first reviewer from the eligible department roster',async({page})=>{
 await mock(page,session(),{operations_overview:overview(),staff:[{name:'new-reviewer@ux.example.test',full_name:'New Reviewer',enabled:1}]});
 let sent:any;await page.route('**/api/method/ia_maturity.grc.api.assign_customer',route=>{sent=route.request().postDataJSON();return route.fulfill({json:{message:{name:'ASSIGN-NEW'}}})});
 await page.goto('/grc/auditor/oversight');await page.getByRole('button',{name:'Assign customer',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Customer assignment',exact:true});
 await expect(dialog).toContainText('assigning customer access alone does not allocate a review task.');
 await expect(dialog.getByRole('combobox',{name:'Auditor',exact:true})).toContainText('New Reviewer');
 await dialog.getByRole('combobox',{name:'Responsibility',exact:true}).click();await page.getByRole('option',{name:'Reviewer',exact:true}).click();
 await dialog.getByRole('button',{name:'Save changes',exact:true}).click();
 expect(sent).toMatchObject({entity,auditor:'new-reviewer@ux.example.test',responsibility:'Reviewer'});
});

test('locked ownership explains why manager assignment changes are unavailable',async({page})=>{
 await mock(page,session(),{operations_overview:overview({customers:[{...org,ownership_locked:true}]})});
 await page.goto('/grc/auditor/oversight');
 await expect(page.getByRole('button',{name:'Assign customer',exact:true})).toBeDisabled();
 await expect(page.getByText('Ownership locked; ask an app administrator to review staff access.')).toBeVisible();
});

test('manager waiting on an app administrator can inspect history but cannot submit an unauthorized decision',async({page})=>{
 const req={name:'OP-1',entity,kind:'Customer Assignment',status:'Pending',requested_by:'consultant@ux.example.test',step:1,payload:{entity},workflow:policy,decisions:[]};
 await mock(page,session(),{operations_overview:overview({requests:[req]})});
 await page.goto('/grc/auditor/oversight');await page.getByRole('tab',{name:'Approvals',exact:true}).click();await page.getByRole('button',{name:'Review request',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Review request',exact:true});
 await expect(dialog).toContainText('waiting for the reviewer responsible for its current approval stage.');
 await expect(dialog.getByRole('button',{name:'Submit decision',exact:true})).toHaveCount(0);
 await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
});

test('manager cannot approve own request and cancellation requires a reason',async({page})=>{
 const req={name:'OP-OWN',entity,kind:'Customer Assignment',status:'Pending',requested_by:manager,step:0,payload:{entity},workflow:policy,decisions:[]};
 await mock(page,session(),{operations_overview:overview({requests:[req]})});
 await page.goto('/grc/auditor/oversight');await page.getByRole('tab',{name:'Approvals',exact:true}).click();await page.getByRole('button',{name:'Review request',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Review request',exact:true});
 await expect(dialog).toContainText('A different authorized reviewer must decide your request.');
 await expect(dialog.getByLabel('Decision reason',{exact:true})).toHaveAttribute('required','');
 await dialog.getByRole('combobox',{name:'Decision',exact:true}).click();
 await expect(page.getByRole('option',{name:'Cancel request',exact:true})).toBeVisible();
 await expect(page.getByRole('option',{name:'Approve',exact:true})).toHaveCount(0);
 await expect(page.getByRole('option',{name:'Reject',exact:true})).toHaveCount(0);
 await page.keyboard.press('Escape');await dialog.getByRole('button',{name:'Close',exact:true}).last().click();
 await expect(dialog).toHaveCount(0);
});

test('reviewer can read follow-ups but sees no unusable add or edit action',async({page})=>{
 await mock(page,session({staff_roles:['GRC Reviewer'],can_operations:false,managed_entities:[],assignments:[{entity,responsibility:'Reviewer'}]}),{followups:[{name:'F-1',entity,note:'Call customer',assigned_to:manager,status:'Open',can_edit:false}]});
 await page.goto('/grc/auditor/followups');
 await expect(page.getByRole('button',{name:'Add follow-up',exact:true})).toBeDisabled();
 await expect(page.getByRole('button',{name:'Edit',exact:true})).toHaveCount(0);
 await expect(page.getByText('Creating or editing a follow-up requires customer management access',{exact:false})).toBeVisible();
});

test('manager can cancel an optional follow-up without completing required fields or saving',async({page})=>{
 await mock(page,session(),{followups:[]});
 let writes=0;await page.route('**/api/method/ia_maturity.grc.api.save_followup',route=>{writes++;return route.fulfill({json:{message:{name:'F-NEW'}}})});
 await page.goto('/grc/auditor/followups');await page.getByRole('button',{name:'Add follow-up',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Follow-up',exact:true});
 await expect(dialog.getByLabel('Note',{exact:true})).toHaveValue('');
 await dialog.getByRole('button',{name:'Cancel',exact:true}).click();await expect(dialog).toHaveCount(0);expect(writes).toBe(0);
});

test('read-only action explains the authorized next actor instead of presenting a save action',async({page})=>{
 await mock(page,session({kind:'Customer',home:'/grc/customer'}),{actions:{items:[{name:'ACTION-1',entity,finding_title:'Document controls',recommended_action:'Provide closure evidence',status:'Open',can_edit:false,can_verify:false}],total:1}});
 await page.goto('/grc/customer/actions');await page.getByRole('button',{name:'Open',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Improvement action',exact:true});
 await expect(dialog).toContainText('This action is read-only for your account.');
 await expect(dialog.getByRole('button',{name:'Save changes',exact:true})).toHaveCount(0);
 await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);
});

test('IA-only organization shows basic details and read-only IA issue guidance without a GRC profile tab',async({page})=>{
 await mock(page,session({staff_roles:['GRC Reviewer'],managed_entities:[],can_operations:false}),{organization_detail:detail(),issues:[{name:'I-1',title:'Document closure',status:'Open',rating:'Medium'}]});
 await page.goto('/grc/auditor/customers/'+encodeURIComponent(entity));
 await expect(page.getByRole('tab',{name:'Company profile',exact:true})).toHaveCount(0);
 await page.getByRole('tab',{name:'Audit issues',exact:true}).click();
 await expect(page.getByRole('button',{name:'Add issue',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Edit',exact:true})).toHaveCount(0);
 await expect(page.getByText('Issue records are read-only for your account.',{exact:false})).toBeVisible();
});

test('GRC organization offers its company profile and does not present IA Q13 issue controls',async({page})=>{
 await mock(page,session({audit_type_access:{[entity]:['GRC']}}),{organization_detail:detail({can_view_company_profile:true})});
 await page.goto('/grc/auditor/customers/'+encodeURIComponent(entity));
 await expect(page.getByRole('tab',{name:'Company profile',exact:true})).toBeVisible();
 await expect(page.getByRole('tab',{name:'Audit issues',exact:true})).toHaveCount(0);
});

test('customer dates and actions have meaningful empty states with a path back to assessments',async({page})=>{
 await mock(page,session({kind:'Customer',home:'/grc/customer'}),{activity:[],actions:{items:[],total:0}});
 await page.goto('/grc/customer/activity');await expect(page.getByRole('heading',{name:'No assessment dates yet',exact:true})).toBeVisible();
 await expect(page.getByText('Start an assessment to record its start date.',{exact:false})).toBeVisible();
 await page.goto('/grc/customer/actions');await expect(page.getByRole('heading',{name:'No improvement actions yet',exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'Assessments',exact:true}).last()).toHaveAttribute('href','/grc/customer/assessments');
});

test('Arabic mobile access stages fit and explain the second approval',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await mock(page,session({kind:'Customer',home:'/grc/customer',can_manage_departments:false,memberships:[{entity,membership_role:'Organization Admin'}]}),{audit_type_requests:[request({status:'Pending Target Approval',can_decide:false})]});
 await page.goto('/grc/customer/audit-access');await page.getByRole('button',{name:'العربية',exact:true}).click();
 await expect(page.getByText('وافق القسم الحالي. الطلب بانتظار مدير القسم المستقبِل، ولم يُفعّل الوصول بعد.')).toBeVisible();
 const size=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}));expect(size.width).toBeLessThanOrEqual(size.viewport);
 await page.screenshot({path:'test-results/ux-manager-access-arabic-mobile.png',fullPage:true,animations:'disabled'});
});
