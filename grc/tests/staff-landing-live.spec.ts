import {test,expect,type Page} from '@playwright/test';
import {execFileSync} from 'node:child_process';

// Explicit local-only opt-in. Fixtures validate the muted disposable site before
// any writes. Never capture authentication fields, passwords, OTPs or sessions.
test.skip(process.env.GRC_RUN_STAFF_LANDING_LIVE!=='1','Requires exclusive guarded local staff-landing acceptance.');
test.describe.configure({mode:'serial'});
test.use({trace:'off',video:'off',screenshot:'off'});

const run='landing20261112';
type Account={email:string;password:string};
type State={staff:Record<'ia'|'grc',Record<'consultant'|'reviewer'|'manager',Account>>};
let state:State;

function guard(baseURL:string|undefined){
 const url=new URL(baseURL||'');
 expect(['127.0.0.1','localhost'].includes(url.hostname),'Only a loopback demo server is allowed.').toBe(true);
 expect(url.port,'Use the guarded local acceptance server.').toBe('8007');
}
function setup():State{
 try{
  return JSON.parse(execFileSync('/home/frappe/frappe-bench/env/bin/python',[
   '../scripts/demo_cycle_fixture.py','setup',run
  ],{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim());
 }catch{throw new Error('Guarded landing fixture setup failed; inspect privately without publishing its output.');}
}
async function login(page:Page,account:Account){
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.goto('/login?staff=1');
 await page.getByLabel('Email or username',{exact:true}).fill(account.email);
 await page.getByLabel('Password',{exact:true}).fill(account.password);
 const pending=page.waitForResponse(response=>response.url().includes('/api/method/login')&&response.request().method()==='POST');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 const response=await pending;
 expect(response.status(),'Reserved staff password login must succeed.').toBe(200);
 expect(Boolean((await response.json()).verification),'Fresh staff inherit disabled-by-default 2FA.').toBe(false);
 await expect(page).toHaveURL(/\/grc\/auditor$/);
 await expect(page.locator('.app-shell .main-content')).toBeVisible();
 if((page.viewportSize()?.width||1440)>850)await expect(page.getByRole('navigation',{name:'Main navigation'})).toBeVisible();
 await expect(page.locator('.navbar')).toHaveCount(0);
 await expect(page.getByRole('link',{name:'Staff Desk',exact:true})).toHaveCount(0);
 // A first-visit tour is optional: Escape must close it without any selection.
 await expect(page.getByRole('button',{name:'Close tour',exact:true})).toBeVisible();
 await page.keyboard.press('Escape');
 await expect(page.getByRole('button',{name:'Close tour',exact:true})).toHaveCount(0);
 await page.evaluate(email=>localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(email)+':skip-auto','1'),account.email);
}
test.beforeAll(({baseURL})=>{guard(baseURL);state=setup()});

for(const [department,label] of [['ia','Internal Audit'],['grc','GRC']] as const){
 test(`live: fresh ${label} consultant enters the custom workspace with optional guidance`,async({page})=>{
  test.setTimeout(90000);
  await login(page,state.staff[department].consultant);
  await expect(page.locator('.brand')).toHaveText(label);
  await expect(page.locator('.topbar-title')).toContainText(label);
  if(department==='ia')await expect(page.locator('.brand')).not.toContainText('GRC');
  const welcome=page.getByRole('region',{name:'Getting started',exact:true});
  await expect(welcome).toBeVisible();
  await expect(welcome).toContainText('Your workspace is ready. No customer organizations are assigned to you yet.');
  await expect(welcome).toContainText('This guidance is optional.');
  await expect(page.getByRole('heading',{name:'No customers assigned',exact:true})).toBeVisible();
  await expect(page.getByRole('combobox',{name:'Organization',exact:true})).toHaveCount(0);
  await expect(page.getByRole('combobox',{name:'Assessment',exact:true})).toHaveCount(0);
  await expect(page.getByRole('combobox',{name:'Status',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Start assessment',exact:true})).toHaveCount(0);
  await page.screenshot({path:`test-results/staff-landing-${department}-desktop.png`,fullPage:true,animations:'disabled'});

  await welcome.getByRole('button',{name:'Dismiss getting started',exact:true}).click();
  await expect(welcome).toHaveCount(0);
  await page.reload();
  await expect(welcome).toHaveCount(0);
  await page.getByRole('button',{name:'Getting started',exact:true}).click();
  await expect(welcome).toBeVisible();
  await welcome.getByRole('button',{name:'Dismiss getting started',exact:true}).focus();
  await page.keyboard.press('Escape');
  await expect(welcome).toHaveCount(0);

  const redirect=await page.request.get('/app/grc-staff',{maxRedirects:0,headers:{Accept:'text/html'}});
  expect(redirect.status(),'Old staff bookmarks must redirect without rendering ERP Desk.').toBe(302);
  expect(redirect.headers().location).toBe('/grc/auditor');
  expect(redirect.headers()['cache-control']).toContain('no-store');
  await page.goto('/app/grc-staff');
  await expect(page).toHaveURL(/\/grc\/auditor$/);
  await expect(page.getByRole('navigation',{name:'Main navigation'})).toBeVisible();
  await page.getByRole('button',{name:'Getting started',exact:true}).click();
  await welcome.getByRole('link',{name:'Open Customer onboarding',exact:true}).click();
  await expect(page).toHaveURL(/\/grc\/auditor\/onboarding$/);
  await page.getByRole('button',{name:'Invite customer',exact:true}).click();
  const invitation=page.getByRole('dialog',{name:'Invite customer',exact:true});
  await expect(invitation.getByLabel('Customer email',{exact:true})).toBeVisible();
  await expect(invitation.getByLabel('Company',{exact:true})).toBeVisible();
  await expect(invitation.getByRole('combobox',{name:'Assessment type',exact:true})).toContainText(label);
  await invitation.getByRole('button',{name:'Close',exact:true}).click();
  await expect(invitation).toHaveCount(0);
  // No invitation or customer/assessment is created by this navigation check.
 });
}

test('live: an unassigned reviewer gets assignment guidance without empty required selectors',async({page})=>{
 await login(page,state.staff.ia.reviewer);
 const welcome=page.getByRole('region',{name:'Getting started',exact:true});
 await expect(welcome).toContainText('Customers and assessments appear after a department manager assigns you.');
 await expect(page.getByRole('heading',{name:'No customers assigned',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Start assessment',exact:true})).toHaveCount(0);
 await expect(page.getByRole('combobox',{name:'Organization',exact:true})).toHaveCount(0);
 await expect(page.getByRole('combobox',{name:'Assessment',exact:true})).toHaveCount(0);
 // Invitation visibility follows the server capability; departmental reviewers
 // are currently permitted to invite by the original department-only rule.
 const response=await page.request.get('/api/method/ia_maturity.grc.api.bootstrap');
 expect(response.status()).toBe(200);
 const session=(await response.json()).message;
 await expect(welcome.getByRole('link',{name:'Open Customer onboarding',exact:true})).toHaveCount(session.can_invite_customers?1:0);
});

test('live: Arabic mobile staff guidance fits and closes with the keyboard',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await login(page,state.staff.grc.reviewer);
 await page.getByRole('button',{name:'العربية',exact:true}).click();
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 const welcome=page.getByRole('region',{name:'البدء',exact:true});
 await expect(welcome).toBeVisible();
 await expect(welcome).toContainText('هذه الإرشادات اختيارية.');
 await expect(page.getByRole('combobox')).toHaveCount(0);
 const size=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}));
 expect(size.width).toBeLessThanOrEqual(size.viewport);
 await page.screenshot({path:'test-results/staff-landing-arabic-mobile.png',fullPage:true,animations:'disabled'});
 await welcome.getByRole('button',{name:'إغلاق إرشادات البدء',exact:true}).focus();
 await page.keyboard.press('Escape');
 await expect(welcome).toHaveCount(0);
 await page.getByRole('button',{name:'البدء',exact:true}).click();
 await expect(welcome).toBeVisible();
});
