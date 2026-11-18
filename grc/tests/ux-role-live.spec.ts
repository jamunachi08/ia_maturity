import {test,expect,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
test.skip(process.env.GRC_RUN_ROLE_UX_LIVE!=='1','Requires the completed guarded local IA/GRC UX cycle.');
test.describe.configure({mode:'serial'});test.use({trace:'off',video:'off',screenshot:'off'});
const run=process.env.GRC_DEMO_RUN||'uxliveb20261112';
type Account={email:string;password:string};
async function login(page:Page,account:Account){
 await page.addInitScript(email=>{localStorage.setItem('grc-language','en');localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(email)+':skip-auto','1')},account.email);
 await page.goto('/login?staff=1');await page.getByLabel('Email or username',{exact:true}).fill(account.email);await page.getByLabel('Password',{exact:true}).fill(account.password);
 const response=page.waitForResponse(r=>r.url().includes('/api/method/login')&&r.request().method()==='POST');await page.getByRole('button',{name:'Sign in',exact:true}).click();expect(Boolean((await(await response).json()).verification)).toBe(false);await expect(page).toHaveURL(/\/grc\/auditor$/);
}
for(const department of ['ia','grc'] as const)test(`live ${department} manager roster, optional assignment and type-specific organization pages`,async({page,baseURL})=>{
 test.setTimeout(90000);const url=new URL(baseURL||'');expect(['localhost','127.0.0.1']).toContain(url.hostname);expect(url.port).toBe('8007');expect(run).toMatch(/^[a-z0-9]{6,24}$/);
 const state=JSON.parse(readFileSync(`../../../sites/grc.local/private/demo-cycle-${run}.json`,'utf8'));
 const company=`Journey demo ${run} self ${department}`;await login(page,state.staff[department].manager);
 await expect(page.getByRole('link',{name:'Available customers',exact:true})).toBeVisible();
 await page.goto('/grc/auditor/oversight');await page.getByLabel('Search',{exact:true}).fill(company);
 const row=page.locator('tbody tr').filter({hasText:company});await expect(row).toHaveCount(1);await row.getByRole('button',{name:'Assign customer',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Customer assignment',exact:true});const writes:string[]=[];page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('api.assign_customer'))writes.push(r.url())});
 await dialog.getByRole('combobox',{name:'Auditor',exact:true}).click();
 await expect(page.getByRole('option').filter({hasText:state.staff[department].reviewer.email})).toBeVisible();
 await expect(page.getByRole('option').filter({hasText:state.staff[department==='ia'?'grc':'ia'].reviewer.email})).toHaveCount(0);
 await page.keyboard.press('Escape');await dialog.getByRole('button',{name:'Close',exact:true}).click();await expect(dialog).toHaveCount(0);expect(writes).toHaveLength(0);
 await page.goto('/grc/auditor/customers/'+encodeURIComponent(company));
 await expect(page.getByRole('tab',{name:'Company profile',exact:true})).toHaveCount(department==='grc'?1:0);
 await expect(page.getByRole('tab',{name:'Audit issues',exact:true})).toHaveCount(department==='ia'?1:0);
 await page.goto('/grc/auditor/guide');await expect(page.getByRole('heading',{name:'Manager guide',exact:true})).toBeVisible();
 await page.screenshot({path:`../../../diagnostics/ux-role-cycle-20261112/screenshots/${department}-manager-live.png`,fullPage:true});
});
