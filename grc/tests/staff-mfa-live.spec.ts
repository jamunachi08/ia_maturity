import {test,expect,type Page,type Browser} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';

// Real UI/API/native login checks. Opt in only on the muted, disposable local site,
// with exclusive access to staff-policy fixtures. Never record passwords or OTPs.
test.skip(process.env.GRC_RUN_STAFF_MFA_LIVE!=='1','Requires exclusive guarded local staff-MFA acceptance.');
test.describe.configure({mode:'serial'});
test.use({trace:'off',video:'off',screenshot:'off'});

const run='staffmfa20261112';
const admin='admin@grc.example.test';
const python='/home/frappe/frappe-bench/env/bin/python';
type Account={email:string;password:string};
type State={staff:Record<'ia'|'grc',Record<'consultant'|'reviewer'|'manager',Account>>};
type Policy='Default'|'Required'|'Disabled';

function fixture(command:string,...args:string[]):any{
 try{
  return JSON.parse(execFileSync(python,['../scripts/demo_cycle_fixture.py',command,run,...args],{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim());
 }catch{throw new Error('Guarded staff-MFA fixture helper failed; inspect the local helper without publishing its output.');}
}
function adminPassword():string{
 return JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'))[admin];
}
function guard(baseURL:string|undefined){
 const url=new URL(baseURL||'');
 expect(['localhost','127.0.0.1'].includes(url.hostname),'Only the local demo server may run this test.').toBe(true);
 expect(url.port,'Use the isolated native SMTP-sink acceptance server.').toBe('8007');
}
async function rpc(page:Page,method:string,args:Record<string,unknown>={},post=false){
 const result=await page.evaluate(async({method,args,post})=>{
  const path='/api/method/ia_maturity.grc.api.'+method;
  const response=await fetch(post?path:path+'?'+new URLSearchParams(Object.entries(args).map(([key,value])=>[key,String(value)])).toString(),{
   method:post?'POST':'GET',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.csrf_token||''},
   ...(post?{body:JSON.stringify(args)}:{})
  });
  return {status:response.status,body:await response.json()};
 },{method,args,post});
 expect(result.status,'Reserved staff security API request must succeed.').toBe(200);
 return result.body.message;
}
async function login(page:Page,account:Account,requiresMFA?:boolean){
 await page.addInitScript(email=>{
  localStorage.setItem('grc-language','en');
  localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(email)+':skip-auto','1');
 },account.email);
 await page.goto('/login?staff=1');
 await page.getByLabel('Email or username',{exact:true}).fill(account.email);
 await page.getByLabel('Password',{exact:true}).fill(account.password);
 const response=page.waitForResponse(r=>r.url().includes('/api/method/login')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 const nativeResponse=await response;
 expect(nativeResponse.status(),'Reserved staff native password login must succeed.').toBe(200);
 const result=await nativeResponse.json();
 const challenged=Boolean(result.verification);
 if(requiresMFA!==undefined)expect(challenged,'Native staff login must follow its effective admin MFA policy.').toBe(requiresMFA);
 if(challenged){
  const label=result.verification.method==='Email'?'Verification code':'Authenticator code';
  await expect(page.getByLabel(label,{exact:true})).toBeVisible();
  // Keep enough time to submit within Frappe's unchanged 30-second window.
  const remaining=30000-Date.now()%30000;
  if(remaining<5000)await new Promise(resolve=>setTimeout(resolve,remaining+50));
  let code:string;
  try{code=JSON.parse(execFileSync(python,['../scripts/performance_mfa_code.py',account.email,result.tmp_id],{encoding:'utf8',stdio:['ignore','pipe','pipe']})).code;}
  catch{throw new Error('Reserved native staff MFA challenge helper failed; inspect privately.');}
  try{await page.getByLabel(label,{exact:true}).fill(code)}catch{throw new Error('Reserved MFA entry failed; inspect privately.')}
  await page.getByRole('button',{name:'Verify and continue',exact:true}).click();
 }
 await expect(page).toHaveURL(/\/grc\/auditor(?:[/?#]|$)/);
 await page.goto('/grc/auditor');
 await expect(page.getByRole('navigation',{name:'Main navigation'})).toBeVisible();
 await expect(page.getByLabel('Authenticator code',{exact:true})).toHaveCount(0);
}
async function verifyLogin(browser:Browser,account:Account,requiresMFA:boolean,baseURL:string){
 const context=await browser.newContext({baseURL});
 try{await login(await context.newPage(),account,requiresMFA)}finally{await context.close()}
}
async function setPolicyInDialog(page:Page,kind:'role'|'user',policy:Policy,password:string){
 const dialog=page.getByRole('dialog',{name:kind==='role'?'MFA role policy':'Individual MFA policy'});
 await expect(dialog).toBeVisible();
 await dialog.getByRole('combobox',{name:'MFA policy',exact:true}).click();
 await page.getByRole('option',{name:policy,exact:true}).click();
 await dialog.getByLabel('Your current password',{exact:true}).fill(password);
 const response=page.waitForResponse(r=>r.url().includes(kind==='role'?'api.set_role_mfa_policy':'api.set_mfa_policy')&&r.request().method()==='POST');
 await dialog.getByRole('button',{name:'Save policy',exact:true}).click();
 expect((await response).status(),'Staff MFA configuration must save through the real UI.').toBe(200);
 await expect(dialog).toHaveCount(0);
}

test('live: admin role requirement and username exception control actual IA/GRC consultant logins',async({page,browser,baseURL})=>{
 test.setTimeout(180000);
 guard(baseURL);
 const state:State=fixture('setup');
 const ia=state.staff.ia.consultant,grc=state.staff.grc.consultant,password=adminPassword();
 await login(page,{email:admin,password});
 await page.goto('/grc/auditor/admin/security');
 await expect(page.getByRole('heading',{name:'Central MFA settings',exact:true})).toBeVisible();
 const settings=await rpc(page,'security_mfa_settings');
 // Preserve an explicitly configured Enabled policy: prepared staff have no
 // optional enrollment, so both non-enforced policies permit baseline passwords.
 // Required role/user overrides are still checked against actual native challenges.
 expect(['Disabled','Enabled'],'This fixture requires a non-enforced central policy.').toContain(settings.policy);
 expect(['OTP App','Email'],'Preserve the configured native challenge method.').toContain(settings.method);
 const roles=await rpc(page,'security_role_policies');
 const originalRole:Policy=roles.find((row:{role:string})=>row.role==='GRC Consultant').policy;
 const accounts=await rpc(page,'security_accounts',{search:ia.email});
 const originalUser:Policy=accounts.rows.find((row:{name:string})=>row.name===ia.email).policy;
 expect(originalRole,'Prepare this reserved run with inherited consultant policy.').toBe('Default');
 expect(originalUser,'Prepare this reserved run with inherited user policy.').toBe('Default');
 try{
  await verifyLogin(browser,ia,false,baseURL!);
  await verifyLogin(browser,grc,false,baseURL!);
  const roleRow=page.getByRole('row').filter({has:page.getByRole('cell',{name:'GRC Consultant',exact:true})});
  await roleRow.getByRole('button',{name:'Edit role policy',exact:true}).click();
  await setPolicyInDialog(page,'role','Required',password);
  await expect(roleRow.getByRole('cell',{name:'Required',exact:true})).toBeVisible();
  await verifyLogin(browser,ia,true,baseURL!);
  await verifyLogin(browser,grc,true,baseURL!);

  await page.getByLabel('Search',{exact:true}).fill(ia.email);
  const userRow=page.getByRole('row').filter({has:page.getByRole('cell',{name:ia.email,exact:true})});
  await userRow.getByRole('button',{name:'Edit security',exact:true}).click();
  await setPolicyInDialog(page,'user','Disabled',password);
  await expect(userRow.getByRole('cell',{name:'Disabled',exact:true})).toBeVisible();
  await expect(userRow.getByRole('cell',{name:'No',exact:true})).toBeVisible();
  await verifyLogin(browser,ia,false,baseURL!);
  await verifyLogin(browser,grc,true,baseURL!);
 }finally{
  // Restore both independently even when the browser/assertion failed midway.
  try{await rpc(page,'set_role_mfa_policy',{role:'GRC Consultant',policy:originalRole,current_password:password},true)}
  finally{await rpc(page,'set_mfa_policy',{user:ia.email,policy:originalUser,current_password:password},true)}
 }
 await verifyLogin(browser,ia,false,baseURL!);
 await verifyLogin(browser,grc,false,baseURL!);
});

test('live: all six prepared manual IA/GRC staff accounts sign in with password only',async({browser,baseURL})=>{
 test.setTimeout(180000);
 guard(baseURL);
 const manual:State=JSON.parse(readFileSync('../../../sites/grc.local/private/demo-cycle-manual20261112.json','utf8'));
 for(const department of ['ia','grc'] as const){
  for(const role of ['consultant','reviewer','manager'] as const){
   await verifyLogin(browser,manual.staff[department][role],false,baseURL!);
  }
 }
});
