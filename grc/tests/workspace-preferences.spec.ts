import {test,expect,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const credentials=JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'));
async function login(page:Page,email:string){
 await page.addInitScript(user=>{
  localStorage.setItem('grc-language','en');
  localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(user)+':skip-auto','1');
 },email);
 await page.goto('/login');await page.getByLabel('Email or username').fill(email);
 await page.getByLabel('Password',{exact:true}).fill(credentials[email]);
 const response=page.waitForResponse(r=>r.url().endsWith('/api/method/login')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 if((await (await response).json()).verification){
  const code=execFileSync('../../../env/bin/python',['../scripts/local_test_otp.py',email],{encoding:'utf8'}).trim();
  await page.getByLabel('Authenticator code').fill(code);await page.getByRole('button',{name:'Verify and continue'}).click();
 }
 await expect(page).toHaveURL(/\/grc\/(customer|auditor)$/);
}
for(const [email,base] of [['customer@alpha.example.test','/grc/customer'],['auditor@grc.example.test','/grc/auditor']]){
 test(email+' independently hides and restores tour/help controls across sessions',async({page,browser})=>{
  await login(page,email);
  const read=async()=> (await (await page.request.get('/api/method/ia_maturity.grc.api.profile')).json()).message.workspace_preferences;
  const original=await read();
  async function settings(){
   await page.goto(base+'/profile');await page.getByRole('tab',{name:'Workspace preferences',exact:true}).click();
  }
  async function save(tour:boolean,help:boolean){
   await page.getByRole('checkbox',{name:'Show page tour button',exact:true}).setChecked(tour);
   await page.getByRole('checkbox',{name:'Show Help button',exact:true}).setChecked(help);
   await page.getByRole('button',{name:'Save workspace preferences',exact:true}).click();
   await expect.poll(read).toEqual({show_page_tour:tour,show_help:help});
  }
  try{
   await settings();await save(false,false);
   await expect(page.getByRole('button',{name:'Take page tour',exact:true})).toHaveCount(0);
   await expect(page.getByRole('link',{name:'Help & guides',exact:true})).toHaveCount(0);
   await page.reload();await page.getByRole('tab',{name:'Workspace preferences',exact:true}).click();
   await expect(page.getByRole('checkbox',{name:'Show page tour button',exact:true})).not.toBeChecked();
   await expect(page.getByRole('checkbox',{name:'Show Help button',exact:true})).not.toBeChecked();
   await page.getByRole('button',{name:'Sign out',exact:true}).click();await expect(page).toHaveURL(/\/login$/);
   const fresh=await browser.newContext();const second=await fresh.newPage();
   try{
    await login(second,email);
    await second.evaluate(()=>{for(const key of Object.keys(localStorage))if(key.startsWith('grc-page-tour:'))localStorage.removeItem(key)});
    await second.goto(base+'/profile');
    await expect(second.getByRole('tab',{name:'Workspace preferences',exact:true})).toBeVisible();
    // Allow the existing 450 ms automatic-tour timer to elapse.
    await second.waitForTimeout(700);
    await expect(second.locator('.page-tour-dialog')).toHaveCount(0);
    await expect(second.getByRole('button',{name:'Take page tour',exact:true})).toHaveCount(0);
    await expect(second.getByRole('link',{name:'Help & guides',exact:true})).toHaveCount(0);
   }finally{await fresh.close()}
   await login(page,email);await settings();await save(true,false);
   await expect(page.getByRole('button',{name:'Take page tour',exact:true})).toBeVisible();
   await expect(page.getByRole('link',{name:'Help & guides',exact:true})).toHaveCount(0);
   await save(false,true);
   await expect(page.getByRole('button',{name:'Take page tour',exact:true})).toHaveCount(0);
   await expect(page.getByRole('link',{name:'Help & guides',exact:true})).toBeVisible();
   await save(true,true);
   await page.getByRole('button',{name:'العربية',exact:true}).click();
   await expect(page.getByRole('checkbox',{name:'إظهار زر جولة الصفحة',exact:true})).toBeVisible();
   await expect(page.getByRole('checkbox',{name:'إظهار زر المساعدة',exact:true})).toBeVisible();
   await page.setViewportSize({width:390,height:844});
   await expect(page.getByRole('button',{name:'حفظ تفضيلات مساحة العمل',exact:true})).toBeInViewport();
   await page.getByRole('button',{name:'English',exact:true}).click();
  }finally{
   await settings();await save(original.show_page_tour,original.show_help);
  }
 });
}
