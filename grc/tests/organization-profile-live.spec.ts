import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';

// Root schedules this serially after preparing a disposable local organization.
// No route mocks: this verifies the browser/API/database connection.
test('live: organization profile saves, reloads and restores its original values',async({page,baseURL})=>{
 test.skip(process.env.GRC_RUN_PROFILE_LIVE!=='1','Enable only after preparing the reserved local profile fixture.');
 expect(new URL(baseURL!).hostname).toMatch(/^(127\.0\.0\.1|localhost)$/);
 const entity='Organization Profile Browser Acceptance';
 const credentials=JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'));
 await page.addInitScript(()=>localStorage.setItem('grc-language','en'));
 await page.goto('/login');
 await page.getByLabel('Email or username').fill('customer@alpha.example.test');
 await page.getByLabel('Password',{exact:true}).fill(credentials['customer@alpha.example.test']);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page).toHaveURL(/\/grc\/customer$/);
 const getProfile=async()=>{
  const response=await page.request.get('/api/method/ia_maturity.grc.api.organization_profile',{params:{entity}});
  const body=await response.json();
  const diagnostic={status:response.status(),type:body.exc_type||String(body.exception||'').split(':')[0],message:typeof body.message==='string'?body.message.slice(0,300):undefined};
  expect(response.ok(),JSON.stringify(diagnostic)).toBeTruthy();return body.message;
 };
 const original=await getProfile();
 expect(original.complete,'Prepare a valid disposable profile before running this live test.').toBe(true);
 try{
  await page.goto('/grc/customer/organization/'+encodeURIComponent(entity));
  await page.getByRole('tab',{name:'Company profile',exact:true}).click();
  const form=page.getByTestId('organization-profile');await expect(form).toBeVisible();
  await form.getByLabel('Other regulator (optional)',{exact:true}).fill('Reserved browser round-trip marker');
  const saved=page.waitForResponse(r=>r.url().includes('api.save_organization_profile')&&r.request().method()==='POST');
  await form.getByRole('button',{name:'Save profile',exact:true}).click();
  expect((await saved).ok()).toBeTruthy();
  await expect(form.getByRole('status')).toContainText('Profile saved.');
  await page.reload();await page.getByRole('tab',{name:'Company profile',exact:true}).click();
  await expect(page.getByTestId('organization-profile').getByLabel('Other regulator (optional)',{exact:true})).toHaveValue('Reserved browser round-trip marker');
  const persisted=await getProfile();
  expect(persisted.profile.other_regulator).toBe('Reserved browser round-trip marker');
  expect(persisted.profile.cr_number).toBe(original.profile.cr_number);
 }finally{
  const current=await getProfile();
  const restored=await page.evaluate(async args=>{
   const response=await fetch('/api/method/ia_maturity.grc.api.save_organization_profile',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':(window as any).csrf_token||''},body:JSON.stringify(args)});
   return {status:response.status,data:await response.json()};
  },{entity,data:original.profile,modified:current.modified});
  expect(restored.status).toBe(200);
  expect(restored.data.message.profile.other_regulator).toBe(original.profile.other_regulator);
 }
});
