import {test,expect,type Page,type Locator} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';

// Native round trips use only the completed reserved local journey fixtures.
// Run sequentially on the muted SMTP-sink server; never record login fields.
test.skip(process.env.GRC_RUN_PERFORMANCE_PREFS_LIVE!=='1','Requires exclusive local native preference acceptance.');
test.describe.configure({mode:'serial'});
test.use({trace:'off',video:'off',screenshot:'off'});
const run=process.env.GRC_DEMO_RUN||'';
const python='/home/frappe/frappe-bench/env/bin/python';
type Account={email:string;password:string};
type Preferences={show_page_tour:boolean;show_help:boolean};
async function enterSecret(field:Locator,value:string){
 await expect(field).toBeEditable();
 try{await field.fill(value)}catch{throw new Error('Reserved authentication entry failed; inspect privately.')}
}
function fixtureCode(email:string,staff=false){
 try{return JSON.parse(execFileSync(python,['../scripts/demo_cycle_fixture.py',staff?'login-code':'code',run,email],{encoding:'utf8',stdio:['ignore','pipe','pipe']})).code as string}
 catch{throw new Error('Reserved local verification helper failed; inspect privately without publishing its output.')}
}
async function login(page:Page,kind:'Customer'|'Auditor'){
 const email=kind==='Customer'?`grc-journey-${run}-self-ia@example.test`:(JSON.parse(readFileSync(`../../../sites/grc.local/private/demo-cycle-${run}.json`,'utf8')).staff.ia.consultant as Account).email;
 await page.addInitScript(email=>{localStorage.setItem('grc-language','en');localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(email)+':skip-auto','1')},email);
 await page.goto(kind==='Customer'?'/login':'/login?staff=1');
 if(kind==='Customer'){
  await page.getByLabel('Email',{exact:true}).fill(email);
  let response=page.waitForResponse(r=>r.url().endsWith('/api/method/ia_maturity.grc.auth.request_code')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Send code',exact:true}).click();
  const first=await response;
  if(first.status()===429){
   const seconds=Number((await first.json()).retry_after_seconds);
   expect(seconds,'Only the real short fixture cooldown may be awaited.').toBeGreaterThan(0);
   expect(seconds,'Hourly quota exhaustion must not be bypassed.').toBeLessThanOrEqual(60);
   await expect(page.getByRole('button',{name:'Send code',exact:true})).toBeEnabled({timeout:(seconds+5)*1000});
   response=page.waitForResponse(r=>r.url().endsWith('/api/method/ia_maturity.grc.auth.request_code')&&r.request().method()==='POST');
   await page.getByRole('button',{name:'Send code',exact:true}).click();
   expect((await response).status()).toBe(200);
  }else expect(first.status()).toBe(200);
  await expect(page.getByLabel('Verification code',{exact:true})).toBeVisible();
  await enterSecret(page.getByLabel('Verification code',{exact:true}),fixtureCode(email));
  await page.getByRole('button',{name:'Verify and continue',exact:true}).click();
 }else{
  const account:Account=JSON.parse(readFileSync(`../../../sites/grc.local/private/demo-cycle-${run}.json`,'utf8')).staff.ia.consultant;
  await page.getByLabel('Email or username',{exact:true}).fill(account.email);
  await enterSecret(page.getByLabel('Password',{exact:true}),account.password);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/method/login')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  const result=await(await response).json();
  if(result.verification){
   await enterSecret(page.getByLabel('Authenticator code',{exact:true}),fixtureCode(email,true));
   await page.getByRole('button',{name:'Verify and continue',exact:true}).click();
  }
 }
 await expect(page).toHaveURL(new RegExp('/grc/'+(kind==='Customer'?'customer':'auditor')+'$'));
}
async function read(page:Page):Promise<Preferences>{
 const response=await page.request.get('/api/method/ia_maturity.grc.api.profile');
 expect(response.status()).toBe(200);
 return (await response.json()).message.workspace_preferences;
}
async function restore(page:Page,preferences:Preferences){
 const status=await page.evaluate(async data=>{
  const response=await fetch('/api/method/ia_maturity.grc.api.save_workspace_preferences',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.csrf_token||''},body:JSON.stringify({data})});
  return response.status;
 },preferences);
 expect(status,'Original native preferences must be restored.').toBe(200);
 await expect.poll(()=>read(page)).toEqual(preferences);
}
for(const kind of ['Customer','Auditor'] as const){
 test(`live ${kind}: preference save, refresh, reload and restoration retain native behavior`,async({page,baseURL})=>{
  test.setTimeout(90000);
  const url=new URL(baseURL||'');expect(['127.0.0.1','localhost']).toContain(url.hostname);expect(url.port).toBe('8007');expect(run).toMatch(/^[a-z0-9]{6,24}$/);
  await login(page,kind);
  const home=kind==='Customer'?'/grc/customer':'/grc/auditor',original=await read(page);
  async function settings(){await page.goto(home+'/profile');await page.getByRole('tab',{name:'Workspace preferences',exact:true}).click()}
  async function save(preferences:Preferences){
   await page.getByRole('checkbox',{name:'Show page tour button',exact:true}).setChecked(preferences.show_page_tour);
   await page.getByRole('checkbox',{name:'Show Help button',exact:true}).setChecked(preferences.show_help);
   await page.getByRole('button',{name:'Save workspace preferences',exact:true}).click();
   await expect.poll(()=>read(page)).toEqual(preferences);
  }
  try{
   await settings();await save({show_page_tour:false,show_help:false});
   await expect(page.getByRole('button',{name:'Take page tour',exact:true})).toHaveCount(0);
   await expect(page.getByRole('link',{name:'Help & guides',exact:true})).toHaveCount(0);
   await page.reload();await page.getByRole('tab',{name:'Workspace preferences',exact:true}).click();
   await expect(page.getByRole('checkbox',{name:'Show Help button',exact:true})).not.toBeChecked();
   await save({show_page_tour:true,show_help:true});
   await expect(page.getByRole('button',{name:'Take page tour',exact:true})).toBeVisible();
   await expect(page.getByRole('link',{name:'Help & guides',exact:true})).toBeVisible();
   await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'العربية',exact:true}).click();
   await expect(page.getByRole('checkbox',{name:'إظهار زر المساعدة',exact:true})).toBeVisible();
  }finally{await restore(page,original)}
 });
}
