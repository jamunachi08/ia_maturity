import {test, expect, Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const credentials = JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json', 'utf8'));
async function login(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel('Email or username').fill(email);
  await page.getByLabel('Password', {exact:true}).fill(credentials[email]);
  await page.getByRole('button', {name:'Sign in',exact:true}).click();
  if(email !== 'erp@grc.example.test') {
    await expect(page.getByLabel('Authenticator code')).toBeVisible();
    const otp = execFileSync('/home/frappe/frappe-bench/env/bin/python', ['../scripts/local_test_otp.py', email], {encoding:'utf8'}).trim();
    await page.getByLabel('Authenticator code').fill(otp);
    await page.getByRole('button', {name:'Verify and continue'}).click();
    await expect(page).toHaveURL(/\/grc\/auditor$/);
  }
}
test('website, real emailed code, organization, save/resume, assignment, review and PDF release', async({page, browser})=>{
  test.setTimeout(120000);
  const id = Date.now().toString(36), email = 'grc-journey-'+id+'@example.test', organization = 'Journey acceptance '+id;
  const errors: string[] = []; page.on('pageerror', e=>errors.push(e.message));
  try {
  await page.goto('/');
  await expect(page.getByRole('heading',{name:/Stronger governance/})).toBeVisible();
  await page.getByRole('link',{name:'Create an account',exact:true}).first().click();
  await expect(page).toHaveURL(/\/signup$/);
  await page.reload();
  await page.getByLabel('Full name').fill('Journey Test Customer');
  await page.getByLabel('Email',{exact:true}).fill(email);
  await expect(page.locator('.segmented')).toHaveCount(0);
  await page.getByLabel('Organization name').fill(organization);
  await page.getByRole('combobox',{name:'Sector',exact:true}).click();
  await page.getByRole('option',{name:'Manufacturing',exact:true}).click();
  await page.getByRole('checkbox').check();
  await page.getByRole('button',{name:'Send verification email',exact:true}).click();
  await expect(page.getByLabel('Verification code')).toBeVisible();
  function verification(mode:string){return execFileSync('/home/frappe/frappe-bench/env/bin/python',['../scripts/local_verification_code.py',email,mode],{encoding:'utf8'}).trim()}
  expect(verification('status')).toBe('pending');
  const link=new URL(verification('link'));
  await page.goto(link.pathname+link.search);
  await expect(page.getByRole('heading',{name:'Verify your email',exact:true})).toBeVisible();
  expect(verification('status')).toBe('pending'); // Loading or scanning the URL cannot create an account.
  await page.getByRole('button',{name:'Verify email and continue',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Your assessments'})).toBeVisible();
  expect(verification('status')).toBe('verified');
  await page.getByRole('button',{name:'Start assessment',exact:true}).click();
  await page.getByRole('dialog').getByRole('button',{name:'Start assessment',exact:true}).click();
  await expect(page.locator('.question-card')).toHaveCount(3);
  const assessmentURL = page.url(), name = assessmentURL.split('/').pop()!;
  for(let section=0; section<6; section++){
    if(section===1){
      await expect(page.locator('.save-state')).toHaveText(/Saved/);
      await page.reload();
      await expect(page.locator('.question-card input[value="C"]:checked')).toHaveCount(3);
      await page.getByRole('button',{name:'Next section',exact:true}).click();
    }
    const radios = page.locator('.question-card input[value="C"]:enabled');
    for(let i=0;i<await radios.count();i++) await radios.nth(i).check();
    if(section===0) await page.locator('.question-card textarea').first().fill('Saved and resumed through the browser.');
    await expect(page.locator('.save-state')).toHaveText(/Saved/);
    if(section<5) await page.getByRole('button',{name:'Next section',exact:true}).click();
  }
  await expect(page.locator('.assessment-progress')).toContainText('20/20');
  await page.getByRole('button',{name:'Submit for review',exact:true}).click();
  await expect(page.locator('.page-title')).toContainText('Submitted');
  await expect(page.getByRole('link',{name:'Download PDF'})).toHaveCount(0);
  const adminContext=await browser.newContext(), admin=await adminContext.newPage();
  await login(admin,'admin@grc.example.test');
  await admin.getByRole('link',{name:'Customer assignments',exact:true}).click();
  await admin.getByRole('combobox',{name:'Organization',exact:true}).click();
  await admin.getByRole('option',{name:organization,exact:true}).click();
  for(const [email,role] of [['auditor@grc.example.test','Consultant'],['reviewer@grc.example.test','Reviewer']]){
    await admin.getByRole('button',{name:'Assign customer',exact:true}).click();
    const dialog=admin.getByRole('dialog');
    await dialog.getByRole('combobox',{name:'Auditor',exact:true}).click();
    await admin.getByRole('option',{name:new RegExp(email.replaceAll('.','\\.'))}).click();
    await dialog.getByRole('combobox',{name:'Responsibility',exact:true}).click();
    await admin.getByRole('option',{name:role,exact:true}).click();
    await dialog.getByRole('button',{name:'Save changes',exact:true}).click();
    await expect(dialog).toHaveCount(0);
  }
  await admin.goto('/grc/auditor/assessments/'+name);
  await admin.getByRole('button',{name:'Assign team',exact:true}).click();
  for(const [role,email] of [['Consultant','auditor@grc.example.test'],['Reviewer','reviewer@grc.example.test']]){
    await admin.getByRole('dialog').getByRole('combobox',{name:role,exact:true}).click();
    await admin.getByRole('option',{name:email,exact:true}).click();
  }
  await admin.getByRole('dialog').getByRole('button',{name:'Save changes',exact:true}).click();
  await expect(admin.getByRole('dialog')).toHaveCount(0);
  const reviewerContext=await browser.newContext(), reviewer=await reviewerContext.newPage();
  await login(reviewer,'reviewer@grc.example.test');
  await reviewer.goto('/grc/auditor/assessments/'+name);
  for(const action of ['Begin review','Approve assessment','Release report']){
    await reviewer.getByRole('button',{name:action,exact:true}).click();
    const dialog=reviewer.getByRole('dialog');
    if(action!=='Release report') await dialog.getByLabel('Review comment').fill('Acceptance test review completed.');
    await dialog.getByRole('button',{name:'Confirm',exact:true}).click();
    await expect(dialog).toHaveCount(0);
  }
  await page.reload();
  await expect(page.getByText('Approved report',{exact:true})).toBeVisible();
  await expect(page.locator('.score-value')).toContainText('75');
  const pdfLink=page.getByRole('link',{name:'Download PDF',exact:true});
  await expect(pdfLink).toBeVisible();
  const pdf=await page.request.get((await pdfLink.getAttribute('href'))!);
  expect(pdf.status()).toBe(200);
  expect(pdf.headers()['content-type']).toContain('pdf');
  expect((await pdf.body()).subarray(0,5).toString()).toBe('%PDF-');
  await page.getByRole('button',{name:'Email report',exact:true}).click();
  await expect(page.getByRole('dialog').getByLabel('Recipient')).toHaveValue(email);
  await page.getByRole('button',{name:'Send report link',exact:true}).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('status')).toContainText('Report email queued.');
  await page.screenshot({path:'test-results/journey-released.png',fullPage:true});
  expect(errors).toEqual([]);
  await adminContext.close(); await reviewerContext.close();
  } finally {
    execFileSync('/home/frappe/frappe-bench/env/bin/python',['../scripts/local_journey_cleanup.py',email]);
  }
});
test('Saudi landing navigation, Arabic mobile, and isolated ERP demo pages',async({page})=>{
  await page.goto('/');
  for(const path of ['services','catalogue','frameworks','about','resources','faq','contact','privacy','terms']){
    await page.goto('/grc-site/'+path); await expect(page.locator('main h1')).toBeVisible();
    await expect(page.locator('main')).not.toContainText('Page not found');
    await page.reload(); await expect(page.locator('main h1')).toBeVisible();
  }
  await page.goto('/');
  await page.getByRole('button',{name:'العربية',exact:true}).click();
  await expect(page.locator('html')).toHaveAttribute('dir','rtl');
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/landing-mobile-arabic.png',fullPage:true});
  await page.getByRole('button',{name:'English',exact:true}).click();
  await page.getByRole('button',{name:'Menu',exact:true}).click();
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Services',exact:true}).click();
  await expect(page.locator('main h1')).toHaveText('Services built around accountable assurance');
  await page.setViewportSize({width:1440,height:1000});
  await login(page,'erp@grc.example.test');
  await expect(page).toHaveURL(/\/(app|desk)/);
  for(const kind of ['customer','auditor']){
    await page.goto('/grc/demo/'+kind);
    await expect(page.getByText(/^Fictional, read-only demonstration/)).toContainText('Fictional');
    await page.reload(); await expect(page.getByText(/^Fictional, read-only demonstration/)).toBeVisible();
    await page.screenshot({path:'test-results/demo-'+kind+'.png',fullPage:true});
    await expect(page.getByRole('link',{name:'Download PDF'})).toHaveCount(0);
  }
});
