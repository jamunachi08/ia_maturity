import {test,expect,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const credentials=JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'));
test.use({trace:'off',video:'off'});
async function login(page:Page,email='admin@grc.example.test'){
 await page.goto('/login?staff=1');await page.getByLabel('Email or username').fill(email);await page.getByLabel('Password',{exact:true}).fill(credentials[email]);
 const response=page.waitForResponse(r=>r.url().includes('/api/method/login')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 if((await(await response).json()).verification){await expect(page.getByLabel('Authenticator code')).toBeVisible();const otp=execFileSync('../../../env/bin/python',['../scripts/local_test_otp.py',email],{encoding:'utf8'}).trim();await page.getByLabel('Authenticator code').fill(otp);await page.getByRole('button',{name:'Verify and continue'}).click()}
 await expect(page).toHaveURL(/\/grc\/auditor$/);
}
test('first visit, per-page skip, replay, automatic opt-out and Arabic',async({page})=>{
 await login(page);const tour=page.getByRole('dialog',{name:'Your workspace'});await expect(tour).toBeVisible();await expect(page.locator('.page-tour-highlight')).toBeVisible();
 await tour.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByRole('dialog',{name:'Navigation'})).toBeVisible();
 await page.getByRole('button',{name:'Skip tour',exact:true}).click();await page.reload();await expect(page.getByRole('button',{name:'Take page tour'})).toBeEnabled();await expect(page.locator('.page-tour-dialog')).toHaveCount(0);
 await page.getByRole('button',{name:'Take page tour'}).click();await expect(page.getByRole('dialog',{name:'Your workspace'})).toBeVisible();await page.getByRole('button',{name:'Skip tour',exact:true}).click();
 await page.getByRole('link',{name:'Assessments',exact:true}).click();await expect(page.getByRole('dialog',{name:'Assessments'})).toBeVisible();await page.getByRole('button',{name:'Skip automatic tours'}).click();
 await page.getByRole('link',{name:'Actions',exact:true}).click();await expect(page.getByRole('button',{name:'Take page tour'})).toBeEnabled();await expect(page.locator('.page-tour-dialog')).toHaveCount(0);
 await page.getByRole('button',{name:'العربية'}).click();await page.getByRole('button',{name:'جولة الصفحة'}).click();await expect(page.getByRole('dialog',{name:'إجراءات التحسين'})).toBeVisible();await expect(page.locator('html')).toHaveAttribute('dir','rtl');await page.keyboard.press('Escape');await expect(page.locator('.page-tour-dialog')).toHaveCount(0);
});
test('customer onboarding and mobile tour remain usable',async({page})=>{
 await page.setViewportSize({width:390,height:844});await login(page);
 await page.route('**/api/method/ia_maturity.grc.api.bootstrap',route=>route.fulfill({json:{message:{enabled:true,kind:'Customer',user:'tour-customer@example.test',full_name:'Tour Customer',home:'/grc/customer',organizations:[]}}}));
 await page.goto('/grc/customer');await expect(page.getByRole('dialog',{name:'Your workspace'})).toBeVisible();await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByRole('dialog',{name:'Navigation'})).toBeVisible();
 await page.getByRole('button',{name:'Skip tour',exact:true}).click();await expect(page.getByRole('button',{name:'Take page tour'})).toBeInViewport();await page.screenshot({path:'test-results/page-tour-mobile.png'});
});

test('assessment detail explains sections and answers when records exist',async({page})=>{
 await login(page);await page.getByRole('button',{name:'Skip tour',exact:true}).click();
 await page.getByRole('link',{name:'Assessments',exact:true}).click();await page.getByRole('button',{name:'Skip tour',exact:true}).click();
 const record=page.locator('.record-link').first();test.skip(await record.count()===0,'No local assessment is available');await record.click();
 await expect(page.getByRole('dialog',{name:'Assessment and status'})).toBeVisible();await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByRole('dialog',{name:'Sections'})).toBeVisible();await expect(page.locator('.page-tour-highlight')).toBeVisible();
 await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByRole('dialog',{name:'Progress and live score'})).toBeVisible();await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByRole('dialog',{name:'Answer a question'})).toBeVisible();
});
