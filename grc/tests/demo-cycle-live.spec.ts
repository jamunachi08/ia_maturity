import {test,expect,type Page,type Browser} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdirSync,writeFileSync} from 'node:fs';

// Explicit opt-in: real requests, database records, native email MIME, and PDFs.
// The loopback SMTP acceptance server replaces transport only for reserved users.
test.skip(process.env.GRC_RUN_DEMO_CYCLE!=='1','Requires the guarded local demo acceptance server and exclusive fixture slot.');
test.describe.configure({mode:'serial'});
test.use({trace:'off',video:'off'});
const run=process.env.GRC_DEMO_RUN||Date.now().toString(36);
const python='/home/frappe/frappe-bench/env/bin/python';
type Account={email:string;password:string};
type Staff={ia:Record<string,Account>;grc:Record<string,Account>};
let staff:Staff;
const records:Record<string,{email:string;company:string;name:string}>={};
function fixture(command:string,...args:string[]){
 return JSON.parse(execFileSync(python,['../scripts/demo_cycle_fixture.py',command,run,...args],{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim());
}
async function rpc(page:Page,method:string,args:Record<string,unknown>={},post=false){
 return page.evaluate(async({method,args,post})=>{
  const url='/api/method/ia_maturity.grc.api.'+method;
  const response=await fetch(post?url:url+'?'+new URLSearchParams(Object.entries(args).map(([k,v])=>[k,String(v)])).toString(),{method:post?'POST':'GET',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.csrf_token||''},...(post?{body:JSON.stringify(args)}:{})});
  return {status:response.status,data:await response.json()};
 },{method,args,post});
}
async function choose(page:Page,label:string,value:string){
 await page.getByRole('combobox',{name:label,exact:true}).click();
 await page.getByRole('option',{name:value,exact:true}).click();
}
async function staffLogin(page:Page,account:Account){
 await page.addInitScript(email=>{localStorage.setItem('grc-language','en');localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(email)+':skip-auto','1')},account.email);
 await page.goto('/login?staff=1');
 await page.getByLabel('Email or username',{exact:true}).fill(account.email);
 await page.getByLabel('Password',{exact:true}).fill(account.password);
 const response=page.waitForResponse(r=>r.url().includes('/api/method/login')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 const result=await(await response).json();
 expect(result.exc_type||'').toBe('');
 if(result.verification){
  const code=fixture('login-code',account.email).code;
  await page.getByLabel('Authenticator code',{exact:true}).fill(code);
  await page.getByRole('button',{name:'Verify and continue',exact:true}).click();
 }
 await expect(page).toHaveURL(/\/grc\/auditor(?:[/?#]|$)/);
}
async function profile(page:Page){
 const form=page.getByTestId('organization-profile');
 await expect(form).toBeVisible();
 await form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect(form.getByRole('alert')).toContainText('Select the industry type.');
 await choose(page,'Industry type','Financial Services');
 await choose(page,'Industry sector','Banking');
 const catalog=await rpc(page,'profile_catalog');
 await choose(page,'Company nationality',catalog.data.message.nationalities[0].name);
 await form.getByRole('checkbox',{name:'Not applicable — no KSA license',exact:true}).check();
 await form.getByRole('button',{name:'Save profile',exact:true}).click();
 await expect(form).toHaveCount(0);
}
async function answerAndSubmit(page:Page,kind:string,artifact:string){
 await expect(page.locator('.question-card').first()).toBeVisible();
 let first=true;
 for(let section=0;section<12;section++){
  const cards=page.locator('.question-card');
  for(let i=0;i<await cards.count();i++){
   const card=cards.nth(i),option=card.locator('input[value="C"]:enabled');
   if(!await option.count())continue;
   if(first&&kind==='GRC'){
    await card.locator('input[value="N/A"]:enabled').check();first=false;
   }else await option.check();
  }
  await expect(page.locator('.save-state')).toHaveText(/Saved/);
  if(section===0){
   await page.reload();
   await expect(page.locator('.question-card input:checked').first()).toBeVisible();
  }
  const next=page.getByRole('button',{name:'Next section',exact:true});
  if(await next.count()){await next.click();continue;}
  break;
 }
 const submit=page.getByRole('button',{name:'Submit for review',exact:true});
 await expect(submit).toBeEnabled();
 await submit.click();
 await expect(page.locator('.page-title')).toContainText(/Submitted|Resubmitted/);
 await expect(page.locator('.score-value')).toContainText('75');
 const pdf=page.getByRole('link',{name:'Download preliminary PDF',exact:true});
 await expect(pdf).toBeVisible();
 const response=await page.request.get((await pdf.getAttribute('href'))!);
 expect(response.status()).toBe(200);
 expect(response.headers()['content-disposition']).toContain(kind==='GRC'?'GRC-':'IA-');
 expect((await response.body()).subarray(0,5).toString()).toBe('%PDF-');
 mkdirSync('test-results',{recursive:true});
 writeFileSync(`test-results/${artifact}-preliminary.pdf`,await response.body());
 mkdirSync('../../../diagnostics/demo-cycle-20261112/actual-pdfs',{recursive:true});
 writeFileSync(`../../../diagnostics/demo-cycle-20261112/actual-pdfs/${artifact}-preliminary.pdf`,await response.body());
}
async function emailPdf(page:Page,email:string){
 await page.getByRole('button',{name:'Email report',exact:true}).click();
 const dialog=page.getByRole('dialog');
 await expect(dialog.getByLabel('Recipient',{exact:true})).toHaveValue(email);
 await dialog.getByRole('button',{name:'Send PDF',exact:true}).click();
 await expect(dialog).toHaveCount(0);
}
async function customerLogin(page:Page,email:string){
 await page.addInitScript(email=>{localStorage.setItem('grc-language','en');localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(email)+':skip-auto','1')},email);
 await page.goto('/login');
 await page.getByLabel('Email',{exact:true}).fill(email);
 await page.getByRole('button',{name:'Send code',exact:true}).click();
 await expect(page.getByLabel('Verification code',{exact:true})).toBeVisible();
 await page.getByLabel('Verification code',{exact:true}).fill(fixture('code',email).code);
 await page.getByRole('button',{name:'Verify and continue',exact:true}).click();
 await expect(page).toHaveURL(/\/grc\/customer$/);
}
async function review(browser:Browser,name:string,kind:string,customer?:Page,clarify=false){
 const context=await browser.newContext(),page=await context.newPage();
 const reviewers=staff[kind==='Internal Audit'?'ia':'grc'];
 await staffLogin(page,reviewers.reviewer);
 await page.goto('/grc/auditor/assessments/'+encodeURIComponent(name));
 for(const label of ['Begin review','Approve assessment','Release report']){
  if(label==='Approve assessment'&&clarify&&customer&&process.env.GRC_DEMO_CLARIFICATION==='1'){
   await page.getByRole('button',{name:'Request clarification',exact:true}).click();
   const request=page.getByRole('dialog');
   await request.getByLabel('Review comment',{exact:true}).fill('Please confirm the reserved demo assessment responses and resubmit.');
   await request.getByRole('button',{name:'Confirm',exact:true}).click();
   await expect(request).toHaveCount(0);
   // The clarification creates an immutable correction chain. Continue its
   // current assessment rather than attempting to edit the older submission.
   await customer.goto('/grc/customer/assessments');
   await customer.locator('.record-link').first().click();
   await expect(customer.locator('.question-card').first()).toBeVisible();
   name=decodeURIComponent(customer.url().split('/assessments/')[1].split('/')[0]);
   await answerAndSubmit(customer,kind,`demo-${run}-${kind==='GRC'?'grc':'ia'}-clarified`);
   await page.goto('/grc/auditor/assessments/'+encodeURIComponent(name));
   await page.getByRole('button',{name:'Begin review',exact:true}).click();
   const again=page.getByRole('dialog');
   await again.getByLabel('Review comment',{exact:true}).fill('Verified the customer resubmission.');
   await again.getByRole('button',{name:'Confirm',exact:true}).click();
   await expect(again).toHaveCount(0);
  }
  await page.getByRole('button',{name:label,exact:true}).click();
  const dialog=page.getByRole('dialog');
  if(label!=='Release report')await dialog.getByLabel('Review comment',{exact:true}).fill('Verified reserved demo assessment and selected coverage.');
  await dialog.getByRole('button',{name:'Confirm',exact:true}).click();
  await expect(dialog).toHaveCount(0);
 }
 await page.screenshot({path:`test-results/demo-${run}-${kind==='GRC'?'grc':'ia'}-auditor.png`,fullPage:true});
 await context.close();
 return name;
}

test.beforeAll(()=>{staff=fixture('setup').staff;});
for(const invited of [false,true])for(const kind of ['Internal Audit','GRC'])test(`${invited?'invited':'self-signup'} ${kind}: customer answers, auditor reviews, PDF and registered email`,async({page,browser})=>{
 test.setTimeout(240000);
 const short=kind==='GRC'?'grc':'ia',mode=invited?'invited':'self';
 const email=`grc-journey-${run}-${mode}-${short}@example.test`,company=`Journey demo ${run} ${mode} ${short}`;
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(email=>{localStorage.setItem('grc-language','en');localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(email)+':skip-auto','1')},email);
 if(invited){
  const context=await browser.newContext(),auditor=await context.newPage();
  await staffLogin(auditor,staff[short].consultant);
  await auditor.goto('/grc/auditor/onboarding');
  await auditor.getByRole('button',{name:'Invite customer',exact:true}).click();
  const dialog=auditor.getByRole('dialog');
  await dialog.getByLabel('Customer email',{exact:true}).fill(email);
  await dialog.getByLabel('Company',{exact:true}).fill(company);
  if(kind==='GRC')await dialog.getByRole('checkbox',{name:'Risk',exact:true}).check();
  await dialog.getByRole('button',{name:'Send invitation',exact:true}).click();
  await expect(dialog).toHaveCount(0);
  const url=new URL(fixture('invite-link',email).url);
  await page.goto(url.pathname+url.search);
  await expect(page.getByText(kind==='GRC'?'Invited by the GRC team':'Invited by the Internal Audit team',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Company',{exact:true})).toHaveValue(company);
  await expect(page.getByLabel('Company',{exact:true})).toHaveAttribute('readonly','');
  await page.getByLabel('Full name',{exact:true}).fill('Journey Invited Customer');
  await page.getByRole('checkbox').check();
  await page.getByRole('button',{name:'Send verification code',exact:true}).click();
  await page.getByLabel('Verification code',{exact:true}).fill(fixture('code',email).code);
  await page.getByRole('button',{name:'Verify and continue',exact:true}).click();
  await expect(page).toHaveURL(/\/grc\/customer\/assessments\//);
  await context.close();
 }else{
  await page.goto('/signup');
  await page.getByLabel('Full name',{exact:true}).fill('Journey Self Customer');
  await page.getByLabel('Company',{exact:true}).fill(company);
  await page.getByLabel('Email',{exact:true}).fill(email);
  await page.getByRole('checkbox').check();
  await page.getByRole('button',{name:'Send verification email',exact:true}).click();
  await expect(page.getByLabel('Verification code',{exact:true})).toBeVisible();
  await page.getByLabel('Verification code',{exact:true}).fill(fixture('code',email).code);
  await page.getByRole('button',{name:'Verify and continue',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Your assessments',exact:true})).toBeVisible();
  await page.getByRole('radio',{name:kind==='GRC'?/Governance, Risk and Compliance/:/Internal Audit/}).check();
  await page.getByRole('button',{name:'Continue',exact:true}).click();
  await page.getByRole('dialog').getByRole('button',{name:'Start assessment',exact:true}).click();
  await expect(page).toHaveURL(/\/assessments\//);
 }
 let name=decodeURIComponent(page.url().split('/assessments/')[1].split('/')[0]);
 if(kind==='GRC'){
  await profile(page);
  await expect(page.getByRole('heading',{name:'What would you like assessed?',exact:true})).toBeVisible();
  const payload=(await rpc(page,'assessment',{name})).data.message;
  const bad=await rpc(page,'confirm_assessment_scope',{name,modified:payload.modified,packages:[]},true);
  expect(bad.status).toBe(417);
  if(invited){
   await expect(page.getByRole('checkbox',{name:/Risk/})).toBeChecked();
   await expect(page.getByRole('checkbox',{name:/Risk/})).toBeDisabled();
  }else await page.getByRole('checkbox',{name:/Risk/}).check();
  await page.getByRole('button',{name:'Confirm scope and continue',exact:true}).click();
 }
 await expect(page.locator('.question-card').first()).toBeVisible();
 if(await page.getByRole('button',{name:'Normal view',exact:true}).count())await page.getByRole('button',{name:'Normal view',exact:true}).click();
 await expect(page.getByRole('heading',{name:kind==='GRC'?'GRC Maturity Assessment':'Internal Audit Maturity Assessment',exact:true})).toBeVisible();
 const partial=await rpc(page,'submit_assessment',{name},true);
 expect(partial.status).toBe(417);
 fixture('assign',company,name,kind);
 await answerAndSubmit(page,kind,`demo-${run}-${mode}-${short}`);
 await emailPdf(page,email);
 const preliminary=fixture('evidence',name);
 expect(preliminary.queue_has_pdf_attachment).toBe(true);
 expect(preliminary.transport_accepted).toBe(true);
 expect(preliminary.recipient).toBe(email);
 expect(preliminary.profile_snapshot).toBe(kind==='GRC');
 if(kind==='GRC')expect(preliminary.section_codes).toEqual(['Awareness','Risk']);
 const oppositeContext=await browser.newContext(),opposite=await oppositeContext.newPage();
 await staffLogin(opposite,staff[short==='ia'?'grc':'ia'].consultant);
 await opposite.goto('/grc/auditor');
 const denied=await rpc(opposite,'assessment',{name});
 expect(denied.status).toBe(403);
 await oppositeContext.close();
 name=await review(browser,name,kind,page,!invited);
 await page.reload();
 await expect(page.getByText('Approved report',{exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'Download PDF',exact:true})).toBeVisible();
 if(process.env.GRC_DEMO_CLARIFICATION==='1'){
  await emailPdf(page,email);
  const finalEvidence=fixture('evidence',name);
  expect(finalEvidence.report_released).toBe(true);
  expect(finalEvidence.queue_has_pdf_attachment).toBe(true);
  expect(finalEvidence.transport_accepted).toBe(true);
  expect(finalEvidence.recipient).toBe(email);
 }
 const released=await page.request.get((await page.getByRole('link',{name:'Download PDF',exact:true}).getAttribute('href'))!);
 expect(released.status()).toBe(200);
 expect(released.headers()['content-disposition']).toContain(kind==='GRC'?'GRC-':'IA-');
 writeFileSync(`test-results/demo-${run}-${mode}-${short}-released.pdf`,await released.body());
 writeFileSync(`../../../diagnostics/demo-cycle-20261112/actual-pdfs/demo-${run}-${mode}-${short}-released.pdf`,await released.body());
 await page.screenshot({path:`test-results/demo-${run}-${mode}-${short}-customer.png`,fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:'العربية',exact:true}).click();
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.screenshot({path:`test-results/demo-${run}-${mode}-${short}-customer-ar-mobile.png`,fullPage:true});
 expect(errors).toEqual([]);
 records[mode+'-'+short]={email,company,name};
});

test('a second audit type requires both department managers before customer access changes',async({page,browser})=>{
 test.setTimeout(120000);
 const record=records['self-ia'];
 await customerLogin(page,record.email);
 let denied=await rpc(page,'start_assessment',{entity:record.company,assessment_type:'GRC'},true);
 expect(denied.status).toBe(403);
 await page.goto('/grc/customer/audit-access');
 await page.getByRole('button',{name:'Request another audit type',exact:true}).click();
 await page.getByRole('button',{name:'Send request',exact:true}).click();
 await expect(page.getByRole('button',{name:'Request pending',exact:true})).toBeDisabled();
 for(const department of ['ia','grc'] as const){
  const context=await browser.newContext(),manager=await context.newPage();
  await staffLogin(manager,staff[department].manager);
  await manager.goto('/grc/auditor/audit-access');
  const row=manager.locator('tbody tr').filter({hasText:record.company});
  await row.getByRole('button',{name:'Approve',exact:true}).click();
  const dialog=manager.getByRole('dialog');
  await dialog.getByLabel('Reason',{exact:true}).fill('Approve reserved demo additional audit access.');
  await dialog.getByRole('button',{name:'Confirm',exact:true}).click();
  await expect(dialog).toHaveCount(0);
  await context.close();
  if(department==='ia'){
   denied=await rpc(page,'start_assessment',{entity:record.company,assessment_type:'GRC'},true);
   expect(denied.status).toBe(403);
  }
 }
 await page.reload();
 await expect(page.getByText('GRC',{exact:true}).first()).toBeVisible();
 const result=await rpc(page,'start_assessment',{entity:record.company,assessment_type:'GRC'},true);
 expect(result.status).toBe(200);
 expect(result.data.message.name).toBeTruthy();
 const otherName=result.data.message.name;
 fixture('assign',record.company,otherName,'GRC');
 for(const [department,forbidden] of [['ia',otherName],['grc',record.name]] as const){
  const context=await browser.newContext(),auditor=await context.newPage();
  await staffLogin(auditor,staff[department].consultant);
  await auditor.goto('/grc/auditor');
  const cross=await rpc(auditor,'assessment',{name:forbidden});
  expect(cross.status).toBe(403);
  const dashboard=await rpc(auditor,'dashboard',{entity:record.company});
  expect(dashboard.status).toBe(200);
  expect(dashboard.data.message.assessments.some((a:{name:string})=>a.name===forbidden)).toBe(false);
  await context.close();
 }
});
