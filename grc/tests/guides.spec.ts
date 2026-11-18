import {test,expect,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const credentials=JSON.parse(readFileSync('../../../sites/grc.local/private/grc-local-credentials.json','utf8'));
async function login(page:Page,email:string,staff:boolean){
 await page.goto('/login'); await page.getByLabel('Email or username').fill(email); await page.getByLabel('Password',{exact:true}).fill(credentials[email]); await page.getByRole('button',{name:'Sign in',exact:true}).click();
 if(staff){await expect(page.getByLabel('Authenticator code')).toBeVisible();const otp=execFileSync('../../../env/bin/python',['../scripts/local_test_otp.py',email],{encoding:'utf8'}).trim();await page.getByLabel('Authenticator code').fill(otp);await page.getByRole('button',{name:'Verify and continue'}).click()}
 await expect(page).toHaveURL(/\/grc\/(customer|auditor)$/);
}
for(const [email,staff,title,pdf] of [['customer@alpha.example.test',false,'Customer guide','customer'],['auditor@grc.example.test',true,'Auditor guide','auditor'],['admin@grc.example.test',true,'Administrator guide','admin']] as const){
 test(`${pdf} guide, tour, language and PDF`,async({page})=>{
  await page.addInitScript(()=>{for(const user of ['admin@grc.example.test','auditor@grc.example.test','guide-test@example.test'])localStorage.setItem('grc-page-tour:v1:'+encodeURIComponent(user)+':skip-auto','1')});
  if(!staff){
   await login(page,'admin@grc.example.test',true);
   await page.route('**/api/method/ia_maturity.grc.api.bootstrap',route=>route.fulfill({json:{message:{enabled:true,kind:'Customer',user:'guide-test@example.test',full_name:'Guide Test',home:'/grc/customer',organizations:[]}}}));
   await page.goto('/grc/customer/guide');
  }else{await login(page,email,staff);await page.getByRole('link',{name:'Help & guides'}).click()}
 await expect(page.getByRole('heading',{name:title})).toBeVisible();
  const download=page.getByRole('link',{name:'Download bilingual PDF'});await expect(download).toHaveAttribute('href',`/assets/ia_maturity/guides/${pdf}-guide.pdf`);const response=await page.request.get(await download.getAttribute('href') as string);expect(response.status()).toBe(200);expect(response.headers()['content-type']).toContain('pdf');
  await page.getByRole('button',{name:'Start guided tour'}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('Step 2');await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button',{name:'العربية'}).click();await expect(page.locator('html')).toHaveAttribute('dir','rtl');await expect(page.getByRole('heading',{name:'المساعدة والأدلة'})).toBeVisible();
 });
}
