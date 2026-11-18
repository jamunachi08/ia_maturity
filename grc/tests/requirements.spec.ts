import {test,expect,Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const credentials=JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'));
async function login(page:Page,email:string,staff=false){
 await page.goto(staff?'/login?staff=1':'/login');
 await page.getByLabel('Email or username').fill(email);
 await page.getByLabel('Password',{exact:true}).fill(credentials[email]);
 const response=page.waitForResponse(r=>r.url().includes('/api/method/login')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 if((await(await response).json()).verification){
  await expect(page.getByLabel('Authenticator code')).toBeVisible();
  const otp=execFileSync('/home/frappe/frappe-bench/env/bin/python',['../scripts/local_test_otp.py',email],{encoding:'utf8'}).trim();
  await page.getByLabel('Authenticator code').fill(otp);
  await page.getByRole('button',{name:'Verify and continue'}).click();
 }
}
test('neutral registration offers sign-in, recovery and cooldown resend',async({page})=>{
 await page.clock.install();
 let requests=0;
 await page.route('**/api/method/ia_maturity.grc.auth.request_code',async route=>{
  requests++;
  await route.fulfill({json:{message:{message:'If eligible, you will receive a verification email.',resend_after_seconds:60,expires_in_seconds:900}}});
 });
 await page.goto('/signup');
 await expect(page.getByRole('link',{name:'Already registered? Sign in',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Forgot password?',exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'Staff sign in',exact:true})).toHaveAttribute('href','/login?staff=1');
 await page.getByLabel('Email',{exact:true}).fill('someone@example.test');
 await page.getByLabel('Full name').fill('New Customer');
 await page.getByLabel('Organization name').fill('New Customer Organization');
 await page.getByRole('combobox',{name:'Sector',exact:true}).click();
 await page.getByRole('option',{name:'Healthcare',exact:true}).click();
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Send verification email',exact:true}).click();
 await expect(page.getByText('If eligible, you will receive a verification email.',{exact:false})).toBeVisible();
 await expect(page.getByRole('button',{name:/Resend code/})).toBeDisabled();
 await expect(page.getByText(/Code expires in 15/)).toBeVisible();
 await page.clock.fastForward(61000);
 await expect(page.getByRole('button',{name:'Resend code',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Resend code',exact:true}).click();
 expect(requests).toBe(2);
 await page.getByRole('button',{name:'Forgot password?',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Password recovery',exact:true})).toBeVisible();
});
test('staff sign-in opens the custom workspace without native Desk chrome',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await login(page,'auditor@grc.example.test',true);
 await expect(page).toHaveURL(/\/grc\/auditor$/);
 await expect(page.getByRole('heading',{name:'My review queue',exact:true})).toBeVisible();
 await expect(page.getByRole('navigation',{name:'Main navigation'})).toBeVisible();
 await expect(page.getByRole('link',{name:'Staff Desk',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Open staff workspace',exact:true})).toHaveCount(0);
 await page.screenshot({path:'test-results/requirements-staff-workspace.png',fullPage:true});
 expect(errors).toEqual([]);
});
test('organization switcher scopes dashboard and persists after refresh',async({page})=>{
 await login(page,'admin@grc.example.test');
 await expect(page).toHaveURL(/\/grc\/auditor$/);
 const selector=page.getByRole('combobox',{name:'Switch organization',exact:true});
 const scoped=page.waitForResponse(r=>r.url().includes('ia_maturity.grc.api.dashboard')&&new URL(r.url()).searchParams.get('entity')==='Al Noor Industries');
 await selector.click();
 await page.getByRole('option',{name:'Al Noor Industries',exact:true}).click();
 await expect(selector).toContainText('Al Noor Industries');
 const data=await (await scoped).json();
 expect(data.message.assessments.every((a:any)=>a.entity==='Al Noor Industries')).toBeTruthy();
 await page.reload();
 await expect(selector).toContainText('Al Noor Industries');
 await page.getByRole('link',{name:'Assessments',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Customer portfolio',exact:true})).toBeVisible();
 await expect(page.getByRole('combobox',{name:'Organization',exact:true})).toContainText('Al Noor Industries');
 await page.screenshot({path:'test-results/requirements-org-switcher.png',fullPage:true});
});
test('customer notification settings separate mandatory and optional email',async({page})=>{
 await login(page,'customer@alpha.example.test');
 await expect(page).toHaveURL(/\/grc\/customer$/);
 await page.getByRole('link',{name:'Notifications',exact:true}).click();
 await expect(page.getByRole('combobox',{name:'Optional reminders',exact:true})).toBeVisible();
 await expect(page.getByRole('combobox',{name:'Optional status updates',exact:true})).toBeVisible();
 await expect(page.getByText('Verification codes, account security emails, invitations and clarification requests are mandatory and cannot be disabled.',{exact:true})).toBeVisible();
});
