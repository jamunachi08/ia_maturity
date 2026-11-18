import {test,expect,type Page} from '@playwright/test';

const user='welcome-consultant@example.test';
async function mockStaff(page:Page,{department='Internal Audit',role='Consultant',invite=true,manager=false,admin=false,organizations=false,language='en'}:{department?:string;role?:string;invite?:boolean;manager?:boolean;admin?:boolean;organizations?:boolean;language?:string}={}){
 await page.addInitScript(({user,language})=>{localStorage.setItem('grc-language',language);localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(user)+':skip-auto','1')},{user,language});
 const org=organizations?[{name:'Assigned company',entity_name:'Assigned company'}]:[];
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap**',route=>route.fulfill({json:{message:{enabled:true,user,full_name:'Demo Consultant',kind:'Auditor',is_admin:admin,home:'/grc/auditor',organizations:org,department_memberships:[{department,role}],staff_roles:['GRC '+role],can_invite_customers:invite,can_manage_departments:manager,can_operations:manager,assignments:organizations?[{entity:'Assigned company',responsibility:role}]:[{entity:'Unavailable company',responsibility:role}]}}}));
 await page.route('**/api/method/ia_maturity.grc.api.dashboard**',route=>route.fulfill({json:{message:{assessments:[],counts:{},total:0,page:1,page_size:15,customer_count:org.length,overdue:0,overdue_actions_count:0,overdue_actions:[],recent_activity:[],needs_reassignment:0,results_visibility:'Preliminary scorecard'}}}));
 await page.route('**/api/method/ia_maturity.grc.api.onboarding_invitations**',route=>route.fulfill({json:{message:[]}}));
}

test('fresh IA consultant sees explanation and invite action without empty required selectors',async({page})=>{
 await mockStaff(page);
 await page.goto('/grc/auditor');
 await expect(page.getByRole('heading',{name:'Getting started · Internal Audit',exact:true})).toBeVisible();
 await expect(page.getByText('Your workspace is ready. No customer organizations are assigned to you yet.')).toBeVisible();
 await expect(page.getByRole('link',{name:'Open Customer onboarding',exact:true})).toHaveAttribute('href','/grc/auditor/onboarding');
 await expect(page.getByRole('combobox',{name:'Organization',exact:true})).toHaveCount(0);
 await expect(page.getByRole('combobox',{name:'Status',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Start assessment',exact:true})).toHaveCount(0);
 await expect(page.getByRole('dialog')).toHaveCount(0);
 await expect(page.locator('.brand span')).toHaveText('Internal Audit');
 await page.getByRole('link',{name:'Open Customer onboarding',exact:true}).click();
 await expect(page).toHaveURL(/\/grc\/auditor\/onboarding$/);
 await expect(page.getByRole('button',{name:'Invite customer',exact:true})).toBeVisible();
});

test('guidance closes with keyboard, stays dismissed on reload, and can reopen',async({page})=>{
 await mockStaff(page);
 await page.goto('/grc/auditor');
 const close=page.getByRole('button',{name:'Dismiss getting started',exact:true});
 await close.focus();await page.keyboard.press('Enter');
 const reopen=page.getByRole('button',{name:'Getting started',exact:true});
 await expect(reopen).toBeFocused();
 await expect(page.getByRole('region',{name:'Getting started',exact:true})).toHaveCount(0);
 await page.reload();await expect(reopen).toBeVisible();
 await reopen.click();await expect(close).toBeVisible();
 await close.focus();await page.keyboard.press('Escape');await expect(reopen).toBeFocused();
});

test('reviewer sees assignment guidance and only permitted invitation actions',async({page})=>{
 await mockStaff(page,{role:'Reviewer',invite:false});
 await page.goto('/grc/auditor');
 await expect(page.getByText('Customers and assessments appear after a department manager assigns you. If you are waiting for an assignment, contact your department manager.')).toBeVisible();
 await expect(page.getByRole('link',{name:'Open Customer onboarding',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Start assessment',exact:true})).toHaveCount(0);
 await expect(page.getByRole('link',{name:'Manage customer assignments',exact:true})).toHaveCount(0);
});

test('manager gets actual department and assignment controls',async({page})=>{
 await mockStaff(page,{role:'Manager',manager:true});
 await page.goto('/grc/auditor');
 await expect(page.getByRole('link',{name:'Manage customer assignments',exact:true})).toHaveAttribute('href','/grc/auditor/oversight');
 await expect(page.getByRole('link',{name:'Manage department access',exact:true})).toHaveAttribute('href','/grc/auditor/audit-access');
 await expect(page.getByRole('link',{name:'Assign customer',exact:true})).toHaveCount(0);
});

test('GRC consultant welcome uses GRC department context',async({page})=>{
 await mockStaff(page,{department:'GRC'});
 await page.goto('/grc/auditor');
 await expect(page.getByRole('heading',{name:'Getting started · GRC',exact:true})).toBeVisible();
 await expect(page.locator('.brand span')).toHaveText('GRC');
 await expect(page.getByRole('heading',{name:'Getting started · Internal Audit',exact:true})).toHaveCount(0);
});

test('assigned staff filters are explicitly optional',async({page})=>{
 await mockStaff(page,{organizations:true});
 await page.goto('/grc/auditor');
 await expect(page.getByRole('button',{name:'Getting started',exact:true})).toBeVisible();
 await expect(page.getByRole('combobox',{name:'Organization',exact:true})).toBeVisible();
 await expect(page.getByText('Filters are optional. Leave All organizations and All statuses selected to see all work available to you.')).toBeVisible();
 await expect(page.getByRole('button',{name:'Start assessment',exact:true})).toBeVisible();
});

test('Arabic mobile guidance has visible close/reopen controls without page overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await mockStaff(page,{language:'ar'});
 await page.goto('/grc/auditor');
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 const close=page.getByRole('button',{name:'إغلاق إرشادات البدء',exact:true});
 await expect(close).toBeVisible();
 await expect(page.getByRole('link',{name:'فتح تهيئة العملاء',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/staff-welcome-arabic-mobile.png',fullPage:true,animations:'disabled'});
 await close.click();await page.getByRole('button',{name:'البدء',exact:true}).click();await expect(close).toBeVisible();
});
